"""Integration tests for Campaign 16 — Governed Execution Loop.

Cross-runtime composition: GovernedExecution → OrganismState,
lifecycle arcs, executive brief integration, strategic context integration.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from typing import Any
from unittest.mock import MagicMock

from substrate.organism.governed_execution_runtime import (
    ExecutionState,
    GovernedExecutionRuntime,
)
from substrate.organism.organism_state_runtime import (
    OrganismMode,
    OrganismStateRuntime,
)
from substrate.organism.execution_lifecycle_runtime import (
    ExecutionLifecycleRuntime,
    LifecycleStage,
)


# ── Shared fakes ─────────────────────────────────────────────────────


class _FakeReadiness:
    def __init__(self, ready: list | None = None, blocked: list | None = None) -> None:
        self._ready = ready or []
        self._blocked = blocked or []

    def ready_work(self) -> list:
        return self._ready

    def blocked_work(self) -> list:
        return self._blocked

    def assess_all(self) -> list:
        return self._ready + self._blocked

    def summary(self) -> dict:
        return {"ready": len(self._ready), "blocked": len(self._blocked)}


class _FakeApprovals:
    def __init__(self, pending: int = 0) -> None:
        self._pending = pending

    def pending(self) -> list:
        return [{"approval_id": f"a-{i}"} for i in range(self._pending)]

    def snapshot(self) -> MagicMock:
        m = MagicMock()
        m.to_dict.return_value = {"pending_count": self._pending}
        return m


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
        return {}

    def summary(self) -> dict:
        return {"contentions": self._contentions}


class _FakePortfolio:
    def __init__(self, health: str = "coherent", coherence: float = 0.9) -> None:
        self._health = health
        self._coherence = coherence

    def health(self) -> MagicMock:
        m = MagicMock()
        m.value = self._health
        return m

    def coherence_score(self) -> float:
        return self._coherence

    def subsystem_health(self) -> list:
        return [
            type("E", (), {"health": self._health, "subsystem": f"sub-{i}"})()
            for i in range(8)
        ]

    def drift_warnings(self) -> list:
        return []


class _FakeBrief:
    def __init__(self, lessons: int = 0) -> None:
        self._lessons = lessons

    def generate(self) -> MagicMock:
        m = MagicMock()
        m.risks = []
        m.blockers = []
        m.drift_warnings = []
        m.recent_lessons = [f"lesson-{i}" for i in range(self._lessons)]
        return m


# ── Test 1: Full pipeline — GovernedExecution feeds OrganismState ────


def _ger(**overrides: Any) -> GovernedExecutionRuntime:
    """Build a GovernedExecutionRuntime with full fakes to avoid lazy-load hangs."""
    defaults: dict[str, Any] = {
        "work_readiness": _FakeReadiness([], []),
        "delegation_readiness": _FakeDelegation(0.0),
        "resource_allocation": _FakeAllocation("balanced"),
        "tradeoff_engine": _FakeTradeoff(0),
        "unified_approvals": _FakeApprovals(0),
    }
    defaults.update(overrides)
    return GovernedExecutionRuntime(**defaults)


class TestPipelineComposition:
    def test_executing_state_propagates_to_executing_mode(self) -> None:
        ger = _ger(
            work_readiness=_FakeReadiness(ready=["w1", "w2"]),
            delegation_readiness=_FakeDelegation(coverage=0.8),
        )
        assert ger.state() == ExecutionState.EXECUTING

        osr = OrganismStateRuntime(
            organism_portfolio=_FakePortfolio("coherent", 0.9),
            governed_execution=ger,
            executive_brief=_FakeBrief(lessons=0),
        )
        assert osr.mode() == OrganismMode.EXECUTING

    def test_idle_state_propagates_to_idle_mode(self) -> None:
        ger = _ger()
        assert ger.state() == ExecutionState.IDLE

        osr = OrganismStateRuntime(
            organism_portfolio=_FakePortfolio("coherent", 0.9),
            governed_execution=ger,
            executive_brief=_FakeBrief(lessons=0),
        )
        assert osr.mode() == OrganismMode.IDLE


# ── Test 2: Governance → execution → GOVERNING mode ─────────────────


class TestGovernanceToExecution:
    def test_pending_approvals_triggers_governing_mode(self) -> None:
        ger = _ger(
            work_readiness=_FakeReadiness(ready=["w1"]),
            unified_approvals=_FakeApprovals(pending=3),
        )
        assert ger.state() == ExecutionState.GOVERNED

        osr = OrganismStateRuntime(
            organism_portfolio=_FakePortfolio("coherent", 0.9),
            governed_execution=ger,
            executive_brief=_FakeBrief(lessons=0),
        )
        assert osr.mode() == OrganismMode.GOVERNING


# ── Test 3: Lifecycle retrospective ─────────────────────────────────


class TestLifecycleRetrospective:
    def test_completed_with_lessons_is_learning(self) -> None:
        lesson = MagicMock()
        lesson.goal_id = "g-1"
        lesson.to_dict = lambda: {"lesson": "test"}

        elr = ExecutionLifecycleRuntime(
            outcome_tracking=type("OT", (), {
                "snapshot": lambda self: type("S", (), {
                    "to_dict": lambda self: {"goals": [{"goal_id": "g-1"}]}
                })(),
                "completion": lambda self, gid: 1.0,
                "health": lambda self, gid: "healthy",
            })(),
            learning_extraction=type("LE", (), {
                "recent_lessons": lambda self, limit=10: [lesson],
            })(),
            outcome_patterns=type("OP", (), {
                "patterns_for_goal": lambda self, gid: [],
                "top_patterns": lambda self, limit=10: [],
            })(),
            capability_evolution=type("CE", (), {
                "advancing": lambda self: [],
                "declining": lambda self: [],
                "stalled": lambda self: [],
            })(),
        )
        arc = elr.arc("g-1")
        assert arc.stage == "learning"

    def test_compounded_with_capability_evolution(self) -> None:
        lesson = MagicMock()
        lesson.goal_id = "g-1"

        elr = ExecutionLifecycleRuntime(
            outcome_tracking=type("OT", (), {
                "snapshot": lambda self: type("S", (), {
                    "to_dict": lambda self: {"goals": [{"goal_id": "g-1"}]}
                })(),
                "completion": lambda self, gid: 1.0,
                "health": lambda self, gid: "healthy",
            })(),
            learning_extraction=type("LE", (), {
                "recent_lessons": lambda self, limit=10: [lesson],
            })(),
            outcome_patterns=type("OP", (), {
                "patterns_for_goal": lambda self, gid: ["p-1"],
                "top_patterns": lambda self, limit=10: ["p-1"],
            })(),
            capability_evolution=type("CE", (), {
                "advancing": lambda self: ["cap-1", "cap-2"],
                "declining": lambda self: [],
                "stalled": lambda self: [],
            })(),
        )
        arc = elr.arc("g-1")
        assert arc.stage == "compounded"
        assert arc.capabilities_evolved == 2


# ── Test 4: Blocked propagation ─────────────────────────────────────


class TestBlockedPropagation:
    def test_blocked_work_does_not_produce_executing_mode(self) -> None:
        ger = _ger(
            work_readiness=_FakeReadiness(ready=["w1"], blocked=["b1", "b2", "b3"]),
        )
        assert ger.state() == ExecutionState.BLOCKED

        osr = OrganismStateRuntime(
            organism_portfolio=_FakePortfolio("coherent", 0.9),
            governed_execution=ger,
            executive_brief=_FakeBrief(lessons=0),
        )
        assert osr.mode() != OrganismMode.EXECUTING


# ── Test 5: Degraded override ────────────────────────────────────────


class TestDegradedOverride:
    def test_critical_health_overrides_executing(self) -> None:
        ger = _ger(
            work_readiness=_FakeReadiness(ready=["w1", "w2"]),
            delegation_readiness=_FakeDelegation(coverage=0.8),
        )
        assert ger.state() == ExecutionState.EXECUTING

        osr = OrganismStateRuntime(
            organism_portfolio=_FakePortfolio("critical", 0.1),
            governed_execution=ger,
            executive_brief=_FakeBrief(lessons=0),
        )
        assert osr.mode() == OrganismMode.DEGRADED
        assert osr.is_degraded() is True

    def test_low_coherence_overrides_governing(self) -> None:
        ger = _ger(
            work_readiness=_FakeReadiness(ready=["w1"]),
            unified_approvals=_FakeApprovals(pending=2),
        )
        assert ger.state() == ExecutionState.GOVERNED

        osr = OrganismStateRuntime(
            organism_portfolio=_FakePortfolio("aligned", 0.2),
            governed_execution=ger,
            executive_brief=_FakeBrief(lessons=0),
        )
        assert osr.mode() == OrganismMode.DEGRADED


# ── Test 6: All three runtimes compose from nothing ──────────────────


class TestGracefulDegradation:
    def test_all_minimal_deps(self) -> None:
        ger = _ger()
        osr = OrganismStateRuntime(
            organism_portfolio=_FakePortfolio("coherent", 0.9),
            governed_execution=ger,
            executive_brief=_FakeBrief(lessons=0),
        )
        elr = ExecutionLifecycleRuntime()

        assert isinstance(ger.state(), ExecutionState)
        assert isinstance(osr.snapshot().to_dict(), dict)
        assert isinstance(elr.overall_stage(), LifecycleStage)


# ── Test 7: Snapshot serialization round-trip ────────────────────────


class TestSnapshotSerialization:
    def test_governed_execution_snapshot_keys(self) -> None:
        rt = _ger()
        d = rt.snapshot().to_dict()
        expected = {"state", "health", "assessment", "readiness_summary",
                    "delegation_summary", "allocation_summary",
                    "tradeoff_summary", "approval_summary", "generated_at"}
        assert expected.issubset(set(d.keys()))

    def test_organism_state_snapshot_keys(self) -> None:
        ger = _ger()
        rt = OrganismStateRuntime(
            organism_portfolio=_FakePortfolio("coherent", 0.9),
            governed_execution=ger,
            executive_brief=_FakeBrief(lessons=0),
        )
        d = rt.snapshot().to_dict()
        expected = {"mode", "health", "coherence_score", "execution_state",
                    "active_concerns", "subsystem_count", "healthy_subsystems",
                    "drift_count", "attention_items", "generated_at"}
        assert expected.issubset(set(d.keys()))

    def test_execution_lifecycle_snapshot_keys(self) -> None:
        rt = ExecutionLifecycleRuntime()
        d = rt.snapshot().to_dict()
        expected = {"arcs", "total_lessons", "total_patterns",
                    "advancing_capabilities", "declining_capabilities",
                    "overall_stage", "generated_at"}
        assert expected.issubset(set(d.keys()))
