"""Tests for Phase 96.8BY — Operational Substrate Scaling Coordination.

Tests:
  contracts, lifecycle, pressure, backpressure, concurrency,
  priority, degraded-mode, observability, replay, boundary policies,
  continuity bridges, coordinator integration,
  and 16 constraint verifications.

UMH substrate subsystem. Phase 96.8BY.
"""

from __future__ import annotations

import shutil
import sys
import tempfile

import pytest

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from core.scaling.operational_scaling_contracts_v1 import (
    AdaptiveRegulationState,
    CapacityAllocationDecision,
    ConcurrencyWindow,
    DegradedModeState,
    DegradedReason,
    ExecutionPressureState,
    ExecutionThrottleState,
    OperationalHealthState,
    OperationalPriorityState,
    PriorityClass,
    QueuePressureState,
    ResourceBudget,
    ScalingCoordinationReceipt,
    ScalingEventType,
    ScalingLifecycleState,
    ScalingReplayState,
    _content_hash,
)
from core.scaling.scaling_lifecycle_engine_v1 import (
    ScalingLifecycleEngine,
    VALID_SCALING_TRANSITIONS,
)
from core.scaling.execution_pressure_engine_v1 import (
    ExecutionPressureEngine,
    PRESSURE_THRESHOLDS,
)
from core.scaling.operational_backpressure_engine_v1 import (
    OperationalBackpressureEngine,
    THROTTLE_DELAY_MAP,
    PRIORITY_PROTECTION,
)
from core.scaling.concurrency_regulation_engine_v1 import (
    ConcurrencyRegulationEngine,
    DEFAULT_CONCURRENCY_LIMITS,
)
from core.scaling.operational_priority_engine_v1 import (
    OperationalPriorityEngine,
    PRIORITY_ORDER,
)
from core.scaling.degraded_mode_coordination_engine_v1 import (
    DegradedModeCoordinationEngine,
    MAX_RECOVERY_ATTEMPTS,
)
from core.scaling.scaling_observability_pipeline_v1 import (
    ScalingObservabilityPipeline,
    EVENT_FILE_MAP,
)
from core.scaling.scaling_replay_validator_v1 import (
    ScalingReplayValidator,
    REPLAY_CHECKS,
)
from core.scaling.scaling_boundary_policies_v1 import (
    DEFAULT_SCALING_BOUNDARIES,
    FORBIDDEN_SCALING_ACTIONS,
    ScalingBoundaryEnforcer,
)
from core.scaling.scaling_continuity_bridges_v1 import (
    ContinuityScalingBridge,
    EnvironmentsScalingBridge,
    ObservabilityScalingBridge,
    OperationsScalingBridge,
    ReplayScalingBridge,
    SessionsScalingBridge,
    WorkflowsScalingBridge,
)
from core.scaling.canonical_operational_scaling_coordinator_v1 import (
    CanonicalOperationalScalingCoordinator,
)


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d)


# ── Contract Tests ──────────────────────────────────────


class TestScalingContracts:
    def test_enum_lifecycle_state(self):
        assert len(ScalingLifecycleState) == 9

    def test_enum_event_type(self):
        assert len(ScalingEventType) == 10

    def test_enum_priority_class(self):
        assert len(PriorityClass) == 5

    def test_enum_degraded_reason(self):
        assert len(DegradedReason) == 5

    def test_resource_budget(self):
        b = ResourceBudget()
        d = b.to_dict()
        assert d["budget_id"].startswith("rbud-")
        assert d["max_concurrent"] == 5

    def test_execution_pressure_state(self):
        s = ExecutionPressureState(active_traversals=3, pressure_score=0.6)
        d = s.to_dict()
        assert d["active_traversals"] == 3
        assert d["pressure_score"] == 0.6

    def test_queue_pressure_state(self):
        q = QueuePressureState(depth=10, throttled=True)
        d = q.to_dict()
        assert d["throttled"] is True

    def test_operational_health_state(self):
        h = OperationalHealthState()
        assert h.to_dict()["overall_healthy"] is True

    def test_scaling_receipt(self):
        r = ScalingCoordinationReceipt(operation="evaluate")
        assert r.to_dict()["receipt_id"].startswith("srcpt-")

    def test_concurrency_window(self):
        w = ConcurrencyWindow(max_concurrent=5, current_active=3)
        d = w.to_dict()
        assert d["current_active"] == 3

    def test_execution_throttle(self):
        t = ExecutionThrottleState(active=True, delay_ms=500)
        d = t.to_dict()
        assert d["active"] is True

    def test_priority_state(self):
        p = OperationalPriorityState(item_id="x", set_by="operator")
        assert p.to_dict()["set_by"] == "operator"

    def test_adaptive_regulation(self):
        a = AdaptiveRegulationState(throttle_active=True, pressure_score=0.8)
        assert a.to_dict()["pressure_score"] == 0.8

    def test_degraded_mode_state(self):
        d = DegradedModeState(active=True)
        assert d.to_dict()["active"] is True

    def test_scaling_replay_state(self):
        r = ScalingReplayState()
        assert r.to_dict()["replay_id"].startswith("srply-")

    def test_capacity_allocation(self):
        c = CapacityAllocationDecision(item_id="x", allocated=True)
        assert c.to_dict()["allocated"] is True

    def test_serialization_deterministic(self):
        b = ResourceBudget()
        h1 = _content_hash(b.to_dict())
        h2 = _content_hash(b.to_dict())
        assert h1 == h2


