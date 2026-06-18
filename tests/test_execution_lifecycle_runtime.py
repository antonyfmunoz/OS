"""Tests for Execution Lifecycle Runtime — Campaign 16.2."""
from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from unittest.mock import MagicMock

from substrate.organism.execution_lifecycle_runtime import (
    ExecutionLifecycleRuntime,
    ExecutionLifecycleSnapshot,
    LifecycleArc,
    LifecycleStage,
)


# ── Enum Tests ───────────────────────────────────────────────────────


class TestLifecycleStageEnum:
    def test_values(self) -> None:
        assert LifecycleStage.NOT_STARTED.value == "not_started"
        assert LifecycleStage.IN_PROGRESS.value == "in_progress"
        assert LifecycleStage.COMPLETED.value == "completed"
        assert LifecycleStage.FAILED.value == "failed"
        assert LifecycleStage.LEARNING.value == "learning"
        assert LifecycleStage.COMPOUNDED.value == "compounded"

    def test_count(self) -> None:
        assert len(LifecycleStage) == 6


# ── Dataclass Tests ──────────────────────────────────────────────────


class TestLifecycleArc:
    def test_defaults(self) -> None:
        a = LifecycleArc()
        assert a.goal_id == ""
        assert a.stage == "not_started"
        assert a.completion_pct == 0.0
        assert a.lessons_extracted == 0
        assert a.patterns_detected == 0
        assert a.capabilities_evolved == 0
        assert a.outcome_health == "unknown"

    def test_to_dict(self) -> None:
        a = LifecycleArc(
            goal_id="g-1",
            stage="in_progress",
            completion_pct=0.6,
            lessons_extracted=3,
        )
        d = a.to_dict()
        assert d["goal_id"] == "g-1"
        assert d["stage"] == "in_progress"
        assert d["completion_pct"] == 0.6
        assert d["lessons_extracted"] == 3
        assert "patterns_detected" in d
        assert "capabilities_evolved" in d
        assert "outcome_health" in d


class TestExecutionLifecycleSnapshot:
    def test_defaults(self) -> None:
        s = ExecutionLifecycleSnapshot()
        assert s.arcs == []
        assert s.total_lessons == 0
        assert s.total_patterns == 0
        assert s.advancing_capabilities == 0
        assert s.declining_capabilities == 0
        assert s.overall_stage == "not_started"
        assert s.generated_at > 0

    def test_to_dict(self) -> None:
        s = ExecutionLifecycleSnapshot(
            overall_stage="learning",
            total_lessons=5,
            advancing_capabilities=2,
        )
        d = s.to_dict()
        assert d["overall_stage"] == "learning"
        assert d["total_lessons"] == 5
        assert d["advancing_capabilities"] == 2
        assert "arcs" in d
        assert "generated_at" in d


# ── Fake subsystems ──────────────────────────────────────────────────


class _FakeOutcomeTracking:
    def __init__(self, goals: list | None = None) -> None:
        self._goals = goals or []

    def snapshot(self) -> MagicMock:
        m = MagicMock()
        m.to_dict.return_value = {"goals": [{"goal_id": g["id"]} for g in self._goals]}
        return m

    def completion(self, goal_id: str) -> float:
        for g in self._goals:
            if g["id"] == goal_id:
                return g.get("completion", 0.0)
        return 0.0

    def health(self, goal_id: str) -> str:
        for g in self._goals:
            if g["id"] == goal_id:
                return g.get("health", "unknown")
        return "unknown"


class _FakeLearningExtraction:
    def __init__(self, lessons: list | None = None) -> None:
        self._lessons = lessons or []

    def recent_lessons(self, limit: int = 10) -> list:
        return self._lessons[:limit]


class _FakeOutcomePatterns:
    def __init__(self, patterns_by_goal: dict | None = None) -> None:
        self._patterns = patterns_by_goal or {}

    def patterns_for_goal(self, goal_id: str) -> list:
        return self._patterns.get(goal_id, [])

    def top_patterns(self, limit: int = 10) -> list:
        all_p = []
        for pats in self._patterns.values():
            all_p.extend(pats)
        return all_p[:limit]


class _FakeCapabilityEvolution:
    def __init__(self, advancing: int = 0, declining: int = 0, stalled: int = 0) -> None:
        self._advancing = advancing
        self._declining = declining
        self._stalled = stalled

    def advancing(self) -> list:
        return [f"cap-{i}" for i in range(self._advancing)]

    def declining(self) -> list:
        return [f"cap-dec-{i}" for i in range(self._declining)]

    def stalled(self) -> list:
        return [f"cap-stall-{i}" for i in range(self._stalled)]


# ── Runtime — No Dependencies ────────────────────────────────────────


