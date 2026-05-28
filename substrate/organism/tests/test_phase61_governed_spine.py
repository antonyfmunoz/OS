"""Tests for Phase 6.1 — GovernedExecutionSpine, ActionEnvelope,
MutationRegistry, ExecutionJournal, SpineGuard.

Validates the single-spine mutation doctrine end-to-end.
"""

from __future__ import annotations

import sys
sys.path.insert(0, "/opt/OS/.claude/worktrees/anti-divergence-gate")

import time
from substrate.organism.action_envelope import (
    ActionEnvelope,
    ActionType,
    BlastRadius,
    EnvelopeStatus,
    ExecutionConstraints,
    ReversibilityClass,
    RollbackStrategy,
    VerificationStrategy,
)
from substrate.organism.event_spine import EventSpine
from substrate.organism.execution_journal import ExecutionJournal, JournalPhase
from substrate.organism.execution_modes import (
    ExecutionMode,
    ExecutionModeManager,
    TransitionReason,
)
from substrate.organism.governed_spine import GovernedExecutionSpine, SpineViolation
from substrate.organism.leverage_metrics import LeverageMetrics
from substrate.organism.mutation_registry import (
    MutationRegistry,
    MutationSpec,
    LOG_ROTATION,
    CONTAINER_RESTART,
)
from substrate.organism.spine_guard import SpineGuard, GuardMode


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_spine(
    mode: ExecutionMode = ExecutionMode.AUTONOMOUS,
) -> tuple[GovernedExecutionSpine, EventSpine, ExecutionModeManager, ExecutionJournal]:
    event_spine = EventSpine()
    mode_mgr = ExecutionModeManager(initial_mode=mode, event_spine=event_spine)
    registry = MutationRegistry()
    journal = ExecutionJournal()
    leverage = LeverageMetrics(event_spine=event_spine)
    spine = GovernedExecutionSpine(
        event_spine=event_spine,
        execution_mode=mode_mgr,
        mutation_registry=registry,
        journal=journal,
        leverage_metrics=leverage,
    )
    return spine, event_spine, mode_mgr, journal


def _success_envelope(intent: str = "test action", source: str = "test") -> ActionEnvelope:
    return ActionEnvelope(
        intent=intent,
        action_type=ActionType.STATE,
        source=source,
        execute_fn=lambda: ("success output", True),
        risk_level="low",
        metadata={"mutation_name": "repo_health"},
    )


def _failing_envelope() -> ActionEnvelope:
    return ActionEnvelope(
        intent="failing action",
        action_type=ActionType.STATE,
        source="test",
        execute_fn=lambda: ("failed", False),
        risk_level="low",
        metadata={"mutation_name": "repo_health"},
    )


def _exception_envelope() -> ActionEnvelope:
    def _boom() -> tuple[str, bool]:
        raise RuntimeError("explosion")
    return ActionEnvelope(
        intent="boom action",
        action_type=ActionType.STATE,
        source="test",
        execute_fn=_boom,
        risk_level="low",
    )


# ── ActionEnvelope tests ────────────────────────────────────────────────────

class TestActionEnvelope:
    def test_creation(self):
        env = _success_envelope()
        assert env.status == EnvelopeStatus.PROPOSED
        assert env.envelope_id
        assert env.created_at > 0
        assert env.action_type == ActionType.STATE

    def test_to_dict(self):
        env = _success_envelope()
        d = env.to_dict()
        assert d["intent"] == "test action"
        assert d["action_type"] == "state"
        assert d["status"] == "proposed"
        assert "envelope_id" in d

    def test_verification_strategy(self):
        vs = VerificationStrategy(description="check file exists")
        d = vs.to_dict()
        assert d["description"] == "check file exists"
        assert d["has_verify_fn"] is False

    def test_rollback_strategy(self):
        rs = RollbackStrategy(description="restore backup")
        d = rs.to_dict()
        assert d["description"] == "restore backup"

    def test_execution_constraints(self):
        ec = ExecutionConstraints(max_retries=3, timeout_seconds=120)
        d = ec.to_dict()
        assert d["max_retries"] == 3
        assert d["timeout_seconds"] == 120.0

    def test_all_action_types(self):
        for at in ActionType:
            env = ActionEnvelope(
                intent=f"test {at.value}",
                action_type=at,
                source="test",
                execute_fn=lambda: ("ok", True),
            )
            assert env.action_type == at

    def test_all_blast_radii(self):
        for br in BlastRadius:
            env = ActionEnvelope(
                intent="test",
                action_type=ActionType.STATE,
                source="test",
                execute_fn=lambda: ("ok", True),
                blast_radius=br,
            )
            assert env.blast_radius == br