# ── Lifecycle Tests ──────────────────────────────────────


class TestScalingLifecycleEngine:
    def test_initial_state(self, tmp_dir):
        eng = ScalingLifecycleEngine(state_dir=tmp_dir)
        assert eng.current_state == "stable"

    def test_valid_transition(self, tmp_dir):
        eng = ScalingLifecycleEngine(state_dir=tmp_dir)
        assert eng.transition(ScalingLifecycleState.ELEVATED)
        assert eng.current_state == "elevated"

    def test_invalid_transition(self, tmp_dir):
        eng = ScalingLifecycleEngine(state_dir=tmp_dir)
        assert not eng.transition(ScalingLifecycleState.DEGRADED)

    def test_nine_states_exist(self):
        assert len(ScalingLifecycleState) == 9
        for state in ScalingLifecycleState:
            assert state.value in VALID_SCALING_TRANSITIONS

    def test_pressure_path(self, tmp_dir):
        eng = ScalingLifecycleEngine(state_dir=tmp_dir)
        eng.transition(ScalingLifecycleState.ELEVATED)
        eng.transition(ScalingLifecycleState.PRESSURED)
        eng.transition(ScalingLifecycleState.THROTTLED)
        assert eng.current_state == "throttled"
        assert eng.is_under_pressure()

    def test_degraded_recovery_path(self, tmp_dir):
        eng = ScalingLifecycleEngine(state_dir=tmp_dir)
        eng.transition(ScalingLifecycleState.ELEVATED)
        eng.transition(ScalingLifecycleState.PRESSURED)
        eng.transition(ScalingLifecycleState.DEGRADED)
        eng.transition(ScalingLifecycleState.RECOVERING)
        eng.transition(ScalingLifecycleState.STABILIZED)
        eng.transition(ScalingLifecycleState.STABLE)
        assert eng.current_state == "stable"

    def test_terminal_state(self, tmp_dir):
        eng = ScalingLifecycleEngine(state_dir=tmp_dir)
        eng.transition(ScalingLifecycleState.SUSPENDED)
        eng.transition(ScalingLifecycleState.ARCHIVED)
        assert eng.is_terminal()

    def test_lineage_persisted(self, tmp_dir):
        from pathlib import Path
        eng = ScalingLifecycleEngine(state_dir=tmp_dir)
        eng.transition(ScalingLifecycleState.ELEVATED)
        assert (Path(tmp_dir) / "scaling_lifecycle_lineage.jsonl").exists()


# ── Pressure Tests ──────────────────────────────────────


