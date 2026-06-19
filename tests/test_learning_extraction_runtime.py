"""Tests for LearningExtractionRuntime — Campaign 12.0."""
from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

import pytest
from substrate.organism.learning_extraction_runtime import (
    ExtractedLesson,
    LearningExtractionRuntime,
    LessonCategory,
    LessonExtractionSnapshot,
)


# ── Fixtures ──────────────────────────────────────────────────────────


class FakeOutcomeLearning:
    def recent_outcomes(self, limit: int = 20) -> list:
        return [type("O", (), {"id": "out-1", "action_type": "deploy", "status": "success", "timestamp": time.time()})]

    def recent_signals(self, limit: int = 20) -> list:
        return []

    def get_reliability(self, action_type: str) -> float:
        return 0.85

    def get_adjustments(self, action_type: str) -> list:
        return []


class FakeDecisionRegistry:
    def active_decisions(self) -> list:
        return [type("D", (), {"id": "dec-1", "title": "Deploy strategy", "goal_id": "g-1", "status": "active", "assumptions": ["asm-1"]})()]

    def decisions_for_goal(self, goal_id: str) -> list:
        return self.active_decisions()


class FakeAssumptionTracking:
    def invalidated(self) -> list:
        return [type("A", (), {"id": "asm-1", "statement": "Users prefer email", "invalidated_at": time.time(), "decision_id": "dec-1"})()]

    def assumptions_for_decision(self, decision_id: str) -> list:
        return self.invalidated()


class FakeOutcomeTracking:
    def goals_at_risk(self) -> list:
        return []

    def progress(self, goal_id: str) -> float:
        return 0.5

    def health(self) -> str:
        return "healthy"


class FakeStrategicMemory:
    def detect_patterns(self) -> list:
        return []

    def synthesize(self) -> dict:
        return {"insights": []}


# ── Type tests ────────────────────────────────────────────────────────


class TestLessonCategory:
    def test_all_values(self) -> None:
        assert len(LessonCategory) == 6
        assert "success_pattern" in [c.value for c in LessonCategory]
        assert "failure_pattern" in [c.value for c in LessonCategory]
        assert "capability_gap" in [c.value for c in LessonCategory]

    def test_str_enum(self) -> None:
        assert isinstance(LessonCategory.SUCCESS_PATTERN, str)


class TestExtractedLesson:
    def test_defaults(self) -> None:
        lesson = ExtractedLesson()
        assert lesson.lesson_id == ""
        assert lesson.confidence == 0.0
        assert lesson.confidence_reason == ""
        assert lesson.source_count == 0
        assert lesson.actionable is False

    def test_to_dict(self) -> None:
        lesson = ExtractedLesson(
            lesson_id="l-1",
            category=LessonCategory.SUCCESS_PATTERN.value,
            title="Deploy succeeds reliably",
            confidence=0.85,
            confidence_reason="3 successful outcomes, 0 failures",
            source_count=3,
            actionable=True,
        )
        d = lesson.to_dict()
        assert d["lesson_id"] == "l-1"
        assert d["confidence"] == 0.85
        assert d["confidence_reason"] == "3 successful outcomes, 0 failures"
        assert d["source_count"] == 3
        assert d["actionable"] is True


class TestLessonExtractionSnapshot:
    def test_defaults(self) -> None:
        snap = LessonExtractionSnapshot()
        assert snap.total_lessons == 0
        assert snap.extraction_velocity == 0.0
        assert snap.staleness_score == 0.0

    def test_to_dict(self) -> None:
        snap = LessonExtractionSnapshot(total_lessons=5, extraction_velocity=1.5)
        d = snap.to_dict()
        assert d["total_lessons"] == 5
        assert d["extraction_velocity"] == 1.5


# ── Runtime tests ─────────────────────────────────────────────────────


class TestLearningExtractionRuntime:
    def _make_runtime(self) -> LearningExtractionRuntime:
        return LearningExtractionRuntime(
            outcome_learning=FakeOutcomeLearning(),
            decision_registry=FakeDecisionRegistry(),
            assumption_tracking=FakeAssumptionTracking(),
            outcome_tracking=FakeOutcomeTracking(),
            strategic_memory=FakeStrategicMemory(),
        )

    def test_instantiation(self) -> None:
        rt = self._make_runtime()
        assert rt is not None

    def test_extract_batch_returns_lessons(self) -> None:
        rt = self._make_runtime()
        lessons = rt.extract_batch()
        assert isinstance(lessons, list)

    def test_extract_from_outcome(self) -> None:
        rt = self._make_runtime()
        result = rt.extract_from_outcome("out-1")
        assert result is None or isinstance(result, ExtractedLesson)

    def test_extract_from_decision(self) -> None:
        rt = self._make_runtime()
        lessons = rt.extract_from_decision("dec-1")
        assert isinstance(lessons, list)

    def test_recent_lessons(self) -> None:
        rt = self._make_runtime()
        rt.extract_batch()
        lessons = rt.recent_lessons(limit=10)
        assert isinstance(lessons, list)

    def test_lessons_by_category(self) -> None:
        rt = self._make_runtime()
        rt.extract_batch()
        by_cat = rt.lessons_by_category(LessonCategory.ASSUMPTION_INVALIDATION.value)
        assert isinstance(by_cat, list)

    def test_actionable_lessons(self) -> None:
        rt = self._make_runtime()
        rt.extract_batch()
        actionable = rt.actionable_lessons()
        assert isinstance(actionable, list)

    def test_snapshot(self) -> None:
        rt = self._make_runtime()
        snap = rt.snapshot()
        assert isinstance(snap, LessonExtractionSnapshot)
        assert snap.total_lessons >= 0

    def test_summary(self) -> None:
        rt = self._make_runtime()
        s = rt.summary()
        assert isinstance(s, dict)
        assert "total_lessons" in s

    def test_health(self) -> None:
        rt = self._make_runtime()
        h = rt.health()
        assert h in ("active", "learning", "stale", "dormant", "unknown")

    def test_provenance(self) -> None:
        rt = self._make_runtime()
        rt.extract_batch()
        lessons = rt.recent_lessons(limit=1)
        if lessons:
            prov = rt.provenance(lessons[0].lesson_id)
            assert isinstance(prov, dict)
            assert "lesson_id" in prov

    def test_no_deps_graceful(self) -> None:
        rt = LearningExtractionRuntime()
        snap = rt.snapshot()
        assert snap.total_lessons >= 0
        h = rt.health()
        assert isinstance(h, str)

    def test_deduplication(self) -> None:
        rt = self._make_runtime()
        rt.extract_batch()
        first_count = len(rt.recent_lessons(limit=100))
        rt.extract_batch()
        second_count = len(rt.recent_lessons(limit=100))
        assert second_count == first_count

    def test_lesson_has_provenance_fields(self) -> None:
        rt = self._make_runtime()
        rt.extract_batch()
        for lesson in rt.recent_lessons(limit=5):
            assert hasattr(lesson, "confidence_reason")
            assert hasattr(lesson, "source_count")
            assert isinstance(lesson.confidence_reason, str)
            assert isinstance(lesson.source_count, int)