# ── MutationRegistry tests ──────────────────────────────────────────────────

class TestMutationRegistry:
    def test_builtins_registered(self):
        registry = MutationRegistry()
        assert registry.is_registered("log_rotation")
        assert registry.is_registered("container_restart")
        assert registry.is_registered("test_suite")
        assert registry.is_registered("graph_rebuild")
        assert registry.is_registered("branch_cleanup")
        assert registry.is_registered("disk_cleanup")
        assert registry.is_registered("repo_health")
        assert registry.is_registered("docker_health")
        assert registry.is_registered("runtime_reconciliation")
        assert registry.is_registered("runtime_refresh")

    def test_lookup(self):
        registry = MutationRegistry()
        spec = registry.lookup("log_rotation")
        assert spec is not None
        assert spec.name == "log_rotation"
        assert spec.action_type == ActionType.FILESYSTEM

    def test_lookup_missing(self):
        registry = MutationRegistry()
        assert registry.lookup("nonexistent") is None

    def test_register_custom(self):
        registry = MutationRegistry()
        spec = MutationSpec(
            name="custom_mutation",
            action_type=ActionType.DEPLOYMENT,
            risk_level="high",
        )
        registry.register(spec)
        assert registry.is_registered("custom_mutation")
        assert registry.lookup("custom_mutation") == spec

    def test_specs_by_risk(self):
        registry = MutationRegistry()
        low = registry.specs_by_risk("low")
        assert len(low) >= 5

    def test_specs_by_type(self):
        registry = MutationRegistry()
        state_specs = registry.specs_by_type(ActionType.STATE)
        assert len(state_specs) >= 2

    def test_to_dict(self):
        registry = MutationRegistry()
        d = registry.to_dict()
        assert d["total_specs"] >= 10
        assert "specs" in d
        assert "by_risk" in d

    def test_mutation_spec_to_dict(self):
        d = LOG_ROTATION.to_dict()
        assert d["name"] == "log_rotation"
        assert d["risk_level"] == "low"
        assert "allowed_modes" in d

    def test_container_restart_requires_approval(self):
        assert CONTAINER_RESTART.require_approval is True
        assert CONTAINER_RESTART.risk_level == "medium"


# ── ExecutionJournal tests ───────────────────────────────────────────────────

