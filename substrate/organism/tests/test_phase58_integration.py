"""Phase 5.8 integration tests — full Operational Leverage Engine.

Tests that the daemon correctly wires all new engines:
  - LeverageMetrics
  - BottleneckEngine
  - ObjectivePhysics
  - OperatorCompression
  - ExecutionModeManager
  - WorkloadProbes

And that they produce real data through the tick cycle.
"""
from __future__ import annotations

import sys
import time

import os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from substrate.organism.daemon import OrganismDaemon
from substrate.organism.event_spine import EventDomain
from substrate.organism.leverage_metrics import TaskRecord
from substrate.organism.operator_compression import InterventionType, OperatorAction
from substrate.organism.objective_physics import ObjectiveState


def _make_daemon() -> OrganismDaemon:
    return OrganismDaemon(store_dir="/tmp/test_phase58_organism")


def test_daemon_has_new_engines():
    d = _make_daemon()
    assert d.leverage_metrics is not None
    assert d.bottleneck_engine is not None
    assert d.objective_physics is not None
    assert d.operator_compression is not None
    assert d.execution_mode_manager is not None
    assert d.workload_probes is not None


def test_daemon_tick_includes_new_stages():
    d = _make_daemon()
    stages = d.autonomous_tick.stages
    assert "leverage_measurement" in stages
    assert "bottleneck_detection" in stages
    assert "objective_physics" in stages
    assert "operator_compression" in stages
    assert "workload_probes" in stages


def test_daemon_tick_runs_all_stages():
    d = _make_daemon()
    result = d.tick()
    assert result["stages_executed"] >= 5
    assert result["elapsed_ms"] >= 0


def test_daemon_status_includes_new_engines():
    d = _make_daemon()
    d.tick()
    status = d.status()
    assert "leverage" in status
    assert "bottlenecks" in status
    assert "objective_physics" in status
    assert "operator_compression" in status
    assert "execution_mode" in status
    assert "workload_probes" in status


def test_leverage_metrics_through_daemon():
    d = _make_daemon()
    now = time.time()
    d.leverage_metrics.record_task(TaskRecord(
        task_id="daemon-t1",
        started_at=now - 10,
        completed_at=now,
        autonomous=True,
        success=True,
        estimated_manual_seconds=120,
    ))
    d.tick()
    summary = d.leverage_metrics.summary()
    assert summary["totals"]["tasks"] >= 1
    assert summary["totals"]["autonomous_resolutions"] >= 1
    assert summary["dimensions"]["time_compression"] > 0


def test_bottleneck_detection_through_daemon():
    d = _make_daemon()
    now = time.time()
    for i in range(5):
        d.leverage_metrics.record_task(TaskRecord(
            task_id=f"fail-{i}",
            started_at=now - 5,
            completed_at=now,
            success=False,
            retries=3,
        ))
    d.tick()
    active = d.bottleneck_engine.active
    assert len(active) > 0


def test_objective_physics_through_daemon():
    d = _make_daemon()
    d.objective_physics.register_objective("build-engine", name="Build Leverage Engine")
    d.objective_physics.register_objective("test-engine", name="Test Engine", depends_on=["build-engine"])
    d.objective_physics.register_objective("deploy", name="Deploy", depends_on=["test-engine"])
    d.tick()
    physics = d.objective_physics.to_dict()
    assert physics["total_objectives"] == 3
    assert physics["blocking_nodes"] == 2


def test_operator_compression_through_daemon():
    d = _make_daemon()
    for i in range(4):
        d.operator_compression.record_intervention(OperatorAction(
            action_id=f"restart-{i}",
            intervention_type=InterventionType.RESTART,
            description="Restarted os-discord",
            context="docker_restart",
            duration_seconds=30,
        ))
    d.tick()
    candidates = d.operator_compression.automation_candidates()
    assert len(candidates) == 1
    assert candidates[0].suggested_automation != ""


def test_execution_mode_through_daemon():
    d = _make_daemon()
    mode = d.execution_mode_manager
    assert mode.current_mode.value == "observe"
    mode.promote(d.execution_mode_manager.current_mode.__class__("recommend"))
    assert mode.current_mode.value == "recommend"


def test_workload_probes_through_daemon():
    d = _make_daemon()
    d.tick()
    cached = d.workload_probes.cached
    assert "disk" in cached
    assert "memory" in cached


def test_event_spine_receives_leverage_events():
    d = _make_daemon()
    events: list[dict] = []
    d.event_spine.subscribe(
        "test_leverage",
        lambda e: events.append(e.to_dict()),
        domains={EventDomain.LEVERAGE},
    )
    d.leverage_metrics.record_task(TaskRecord(
        task_id="ev-test",
        started_at=time.time() - 5,
        completed_at=time.time(),
        success=True,
    ))
    d.tick()
    leverage_events = [e for e in events if e["event_type"] == "leverage_measured"]
    assert len(leverage_events) >= 1


def test_event_spine_receives_bottleneck_events():
    d = _make_daemon()
    events: list[dict] = []
    d.event_spine.subscribe(
        "test_bottleneck",
        lambda e: events.append(e.to_dict()),
        domains={EventDomain.OBSERVABILITY},
    )
    now = time.time()
    for i in range(5):
        d.leverage_metrics.record_task(TaskRecord(
            task_id=f"bn-{i}",
            started_at=now - 5,
            completed_at=now,
            success=False,
        ))
    d.tick()
    bn_events = [e for e in events if e["event_type"] == "bottleneck_detected"]
    assert len(bn_events) >= 1


def test_full_cycle_no_failures():
    """Ensure a complete 3-cycle run has zero stage failures."""
    d = _make_daemon()
    for _ in range(3):
        result = d.tick()
        assert result["stages_failed"] == 0, f"Stage failures: {result.get('stage_details')}"


if __name__ == "__main__":
    test_daemon_has_new_engines()
    test_daemon_tick_includes_new_stages()
    test_daemon_tick_runs_all_stages()
    test_daemon_status_includes_new_engines()
    test_leverage_metrics_through_daemon()
    test_bottleneck_detection_through_daemon()
    test_objective_physics_through_daemon()
    test_operator_compression_through_daemon()
    test_execution_mode_through_daemon()
    test_workload_probes_through_daemon()
    test_event_spine_receives_leverage_events()
    test_event_spine_receives_bottleneck_events()
    test_full_cycle_no_failures()
    print("ALL PHASE 5.8 INTEGRATION TESTS PASSED")
