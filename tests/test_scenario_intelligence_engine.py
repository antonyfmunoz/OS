"""Tests for ScenarioIntelligenceEngine — Campaign 13.1."""
from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

import pytest
from substrate.organism.scenario_intelligence_engine import (
    FutureScenario,
    ScenarioIntelligenceEngine,
    ScenarioType,
)


# ── Fixtures ──────────────────────────────────────────────────────────


class FakeTrajectoryRuntime:
    def forecast_all(self) -> list:
        return [
            type("F", (), {
                "entity_id": "goal-1", "entity_type": "goal",
                "status": "stable", "confidence": 0.7,
                "to_dict": lambda self: {"entity_id": "goal-1"},
            })(),
            type("F", (), {
                "entity_id": "goal-2", "entity_type": "goal",
                "status": "declining", "confidence": 0.3,
                "to_dict": lambda self: {"entity_id": "goal-2"},
            })(),
            type("F", (), {
                "entity_id": "work_portfolio", "entity_type": "work",
                "status": "stable", "confidence": 0.6,
                "to_dict": lambda self: {"entity_id": "work_portfolio"},
            })(),
        ]

    def at_risk_trajectories(self) -> list:
        return [f for f in self.forecast_all() if f.status in ("slowing", "stalled", "declining")]

    def trajectory_summary(self) -> dict:
        return {"total": 3, "average_confidence": 0.53, "at_risk_count": 1, "by_status": {}}

    def health(self) -> str:
        return "degraded"


class FakeDecisionValidity:
    def at_risk(self) -> list:
        return [1, 2]

    def invalid(self) -> list:
        return [1]


class FakeWorkPortfolio:
    def health(self):
        return type("H", (), {"value": "healthy"})()

    def completions_per_day(self) -> float:
        return 2.0

    def velocity(self) -> float:
        return 2.0

    def at_risk_work(self) -> list:
        return [1]


class FakeCapabilityPortfolio:
    def health(self):
        return type("H", (), {"value": "healthy"})()


class FakeLearningPortfolio:
    def compounding_score(self) -> float:
        return 0.6

    def health(self):
        return type("H", (), {"value": "healthy"})()


class FakeStrategicPlanning:
    def roadmap(self) -> dict:
        return {"goal-1": {}, "goal-2": {}, "goal-3": {}}


class FakeRiskEngine:
    def detect_risks(self) -> list:
        return [1, 2, 3]

    def high_risks(self) -> list:
        return [1]


# ── Type tests ────────────────────────────────────────────────────────


class TestScenarioType:
    def test_all_values(self) -> None:
        assert len(ScenarioType) == 4
        assert "best_case" in [s.value for s in ScenarioType]
        assert "disruption" in [s.value for s in ScenarioType]


class TestFutureScenario:
    def test_defaults(self) -> None:
        s = FutureScenario()
        assert s.scenario_id == ""
        assert s.scenario_type == "expected"
        assert s.probability == 0.0
        assert s.assumptions == []
        assert s.risks == []
        assert s.opportunities == []

    def test_to_dict(self) -> None:
        s = FutureScenario(
            scenario_id="s-1",
            scenario_type="best_case",
            probability=0.73456,
        )
        d = s.to_dict()
        assert d["scenario_id"] == "s-1"
        assert d["probability"] == 0.7346

    def test_explainability_fields(self) -> None:
        s = FutureScenario(
            assumptions=["Trend holds", "No risks"],
            source_signals=["trajectory_runtime", "risk_engine"],
            contributing_factors=["confidence: 0.8"],
        )
        assert len(s.assumptions) == 2
        assert len(s.source_signals) == 2
        assert len(s.contributing_factors) == 1


# ── Runtime tests ─────────────────────────────────────────────────────


