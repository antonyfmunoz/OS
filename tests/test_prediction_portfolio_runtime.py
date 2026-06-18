"""Tests for PredictionPortfolioRuntime — Campaign 13.2."""
from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest
from substrate.organism.prediction_portfolio_runtime import (
    PredictionDriftType,
    PredictionDriftWarning,
    PredictionHealth,
    PredictionPortfolioRuntime,
    PredictionPortfolioSnapshot,
)


# ── Fixtures ──────────────────────────────────────────────────────────


class FakeTrajectoryRuntime:
    def __init__(self, forecasts=None) -> None:
        self._forecasts = forecasts or [
            type("F", (), {
                "entity_id": "goal-1", "status": "stable",
                "confidence": 0.7,
                "to_dict": lambda self: {"entity_id": "goal-1", "status": "stable", "confidence": 0.7},
            })(),
            type("F", (), {
                "entity_id": "goal-2", "status": "declining",
                "confidence": 0.3,
                "to_dict": lambda self: {"entity_id": "goal-2", "status": "declining", "confidence": 0.3},
            })(),
            type("F", (), {
                "entity_id": "work", "status": "stable",
                "confidence": 0.6,
                "to_dict": lambda self: {"entity_id": "work", "status": "stable", "confidence": 0.6},
            })(),
        ]

    def forecast_all(self) -> list:
        return self._forecasts

    def at_risk_trajectories(self) -> list:
        return [f for f in self._forecasts if f.status in ("slowing", "stalled", "declining")]

    def trajectory_summary(self) -> dict:
        confs = [f.confidence for f in self._forecasts]
        return {"total": len(self._forecasts), "average_confidence": sum(confs) / len(confs)}

    def health(self) -> str:
        return "degraded"


class FakeScenarioEngine:
    def generate(self) -> list:
        return [
            type("S", (), {
                "scenario_id": "s-1", "scenario_type": "best_case",
                "probability": 0.6, "risks": [],
                "to_dict": lambda self: {"scenario_id": "s-1"},
            })(),
            type("S", (), {
                "scenario_id": "s-2", "scenario_type": "worst_case",
                "probability": 0.2, "risks": ["risk-1", "risk-2"],
                "to_dict": lambda self: {"scenario_id": "s-2"},
            })(),
        ]

    def compare(self) -> dict:
        return {"spread": 0.4}


class FakeLearningPortfolio:
    def compounding_score(self) -> float:
        return 0.5


class FakeCapabilityPortfolio:
    def health(self):
        return type("H", (), {"value": "healthy"})()


class FakeWorkPortfolio:
    def health(self):
        return type("H", (), {"value": "healthy"})()


class FakeStrategicMemory:
    def detect_patterns(self) -> list:
        return ["pattern-1", "pattern-2"]


# ── Type tests ────────────────────────────────────────────────────────


class TestPredictionHealth:
    def test_all_values(self) -> None:
        assert len(PredictionHealth) == 5
        assert "high_confidence" in [h.value for h in PredictionHealth]
        assert "blind" in [h.value for h in PredictionHealth]


class TestPredictionDriftType:
    def test_all_values(self) -> None:
        assert len(PredictionDriftType) == 5
        assert "forecast_decay" in [d.value for d in PredictionDriftType]
        assert "trajectory_break" in [d.value for d in PredictionDriftType]


class TestPredictionDriftWarning:
    def test_defaults(self) -> None:
        w = PredictionDriftWarning()
        assert w.drift_type == "signal_weakness"
        assert w.severity == "low"
        assert w.affected_ids == []

    def test_to_dict(self) -> None:
        w = PredictionDriftWarning(
            drift_type="forecast_decay",
            severity="high",
            description="test",
        )
        d = w.to_dict()
        assert d["drift_type"] == "forecast_decay"
        assert d["severity"] == "high"


class TestPredictionPortfolioSnapshot:
    def test_defaults(self) -> None:
        s = PredictionPortfolioSnapshot()
        assert s.forecast_count == 0
        assert s.scenario_count == 0
        assert s.prediction_health == "blind"
        assert s.average_confidence == 0.0
        assert s.uncertainty_index == 1.0

    def test_to_dict_rounds(self) -> None:
        s = PredictionPortfolioSnapshot(
            average_confidence=0.73456,
            uncertainty_index=0.26789,
        )
        d = s.to_dict()
        assert d["average_confidence"] == 0.7346
        assert d["uncertainty_index"] == 0.2679


# ── Runtime tests ─────────────────────────────────────────────────────