class TestExecutionJournal:
    def test_record_and_query(self):
        journal = ExecutionJournal()
        entry = journal.record("env-1", JournalPhase.PROPOSED, "test")
        assert entry.envelope_id == "env-1"
        assert entry.phase == JournalPhase.PROPOSED

        entries = journal.entries_for("env-1")
        assert len(entries) == 1

    def test_lifecycle(self):
        journal = ExecutionJournal()
        journal.record("env-1", JournalPhase.PROPOSED, "test")
        journal.record("env-1", JournalPhase.APPROVED, "test")
        journal.record("env-1", JournalPhase.EXECUTION_STARTED, "test")
        journal.record("env-1", JournalPhase.EXECUTION_COMPLETED, "test")

        lifecycle = journal.execution_lifecycle("env-1")
        assert len(lifecycle) == 4
        phases = [e["phase"] for e in lifecycle]
        assert phases == ["proposed", "approved", "execution_started", "execution_completed"]

    def test_entries_by_phase(self):
        journal = ExecutionJournal()
        journal.record("env-1", JournalPhase.PROPOSED, "test")
        journal.record("env-2", JournalPhase.PROPOSED, "test")
        journal.record("env-1", JournalPhase.APPROVED, "test")

        proposed = journal.entries_by_phase(JournalPhase.PROPOSED)
        assert len(proposed) == 2

    def test_statistics(self):
        journal = ExecutionJournal()
        journal.record("env-1", JournalPhase.EXECUTION_COMPLETED, "test")
        journal.record("env-2", JournalPhase.EXECUTION_COMPLETED, "test")
        journal.record("env-3", JournalPhase.EXECUTION_FAILED, "test")

        stats = journal.statistics()
        assert stats["success_rate"] == round(2 / 3, 4)

    def test_replay_with_filters(self):
        journal = ExecutionJournal()
        journal.record("env-1", JournalPhase.PROPOSED, "test")
        time.sleep(0.01)
        cutoff = time.time()
        time.sleep(0.01)
        journal.record("env-2", JournalPhase.PROPOSED, "test")

        after = journal.replay(since=cutoff)
        assert len(after) == 1
        assert after[0].envelope_id == "env-2"

    def test_to_dict(self):
        journal = ExecutionJournal()
        journal.record("env-1", JournalPhase.PROPOSED, "test")
        d = journal.to_dict()
        assert d["total_entries"] == 1
        assert "recent" in d

    def test_all_journal_phases(self):
        journal = ExecutionJournal()
        for phase in JournalPhase:
            entry = journal.record("env-all", phase, "test")
            assert entry.phase == phase
        assert len(journal.entries_for("env-all")) == len(JournalPhase)


# ── GovernedExecutionSpine tests ─────────────────────────────────────────────

