"""Integration tests for Phase 5.9 — end-to-end workload execution."""

from __future__ import annotations

import sys
sys.path.insert(0, "/opt/OS/.claude/worktrees/anti-divergence-gate")

from substrate.organism.daemon import OrganismDaemon
from substrate.organism.execution_modes import ExecutionMode, TransitionReason
from substrate.organism.workload_runner import WorkloadType


def test_daemon_has_phase59_subsystems():
    daemon = OrganismDaemon()
    assert daemon.workload_runner is not None
    assert daemon.automation_pipeline is not None
    assert daemon.maintenance_loop is not None
    assert daemon.assisted_executor is not None


def test_tick_includes_maintenance_and_automation():
    daemon = OrganismDaemon()
    stages = list(daemon.autonomous_tick.stages.keys())
    assert "maintenance_cycle" in stages
    assert "automation_scan" in stages


def test_daemon_status_includes_phase59():
    daemon = OrganismDaemon()
    daemon.start()
    status = daemon.status()
    assert "workload_runner" in status
    assert "automation_pipeline" in status
    assert "maintenance_loop" in status
    assert "assisted_executor" in status
    daemon.stop()


def test_full_tick_cycle():
    daemon = OrganismDaemon()
    daemon.start()
    report = daemon.tick()
    assert report["cycle"] == 1
    assert report["stages_executed"] > 0
    daemon.stop()


def test_workload_runner_through_daemon():
    daemon = OrganismDaemon()
    daemon.start()
    outcome = daemon.workload_runner.run_workload(WorkloadType.REPO_HEALTH)
    assert outcome.success
    assert outcome.findings
    daemon.stop()


def test_run_all_observe_through_daemon():
    daemon = OrganismDaemon()
    daemon.start()
    outcomes = daemon.workload_runner.run_all_observe()
    assert len(outcomes) >= 5
    successes = sum(1 for o in outcomes if o.success)
    assert successes >= 3
    daemon.stop()


def test_assisted_blocked_in_observe():
    daemon = OrganismDaemon()
    daemon.start()
    from substrate.organism.maintenance_loop import ActionCategory
    result = daemon.assisted_executor.execute_action(
        action_id="test-1",
        category=ActionCategory.RUNTIME_REFRESH,
        description="test",
    )
    assert result.result.value == "blocked"
    daemon.stop()


def test_assisted_works_after_promotion():
    daemon = OrganismDaemon()
    daemon.start()
    daemon.execution_mode_manager.promote(
        ExecutionMode.ASSISTED,
        reason=TransitionReason.OPERATOR_PROMOTION,
        justification="integration test",
    )
    from substrate.organism.maintenance_loop import ActionCategory
    result = daemon.assisted_executor.execute_action(
        action_id="test-1",
        category=ActionCategory.RUNTIME_REFRESH,
        description="test",
    )
    assert result.result.value != "blocked"
    daemon.stop()


def test_leverage_records_from_workloads():
    daemon = OrganismDaemon()
    daemon.start()
    daemon.workload_runner.run_workload(WorkloadType.REPO_HEALTH)
    daemon.workload_runner.run_workload(WorkloadType.DISK_PRESSURE)
    summary = daemon.leverage_metrics.summary()
    assert summary["totals"]["tasks"] >= 2
    daemon.stop()


def test_events_emitted_during_workloads():
    daemon = OrganismDaemon()
    daemon.start()
    daemon.workload_runner.run_workload(WorkloadType.REPO_HEALTH)
    events = daemon.event_spine.recent(limit=100)
    event_types = [e.event_type for e in events]
    assert "workload_started" in event_types
    assert "workload_completed" in event_types
    daemon.stop()
