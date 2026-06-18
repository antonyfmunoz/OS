"""Tests for TradeoffIntelligenceEngine — Campaign 14.1."""
from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest
from substrate.organism.tradeoff_intelligence_engine import (
    TradeoffAnalysis,
    TradeoffIntelligenceEngine,
    TradeoffOption,
    TradeoffSeverity,
    TradeoffSnapshot,
)


# ── Fixtures ──────────────────────────────────────────────────────────


class FakeAllocationRecommendation:
    def __init__(self, target_id: str, target_name: str, leverage: float, rationale: str = "") -> None:
        self.recommendation_id = f"rec-{target_id}"
        self.resource_type = "time"
        self.target_id = target_id
        self.target_name = target_name
        self.target_type = "goal"
        self.priority = "medium"
        self.leverage_score = leverage
        self.allocation_confidence = 0.6
        self.rationale = rationale
        self.competing_targets = []
        self.source_signals = []
        self.generated_at = 1.0


class FakeResourceAllocation:
    def __init__(self, recs=None) -> None:
        self._recs = recs or [
            FakeAllocationRecommendation("goal-1", "Revenue Target", 0.8),
            FakeAllocationRecommendation("goal-2", "Content Pipeline", 0.5),
            FakeAllocationRecommendation("goal-3", "Infrastructure", 0.3),
        ]

    def recommend_all(self) -> list:
        return self._recs

    def budgets(self) -> list:
        return []


class FakeStrategicPlanning:
    def roadmap(self) -> dict:
        return {
            "goal-1": {"status": "active"},
            "goal-2": {"status": "active"},
            "goal-3": {"status": "active"},
        }


class FakeGoalAlignment:
    def coverage(self) -> dict:
        return {"goal-1": 3, "goal-2": 1, "goal-3": 0}

    def orphan_goals(self) -> list:
        return []


class FakeWorkPortfolio:
    def velocity(self) -> dict:
        return {"completions_per_day": 2.0}

    def at_risk_work(self) -> list:
        return []


class FakeCapabilityGap:
    def analyze_gaps(self) -> list:
        return [1, 2]

    def critical_gaps(self) -> list:
        return [1]


class FakePredictionPortfolio:
    def highest_risk_forecasts(self, limit: int = 10) -> list:
        return [
            type("F", (), {"entity_id": "goal-2", "status": "declining"})(),
        ]


# ── Type tests ────────────────────────────────────────────────────────


class TestTradeoffSeverity:
    def test_all_values(self) -> None:
        assert len(TradeoffSeverity) == 5
        assert "negligible" in [s.value for s in TradeoffSeverity]
        assert "critical" in [s.value for s in TradeoffSeverity]


class TestTradeoffOption:
    def test_defaults(self) -> None:
        o = TradeoffOption()
        assert o.option_id == ""
        assert o.resource_cost == {}
        assert o.leverage_score == 0.0

    def test_to_dict(self) -> None:
        o = TradeoffOption(
            option_id="opt-1",
            target_id="goal-1",
            leverage_score=0.73456,
            resource_cost={"time": 0.33333},
        )
        d = o.to_dict()
        assert d["leverage_score"] == 0.7346
        assert d["resource_cost"]["time"] == 0.3333


class TestTradeoffAnalysis:
    def test_defaults(self) -> None:
        a = TradeoffAnalysis()
        assert a.severity == "negligible"
        assert a.recommendation == "proceed"
        assert a.displaced == []

    def test_to_dict(self) -> None:
        a = TradeoffAnalysis(
            analysis_id="a-1",
            severity="major",
            recommendation="reconsider",
            leverage_delta=0.25678,
        )
        d = a.to_dict()
        assert d["severity"] == "major"
        assert d["leverage_delta"] == 0.2568


class TestTradeoffSnapshot:
    def test_defaults(self) -> None:
        s = TradeoffSnapshot()
        assert s.overall_severity == "negligible"
        assert s.active_tradeoffs == []

    def test_to_dict(self) -> None:
        s = TradeoffSnapshot(overall_severity="significant")
        d = s.to_dict()
        assert d["overall_severity"] == "significant"


# ── Runtime tests ─────────────────────────────────────────────────────


