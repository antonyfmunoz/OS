"""Tests for ExecutivePortfolioRuntime — Campaign 14.2."""
from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest
from substrate.organism.executive_portfolio_runtime import (
    ExecutiveDriftType,
    ExecutiveDriftWarning,
    ExecutiveHealth,
    ExecutivePortfolioRuntime,
    ExecutivePortfolioSnapshot,
)


# ── Fixtures ──────────────────────────────────────────────────────────


class FakeResourceAllocation:
    def __init__(self, health_val="balanced", overcommitted=None) -> None:
        self._health_val = health_val
        self._overcommitted = overcommitted or []

    def health(self):
        return type("H", (), {"value": self._health_val})()

    def summary(self) -> dict:
        return {"recommendation_count": 3, "allocation_health": self._health_val}

    def budgets(self) -> list:
        return [
            type("B", (), {"resource_type": "time", "overcommitted": "time" in self._overcommitted})(),
            type("B", (), {"resource_type": "attention", "overcommitted": "attention" in self._overcommitted})(),
            type("B", (), {"resource_type": "capital", "overcommitted": "capital" in self._overcommitted})(),
            type("B", (), {"resource_type": "capability_building", "overcommitted": False})(),
            type("B", (), {"resource_type": "execution_capacity", "overcommitted": False})(),
        ]

    def top_leverage(self, limit: int = 5) -> list:
        return [
            type("R", (), {
                "target_id": "goal-1", "target_name": "Revenue", "priority": "high",
                "leverage_score": 0.8, "rationale": "at-risk trajectory",
                "to_dict": lambda self: {"target_id": "goal-1", "target_name": "Revenue",
                                          "priority": "high", "leverage_score": 0.8},
            })(),
        ]

    def unallocated_goals(self) -> list:
        return []


class FakeResourceAllocationWithUnallocated(FakeResourceAllocation):
    def unallocated_goals(self) -> list:
        return ["goal-4", "goal-5", "goal-6", "goal-7"]


class FakeTradeoffEngine:
    def __init__(self, severity="negligible") -> None:
        self._severity = severity

    def snapshot(self):
        return type("S", (), {"overall_severity": self._severity})()

    def contention_map(self) -> dict:
        return {"time": ["goal-1", "goal-2", "goal-3"]}


class FakeWorkPortfolio:
    def health(self):
        return type("H", (), {"value": "healthy"})()

    def snapshot(self):
        return type("S", (), {
            "to_dict": lambda self: {"block_rate": 0.1}
        })()


class FakePredictionPortfolio:
    def health(self):
        return type("H", (), {"value": "stable"})()

    def drift_warnings(self) -> list:
        return []


class FakePredictionPortfolioWithDrift:
    def health(self):
        return type("H", (), {"value": "volatile"})()

    def drift_warnings(self) -> list:
        return [
            type("W", (), {
                "drift_type": "forecast_decay", "affected_ids": ["goal-drift-1"],
            })(),
        ]


class FakeLearningPortfolio:
    def health(self):
        return type("H", (), {"value": "healthy"})()


class FakeDecisionImpact:
    def summary(self) -> dict:
        return {"total_decisions": 5, "valid_decisions": 4, "at_risk_count": 1, "invalid_count": 0}


class FakeDecisionImpactStale:
    def summary(self) -> dict:
        return {"total_decisions": 5, "valid_decisions": 2, "at_risk_count": 4, "invalid_count": 1}


class FakeCapabilityGap:
    def gap_summary(self) -> dict:
        return {"critical_gap_count": 1, "total_gap_count": 3}


class FakeGoalAlignment:
    def alignment_score(self) -> float:
        return 0.7


class FakeStrategicPlanning:
    def __init__(self, goal_count: int = 3) -> None:
        self._goals = {f"goal-{i}": {} for i in range(goal_count)}

    def roadmap(self) -> dict:
        return self._goals


# ── Type tests ────────────────────────────────────────────────────────


