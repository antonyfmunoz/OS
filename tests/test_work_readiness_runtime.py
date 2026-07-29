"""Tests for WorkReadinessRuntime — Campaign 11.0."""

import sys
import os
import time

# Repo root is DERIVED from the active checkout, never hardcoded. The previous
# module-scope `sys.path.insert(...)` + `os.environ.setdefault("UMH_ROOT", ...)`
# pinned a foreign campaign worktree at IMPORT time and never restored it, so it
# leaked into every module collected afterwards and hard-aborted whole shards.
from tests.repo_root import ensure_repo_on_path

ensure_repo_on_path()

import pytest
from substrate.organism.work_readiness_runtime import (
    ReadinessStatus,
    ReadinessAssessment,
    WorkReadinessSnapshot,
    WorkReadinessRuntime,
)


# ── Mock helpers ──────────────────────────────────────────────────────────


class _MockNode:
    def __init__(self, node_id="wp-1", status="approved", description="test work",
                 dependencies=None, blockers=None):
        self.node_id = node_id
        self.status = status
        self.description = description
        self.dependencies = dependencies or []
        self.blockers = blockers or []


class _MockBlocker:
    def __init__(self, description="blocked by X"):
        self.description = description


class _MockWorkGraph:
    def __init__(self, nodes=None):
        self._nodes = nodes or []

    def all_work(self):
        return self._nodes

    def blocked_work(self):
        return [n for n in self._nodes if n.status == "blocked"]

    def executable_work(self):
        return [n for n in self._nodes if n.status == "approved" and not n.blockers]

    def dependencies_of(self, node_id):
        for n in self._nodes:
            if n.node_id == node_id:
                return n.dependencies
        return []


class _MockGoalAlignment:
    def __init__(self, mapping=None):
        self._mapping = mapping or {}

    def goal_for_work(self, work_id):
        return self._mapping.get(work_id, [])


class _MockCapabilityGap:
    def __init__(self, gaps=None):
        self._gaps = gaps or {}

    def gaps_for_goal(self, goal_id):
        return self._gaps.get(goal_id, [])


class _MockGap:
    def __init__(self, required_capability="python"):
        self.required_capability = required_capability


class _MockApprovalRuntime:
    def __init__(self, pending=None):
        self._pending = pending or []

    def snapshot(self):
        return _MockApprovalSnap(self._pending)


class _MockApprovalSnap:
    def __init__(self, pending):
        self.pending = pending


class _MockApproval:
    def __init__(self, source_id="wp-1", approval_id="apr-1"):
        self.source_id = source_id
        self.approval_id = approval_id


class _MockDelegation:
    def __init__(self, missions=None):
        self._missions = missions or {}


# ── ReadinessStatus Tests ─────────────────────────────────────────────────


class TestReadinessStatus:
    def test_values(self):
        assert ReadinessStatus.READY.value == "ready"
        assert ReadinessStatus.WAITING_APPROVAL.value == "waiting_approval"
        assert ReadinessStatus.WAITING_CAPABILITY.value == "waiting_capability"
        assert ReadinessStatus.WAITING_DEPENDENCY.value == "waiting_dependency"
        assert ReadinessStatus.WAITING_DELEGATION.value == "waiting_delegation"
        assert ReadinessStatus.BLOCKED.value == "blocked"

    def test_is_str_enum(self):
        assert isinstance(ReadinessStatus.READY, str)

    def test_all_values(self):
        assert len(ReadinessStatus) == 6


# ── ReadinessAssessment Tests ─────────────────────────────────────────────


class TestReadinessAssessment:
    def test_defaults(self):
        a = ReadinessAssessment()
        assert a.work_id == ""
        assert a.status == ReadinessStatus.BLOCKED
        assert a.readiness_score == 0.0

    def test_to_dict(self):
        a = ReadinessAssessment(
            work_id="wp-1",
            status=ReadinessStatus.READY,
            readiness_score=1.0,
            recommended_action="execute",
        )
        d = a.to_dict()
        assert d["work_id"] == "wp-1"
        assert d["status"] == "ready"
        assert d["readiness_score"] == 1.0

    def test_from_dict(self):
        d = {
            "work_id": "wp-2",
            "status": "waiting_approval",
            "readiness_score": 0.3,
            "blocking_reasons": ["awaiting approval"],
        }
        a = ReadinessAssessment.from_dict(d)
        assert a.work_id == "wp-2"
        assert a.status == ReadinessStatus.WAITING_APPROVAL
        assert len(a.blocking_reasons) == 1

    def test_from_dict_invalid_status(self):
        d = {"status": "invalid_status"}
        a = ReadinessAssessment.from_dict(d)
        assert a.status == ReadinessStatus.BLOCKED

    def test_roundtrip(self):
        a = ReadinessAssessment(
            work_id="wp-3",
            status=ReadinessStatus.WAITING_DEPENDENCY,
            blocking_reasons=["dep-1 pending"],
            unresolved_dependencies=["dep-1"],
            readiness_score=0.6,
        )
        d = a.to_dict()
        a2 = ReadinessAssessment.from_dict(d)
        assert a2.work_id == a.work_id
        assert a2.status == a.status
        assert a2.readiness_score == a.readiness_score


# ── WorkReadinessSnapshot Tests ───────────────────────────────────────────


class TestWorkReadinessSnapshot:
    def test_defaults(self):
        snap = WorkReadinessSnapshot()
        assert snap.total == 0
        assert snap.health == "unknown"

    def test_to_dict(self):
        snap = WorkReadinessSnapshot(
            total=5,
            by_status={"ready": 3, "blocked": 2},
            health="mostly_ready",
        )
        d = snap.to_dict()
        assert d["total"] == 5
        assert d["health"] == "mostly_ready"
        assert d["by_status"]["ready"] == 3