class TestExecutionLifecycleNoDeps:
    @classmethod
    def setup_class(cls) -> None:
        cls.rt = ExecutionLifecycleRuntime()

    def test_all_arcs_empty(self) -> None:
        assert self.rt.all_arcs() == []

    def test_overall_stage_not_started(self) -> None:
        assert self.rt.overall_stage() == LifecycleStage.NOT_STARTED

    def test_recent_lessons_returns_list(self) -> None:
        assert isinstance(self.rt.recent_lessons(), list)

    def test_recent_patterns_returns_list(self) -> None:
        assert isinstance(self.rt.recent_patterns(), list)

    def test_capability_momentum_zeros(self) -> None:
        m = self.rt.capability_momentum()
        assert m["advancing"] == 0
        assert m["declining"] == 0
        assert m["momentum_score"] == 0.0

    def test_health_dormant(self) -> None:
        assert self.rt.health() == "dormant"

    def test_snapshot_returns_snapshot(self) -> None:
        snap = self.rt.snapshot()
        assert isinstance(snap, ExecutionLifecycleSnapshot)
        d = snap.to_dict()
        assert "arcs" in d
        assert "overall_stage" in d

    def test_summary_has_keys(self) -> None:
        s = self.rt.summary()
        assert "overall_stage" in s
        assert "health" in s
        assert "arc_count" in s
        assert "momentum_score" in s


# ── Stage Classification ─────────────────────────────────────────────


class TestStageClassification:
    def setup_method(self) -> None:
        self.rt = ExecutionLifecycleRuntime()

    def test_not_started(self) -> None:
        stage = self.rt._classify_stage(0.0, "unknown", 0, 0)
        assert stage == LifecycleStage.NOT_STARTED

    def test_in_progress(self) -> None:
        stage = self.rt._classify_stage(0.5, "healthy", 0, 0)
        assert stage == LifecycleStage.IN_PROGRESS

    def test_failed(self) -> None:
        stage = self.rt._classify_stage(0.3, "failed", 0, 0)
        assert stage == LifecycleStage.FAILED

    def test_at_risk_failed(self) -> None:
        stage = self.rt._classify_stage(0.7, "at_risk", 0, 0)
        assert stage == LifecycleStage.FAILED

    def test_completed_no_lessons(self) -> None:
        stage = self.rt._classify_stage(1.0, "healthy", 0, 0)
        assert stage == LifecycleStage.COMPLETED

    def test_learning_with_lessons(self) -> None:
        stage = self.rt._classify_stage(1.0, "healthy", 3, 0)
        assert stage == LifecycleStage.LEARNING

    def test_compounded(self) -> None:
        stage = self.rt._classify_stage(1.0, "healthy", 2, 1)
        assert stage == LifecycleStage.COMPOUNDED


# ── Runtime — With Fakes ─────────────────────────────────────────────


