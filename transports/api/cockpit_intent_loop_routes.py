"""Cockpit intent-loop routes — P4S-31 read surface + P4S-31B intent rail seams.

Covers:
- GET  /intent-loop                    (read surface — P4S-31)
- POST /intent-loop/submit             (canonical intent event endpoint — P4S-31B)
- POST /intent-loop/{loop_id}/decision (approve/reject the held gate — P4S-31B)

Doctrine (P4S-31B architecture correction): intent originates ONLY through
sanctioned Cockpit conversational surfaces — Cockpit Chat now, Cockpit Voice
later as a thin adapter into the same Chat channel. The Cockpit Chat rail
(``transports.api.cockpit_chat_routes.try_chat_intent_rail``) is what feeds
:func:`governed_intent_submit` — the ONE governed submit shared by the rail and
the ``POST /intent-loop/submit`` endpoint. Panels are downstream control
surfaces only (approve, reject, inspect); the cockpit frontend does NOT call
/intent-loop/submit directly.

All routes are thin transport wrappers over the substrate-owned IntentLoop,
following the read-surface / governed-write discipline of the sibling EOS
action-proposal routes:

- lazy import of the substrate loop INSIDE the handler,
- try/except → dict, never a 500,
- operator-only auth like sibling cockpit routes (Depends(_require_operator_role)),
- EVERY write routes through the canonical ``governed_mutation`` runtime by
  injecting it as the loop's ``mutation_runner`` — the substrate loop then
  submits each write under its REGISTERED MutationSpec (intent_loop_submit /
  intent_loop_approval_decision). No ungoverned write path.

The gate HOLDS: submit lands the loop at AWAITING_APPROVAL and never advances;
/decision is the ONLY way forward, and approval produces a governed proof
record. A successful decision also persists a server-truth status turn back
into the Cockpit Chat thread (governed ``conversation_send``; non-fatal when
the control plane is down — same availability posture as chat itself).

The path is /intent-loop (not /intent/loop) to avoid colliding with the
existing /intent/{intent_id} intent-preservation route in
cockpit_intent_routes.py — a different concern (IntentRuntime capture/lineage).

UMH transport layer.
"""

from __future__ import annotations

import logging
from typing import Any

from transports.api.read_path_isolation import isolated_read

logger = logging.getLogger(__name__)


def governed_intent_submit(raw_text: str, user_id: str = "umh_operator") -> dict:
    """The ONE governed intent submission — shared by the Cockpit Chat rail and
    the POST /intent-loop/submit endpoint.

    Operator text → deterministic IntentSpec + WorkPacketDraft → captured at
    AWAITING_APPROVAL. The capture WRITE is governed: the substrate loop is
    built with the live ``governed_mutation`` runner injected, so the append
    routes through the registered ``intent_loop_submit`` MutationSpec. The gate
    HOLDS — the loop never auto-advances past AWAITING_APPROVAL. Returns a
    stable dict; never raises.
    """
    try:
        from substrate.execution.intent.loop import IntentLoop
        from transports.api.governed import governed_mutation

        text = (raw_text or "").strip()
        if not text:
            return {
                "surface": "intent_loop_submit",
                "submitted": False,
                "error": "text is required",
            }

        loop = IntentLoop(mutation_runner=governed_mutation)
        record = loop.submit(text, user_id=user_id)
        return {
            "surface": "intent_loop_submit",
            "submitted": True,
            "loop_id": record.loop_id,
            "stage": record.stage,
            "spec": record.spec,
            "draft": record.draft,
            "error": None,
        }
    except Exception as e:
        logger.debug("governed intent submit failed: %s", e)
        return {
            "surface": "intent_loop_submit",
            "submitted": False,
            "error": str(e),
        }


def _persist_decision_status_to_chat(record: Any, decision: str, decided_by: str) -> None:
    """Server-truth decision status back into the Cockpit Chat thread.

    Doctrine: the conversational surface reflects the loop's stage/proof.
    Persisted as a governed ``conversation_send`` turn (the same mutation the
    chat pipeline uses). Best-effort and non-fatal: with the control plane down
    the conversation_send spec fails closed (chat history is daemon-backed
    today), while the decision itself was already governed and recorded.
    Never raises.
    """
    try:
        from transports.api.governed import governed_mutation

        proof = record.proof or {}
        text = (
            f"Intent loop `{record.loop_id}` {decision} by {decided_by} — "
            f"stage {record.stage}, proof `{proof.get('proof_id', '')}` "
            f"(governed_success={proof.get('governed_success')})."
        )

        def _persist() -> tuple[str, bool]:
            from substrate.organism.store import OrganismStore
            from substrate.state.business.business_instance import get_ai_name

            OrganismStore().save_conversation_turn(
                content=f"{decision} intent loop {record.loop_id}",
                response=text,
                origin_channel="cockpit",
                responder=get_ai_name().lower(),
            )
            return ("intent loop decision status saved to chat thread", True)

        governed_mutation(
            mutation_name="conversation_send",
            intent=f"intent loop decision status: {record.loop_id}",
            execute_fn=_persist,
            source="cockpit",
        )
    except Exception as exc:
        logger.debug("decision status chat persistence failed (non-fatal): %s", exc)


