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
from dataclasses import dataclass, field
from typing import Any

from substrate.organism.action_envelope import (
    ActionEnvelope,
    BlastRadius,
    EnvelopeStatus,
    ReversibilityClass,
)
from substrate.organism.coherence_propagation import (
    OutcomeCommitted,
    OutcomeFailed,
    ParallelPropagationEngine,
)
from substrate.organism.event_spine import EventDomain, EventPriority, EventSpine
from substrate.organism.execution_journal import ExecutionJournal, JournalPhase
from substrate.organism.execution_modes import ExecutionMode, ExecutionModeManager
from substrate.organism.leverage_metrics import LeverageMetrics, TaskRecord
from substrate.organism.mutation_registry import MutationRegistry
from substrate.organism.outcome_learning import (
    OutcomeLearningLoop,
    OutcomeRecord,
    OutcomeStatus,
)

logger = logging.getLogger(__name__)

_MAX_QUEUE = 500
_MAX_COMPLETED = 1000

_FAST_PATH_BLAST_RADII = frozenset({BlastRadius.LOCAL_FILE, BlastRadius.LOCAL_RUNTIME})
_FAST_PATH_MIN_RELIABILITY = 0.95


@dataclass
class FastPathResult:
    eligible: bool = False
    reason: str = ""
    skipped_stages: list[str] = field(default_factory=list)