class TestExecutionLifecycleWithFakes:
    def test_arc_not_started(self) -> None:
        rt = ExecutionLifecycleRuntime(
            outcome_tracking=_FakeOutcomeTracking([
                {"id": "g-1", "completion": 0.0, "health": "unknown"},
            ]),
            learning_extraction=_FakeLearningExtraction([]),
            outcome_patterns=_FakeOutcomePatterns({}),
            capability_evolution=_FakeCapabilityEvolution(0),
        )
        arc = rt.arc("g-1")
        assert arc.stage == "not_started"
        assert arc.goal_id == "g-1"

    def test_arc_in_progress(self) -> None:
        rt = ExecutionLifecycleRuntime(
            outcome_tracking=_FakeOutcomeTracking([
                {"id": "g-1", "completion": 0.6, "health": "healthy"},
            ]),
            learning_extraction=_FakeLearningExtraction([]),
            outcome_patterns=_FakeOutcomePatterns({}),
            capability_evolution=_FakeCapabilityEvolution(0),
        )
        arc = rt.arc("g-1")
        assert arc.stage == "in_progress"
        assert arc.completion_pct == 0.6

    def test_arc_completed(self) -> None:
        rt = ExecutionLifecycleRuntime(
            outcome_tracking=_FakeOutcomeTracking([
                {"id": "g-1", "completion": 1.0, "health": "healthy"},
            ]),
            learning_extraction=_FakeLearningExtraction([]),
            outcome_patterns=_FakeOutcomePatterns({}),
            capability_evolution=_FakeCapabilityEvolution(0),
        )
        arc = rt.arc("g-1")
        assert arc.stage == "completed"

    def test_arc_learning(self) -> None:
        lesson = MagicMock()
        lesson.goal_id = "g-1"
        lesson.to_dict = lambda: {"lesson": "test"}
        rt = ExecutionLifecycleRuntime(
            outcome_tracking=_FakeOutcomeTracking([
                {"id": "g-1", "completion": 1.0, "health": "healthy"},
            ]),
            learning_extraction=_FakeLearningExtraction([lesson]),
            outcome_patterns=_FakeOutcomePatterns({}),
            capability_evolution=_FakeCapabilityEvolution(0),
        )
        arc = rt.arc("g-1")
        assert arc.stage == "learning"
        assert arc.lessons_extracted == 1

    def test_arc_compounded(self) -> None:
        lesson = MagicMock()
        lesson.goal_id = "g-1"
        lesson.to_dict = lambda: {"lesson": "test"}
        rt = ExecutionLifecycleRuntime(
            outcome_tracking=_FakeOutcomeTracking([
                {"id": "g-1", "completion": 1.0, "health": "healthy"},
            ]),
            learning_extraction=_FakeLearningExtraction([lesson]),
            outcome_patterns=_FakeOutcomePatterns({"g-1": ["pattern-1"]}),
            capability_evolution=_FakeCapabilityEvolution(advancing=2),
        )
        arc = rt.arc("g-1")
        assert arc.stage == "compounded"
        assert arc.capabilities_evolved == 2

    def test_arc_failed(self) -> None:
        rt = ExecutionLifecycleRuntime(
            outcome_tracking=_FakeOutcomeTracking([
                {"id": "g-1", "completion": 0.4, "health": "failed"},
            ]),
            learning_extraction=_FakeLearningExtraction([]),
            outcome_patterns=_FakeOutcomePatterns({}),
            capability_evolution=_FakeCapabilityEvolution(0),
        )
        arc = rt.arc("g-1")
        assert arc.stage == "failed"

    def test_all_arcs_multiple_goals(self) -> None:
        rt = ExecutionLifecycleRuntime(
            outcome_tracking=_FakeOutcomeTracking([
                {"id": "g-1", "completion": 1.0, "health": "healthy"},
                {"id": "g-2", "completion": 0.5, "health": "healthy"},
            ]),
            learning_extraction=_FakeLearningExtraction([]),
            outcome_patterns=_FakeOutcomePatterns({}),
            capability_evolution=_FakeCapabilityEvolution(0),
        )
        arcs = rt.all_arcs()
        assert len(arcs) == 2
        stages = {a.goal_id: a.stage for a in arcs}
        assert stages["g-1"] == "completed"
        assert stages["g-2"] == "in_progress"

    def test_overall_stage_mixed(self) -> None:
        rt = ExecutionLifecycleRuntime(
            outcome_tracking=_FakeOutcomeTracking([
                {"id": "g-1", "completion": 1.0, "health": "healthy"},
                {"id": "g-2", "completion": 0.5, "health": "healthy"},
            ]),
            learning_extraction=_FakeLearningExtraction([]),
            outcome_patterns=_FakeOutcomePatterns({}),
            capability_evolution=_FakeCapabilityEvolution(0),
        )
        assert rt.overall_stage() == LifecycleStage.IN_PROGRESS

    def test_capability_momentum_with_data(self) -> None:
        rt = ExecutionLifecycleRuntime(
            capability_evolution=_FakeCapabilityEvolution(advancing=3, declining=1, stalled=2),
        )
        m = rt.capability_momentum()
        assert m["advancing"] == 3
        assert m["declining"] == 1
        assert m["stalled"] == 2
        assert m["total"] == 6
        assert m["momentum_score"] == 0.5

    def test_health_thriving(self) -> None:
        lesson = MagicMock()
        lesson.goal_id = "g-1"
        rt = ExecutionLifecycleRuntime(
            outcome_tracking=_FakeOutcomeTracking([
                {"id": "g-1", "completion": 1.0, "health": "healthy"},
            ]),
            learning_extraction=_FakeLearningExtraction([lesson]),
            outcome_patterns=_FakeOutcomePatterns({}),
            capability_evolution=_FakeCapabilityEvolution(advancing=1),
        )
        assert rt.health() == "thriving"

    def test_snapshot_with_data(self) -> None:
        rt = ExecutionLifecycleRuntime(
            outcome_tracking=_FakeOutcomeTracking([
                {"id": "g-1", "completion": 0.5, "health": "healthy"},
            ]),
            learning_extraction=_FakeLearningExtraction([]),
            outcome_patterns=_FakeOutcomePatterns({}),
            capability_evolution=_FakeCapabilityEvolution(0),
        )
        snap = rt.snapshot()
        d = snap.to_dict()
        assert len(d["arcs"]) == 1
        assert d["overall_stage"] == "in_progress"


# ── Canonical Type Registration ──────────────────────────────────────


class TestCanonicalTypes:
    def test_execution_lifecycle_runtime_importable(self) -> None:
        from substrate.organism.execution_lifecycle_runtime import ExecutionLifecycleRuntime
        rt = ExecutionLifecycleRuntime()
        assert rt is not None