class TestExecutionPressureEngine:
    def test_initial_pressure_zero(self, tmp_dir):
        eng = ExecutionPressureEngine(state_dir=tmp_dir)
        state = eng.compute_pressure()
        assert state.pressure_score == 0.0

    def test_traversal_pressure(self, tmp_dir):
        eng = ExecutionPressureEngine(state_dir=tmp_dir, max_concurrent=5)
        for _ in range(4):
            eng.record_traversal_start()
        state = eng.compute_pressure()
        assert state.pressure_score > 0.2
        assert state.active_traversals == 4

    def test_queue_pressure(self, tmp_dir):
        eng = ExecutionPressureEngine(state_dir=tmp_dir, max_queue=10)
        eng.record_queue_change(8)
        state = eng.compute_pressure()
        assert state.queue_depth == 8
        assert state.pressure_score > 0.1

    def test_pressure_levels(self, tmp_dir):
        eng = ExecutionPressureEngine(state_dir=tmp_dir)
        assert eng.get_pressure_level(0.1) == "nominal"
        assert eng.get_pressure_level(0.35) == "low"
        assert eng.get_pressure_level(0.55) == "elevated"
        assert eng.get_pressure_level(0.75) == "high"
        assert eng.get_pressure_level(0.95) == "critical"

    def test_thresholds_defined(self):
        assert len(PRESSURE_THRESHOLDS) == 4

    def test_latency_tracking(self, tmp_dir):
        eng = ExecutionPressureEngine(state_dir=tmp_dir)
        eng.record_traversal_start()
        eng.record_traversal_end(100.0)
        eng.record_traversal_start()
        eng.record_traversal_end(200.0)
        state = eng.compute_pressure()
        assert state.avg_latency_ms == 150.0

    def test_pressure_hash_stable(self, tmp_dir):
        eng = ExecutionPressureEngine(state_dir=tmp_dir)
        eng.compute_pressure()
        h1 = eng.get_pressure_hash()
        h2 = eng.get_pressure_hash()
        assert h1 == h2

    def test_snapshot_persisted(self, tmp_dir):
        from pathlib import Path
        eng = ExecutionPressureEngine(state_dir=tmp_dir)
        eng.compute_pressure()
        assert (Path(tmp_dir) / "execution_pressure_snapshots.jsonl").exists()


# ── Backpressure Tests ──────────────────────────────────────


class TestOperationalBackpressureEngine:
    def test_nominal_no_throttle(self, tmp_dir):
        eng = OperationalBackpressureEngine(state_dir=tmp_dir)
        t = eng.apply_throttle("nominal")
        assert not t.active

    def test_elevated_throttle(self, tmp_dir):
        eng = OperationalBackpressureEngine(state_dir=tmp_dir)
        t = eng.apply_throttle("elevated")
        assert t.active
        assert t.delay_ms == 200

    def test_critical_throttle(self, tmp_dir):
        eng = OperationalBackpressureEngine(state_dir=tmp_dir)
        t = eng.apply_throttle("critical")
        assert t.active
        assert t.delay_ms == 1000

    def test_release_throttle(self, tmp_dir):
        eng = OperationalBackpressureEngine(state_dir=tmp_dir)
        eng.apply_throttle("high")
        t = eng.release_throttle()
        assert not t.active
        assert t.delay_ms == 0

    def test_critical_protected(self, tmp_dir):
        eng = OperationalBackpressureEngine(state_dir=tmp_dir)
        assert eng.should_protect("critical")
        assert not eng.should_protect("standard")
        assert not eng.should_protect("deferred")

    def test_queue_delay(self, tmp_dir):
        eng = OperationalBackpressureEngine(state_dir=tmp_dir)
        assert eng.compute_queue_delay(25, 50) == 5000
        assert eng.compute_queue_delay(0, 50) == 0

    def test_continuation_pace(self, tmp_dir):
        eng = OperationalBackpressureEngine(state_dir=tmp_dir)
        assert eng.compute_continuation_pace(0) == 0
        assert eng.compute_continuation_pace(1) == 500
        assert eng.compute_continuation_pace(10) == 3000

    def test_throttle_delay_map(self):
        assert len(THROTTLE_DELAY_MAP) == 5


# ── Concurrency Tests ──────────────────────────────────────


class TestConcurrencyRegulationEngine:
    def test_request_slot(self, tmp_dir):
        eng = ConcurrencyRegulationEngine(state_dir=tmp_dir)
        d = eng.request_slot(item_id="t1")
        assert d.allocated

    def test_global_limit(self, tmp_dir):
        eng = ConcurrencyRegulationEngine(
            state_dir=tmp_dir, overrides={"global": 2},
        )
        eng.request_slot(item_id="t1")
        eng.request_slot(item_id="t2")
        d = eng.request_slot(item_id="t3")
        assert not d.allocated
        assert d.reason == "global_limit_reached"

    def test_environment_limit(self, tmp_dir):
        eng = ConcurrencyRegulationEngine(
            state_dir=tmp_dir, overrides={"per_environment": 1},
        )
        eng.request_slot(item_id="t1", environment_id="env-1")
        d = eng.request_slot(item_id="t2", environment_id="env-1")
        assert not d.allocated

    def test_release_slot(self, tmp_dir):
        eng = ConcurrencyRegulationEngine(
            state_dir=tmp_dir, overrides={"global": 1},
        )
        eng.request_slot(item_id="t1")
        eng.release_slot()
        d = eng.request_slot(item_id="t2")
        assert d.allocated

    def test_window(self, tmp_dir):
        eng = ConcurrencyRegulationEngine(state_dir=tmp_dir)
        eng.request_slot(item_id="t1", environment_id="env-1")
        w = eng.get_window()
        assert w.current_active == 1

    def test_override_capping(self):
        eng = ConcurrencyRegulationEngine(overrides={"global": 100})
        assert eng._limits["global"] == 5

    def test_concurrency_hash_stable(self, tmp_dir):
        eng = ConcurrencyRegulationEngine(state_dir=tmp_dir)
        eng.request_slot(item_id="t1")
        h1 = eng.get_concurrency_hash()
        h2 = eng.get_concurrency_hash()
        assert h1 == h2

    def test_default_limits(self):
        assert len(DEFAULT_CONCURRENCY_LIMITS) == 5


