"""Tests for ResourceAllocationRuntime — Campaign 14.0."""
from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest
from substrate.organism.resource_allocation_runtime import (
    AllocationHealth,
    AllocationPriority,
    AllocationRecommendation,
    AllocationSnapshot,
    ResourceAllocationRuntime,
    ResourceBudget,
    ResourceType,
)


# ── Fixtures ──────────────────────────────────────────────────────────


class FakeStrategicPlanning:
    def __init__(self, goals=None) -> None:
        self._goals = goals or {
            "goal-1": {"status": "active"},
            "goal-2": {"status": "active"},
            "goal-3": {"status": "active"},
        }

    def roadmap(self) -> dict:
        return self._goals

    def status(self, goal_id: str) -> dict:
        return self._goals.get(goal_id, {})


class FakeGoalAlignment:
    def alignment_score(self) -> float:
        return 0.7

    def coverage(self) -> dict:
        return {"goal-1": 3, "goal-2": 1, "goal-3": 0}

    def orphan_goals(self) -> list:
        return ["goal-orphan"]

    def report(self) -> dict:
        return {"aligned": 2, "orphaned": 1}


class FakeCapabilityGap:
    def analyze_gaps(self) -> list:
        return [1, 2, 3, 4, 5]

    def critical_gaps(self) -> list:
        return [1, 2]

    def next_to_build(self, limit: int = 5) -> list:
        return [{"name": "gap-1"}]


class FakeWorkPortfolio:
    def health(self):
        return type("H", (), {"value": "healthy"})()

    def velocity(self) -> dict:
        return {"completions_per_day": 2.5, "trend": "stable"}

    def at_risk_work(self) -> list:
        return ["work-1"]

    def snapshot(self):
        return type("S", (), {
            "to_dict": lambda self: {"block_rate": 0.1, "active_count": 5}
        })()


class FakePredictionPortfolio:
    def snapshot(self):
        return type("S", (), {
            "to_dict": lambda self: {"average_confidence": 0.6, "uncertainty_index": 0.4}
        })()

    def highest_risk_forecasts(self, limit: int = 10) -> list:
        return [
            type("F", (), {"entity_id": "goal-2", "status": "declining"})(),
        ]

    def health(self):
        return type("H", (), {"value": "stable"})()


class FakeLearningPortfolio:
    def compounding_score(self) -> float:
        return 0.55

    def health(self):
        return type("H", (), {"value": "healthy"})()


class FakeDecisionImpact:
    def assess(self, decision_id: str):
        return {"decision_id": decision_id}

    def highest_impact(self, limit: int = 10) -> list:
        return [1, 2, 3]

    def summary(self) -> dict:
        return {"total_decisions": 5, "valid_decisions": 4, "at_risk_count": 1, "invalid_count": 0}


# ── Type tests ────────────────────────────────────────────────────────


class TestResourceType:
    def test_all_values(self) -> None:
        assert len(ResourceType) == 5
        assert "time" in [r.value for r in ResourceType]
        assert "execution_capacity" in [r.value for r in ResourceType]


class TestAllocationPriority:
    def test_all_values(self) -> None:
        assert len(AllocationPriority) == 5
        assert "critical" in [p.value for p in AllocationPriority]
        assert "defer" in [p.value for p in AllocationPriority]


class TestAllocationHealth:
    def test_all_values(self) -> None:
        assert len(AllocationHealth) == 5
        assert "optimized" in [h.value for h in AllocationHealth]
        assert "critical" in [h.value for h in AllocationHealth]


class TestAllocationRecommendation:
    def test_defaults(self) -> None:
        r = AllocationRecommendation()
        assert r.recommendation_id == ""
        assert r.leverage_score == 0.0
        assert r.allocation_confidence == 0.0
        assert r.competing_targets == []
        assert r.source_signals == []

    def test_to_dict(self) -> None:
        r = AllocationRecommendation(
            recommendation_id="rec-1",
            target_id="goal-1",
            leverage_score=0.73456,
            allocation_confidence=0.55123,
        )
        d = r.to_dict()
        assert d["recommendation_id"] == "rec-1"
        assert d["leverage_score"] == 0.7346
        assert d["allocation_confidence"] == 0.5512


class TestResourceBudget:
    def test_defaults(self) -> None:
        b = ResourceBudget()
        assert b.total_capacity == 1.0
        assert b.available == 1.0
        assert b.overcommitted is False

    def test_to_dict(self) -> None:
        b = ResourceBudget(
            resource_type="attention",
            allocated=0.73456,
            available=0.26544,
            overcommitted=True,
        )
        d = b.to_dict()
        assert d["allocated"] == 0.7346
        assert d["overcommitted"] is True


class TestAllocationSnapshot:
    def test_defaults(self) -> None:
        s = AllocationSnapshot()
        assert s.recommendations == []
        assert s.allocation_health == "balanced"

    def test_to_dict(self) -> None:
        s = AllocationSnapshot(allocation_health="optimized")
        d = s.to_dict()
        assert d["allocation_health"] == "optimized"


# ── Runtime tests ─────────────────────────────────────────────────────