class TestGovernedSpine:
    def test_submit_and_execute_success(self):
        spine, event_spine, mode_mgr, journal = _make_spine()
        env = _success_envelope()
        result = spine.submit(env)
        assert result.status == EnvelopeStatus.COMPLETED
        assert result.result_success is True
        assert result.result_output == "success output"
        assert result.started_at > 0
        assert result.completed_at > 0

    def test_submit_failing_action(self):
        spine, _, _, journal = _make_spine()
        env = _failing_envelope()
        result = spine.submit(env)
        assert result.status == EnvelopeStatus.FAILED
        assert result.result_success is False

    def test_submit_exception_action(self):
        spine, _, _, journal = _make_spine()
        env = _exception_envelope()
        result = spine.submit(env)
        assert result.status == EnvelopeStatus.FAILED
        assert "explosion" in result.result_output

    def test_governance_rejects_unregistered_mutation(self):
        spine, _, _, journal = _make_spine()
        env = ActionEnvelope(
            intent="unknown mutation",
            action_type=ActionType.STATE,
            source="test",
            execute_fn=lambda: ("ok", True),
            metadata={"mutation_name": "nonexistent_mutation"},
        )
        result = spine.submit(env)
        assert result.status == EnvelopeStatus.REJECTED
        assert "unregistered" in result.rejected_reason

    def test_governance_rejects_insufficient_mode(self):
        spine, _, mode_mgr, _ = _make_spine(mode=ExecutionMode.OBSERVE)
        env = ActionEnvelope(
            intent="high risk action",
            action_type=ActionType.CONTAINER,
            source="test",
            execute_fn=lambda: ("ok", True),
            risk_level="high",
        )
        result = spine.submit(env)
        assert result.status == EnvelopeStatus.REJECTED

    def test_approval_flow(self):
        spine, _, _, _ = _make_spine()
        env = ActionEnvelope(
            intent="needs approval",
            action_type=ActionType.CONTAINER,
            source="test",
            execute_fn=lambda: ("approved output", True),
            constraints=ExecutionConstraints(require_approval=True),
            metadata={"mutation_name": "container_restart"},
        )
        result = spine.submit(env)
        assert result.status == EnvelopeStatus.PROPOSED

        pending = spine.pending_envelopes()
        assert len(pending) == 1

        approved = spine.approve(env.envelope_id, approved_by="test_operator")
        assert approved is not None
        assert approved.status == EnvelopeStatus.COMPLETED
        assert approved.approved_by == "test_operator"

    def test_rejection_flow(self):
        spine, _, _, _ = _make_spine()
        env = ActionEnvelope(
            intent="to be rejected",
            action_type=ActionType.STATE,
            source="test",
            execute_fn=lambda: ("ok", True),
            constraints=ExecutionConstraints(require_approval=True),
        )
        spine.submit(env)
        rejected = spine.reject(env.envelope_id, reason="not needed")
        assert rejected is not None
        assert rejected.status == EnvelopeStatus.REJECTED
        assert rejected.rejected_reason == "not needed"

    def test_retry_on_failure(self):
        call_count = [0]

        def _retry_fn() -> tuple[str, bool]:
            call_count[0] += 1
            if call_count[0] < 3:
                return "retrying", False
            return "succeeded on retry", True

        spine, _, _, _ = _make_spine()
        env = ActionEnvelope(
            intent="retry test",
            action_type=ActionType.STATE,
            source="test",
            execute_fn=_retry_fn,
            constraints=ExecutionConstraints(max_retries=3),
        )
        result = spine.submit(env)
        assert result.status == EnvelopeStatus.COMPLETED
        assert result.retry_count == 2

    def test_verification(self):
        spine, _, _, _ = _make_spine()
        env = ActionEnvelope(
            intent="verified action",
            action_type=ActionType.STATE,
            source="test",
            execute_fn=lambda: ("done", True),
            verification=VerificationStrategy(
                description="check it worked",
                verify_fn=lambda: True,
            ),
        )
        result = spine.submit(env)
        assert result.status == EnvelopeStatus.VERIFIED

    def test_verification_failure(self):
        spine, _, _, _ = _make_spine()
        env = ActionEnvelope(
            intent="verification will fail",
            action_type=ActionType.STATE,
            source="test",
            execute_fn=lambda: ("done", True),
            verification=VerificationStrategy(
                description="always fails",
                verify_fn=lambda: False,
            ),
        )
        result = spine.submit(env)
        assert result.status == EnvelopeStatus.VERIFICATION_FAILED

    def test_rollback_on_failure(self):
        rolled_back = [False]

        def _rollback() -> bool:
            rolled_back[0] = True
            return True

        spine, _, _, _ = _make_spine()
        env = ActionEnvelope(
            intent="will fail and rollback",
            action_type=ActionType.STATE,
            source="test",
            execute_fn=lambda: ("failed", False),
            rollback=RollbackStrategy(
                description="rollback",
                rollback_fn=_rollback,
            ),
        )
        result = spine.submit(env)
        assert result.status == EnvelopeStatus.ROLLED_BACK
        assert rolled_back[0] is True

    def test_idempotency(self):
        spine, _, _, _ = _make_spine()
        env1 = ActionEnvelope(
            intent="idempotent action",
            action_type=ActionType.STATE,
            source="test",
            execute_fn=lambda: ("done", True),
            constraints=ExecutionConstraints(idempotent=True),
        )
        result1 = spine.submit(env1)
        assert result1.status == EnvelopeStatus.COMPLETED

        env2 = ActionEnvelope(
            intent="idempotent action",
            action_type=ActionType.STATE,
            source="test",
            execute_fn=lambda: ("done again", True),
            constraints=ExecutionConstraints(idempotent=True),
        )
        result2 = spine.submit(env2)
        assert result2.status == EnvelopeStatus.REJECTED
        assert "idempotent" in result2.rejected_reason

    def test_journal_records_lifecycle(self):
        spine, _, _, journal = _make_spine()
        env = _success_envelope()
        spine.submit(env)

        entries = journal.entries_for(env.envelope_id)
        phases = [e.phase for e in entries]
        assert JournalPhase.PROPOSED in phases
        assert JournalPhase.GOVERNANCE_CHECK in phases
        assert JournalPhase.APPROVED in phases
        assert JournalPhase.EXECUTION_STARTED in phases
        assert JournalPhase.EXECUTION_COMPLETED in phases

    def test_event_spine_emissions(self):
        spine, event_spine, _, _ = _make_spine()
        env = _success_envelope()
        spine.submit(env)

        events = event_spine.recent(100)
        event_types = [e.event_type for e in events]
        assert "envelope_proposed" in event_types
        assert "envelope_executing" in event_types
        assert "envelope_completed" in event_types

    def test_to_dict(self):
        spine, _, _, _ = _make_spine()
        spine.submit(_success_envelope())
        spine.submit(_failing_envelope())

        d = spine.to_dict()
        assert d["total_executed"] == 2
        assert d["total_succeeded"] == 1
        assert d["total_failed"] == 1
        assert "success_rate" in d
        assert "current_mode" in d

    def test_completed_envelopes_query(self):
        spine, _, _, _ = _make_spine()
        spine.submit(_success_envelope("action 1"))
        spine.submit(_success_envelope("action 2"))

        completed = spine.completed_envelopes()
        assert len(completed) == 2

    def test_approve_nonexistent(self):
        spine, _, _, _ = _make_spine()
        result = spine.approve("nonexistent")
        assert result is None

    def test_reject_nonexistent(self):
        spine, _, _, _ = _make_spine()
        result = spine.reject("nonexistent")
        assert result is None

    def test_leverage_metrics_recorded(self):
        event_spine = EventSpine()
        mode_mgr = ExecutionModeManager(initial_mode=ExecutionMode.AUTONOMOUS, event_spine=event_spine)
        registry = MutationRegistry()
        journal = ExecutionJournal()
        leverage = LeverageMetrics(event_spine=event_spine)
        spine = GovernedExecutionSpine(
            event_spine=event_spine,
            execution_mode=mode_mgr,
            mutation_registry=registry,
            journal=journal,
            leverage_metrics=leverage,
        )
        spine.submit(_success_envelope())
        metrics = leverage.to_dict()
        assert metrics["totals"]["tasks"] >= 1