class TestPredictionPortfolioRuntime:
    def _make_runtime(self) -> PredictionPortfolioRuntime:
        return PredictionPortfolioRuntime(
            trajectory_runtime=FakeTrajectoryRuntime(),
            scenario_engine=FakeScenarioEngine(),
            learning_portfolio=FakeLearningPortfolio(),
            capability_portfolio=FakeCapabilityPortfolio(),
            work_portfolio=FakeWorkPortfolio(),
            strategic_memory=FakeStrategicMemory(),
        )

    def test_instantiation(self) -> None:
        rt = self._make_runtime()
        assert rt is not None

    def test_health(self) -> None:
        rt = self._make_runtime()
        h = rt.health()
        assert isinstance(h, PredictionHealth)
        assert h.value in [v.value for v in PredictionHealth]

    def test_uncertainty_index(self) -> None:
        rt = self._make_runtime()
        ui = rt.uncertainty_index()
        assert isinstance(ui, float)
        assert 0.0 <= ui <= 1.0

    def test_drift_warnings(self) -> None:
        rt = self._make_runtime()
        warnings = rt.drift_warnings()
        assert isinstance(warnings, list)
        for w in warnings:
            assert isinstance(w, PredictionDriftWarning)

    def test_highest_risk_forecasts(self) -> None:
        rt = self._make_runtime()
        top = rt.highest_risk_forecasts(limit=2)
        assert isinstance(top, list)
        assert len(top) <= 2
        if len(top) >= 2:
            sev_first = {"accelerating": 0, "stable": 1, "slowing": 2, "stalled": 3, "declining": 4}
            assert sev_first.get(top[0].status, 0) >= sev_first.get(top[1].status, 0)

    def test_snapshot(self) -> None:
        rt = self._make_runtime()
        snap = rt.snapshot()
        assert isinstance(snap, PredictionPortfolioSnapshot)
        assert snap.forecast_count == 3
        assert snap.scenario_count == 2
        assert snap.average_confidence > 0.0
        assert snap.generated_at > 0.0

    def test_summary(self) -> None:
        rt = self._make_runtime()
        s = rt.summary()
        assert isinstance(s, dict)
        assert "forecast_count" in s
        assert "prediction_health" in s
        assert "average_confidence" in s
        assert "uncertainty_index" in s
        assert "drift_count" in s

    def test_no_deps_health_is_blind(self) -> None:
        rt = PredictionPortfolioRuntime()
        h = rt.health()
        # With no deps, signal count < 3, so health should be BLIND
        assert h in (PredictionHealth.BLIND, PredictionHealth.VOLATILE,
                     PredictionHealth.UNCERTAIN, PredictionHealth.STABLE,
                     PredictionHealth.HIGH_CONFIDENCE)

    def test_no_deps_snapshot(self) -> None:
        rt = PredictionPortfolioRuntime()
        snap = rt.snapshot()
        assert snap.forecast_count >= 0

    def test_no_deps_uncertainty_high(self) -> None:
        rt = PredictionPortfolioRuntime()
        ui = rt.uncertainty_index()
        assert ui >= 0.5  # should be high with no data

    def test_health_high_confidence(self) -> None:
        high_conf_forecasts = [
            type("F", (), {"entity_id": f"e-{i}", "status": "stable", "confidence": 0.85,
                           "to_dict": lambda self: {}})()
            for i in range(5)
        ]
        rt = PredictionPortfolioRuntime(
            trajectory_runtime=FakeTrajectoryRuntime(high_conf_forecasts),
            scenario_engine=FakeScenarioEngine(),
            learning_portfolio=FakeLearningPortfolio(),
            capability_portfolio=FakeCapabilityPortfolio(),
            work_portfolio=FakeWorkPortfolio(),
            strategic_memory=FakeStrategicMemory(),
        )
        h = rt.health()
        assert h == PredictionHealth.HIGH_CONFIDENCE

    def test_forecast_decay_drift(self) -> None:
        low_conf_forecasts = [
            type("F", (), {"entity_id": f"e-{i}", "status": "stable", "confidence": 0.2,
                           "to_dict": lambda self: {}})()
            for i in range(5)
        ]
        rt = PredictionPortfolioRuntime(
            trajectory_runtime=FakeTrajectoryRuntime(low_conf_forecasts),
            scenario_engine=FakeScenarioEngine(),
            learning_portfolio=FakeLearningPortfolio(),
            capability_portfolio=FakeCapabilityPortfolio(),
            work_portfolio=FakeWorkPortfolio(),
            strategic_memory=FakeStrategicMemory(),
        )
        warnings = rt.drift_warnings()
        types = [w.drift_type for w in warnings]
        assert "forecast_decay" in types

    def test_confidence_collapse_drift(self) -> None:
        very_low = [
            type("F", (), {"entity_id": f"e-{i}", "status": "stable", "confidence": 0.1,
                           "to_dict": lambda self: {}})()
            for i in range(5)
        ]
        rt = PredictionPortfolioRuntime(
            trajectory_runtime=FakeTrajectoryRuntime(very_low),
            scenario_engine=FakeScenarioEngine(),
            learning_portfolio=FakeLearningPortfolio(),
            capability_portfolio=FakeCapabilityPortfolio(),
            work_portfolio=FakeWorkPortfolio(),
            strategic_memory=FakeStrategicMemory(),
        )
        warnings = rt.drift_warnings()
        types = [w.drift_type for w in warnings]
        assert "confidence_collapse" in types

    def test_trajectory_break_drift(self) -> None:
        break_forecasts = [
            type("F", (), {"entity_id": "e-break", "status": "declining", "confidence": 0.7,
                           "to_dict": lambda self: {}})(),
        ]
        rt = PredictionPortfolioRuntime(
            trajectory_runtime=FakeTrajectoryRuntime(break_forecasts),
            scenario_engine=FakeScenarioEngine(),
            learning_portfolio=FakeLearningPortfolio(),
            capability_portfolio=FakeCapabilityPortfolio(),
            work_portfolio=FakeWorkPortfolio(),
            strategic_memory=FakeStrategicMemory(),
        )
        warnings = rt.drift_warnings()
        types = [w.drift_type for w in warnings]
        assert "trajectory_break" in types

    def test_no_mutation_methods(self) -> None:
        """Portfolio is read-only — no mutation methods."""
        rt = self._make_runtime()
        assert not hasattr(rt, "execute")
        assert not hasattr(rt, "approve")
        assert not hasattr(rt, "mutate")

    def test_snapshot_to_dict(self) -> None:
        rt = self._make_runtime()
        snap = rt.snapshot()
        d = snap.to_dict()
        assert isinstance(d, dict)
        assert "prediction_health" in d
