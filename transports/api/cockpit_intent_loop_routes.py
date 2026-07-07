"""Cockpit intent-loop routes — P4S-31 read surface + P4S-31B input surface.

Covers:
- GET  /intent-loop                    (read surface — P4S-31)
- POST /intent-loop/submit             (operator text → captured loop — P4S-31B)
- POST /intent-loop/{loop_id}/decision (approve/reject the held gate — P4S-31B)

All three are thin transport wrappers over the substrate-owned IntentLoop,
following the read-surface / governed-write discipline of the sibling EOS
action-proposal routes (rules/projection-read-surfaces.md adapted for a
substrate-owned surface):

- lazy import of the substrate loop INSIDE the handler,
- try/except → dict, never a 500,
- operator-only auth like sibling cockpit routes (Depends(_require_operator_role)),
- EVERY write routes through the canonical ``governed_mutation`` runtime by
  injecting it as the loop's ``mutation_runner`` — the substrate loop then
  submits each write under its REGISTERED MutationSpec (intent_loop_submit /
  intent_loop_approval_decision). No ungoverned write path.

The gate HOLDS: /submit lands the loop at AWAITING_APPROVAL and never advances;
/decision is the ONLY way forward, and approval produces a governed proof
record. The route never auto-executes anything.

The path is /intent-loop (not /intent/loop) to avoid colliding with the
existing /intent/{intent_id} intent-preservation route in
cockpit_intent_routes.py — a different concern (IntentRuntime capture/lineage).

UMH transport layer.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def register_intent_loop_routes(router, _require_operator_role, helpers):
    """Register the intent-loop read + input surfaces onto the given router."""

    from fastapi import Depends

    @router.get("/intent-loop", dependencies=[Depends(_require_operator_role)])
    def intent_loop():
        """MVP operating-loop server truth — P4S-31.

        Reflects the substrate-owned intent-loop state: each captured intent, its
        drafted packet, the held/decided approval gate, and any governed proof
        record. Read-only mirror; never mutates. Returns a stable flat dict on
        every path (never a 500).
        """
        try:
            from substrate.execution.intent.loop import read_intent_loop_surface

            return read_intent_loop_surface()
        except Exception as e:
            logger.debug("intent loop read surface failed: %s", e)
            return {
                "surface": "intent_loop",
                "connection_status": "error",
                "total": 0,
                "awaiting_approval": 0,
                "proof_recorded": 0,
                "stage_counts": {},
                "loops": [],
                "error": str(e),
            }

    @router.post("/intent-loop/submit")
    def intent_loop_submit(
        payload: dict | None = None,
        operator_identity: str = Depends(_require_operator_role),
    ):
        """Capture one operator intent — P4S-31B input surface.

        Operator text → deterministic IntentSpec + WorkPacketDraft → captured at
        AWAITING_APPROVAL. The capture WRITE is governed: the substrate loop is
        built with the live ``governed_mutation`` runner injected, so the append
        routes through the registered ``intent_loop_submit`` MutationSpec. The
        gate HOLDS — the loop never auto-advances past AWAITING_APPROVAL. Thin
        wrapper, try/except → dict, never a 500.
        """
        try:
            from substrate.execution.intent.loop import IntentLoop
            from transports.api.governed import governed_mutation

            body = payload or {}
            raw_text = str(body.get("text") or body.get("raw_text") or "").strip()
            if not raw_text:
                return {
                    "surface": "intent_loop_submit",
                    "submitted": False,
                    "error": "text is required",
                }

            loop = IntentLoop(mutation_runner=governed_mutation)
            record = loop.submit(raw_text, user_id=operator_identity)
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
            logger.debug("intent loop submit failed: %s", e)
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
        the AUTHENTICATED operator identity, never client input. Thin wrapper,
        try/except → dict, never a 500. Never executes the drafted work.
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