# ── Priority Tests ──────────────────────────────────────


class TestOperationalPriorityEngine:
    def test_set_priority(self, tmp_dir):
        eng = OperationalPriorityEngine(state_dir=tmp_dir)
        s = eng.set_priority("t1", "critical", "operator")
        assert s.priority_class == "critical"
        assert s.set_by == "operator"

    def test_arbitrate_order(self, tmp_dir):
        eng = OperationalPriorityEngine(state_dir=tmp_dir)
        eng.set_priority("t1", "deferred")
        eng.set_priority("t2", "critical")
        eng.set_priority("t3", "standard")
        order = eng.arbitrate(["t1", "t2", "t3"])
        assert order == ["t2", "t3", "t1"]

    def test_suspended_excluded(self, tmp_dir):
        eng = OperationalPriorityEngine(state_dir=tmp_dir)
        eng.set_priority("t1", "suspended")
        eng.set_priority("t2", "standard")
        order = eng.arbitrate(["t1", "t2"])
        assert "t1" not in order
        assert "t2" in order

    def test_override(self, tmp_dir):
        eng = OperationalPriorityEngine(state_dir=tmp_dir)
        eng.set_priority("t1", "standard", "operator")
        assert eng.override_priority("t1", "critical", "operator")
        s = eng.get_priority("t1")
        assert s.priority_class == "critical"

    def test_priority_order(self):
        assert len(PRIORITY_ORDER) == 5
        assert PRIORITY_ORDER[0] == "critical"
        assert PRIORITY_ORDER[-1] == "suspended"

    def test_priority_hash_stable(self, tmp_dir):
        eng = OperationalPriorityEngine(state_dir=tmp_dir)
        eng.set_priority("t1", "high")
        eng.arbitrate(["t1"])
        h1 = eng.get_priority_hash()
        h2 = eng.get_priority_hash()
        assert h1 == h2


# ── Degraded-Mode Tests ──────────────────────────────────────


class TestDegradedModeCoordinationEngine:
    def test_enter_degraded(self, tmp_dir):
        eng = DegradedModeCoordinationEngine(state_dir=tmp_dir)
        mode = eng.enter_degraded("resource_exhaustion", ["env-1"])
        assert mode.active
        assert mode.reduced_concurrency > 0
        assert mode.reduced_concurrency < 5

    def test_recovery(self, tmp_dir):
        eng = DegradedModeCoordinationEngine(state_dir=tmp_dir)
        eng.enter_degraded()
        assert eng.attempt_recovery()
        mode = eng.complete_recovery()
        assert not mode.active

    def test_max_recovery_attempts(self, tmp_dir):
        eng = DegradedModeCoordinationEngine(state_dir=tmp_dir)
        eng.enter_degraded()
        for _ in range(MAX_RECOVERY_ATTEMPTS):
            eng.attempt_recovery()
        assert not eng.attempt_recovery()

    def test_not_degraded_initially(self, tmp_dir):
        eng = DegradedModeCoordinationEngine(state_dir=tmp_dir)
        assert not eng.is_degraded()

    def test_reduced_concurrency(self, tmp_dir):
        eng = DegradedModeCoordinationEngine(state_dir=tmp_dir, base_concurrency=10)
        assert eng.get_reduced_concurrency() == 10
        eng.enter_degraded()
        assert eng.get_reduced_concurrency() == 5

    def test_degraded_hash_stable(self, tmp_dir):
        eng = DegradedModeCoordinationEngine(state_dir=tmp_dir)
        eng.enter_degraded()
        h1 = eng.get_degraded_hash()
        h2 = eng.get_degraded_hash()
        assert h1 == h2


# ── Observability Tests ──────────────────────────────────────