class TestResourceAllocationRuntime:
    def _make_runtime(self) -> ResourceAllocationRuntime:
        return ResourceAllocationRuntime(
            strategic_planning=FakeStrategicPlanning(),
            goal_alignment=FakeGoalAlignment(),
            capability_gap=FakeCapabilityGap(),
            work_portfolio=FakeWorkPortfolio(),
            prediction_portfolio=FakePredictionPortfolio(),
            learning_portfolio=FakeLearningPortfolio(),
            decision_impact=FakeDecisionImpact(),
        )

    def test_instantiation(self) -> None:
        rt = self._make_runtime()
        assert rt is not None

    def test_recommend_all(self) -> None:
        rt = self._make_runtime()
        recs = rt.recommend_all()
        assert isinstance(recs, list)
        assert len(recs) == 3
        for r in recs:
            assert isinstance(r, AllocationRecommendation)
            assert r.target_id != ""
            assert r.leverage_score > 0.0
            assert r.allocation_confidence > 0.0

    def test_recommendations_sorted_by_leverage(self) -> None:
        rt = self._make_runtime()
        recs = rt.recommend_all()
        if len(recs) >= 2:
            assert recs[0].leverage_score >= recs[1].leverage_score

    def test_recommend_by_type(self) -> None:
        rt = self._make_runtime()
        recs = rt.recommend(resource_type="time")
        assert isinstance(recs, list)

    def test_top_leverage(self) -> None:
        rt = self._make_runtime()
        top = rt.top_leverage(limit=2)
        assert len(top) <= 2

    def test_budgets(self) -> None:
        rt = self._make_runtime()
        budgets = rt.budgets()
        assert isinstance(budgets, list)
        assert len(budgets) == 5
        types = {b.resource_type for b in budgets}
        assert "time" in types
        assert "attention" in types
        assert "execution_capacity" in types

    def test_health(self) -> None:
        rt = self._make_runtime()
        h = rt.health()
        assert isinstance(h, AllocationHealth)
        assert h.value in [v.value for v in AllocationHealth]

    def test_snapshot(self) -> None:
        rt = self._make_runtime()
        snap = rt.snapshot()
        assert isinstance(snap, AllocationSnapshot)
        assert snap.allocation_health in [h.value for h in AllocationHealth]
        assert snap.generated_at > 0.0

    def test_snapshot_to_dict(self) -> None:
        rt = self._make_runtime()
        snap = rt.snapshot()
        d = snap.to_dict()
        assert isinstance(d, dict)
        assert "allocation_health" in d
        assert "recommendations" in d

    def test_summary(self) -> None:
        rt = self._make_runtime()
        s = rt.summary()
        assert isinstance(s, dict)
        assert "recommendation_count" in s
        assert "allocation_health" in s
        assert "average_confidence" in s
        assert s["recommendation_count"] == 3

    def test_unallocated_goals(self) -> None:
        rt = self._make_runtime()
        unalloc = rt.unallocated_goals()
        assert isinstance(unalloc, list)

    def test_allocation_confidence_bounded(self) -> None:
        rt = self._make_runtime()
        recs = rt.recommend_all()
        for r in recs:
            assert 0.0 <= r.allocation_confidence <= 1.0

    def test_leverage_score_bounded(self) -> None:
        rt = self._make_runtime()
        recs = rt.recommend_all()
        for r in recs:
            assert 0.0 <= r.leverage_score <= 1.0

    def test_at_risk_goal_gets_higher_priority(self) -> None:
        rt = self._make_runtime()
        recs = rt.recommend_all()
        risk_rec = next((r for r in recs if r.target_id == "goal-2"), None)
        if risk_rec:
            assert risk_rec.rationale and "at-risk" in risk_rec.rationale

    def test_source_signals_populated(self) -> None:
        rt = self._make_runtime()
        recs = rt.recommend_all()
        for r in recs:
            assert isinstance(r.source_signals, list)
            assert len(r.source_signals) > 0

    def test_no_deps_health(self) -> None:
        rt = ResourceAllocationRuntime()
        h = rt.health()
        assert isinstance(h, AllocationHealth)

    def test_no_deps_recommend(self) -> None:
        rt = ResourceAllocationRuntime()
        recs = rt.recommend_all()
        assert isinstance(recs, list)
        assert len(recs) == 0

    def test_no_deps_budgets(self) -> None:
        rt = ResourceAllocationRuntime()
        budgets = rt.budgets()
        assert isinstance(budgets, list)
        assert len(budgets) == 5

    def test_no_mutation_methods(self) -> None:
        rt = self._make_runtime()
        assert not hasattr(rt, "execute")
        assert not hasattr(rt, "approve")
        assert not hasattr(rt, "mutate")

    def test_many_goals_overcommitted(self) -> None:
        goals = {f"goal-{i}": {"status": "active"} for i in range(12)}
        rt = ResourceAllocationRuntime(
            strategic_planning=FakeStrategicPlanning(goals),
            goal_alignment=FakeGoalAlignment(),
            capability_gap=FakeCapabilityGap(),
            work_portfolio=FakeWorkPortfolio(),
            prediction_portfolio=FakePredictionPortfolio(),
            learning_portfolio=FakeLearningPortfolio(),
            decision_impact=FakeDecisionImpact(),
        )
        budgets = rt.budgets()
        time_budget = next(b for b in budgets if b.resource_type == "time")
        assert time_budget.overcommitted is True

    def test_competing_targets_populated(self) -> None:
        rt = self._make_runtime()
        recs = rt.recommend_all()
        for r in recs:
            assert isinstance(r.competing_targets, list)