class TestExecutiveHealth:
    def test_all_values(self) -> None:
        assert len(ExecutiveHealth) == 5
        assert "optimized" in [h.value for h in ExecutiveHealth]
        assert "critical" in [h.value for h in ExecutiveHealth]


class TestExecutiveDriftType:
    def test_all_values(self) -> None:
        assert len(ExecutiveDriftType) == 5
        assert "allocation_drift" in [d.value for d in ExecutiveDriftType]
        assert "prediction_ignorance" in [d.value for d in ExecutiveDriftType]


class TestExecutiveDriftWarning:
    def test_defaults(self) -> None:
        w = ExecutiveDriftWarning()
        assert w.drift_type == "allocation_drift"
        assert w.severity == "low"
        assert w.affected_ids == []

    def test_to_dict(self) -> None:
        w = ExecutiveDriftWarning(
            drift_type="strategic_scatter",
            severity="critical",
            description="test scatter",
            recommendation="reduce goals",
        )
        d = w.to_dict()
        assert d["drift_type"] == "strategic_scatter"
        assert d["severity"] == "critical"


class TestExecutivePortfolioSnapshot:
    def test_defaults(self) -> None:
        s = ExecutivePortfolioSnapshot()
        assert s.executive_health == "focused"
        assert s.focus_score == 0.5
        assert s.overcommitment_index == 0.0

    def test_to_dict(self) -> None:
        s = ExecutivePortfolioSnapshot(
            focus_score=0.73456,
            overcommitment_index=0.25678,
        )
        d = s.to_dict()
        assert d["focus_score"] == 0.7346
        assert d["overcommitment_index"] == 0.2568


# ── Runtime tests ─────────────────────────────────────────────────────