class TestScalingObservabilityPipeline:
    def test_all_10_event_types(self):
        assert len(ScalingEventType) == 10

    def test_event_file_map_complete(self):
        for et in ScalingEventType:
            assert et.value in EVENT_FILE_MAP

    def test_convenience_methods(self, tmp_dir):
        obs = ScalingObservabilityPipeline(state_dir=tmp_dir)
        obs.emit_pressure_increase(score=0.8)
        obs.emit_pressure_relief()
        obs.emit_queue_throttle()
        obs.emit_execution_delayed()
        obs.emit_degraded_mode_entered()
        obs.emit_degraded_mode_recovered()
        obs.emit_concurrency_limited()
        obs.emit_resource_budget_exceeded()
        obs.emit_priority_arbitrated()
        obs.emit_scaling_boundary_denied()
        assert obs.get_stats()["total_events"] == 10

    def test_read_back(self, tmp_dir):
        obs = ScalingObservabilityPipeline(state_dir=tmp_dir)
        obs.emit_pressure_increase(score=0.5)
        events = obs.read_events(ScalingEventType.PRESSURE_INCREASE)
        assert len(events) == 1


# ── Replay Tests ──────────────────────────────────────


class TestScalingReplayValidator:
    def test_five_checks(self):
        assert len(REPLAY_CHECKS) == 5

    def test_validate_trace(self, tmp_dir):
        v = ScalingReplayValidator(state_dir=tmp_dir)
        result = v.validate_trace({
            "pressure_regulation": {"score": 0.5},
            "throttling_decisions": {"delay": 200},
            "concurrency_arbitration": {"granted": 3},
            "degraded_mode_transitions": {"entries": 1},
            "priority_arbitration": {"order": ["t1"]},
        })
        assert result["all_passed"]

    def test_missing_check_fails(self, tmp_dir):
        v = ScalingReplayValidator(state_dir=tmp_dir)
        result = v.validate_trace({"pressure_regulation": {"score": 0.5}})
        assert not result["all_passed"]

    def test_pressure_determinism(self, tmp_dir):
        v = ScalingReplayValidator(state_dir=tmp_dir)
        data = [{"score": 0.5}]
        assert v.validate_pressure_determinism(data, data)["passed"]

    def test_arbitration_determinism(self, tmp_dir):
        v = ScalingReplayValidator(state_dir=tmp_dir)
        data = [{"order": ["t1", "t2"]}]
        assert v.validate_arbitration_determinism(data, data)["passed"]

    def test_degraded_determinism(self, tmp_dir):
        v = ScalingReplayValidator(state_dir=tmp_dir)
        data = [{"entries": 1}]
        assert v.validate_degraded_determinism(data, data)["passed"]

    def test_proof_persisted(self, tmp_dir):
        from pathlib import Path
        v = ScalingReplayValidator(state_dir=tmp_dir)
        v.validate_trace({"pressure_regulation": {"x": 1}})
        assert (Path(tmp_dir) / "scaling_replay_proofs.jsonl").exists()


# ── Boundary Policy Tests ──────────────────────────────────────


class TestScalingBoundaryPolicies:
    def test_default_limits(self):
        assert len(DEFAULT_SCALING_BOUNDARIES) == 7

    def test_forbidden_actions(self):
        assert len(FORBIDDEN_SCALING_ACTIONS) == 10

    def test_passing_check(self):
        enf = ScalingBoundaryEnforcer()
        assert enf.check_concurrent(2)["passed"]

    def test_failing_check(self):
        enf = ScalingBoundaryEnforcer()
        assert not enf.check_concurrent(5)["passed"]

    def test_override_capping(self):
        enf = ScalingBoundaryEnforcer(overrides={"max_concurrent_global": 100})
        assert enf.limits["max_concurrent_global"] == 5

    def test_override_tightening(self):
        enf = ScalingBoundaryEnforcer(overrides={"max_concurrent_global": 3})
        assert enf.limits["max_concurrent_global"] == 3

    def test_forbidden_action_check(self):
        enf = ScalingBoundaryEnforcer()
        assert not enf.check_no_forbidden_action("autonomous_scaling")["passed"]

    def test_safe_action(self):
        enf = ScalingBoundaryEnforcer()
        assert enf.check_no_forbidden_action("evaluate_pressure")["passed"]

    def test_bulk_check(self):
        enf = ScalingBoundaryEnforcer()
        result = enf.check_all(concurrent=2, queue_depth=10)
        assert result["all_passed"]

    def test_queue_depth_check(self):
        enf = ScalingBoundaryEnforcer()
        assert not enf.check_queue_depth(50)["passed"]