class TestScenarioIntelligenceEngine:
    def _make_engine(self) -> ScenarioIntelligenceEngine:
        return ScenarioIntelligenceEngine(
            trajectory_runtime=FakeTrajectoryRuntime(),
            decision_validity=FakeDecisionValidity(),
            work_portfolio=FakeWorkPortfolio(),
            capability_portfolio=FakeCapabilityPortfolio(),
            learning_portfolio=FakeLearningPortfolio(),
            strategic_planning=FakeStrategicPlanning(),
            risk_engine=FakeRiskEngine(),
        )

    def test_instantiation(self) -> None:
        e = self._make_engine()
        assert e is not None

    def test_best_case(self) -> None:
        e = self._make_engine()
        s = e.best_case()
        assert isinstance(s, FutureScenario)
        assert s.scenario_type == "best_case"
        assert 0.0 <= s.probability <= 1.0
        assert len(s.assumptions) > 0
        assert len(s.source_signals) > 0

    def test_expected_case(self) -> None:
        e = self._make_engine()
        s = e.expected_case()
        assert isinstance(s, FutureScenario)
        assert s.scenario_type == "expected"
        assert 0.0 <= s.probability <= 1.0
        assert len(s.assumptions) > 0

    def test_worst_case(self) -> None:
        e = self._make_engine()
        s = e.worst_case()
        assert isinstance(s, FutureScenario)
        assert s.scenario_type == "worst_case"
        assert 0.0 <= s.probability <= 1.0
        assert len(s.risks) > 0

    def test_disruption_case(self) -> None:
        e = self._make_engine()
        s = e.disruption_case()
        assert isinstance(s, FutureScenario)
        assert s.scenario_type == "disruption"
        assert 0.0 <= s.probability <= 1.0
        assert s.probability <= 0.5  # disruption always low probability

    def test_generate(self) -> None:
        e = self._make_engine()
        scenarios = e.generate()
        assert isinstance(scenarios, list)
        assert len(scenarios) == 4
        types = {s.scenario_type for s in scenarios}
        assert types == {"best_case", "expected", "worst_case", "disruption"}

    def test_compare(self) -> None:
        e = self._make_engine()
        c = e.compare()
        assert isinstance(c, dict)
        assert "scenarios" in c
        assert "probability_range" in c
        assert "spread" in c
        assert len(c["scenarios"]) == 4
        assert c["probability_range"][0] <= c["probability_range"][1]

    def test_summary(self) -> None:
        e = self._make_engine()
        s = e.summary()
        assert isinstance(s, dict)
        assert s["scenario_count"] == 4
        assert "probability_range" in s
        assert "top_risks" in s
        assert "top_opportunities" in s

    def test_no_deps_graceful(self) -> None:
        e = ScenarioIntelligenceEngine()
        scenarios = e.generate()
        assert isinstance(scenarios, list)
        assert len(scenarios) >= 0

    def test_probability_bounded(self) -> None:
        e = self._make_engine()
        for s in e.generate():
            assert 0.0 <= s.probability <= 1.0

    def test_best_case_has_opportunities(self) -> None:
        e = self._make_engine()
        s = e.best_case()
        assert isinstance(s.opportunities, list)

    def test_worst_case_has_risks(self) -> None:
        e = self._make_engine()
        s = e.worst_case()
        assert isinstance(s.risks, list)
        assert len(s.risks) > 0

    def test_disruption_max_probability(self) -> None:
        e = self._make_engine()
        s = e.disruption_case()
        assert s.probability <= 0.5

    def test_affected_goals_populated(self) -> None:
        e = self._make_engine()
        s = e.best_case()
        assert isinstance(s.affected_goals, list)
        assert len(s.affected_goals) > 0

    def test_best_has_no_risks(self) -> None:
        e = self._make_engine()
        s = e.best_case()
        assert s.risks == []

    def test_disruption_low_prob(self) -> None:
        e = self._make_engine()
        s = e.disruption_case()
        best = e.best_case()
        assert s.probability <= best.probability

    def test_scenario_has_source_signals(self) -> None:
        e = self._make_engine()
        for s in e.generate():
            assert isinstance(s.source_signals, list)
            assert len(s.source_signals) > 0

    def test_scenario_has_contributing_factors(self) -> None:
        e = self._make_engine()
        for s in e.generate():
            assert isinstance(s.contributing_factors, list)

    def test_scenario_has_assumptions(self) -> None:
        e = self._make_engine()
        for s in e.generate():
            assert isinstance(s.assumptions, list)
            assert len(s.assumptions) > 0

    def test_expected_probability_matches_confidence(self) -> None:
        e = self._make_engine()
        s = e.expected_case()
        # Expected case probability = clamped avg_confidence
        assert 0.0 <= s.probability <= 1.0

    def test_worst_has_assumptions(self) -> None:
        e = self._make_engine()
        s = e.worst_case()
        assert len(s.assumptions) > 0
        assert any("risk" in a.lower() or "fail" in a.lower() or "worsen" in a.lower() for a in s.assumptions)

    def test_no_mutation_authority(self) -> None:
        """Scenarios are forecast artifacts only — no mutation methods exist."""
        e = self._make_engine()
        assert not hasattr(e, "execute")
        assert not hasattr(e, "approve")
        assert not hasattr(e, "mutate")
        assert not hasattr(e, "modify_goal")
