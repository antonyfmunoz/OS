"""Tests for TrajectoryIntelligenceRuntime — Campaign 13.0."""
from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

import pytest
from substrate.organism.trajectory_intelligence_runtime import (
    TrajectoryForecast,
    TrajectoryIntelligenceRuntime,
    TrajectoryStatus,
)


# ── Fixtures ──────────────────────────────────────────────────────────


class FakeProjectionEngine:
    def get_projection_state(self) -> dict:
        return {
            "trends": [
                type("T", (), {"direction": "positive"})(),
                type("T", (), {"direction": "positive"})(),
                type("T", (), {"direction": "negative"})(),
            ],
            "projections": [
                type("P", (), {"confidence_score": 0.7})(),
                type("P", (), {"confidence_score": 0.8})(),
            ],
        }

    def run_projections(self, **kwargs) -> dict:
        return {}


class FakeOutcomeTracking:
    def completion(self, goal_id: str) -> float:
        return 0.6

    def health(self, goal_id: str) -> str:
        return "healthy"

    def goals_at_risk(self) -> list:
        return [type("G", (), {"goal_id": "goal-1"})(), type("G", (), {"goal_id": "goal-2"})()]


class FakeGoalDrift:
    def detect(self) -> list:
        return []

    def drift_for_goal(self, goal_id: str) -> list:
        if goal_id == "goal-2":
            return [type("D", (), {"drift_type": "activity_drift"})()]
        return []


class FakeDecisionValidity:
    def evaluate_all(self) -> list:
        return [1, 2, 3]

    def at_risk(self) -> list:
        return [1]

    def invalid(self) -> list:
        return []


class FakeCapabilityEvolution:
    def trajectory(self, cap_id: str):
        return type("T", (), {
            "capability_id": cap_id,
            "maturity_trend": 0.3,
        })()

    def all_trajectories(self) -> list:
        return [
            type("T", (), {"capability_id": "cap-1"})(),
            type("T", (), {"capability_id": "cap-2"})(),
        ]

    def advancing(self) -> list:
        return [1]

    def declining(self) -> list:
        return []

    def stalled(self) -> list:
        return [1]


class FakeLearningPortfolio:
    def lesson_velocity(self) -> float:
        return 0.5

    def health(self):
        return type("H", (), {"value": "healthy"})()

    def compounding_score(self) -> float:
        return 0.6


class FakeWorkPortfolio:
    def completions_per_day(self) -> float:
        return 2.5

    def health(self):
        return type("H", (), {"value": "healthy"})()

    def velocity(self) -> float:
        return 2.5

    def at_risk_work(self) -> list:
        return [1]


# ── Type tests ────────────────────────────────────────────────────────


class TestTrajectoryStatus:
    def test_all_values(self) -> None:
        assert len(TrajectoryStatus) == 5
        assert "accelerating" in [s.value for s in TrajectoryStatus]
        assert "declining" in [s.value for s in TrajectoryStatus]


class TestTrajectoryForecast:
    def test_defaults(self) -> None:
        f = TrajectoryForecast()
        assert f.entity_id == ""
        assert f.entity_type == ""
        assert f.confidence == 0.0
        assert f.status == "stable"
        assert f.forecast_horizon_days == 30
        assert f.source_signals == []
        assert f.contributing_factors == []

    def test_to_dict(self) -> None:
        f = TrajectoryForecast(
            entity_id="goal-1",
            entity_type="goal",
            confidence=0.73456,
            status="accelerating",
        )
        d = f.to_dict()
        assert d["entity_id"] == "goal-1"
        assert d["confidence"] == 0.7346

    def test_explainability_fields(self) -> None:
        f = TrajectoryForecast(
            confidence_reason="High confidence from 5 signals",
            source_signals=["projection_engine", "outcome_tracking"],
        )
        assert f.confidence_reason == "High confidence from 5 signals"
        assert len(f.source_signals) == 2


# ── Runtime tests ─────────────────────────────────────────────────────