# ── WorkReadinessRuntime Tests ────────────────────────────────────────────


class TestWorkReadinessRuntime:
    @pytest.fixture
    def nodes(self):
        return [
            _MockNode("wp-1", "approved"),
            _MockNode("wp-2", "blocked", blockers=[_MockBlocker("hard block")]),
            _MockNode("wp-3", "approval_pending"),
            _MockNode("wp-4", "approved"),
        ]

    @pytest.fixture
    def runtime(self, nodes):
        return WorkReadinessRuntime(
            work_graph=_MockWorkGraph(nodes),
            goal_alignment=_MockGoalAlignment({
                "wp-1": [{"goal_id": "g-1"}],
                "wp-4": [{"goal_id": "g-2"}],
            }),
            capability_gap=_MockCapabilityGap({
                "g-2": [_MockGap("advanced-ml")],
            }),
            approval_runtime=_MockApprovalRuntime(),
            delegation_runtime=_MockDelegation(),
        )

    def test_assess_ready(self, runtime):
        a = runtime.assess("wp-1")
        assert a.status == ReadinessStatus.READY
        assert a.readiness_score == 1.0
        assert a.recommended_action == "execute"

    def test_assess_blocked(self, runtime):
        a = runtime.assess("wp-2")
        assert a.status == ReadinessStatus.BLOCKED
        assert "hard block" in a.blocking_reasons[0]
        assert a.readiness_score == 0.0

    def test_assess_waiting_approval(self, runtime):
        a = runtime.assess("wp-3")
        assert a.status == ReadinessStatus.WAITING_APPROVAL
        assert a.readiness_score == 0.3

    def test_assess_waiting_capability(self, runtime):
        a = runtime.assess("wp-4")
        assert a.status == ReadinessStatus.WAITING_CAPABILITY
        assert "advanced-ml" in a.missing_capabilities

    def test_assess_not_found(self, runtime):
        a = runtime.assess("wp-missing")
        assert a.status == ReadinessStatus.BLOCKED
        assert "not found" in a.blocking_reasons[0]

    def test_assess_all(self, runtime):
        results = runtime.assess_all()
        assert len(results) == 4
        statuses = {a.status for a in results}
        assert ReadinessStatus.READY in statuses
        assert ReadinessStatus.BLOCKED in statuses

    def test_ready_work(self, runtime):
        ready = runtime.ready_work()
        assert all(a.status == ReadinessStatus.READY for a in ready)

    def test_blocked_work(self, runtime):
        blocked = runtime.blocked_work()
        assert all(a.status != ReadinessStatus.READY for a in blocked)
        assert len(blocked) > 0

    def test_work_for_goal(self, runtime):
        items = runtime.work_for_goal("g-1")
        assert len(items) >= 1
        assert all("g-1" in a.goal_ids for a in items)

    def test_work_for_goal_no_match(self, runtime):
        items = runtime.work_for_goal("g-nonexistent")
        assert len(items) == 0

    def test_work_for_capability(self, runtime):
        items = runtime.work_for_capability("advanced-ml")
        assert len(items) >= 1
        assert all("advanced-ml" in a.missing_capabilities for a in items)

    def test_next_unblockable(self, runtime):
        results = runtime.next_unblockable()
        assert isinstance(results, list)
        if len(results) >= 2:
            assert results[0].readiness_score >= results[1].readiness_score

    def test_snapshot(self, runtime):
        snap = runtime.snapshot()
        assert snap.total == 4
        assert isinstance(snap.by_status, dict)
        assert snap.health in ("ready", "mostly_ready", "constrained", "blocked", "unknown")

    def test_summary(self, runtime):
        s = runtime.summary()
        assert "total" in s
        assert "health" in s
        assert "by_status" in s

    def test_health(self, runtime):
        h = runtime.health()
        assert h in ("ready", "mostly_ready", "constrained", "blocked", "unknown")

    def test_graceful_degradation_no_subsystems(self):
        empty_wg = _MockWorkGraph([])
        rt = WorkReadinessRuntime(work_graph=empty_wg)
        snap = rt.snapshot()
        assert snap.total == 0
        assert snap.health == "unknown"

    def test_snapshot_to_dict(self, runtime):
        snap = runtime.snapshot()
        d = snap.to_dict()
        assert isinstance(d, dict)
        assert "total" in d
        assert "ready_count" in d
        assert "blocked_count" in d

    def test_dependency_classification(self):
        dep_node = _MockNode("dep-1", "completed")
        main_node = _MockNode("wp-main", "approved", dependencies=["dep-1"])
        wg = _MockWorkGraph([dep_node, main_node])
        rt = WorkReadinessRuntime(work_graph=wg)
        a = rt.assess("wp-main")
        assert a.status == ReadinessStatus.READY

    def test_unresolved_dependency(self):
        dep_node = _MockNode("dep-1", "drafted")
        main_node = _MockNode("wp-main", "approved", dependencies=["dep-1"])
        wg = _MockWorkGraph([dep_node, main_node])
        rt = WorkReadinessRuntime(work_graph=wg)
        a = rt.assess("wp-main")
        assert a.status == ReadinessStatus.WAITING_DEPENDENCY
        assert "dep-1" in a.unresolved_dependencies

    def test_completed_work_not_assessed(self, runtime):
        nodes_with_completed = [
            _MockNode("wp-done", "completed"),
            _MockNode("wp-active", "approved"),
        ]
        rt = WorkReadinessRuntime(work_graph=_MockWorkGraph(nodes_with_completed))
        results = rt.assess_all()
        assert len(results) == 1
        assert results[0].work_id == "wp-active"