def register_intent_loop_routes(router, _require_operator_role, helpers):
    """Register the intent-loop read + decision surfaces onto the given router."""

    from fastapi import Depends

    @router.get("/intent-loop", dependencies=[Depends(_require_operator_role)])
    async def intent_loop():
        """MVP operating-loop server truth — P4S-31.

        Reflects the substrate-owned intent-loop state: each captured intent, its
        drafted packet, the held/decided approval gate, and any governed proof
        record. Read-only mirror; never mutates. Returns a stable flat dict on
        every path (never a 500).

        P4S-31C: this is the primary hot poll surface. It is now ``async`` and
        runs its (bounded) read on the dedicated read pool under a short hard
        timeout, so cockpit polling can NEVER drain the shared AnyIO threadpool
        by piling up copies of this handler, and a stalled filesystem read
        cannot wedge the poller. Response shape is unchanged; on
        timeout/failure it returns the same stable ``error``-shaped dict.
        """
        error_fallback = {
            "surface": "intent_loop",
            "connection_status": "error",
            "total": 0,
            "awaiting_approval": 0,
            "proof_recorded": 0,
            "stage_counts": {},
            "loops": [],
            "error": "read surface unavailable",
        }

        def _read() -> dict:
            from substrate.execution.intent.loop import read_intent_loop_surface

            return read_intent_loop_surface()

        return await isolated_read(
            _read,
            timeout=5.0,
            fallback=error_fallback,
            label="intent_loop_surface",
        )

    @router.post("/intent-loop/submit")
    def intent_loop_submit(
        payload: dict | None = None,
        operator_identity: str = Depends(_require_operator_role),
    ):
        """Canonical intent event endpoint — P4S-31B.

        Fed by the Cockpit Chat intent rail (the sanctioned intent origin); the
        cockpit panel does NOT call this directly. Thin wrapper over
        :func:`governed_intent_submit`; try/except → dict, never a 500.
        """
        try:
            body = payload or {}
            raw_text = str(body.get("text") or body.get("raw_text") or "")
            return governed_intent_submit(raw_text, user_id=operator_identity)
        except Exception as e:
            logger.debug("intent loop submit route failed: %s", e)
            return {
                "surface": "intent_loop_submit",
                "submitted": False,
                "error": str(e),
            }

    @router.post("/intent-loop/{loop_id}/decision")
    def intent_loop_decision(
        loop_id: str,
        payload: dict | None = None,
        operator_identity: str = Depends(_require_operator_role),
    ):
        """Decide one held intent loop — P4S-31B approve/reject.

        The ONLY way the gate advances. The decision routes through the canonical
        ``governed_mutation`` runtime under the registered
        ``intent_loop_approval_decision`` MutationSpec; approval produces a
        governed proof record and reaches PROOF_RECORDED. The recorded decider is
        the AUTHENTICATED operator identity, never client input. A successful
        decision persists a server-truth status turn into the Cockpit Chat
        thread. Thin wrapper, try/except → dict, never a 500. Never executes the
        drafted work.
        """
        try:
            from substrate.execution.intent.loop import IntentLoop
            from transports.api.governed import governed_mutation

            body = payload or {}
            decision = str(body.get("decision") or "").strip().lower()
            reason = str(body["reason"]) if body.get("reason") else None

            loop = IntentLoop(mutation_runner=governed_mutation)
            record = loop.decide(
                loop_id,
                decision,
                decided_by=operator_identity,
                reason=reason,
            )
            if record is None:
                return {
                    "surface": "intent_loop_decision",
                    "decided": False,
                    "loop_id": loop_id,
                    "decision": decision,
                    "error": "unknown loop",
                }

            if record.proof is not None:
                _persist_decision_status_to_chat(record, decision, operator_identity)

            return {
                "surface": "intent_loop_decision",
                "decided": True,
                "loop_id": record.loop_id,
                "stage": record.stage,
                "proof": record.proof,
                "error": None,
            }
        except Exception as e:
            logger.debug("intent loop decision failed: %s", e)
            return {
                "surface": "intent_loop_decision",
                "decided": False,
                "loop_id": loop_id,
                "error": str(e),
            }
