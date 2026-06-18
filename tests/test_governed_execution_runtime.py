"""Tests for Governed Execution Runtime — Campaign 16.0."""
from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from unittest.mock import MagicMock

from substrate.organism.governed_execution_runtime import (
    ExecutionBlocker,
    ExecutionState,
    ExecutionStateAssessment,
    GovernedExecutionHealth,
    GovernedExecutionRuntime,
    GovernedExecutionSnapshot,
)


# ── Enum Tests ───────────────────────────────────────────────────────


class TestExecutionStateEnum:
    def test_values(self) -> None:
        assert ExecutionState.IDLE.value == "idle"
        assert ExecutionState.ASSESSING.value == "assessing"
        assert ExecutionState.GOVERNED.value == "governed"
        assert ExecutionState.EXECUTING.value == "executing"
        assert ExecutionState.BLOCKED.value == "blocked"

    def test_count(self) -> None:
        assert len(ExecutionState) == 5


class TestExecutionBlockerEnum:
    def test_values(self) -> None:
        assert ExecutionBlocker.UNRESOLVED_DEPS.value == "unresolved_deps"
        assert ExecutionBlocker.MISSING_CAPABILITY.value == "missing_capability"
        assert ExecutionBlocker.PENDING_APPROVAL.value == "pending_approval"
        assert ExecutionBlocker.RESOURCE_CONTENTION.value == "resource_contention"
        assert ExecutionBlocker.NO_EXECUTOR.value == "no_executor"

    def test_count(self) -> None:
        assert len(ExecutionBlocker) == 5


class TestGovernedExecutionHealthEnum:
    def test_values(self) -> None:
        assert GovernedExecutionHealth.OPTIMAL.value == "optimal"
        assert GovernedExecutionHealth.ACTIVE.value == "active"
        assert GovernedExecutionHealth.CONSTRAINED.value == "constrained"
        assert GovernedExecutionHealth.BLOCKED.value == "blocked"
        assert GovernedExecutionHealth.OFFLINE.value == "offline"

    def test_count(self) -> None:
        assert len(GovernedExecutionHealth) == 5


# ── Dataclass Tests ──────────────────────────────────────────────────


class TestExecutionStateAssessment:
    def test_defaults(self) -> None:
        a = ExecutionStateAssessment()
        assert a.state == "idle"
        assert a.ready_count == 0
        assert a.blocked_count == 0
        assert a.pending_approval_count == 0
        assert a.active_tradeoffs == 0
        assert a.top_blockers == []
        assert a.resource_health == "unknown"
        assert a.delegation_coverage == 0.0
        assert a.timestamp > 0

    def test_to_dict(self) -> None:
        a = ExecutionStateAssessment(state="executing", ready_count=3)
        d = a.to_dict()
        assert d["state"] == "executing"
        assert d["ready_count"] == 3
        assert "timestamp" in d


class TestGovernedExecutionSnapshot:
    def test_defaults(self) -> None:
        s = GovernedExecutionSnapshot()
        assert s.state == "idle"
        assert s.health == "offline"
        assert s.assessment == {}
        assert s.generated_at > 0

    def test_to_dict(self) -> None:
        s = GovernedExecutionSnapshot(state="executing", health="optimal")
        d = s.to_dict()
        assert d["state"] == "executing"
        assert d["health"] == "optimal"
        assert "readiness_summary" in d
        assert "delegation_summary" in d
        assert "allocation_summary" in d
        assert "tradeoff_summary" in d
        assert "approval_summary" in d
        assert "generated_at" in d


# ── Runtime — No Dependencies ────────────────────────────────────────