# ── Continuity Bridge Tests ──────────────────────────────────────


class TestScalingContinuityBridges:
    def test_operations_bridge(self, tmp_dir):
        b = OperationsScalingBridge(state_dir=tmp_dir)
        r = b.capture(campaign_id="cmp-1", pressure_score=0.5)
        assert r["bridge_type"] == "operations_scaling"

    def test_environments_bridge(self, tmp_dir):
        b = EnvironmentsScalingBridge(state_dir=tmp_dir)
        r = b.capture(environment_id="env-1", saturation=0.3)
        assert r["bridge_type"] == "environments_scaling"

    def test_workflows_bridge(self, tmp_dir):
        b = WorkflowsScalingBridge(state_dir=tmp_dir)
        r = b.capture(workflow_id="wf-1")
        assert r["bridge_type"] == "workflows_scaling"

    def test_sessions_bridge(self, tmp_dir):
        b = SessionsScalingBridge(state_dir=tmp_dir)
        r = b.capture(session_id="sess-1")
        assert r["bridge_type"] == "sessions_scaling"

    def test_observability_bridge(self, tmp_dir):
        b = ObservabilityScalingBridge(state_dir=tmp_dir)
        r = b.capture(total_events=100)
        assert r["data"]["total_events"] == 100

    def test_replay_bridge(self, tmp_dir):
        b = ReplayScalingBridge(state_dir=tmp_dir)
        r = b.capture(total_validations=10, total_passes=10)
        assert r["data"]["total_passes"] == 10

    def test_continuity_bridge(self, tmp_dir):
        b = ContinuityScalingBridge(state_dir=tmp_dir)
        r = b.capture(checkpoint_count=3, continuation_depth=2)
        assert r["data"]["continuation_depth"] == 2


# ── Coordinator Integration Tests ──────────────────────────────────────


class TestCanonicalCoordinator:
    def test_evaluate_pressure(self, tmp_dir):
        eng = CanonicalOperationalScalingCoordinator(state_dir=tmp_dir)
        result = eng.evaluate_pressure()
        assert result["level"] == "nominal"
        assert result["lifecycle_state"] == "stable"

    def test_request_slot(self, tmp_dir):
        eng = CanonicalOperationalScalingCoordinator(state_dir=tmp_dir)
        d = eng.request_execution_slot(item_id="t1")
        assert d["allocated"]

    def test_slot_denied_at_limit(self, tmp_dir):
        budget = ResourceBudget(max_concurrent=2)
        eng = CanonicalOperationalScalingCoordinator(state_dir=tmp_dir, budget=budget)
        eng.request_execution_slot(item_id="t1")
        eng.request_execution_slot(item_id="t2")
        d = eng.request_execution_slot(item_id="t3")
        assert not d["allocated"]

    def test_release_slot(self, tmp_dir):
        budget = ResourceBudget(max_concurrent=1)
        eng = CanonicalOperationalScalingCoordinator(state_dir=tmp_dir, budget=budget)
        eng.request_execution_slot(item_id="t1")
        eng.release_execution_slot(latency_ms=50.0)
        d = eng.request_execution_slot(item_id="t2")
        assert d["allocated"]

    def test_set_and_arbitrate_priority(self, tmp_dir):
        eng = CanonicalOperationalScalingCoordinator(state_dir=tmp_dir)
        eng.set_priority("t1", "deferred", "operator")
        eng.set_priority("t2", "critical", "operator")
        order = eng.arbitrate_queue(["t1", "t2"])
        assert order == ["t2", "t1"]

    def test_override_priority(self, tmp_dir):
        eng = CanonicalOperationalScalingCoordinator(state_dir=tmp_dir)
        eng.set_priority("t1", "standard", "operator")
        assert eng.override_priority("t1", "critical", "operator")

    def test_enter_degraded(self, tmp_dir):
        eng = CanonicalOperationalScalingCoordinator(state_dir=tmp_dir)
        mode = eng.enter_degraded_mode("resource_exhaustion")
        assert mode["active"]

    def test_recovery(self, tmp_dir):
        eng = CanonicalOperationalScalingCoordinator(state_dir=tmp_dir)
        eng.enter_degraded_mode()
        assert eng.attempt_recovery()
        mode = eng.complete_recovery()
        assert not mode["active"]

    def test_health(self, tmp_dir):
        eng = CanonicalOperationalScalingCoordinator(state_dir=tmp_dir)
        health = eng.get_health()
        assert health["lifecycle_state"] == "stable"
        assert not health["degraded"]

    def test_budget(self, tmp_dir):
        eng = CanonicalOperationalScalingCoordinator(state_dir=tmp_dir)
        budget = eng.get_budget()
        assert budget["max_concurrent"] == 5

    def test_receipts(self, tmp_dir):
        eng = CanonicalOperationalScalingCoordinator(state_dir=tmp_dir)
        eng.evaluate_pressure()
        receipts = eng.get_recent_receipts()
        assert len(receipts) >= 1

    def test_stats(self, tmp_dir):
        eng = CanonicalOperationalScalingCoordinator(state_dir=tmp_dir)
        stats = eng.get_stats()
        assert "lifecycle" in stats
        assert "pressure" in stats
        assert "concurrency" in stats


