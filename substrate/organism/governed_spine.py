"""GovernedExecutionSpine — THE single mutation gateway in the organism.

EVERY mutation to reality (filesystem, containers, processes, network,
state) MUST flow through this spine. No exceptions.

Subsystems (WorkloadRunner, AssistedExecutor, MaintenanceLoop, Advisor)
become proposal generators. They produce ActionEnvelopes. Only this
spine executes them.

Responsibilities:
  - governance enforcement (execution mode check)
  - mutation registry validation
  - approval gating
  - execution dispatch
  - retry logic
  - rollback orchestration
  - verification
  - journal recording
  - EventSpine emission
  - execution economics
  - idempotency tracking

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import Any

from substrate.organism.action_envelope import (
    ActionEnvelope,
    EnvelopeStatus,
)
from substrate.organism.event_spine import EventDomain, EventPriority, EventSpine
from substrate.organism.execution_journal import ExecutionJournal, JournalPhase
from substrate.organism.execution_modes import ExecutionMode, ExecutionModeManager
from substrate.organism.leverage_metrics import LeverageMetrics, TaskRecord
from substrate.organism.mutation_registry import MutationRegistry

logger = logging.getLogger(__name__)

_MAX_QUEUE = 500
_MAX_COMPLETED = 1000


class SpineViolation(Exception):
    """Raised when a mutation attempt bypasses the spine."""


class GovernedExecutionSpine:
    """THE single mutation gateway for the organism.

    All mutations go through execute(). Direct mutation is blocked.
    """

    def __init__(
        self,
        event_spine: EventSpine,
        execution_mode: ExecutionModeManager,
        mutation_registry: MutationRegistry,
        journal: ExecutionJournal,
        leverage_metrics: LeverageMetrics | None = None,
    ) -> None:
        self._event_spine = event_spine
        self._mode = execution_mode
        self._registry = mutation_registry
        self._journal = journal
        self._leverage = leverage_metrics
        self._lock = threading.Lock()

        self._pending: deque[ActionEnvelope] = deque(maxlen=_MAX_QUEUE)
        self._active: dict[str, ActionEnvelope] = {}
        self._completed: deque[ActionEnvelope] = deque(maxlen=_MAX_COMPLETED)
        self._idempotency_keys: dict[str, str] = {}

        self._total_executed: int = 0
        self._total_succeeded: int = 0
        self._total_failed: int = 0
        self._total_rejected: int = 0
        self._total_rolled_back: int = 0
        self._total_verified: int = 0

    def submit(self, envelope: ActionEnvelope) -> ActionEnvelope:
        """Submit an ActionEnvelope for governance review and execution.

        This is the ONLY entry point for mutations.
        """
        self._journal.record(
            envelope.envelope_id,
            JournalPhase.PROPOSED,
            envelope.source,
            {"intent": envelope.intent, "action_type": envelope.action_type.value},
        )

        self._event_spine.emit(
            EventDomain.EXECUTION,
            "envelope_proposed",
            "governed_spine",
            {"envelope_id": envelope.envelope_id, "intent": envelope.intent},
        )

        rejection = self._governance_check(envelope)
        if rejection:
            envelope.status = EnvelopeStatus.REJECTED
            envelope.rejected_reason = rejection
            self._total_rejected += 1

            self._journal.record(
                envelope.envelope_id,
                JournalPhase.REJECTED,
                "governed_spine",
                {"reason": rejection},
            )
            self._event_spine.emit(
                EventDomain.GOVERNANCE,
                "envelope_rejected",
                "governed_spine",
                {"envelope_id": envelope.envelope_id, "reason": rejection},
                priority=EventPriority.HIGH,
            )

            with self._lock:
                self._completed.append(envelope)
            return envelope

        if envelope.constraints.require_approval:
            envelope.status = EnvelopeStatus.PROPOSED
            with self._lock:
                self._pending.append(envelope)

            self._journal.record(
                envelope.envelope_id,
                JournalPhase.GOVERNANCE_CHECK,
                "governed_spine",
                {"awaiting_approval": True},
            )
            self._event_spine.emit(
                EventDomain.GOVERNANCE,
                "envelope_awaiting_approval",
                "governed_spine",
                {"envelope_id": envelope.envelope_id, "intent": envelope.intent},
            )
            return envelope

        envelope.status = EnvelopeStatus.APPROVED
        envelope.approved_by = "auto_governance"
        self._journal.record(
            envelope.envelope_id,
            JournalPhase.APPROVED,
            "governed_spine",
            {"approved_by": "auto_governance"},
        )

        return self._execute(envelope)

    def approve(self, envelope_id: str, approved_by: str = "operator") -> ActionEnvelope | None:
        """Approve a pending envelope and execute it."""
        envelope = self._pop_pending(envelope_id)
        if envelope is None:
            return None

        envelope.status = EnvelopeStatus.APPROVED
        envelope.approved_by = approved_by

        self._journal.record(
            envelope.envelope_id,
            JournalPhase.APPROVED,
            "governed_spine",
            {"approved_by": approved_by},
        )

        return self._execute(envelope)

    def reject(self, envelope_id: str, reason: str = "operator_rejected") -> ActionEnvelope | None:
        """Reject a pending envelope."""
        envelope = self._pop_pending(envelope_id)
        if envelope is None:
            return None

        envelope.status = EnvelopeStatus.REJECTED
        envelope.rejected_reason = reason
        self._total_rejected += 1

        self._journal.record(
            envelope.envelope_id,
            JournalPhase.REJECTED,
            "governed_spine",
            {"reason": reason},
        )

        with self._lock:
            self._completed.append(envelope)
        return envelope

    def _governance_check(self, envelope: ActionEnvelope) -> str:
        """Validate the envelope against governance rules. Returns rejection reason or empty string."""
        mutation_name = envelope.metadata.get("mutation_name", "")

        if mutation_name and not self._registry.is_registered(mutation_name):
            return f"unregistered mutation: {mutation_name}"

        spec = self._registry.lookup(mutation_name) if mutation_name else None

        if spec is not None:
            if not any(self._mode.can_execute(m) for m in spec.allowed_modes):
                return (
                    f"execution mode {self._mode.current_mode.value} "
                    f"not in allowed modes for {mutation_name}"
                )
        else:
            risk = envelope.risk_level
            if risk in ("high", "critical"):
                if not self._mode.can_execute(ExecutionMode.AUTONOMOUS):
                    return f"risk={risk} requires AUTONOMOUS mode, current={self._mode.current_mode.value}"
            elif risk == "medium":
                if not self._mode.can_execute(ExecutionMode.ASSISTED):
                    return f"risk=medium requires ASSISTED mode, current={self._mode.current_mode.value}"

        if envelope.constraints.idempotent:
            idem_key = f"{envelope.source}:{envelope.intent}"
            if idem_key in self._idempotency_keys:
                return f"idempotent action already executed: {idem_key}"

        self._journal.record(
            envelope.envelope_id,
            JournalPhase.GOVERNANCE_CHECK,
            "governed_spine",
            {"mode": self._mode.current_mode.value, "mutation_name": mutation_name},
        )
        return ""

    def _execute(self, envelope: ActionEnvelope) -> ActionEnvelope:
        """Execute an approved envelope."""
        envelope.status = EnvelopeStatus.EXECUTING
        envelope.started_at = time.time()

        with self._lock:
            self._active[envelope.envelope_id] = envelope

        self._journal.record(
            envelope.envelope_id,
            JournalPhase.EXECUTION_STARTED,
            "governed_spine",
            {"retry_count": envelope.retry_count},
        )
        self._event_spine.emit(
            EventDomain.EXECUTION,
            "envelope_executing",
            "governed_spine",
            {"envelope_id": envelope.envelope_id, "intent": envelope.intent},
        )

        start = time.monotonic()
        try:
            output, success = envelope.execute_fn()
            envelope.result_output = output
            envelope.result_success = success
            duration = time.monotonic() - start

            if success:
                envelope.status = EnvelopeStatus.COMPLETED
                self._total_succeeded += 1

                self._journal.record(
                    envelope.envelope_id,
                    JournalPhase.EXECUTION_COMPLETED,
                    "governed_spine",
                    {"output": output[:500], "duration_s": round(duration, 2)},
                )
            else:
                if envelope.retry_count < envelope.constraints.max_retries:
                    envelope.retry_count += 1
                    self._journal.record(
                        envelope.envelope_id,
                        JournalPhase.RETRY,
                        "governed_spine",
                        {"retry": envelope.retry_count, "last_output": output[:200]},
                    )
                    with self._lock:
                        self._active.pop(envelope.envelope_id, None)
                    return self._execute(envelope)

                envelope.status = EnvelopeStatus.FAILED
                self._total_failed += 1

                self._journal.record(
                    envelope.envelope_id,
                    JournalPhase.EXECUTION_FAILED,
                    "governed_spine",
                    {"output": output[:500], "duration_s": round(duration, 2)},
                )

        except Exception as exc:
            duration = time.monotonic() - start
            envelope.result_output = str(exc)
            envelope.result_success = False
            envelope.status = EnvelopeStatus.FAILED
            self._total_failed += 1

            self._journal.record(
                envelope.envelope_id,
                JournalPhase.EXECUTION_FAILED,
                "governed_spine",
                {"error": str(exc), "duration_s": round(duration, 2)},
            )
            logger.warning("spine execution failed: %s — %s", envelope.envelope_id, exc)

        envelope.completed_at = time.time()
        self._total_executed += 1

        if envelope.result_success and envelope.verification is not None:
            self._verify(envelope)

        if not envelope.result_success and envelope.rollback is not None:
            self._rollback(envelope)

        if envelope.constraints.idempotent and envelope.result_success:
            idem_key = f"{envelope.source}:{envelope.intent}"
            self._idempotency_keys[idem_key] = envelope.envelope_id

        self._mode.record_outcome(
            envelope.envelope_id,
            envelope.result_success,
            result=envelope.result_output[:200],
        )

        if self._leverage is not None:
            self._leverage.record_task(TaskRecord(
                task_id=envelope.envelope_id,
                started_at=envelope.started_at,
                completed_at=envelope.completed_at,
                autonomous=(envelope.approved_by == "auto_governance"),
                required_approval=envelope.constraints.require_approval,
                success=envelope.result_success,
                estimated_manual_seconds=envelope.estimated_manual_seconds,
                actual_seconds=max(envelope.completed_at - envelope.started_at, 0.01),
            ))

        self._event_spine.emit(
            EventDomain.EXECUTION,
            "envelope_completed",
            "governed_spine",
            {
                "envelope_id": envelope.envelope_id,
                "success": envelope.result_success,
                "status": envelope.status.value,
                "duration_s": round(max(envelope.completed_at - envelope.started_at, 0), 2),
            },
            priority=EventPriority.HIGH if not envelope.result_success else EventPriority.NORMAL,
        )

        with self._lock:
            self._active.pop(envelope.envelope_id, None)
            self._completed.append(envelope)

        return envelope

    def _verify(self, envelope: ActionEnvelope) -> None:
        if envelope.verification is None or envelope.verification.verify_fn is None:
            return

        self._journal.record(
            envelope.envelope_id,
            JournalPhase.VERIFICATION_STARTED,
            "governed_spine",
        )

        try:
            passed = envelope.verification.verify_fn()
            if passed:
                envelope.status = EnvelopeStatus.VERIFIED
                self._total_verified += 1
                self._journal.record(
                    envelope.envelope_id,
                    JournalPhase.VERIFICATION_PASSED,
                    "governed_spine",
                )
            else:
                envelope.status = EnvelopeStatus.VERIFICATION_FAILED
                self._journal.record(
                    envelope.envelope_id,
                    JournalPhase.VERIFICATION_FAILED,
                    "governed_spine",
                )
        except Exception as exc:
            envelope.status = EnvelopeStatus.VERIFICATION_FAILED
            self._journal.record(
                envelope.envelope_id,
                JournalPhase.VERIFICATION_FAILED,
                "governed_spine",
                {"error": str(exc)},
            )
            logger.warning("verification failed for %s: %s", envelope.envelope_id, exc)

    def _rollback(self, envelope: ActionEnvelope) -> None:
        if envelope.rollback is None or envelope.rollback.rollback_fn is None:
            return

        self._journal.record(
            envelope.envelope_id,
            JournalPhase.ROLLBACK_STARTED,
            "governed_spine",
        )

        try:
            success = envelope.rollback.rollback_fn()
            if success:
                envelope.status = EnvelopeStatus.ROLLED_BACK
                self._total_rolled_back += 1
                self._journal.record(
                    envelope.envelope_id,
                    JournalPhase.ROLLBACK_COMPLETED,
                    "governed_spine",
                )
            else:
                self._journal.record(
                    envelope.envelope_id,
                    JournalPhase.ROLLBACK_FAILED,
                    "governed_spine",
                )
        except Exception as exc:
            self._journal.record(
                envelope.envelope_id,
                JournalPhase.ROLLBACK_FAILED,
                "governed_spine",
                {"error": str(exc)},
            )
            logger.warning("rollback failed for %s: %s", envelope.envelope_id, exc)

    def _pop_pending(self, envelope_id: str) -> ActionEnvelope | None:
        with self._lock:
            for i, env in enumerate(self._pending):
                if env.envelope_id == envelope_id:
                    del self._pending[i]
                    return env
        return None

    # ── Query interface ──────────────────────────────────────────────────

    def pending_envelopes(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            pending = list(self._pending)
        return [e.to_dict() for e in pending[-limit:]]

    def active_envelopes(self) -> list[dict[str, Any]]:
        with self._lock:
            active = list(self._active.values())
        return [e.to_dict() for e in active]

    def completed_envelopes(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            completed = list(self._completed)
        return [e.to_dict() for e in completed[-limit:]]

    def envelope_lifecycle(self, envelope_id: str) -> list[dict[str, Any]]:
        return self._journal.execution_lifecycle(envelope_id)

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            pending_count = len(self._pending)
            active_count = len(self._active)
            completed_count = len(self._completed)

        total = self._total_succeeded + self._total_failed
        success_rate = round(self._total_succeeded / max(total, 1), 4)

        return {
            "total_executed": self._total_executed,
            "total_succeeded": self._total_succeeded,
            "total_failed": self._total_failed,
            "total_rejected": self._total_rejected,
            "total_rolled_back": self._total_rolled_back,
            "total_verified": self._total_verified,
            "success_rate": success_rate,
            "pending_count": pending_count,
            "active_count": active_count,
            "completed_count": completed_count,
            "current_mode": self._mode.current_mode.value,
            "registered_mutations": len(self._registry.all_specs()),
        }
