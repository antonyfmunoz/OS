"""Tests for CommandCenterMVPRuntime — Campaign 3.2.

Covers: empty state degradation, individual section composition,
recommendation priority ordering, snapshot assembly, type serialization,
section routing, subsystem failure isolation.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.workstation.command_center_mvp_runtime import (
    CapabilityPulse,
    CommandCenterMVPRuntime,
    CommandCenterRecommendation,
    CommandCenterSection,
    CommandCenterSnapshot,
    ExecutionPulse,
    MigrationPulse,
    _safe_call,
)


# ── Mock subsystems ───────────────────────────────────────────────────────

class MockSnapshotRuntime:
    def situation(self) -> dict:
        return {"mode": "focused", "active_venture": "test-venture"}


class MockAttentionEngine:
    def __init__(self, items=None):
        self._items = items or []

    def top(self, n: int = 5):
        return self._items[:n]


class MockAgentFleet:
    def __init__(self, status=None, dispatches=None):
        self._status = status or {"active_agents": 3}
        self._dispatches = dispatches or [{"id": "a1"}, {"id": "a2"}]

    def fleet_status(self):
        return self._status

    def active_dispatches(self):
        return self._dispatches


class MockComputeFabric:
    def __init__(self, health=None):
        self._health = health or {"online_nodes": 2}

    def health(self):
        return self._health


class MockGovernedWork:
    def __init__(self, active=None, blocked=None, queue=None):
        self._active = active or []
        self._blocked = blocked or []
        self._queue = queue or []

    def active(self):
        return self._active

    def blocked(self):
        return self._blocked

    def queue(self):
        return self._queue


class MockCompoundingEngine:
    def __init__(self, candidates=None):
        self._candidates = candidates or []

    def list_candidates(self, status="proposed"):
        return self._candidates


class MockMigrationRuntime:
    def __init__(self, report=None, priorities=None):
        self._report = report or {"total_exits": 0, "coverage_percentage": 0.0}
        self._priorities = priorities or []

    def coverage_report(self):
        return self._report

    def migration_priorities(self):
        return self._priorities


class MockCapabilityRuntime:
    def __init__(self, summary=None, emerging=None):
        self._summary = summary or {"total": 28, "by_maturity": {"mature": 20, "emerging": 8}}
        self._emerging = emerging or [{"name": "voice"}]

    def summary(self):
        return self._summary

    def capabilities_by_maturity(self, maturity: str):
        if maturity == "emerging":
            return self._emerging
        return []


class MockCapabilityMap:
    def summary(self):
        return {"total_routes": 52, "total_panels": 53, "mvp_gap_count": 2}


class FailingSubsystem:
    def __getattr__(self, name):
        def boom(*a, **kw):
            raise RuntimeError("subsystem failure")
        return boom


class DictReturnSubsystem:
    """Returns to_dict-compatible objects."""
    pass


# ── Empty State (no subsystems) ──────────────────────────────────────────

class TestEmptyState:
    def test_snapshot_returns_snapshot(self) -> None:
        rt = CommandCenterMVPRuntime()
        snap = rt.snapshot()
        assert isinstance(snap, CommandCenterSnapshot)

    def test_situation_unavailable(self) -> None:
        rt = CommandCenterMVPRuntime()
        result = rt.situation()
        assert result["status"] == "unavailable"

    def test_attention_empty(self) -> None:
        rt = CommandCenterMVPRuntime()
        assert rt.attention() == []

    def test_execution_pulse_zeros(self) -> None:
        rt = CommandCenterMVPRuntime()
        ep = rt.execution_pulse()
        assert ep.active_work == 0
        assert ep.blocked_work == 0
        assert ep.queue_depth == 0

    def test_capability_pulse_zeros(self) -> None:
        rt = CommandCenterMVPRuntime()
        cp = rt.capability_pulse()
        assert cp.total_capabilities == 0

    def test_migration_pulse_zeros(self) -> None:
        rt = CommandCenterMVPRuntime()
        mp = rt.migration_pulse()
        assert mp.total_exits == 0

    def test_recommendations_empty(self) -> None:
        rt = CommandCenterMVPRuntime()
        assert rt.recommendations() == []

    def test_snapshot_to_dict_serializable(self) -> None:
        rt = CommandCenterMVPRuntime()
        d = rt.snapshot().to_dict()
        assert isinstance(d, dict)
        assert "situation" in d
        assert "execution" in d


# ── Situation Section ─────────────────────────────────────────────────────

class TestSituation:
    def test_with_snapshot_runtime(self) -> None:
        rt = CommandCenterMVPRuntime(snapshot_runtime=MockSnapshotRuntime())
        result = rt.situation()
        assert result["mode"] == "focused"

    def test_with_failing_runtime(self) -> None:
        rt = CommandCenterMVPRuntime(snapshot_runtime=FailingSubsystem())
        result = rt.situation()
        assert result["status"] == "unavailable"


# ── Attention Section ─────────────────────────────────────────────────────

class TestAttention:
    def test_with_items(self) -> None:
        items = [
            {"title": "Deploy failing", "severity": "high"},
            {"title": "New PR", "severity": "low"},
        ]
        rt = CommandCenterMVPRuntime(attention_engine=MockAttentionEngine(items))
        result = rt.attention(limit=5)
        assert len(result) == 2
        assert result[0]["title"] == "Deploy failing"

    def test_respects_limit(self) -> None:
        items = [{"title": f"item-{i}"} for i in range(10)]
        rt = CommandCenterMVPRuntime(attention_engine=MockAttentionEngine(items))
        result = rt.attention(limit=3)
        assert len(result) == 3

    def test_with_to_dict_objects(self) -> None:
        class FakeItem:
            def to_dict(self):
                return {"title": "from to_dict"}

        rt = CommandCenterMVPRuntime(attention_engine=MockAttentionEngine([FakeItem()]))
        result = rt.attention()
        assert result[0]["title"] == "from to_dict"


# ── Execution Pulse ──────────────────────────────────────────────────────

class TestExecutionPulse:
    def test_active_work_count(self) -> None:
        rt = CommandCenterMVPRuntime(governed_work=MockGovernedWork(active=["a", "b"]))
        ep = rt.execution_pulse()
        assert ep.active_work == 2

    def test_blocked_work_count(self) -> None:
        rt = CommandCenterMVPRuntime(governed_work=MockGovernedWork(blocked=["x"]))
        ep = rt.execution_pulse()
        assert ep.blocked_work == 1

    def test_queue_depth(self) -> None:
        rt = CommandCenterMVPRuntime(governed_work=MockGovernedWork(queue=["q1", "q2", "q3"]))
        ep = rt.execution_pulse()
        assert ep.queue_depth == 3

    def test_active_agents_from_fleet(self) -> None:
        rt = CommandCenterMVPRuntime(agent_fleet=MockAgentFleet(status={"active_agents": 5}))
        ep = rt.execution_pulse()
        assert ep.active_agents == 5

    def test_active_agents_from_dispatches(self) -> None:
        rt = CommandCenterMVPRuntime(
            agent_fleet=MockAgentFleet(status={"active_agents": 1}, dispatches=["d1", "d2", "d3"])
        )
        ep = rt.execution_pulse()
        assert ep.active_agents == 3

    def test_compute_nodes_from_fabric(self) -> None:
        rt = CommandCenterMVPRuntime(compute_fabric=MockComputeFabric({"online_nodes": 4}))
        ep = rt.execution_pulse()
        assert ep.active_compute_nodes == 4

    def test_compounding_candidates(self) -> None:
        rt = CommandCenterMVPRuntime(compounding_engine=MockCompoundingEngine(["c1", "c2"]))
        ep = rt.execution_pulse()
        assert ep.compounding_candidates == 2

    def test_pending_approvals_from_queue(self) -> None:
        queue = [
            {"id": "1", "status": "approval_pending"},
            {"id": "2", "status": "active"},
            {"id": "3", "status": "approval_pending"},
        ]
        rt = CommandCenterMVPRuntime(governed_work=MockGovernedWork(queue=queue))
        ep = rt.execution_pulse()
        assert ep.pending_approvals == 2

    def test_failing_fleet_still_returns_pulse(self) -> None:
        rt = CommandCenterMVPRuntime(
            agent_fleet=FailingSubsystem(),
            compute_fabric=MockComputeFabric(),
        )
        ep = rt.execution_pulse()
        assert ep.active_compute_nodes == 2
        assert ep.active_agents == 0


# ── Capability Pulse ─────────────────────────────────────────────────────

class TestCapabilityPulse:
    def test_total_from_summary(self) -> None:
        rt = CommandCenterMVPRuntime(capability_runtime=MockCapabilityRuntime())
        cp = rt.capability_pulse()
        assert cp.total_capabilities == 28

    def test_by_maturity(self) -> None:
        rt = CommandCenterMVPRuntime(capability_runtime=MockCapabilityRuntime())
        cp = rt.capability_pulse()
        assert cp.by_maturity["mature"] == 20

    def test_coverage_gaps_from_emerging(self) -> None:
        rt = CommandCenterMVPRuntime(
            capability_runtime=MockCapabilityRuntime(emerging=[{"a": 1}, {"b": 2}])
        )
        cp = rt.capability_pulse()
        assert cp.coverage_gaps == 2


# ── Migration Pulse ──────────────────────────────────────────────────────

class TestMigrationPulse:
    def test_total_exits(self) -> None:
        rt = CommandCenterMVPRuntime(
            migration_runtime=MockMigrationRuntime(
                report={"total_exits": 15, "coverage_percentage": 60.0}
            )
        )
        mp = rt.migration_pulse()
        assert mp.total_exits == 15
        assert mp.coverage_percentage == 60.0

    def test_priorities(self) -> None:
        prios = [
            {"reason": "ChatGPT", "count": 5, "percentage": 33.0},
            {"reason": "Manual SSH", "count": 3, "percentage": 20.0},
        ]
        rt = CommandCenterMVPRuntime(
            migration_runtime=MockMigrationRuntime(priorities=prios)
        )
        mp = rt.migration_pulse()
        assert len(mp.top_exit_reasons) == 2
        assert mp.top_exit_reasons[0]["reason"] == "ChatGPT"


# ── Recommendations ──────────────────────────────────────────────────────

class TestRecommendations:
    def test_blocked_work_generates_priority_1(self) -> None:
        rt = CommandCenterMVPRuntime(governed_work=MockGovernedWork(blocked=["b1"]))
        recs = rt.recommendations()
        assert recs[0].priority == 1
        assert recs[0].action == "Unblock"

    def test_pending_approvals_generates_priority_2(self) -> None:
        queue = [{"id": "1", "status": "approval_pending"}]
        rt = CommandCenterMVPRuntime(governed_work=MockGovernedWork(queue=queue))
        recs = rt.recommendations()
        priorities = [r.priority for r in recs]
        assert 2 in priorities

    def test_high_attention_generates_priority_3(self) -> None:
        items = [{"title": "Critical issue", "severity": "high", "action_hint": "Investigate"}]
        rt = CommandCenterMVPRuntime(attention_engine=MockAttentionEngine(items))
        recs = rt.recommendations()
        priorities = [r.priority for r in recs]
        assert 3 in priorities

    def test_queue_depth_generates_priority_4(self) -> None:
        rt = CommandCenterMVPRuntime(governed_work=MockGovernedWork(queue=["q1"]))
        recs = rt.recommendations()
        priorities = [r.priority for r in recs]
        assert 4 in priorities

    def test_compounding_generates_priority_5(self) -> None:
        rt = CommandCenterMVPRuntime(compounding_engine=MockCompoundingEngine(["c1"]))
        recs = rt.recommendations()
        priorities = [r.priority for r in recs]
        assert 5 in priorities

    def test_migration_generates_priority_6(self) -> None:
        prios = [{"reason": "External tool", "count": 1}]
        rt = CommandCenterMVPRuntime(
            migration_runtime=MockMigrationRuntime(priorities=prios)
        )
        recs = rt.recommendations()
        priorities = [r.priority for r in recs]
        assert 6 in priorities

    def test_recommendations_sorted_by_priority(self) -> None:
        queue = [{"id": "1", "status": "approval_pending"}]
        rt = CommandCenterMVPRuntime(
            governed_work=MockGovernedWork(blocked=["b1"], queue=queue),
            compounding_engine=MockCompoundingEngine(["c1"]),
        )
        recs = rt.recommendations()
        for i in range(len(recs) - 1):
            assert recs[i].priority <= recs[i + 1].priority

    def test_limit_respected(self) -> None:
        queue = [{"id": "1", "status": "approval_pending"}]
        prios = [{"reason": "External tool", "count": 1}]
        rt = CommandCenterMVPRuntime(
            governed_work=MockGovernedWork(blocked=["b1"], queue=queue),
            compounding_engine=MockCompoundingEngine(["c1"]),
            migration_runtime=MockMigrationRuntime(priorities=prios),
        )
        recs = rt.recommendations(limit=2)
        assert len(recs) <= 2

    def test_all_recs_have_panel_link(self) -> None:
        queue = [{"id": "1", "status": "approval_pending"}]
        rt = CommandCenterMVPRuntime(
            governed_work=MockGovernedWork(blocked=["b1"], queue=queue),
        )
        for r in rt.recommendations():
            assert r.panel_link != ""


# ── Section Routing ──────────────────────────────────────────────────────

class TestSectionRouting:
    def test_situation_section(self) -> None:
        rt = CommandCenterMVPRuntime(snapshot_runtime=MockSnapshotRuntime())
        result = rt.section("situation")
        assert "mode" in result

    def test_attention_section(self) -> None:
        rt = CommandCenterMVPRuntime()
        result = rt.section("attention")
        assert "items" in result

    def test_execution_section(self) -> None:
        rt = CommandCenterMVPRuntime()
        result = rt.section("execution")
        assert "active_work" in result

    def test_capability_section(self) -> None:
        rt = CommandCenterMVPRuntime()
        result = rt.section("capability")
        assert "total_capabilities" in result

    def test_migration_section(self) -> None:
        rt = CommandCenterMVPRuntime()
        result = rt.section("migration")
        assert "total_exits" in result

    def test_recommendations_section(self) -> None:
        rt = CommandCenterMVPRuntime()
        result = rt.section("recommendations")
        assert "items" in result

    def test_unknown_section_error(self) -> None:
        rt = CommandCenterMVPRuntime()
        result = rt.section("nonexistent")
        assert "error" in result


# ── Snapshot Assembly ────────────────────────────────────────────────────

class TestSnapshotAssembly:
    def test_full_snapshot_with_all_subsystems(self) -> None:
        rt = CommandCenterMVPRuntime(
            snapshot_runtime=MockSnapshotRuntime(),
            attention_engine=MockAttentionEngine([{"title": "t"}]),
            agent_fleet=MockAgentFleet(),
            compute_fabric=MockComputeFabric(),
            governed_work=MockGovernedWork(active=["a"]),
            compounding_engine=MockCompoundingEngine(),
            migration_runtime=MockMigrationRuntime(),
            capability_runtime=MockCapabilityRuntime(),
            capability_map=MockCapabilityMap(),
        )
        snap = rt.snapshot()
        assert snap.situation["mode"] == "focused"
        assert len(snap.attention) == 1
        assert snap.execution.active_work == 1
        assert snap.capability.total_capabilities == 28
        assert snap.cockpit_health["total_routes"] == 52

    def test_snapshot_generated_at(self) -> None:
        rt = CommandCenterMVPRuntime()
        snap = rt.snapshot()
        assert snap.generated_at > 0

    def test_snapshot_to_dict_complete(self) -> None:
        rt = CommandCenterMVPRuntime()
        d = rt.snapshot().to_dict()
        assert "situation" in d
        assert "attention" in d
        assert "execution" in d
        assert "capability" in d
        assert "migration" in d
        assert "recommendations" in d
        assert "cockpit_health" in d
        assert "generated_at" in d


# ── Type Serialization ───────────────────────────────────────────────────

class TestTypeSerialization:
    def test_execution_pulse_to_dict(self) -> None:
        ep = ExecutionPulse(active_work=3, blocked_work=1)
        d = ep.to_dict()
        assert d["active_work"] == 3
        assert d["blocked_work"] == 1

    def test_capability_pulse_to_dict(self) -> None:
        cp = CapabilityPulse(total_capabilities=10, by_maturity={"mature": 8})
        d = cp.to_dict()
        assert d["total_capabilities"] == 10
        assert d["by_maturity"]["mature"] == 8

    def test_migration_pulse_to_dict(self) -> None:
        mp = MigrationPulse(total_exits=5, coverage_percentage=75.0)
        d = mp.to_dict()
        assert d["total_exits"] == 5
        assert d["coverage_percentage"] == 75.0

    def test_recommendation_to_dict(self) -> None:
        r = CommandCenterRecommendation(
            priority=1, action="Fix", rationale="broken",
            panel_link="work", source_system="governed_work",
        )
        d = r.to_dict()
        assert d["priority"] == 1
        assert d["source_system"] == "governed_work"


# ── safe_call isolation ──────────────────────────────────────────────────

class TestSafeCall:
    def test_none_obj_returns_none(self) -> None:
        assert _safe_call(None, "foo") is None

    def test_missing_method_returns_none(self) -> None:
        assert _safe_call(object(), "nonexistent") is None

    def test_exception_returns_none(self) -> None:
        assert _safe_call(FailingSubsystem(), "boom") is None

    def test_successful_call(self) -> None:
        class OK:
            def val(self):
                return 42
        assert _safe_call(OK(), "val") == 42


# ── CommandCenterSection Enum ────────────────────────────────────────────

class TestCommandCenterSectionEnum:
    def test_all_sections(self) -> None:
        names = {s.value for s in CommandCenterSection}
        assert names == {
            "situation", "attention", "execution",
            "capability", "migration", "recommendations",
        }

    def test_string_enum_value(self) -> None:
        assert CommandCenterSection.SITUATION == "situation"
        assert isinstance(CommandCenterSection.SITUATION, str)