# ── Constraint Tests ──────────────────────────────────────


class TestNoAutonomousScaling:
    def test_forbidden(self):
        enf = ScalingBoundaryEnforcer()
        assert not enf.check_no_forbidden_action("autonomous_scaling")["passed"]

    def test_coordinator_no_scale(self):
        assert not hasattr(CanonicalOperationalScalingCoordinator, "scale_up")
        assert not hasattr(CanonicalOperationalScalingCoordinator, "scale_down")
        assert not hasattr(CanonicalOperationalScalingCoordinator, "add_worker")


class TestNoRecursiveScalingLoops:
    def test_forbidden(self):
        enf = ScalingBoundaryEnforcer()
        assert not enf.check_no_forbidden_action("recursive_scaling_loops")["passed"]


class TestNoHiddenConcurrencyExpansion:
    def test_forbidden(self):
        enf = ScalingBoundaryEnforcer()
        assert not enf.check_no_forbidden_action("hidden_concurrency_expansion")["passed"]

    def test_limits_enforced(self, tmp_dir):
        eng = ConcurrencyRegulationEngine(
            state_dir=tmp_dir, overrides={"global": 1},
        )
        eng.request_slot(item_id="t1")
        d = eng.request_slot(item_id="t2")
        assert not d.allocated


class TestNoHiddenPriorityMutation:
    def test_forbidden(self):
        enf = ScalingBoundaryEnforcer()
        assert not enf.check_no_forbidden_action("hidden_priority_mutation")["passed"]

    def test_priority_has_set_by(self, tmp_dir):
        eng = OperationalPriorityEngine(state_dir=tmp_dir)
        s = eng.set_priority("t1", "high", "operator")
        assert s.set_by == "operator"


class TestNoUncontrolledThrottlingBypass:
    def test_forbidden(self):
        enf = ScalingBoundaryEnforcer()
        assert not enf.check_no_forbidden_action("hidden_throttling_bypass")["passed"]

    def test_critical_protected(self):
        eng = OperationalBackpressureEngine()
        assert eng.should_protect("critical")


class TestDeterministicPressureReplay:
    def test_pressure_hash_stable(self, tmp_dir):
        eng = ExecutionPressureEngine(state_dir=tmp_dir)
        eng.record_traversal_start()
        eng.compute_pressure()
        h1 = eng.get_pressure_hash()
        h2 = eng.get_pressure_hash()
        assert h1 == h2


class TestDeterministicArbitrationReplay:
    def test_priority_hash_stable(self, tmp_dir):
        eng = OperationalPriorityEngine(state_dir=tmp_dir)
        eng.set_priority("t1", "critical")
        eng.set_priority("t2", "deferred")
        eng.arbitrate(["t1", "t2"])
        h1 = eng.get_priority_hash()
        h2 = eng.get_priority_hash()
        assert h1 == h2


class TestDeterministicDegradedModeReplay:
    def test_degraded_hash_stable(self, tmp_dir):
        eng = DegradedModeCoordinationEngine(state_dir=tmp_dir)
        eng.enter_degraded()
        h1 = eng.get_degraded_hash()
        h2 = eng.get_degraded_hash()
        assert h1 == h2


class TestBoundedConcurrencyEnforcement:
    def test_global_ceiling(self, tmp_dir):
        eng = ConcurrencyRegulationEngine(
            state_dir=tmp_dir, overrides={"global": 3},
        )
        for i in range(3):
            eng.request_slot(item_id=f"t{i}")
        d = eng.request_slot(item_id="t3")
        assert not d.allocated


class TestBoundedQueueGrowth:
    def test_queue_bounded(self):
        enf = ScalingBoundaryEnforcer()
        assert enf.check_queue_depth(49)["passed"]
        assert not enf.check_queue_depth(50)["passed"]