class TestGovernedExecutionNoDeps:
    @classmethod
    def setup_class(cls) -> None:
        cls.rt = GovernedExecutionRuntime()

    def test_state_returns_valid_enum(self) -> None:
        s = self.rt.state()
        assert isinstance(s, ExecutionState)

    def test_assessment_returns_assessment(self) -> None:
        a = self.rt.assessment()
        assert isinstance(a, ExecutionStateAssessment)
        assert a.state in [e.value for e in ExecutionState]

    def test_blockers_returns_list(self) -> None:
        b = self.rt.blockers()
        assert isinstance(b, list)

    def test_readiness_summary_returns_dict(self) -> None:
        s = self.rt.readiness_summary()
        assert isinstance(s, dict)

    def test_delegation_summary_returns_dict(self) -> None:
        s = self.rt.delegation_summary()
        assert isinstance(s, dict)

    def test_allocation_summary_returns_dict(self) -> None:
        s = self.rt.allocation_summary()
        assert isinstance(s, dict)

    def test_tradeoff_summary_returns_dict(self) -> None:
        s = self.rt.tradeoff_summary()
        assert isinstance(s, dict)

    def test_approval_summary_returns_dict(self) -> None:
        s = self.rt.approval_summary()
        assert isinstance(s, dict)

    def test_health_returns_valid_enum(self) -> None:
        h = self.rt.health()
        assert isinstance(h, GovernedExecutionHealth)

    def test_snapshot_no_deps(self) -> None:
        snap = self.rt.snapshot()
        assert isinstance(snap, GovernedExecutionSnapshot)
        d = snap.to_dict()
        assert "state" in d
        assert "health" in d

    def test_summary_no_deps(self) -> None:
        s = self.rt.summary()
        assert "state" in s
        assert "health" in s
        assert "ready_count" in s
        assert "blocked_count" in s


# ── Runtime — With Fakes ─────────────────────────────────────────────


class _FakeReadiness:
    def __init__(
        self, ready: list | None = None, blocked: list | None = None, all_work: list | None = None
    ) -> None:
        self._ready = ready or []
        self._blocked = blocked or []
        self._all = all_work if all_work is not None else self._ready + self._blocked

    def ready_work(self) -> list:
        return self._ready

    def blocked_work(self) -> list:
        return self._blocked

    def assess_all(self) -> list:
        return self._all

    def summary(self) -> dict:
        return {"ready": len(self._ready), "blocked": len(self._blocked)}


class _FakeDelegation:
    def __init__(self, coverage: float = 0.0) -> None:
        self._coverage = coverage

    def snapshot(self) -> MagicMock:
        m = MagicMock()
        m.to_dict.return_value = {
            "total_assessed": 10,
            "delegatable_count": int(10 * self._coverage),
        }
        return m

    def summary(self) -> dict:
        return {"coverage": self._coverage}


class _FakeAllocation:
    def __init__(self, health: str = "balanced") -> None:
        self._health = health

    def health(self) -> MagicMock:
        m = MagicMock()
        m.value = self._health
        return m

    def summary(self) -> dict:
        return {"health": self._health}


class _FakeTradeoff:
    def __init__(self, contentions: int = 0) -> None:
        self._contentions = contentions

    def contention_map(self) -> dict:
        return {f"resource_{i}": [f"t{j}" for j in range(3)] for i in range(self._contentions)}

    def summary(self) -> dict:
        return {"contentions": self._contentions}


class _FakeApprovals:
    def __init__(self, pending: int = 0) -> None:
        self._pending = pending

    def pending(self) -> list:
        return [{"approval_id": f"a-{i}"} for i in range(self._pending)]

    def snapshot(self) -> MagicMock:
        m = MagicMock()
        m.to_dict.return_value = {"pending_count": self._pending}
        return m


