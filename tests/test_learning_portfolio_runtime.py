"""Tests for LearningPortfolioRuntime — Campaign 12.3."""
from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

import pytest
from substrate.organism.learning_portfolio_runtime import (
    LearningDriftType,
    LearningDriftWarning,
    LearningHealth,
    LearningPortfolioRuntime,
    LearningPortfolioSnapshot,
)


# ── Fixtures ──────────────────────────────────────────────────────────


class FakeLessonSnapshot:
    total_lessons = 10
    actionable_count = 4
    extraction_velocity = 1.5
    staleness_score = 0.3
    top_lessons = [{"id": "l-1", "title": "Test lesson"}]
    category_distribution = {"success_pattern": 5, "failure_pattern": 5}

    def to_dict(self):
        return {"total_lessons": self.total_lessons}


class FakeLearningExtraction:
    def snapshot(self):
        return FakeLessonSnapshot()

    def recent_lessons(self, limit: int = 50):
        return []

    def actionable_lessons(self):
        return []


class FakePatternSnapshot:
    total_patterns = 5
    pattern_velocity = 0.8
    top_patterns = [{"id": "p-1", "title": "Pattern"}]

    def to_dict(self):
        return {"total_patterns": self.total_patterns}


class FakePatternEngine:
    def snapshot(self):
        return FakePatternSnapshot()

    def top_patterns(self, limit: int = 100):
        return [type("P", (), {"recommendation": "Do X"})() for _ in range(3)]


class FakeEvolutionSnapshot:
    total_capabilities = 8
    advancing_count = 3
    declining_count = 1
    stalled_count = 2
    evolution_velocity = 0.5
    top_advancing = [{"id": "cap-1"}]
    top_declining = [{"id": "cap-3"}]

    def to_dict(self):
        return {"total_capabilities": self.total_capabilities}


class FakeEvolutionEngine:
    def snapshot(self):
        return FakeEvolutionSnapshot()


class FakeOutcomeLearning:
    def recent_outcomes(self, limit: int = 5):
        return [type("O", (), {"timestamp": time.time()})()]

    def summary(self):
        return {"total_outcomes": 15, "reliability_scores": {"deploy": 0.9, "test": 0.7}}


class FakeCompounding:
    def compounding_report(self, days: int = 30):
        return {"promoted_count": 3, "pending_count": 2, "rejected_count": 1}


class FakeWorkPortfolio:
    def summary(self):
        return {"health": "healthy"}


class FakeCapabilityPortfolio:
    def snapshot(self):
        return type("S", (), {"health": "healthy", "to_dict": lambda self: {}})()


# ── Type tests ────────────────────────────────────────────────────────


class TestLearningHealth:
    def test_all_values(self) -> None:
        assert len(LearningHealth) == 5
        assert "thriving" in [h.value for h in LearningHealth]
        assert "critical" in [h.value for h in LearningHealth]

    def test_str_enum(self) -> None:
        assert isinstance(LearningHealth.THRIVING, str)


class TestLearningDriftType:
    def test_all_values(self) -> None:
        assert len(LearningDriftType) == 5
        assert "lesson_staleness" in [d.value for d in LearningDriftType]
        assert "compounding_blockage" in [d.value for d in LearningDriftType]


class TestLearningDriftWarning:
    def test_defaults(self) -> None:
        w = LearningDriftWarning()
        assert w.severity == "low"
        assert w.description == ""

    def test_to_dict(self) -> None:
        w = LearningDriftWarning(
            drift_type="lesson_staleness",
            severity="high",
            description="Stale lessons",
        )
        d = w.to_dict()
        assert d["severity"] == "high"


class TestLearningPortfolioSnapshot:
    def test_defaults(self) -> None:
        snap = LearningPortfolioSnapshot()
        assert snap.lesson_count == 0
        assert snap.compounding_score == 0.0
        assert snap.health == "stagnant"

    def test_to_dict(self) -> None:
        snap = LearningPortfolioSnapshot(
            lesson_count=10, compounding_score=0.654321
        )
        d = snap.to_dict()
        assert d["lesson_count"] == 10
        assert d["compounding_score"] == 0.6543


# ── Runtime tests ─────────────────────────────────────────────────────


class TestLearningPortfolioRuntime:
    def _make_runtime(self) -> LearningPortfolioRuntime:
        return LearningPortfolioRuntime(
            learning_extraction=FakeLearningExtraction(),
            outcome_patterns=FakePatternEngine(),
            capability_evolution=FakeEvolutionEngine(),
            outcome_learning=FakeOutcomeLearning(),
            compounding_engine=FakeCompounding(),
            work_portfolio=FakeWorkPortfolio(),
            capability_portfolio=FakeCapabilityPortfolio(),
        )

    def test_instantiation(self) -> None:
        rt = self._make_runtime()
        assert rt is not None

    def test_health_with_data(self) -> None:
        rt = self._make_runtime()
        h = rt.health()
        assert isinstance(h, LearningHealth)

    def test_health_no_deps(self) -> None:
        rt = LearningPortfolioRuntime()
        h = rt.health()
        assert isinstance(h, LearningHealth)

    def test_compounding_score(self) -> None:
        rt = self._make_runtime()
        score = rt.compounding_score()
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_compounding_score_no_deps(self) -> None:
        rt = LearningPortfolioRuntime()
        score = rt.compounding_score()
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_lesson_velocity(self) -> None:
        rt = self._make_runtime()
        vel = rt.lesson_velocity()
        assert vel == 1.5

    def test_lesson_velocity_no_deps(self) -> None:
        rt = LearningPortfolioRuntime()
        vel = rt.lesson_velocity()
        assert isinstance(vel, float)
        assert vel >= 0.0

    def test_learning_effectiveness(self) -> None:
        rt = self._make_runtime()
        eff = rt.learning_effectiveness()
        assert isinstance(eff, dict)
        assert "actionable_ratio" in eff
        assert "pattern_to_recommendation_ratio" in eff
        assert "compounding_score" in eff

    def test_drift_warnings(self) -> None:
        rt = self._make_runtime()
        warnings = rt.drift_warnings()
        assert isinstance(warnings, list)
        for w in warnings:
            assert isinstance(w, LearningDriftWarning)

    def test_snapshot(self) -> None:
        rt = self._make_runtime()
        snap = rt.snapshot()
        assert isinstance(snap, LearningPortfolioSnapshot)
        assert snap.lesson_count == 10
        assert snap.pattern_count == 5
        assert snap.active_trajectories == 8
        assert snap.advancing_capabilities == 3

    def test_snapshot_serialization(self) -> None:
        rt = self._make_runtime()
        snap = rt.snapshot()
        d = snap.to_dict()
        assert isinstance(d, dict)
        assert "lesson_count" in d
        assert "health" in d
        assert "generated_at" in d

    def test_summary(self) -> None:
        rt = self._make_runtime()
        s = rt.summary()
        assert isinstance(s, dict)
        assert "lesson_count" in s

    def test_drift_no_deps(self) -> None:
        rt = LearningPortfolioRuntime()
        warnings = rt.drift_warnings()
        assert isinstance(warnings, list)

    def test_snapshot_no_deps(self) -> None:
        rt = LearningPortfolioRuntime()
        snap = rt.snapshot()
        assert snap.lesson_count >= 0
        assert snap.pattern_count >= 0