# ── SpineGuard tests ─────────────────────────────────────────────────────────

class TestSpineGuard:
    def test_report_violation(self):
        guard = SpineGuard()
        guard.report_direct_mutation("test_source", "direct subprocess call")
        assert guard.to_dict()["total_violations"] == 1

    def test_recent_violations(self):
        guard = SpineGuard()
        guard.report_direct_mutation("src1", "desc1")
        guard.report_direct_mutation("src2", "desc2")
        recent = guard.recent_violations()
        assert len(recent) == 2

    def test_mode_setting(self):
        guard = SpineGuard(mode=GuardMode.WARN)
        assert guard.mode == GuardMode.WARN
        guard.set_mode(GuardMode.ENFORCE_ALL)
        assert guard.mode == GuardMode.ENFORCE_ALL

    def test_event_spine_emission(self):
        event_spine = EventSpine()
        guard = SpineGuard(event_spine=event_spine)
        guard.report_direct_mutation("test", "violation")
        events = event_spine.recent(10)
        guard_events = [e for e in events if "spine_guard" in e.event_type]
        assert len(guard_events) == 1


# ── Integration tests ────────────────────────────────────────────────────────

class TestIntegration:
    def test_workload_runner_creates_envelope(self):
        from substrate.organism.workload_runner import WorkloadRunner, WorkloadType
        from substrate.organism.operator_compression import OperatorCompression

        event_spine = EventSpine()
        mode_mgr = ExecutionModeManager(initial_mode=ExecutionMode.AUTONOMOUS, event_spine=event_spine)
        leverage = LeverageMetrics(event_spine=event_spine)
        compression = OperatorCompression(event_spine=event_spine)
        runner = WorkloadRunner(
            event_spine=event_spine,
            execution_mode=mode_mgr,
            leverage_metrics=leverage,
            operator_compression=compression,
        )

        env = runner.create_envelope(WorkloadType.REPO_HEALTH)
        assert env.action_type == ActionType.STATE
        assert env.source == "workload_runner"
        assert env.metadata["workload_type"] == "repo_health"

    def test_assisted_executor_creates_envelope(self):
        from substrate.organism.assisted_executor import AssistedExecutor
        from substrate.organism.maintenance_loop import ActionCategory

        event_spine = EventSpine()
        mode_mgr = ExecutionModeManager(initial_mode=ExecutionMode.ASSISTED, event_spine=event_spine)
        leverage = LeverageMetrics(event_spine=event_spine)
        executor = AssistedExecutor(
            execution_mode=mode_mgr,
            event_spine=event_spine,
            leverage_metrics=leverage,
        )

        env = executor.create_envelope(
            action_id="test-1",
            category=ActionCategory.LOG_ROTATION,
            description="Rotate large logs",
        )
        assert env.action_type == ActionType.FILESYSTEM
        assert env.source == "assisted_executor"
        assert env.constraints.require_approval is True

    def test_workload_envelope_through_spine(self):
        from substrate.organism.workload_runner import WorkloadRunner, WorkloadType
        from substrate.organism.operator_compression import OperatorCompression

        event_spine = EventSpine()
        mode_mgr = ExecutionModeManager(initial_mode=ExecutionMode.AUTONOMOUS, event_spine=event_spine)
        leverage = LeverageMetrics(event_spine=event_spine)
        compression = OperatorCompression(event_spine=event_spine)
        runner = WorkloadRunner(
            event_spine=event_spine,
            execution_mode=mode_mgr,
            leverage_metrics=leverage,
            operator_compression=compression,
        )
        registry = MutationRegistry()
        journal = ExecutionJournal()
        spine = GovernedExecutionSpine(
            event_spine=event_spine,
            execution_mode=mode_mgr,
            mutation_registry=registry,
            journal=journal,
            leverage_metrics=leverage,
        )

        env = runner.create_envelope(WorkloadType.REPO_HEALTH)
        result = spine.submit(env)
        assert result.result_success is True
        assert result.status in (EnvelopeStatus.COMPLETED, EnvelopeStatus.VERIFIED)

    def test_full_daemon_has_spine(self):
        from substrate.organism.daemon import OrganismDaemon

        daemon = OrganismDaemon(store_dir="/tmp/test_phase61_daemon")
        assert daemon.governed_spine is not None
        assert daemon.mutation_registry is not None
        assert daemon.execution_journal is not None
        assert daemon.spine_guard is not None

        d = daemon.governed_spine.to_dict()
        assert d["registered_mutations"] >= 10

    def test_mode_transition_blocks_execution(self):
        spine, _, mode_mgr, _ = _make_spine(mode=ExecutionMode.OBSERVE)

        env = ActionEnvelope(
            intent="needs assisted mode",
            action_type=ActionType.CONTAINER,
            source="test",
            execute_fn=lambda: ("ok", True),
            risk_level="medium",
        )
        result = spine.submit(env)
        assert result.status == EnvelopeStatus.REJECTED

        mode_mgr.promote(
            ExecutionMode.AUTONOMOUS,
            reason=TransitionReason.OPERATOR_PROMOTION,
            justification="test",
        )

        env2 = ActionEnvelope(
            intent="now allowed",
            action_type=ActionType.STATE,
            source="test",
            execute_fn=lambda: ("ok", True),
            risk_level="medium",
        )
        result2 = spine.submit(env2)
        assert result2.status == EnvelopeStatus.COMPLETED