class TestTrajectoryIntelligenceRuntime:
    def _make_runtime(self) -> TrajectoryIntelligenceRuntime:
        return TrajectoryIntelligenceRuntime(
            projection_engine=FakeProjectionEngine(),
            outcome_tracking=FakeOutcomeTracking(),
            goal_drift=FakeGoalDrift(),
            decision_validity=FakeDecisionValidity(),
            capability_evolution=FakeCapabilityEvolution(),
            learning_portfolio=FakeLearningPortfolio(),
            work_portfolio=FakeWorkPortfolio(),
        )

    def test_instantiation(self) -> None:
        rt = self._make_runtime()
        assert rt is not None

    def test_forecast_goal(self) -> None:
        rt = self._make_runtime()
        f = rt.forecast_goal("goal-1")
        assert isinstance(f, TrajectoryForecast)
        assert f.entity_id == "goal-1"
        assert f.entity_type == "goal"
        assert 0.0 <= f.confidence <= 1.0
        assert f.status in [s.value for s in TrajectoryStatus]
        assert len(f.source_signals) > 0
        assert f.confidence_reason != ""

    def test_forecast_goal_with_drift(self) -> None:
        rt = self._make_runtime()
        f = rt.forecast_goal("goal-2")
        assert f.entity_id == "goal-2"
        assert any("drift" in factor for factor in f.contributing_factors)

    def test_forecast_capability(self) -> None:
        rt = self._make_runtime()
        f = rt.forecast_capability("cap-1")
        assert isinstance(f, TrajectoryForecast)
        assert f.entity_id == "cap-1"
        assert f.entity_type == "capability"
        assert f.confidence_reason != ""
        assert len(f.source_signals) > 0

    def test_forecast_work(self) -> None:
        rt = self._make_runtime()
        f = rt.forecast_work()
        assert isinstance(f, TrajectoryForecast)
        assert f.entity_id == "work_portfolio"
        assert f.entity_type == "work"
        assert any("velocity" in factor for factor in f.contributing_factors)

    def test_forecast_learning(self) -> None:
        rt = self._make_runtime()
        f = rt.forecast_learning()
        assert isinstance(f, TrajectoryForecast)
        assert f.entity_id == "learning_portfolio"
        assert f.entity_type == "learning"
        assert any("learning" in factor for factor in f.contributing_factors)

    def test_forecast_all(self) -> None:
        rt = self._make_runtime()
        forecasts = rt.forecast_all()
        assert isinstance(forecasts, list)
        assert len(forecasts) >= 4  # 2 goals + 2 capabilities + work + learning
        types = {f.entity_type for f in forecasts}
        assert "goal" in types
        assert "capability" in types
        assert "work" in types
        assert "learning" in types

    def test_at_risk_trajectories(self) -> None:
        rt = self._make_runtime()
        at_risk = rt.at_risk_trajectories()
        assert isinstance(at_risk, list)
        for f in at_risk:
            assert f.status in ("slowing", "stalled", "declining")

    def test_trajectory_summary(self) -> None:
        rt = self._make_runtime()
        s = rt.trajectory_summary()
        assert isinstance(s, dict)
        assert "total" in s
        assert "by_status" in s
        assert "average_confidence" in s
        assert "at_risk_count" in s
        assert s["total"] >= 4

    def test_health(self) -> None:
        rt = self._make_runtime()
        h = rt.health()
        assert h in ("healthy", "degraded", "critical", "unknown")

    def test_summary(self) -> None:
        rt = self._make_runtime()
        s = rt.summary()
        assert "health" in s
        assert "total" in s

    def test_no_deps_graceful(self) -> None:
        rt = TrajectoryIntelligenceRuntime()
        s = rt.trajectory_summary()
        assert s["total"] >= 0

    def test_no_deps_health(self) -> None:
        rt = TrajectoryIntelligenceRuntime()
        h = rt.health()
        assert h in ("healthy", "degraded", "critical", "unknown")

    def test_confidence_bounded(self) -> None:
        rt = self._make_runtime()
        forecasts = rt.forecast_all()
        for f in forecasts:
            assert 0.0 <= f.confidence <= 1.0

    def test_forecast_has_source_signals(self) -> None:
        rt = self._make_runtime()
        f = rt.forecast_goal("goal-1")
        assert isinstance(f.source_signals, list)
        assert len(f.source_signals) >= 1

    def test_forecast_has_confidence_reason(self) -> None:
        rt = self._make_runtime()
        f = rt.forecast_goal("goal-1")
        assert isinstance(f.confidence_reason, str)
        assert len(f.confidence_reason) > 0

    def test_forecast_has_contributing_factors(self) -> None:
        rt = self._make_runtime()
        f = rt.forecast_goal("goal-1")
        assert isinstance(f.contributing_factors, list)

    def test_status_classification_accelerating(self) -> None:
        rt = self._make_runtime()
        status, reason = rt._classify_status(
            trend="positive", confidence=0.8, drift_count=0,
            velocity=0.5, declining_signals=0,
        )
        assert status == "accelerating"

    def test_status_classification_declining(self) -> None:
        rt = self._make_runtime()
        status, reason = rt._classify_status(
            trend="negative", confidence=0.3, drift_count=3,
            velocity=0.0, declining_signals=2,
        )
        assert status == "declining"

    def test_status_classification_stalled(self) -> None:
        rt = self._make_runtime()
        status, reason = rt._classify_status(
            trend="neutral", confidence=0.5, drift_count=2,
            velocity=0.05, declining_signals=0,
        )
        assert status == "stalled"

    def test_status_classification_slowing(self) -> None:
        rt = self._make_runtime()
        status, reason = rt._classify_status(
            trend="positive", confidence=0.6, drift_count=0,
            velocity=0.05, declining_signals=0,
        )
        assert status == "slowing"

    def test_status_classification_stable(self) -> None:
        rt = self._make_runtime()
        status, reason = rt._classify_status(
            trend="neutral", confidence=0.5, drift_count=0,
            velocity=0.3, declining_signals=0,
        )
        assert status == "stable"

    def test_compute_confidence_low_signals(self) -> None:
        rt = self._make_runtime()
        conf, reason = rt._compute_confidence(
            base_confidence=0.8, drift_count=0,
            invalid_decisions=0, signal_count=2,
        )
        assert conf < 0.8
        assert "low signal count" in reason

    def test_compute_confidence_drift_penalty(self) -> None:
        rt = self._make_runtime()
        conf, reason = rt._compute_confidence(
            base_confidence=0.8, drift_count=3,
            invalid_decisions=0, signal_count=5,
        )
        assert conf < 0.8
        assert "drift penalty" in reason
