"""Operator Loop Runtime — the Jarvis Runtime.

This IS the product. Not another subsystem — the thing the operator
talks to. Every cockpit interaction, every voice command, every text
query resolves through this runtime.

The 7 methods ARE the operator experience:

  observe    → what's happening right now
  understand → query resolution (voice/text)
  decide     → submit work from intent
  approve    → approve/reject submitted work
  execute    → trigger governed execution
  verify     → inspect proof packages
  continue   → recover/resume + re-observe

No new authority. Pure composition. All execution routes through
GovernedWorkRuntime — this runtime delegates, never bypasses.

Gate 3 — Governed Work Runtime. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Phase enum
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class OperatorLoopPhase(str, Enum):
    OBSERVE = "observe"
    UNDERSTAND = "understand"
    DECIDE = "decide"
    APPROVE = "approve"
    EXECUTE = "execute"
    VERIFY = "verify"
    CONTINUE = "continue"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# State container
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class OperatorLoopState:
    phase: OperatorLoopPhase = OperatorLoopPhase.OBSERVE
    context: dict[str, Any] = field(default_factory=dict)
    available_actions: list[str] = field(default_factory=list)
    work_in_flight: list[dict[str, Any]] = field(default_factory=list)
    pending_approvals: int = 0
    recent_proofs: int = 0
    recovery_available: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase.value
            if isinstance(self.phase, OperatorLoopPhase) else self.phase,
            "context": self.context,
            "available_actions": self.available_actions,
            "work_in_flight": self.work_in_flight,
            "pending_approvals": self.pending_approvals,
            "recent_proofs": self.recent_proofs,
            "recovery_available": self.recovery_available,
            "timestamp": self.timestamp,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# OperatorLoopRuntime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class OperatorLoopRuntime:
    """The Jarvis Runtime — pure composition of existing subsystems.

    Composes:
      - OperatorContextEngine (observe)
      - VoiceQueryEngine (understand)
      - GovernedWorkRuntime (decide / approve / execute)
      - ProofRuntime (verify)
      - WorkRecoveryRuntime (continue)
    """

    def __init__(
        self,
        context_engine: Any | None = None,
        voice_engine: Any | None = None,
        work_runtime: Any | None = None,
        proof_runtime: Any | None = None,
        recovery_runtime: Any | None = None,
    ) -> None:
        self._context_engine = context_engine
        self._voice_engine = voice_engine
        self._work_runtime = work_runtime
        self._proof_runtime = proof_runtime
        self._recovery_runtime = recovery_runtime
        self._current_phase = OperatorLoopPhase.OBSERVE

    # ── Lazy subsystem access ────────────────────────────────────

    @property
    def context_engine(self) -> Any | None:
        if self._context_engine is None:
            try:
                from substrate.operator.operator_context_engine import (
                    OperatorContextEngine,
                )
                self._context_engine = OperatorContextEngine()
            except Exception:
                logger.debug("OperatorContextEngine unavailable")
        return self._context_engine

    @property
    def voice_engine(self) -> Any | None:
        if self._voice_engine is None:
            try:
                from substrate.operator.voice_query_engine import VoiceQueryEngine
                self._voice_engine = VoiceQueryEngine()
            except Exception:
                logger.debug("VoiceQueryEngine unavailable")
        return self._voice_engine

    @property
    def work_runtime(self) -> Any:
        if self._work_runtime is None:
            try:
                from substrate.organism.governed_work_runtime import (
                    GovernedWorkRuntime,
                )
                self._work_runtime = GovernedWorkRuntime()
            except Exception:
                logger.debug("GovernedWorkRuntime unavailable")
        return self._work_runtime

    @property
    def proof_runtime(self) -> Any | None:
        if self._proof_runtime is None:
            try:
                from substrate.organism.proof_runtime import ProofRuntime
                self._proof_runtime = ProofRuntime()
            except Exception:
                logger.debug("ProofRuntime unavailable")
        return self._proof_runtime

    @property
    def recovery_runtime(self) -> Any | None:
        if self._recovery_runtime is None:
            try:
                from substrate.organism.work_recovery_runtime import (
                    WorkRecoveryRuntime,
                )
                self._recovery_runtime = WorkRecoveryRuntime()
            except Exception:
                logger.debug("WorkRecoveryRuntime unavailable")
        return self._recovery_runtime

    # ── The 7 operator methods ───────────────────────────────────

    def observe(self) -> OperatorLoopState:
        """What's happening right now — the operator's situational awareness."""
        self._current_phase = OperatorLoopPhase.OBSERVE

        context: dict[str, Any] = {}

        if self.context_engine is not None:
            try:
                snapshot = self.context_engine.snapshot()
                context["snapshot"] = snapshot.to_dict() if hasattr(snapshot, "to_dict") else {}
            except Exception:
                context["snapshot"] = {"error": "unavailable"}

        work_in_flight: list[dict[str, Any]] = []
        pending_approvals = 0
        recent_proofs = 0
        recovery_available = 0

        if self.work_runtime is not None:
            try:
                work_in_flight = self.work_runtime.active()
            except Exception:
                pass

            try:
                graph = self.work_runtime.graph_snapshot()
                context["work_graph"] = {
                    "total": graph.get("total", 0),
                    "active": graph.get("active", 0),
                    "blocked": graph.get("blocked", 0),
                    "completed": graph.get("completed", 0),
                    "failed": graph.get("failed", 0),
                }
            except Exception:
                pass

        if self.work_runtime is not None and self.work_runtime.work_graph is not None:
            try:
                pending = self.work_runtime.work_graph.work_by_status("approval_pending")
                pending_approvals = len(pending)
            except Exception:
                pass

        if self.proof_runtime is not None:
            try:
                recent_proofs = len(self.proof_runtime.recent(10))
            except Exception:
                pass

        if self.recovery_runtime is not None:
            try:
                recovery_available = len(self.recovery_runtime.recoverable_work())
            except Exception:
                pass

        actions = self._compute_available_actions(
            pending_approvals, recovery_available, work_in_flight,
        )

        return OperatorLoopState(
            phase=OperatorLoopPhase.OBSERVE,
            context=context,
            available_actions=actions,
            work_in_flight=work_in_flight,
            pending_approvals=pending_approvals,
            recent_proofs=recent_proofs,
            recovery_available=recovery_available,
        )

    def understand(self, query: str) -> dict[str, Any]:
        """Resolve a query — voice or text — through VoiceQueryEngine."""
        self._current_phase = OperatorLoopPhase.UNDERSTAND

        if self.voice_engine is not None:
            try:
                resolution = self.voice_engine.resolve(query)
                if hasattr(resolution, "to_dict"):
                    return resolution.to_dict()
                return {"query": query, "result": str(resolution)}
            except Exception as exc:
                return {"query": query, "error": str(exc)}

        return {"query": query, "error": "VoiceQueryEngine unavailable"}

    def decide(
        self,
        intent: str,
        risk_class: str = "low",
        target_executor: str = "",
        description: str = "",
    ) -> dict[str, Any]:
        """Create work from operator intent — routes through GovernedWorkRuntime.

        Wave 2: no ``simulation`` default. The executor must be explicit;
        GovernedWorkRuntime rejects the fake ``simulation`` executor unless a
        test opts in (UMH_ALLOW_SIMULATION_EXECUTOR=1).
        """
        self._current_phase = OperatorLoopPhase.DECIDE

        if self.work_runtime is None:
            return {"error": "GovernedWorkRuntime unavailable"}

        submission = self.work_runtime.submit_work(
            intent=intent,
            risk_class=risk_class,
            target_executor=target_executor,
            description=description,
        )
        return submission.to_dict()

    def approve(
        self,
        work_id: str,
        decided_by: str = "operator",
    ) -> dict[str, Any]:
        """Approve a work item — routes through GovernedWorkRuntime."""
        self._current_phase = OperatorLoopPhase.APPROVE

        if self.work_runtime is None:
            return {"error": "GovernedWorkRuntime unavailable"}

        return self.work_runtime.approve_work(work_id, decided_by=decided_by)

    def reject(
        self,
        work_id: str,
        reason: str = "",
        decided_by: str = "operator",
    ) -> dict[str, Any]:
        """Reject a work item — routes through GovernedWorkRuntime."""
        self._current_phase = OperatorLoopPhase.APPROVE

        if self.work_runtime is None:
            return {"error": "GovernedWorkRuntime unavailable"}

        return self.work_runtime.reject_work(work_id, reason=reason, decided_by=decided_by)

    def execute(self, work_id: str) -> dict[str, Any]:
        """Execute approved work — routes through GovernedWorkRuntime."""
        self._current_phase = OperatorLoopPhase.EXECUTE

        if self.work_runtime is None:
            return {"error": "GovernedWorkRuntime unavailable"}

        receipt = self.work_runtime.execute_work(work_id)
        return receipt.to_dict()

    def verify(self, work_id: str) -> dict[str, Any]:
        """Inspect proof for a work item."""
        self._current_phase = OperatorLoopPhase.VERIFY

        if self.work_runtime is not None:
            proof = self.work_runtime.proof(work_id)
            if proof is not None:
                return proof

        if self.proof_runtime is not None:
            pkg = self.proof_runtime.package_for(work_id)
            if pkg is not None:
                return pkg.to_dict()

        return {"work_id": work_id, "proof": None, "message": "No proof found"}

    def continue_loop(self) -> OperatorLoopState:
        """Recover/resume + re-observe — the "what should I do next?" method."""
        self._current_phase = OperatorLoopPhase.CONTINUE

        state = self.observe()
        state.phase = OperatorLoopPhase.CONTINUE

        if self.recovery_runtime is not None:
            try:
                recoverable = self.recovery_runtime.recoverable_work()
                if recoverable:
                    state.context["recovery"] = [
                        a.to_dict() for a in recoverable[:5]
                    ]
            except Exception:
                pass

        return state

    def current_state(self) -> OperatorLoopState:
        """Return current loop state without transitioning phase."""
        return self.observe()

    # ── Delegation ───────────────────────────────────────────────

    def classify(self, message: str) -> str:
        """Classify operator message intent type."""
        try:
            from substrate.organism.delegation_runtime import classify_intent
            return classify_intent(message).value
        except Exception:
            return "discussion"

    def delegate(
        self, intent: str, clarified_intent: str = "",
        understanding: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Propose delegation through DelegationRuntime."""
        try:
            from substrate.organism.delegation_runtime import DelegationRuntime
            dr = DelegationRuntime()
            proposal = dr.propose_delegation(intent, clarified_intent, understanding)
            return proposal.to_dict()
        except Exception as e:
            logger.error("Delegation failed: %s", e)
            return {"error": str(e)}

    # ── Internal ─────────────────────────────────────────────────

    @staticmethod
    def _compute_available_actions(
        pending_approvals: int,
        recovery_available: int,
        work_in_flight: list[dict[str, Any]],
    ) -> list[str]:
        actions = ["observe", "understand", "decide"]
        if pending_approvals > 0:
            actions.append("approve")
        if work_in_flight:
            actions.append("execute")
            actions.append("verify")
        if recovery_available > 0:
            actions.append("continue")
        return actions