@dataclass
class SpineTimingData:
    spine_submit_ms: float = 0.0
    governance_check_ms: float = 0.0
    execution_ms: float = 0.0
    proof_capture_ms: float = 0.0
    journal_write_ms: float = 0.0
    learning_record_ms: float = 0.0
    total_overhead_ms: float = 0.0
    fast_path_used: bool = False
    fast_path_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        for k in ("spine_submit_ms", "governance_check_ms", "execution_ms",
                   "proof_capture_ms", "journal_write_ms", "learning_record_ms",
                   "total_overhead_ms"):
            d[k] = round(getattr(self, k), 2)
        d["fast_path_used"] = self.fast_path_used
        d["fast_path_reason"] = self.fast_path_reason
        return d


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
        propagation_engine: ParallelPropagationEngine | None = None,
        learning_loop: OutcomeLearningLoop | None = None,
        compounding_engine: Any | None = None,
        template_extractor: Any | None = None,
        authorization_lookup: Any | None = None,
    ) -> None:
        self._event_spine = event_spine
        self._mode = execution_mode
        self._registry = mutation_registry
        self._journal = journal
        self._leverage = leverage_metrics
        self._propagation = propagation_engine
        self._learning = learning_loop
        self._compounding = compounding_engine
        self._template_extractor = template_extractor
        self._proof_store: Any = None
        # Wave 2 clause 5: resolves an execution authorization_ref to its grant
        # (decision_ref → object with authorized_scope_hash / task_frontier /
        # expires_at / status). Injected to keep the spine substrate-composed. A
        # None lookup with a present authorization_ref fails closed.
        self._authorization_lookup = authorization_lookup
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

    def set_proof_store(self, proof_store: Any) -> None:
        self._proof_store = proof_store

    def _capture_proof(
        self, envelope: ActionEnvelope, timing: SpineTimingData, use_fast: bool
    ) -> None:
        if self._proof_store is None or use_fast:
            return
        try:
            proof_start = time.monotonic()
            pkg = self._proof_store.create(
                request_id=envelope.envelope_id,
                description=envelope.intent,
            )
            pkg.commands_run.append(envelope.result_output[:500])
            pkg.status = "verified" if envelope.result_success else "failed"
            self._proof_store.update(pkg)
            envelope.metadata["proof_id"] = pkg.proof_id
            timing.proof_capture_ms = (time.monotonic() - proof_start) * 1000
        except Exception as exc:
            logger.debug("proof capture failed: %s", exc)

    def _check_fast_path(self, envelope: ActionEnvelope) -> FastPathResult:
        """Determine if this envelope qualifies for reduced-overhead execution.

        Uses learning signal feed when available to inform governance
        decisions — auto_approve_candidate from signal feed reinforces
        fast-path eligibility, block_auto_approval prevents it.
        """
        if self._learning is None:
            return FastPathResult(reason="no learning loop")

        action_type = envelope.action_type.value
        rel = self._learning.get_reliability(action_type)

        signal_feed = self._learning.get_signal_feed(action_type)
        if signal_feed.block_auto_approval:
            return FastPathResult(reason="signal_feed blocked auto-approval")

        if rel < _FAST_PATH_MIN_RELIABILITY:
            return FastPathResult(reason=f"reliability {rel:.3f} < {_FAST_PATH_MIN_RELIABILITY}")
        if envelope.blast_radius not in _FAST_PATH_BLAST_RADII:
            return FastPathResult(reason=f"blast_radius {envelope.blast_radius.value} not local")
        if envelope.reversibility != ReversibilityClass.FULLY_REVERSIBLE:
            return FastPathResult(reason=f"not fully_reversible")

        skipped = ["detailed_proof", "detailed_journal", "governance_scoring"]
        reason = "high-reliability local reversible"
        if signal_feed.auto_approve_candidate:
            skipped.append("manual_approval_check")
            reason = "high-reliability + signal_feed auto_approve"
            envelope.metadata["signal_feed_auto_approve"] = True

        return FastPathResult(eligible=True, reason=reason, skipped_stages=skipped)

    def submit(self, envelope: ActionEnvelope) -> ActionEnvelope:
        """Submit an ActionEnvelope for governance review and execution.

        This is the ONLY entry point for mutations.
        """
        submit_start = time.monotonic()
        timing = SpineTimingData()

        fast_path = self._check_fast_path(envelope)
        timing.fast_path_used = fast_path.eligible
        timing.fast_path_reason = fast_path.reason

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

        gov_start = time.monotonic()
        rejection = self._governance_check(envelope)
        timing.governance_check_ms = (time.monotonic() - gov_start) * 1000

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

            timing.spine_submit_ms = (time.monotonic() - submit_start) * 1000
            timing.total_overhead_ms = timing.spine_submit_ms
            envelope.metadata["spine_timing"] = timing.to_dict()

            with self._lock:
                self._completed.append(envelope)
            return envelope

        self._pre_execution_template_match(envelope)

        if envelope.constraints.require_approval:
            envelope.status = EnvelopeStatus.PROPOSED
            with self._lock:
                self._pending.append(envelope)

            if not fast_path.eligible:
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

            timing.spine_submit_ms = (time.monotonic() - submit_start) * 1000
            timing.total_overhead_ms = timing.spine_submit_ms
            envelope.metadata["spine_timing"] = timing.to_dict()
            return envelope

        envelope.status = EnvelopeStatus.APPROVED
        envelope.approved_by = "auto_governance"

        if not fast_path.eligible:
            self._journal.record(
                envelope.envelope_id,
                JournalPhase.APPROVED,
                "governed_spine",
                {"approved_by": "auto_governance"},
            )

        timing.spine_submit_ms = (time.monotonic() - submit_start) * 1000

        return self._execute(envelope, timing, fast_path)

    def approve(self, envelope_id: str, approved_by: str = "operator") -> ActionEnvelope | None:
        """Approve a pending envelope and execute it."""
        envelope = self._pop_pending(envelope_id)
        if envelope is None:
            return None

        envelope.status = EnvelopeStatus.APPROVED
        envelope.approved_by = approved_by

        timing = SpineTimingData()
        fast_path = self._check_fast_path(envelope)
        timing.fast_path_used = fast_path.eligible
        timing.fast_path_reason = fast_path.reason

        self._journal.record(
            envelope.envelope_id,
            JournalPhase.APPROVED,
            "governed_spine",
            {"approved_by": approved_by},
        )

        return self._execute(envelope, timing, fast_path)

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

        # Wave 2 authorization consumption (Amendment v1 clause 5). If the
        # envelope carries an execution authorization_ref, the action MUST be a
        # subset of the authorized scope. This runs BEFORE the fast-path/approval
        # branch, so no reliability fast path or require_approval=False can bypass
        # it. An out-of-scope or expired authority is rejected (fail closed).
        auth_rejection = self._check_authorization_scope(envelope)
        if auth_rejection:
            return auth_rejection

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

    def _check_authorization_scope(self, envelope: ActionEnvelope) -> str:
        """Wave 2 clause 5: consume explicit HUD execution authority. Returns a
        rejection reason if the action is not a subset of the authorized scope,
        or empty string if the envelope carries no authorization_ref (non-Wave-2
        actions are unaffected)."""
        auth_ref = getattr(envelope, "authorization_ref", "")
        if not auth_ref:
            return ""  # not an authorization-bound action

        if self._authorization_lookup is None:
            return f"authorization {auth_ref} cannot be validated (no lookup) — fail closed"
        try:
            grant = self._authorization_lookup(auth_ref)
        except Exception as exc:
            return f"authorization {auth_ref} lookup failed: {exc}"
        if grant is None:
            return f"authorization {auth_ref} not found — fail closed"

        # Must be an ACTIVE grant.
        if getattr(grant, "status", "") != "active":
            return f"authorization {auth_ref} is {getattr(grant, 'status', '')!r}, not active"

        # Not expired.
        expires_at = float(getattr(grant, "expires_at", 0.0) or 0.0)
        if expires_at and time.time() >= expires_at:
            return f"authorization {auth_ref} expired"

        # Scope-hash must match (immutable authorized scope).
        env_hash = getattr(envelope, "authorized_scope_hash", "")
        grant_hash = getattr(grant, "authorized_scope_hash", "")
        if env_hash and grant_hash and env_hash != grant_hash:
            return f"authorization {auth_ref} scope hash mismatch (out of scope)"

        # Authorized subjects must be a subset of the grant's task frontier.
        env_subjects = set(getattr(envelope, "authorized_subject_ids", []) or [])
        grant_frontier = set(getattr(grant, "task_frontier", []) or [])
        if env_subjects and not env_subjects.issubset(grant_frontier):
            out_of_scope = sorted(env_subjects - grant_frontier)
            return f"authorization {auth_ref}: subjects {out_of_scope} not in authorized frontier"

        return ""

    def _execute(
        self,
        envelope: ActionEnvelope,
        timing: SpineTimingData | None = None,
        fast_path: FastPathResult | None = None,
    ) -> ActionEnvelope:
        """Execute an approved envelope."""
        if timing is None:
            timing = SpineTimingData()
        if fast_path is None:
            fast_path = FastPathResult()
        use_fast = fast_path.eligible

        envelope.status = EnvelopeStatus.EXECUTING
        envelope.started_at = time.time()

        with self._lock:
            self._active[envelope.envelope_id] = envelope

        j_start = time.monotonic()
        self._journal.record(
            envelope.envelope_id,
            JournalPhase.EXECUTION_STARTED,
            "governed_spine",
            {"retry_count": envelope.retry_count, "fast_path": use_fast},
        )
        self._event_spine.emit(
            EventDomain.EXECUTION,
            "envelope_executing",
            "governed_spine",
            {"envelope_id": envelope.envelope_id, "intent": envelope.intent},
        )

        exec_start = time.monotonic()
        try:
            output, success = envelope.execute_fn()
            envelope.result_output = output
            envelope.result_success = success
            timing.execution_ms = (time.monotonic() - exec_start) * 1000

            if success:
                envelope.status = EnvelopeStatus.COMPLETED
                self._total_succeeded += 1

                if not use_fast:
                    self._journal.record(
                        envelope.envelope_id,
                        JournalPhase.EXECUTION_COMPLETED,
                        "governed_spine",
                        {"output": output[:500], "duration_s": round(timing.execution_ms / 1000, 2)},
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
                    return self._execute(envelope, timing, fast_path)

                envelope.status = EnvelopeStatus.FAILED
                self._total_failed += 1

                self._journal.record(
                    envelope.envelope_id,
                    JournalPhase.EXECUTION_FAILED,
                    "governed_spine",
                    {"output": output[:500], "duration_s": round(timing.execution_ms / 1000, 2)},
                )

        except Exception as exc:
            timing.execution_ms = (time.monotonic() - exec_start) * 1000
            envelope.result_output = str(exc)
            envelope.result_success = False
            envelope.status = EnvelopeStatus.FAILED
            self._total_failed += 1

            self._journal.record(
                envelope.envelope_id,
                JournalPhase.EXECUTION_FAILED,
                "governed_spine",
                {"error": str(exc), "duration_s": round(timing.execution_ms / 1000, 2)},
            )
            logger.warning("spine execution failed: %s — %s", envelope.envelope_id, exc)

        envelope.completed_at = time.time()
        self._total_executed += 1
        timing.journal_write_ms = (time.monotonic() - j_start) * 1000 - timing.execution_ms

        self._capture_proof(envelope, timing, use_fast)

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
            self._leverage.record_task(
                TaskRecord(
                    task_id=envelope.envelope_id,
                    started_at=envelope.started_at,
                    completed_at=envelope.completed_at,
                    autonomous=(envelope.approved_by == "auto_governance"),
                    required_approval=envelope.constraints.require_approval,
                    success=envelope.result_success,
                    estimated_manual_seconds=envelope.estimated_manual_seconds,
                    actual_seconds=max(envelope.completed_at - envelope.started_at, 0.01),
                )
            )

        learn_start = time.monotonic()
        self._record_learning(envelope)
        timing.learning_record_ms = (time.monotonic() - learn_start) * 1000

        self._post_execution_compounding(envelope)

        self._event_spine.emit(
            EventDomain.EXECUTION,
            "envelope_completed",
            "governed_spine",
            {
                "envelope_id": envelope.envelope_id,
                "success": envelope.result_success,
                "status": envelope.status.value,
                "duration_s": round(max(envelope.completed_at - envelope.started_at, 0), 2),
                "fast_path": use_fast,
            },
            priority=EventPriority.HIGH if not envelope.result_success else EventPriority.NORMAL,
        )

        self._emit_outcome(envelope)

        if use_fast:
            self._journal.record(
                envelope.envelope_id,
                JournalPhase.EXECUTION_COMPLETED,
                "governed_spine",
                {"fast_path": True, "status": envelope.status.value,
                 "duration_s": round(timing.execution_ms / 1000, 2)},
            )

        timing.total_overhead_ms = (
            timing.spine_submit_ms + timing.governance_check_ms
            + timing.journal_write_ms + timing.learning_record_ms
        )
        envelope.metadata["spine_timing"] = timing.to_dict()

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

        self._attach_outcome_verification(envelope)

    def _attach_outcome_verification(self, envelope: ActionEnvelope) -> None:
        """If an OutcomeVerificationEngine produced a result for this envelope,
        store it in the envelope metadata for downstream consumers."""
        try:
            from substrate.organism.outcome_verification import (
                OutcomeVerificationEngine,
            )

            engine = getattr(self, "_outcome_engine", None)
            if engine is None:
                return
            verification = engine.get_verification(envelope.envelope_id)
            if verification is not None:
                if not hasattr(envelope, "metadata"):
                    return
                envelope.metadata["outcome_verification"] = verification.to_dict()
        except Exception as exc:
            logger.debug("outcome verification attach skipped: %s", exc)

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

    def _emit_outcome(self, envelope: ActionEnvelope) -> None:
        """Emit OutcomeCommitted or OutcomeFailed based on envelope final state.

        If a propagation engine is registered, triggers organism-wide
        coherence propagation automatically. This is the spine-native
        propagation path — callers never need to call propagation manually.
        """
        duration_ms = max(envelope.completed_at - envelope.started_at, 0) * 1000
        metadata = envelope.metadata

        if envelope.status in (EnvelopeStatus.VERIFIED, EnvelopeStatus.COMPLETED):
            validation = "passed" if envelope.status == EnvelopeStatus.VERIFIED else "not_verified"
            rollback = "not_needed"
            if envelope.status == EnvelopeStatus.COMPLETED and envelope.rollback is not None:
                rollback = "not_triggered"

            outcome = OutcomeCommitted(
                action_envelope_id=envelope.envelope_id,
                execution_graph_id=metadata.get("execution_graph_id", ""),
                trial_id=metadata.get("trial_id", ""),
                action_type=envelope.action_type.value,
                mutation_type=metadata.get("mutation_name", ""),
                risk_class=envelope.risk_level,
                agent_type=metadata.get("agent_type", "developer_agent"),
                capabilities_used=envelope.required_capabilities,
                validation_result=validation,
                rollback_result=rollback,
                duration_ms=duration_ms,
                changed_files=metadata.get("changed_files", []),
                changed_entities=metadata.get("changed_entities", []),
                affected_subsystems=metadata.get("affected_subsystems", []),
                evidence=[f"output: {envelope.result_output[:200]}"],
                completed_at=envelope.completed_at,
            )

            self._event_spine.emit(
                EventDomain.EXECUTION,
                "outcome_committed",
                "governed_spine",
                outcome.to_dict(),
            )

            if self._propagation is not None:
                try:
                    self._propagation.handle_outcome(outcome)
                except Exception as exc:
                    logger.warning(
                        "Propagation failed for %s (non-fatal): %s",
                        envelope.envelope_id,
                        exc,
                    )

        elif envelope.status in (
            EnvelopeStatus.FAILED,
            EnvelopeStatus.VERIFICATION_FAILED,
            EnvelopeStatus.ROLLED_BACK,
        ):
            rollback_result = "not_attempted"
            if envelope.status == EnvelopeStatus.ROLLED_BACK:
                rollback_result = "rolled_back"

            failed = OutcomeFailed(
                action_envelope_id=envelope.envelope_id,
                execution_graph_id=metadata.get("execution_graph_id", ""),
                trial_id=metadata.get("trial_id", ""),
                action_type=envelope.action_type.value,
                risk_class=envelope.risk_level,
                agent_type=metadata.get("agent_type", "developer_agent"),
                failure_reason=envelope.result_output[:500],
                validation_result=(
                    "verification_failed"
                    if envelope.status == EnvelopeStatus.VERIFICATION_FAILED
                    else "execution_failed"
                ),
                evidence=[f"output: {envelope.result_output[:200]}"],
            )

            self._event_spine.emit(
                EventDomain.EXECUTION,
                "outcome_failed",
                "governed_spine",
                failed.to_dict(),
                priority=EventPriority.HIGH,
            )

            if self._propagation is not None:
                try:
                    self._propagation.handle_failure(failed)
                except Exception as exc:
                    logger.warning(
                        "Failure recording failed for %s: %s",
                        envelope.envelope_id,
                        exc,
                    )

    def _pre_execution_template_match(self, envelope: ActionEnvelope) -> None:
        """Check if a template matches this envelope's intent before execution."""
        if self._template_extractor is None:
            return
        try:
            files_hint = envelope.metadata.get("files_changed", [])
            matched = self._template_extractor.match_template(
                files_changed=files_hint,
                task_description=envelope.intent,
            )
            if matched is not None:
                envelope.metadata["matched_template"] = {
                    "template_id": matched.template_id,
                    "task_shape": matched.task_shape,
                    "times_matched": matched.times_matched,
                }
                logger.info(
                    "Template %s matched for envelope %s (shape=%s)",
                    matched.template_id, envelope.envelope_id, matched.task_shape,
                )
        except Exception as exc:
            logger.debug("template match failed (non-fatal): %s", exc)

    def _post_execution_compounding(self, envelope: ActionEnvelope) -> None:
        """Run compounding pipeline after successful execution.

        Wires three dormant systems:
        1. CompoundingEngine.scan_after_cycle — detects promotion candidates
        2. TemplateExtractor.extract_from_cycle — builds/matches templates
        3. Signal feed already consumed in _check_fast_path
        """
        if not envelope.result_success:
            return

        if self._compounding is not None:
            try:
                outcome_data = {
                    "envelope_id": envelope.envelope_id,
                    "action_type": envelope.action_type.value,
                    "intent": envelope.intent[:200],
                    "success": envelope.result_success,
                    "output": envelope.result_output[:200],
                    "duration_s": max(envelope.completed_at - envelope.started_at, 0),
                }
                candidates = self._compounding.scan_after_cycle(
                    outcomes=[outcome_data],
                )
                if candidates:
                    envelope.metadata["compounding_candidates"] = len(candidates)
                    logger.info(
                        "Compounding found %d candidates for envelope %s",
                        len(candidates), envelope.envelope_id,
                    )
            except Exception as exc:
                logger.debug("compounding scan failed (non-fatal): %s", exc)

        if self._template_extractor is not None:
            try:
                files_changed = envelope.metadata.get("files_changed", [])
                extracted = self._template_extractor.extract_from_cycle(
                    cycle_id=envelope.envelope_id,
                    files_changed=files_changed,
                    task_description=envelope.intent,
                )
                if extracted is not None:
                    envelope.metadata["extracted_template"] = {
                        "template_id": extracted.template_id,
                        "task_shape": extracted.task_shape,
                    }
            except Exception as exc:
                logger.debug("template extraction failed (non-fatal): %s", exc)

    def _record_learning(self, envelope: ActionEnvelope) -> None:
        """Record the execution outcome in the learning loop.

        Direct path — does not depend on propagation engine being wired.
        """
        if self._learning is None:
            return
        try:
            duration = max(envelope.completed_at - envelope.started_at, 0)
            status = OutcomeStatus.SUCCESS if envelope.result_success else OutcomeStatus.FAILURE
            if envelope.result_success and envelope.status == EnvelopeStatus.VERIFICATION_FAILED:
                status = OutcomeStatus.PARTIAL

            record = OutcomeRecord(
                action_type=envelope.action_type.value,
                description=envelope.intent[:200],
                status=status,
                expected_result="success",
                actual_result=envelope.result_output[:200],
                duration_seconds=duration,
                error="" if envelope.result_success else envelope.result_output[:200],
            )
            self._learning.record_outcome(record)
        except Exception as exc:
            logger.debug("learning loop record failed (non-fatal): %s", exc)

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

    @property
    def propagation_engine(self) -> ParallelPropagationEngine | None:
        return self._propagation

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            pending_count = len(self._pending)
            active_count = len(self._active)
            completed_count = len(self._completed)

        total = self._total_succeeded + self._total_failed
        success_rate = round(self._total_succeeded / max(total, 1), 4)

        learning_summary = self._learning.summary() if self._learning is not None else None

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
            "spine_native_propagation": self._propagation is not None,
            "learning_loop_connected": self._learning is not None,
            "learning_summary": learning_summary,
        }
