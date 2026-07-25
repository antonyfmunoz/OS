"""IntentLoop — the thinnest UMH operating-loop state machine.

P4S-31. Turns one operator intent into a governed proof record:

    SUBMITTED → SPEC_PARSED → PACKET_DRAFTED → AWAITING_APPROVAL
        (gate HOLDS — no auto-advance)
        → approve/reject via governed_mutation → PROOF_RECORDED

This is the MVP operating-loop SKELETON, not autonomy. It:
- captures intent in a bounded way (deterministic IntentSpec parse),
- drafts one typed WorkPacketDraft,
- HOLDS at the approval gate (never self-advances past AWAITING_APPROVAL),
- routes the approve/reject decision through the canonical
  ``governed_mutation`` runtime (registered MutationSpec — no bypass),
- records a proof/status record in substrate-owned JSON state,
- exposes a flat read-surface dict for Cockpit to mirror.

It NEVER dispatches an agent, executes a provider action, or writes a projection
DB. The only state it writes is substrate-owned JSON under
``<runtime-state>/operator/intent_loop/`` — the same class of local state
``IntentReceiptStore`` and ``IntentContractManager`` already persist.

Governance is REAL, not simulated: the approval decision is submitted through
``transports.api.governed.governed_mutation`` under the registered
``intent_loop_approval_decision`` MutationSpec. When the organism daemon is up
it routes through the GovernedExecutionSpine; when it is down the substrate
fail-closed gate governs it (the spec is low-risk / LOCAL_FILE /
degraded_mode_allowed, so it executes with a mandatory degraded audit record —
governed, never ungoverned).

Deterministic-first: no LLM anywhere in this loop. "All providers down" still
produces IntentSpec + draft + proof.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from substrate.execution.intent.intent_spec import (
    IntentLoopStage,
    IntentSpec,
)

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


def _resolve_default_store_path() -> str:
    from substrate.state.runtime_paths import runtime_state_path

    return str(
        runtime_state_path("operator/intent_loop", "intent_loops.jsonl", create_parent=False)
    )


# Module-level constant computed through the canonical runtime-state boundary.
# It stays a CONSTANT (not a function) because it is the established
# test-isolation seam — the intent-rail and voice suites monkeypatch this
# attribute to redirect the store to a tmp path.
_DEFAULT_STORE_PATH = _resolve_default_store_path()


def _default_store_path() -> str:
    return _DEFAULT_STORE_PATH


# The registered mutation name for the approval decision. Registered in
# substrate.organism.mutation_registry as INTENT_LOOP_APPROVAL_DECISION.
APPROVAL_MUTATION_NAME = "intent_loop_approval_decision"

# The registered mutation name for capturing (submitting) one operator intent.
# Registered in substrate.organism.mutation_registry as INTENT_LOOP_SUBMIT. The
# submit write is governed (never an ungoverned append); the gate still HOLDS —
# a submitted loop lands at AWAITING_APPROVAL and never auto-advances.
SUBMIT_MUTATION_NAME = "intent_loop_submit"

_VALID_DECISIONS = ("approve", "reject")


@dataclass
class ProofRecord:
    """The proof/status artifact for one governed loop decision.

    Every id here comes from the real governed run — the mutation envelope id,
    the decision, the resulting stage. No fabricated envelope ids.
    """

    proof_id: str
    intent_id: str
    draft_id: str
    decision: str
    decided_by: str
    mutation_name: str
    envelope_id: str
    governance_status: str
    governed_success: bool
    degraded: bool
    resulting_stage: str
    recorded_at: float = field(default_factory=time.time)
    reason: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ProofRecord:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class IntentLoopRecord:
    """The full server-truth record of one operating loop.

    Persisted in substrate-owned JSON; this is what the read surface mirrors.
    """

    loop_id: str
    stage: str
    spec: dict[str, Any]
    draft: dict[str, Any]
    proof: dict[str, Any] | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> IntentLoopRecord:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class IntentLoopStore:
    """JSONL append + atomic-rewrite store for IntentLoopRecords.

    Same persistence mechanism as IntentReceiptStore — append-only JSONL with a
    tempfile+os.replace atomic update. NOT a new store technology.
    """

    _lock = threading.Lock()

    def __init__(self, store_path: str | None = None) -> None:
        self._path = store_path or _DEFAULT_STORE_PATH
        os.makedirs(os.path.dirname(self._path), exist_ok=True)

    def append(self, record: IntentLoopRecord) -> None:
        with self._lock:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record.to_dict(), default=str, separators=(",", ":")) + "\n")

    def load_all(self) -> list[IntentLoopRecord]:
        if not os.path.exists(self._path):
            return []
        records: list[IntentLoopRecord] = []
        with open(self._path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(IntentLoopRecord.from_dict(json.loads(line)))
                except (json.JSONDecodeError, TypeError) as exc:
                    logger.debug("skipping malformed intent-loop line: %s", exc)
        return records

    def get(self, loop_id: str) -> IntentLoopRecord | None:
        for r in self.load_all():
            if r.loop_id == loop_id:
                return r
        return None

    def query_recent(self, limit: int = 50) -> list[IntentLoopRecord]:
        records = self.load_all()
        records.sort(key=lambda r: r.created_at, reverse=True)
        return records[:limit]

    def update(self, record: IntentLoopRecord) -> None:
        with self._lock:
            self._update_locked(record)

    def _update_locked(self, record: IntentLoopRecord) -> None:
        records = self.load_all()
        updated = False
        for i, r in enumerate(records):
            if r.loop_id == record.loop_id:
                records[i] = record
                updated = True
                break
        if not updated:
            records.append(record)

        dir_name = os.path.dirname(self._path)
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                for r in records:
                    f.write(json.dumps(r.to_dict(), default=str, separators=(",", ":")) + "\n")
            os.replace(tmp_path, self._path)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise


def _substrate_native_governed_mutation(
    mutation_name: str,
    intent: str,
    execute_fn: Callable[[], tuple[str, bool]],
    source: str = "intent_loop",
    metadata: dict[str, Any] | None = None,
) -> Any:
    """Substrate-native governed submission — canonical spine when live, else fail-closed.

    Resolution order (both in-substrate — dependency-direction law preserved,
    substrate never imports transports):

    1. If a live organism daemon is registered on the CANONICAL organism port
       (``substrate.sockets.organism_port`` — populated by whichever entrypoint
       started the daemon), route through the full daemon-backed
       ``MutationRouter`` → ``GovernedExecutionSpine``. This is what lets a
       HIGH-risk, degraded-disallowed mutation (e.g.
       ``execution_authorization_decision``) actually execute: the control plane
       is present, so it is NOT degraded.
    2. Otherwise fall back to ``route_mutation_degraded`` — the fail-closed gate
       that rejects any non-eligible mutation and only runs low-risk / LOCAL /
       degraded-opted-in specs, always audited.

    Before this, the native runner ALWAYS used route_mutation_degraded, so every
    substrate-native governed mutation degraded even with the daemon running —
    fail-closing execution_authorization_decision and leaving the grant stuck in
    ACTIVATING (observed field run 20260725T175325Z-p1: HUD approve 200, grant
    never ACTIVE, no worker ran). The transport shim's daemon runner is only
    injected on some call paths; the decision source under UnifiedApprovalRuntime
    used this native path, so the daemon must be reachable HERE too.
    """
    from substrate.organism.mutation_router import MutationRequest, route_mutation_degraded

    request = MutationRequest(
        mutation_name=mutation_name,
        intent=intent,
        execute_fn=execute_fn,
        source=source,
        metadata=metadata or {},
    )

    # (1) canonical spine when a daemon is registered — via the substrate port.
    try:
        from substrate.sockets.organism_port import get_organism

        daemon = get_organism()
        if daemon is not None:
            spine = getattr(daemon, "governed_spine", None)
            registry = getattr(daemon, "mutation_registry", None)
            if spine is not None and registry is not None:
                from substrate.organism.mutation_router import MutationRouter

                return MutationRouter(spine=spine, registry=registry).execute(request)
    except Exception:  # noqa: BLE001 — never fail the mutation on router construction; degrade below
        pass

    # (2) no live control plane → substrate's fail-closed degraded gate.
    return route_mutation_degraded(request)


class IntentLoop:
    """The MVP operating-loop orchestrator.

    Thin composition over existing primitives: IntentSpec (deterministic parse),
    WorkPacketDraft, IntentLoopStore (substrate-owned state), and
    governed_mutation (canonical runtime) for the approval gate.
    """

    def __init__(
        self,
        store: IntentLoopStore | None = None,
        mutation_runner: Callable[..., Any] | None = None,
    ) -> None:
        self._store = store or IntentLoopStore()
        # Injectable governed submission callable. The transport route injects
        # transports.api.governed.governed_mutation (full daemon path through the
        # GovernedExecutionSpine). When omitted, the loop falls back to the
        # SUBSTRATE-NATIVE canonical choke point — substrate.organism.
        # mutation_router.route_mutation_degraded — which is exactly what the
        # transport shim itself delegates to when the daemon is down. substrate/
        # never imports transports/ (dependency-direction law); governance is
        # obtained either by injection or from this in-substrate fail-closed
        # gate. There is no ungoverned default path.
        self._mutation_runner = mutation_runner

    def _resolve_mutation_runner(self) -> Callable[..., Any]:
        if self._mutation_runner is not None:
            return self._mutation_runner
        return _substrate_native_governed_mutation

    def submit(
        self,
        raw_text: str,
        org_id: str | None = None,
        user_id: str | None = None,
    ) -> IntentLoopRecord:
        """Capture one bounded intent → IntentSpec → draft → AWAITING_APPROVAL.

        The capture WRITE is governed: the substrate-owned JSON append runs
        inside the registered ``intent_loop_submit`` MutationSpec through the
        canonical governed runner (injected ``governed_mutation`` on the live
        spine path, or the substrate-native fail-closed ``route_mutation_degraded``
        gate when no daemon is injected). There is no ungoverned append path.

        The gate HOLDS here: the returned record is at AWAITING_APPROVAL and does
        NOT advance until :meth:`decide` is called with a governed decision. The
        governance governs the *capture*, never an advancement.
        """
        spec = IntentSpec.from_intent(raw_text, org_id=org_id, user_id=user_id)
        draft = spec.to_draft()

        record = IntentLoopRecord(
            loop_id=f"loop_{uuid.uuid4().hex[:12]}",
            stage=IntentLoopStage.AWAITING_APPROVAL.value,
            spec=spec.to_dict(),
            draft=draft.to_dict(),
        )

        # The governed capture: the ONLY thing that persists the loop. Writes
        # only substrate-owned JSON — no projection DB, no provider, and the gate
        # stays at AWAITING_APPROVAL (never advanced by the capture).
        outcome: dict[str, Any] = {}

        def _execute() -> tuple[str, bool]:
            self._store.append(record)
            outcome["applied"] = True
            return (f"intent captured: loop {record.loop_id}", True)

        runner = self._resolve_mutation_runner()
        try:
            response = runner(
                mutation_name=SUBMIT_MUTATION_NAME,
                intent=f"capture operator intent: {raw_text[:80]}",
                execute_fn=_execute,
                source="intent_loop",
                metadata={
                    "loop_id": record.loop_id,
                    "intent_id": spec.intent_id,
                    "draft_id": draft.draft_id,
                    "org_id": org_id or "",
                    "user_id": user_id or "",
                },
            )
        except Exception as exc:
            logger.error("intent loop submit governed capture failed: %s", exc)
            raise

        governed_success = (
            bool(getattr(response, "success", False)) and outcome.get("applied") is True
        )
        if not governed_success:
            # Fail-closed: the governed gate rejected the capture. No loop was
            # persisted; surface the governance reason rather than a phantom loop.
            reason = getattr(response, "output", "") or getattr(response, "rejected_reason", "")
            raise RuntimeError(f"intent loop submit rejected by governance: {reason}")

        logger.info(
            "intent loop %s: intent %s drafted packet %s, gate HELD at AWAITING_APPROVAL "
            "(governed capture, envelope=%s)",
            record.loop_id,
            spec.intent_id,
            draft.draft_id,
            getattr(response, "envelope_id", "") or "",
        )
        return record

    def decide(
        self,
        loop_id: str,
        decision: str,
        decided_by: str = "umh_operator",
        reason: str | None = None,
    ) -> IntentLoopRecord | None:
        """Advance the gate via a REAL governed_mutation.

        The decision is submitted through the canonical governed runtime under
        the registered ``intent_loop_approval_decision`` MutationSpec. The
        state transition (stage → APPROVED/REJECTED → PROOF_RECORDED and the
        proof write) happens INSIDE the mutation's execute_fn, so the governed
        spine is the only thing that flips the gate. No bypass.

        Returns the updated record, or None if the loop is unknown. Never raises.
        """
        decision = (decision or "").strip().lower()
        record = self._store.get(loop_id)
        if record is None:
            logger.warning("intent loop decide: unknown loop %s", loop_id)
            return None

        if record.stage != IntentLoopStage.AWAITING_APPROVAL.value:
            logger.warning(
                "intent loop %s not awaiting approval (stage=%s); decision ignored",
                loop_id,
                record.stage,
            )
            return record

        if decision not in _VALID_DECISIONS:
            record.proof = ProofRecord(
                proof_id=f"proof_{uuid.uuid4().hex[:12]}",
                intent_id=record.spec.get("intent_id", ""),
                draft_id=record.draft.get("draft_id", ""),
                decision=decision,
                decided_by=decided_by,
                mutation_name=APPROVAL_MUTATION_NAME,
                envelope_id="",
                governance_status="invalid_request",
                governed_success=False,
                degraded=False,
                resulting_stage=record.stage,
                reason=reason,
                error=f"decision must be one of {list(_VALID_DECISIONS)}",
            ).to_dict()
            record.updated_at = time.time()
            self._store.update(record)
            return record

        target_stage = (
            IntentLoopStage.APPROVED.value
            if decision == "approve"
            else IntentLoopStage.REJECTED.value
        )

        # Mutable capture for the governed execute_fn's outcome.
        outcome: dict[str, Any] = {}

        def _execute() -> tuple[str, bool]:
            # The ONLY thing that flips the gate. Runs inside the governed spine
            # (or the fail-closed degraded gate). Writes only substrate-owned
            # JSON — no projection DB, no provider.
            record.stage = target_stage
            record.updated_at = time.time()
            self._store.update(record)
            outcome["applied"] = True
            return (f"loop {loop_id} {decision}d", True)

        runner = self._resolve_mutation_runner()
        try:
            response = runner(
                mutation_name=APPROVAL_MUTATION_NAME,
                intent=f"{decision} intent loop {loop_id}",
                execute_fn=_execute,
                source="intent_loop",
                metadata={
                    "loop_id": loop_id,
                    "intent_id": record.spec.get("intent_id", ""),
                    "draft_id": record.draft.get("draft_id", ""),
                    "decision": decision,
                    "decided_by": decided_by,
                    "reason": reason or "",
                },
            )
        except Exception as exc:
            logger.error("intent loop %s governed decision failed: %s", loop_id, exc)
            record.proof = ProofRecord(
                proof_id=f"proof_{uuid.uuid4().hex[:12]}",
                intent_id=record.spec.get("intent_id", ""),
                draft_id=record.draft.get("draft_id", ""),
                decision=decision,
                decided_by=decided_by,
                mutation_name=APPROVAL_MUTATION_NAME,
                envelope_id="",
                governance_status="governance_unavailable",
                governed_success=False,
                degraded=False,
                resulting_stage=record.stage,
                reason=reason,
                error=str(exc),
            ).to_dict()
            record.updated_at = time.time()
            self._store.update(record)
            return record

        governed_success = (
            bool(getattr(response, "success", False)) and outcome.get("applied") is True
        )

        # Reload — the execute_fn wrote the stage transition through the store.
        record = self._store.get(loop_id) or record

        # Only a successfully-governed decision reaches PROOF_RECORDED. A
        # governance rejection/failure leaves the gate where it was.
        if governed_success:
            resulting_stage = IntentLoopStage.PROOF_RECORDED.value
        else:
            resulting_stage = record.stage

        proof = ProofRecord(
            proof_id=f"proof_{uuid.uuid4().hex[:12]}",
            intent_id=record.spec.get("intent_id", ""),
            draft_id=record.draft.get("draft_id", ""),
            decision=decision,
            decided_by=decided_by,
            mutation_name=APPROVAL_MUTATION_NAME,
            envelope_id=getattr(response, "envelope_id", "") or "",
            governance_status=getattr(response, "status", "") or "",
            governed_success=governed_success,
            degraded=bool(getattr(response, "degraded", False)),
            resulting_stage=resulting_stage,
            reason=reason,
            error=None if governed_success else (getattr(response, "output", "") or None),
        )
        record.stage = resulting_stage
        record.proof = proof.to_dict()
        record.updated_at = time.time()
        self._store.update(record)

        logger.info(
            "intent loop %s: %s governed (success=%s, envelope=%s) → %s",
            loop_id,
            decision,
            governed_success,
            proof.envelope_id,
            resulting_stage,
        )
        return record

    # ── Read surface ─────────────────────────────────────────────────────────

    def read_surface(self, limit: int = 50) -> dict[str, Any]:
        """Flat, JSON-serializable server-truth dict for Cockpit to mirror.

        Side-effect-free, never raises: returns a stable shape even on error.
        This is the substrate-owned analog of a projection read surface.
        """
        try:
            records = self._store.query_recent(limit=limit)
            loops = [r.to_dict() for r in records]
            stage_counts: dict[str, int] = {}
            for r in records:
                stage_counts[r.stage] = stage_counts.get(r.stage, 0) + 1
            return {
                "surface": "intent_loop",
                "canonical_runtime": "governed_mutation -> MutationRouter -> GovernedExecutionSpine",
                "connection_status": "connected",
                "total": len(loops),
                "awaiting_approval": stage_counts.get(IntentLoopStage.AWAITING_APPROVAL.value, 0),
                "proof_recorded": stage_counts.get(IntentLoopStage.PROOF_RECORDED.value, 0),
                "stage_counts": stage_counts,
                "loops": loops,
                "error": None,
            }
        except Exception as exc:  # read surface NEVER 500s
            logger.debug("intent loop read surface error: %s", exc)
            return {
                "surface": "intent_loop",
                "connection_status": "error",
                "total": 0,
                "awaiting_approval": 0,
                "proof_recorded": 0,
                "stage_counts": {},
                "loops": [],
                "error": str(exc),
            }


def read_intent_loop_surface(limit: int = 50) -> dict[str, Any]:
    """Module-level accessor — the substrate-owned read surface for the route.

    Mirrors the projection-read-surface accessor convention (a single named
    function the thin transport route calls). Env-safe and side-effect-free.
    """
    return IntentLoop().read_surface(limit=limit)


__all__ = [
    "APPROVAL_MUTATION_NAME",
    "SUBMIT_MUTATION_NAME",
    "IntentLoop",
    "IntentLoopRecord",
    "IntentLoopStore",
    "ProofRecord",
    "read_intent_loop_surface",
]