class TestTradeoffIntelligenceEngine:
    def _make_engine(self) -> TradeoffIntelligenceEngine:
        return TradeoffIntelligenceEngine(
            resource_allocation=FakeResourceAllocation(),
            strategic_planning=FakeStrategicPlanning(),
            goal_alignment=FakeGoalAlignment(),
            work_portfolio=FakeWorkPortfolio(),
            capability_gap=FakeCapabilityGap(),
            prediction_portfolio=FakePredictionPortfolio(),
        )

    def test_instantiation(self) -> None:
        e = self._make_engine()
        assert e is not None

    def test_analyze_known_target(self) -> None:
        e = self._make_engine()
        a = e.analyze("goal-1")
        assert isinstance(a, TradeoffAnalysis)
        assert a.analysis_id != ""
        assert a.severity in [s.value for s in TradeoffSeverity]
        assert a.recommendation in ("proceed", "reconsider", "defer")

    def test_analyze_unknown_target(self) -> None:
        e = self._make_engine()
        a = e.analyze("nonexistent")
        assert isinstance(a, TradeoffAnalysis)
        assert "not found" in a.rationale

    def test_analyze_has_source_signals(self) -> None:
        e = self._make_engine()
        a = e.analyze("goal-1")
        assert isinstance(a.source_signals, list)
        assert len(a.source_signals) > 0

    def test_analyze_pair(self) -> None:
        e = self._make_engine()
        result = e.analyze_pair("goal-1", "goal-2")
        assert isinstance(result, dict)
        assert "preferred" in result
        assert "reason" in result
        assert "target_a" in result
        assert "target_b" in result

    def test_analyze_pair_prefers_higher_leverage(self) -> None:
        e = self._make_engine()
        result = e.analyze_pair("goal-1", "goal-3")
        assert result["preferred"] in ("goal-1", "goal-3")

    def test_contention_map(self) -> None:
        e = self._make_engine()
        cm = e.contention_map()
        assert isinstance(cm, dict)
        for resource, targets in cm.items():
            assert isinstance(targets, list)
            assert len(targets) >= 2

    def test_highest_cost_targets(self) -> None:
        e = self._make_engine()
        top = e.highest_cost_targets(limit=2)
        assert isinstance(top, list)
        assert len(top) <= 2
        for t in top:
            assert isinstance(t, dict)
            assert "total_cost" in t

    def test_lowest_cost_targets(self) -> None:
        e = self._make_engine()
        low = e.lowest_cost_targets(limit=2)
        assert isinstance(low, list)
        assert len(low) <= 2

    def test_cost_ordering(self) -> None:
        e = self._make_engine()
        high = e.highest_cost_targets(limit=10)
        low = e.lowest_cost_targets(limit=10)
        if len(high) >= 2:
            assert high[0]["total_cost"] >= high[-1]["total_cost"]
        if len(low) >= 2:
            assert low[0]["total_cost"] <= low[-1]["total_cost"]

    def test_snapshot(self) -> None:
        e = self._make_engine()
        snap = e.snapshot()
        assert isinstance(snap, TradeoffSnapshot)
        assert snap.overall_severity in [s.value for s in TradeoffSeverity]
        assert snap.generated_at > 0.0

    def test_snapshot_to_dict(self) -> None:
        e = self._make_engine()
        snap = e.snapshot()
        d = snap.to_dict()
        assert isinstance(d, dict)
        assert "overall_severity" in d
        assert "resource_contention" in d

    def test_summary(self) -> None:
        e = self._make_engine()
        s = e.summary()
        assert isinstance(s, dict)
        assert "total_targets" in s
        assert "contention_resource_count" in s
        assert s["total_targets"] == 3

    def test_no_deps_analyze(self) -> None:
        e = TradeoffIntelligenceEngine()
        a = e.analyze("goal-1")
        assert isinstance(a, TradeoffAnalysis)
        assert "not found" in a.rationale

    def test_no_deps_contention(self) -> None:
        e = TradeoffIntelligenceEngine()
        cm = e.contention_map()
        assert isinstance(cm, dict)

    def test_no_mutation_methods(self) -> None:
        e = self._make_engine()
        assert not hasattr(e, "execute")
        assert not hasattr(e, "approve")
        assert not hasattr(e, "mutate")

    def test_severity_classification(self) -> None:
        e = self._make_engine()
        s = e._classify_severity(0.7, 0.5)
        assert s == TradeoffSeverity.CRITICAL
        s = e._classify_severity(0.0, 0.0)
        assert s == TradeoffSeverity.NEGLIGIBLE
        s = e._classify_severity(0.3, 0.1)
        assert s in (TradeoffSeverity.SIGNIFICANT, TradeoffSeverity.MAJOR)

    def test_recommendation_classification(self) -> None:
        e = self._make_engine()
        assert e._classify_recommendation(TradeoffSeverity.CRITICAL, -0.5) == "defer"
        assert e._classify_recommendation(TradeoffSeverity.CRITICAL, 0.5) == "reconsider"
        assert e._classify_recommendation(TradeoffSeverity.NEGLIGIBLE, 0.0) == "proceed"
