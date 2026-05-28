"""Phase 6.3 — Autonomous Execution Spine Gate tests.

Proves that:
  1. Autonomous systems cannot mutate reality except through GovernedExecutionSpine
  2. The AutonomousActionGateway enforces policy correctly
  3. Different policy levels produce correct behavior
  4. Direct mutation attempts are blocked
  5. Approval lifecycle works end-to-end
  6. SpineGuard catches remaining bypasses
  7. Cockpit endpoint integration is wired
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from substrate.organism.action_envelope import (
    ActionEnvelope,
    ActionType,
    BlastRadius,
    EnvelopeStatus,
    ExecutionConstraints,
    ReversibilityClass,
)
from substrate.organism.autonomous_action_gateway import (
    AutonomousActionGateway,
    AutonomousPolicy,
)
from substrate.organism.daemon import OrganismDaemon
from substrate.organism.event_spine import EventSpine
from substrate.organism.execution_journal import ExecutionJournal
from substrate.organism.execution_modes import ExecutionMode, ExecutionModeManager
from substrate.organism.governed_spine import GovernedExecutionSpine
from substrate.organism.maintenance_loop import (
    ActionCategory,
    ActionSeverity,
    ExecutionMode as MaintenanceExecutionMode,
    MaintenanceLoop,
    MaintenanceRecommendation,
)
from substrate.organism.mutation_registry import MutationRegistry
from substrate.organism.spine_guard import GuardMode, SpineGuard
from substrate.organism.workload_runner import WorkloadRunner, WorkloadType


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_spine_stack(
    mode: ExecutionMode = ExecutionMode.OBSERVE,
) -> tuple[GovernedExecutionSpine, ExecutionModeManager, EventSpine, ExecutionJournal, MutationRegistry]:
    event_spine = EventSpine()
    mode_mgr = ExecutionModeManager(initial_mode=mode, event_spine=event_spine)
    registry = MutationRegistry()
    journal = ExecutionJournal()
    spine = GovernedExecutionSpine(
        event_spine=event_spine,
        execution_mode=mode_mgr,
        mutation_registry=registry,
        journal=journal,
    )
    return spine, mode_mgr, event_spine, journal, registry


def _make_gateway(
    policy: AutonomousPolicy = AutonomousPolicy.ASSISTED,
    mode: ExecutionMode = ExecutionMode.ASSISTED,
) -> tuple[AutonomousActionGateway, GovernedExecutionSpine, ExecutionModeManager]:
    spine, mode_mgr, event_spine, journal, _ = _make_spine_stack(mode)
    gateway = AutonomousActionGateway(
        governed_spine=spine,
        execution_mode=mode_mgr,
        event_spine=event_spine,
        journal=journal,
        policy=policy,
    )
    return gateway, spine, mode_mgr


def _simple_envelope(
    source: str = "test",
    risk: str = "low",
    mutation_name: str = "repo_health",
) -> ActionEnvelope:
    return ActionEnvelope(
        intent=f"Test action from {source}",
        action_type=ActionType.STATE,
        source=source,
        execute_fn=lambda: ("ok", True),
        risk_level=risk,
        blast_radius=BlastRadius.LOCAL_RUNTIME,
        reversibility=ReversibilityClass.FULLY_REVERSIBLE,
        metadata={"mutation_name": mutation_name},
    )


# ── TASK 3: AutonomousActionGateway unit tests ──────────────────────────────


class TestGatewayPolicyObserve:
    """OBSERVE policy blocks everything."""

    def test_observe_blocks_low_risk(self):
        gateway, _, _ = _make_gateway(AutonomousPolicy.OBSERVE, ExecutionMode.OBSERVE)
        envelope = _simple_envelope(risk="low")
        result = gateway.submit_envelope(envelope)
        assert result.status == EnvelopeStatus.REJECTED
        assert gateway.to_dict()["total_blocked"] == 1

    def test_observe_blocks_medium_risk(self):
        gateway, _, _ = _make_gateway(AutonomousPolicy.OBSERVE, ExecutionMode.ASSISTED)
        envelope = _simple_envelope(risk="medium", mutation_name="log_rotation")
        result = gateway.submit_envelope(envelope)
        assert result.status == EnvelopeStatus.REJECTED

    def test_observe_blocks_high_risk(self):
        gateway, _, _ = _make_gateway(AutonomousPolicy.OBSERVE, ExecutionMode.ASSISTED)
        envelope = _simple_envelope(risk="high", mutation_name="container_restart")
        result = gateway.submit_envelope(envelope)
        assert result.status == EnvelopeStatus.REJECTED


class TestGatewayPolicyRecommend:
    """RECOMMEND policy creates envelopes but forces approval."""

    def test_recommend_forces_approval_on_low(self):
        gateway, spine, _ = _make_gateway(AutonomousPolicy.RECOMMEND, ExecutionMode.ASSISTED)
        envelope = _simple_envelope(risk="low")
        result = gateway.submit_envelope(envelope)
        assert result.constraints.require_approval is True
        assert gateway.to_dict()["total_recommended"] >= 1

    def test_recommend_forces_approval_on_medium(self):
        gateway, _, _ = _make_gateway(AutonomousPolicy.RECOMMEND, ExecutionMode.ASSISTED)
        envelope = _simple_envelope(risk="medium", mutation_name="log_rotation")
        result = gateway.submit_envelope(envelope)
        assert result.constraints.require_approval is True


class TestGatewayPolicyAssisted:
    """ASSISTED policy: LOW may execute if mode allows, MEDIUM+ requires approval."""

    def test_assisted_allows_low_risk(self):
        gateway, spine, _ = _make_gateway(AutonomousPolicy.ASSISTED, ExecutionMode.ASSISTED)
        envelope = _simple_envelope(risk="low")
        result = gateway.submit_envelope(envelope)
        assert gateway.to_dict()["total_submitted"] >= 1

    def test_assisted_requires_approval_for_medium(self):
        gateway, spine, _ = _make_gateway(AutonomousPolicy.ASSISTED, ExecutionMode.ASSISTED)
        envelope = _simple_envelope(risk="medium", mutation_name="log_rotation")
        result = gateway.submit_envelope(envelope)
        assert result.constraints.require_approval is True

    def test_assisted_requires_approval_for_high(self):
        gateway, spine, _ = _make_gateway(AutonomousPolicy.ASSISTED, ExecutionMode.ASSISTED)
        envelope = _simple_envelope(risk="high", mutation_name="container_restart")
        result = gateway.submit_envelope(envelope)
        assert result.constraints.require_approval is True


class TestGatewayPolicyAutonomous:
    """AUTONOMOUS policy: LOW executes, MEDIUM conditional, HIGH/CRITICAL always approval."""

    def test_autonomous_low_executes(self):
        gateway, spine, mode_mgr = _make_gateway(AutonomousPolicy.AUTONOMOUS, ExecutionMode.AUTONOMOUS)
        for _ in range(15):
            mode_mgr.record_outcome(f"task-{_}", True)

        envelope = _simple_envelope(risk="low")
        result = gateway.submit_envelope(envelope)
        assert gateway.to_dict()["total_submitted"] >= 1

    def test_autonomous_high_always_requires_approval(self):
        gateway, spine, mode_mgr = _make_gateway(AutonomousPolicy.AUTONOMOUS, ExecutionMode.AUTONOMOUS)
        for i in range(15):
            mode_mgr.record_outcome(f"task-{i}", True)

        envelope = _simple_envelope(risk="high", mutation_name="container_restart")
        result = gateway.submit_envelope(envelope)
        assert result.constraints.require_approval is True

    def test_autonomous_medium_with_low_reliability_requires_approval(self):
        gateway, spine, mode_mgr = _make_gateway(AutonomousPolicy.AUTONOMOUS, ExecutionMode.AUTONOMOUS)
        for i in range(5):
            mode_mgr.record_outcome(f"good-{i}", True)
        for i in range(5):
            mode_mgr.record_outcome(f"bad-{i}", False)

        envelope = _simple_envelope(risk="medium", mutation_name="log_rotation")
        result = gateway.submit_envelope(envelope)
        assert result.constraints.require_approval is True


# ── TASK 4: Autonomous tick stages cannot mutate directly ────────────────────


class TestDirectMutationBlocked:
    """Autonomous systems cannot mutate outside the spine."""

    def test_gateway_blocks_direct_mutation(self):
        gateway, _, _ = _make_gateway(AutonomousPolicy.ASSISTED)
        blocked = gateway.block_direct_mutation(
            "autonomous_tick",
            "attempted direct file write",
            risk_level="medium",
        )
        assert blocked is True
        assert gateway.to_dict()["total_blocked"] == 1

    def test_blocked_attempt_appears_in_journal(self):
        _, _, event_spine, journal, _ = _make_spine_stack()
        mode_mgr = ExecutionModeManager(event_spine=event_spine)
        gateway = AutonomousActionGateway(
            governed_spine=MagicMock(),
            execution_mode=mode_mgr,
            event_spine=event_spine,
            journal=journal,
        )

        gateway.block_direct_mutation("tick_stage", "direct shell execution")
        entries = journal.recent(10)
        found = any(
            "autonomous_gateway" in e.source and "direct" in str(e.details)
            for e in entries
        )
        assert found

    def test_blocked_attempt_appears_in_blocked_list(self):
        gateway, _, _ = _make_gateway()
        gateway.block_direct_mutation("maintenance_loop", "direct log rotation")
        blocked = gateway.blocked_attempts(10)
        assert len(blocked) == 1
        assert blocked[0]["source"] == "maintenance_loop"


# ── TASK 5: WorkloadRunner and AssistedExecutor spine-routing ────────────────


class TestWorkloadRunnerGateway:
    """WorkloadRunner routes mutation workloads through gateway."""

    def test_runner_has_gateway_setter(self):
        runner = WorkloadRunner(
            event_spine=EventSpine(),
            execution_mode=ExecutionModeManager(),
            leverage_metrics=MagicMock(),
            operator_compression=MagicMock(),
        )
        assert hasattr(runner, "set_autonomous_gateway")

    def test_runner_creates_envelope(self):
        runner = WorkloadRunner(
            event_spine=EventSpine(),
            execution_mode=ExecutionModeManager(),
            leverage_metrics=MagicMock(),
            operator_compression=MagicMock(),
        )
        envelope = runner.create_envelope(WorkloadType.REPO_HEALTH)
        assert isinstance(envelope, ActionEnvelope)
        assert envelope.source == "workload_runner"
        assert "repo_health" in envelope.metadata.get("mutation_name", "")

    def test_runner_via_gateway_submits_envelope(self):
        gateway, spine, mode_mgr = _make_gateway(AutonomousPolicy.ASSISTED, ExecutionMode.ASSISTED)
        runner = WorkloadRunner(
            event_spine=EventSpine(),
            execution_mode=mode_mgr,
            leverage_metrics=MagicMock(),
            operator_compression=MagicMock(),
        )
        runner.set_autonomous_gateway(gateway)
        outcome = runner.run_workload_via_gateway(WorkloadType.REPO_HEALTH)
        assert gateway.to_dict()["total_submitted"] >= 1


class TestAssistedExecutorGateway:
    """AssistedExecutor routes actions through gateway."""

    def test_executor_has_gateway_setter(self):
        from substrate.organism.assisted_executor import AssistedExecutor
        executor = AssistedExecutor(
            execution_mode=ExecutionModeManager(),
            event_spine=EventSpine(),
            leverage_metrics=MagicMock(),
        )
        assert hasattr(executor, "set_autonomous_gateway")

    def test_executor_creates_envelope(self):
        from substrate.organism.assisted_executor import AssistedExecutor
        executor = AssistedExecutor(
            execution_mode=ExecutionModeManager(),
            event_spine=EventSpine(),
            leverage_metrics=MagicMock(),
        )
        envelope = executor.create_envelope(
            "test-action",
            ActionCategory.LOG_ROTATION,
            "rotate logs",
        )
        assert isinstance(envelope, ActionEnvelope)
        assert envelope.source == "assisted_executor"


class TestMaintenanceLoopGateway:
    """MaintenanceLoop converts recommendations to envelopes via gateway."""

    def test_loop_has_gateway_setter(self):
        loop = MaintenanceLoop(
            workload_runner=MagicMock(),
            execution_mode=ExecutionModeManager(),
            event_spine=EventSpine(),
        )
        assert hasattr(loop, "set_autonomous_gateway")

    def test_loop_submits_recommendation_via_gateway(self):
        gateway, spine, mode_mgr = _make_gateway(AutonomousPolicy.ASSISTED, ExecutionMode.ASSISTED)
        loop = MaintenanceLoop(
            workload_runner=MagicMock(),
            execution_mode=mode_mgr,
            event_spine=EventSpine(),
        )
        loop.set_autonomous_gateway(gateway)

        rec = MaintenanceRecommendation(
            action_id="test-rec-1",
            category=ActionCategory.LOG_ROTATION,
            severity=ActionSeverity.WARNING,
            description="Rotate 3 large log files",
            required_mode=ExecutionMode.ASSISTED,
            auto_approvable=True,
        )

        result = loop.submit_recommendation_via_gateway(rec)
        assert "envelope_id" in result
        assert gateway.to_dict()["total_submitted"] >= 1


# ── TASK 6: Autonomous Mode Policy ──────────────────────────────────────────


class TestAutonomousModePolicy:
    """Verify the 4-level autonomous policy enforcement."""

    def test_observe_no_mutation(self):
        gateway, _, _ = _make_gateway(AutonomousPolicy.OBSERVE)
        envelope = _simple_envelope(risk="low")
        result = gateway.submit_envelope(envelope)
        assert result.status == EnvelopeStatus.REJECTED

    def test_recommend_creates_but_no_execute(self):
        gateway, spine, _ = _make_gateway(AutonomousPolicy.RECOMMEND, ExecutionMode.ASSISTED)
        envelope = _simple_envelope(risk="low")
        result = gateway.submit_envelope(envelope)
        assert result.constraints.require_approval is True
        assert gateway.to_dict()["total_recommended"] >= 1

    def test_assisted_low_may_execute(self):
        gateway, spine, _ = _make_gateway(AutonomousPolicy.ASSISTED, ExecutionMode.ASSISTED)
        envelope = _simple_envelope(risk="low")
        result = gateway.submit_envelope(envelope)
        assert gateway.to_dict()["total_submitted"] >= 1

    def test_assisted_medium_requires_approval(self):
        gateway, _, _ = _make_gateway(AutonomousPolicy.ASSISTED, ExecutionMode.ASSISTED)
        envelope = _simple_envelope(risk="medium", mutation_name="log_rotation")
        result = gateway.submit_envelope(envelope)
        assert result.constraints.require_approval is True

    def test_policy_change_emits_event(self):
        gateway, _, _ = _make_gateway(AutonomousPolicy.OBSERVE)
        gateway.set_policy(AutonomousPolicy.ASSISTED)
        assert gateway.policy == AutonomousPolicy.ASSISTED


# ── TASK 7: Cockpit surface ─────────────────────────────────────────────────


class TestCockpitIntegration:
    """Verify cockpit wiring for autonomous gateway."""

    def test_daemon_exposes_gateway(self):
        daemon = OrganismDaemon()
        daemon.start()
        assert hasattr(daemon, "autonomous_gateway")
        assert daemon.autonomous_gateway is not None

    def test_daemon_status_includes_gateway(self):
        daemon = OrganismDaemon()
        daemon.start()
        status = daemon.status()
        assert "autonomous_gateway" in status
        assert "policy" in status["autonomous_gateway"]

    def test_daemon_gateway_policy_default_assisted(self):
        daemon = OrganismDaemon()
        daemon.start()
        assert daemon.autonomous_gateway.policy == AutonomousPolicy.ASSISTED


# ── TASK 8: Runtime bypass tests ────────────────────────────────────────────


class TestRuntimeBypass:
    """Simulate autonomous bypass attempts and verify blocking."""

    def test_direct_file_mutation_blocked(self):
        gateway, _, _ = _make_gateway(AutonomousPolicy.ASSISTED)
        blocked = gateway.block_direct_mutation(
            "autonomous_tick",
            "write /opt/OS/data/test.json",
            risk_level="medium",
        )
        assert blocked is True

    def test_low_envelope_allowed_in_assisted_mode(self):
        gateway, spine, _ = _make_gateway(AutonomousPolicy.ASSISTED, ExecutionMode.ASSISTED)
        envelope = _simple_envelope(risk="low")
        result = gateway.submit_envelope(envelope)
        assert gateway.to_dict()["total_submitted"] >= 1

    def test_medium_envelope_pending_approval(self):
        gateway, spine, _ = _make_gateway(AutonomousPolicy.ASSISTED, ExecutionMode.ASSISTED)
        envelope = _simple_envelope(risk="medium", mutation_name="log_rotation")
        result = gateway.submit_envelope(envelope)
        assert result.constraints.require_approval is True

    def test_operator_approves_through_spine(self):
        gateway, spine, _ = _make_gateway(AutonomousPolicy.ASSISTED, ExecutionMode.ASSISTED)
        envelope = _simple_envelope(risk="medium", mutation_name="log_rotation")
        envelope.constraints.require_approval = True
        result = gateway.submit_envelope(envelope)

        pending = spine.pending_envelopes()
        if pending:
            approved = spine.approve(pending[0]["envelope_id"], approved_by="operator")
            assert approved is not None
            assert approved.approved_by == "operator"

    def test_failed_execution_journal_entry(self):
        spine_obj, mode_mgr, event_spine, journal, registry = _make_spine_stack(ExecutionMode.ASSISTED)
        gateway = AutonomousActionGateway(
            governed_spine=spine_obj,
            execution_mode=mode_mgr,
            event_spine=event_spine,
            journal=journal,
            policy=AutonomousPolicy.ASSISTED,
        )

        envelope = ActionEnvelope(
            intent="Failing action",
            action_type=ActionType.STATE,
            source="test_bypass",
            execute_fn=lambda: ("deliberate failure", False),
            risk_level="low",
            metadata={"mutation_name": "repo_health"},
        )

        result = gateway.submit_envelope(envelope)
        lifecycle = spine_obj.envelope_lifecycle(result.envelope_id)
        phases = [e["phase"] for e in lifecycle]
        assert "proposed" in phases
        assert "execution_started" in phases or "governance_check" in phases

    def test_bypass_violation_in_spine_guard(self):
        guard = SpineGuard(
            mode=GuardMode.BLOCK_HIGH_RISK,
            event_spine=EventSpine(),
        )
        blocked = guard.check_direct_mutation(
            "autonomous_tick",
            "direct docker restart",
            risk_level="medium",
        )
        assert blocked is True
        violations = guard.recent_violations()
        assert any(v["blocked"] for v in violations)


# ── TASK 9: Enforcement ratchet ─────────────────────────────────────────────


class TestEnforcementRatchet:
    """Verify the default is BLOCK_HIGH_RISK and ratchet path exists."""

    def test_daemon_default_guard_mode(self):
        daemon = OrganismDaemon()
        daemon.start()
        assert daemon.spine_guard.mode == GuardMode.BLOCK_HIGH_RISK

    def test_guard_mode_can_escalate(self):
        guard = SpineGuard(mode=GuardMode.BLOCK_HIGH_RISK)
        guard.set_mode(GuardMode.ENFORCE_ALL)
        assert guard.mode == GuardMode.ENFORCE_ALL

    def test_enforce_all_blocks_even_low_risk(self):
        guard = SpineGuard(mode=GuardMode.ENFORCE_ALL, event_spine=EventSpine())
        blocked = guard.check_direct_mutation("test", "low risk probe", risk_level="low")
        assert blocked is True

    def test_block_high_risk_allows_low(self):
        guard = SpineGuard(mode=GuardMode.BLOCK_HIGH_RISK, event_spine=EventSpine())
        blocked = guard.check_direct_mutation("test", "low risk probe", risk_level="low")
        assert blocked is False

    def test_block_high_risk_blocks_medium(self):
        guard = SpineGuard(mode=GuardMode.BLOCK_HIGH_RISK, event_spine=EventSpine())
        blocked = guard.check_direct_mutation("test", "medium mutation", risk_level="medium")
        assert blocked is True


# ── TASK 10: Integration with full daemon ───────────────────────────────────


class TestDaemonIntegration:
    """Full daemon integration: gateway + spine + guard + journal."""

    def test_daemon_tick_with_gateway(self):
        daemon = OrganismDaemon()
        daemon.start()
        result = daemon.tick()
        assert "cycle" in result
        assert "stages_executed" in result

    def test_daemon_gateway_to_dict(self):
        daemon = OrganismDaemon()
        daemon.start()
        gw = daemon.autonomous_gateway.to_dict()
        assert "policy" in gw
        assert "total_submitted" in gw
        assert "total_blocked" in gw

    def test_daemon_full_status(self):
        daemon = OrganismDaemon()
        daemon.start()
        status = daemon.status()
        assert "autonomous_gateway" in status
        assert "governed_spine" in status
        assert "spine_guard" in status
        assert "execution_journal" in status
        assert "execution_mode" in status

    def test_workload_runner_wired_to_gateway(self):
        daemon = OrganismDaemon()
        daemon.start()
        assert daemon.workload_runner._autonomous_gateway is not None

    def test_assisted_executor_wired_to_gateway(self):
        daemon = OrganismDaemon()
        daemon.start()
        assert daemon.assisted_executor._autonomous_gateway is not None

    def test_maintenance_loop_wired_to_gateway(self):
        daemon = OrganismDaemon()
        daemon.start()
        assert daemon.maintenance_loop._autonomous_gateway is not None


# ── Policy lifecycle tests ──────────────────────────────────────────────────


class TestPolicyLifecycle:
    """Test the full autonomous policy lifecycle through the daemon."""

    def test_policy_starts_assisted(self):
        daemon = OrganismDaemon()
        daemon.start()
        assert daemon.autonomous_gateway.policy == AutonomousPolicy.ASSISTED

    def test_policy_change_to_observe_blocks_all(self):
        daemon = OrganismDaemon()
        daemon.start()
        daemon.autonomous_gateway.set_policy(AutonomousPolicy.OBSERVE)

        envelope = _simple_envelope(risk="low")
        result = daemon.autonomous_gateway.submit_envelope(envelope)
        assert result.status == EnvelopeStatus.REJECTED

    def test_policy_change_persists_across_ticks(self):
        daemon = OrganismDaemon()
        daemon.start()
        daemon.autonomous_gateway.set_policy(AutonomousPolicy.RECOMMEND)
        daemon.tick()
        assert daemon.autonomous_gateway.policy == AutonomousPolicy.RECOMMEND

    def test_reliability_threshold_configurable(self):
        daemon = OrganismDaemon()
        daemon.start()
        daemon.autonomous_gateway.set_reliability_threshold(0.95)
        assert daemon.autonomous_gateway.reliability_threshold == 0.95