class TestExecutivePortfolioRuntime:
    def _make_runtime(self, **overrides) -> ExecutivePortfolioRuntime:
        defaults = {
            "resource_allocation": FakeResourceAllocation(),
            "tradeoff_engine": FakeTradeoffEngine(),
            "work_portfolio": FakeWorkPortfolio(),
            "prediction_portfolio": FakePredictionPortfolio(),
            "learning_portfolio": FakeLearningPortfolio(),
            "decision_impact": FakeDecisionImpact(),
            "capability_gap": FakeCapabilityGap(),
            "goal_alignment": FakeGoalAlignment(),
            "strategic_planning": FakeStrategicPlanning(),
        }
        defaults.update(overrides)
        return ExecutivePortfolioRuntime(**defaults)

    def test_instantiation(self) -> None:
        rt = self._make_runtime()
        assert rt is not None

    def test_health(self) -> None:
        rt = self._make_runtime()
        h = rt.health()
        assert isinstance(h, ExecutiveHealth)
        assert h.value in [v.value for v in ExecutiveHealth]

    def test_focus_score(self) -> None:
        rt = self._make_runtime()
        fs = rt.focus_score()
        assert isinstance(fs, float)
        assert 0.0 <= fs <= 1.0

    def test_focus_high_with_few_goals(self) -> None:
        rt = self._make_runtime(strategic_planning=FakeStrategicPlanning(goal_count=2))
        fs = rt.focus_score()
        assert fs >= 0.7

    def test_focus_low_with_many_goals(self) -> None:
        rt = self._make_runtime(strategic_planning=FakeStrategicPlanning(goal_count=15))
        fs = rt.focus_score()
        assert fs < 0.5

    def test_overcommitment_index(self) -> None:
        rt = self._make_runtime()
        oi = rt.overcommitment_index()
        assert isinstance(oi, float)
        assert 0.0 <= oi <= 1.0

    def test_overcommitment_increases_with_overcommitted_budgets(self) -> None:
        rt_low = self._make_runtime()
        rt_high = self._make_runtime(
            resource_allocation=FakeResourceAllocation(overcommitted=["time", "attention", "capital"])
        )
        assert rt_high.overcommitment_index() > rt_low.overcommitment_index()

    def test_drift_warnings(self) -> None:
        rt = self._make_runtime()
        warnings = rt.drift_warnings()
        assert isinstance(warnings, list)
        for w in warnings:
            assert isinstance(w, ExecutiveDriftWarning)

    def test_allocation_drift_detected(self) -> None:
        rt = self._make_runtime(
            resource_allocation=FakeResourceAllocationWithUnallocated()
        )
        warnings = rt.drift_warnings()
        types = [w.drift_type for w in warnings]
        assert "allocation_drift" in types

    def test_tradeoff_blindness_detected(self) -> None:
        rt = self._make_runtime()
        warnings = rt.drift_warnings()
        types = [w.drift_type for w in warnings]
        assert "tradeoff_blindness" in types

    def test_strategic_scatter_detected(self) -> None:
        rt = self._make_runtime(strategic_planning=FakeStrategicPlanning(goal_count=15))
        warnings = rt.drift_warnings()
        types = [w.drift_type for w in warnings]
        assert "strategic_scatter" in types

    def test_decision_staleness_detected(self) -> None:
        rt = self._make_runtime(decision_impact=FakeDecisionImpactStale())
        warnings = rt.drift_warnings()
        types = [w.drift_type for w in warnings]
        assert "decision_staleness" in types

    def test_prediction_ignorance_detected(self) -> None:
        rt = self._make_runtime(
            prediction_portfolio=FakePredictionPortfolioWithDrift()
        )
        warnings = rt.drift_warnings()
        types = [w.drift_type for w in warnings]
        assert "prediction_ignorance" in types

    def test_top_recommendations(self) -> None:
        rt = self._make_runtime()
        recs = rt.top_recommendations(limit=3)
        assert isinstance(recs, list)

    def test_snapshot(self) -> None:
        rt = self._make_runtime()
        snap = rt.snapshot()
        assert isinstance(snap, ExecutivePortfolioSnapshot)
        assert snap.executive_health in [h.value for h in ExecutiveHealth]
        assert snap.generated_at > 0.0

    def test_snapshot_to_dict(self) -> None:
        rt = self._make_runtime()
        snap = rt.snapshot()
        d = snap.to_dict()
        assert isinstance(d, dict)
        assert "executive_health" in d
        assert "focus_score" in d
        assert "overcommitment_index" in d

    def test_summary(self) -> None:
        rt = self._make_runtime()
        s = rt.summary()
        assert isinstance(s, dict)
        assert "executive_health" in s
        assert "focus_score" in s
        assert "overcommitment_index" in s
        assert "drift_count" in s
        assert "subsystem_health" in s

    def test_no_deps_health(self) -> None:
        rt = ExecutivePortfolioRuntime()
        h = rt.health()
        assert isinstance(h, ExecutiveHealth)

    def test_no_deps_focus(self) -> None:
        rt = ExecutivePortfolioRuntime()
        fs = rt.focus_score()
        assert isinstance(fs, float)
        assert 0.0 <= fs <= 1.0

    def test_no_deps_snapshot(self) -> None:
        rt = ExecutivePortfolioRuntime()
        snap = rt.snapshot()
        assert isinstance(snap, ExecutivePortfolioSnapshot)

    def test_no_mutation_methods(self) -> None:
        rt = self._make_runtime()
        assert not hasattr(rt, "execute")
        assert not hasattr(rt, "approve")
        assert not hasattr(rt, "mutate")

    def test_health_optimized_conditions(self) -> None:
        rt = self._make_runtime(
            strategic_planning=FakeStrategicPlanning(goal_count=2),
            resource_allocation=FakeResourceAllocation(health_val="optimized"),
            tradeoff_engine=FakeTradeoffEngine(severity="negligible"),
        )
        h = rt.health()
        assert h in (ExecutiveHealth.OPTIMIZED, ExecutiveHealth.FOCUSED)

    def test_health_critical_conditions(self) -> None:
        rt = self._make_runtime(
            strategic_planning=FakeStrategicPlanning(goal_count=15),
            resource_allocation=FakeResourceAllocation(
                overcommitted=["time", "attention", "capital", "capability_building"]
            ),
        )
        h = rt.health()
        assert h in (ExecutiveHealth.OVERCOMMITTED, ExecutiveHealth.CRITICAL)