class TestBoundedContinuationPacing:
    def test_continuation_pace_bounded(self, tmp_dir):
        eng = OperationalBackpressureEngine(state_dir=tmp_dir)
        pace = eng.compute_continuation_pace(100)
        assert pace <= 3000


class TestNoExecutionOutsideSpine:
    def test_coordinator_no_execute(self):
        assert not hasattr(CanonicalOperationalScalingCoordinator, "execute")
        assert not hasattr(CanonicalOperationalScalingCoordinator, "run_command")


class TestNoGovernanceBypass:
    def test_forbidden(self):
        enf = ScalingBoundaryEnforcer()
        for action in FORBIDDEN_SCALING_ACTIONS:
            assert not enf.check_no_forbidden_action(action)["passed"]


class TestNoHiddenScalingState:
    def test_decisions_persisted(self, tmp_dir):
        from pathlib import Path
        eng = CanonicalOperationalScalingCoordinator(state_dir=tmp_dir)
        eng.evaluate_pressure()
        assert (Path(tmp_dir) / "scaling_coordination_receipts.jsonl").exists()


class TestNoEnvironmentSelfRegulation:
    def test_forbidden(self):
        enf = ScalingBoundaryEnforcer()
        assert not enf.check_no_forbidden_action("environment_self_regulation")["passed"]


class TestNoUncontrolledRecoveryStorms:
    def test_max_recovery_bounded(self, tmp_dir):
        eng = DegradedModeCoordinationEngine(state_dir=tmp_dir)
        eng.enter_degraded()
        for _ in range(MAX_RECOVERY_ATTEMPTS):
            eng.attempt_recovery()
        assert not eng.attempt_recovery()


# ── Full Integration Tests ──────────────────────────────────────


class TestIntegration:
    def test_full_pressure_lifecycle(self, tmp_dir):
        eng = CanonicalOperationalScalingCoordinator(state_dir=tmp_dir)
        result = eng.evaluate_pressure()
        assert result["level"] == "nominal"

        for _ in range(3):
            eng.request_execution_slot(item_id="t")

        eng.set_priority("t1", "critical", "operator")
        eng.set_priority("t2", "deferred", "operator")
        order = eng.arbitrate_queue(["t2", "t1"])
        assert order[0] == "t1"

    def test_degraded_recovery_lifecycle(self, tmp_dir):
        eng = CanonicalOperationalScalingCoordinator(state_dir=tmp_dir)
        eng.enter_degraded_mode("concurrency_overload")
        assert eng.attempt_recovery()
        mode = eng.complete_recovery()
        assert not mode["active"]

        health = eng.get_health()
        assert health["lifecycle_state"] == "stable"

    def test_bridges_integration(self, tmp_dir):
        bridges = [
            OperationsScalingBridge(state_dir=tmp_dir),
            EnvironmentsScalingBridge(state_dir=tmp_dir),
            WorkflowsScalingBridge(state_dir=tmp_dir),
            SessionsScalingBridge(state_dir=tmp_dir),
            ObservabilityScalingBridge(state_dir=tmp_dir),
            ReplayScalingBridge(state_dir=tmp_dir),
            ContinuityScalingBridge(state_dir=tmp_dir),
        ]
        for b in bridges:
            r = b.capture()
            assert r["bridge_id"].startswith("sbr-")
        assert len(bridges) == 7

    def test_boundary_enforcement_integration(self):
        enf = ScalingBoundaryEnforcer()
        for action in FORBIDDEN_SCALING_ACTIONS:
            assert not enf.check_no_forbidden_action(action)["passed"]
        assert enf.check_no_forbidden_action("evaluate_pressure")["passed"]

    def test_replay_end_to_end(self, tmp_dir):
        v = ScalingReplayValidator(state_dir=tmp_dir)
        data = [{"score": 0.5, "level": "elevated"}]
        r1 = v.validate_pressure_determinism(data, data)
        assert r1["passed"]
        r2 = v.validate_arbitration_determinism(data, data)
        assert r2["passed"]
        assert v.get_stats()["total_passes"] == 2

    def test_concurrency_release_cycle(self, tmp_dir):
        budget = ResourceBudget(max_concurrent=2)
        eng = CanonicalOperationalScalingCoordinator(state_dir=tmp_dir, budget=budget)
        eng.request_execution_slot(item_id="t1")
        eng.request_execution_slot(item_id="t2")
        d = eng.request_execution_slot(item_id="t3")
        assert not d["allocated"]
        eng.release_execution_slot(latency_ms=100)
        d = eng.request_execution_slot(item_id="t3")
        assert d["allocated"]