class TestGovernedExecutionStateMachine:
    def test_idle_no_work(self) -> None:
        rt = GovernedExecutionRuntime(
            work_readiness=_FakeReadiness([], [], []),
            unified_approvals=_FakeApprovals(0),
        )
        assert rt.state() == ExecutionState.IDLE

    def test_governed_with_pending_approvals(self) -> None:
        rt = GovernedExecutionRuntime(
            work_readiness=_FakeReadiness(["w1"], [], ["w1"]),
            unified_approvals=_FakeApprovals(2),
        )
        assert rt.state() == ExecutionState.GOVERNED

    def test_executing_ready_with_delegation(self) -> None:
        rt = GovernedExecutionRuntime(
            work_readiness=_FakeReadiness(["w1", "w2"], [], ["w1", "w2"]),
            delegation_readiness=_FakeDelegation(coverage=0.8),
            unified_approvals=_FakeApprovals(0),
        )
        assert rt.state() == ExecutionState.EXECUTING

    def test_blocked_more_blocked_than_ready(self) -> None:
        rt = GovernedExecutionRuntime(
            work_readiness=_FakeReadiness(["w1"], ["b1", "b2", "b3"], ["w1", "b1", "b2", "b3"]),
            unified_approvals=_FakeApprovals(0),
        )
        assert rt.state() == ExecutionState.BLOCKED

    def test_assessing_work_exists_low_coverage(self) -> None:
        rt = GovernedExecutionRuntime(
            work_readiness=_FakeReadiness(["w1"], [], ["w1"]),
            delegation_readiness=_FakeDelegation(coverage=0.2),
            unified_approvals=_FakeApprovals(0),
        )
        assert rt.state() == ExecutionState.ASSESSING


class TestGovernedExecutionHealth:
    def test_offline_no_work(self) -> None:
        rt = GovernedExecutionRuntime(
            work_readiness=_FakeReadiness([], [], []),
            unified_approvals=_FakeApprovals(0),
        )
        assert rt.health() == GovernedExecutionHealth.OFFLINE

    def test_optimal_ready_no_blocks(self) -> None:
        rt = GovernedExecutionRuntime(
            work_readiness=_FakeReadiness(["w1", "w2"], [], ["w1", "w2"]),
            delegation_readiness=_FakeDelegation(coverage=0.8),
            resource_allocation=_FakeAllocation("balanced"),
            tradeoff_engine=_FakeTradeoff(0),
            unified_approvals=_FakeApprovals(0),
        )
        assert rt.health() == GovernedExecutionHealth.OPTIMAL

    def test_blocked_health(self) -> None:
        rt = GovernedExecutionRuntime(
            work_readiness=_FakeReadiness([], ["b1", "b2"], ["b1", "b2"]),
            unified_approvals=_FakeApprovals(0),
        )
        assert rt.health() == GovernedExecutionHealth.BLOCKED

    def test_active_health(self) -> None:
        rt = GovernedExecutionRuntime(
            work_readiness=_FakeReadiness(["w1", "w2"], ["b1"], ["w1", "w2", "b1"]),
            delegation_readiness=_FakeDelegation(coverage=0.5),
            unified_approvals=_FakeApprovals(0),
        )
        h = rt.health()
        assert h in (GovernedExecutionHealth.ACTIVE, GovernedExecutionHealth.CONSTRAINED)


class TestGovernedExecutionSnapshot:
    def test_snapshot_with_fakes(self) -> None:
        rt = GovernedExecutionRuntime(
            work_readiness=_FakeReadiness(["w1"], ["b1"], ["w1", "b1"]),
            delegation_readiness=_FakeDelegation(0.5),
            resource_allocation=_FakeAllocation("balanced"),
            tradeoff_engine=_FakeTradeoff(1),
            unified_approvals=_FakeApprovals(1),
        )
        snap = rt.snapshot()
        d = snap.to_dict()
        assert d["state"] == "governed"
        assert "readiness_summary" in d
        assert d["readiness_summary"]["ready"] == 1

    def test_summary_with_fakes(self) -> None:
        rt = GovernedExecutionRuntime(
            work_readiness=_FakeReadiness(["w1", "w2"], [], ["w1", "w2"]),
            unified_approvals=_FakeApprovals(0),
        )
        s = rt.summary()
        assert s["ready_count"] == 2
        assert s["blocked_count"] == 0


# ── Canonical Type Registration ──────────────────────────────────────


class TestCanonicalTypes:
    def test_governed_execution_runtime_importable(self) -> None:
        from substrate.organism.governed_execution_runtime import GovernedExecutionRuntime
        rt = GovernedExecutionRuntime()
        assert rt is not None
