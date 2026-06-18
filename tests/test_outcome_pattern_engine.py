"""Tests for OutcomePatternEngine — Campaign 12.1."""
from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

import pytest
from substrate.organism.outcome_pattern_engine import (
    AttributionLink,
    DetectedPattern,
    OutcomePatternEngine,
    PatternSnapshot,
    PatternType,
)


# ── Fixtures ──────────────────────────────────────────────────────────


class FakeLearningExtraction:
    def recent_lessons(self, limit: int = 50) -> list:
        return [
            type("L", (), {
                "id": f"l-{i}",
                "category": "success_pattern",
                "title": f"Lesson {i}",
                "evidence_sources": [{"type": "outcome", "id": f"out-{i}"}],
                "confidence": 0.8,
                "related_decision_ids": [f"dec-{i}"],
                "related_goal_ids": [f"g-{i}"],
                "related_capability_ids": [f"cap-{i}"],
            })()
            for i in range(5)
        ]

    def lessons_by_category(self, category: str) -> list:
        return [l for l in self.recent_lessons() if l.category == category]


class FakeDecisionLineage:
    def trace(self, decision_id: str) -> list:
        return [{"decision_id": decision_id, "parent_id": None}]

    def blast_radius(self, decision_id: str) -> dict:
        return {"affected_decisions": [decision_id], "affected_goals": ["g-1"]}

    def full_chain(self, decision_id: str) -> list:
        return [decision_id]


class FakeDecisionValidity:
    def at_risk(self) -> list:
        return []

    def invalid(self) -> list:
        return []


class FakeDecisionImpact:
    def highest_impact(self, limit: int = 10) -> list:
        return [type("I", (), {"decision_id": "dec-1", "impact_score": 0.9})()]


class FakeOutcomeLearning:
    def recent_outcomes(self, limit: int = 20) -> list:
        return [
            type("O", (), {
                "id": f"out-{i}",
                "action_type": "deploy",
                "status": "success" if i % 2 == 0 else "failure",
                "timestamp": time.time() - i * 86400,
                "decision_id": f"dec-{i}",
            })()
            for i in range(10)
        ]

    def get_reliability(self, action_type: str) -> float:
        return 0.7


class FakeCompounding:
    def detect_outcome_to_insight(self) -> list:
        return [{"outcome_id": "out-1", "insight": "Deploy reliability high"}]

    def compounding_report(self, days: int = 90) -> dict:
        return {"promoted_count": 2, "pending_count": 1, "rejected_count": 0}


class FakeGoalHierarchy:
    def descendants(self, goal_id: str) -> list:
        return [goal_id]

    def ancestors(self, goal_id: str) -> list:
        return [goal_id]


# ── Type tests ────────────────────────────────────────────────────────


class TestPatternType:
    def test_all_values(self) -> None:
        assert len(PatternType) == 7
        assert "recurring_success" in [p.value for p in PatternType]
        assert "velocity_trend" in [p.value for p in PatternType]


class TestDetectedPattern:
    def test_defaults(self) -> None:
        p = DetectedPattern()
        assert p.pattern_id == ""
        assert p.occurrences == 0
        assert p.confidence == 0.0

    def test_to_dict(self) -> None:
        p = DetectedPattern(
            pattern_id="p-1",
            pattern_type=PatternType.RECURRING_SUCCESS.value,
            title="Deploy always works",
            occurrences=5,
            confidence=0.9,
        )
        d = p.to_dict()
        assert d["pattern_id"] == "p-1"
        assert d["occurrences"] == 5


class TestAttributionLink:
    def test_to_dict(self) -> None:
        link = AttributionLink(
            source_type="outcome",
            source_id="out-1",
            target_type="decision",
            target_id="dec-1",
            strength=0.85,
        )
        d = link.to_dict()
        assert d["strength"] == 0.85


class TestPatternSnapshot:
    def test_defaults(self) -> None:
        snap = PatternSnapshot()
        assert snap.total_patterns == 0
        assert snap.pattern_velocity == 0.0


# ── Runtime tests ─────────────────────────────────────────────────────


class TestOutcomePatternEngine:
    def _make_engine(self) -> OutcomePatternEngine:
        return OutcomePatternEngine(
            learning_extraction=FakeLearningExtraction(),
            decision_lineage=FakeDecisionLineage(),
            decision_validity=FakeDecisionValidity(),
            decision_impact=FakeDecisionImpact(),
            outcome_learning=FakeOutcomeLearning(),
            compounding_engine=FakeCompounding(),
            goal_hierarchy=FakeGoalHierarchy(),
        )

    def test_instantiation(self) -> None:
        engine = self._make_engine()
        assert engine is not None

    def test_detect_patterns(self) -> None:
        engine = self._make_engine()
        patterns = engine.detect_patterns()
        assert isinstance(patterns, list)

    def test_attribute_outcome(self) -> None:
        engine = self._make_engine()
        attrs = engine.attribute_outcome("out-1")
        assert isinstance(attrs, list)

    def test_correlations(self) -> None:
        engine = self._make_engine()
        engine.detect_patterns()
        corrs = engine.correlations()
        assert isinstance(corrs, list)

    def test_patterns_for_goal(self) -> None:
        engine = self._make_engine()
        engine.detect_patterns()
        p = engine.patterns_for_goal("g-1")
        assert isinstance(p, list)

    def test_patterns_for_capability(self) -> None:
        engine = self._make_engine()
        engine.detect_patterns()
        p = engine.patterns_for_capability("cap-1")
        assert isinstance(p, list)

    def test_patterns_by_type(self) -> None:
        engine = self._make_engine()
        engine.detect_patterns()
        p = engine.patterns_by_type(PatternType.RECURRING_SUCCESS.value)
        assert isinstance(p, list)

    def test_top_patterns(self) -> None:
        engine = self._make_engine()
        engine.detect_patterns()
        top = engine.top_patterns(limit=5)
        assert isinstance(top, list)
        for p in top:
            assert hasattr(p, "confidence")

    def test_snapshot(self) -> None:
        engine = self._make_engine()
        engine.detect_patterns()
        snap = engine.snapshot()
        assert isinstance(snap, PatternSnapshot)
        assert snap.total_patterns >= 0

    def test_summary(self) -> None:
        engine = self._make_engine()
        s = engine.summary()
        assert isinstance(s, dict)
        assert "total_patterns" in s

    def test_health(self) -> None:
        engine = self._make_engine()
        h = engine.health()
        assert h in ("active", "learning", "dormant", "unknown")

    def test_no_deps_graceful(self) -> None:
        engine = OutcomePatternEngine()
        snap = engine.snapshot()
        assert snap.total_patterns >= 0

    def test_pattern_dedup(self) -> None:
        engine = self._make_engine()
        engine.detect_patterns()
        first = engine.snapshot().total_patterns
        engine.detect_patterns()
        second = engine.snapshot().total_patterns
        assert second == first

    def test_attribution_returns_links(self) -> None:
        engine = self._make_engine()
        links = engine.attribute_outcome("out-1")
        for link in links:
            assert hasattr(link, "source_type")
            assert hasattr(link, "strength")
