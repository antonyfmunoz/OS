"""Tests for GoalDriftEngine — Campaign 8.5.

Validates four drift detectors (activity, alignment, outcome, planning),
severity classification, and snapshot aggregation.
"""

import sys
import time

# Repo root DERIVED from the active checkout — never a hardcoded worktree path.
from tests.repo_root import ensure_repo_on_path

ensure_repo_on_path()

import pytest

from substrate.organism.strategic_gap_engine import (
    Goal,
    GoalRegistry,
    GoalStatus,
    GoalType,
    SuccessCriterion,
)
from substrate.organism.goal_hierarchy_engine import GoalHierarchyEngine
from substrate.organism.outcome_tracking_runtime import OutcomeProgress, OutcomeTrackingRuntime
from substrate.organism.strategic_planning_engine import PlanningStatus
from substrate.organism.goal_alignment_engine import GoalAlignmentEngine
from substrate.organism.goal_drift_engine import (
    GoalDriftEngine,
    GoalDriftSnapshot,
    GoalDriftType,
    GoalDriftWarning,
)


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def tmp_goals(tmp_path):
    store = str(tmp_path / "goals.jsonl")
    registry = GoalRegistry(store_path=store)

    registry.add(Goal(
        goal_id="v-1", title="Revenue Vision",
        goal_type=GoalType.VISION, status=GoalStatus.ACTIVE,
    ))
    registry.add(Goal(
        goal_id="obj-1", title="Launch Product",
        goal_type=GoalType.OBJECTIVE, status=GoalStatus.ACTIVE,
        parent_goal_id="v-1",
    ))
    registry.add(Goal(
        goal_id="proj-1", title="Outreach",
        goal_type=GoalType.PROJECT, status=GoalStatus.ACTIVE,
        parent_goal_id="obj-1",
    ))
    return registry


@pytest.fixture
def hierarchy(tmp_goals):
    return GoalHierarchyEngine(goal_registry=tmp_goals)


class FakeOutcomeTracking:
    """Controllable OutcomeTrackingRuntime stand-in."""

    def __init__(self, progress_map=None):
        self._progress = progress_map or {}

    def progress(self, goal_id):
        return self._progress.get(goal_id, OutcomeProgress(goal_id=goal_id))


class FakeAlignmentEngine:
    def __init__(self, score=1.0, unlinked=None):
        self._score = score
        self._unlinked = unlinked or []

    def alignment_score(self):
        return self._score

    def unlinked_work(self):
        return self._unlinked


class FakePlanningEngine:
    def __init__(self, status_map=None):
        self._status = status_map or {}

    def status(self, goal_id):
        return self._status.get(goal_id, PlanningStatus.ON_TRACK)


# ── GoalDriftType enum ──────────────────────────────────────────────


class TestGoalDriftTypeEnum:
    def test_activity_drift_value(self):
        assert GoalDriftType.ACTIVITY_DRIFT.value == "activity_drift"

    def test_alignment_drift_value(self):
        assert GoalDriftType.ALIGNMENT_DRIFT.value == "alignment_drift"

    def test_outcome_drift_value(self):
        assert GoalDriftType.OUTCOME_DRIFT.value == "outcome_drift"

    def test_planning_drift_value(self):
        assert GoalDriftType.PLANNING_DRIFT.value == "planning_drift"

    def test_all_four_types(self):
        assert len(GoalDriftType) == 4


# ── GoalDriftWarning defaults ───────────────────────────────────────


class TestGoalDriftWarningDefaults:
    def test_default_fields(self):
        w = GoalDriftWarning()
        assert w.drift_id.startswith("gd-")
        assert w.goal_id == ""
        assert w.goal_title == ""
        assert w.drift_type == GoalDriftType.ACTIVITY_DRIFT.value
        assert w.severity == "medium"
        assert w.description == ""
        assert w.evidence == []
        assert w.detected_at > 0

    def test_to_dict(self):
        w = GoalDriftWarning(goal_id="g1", goal_title="Goal 1", severity="high")
        d = w.to_dict()
        assert d["goal_id"] == "g1"
        assert d["severity"] == "high"
        assert "drift_id" in d
        assert "detected_at" in d

    def test_custom_drift_type(self):
        w = GoalDriftWarning(drift_type=GoalDriftType.OUTCOME_DRIFT.value)
        assert w.drift_type == "outcome_drift"


# ── GoalDriftSnapshot defaults ──────────────────────────────────────


class TestGoalDriftSnapshotDefaults:
    def test_default_fields(self):
        s = GoalDriftSnapshot()
        assert s.warnings == []
        assert s.high_drift_count == 0
        assert s.drift_by_type == {}
        assert s.overall_drift_health == "healthy"
        assert s.generated_at == 0.0

    def test_to_dict(self):
        s = GoalDriftSnapshot(
            warnings=[{"drift_id": "gd-1"}],
            high_drift_count=1,
            drift_by_type={"activity_drift": 1},
            overall_drift_health="degraded",
            generated_at=time.time(),
        )
        d = s.to_dict()
        assert d["warning_count"] == 1
        assert d["high_drift_count"] == 1
        assert d["overall_drift_health"] == "degraded"


# ── Constructor degradation ─────────────────────────────────────────


class TestConstructorDegradation:
    def test_all_none_detect(self):
        engine = GoalDriftEngine()
        assert engine.detect() == []

    def test_all_none_high_drift(self):
        engine = GoalDriftEngine()
        assert engine.high_drift() == []

    def test_all_none_summary(self):
        engine = GoalDriftEngine()
        snap = engine.summary()
        assert snap.overall_drift_health == "healthy"
        assert snap.warnings == []

    def test_all_none_drift_for_goal(self):
        engine = GoalDriftEngine()
        assert engine.drift_for_goal("g1") == []


# ── Empty registry ──────────────────────────────────────────────────


class TestEmptyRegistry:
    def test_no_goals_no_drift(self, tmp_path):
        empty_reg = GoalRegistry(store_path=str(tmp_path / "empty.jsonl"))
        engine = GoalDriftEngine(
            goal_registry=empty_reg,
            outcome_tracking=FakeOutcomeTracking(),
            alignment_engine=FakeAlignmentEngine(),
            planning_engine=FakePlanningEngine(),
        )
        assert engine.detect() == []


# ── Activity drift detector ─────────────────────────────────────────


class TestActivityDrift:
    def test_triggers_when_many_active_low_progress(self, tmp_goals, hierarchy):
        outcomes = FakeOutcomeTracking({
            "v-1": OutcomeProgress(goal_id="v-1", active_work_count=5, percent_complete=0.05),
            "obj-1": OutcomeProgress(goal_id="obj-1", active_work_count=0, percent_complete=0.0),
            "proj-1": OutcomeProgress(goal_id="proj-1", active_work_count=0, percent_complete=0.0),
        })
        engine = GoalDriftEngine(
            goal_registry=tmp_goals,
            outcome_tracking=outcomes,
        )
        warnings = engine._detect_activity_drift()
        assert len(warnings) == 1
        assert warnings[0].goal_id == "v-1"
        assert warnings[0].drift_type == GoalDriftType.ACTIVITY_DRIFT.value
        assert warnings[0].severity == "high"

    def test_no_trigger_when_progress_above_threshold(self, tmp_goals, hierarchy):
        outcomes = FakeOutcomeTracking({
            "v-1": OutcomeProgress(goal_id="v-1", active_work_count=5, percent_complete=0.5),
            "obj-1": OutcomeProgress(goal_id="obj-1", active_work_count=0, percent_complete=0.0),
            "proj-1": OutcomeProgress(goal_id="proj-1", active_work_count=0, percent_complete=0.0),
        })
        engine = GoalDriftEngine(
            goal_registry=tmp_goals,
            outcome_tracking=outcomes,
        )
        warnings = engine._detect_activity_drift()
        assert len(warnings) == 0

    def test_medium_severity_for_3_active(self, tmp_goals):
        outcomes = FakeOutcomeTracking({
            "v-1": OutcomeProgress(goal_id="v-1", active_work_count=3, percent_complete=0.05),
            "obj-1": OutcomeProgress(goal_id="obj-1", active_work_count=0, percent_complete=0.0),
            "proj-1": OutcomeProgress(goal_id="proj-1", active_work_count=0, percent_complete=0.0),
        })
        engine = GoalDriftEngine(
            goal_registry=tmp_goals,
            outcome_tracking=outcomes,
        )
        warnings = engine._detect_activity_drift()
        assert len(warnings) == 1
        assert warnings[0].severity == "medium"

    def test_no_trigger_with_few_active(self, tmp_goals):
        outcomes = FakeOutcomeTracking({
            "v-1": OutcomeProgress(goal_id="v-1", active_work_count=2, percent_complete=0.05),
            "obj-1": OutcomeProgress(goal_id="obj-1", active_work_count=0, percent_complete=0.0),
            "proj-1": OutcomeProgress(goal_id="proj-1", active_work_count=0, percent_complete=0.0),
        })
        engine = GoalDriftEngine(
            goal_registry=tmp_goals,
            outcome_tracking=outcomes,
        )
        assert len(engine._detect_activity_drift()) == 0


# ── Alignment drift detector ────────────────────────────────────────


class TestAlignmentDrift:
    def test_triggers_below_50_percent(self):
        alignment = FakeAlignmentEngine(
            score=0.3,
            unlinked=[{"work_id": "wp-1"}, {"work_id": "wp-2"}],
        )
        engine = GoalDriftEngine(alignment_engine=alignment)
        warnings = engine._detect_alignment_drift()
        assert len(warnings) == 1
        assert warnings[0].drift_type == GoalDriftType.ALIGNMENT_DRIFT.value
        assert warnings[0].goal_id == "system"

    def test_critical_below_25_percent(self):
        alignment = FakeAlignmentEngine(score=0.1)
        engine = GoalDriftEngine(alignment_engine=alignment)
        warnings = engine._detect_alignment_drift()
        assert len(warnings) == 1
        assert warnings[0].severity == "critical"

    def test_high_between_25_and_50(self):
        alignment = FakeAlignmentEngine(score=0.4)
        engine = GoalDriftEngine(alignment_engine=alignment)
        warnings = engine._detect_alignment_drift()
        assert len(warnings) == 1
        assert warnings[0].severity == "high"

    def test_no_trigger_above_50(self):
        alignment = FakeAlignmentEngine(score=0.8)
        engine = GoalDriftEngine(alignment_engine=alignment)
        assert len(engine._detect_alignment_drift()) == 0


# ── Outcome drift detector ──────────────────────────────────────────


class TestOutcomeDrift:
    def test_triggers_no_work_incomplete(self, tmp_goals):
        outcomes = FakeOutcomeTracking({
            "v-1": OutcomeProgress(goal_id="v-1", active_work_count=0, percent_complete=0.1),
            "obj-1": OutcomeProgress(goal_id="obj-1", active_work_count=0, percent_complete=0.0),
            "proj-1": OutcomeProgress(goal_id="proj-1", active_work_count=1, percent_complete=0.0),
        })
        engine = GoalDriftEngine(
            goal_registry=tmp_goals,
            outcome_tracking=outcomes,
        )
        warnings = engine._detect_outcome_drift()
        assert len(warnings) == 2
        goal_ids = {w.goal_id for w in warnings}
        assert "v-1" in goal_ids
        assert "obj-1" in goal_ids

    def test_high_severity_below_25(self, tmp_goals):
        outcomes = FakeOutcomeTracking({
            "v-1": OutcomeProgress(goal_id="v-1", active_work_count=0, percent_complete=0.1),
            "obj-1": OutcomeProgress(goal_id="obj-1", active_work_count=1, percent_complete=0.0),
            "proj-1": OutcomeProgress(goal_id="proj-1", active_work_count=1, percent_complete=0.0),
        })
        engine = GoalDriftEngine(
            goal_registry=tmp_goals,
            outcome_tracking=outcomes,
        )
        warnings = engine._detect_outcome_drift()
        assert len(warnings) == 1
        assert warnings[0].severity == "high"

    def test_medium_severity_above_25(self, tmp_goals):
        outcomes = FakeOutcomeTracking({
            "v-1": OutcomeProgress(goal_id="v-1", active_work_count=0, percent_complete=0.5),
            "obj-1": OutcomeProgress(goal_id="obj-1", active_work_count=1, percent_complete=0.0),
            "proj-1": OutcomeProgress(goal_id="proj-1", active_work_count=1, percent_complete=0.0),
        })
        engine = GoalDriftEngine(
            goal_registry=tmp_goals,
            outcome_tracking=outcomes,
        )
        warnings = engine._detect_outcome_drift()
        assert len(warnings) == 1
        assert warnings[0].severity == "medium"

    def test_no_trigger_when_completed(self, tmp_goals):
        outcomes = FakeOutcomeTracking({
            "v-1": OutcomeProgress(goal_id="v-1", active_work_count=0, percent_complete=1.0),
            "obj-1": OutcomeProgress(goal_id="obj-1", active_work_count=0, percent_complete=1.0),
            "proj-1": OutcomeProgress(goal_id="proj-1", active_work_count=0, percent_complete=1.0),
        })
        engine = GoalDriftEngine(
            goal_registry=tmp_goals,
            outcome_tracking=outcomes,
        )
        assert len(engine._detect_outcome_drift()) == 0

    def test_no_trigger_with_active_work(self, tmp_goals):
        outcomes = FakeOutcomeTracking({
            "v-1": OutcomeProgress(goal_id="v-1", active_work_count=2, percent_complete=0.1),
            "obj-1": OutcomeProgress(goal_id="obj-1", active_work_count=1, percent_complete=0.0),
            "proj-1": OutcomeProgress(goal_id="proj-1", active_work_count=1, percent_complete=0.0),
        })
        engine = GoalDriftEngine(
            goal_registry=tmp_goals,
            outcome_tracking=outcomes,
        )
        assert len(engine._detect_outcome_drift()) == 0


# ── Planning drift detector ─────────────────────────────────────────


class TestPlanningDrift:
    def test_triggers_on_blocked(self, tmp_goals):
        planning = FakePlanningEngine({
            "v-1": PlanningStatus.BLOCKED,
            "obj-1": PlanningStatus.ON_TRACK,
            "proj-1": PlanningStatus.ON_TRACK,
        })
        engine = GoalDriftEngine(
            goal_registry=tmp_goals,
            planning_engine=planning,
        )
        warnings = engine._detect_planning_drift()
        assert len(warnings) == 1
        assert warnings[0].severity == "high"
        assert warnings[0].drift_type == GoalDriftType.PLANNING_DRIFT.value

    def test_triggers_on_not_started(self, tmp_goals):
        planning = FakePlanningEngine({
            "v-1": PlanningStatus.NOT_STARTED,
            "obj-1": PlanningStatus.ON_TRACK,
            "proj-1": PlanningStatus.ON_TRACK,
        })
        engine = GoalDriftEngine(
            goal_registry=tmp_goals,
            planning_engine=planning,
        )
        warnings = engine._detect_planning_drift()
        assert len(warnings) == 1
        assert warnings[0].severity == "medium"

    def test_no_trigger_on_track(self, tmp_goals):
        planning = FakePlanningEngine({
            "v-1": PlanningStatus.ON_TRACK,
            "obj-1": PlanningStatus.ON_TRACK,
            "proj-1": PlanningStatus.ON_TRACK,
        })
        engine = GoalDriftEngine(
            goal_registry=tmp_goals,
            planning_engine=planning,
        )
        assert len(engine._detect_planning_drift()) == 0

    def test_at_risk_no_trigger(self, tmp_goals):
        planning = FakePlanningEngine({
            "v-1": PlanningStatus.AT_RISK,
            "obj-1": PlanningStatus.ON_TRACK,
            "proj-1": PlanningStatus.ON_TRACK,
        })
        engine = GoalDriftEngine(
            goal_registry=tmp_goals,
            planning_engine=planning,
        )
        assert len(engine._detect_planning_drift()) == 0


# ── detect() aggregate ──────────────────────────────────────────────


class TestDetect:
    def test_collects_all_drift_types(self, tmp_goals):
        outcomes = FakeOutcomeTracking({
            "v-1": OutcomeProgress(goal_id="v-1", active_work_count=5, percent_complete=0.05),
            "obj-1": OutcomeProgress(goal_id="obj-1", active_work_count=0, percent_complete=0.1),
            "proj-1": OutcomeProgress(goal_id="proj-1", active_work_count=0, percent_complete=0.0),
        })
        alignment = FakeAlignmentEngine(score=0.2)
        planning = FakePlanningEngine({
            "v-1": PlanningStatus.BLOCKED,
            "obj-1": PlanningStatus.ON_TRACK,
            "proj-1": PlanningStatus.ON_TRACK,
        })
        engine = GoalDriftEngine(
            goal_registry=tmp_goals,
            outcome_tracking=outcomes,
            alignment_engine=alignment,
            planning_engine=planning,
        )
        warnings = engine.detect()
        types = {w.drift_type for w in warnings}
        assert GoalDriftType.ACTIVITY_DRIFT.value in types
        assert GoalDriftType.ALIGNMENT_DRIFT.value in types
        assert GoalDriftType.OUTCOME_DRIFT.value in types
        assert GoalDriftType.PLANNING_DRIFT.value in types


# ── high_drift ──────────────────────────────────────────────────────


class TestHighDrift:
    def test_filters_to_critical_and_high(self, tmp_goals):
        outcomes = FakeOutcomeTracking({
            "v-1": OutcomeProgress(goal_id="v-1", active_work_count=3, percent_complete=0.05),
            "obj-1": OutcomeProgress(goal_id="obj-1", active_work_count=0, percent_complete=0.0),
            "proj-1": OutcomeProgress(goal_id="proj-1", active_work_count=0, percent_complete=0.0),
        })
        alignment = FakeAlignmentEngine(score=0.1)
        engine = GoalDriftEngine(
            goal_registry=tmp_goals,
            outcome_tracking=outcomes,
            alignment_engine=alignment,
        )
        high = engine.high_drift()
        for w in high:
            assert w.severity in ("critical", "high")

    def test_excludes_medium(self, tmp_goals):
        outcomes = FakeOutcomeTracking({
            "v-1": OutcomeProgress(goal_id="v-1", active_work_count=3, percent_complete=0.05),
            "obj-1": OutcomeProgress(goal_id="obj-1", active_work_count=0, percent_complete=0.0),
            "proj-1": OutcomeProgress(goal_id="proj-1", active_work_count=0, percent_complete=0.0),
        })
        engine = GoalDriftEngine(
            goal_registry=tmp_goals,
            outcome_tracking=outcomes,
        )
        all_w = engine.detect()
        high = engine.high_drift()
        medium_count = sum(1 for w in all_w if w.severity == "medium")
        assert len(high) == len(all_w) - medium_count


# ── drift_for_goal ──────────────────────────────────────────────────


class TestDriftForGoal:
    def test_filters_to_specific_goal(self, tmp_goals):
        outcomes = FakeOutcomeTracking({
            "v-1": OutcomeProgress(goal_id="v-1", active_work_count=5, percent_complete=0.05),
            "obj-1": OutcomeProgress(goal_id="obj-1", active_work_count=0, percent_complete=0.0),
            "proj-1": OutcomeProgress(goal_id="proj-1", active_work_count=0, percent_complete=0.0),
        })
        engine = GoalDriftEngine(
            goal_registry=tmp_goals,
            outcome_tracking=outcomes,
        )
        v1_drift = engine.drift_for_goal("v-1")
        for w in v1_drift:
            assert w.goal_id == "v-1"

    def test_nonexistent_goal(self, tmp_goals):
        engine = GoalDriftEngine(goal_registry=tmp_goals)
        assert engine.drift_for_goal("nonexistent") == []


# ── summary ─────────────────────────────────────────────────────────


class TestSummary:
    def test_healthy_with_no_drift(self, tmp_goals):
        outcomes = FakeOutcomeTracking({
            "v-1": OutcomeProgress(goal_id="v-1", active_work_count=2, percent_complete=0.5),
            "obj-1": OutcomeProgress(goal_id="obj-1", active_work_count=1, percent_complete=0.5),
            "proj-1": OutcomeProgress(goal_id="proj-1", active_work_count=1, percent_complete=0.5),
        })
        alignment = FakeAlignmentEngine(score=0.9)
        planning = FakePlanningEngine()
        engine = GoalDriftEngine(
            goal_registry=tmp_goals,
            outcome_tracking=outcomes,
            alignment_engine=alignment,
            planning_engine=planning,
        )
        snap = engine.summary()
        assert snap.overall_drift_health == "healthy"
        assert snap.high_drift_count == 0

    def test_degraded_with_high_drift(self, tmp_goals):
        outcomes = FakeOutcomeTracking({
            "v-1": OutcomeProgress(goal_id="v-1", active_work_count=5, percent_complete=0.05),
            "obj-1": OutcomeProgress(goal_id="obj-1", active_work_count=1, percent_complete=0.5),
            "proj-1": OutcomeProgress(goal_id="proj-1", active_work_count=1, percent_complete=0.5),
        })
        engine = GoalDriftEngine(
            goal_registry=tmp_goals,
            outcome_tracking=outcomes,
        )
        snap = engine.summary()
        assert snap.overall_drift_health in ("degraded", "watch")
        assert snap.high_drift_count >= 0

    def test_critical_with_critical_drift(self, tmp_goals):
        alignment = FakeAlignmentEngine(score=0.1)
        engine = GoalDriftEngine(
            goal_registry=tmp_goals,
            alignment_engine=alignment,
        )
        snap = engine.summary()
        assert snap.overall_drift_health == "critical"

    def test_drift_by_type_populated(self, tmp_goals):
        outcomes = FakeOutcomeTracking({
            "v-1": OutcomeProgress(goal_id="v-1", active_work_count=5, percent_complete=0.05),
            "obj-1": OutcomeProgress(goal_id="obj-1", active_work_count=0, percent_complete=0.0),
            "proj-1": OutcomeProgress(goal_id="proj-1", active_work_count=0, percent_complete=0.0),
        })
        engine = GoalDriftEngine(
            goal_registry=tmp_goals,
            outcome_tracking=outcomes,
        )
        snap = engine.summary()
        assert isinstance(snap.drift_by_type, dict)
        assert len(snap.drift_by_type) > 0

    def test_summary_to_dict(self, tmp_goals):
        engine = GoalDriftEngine(goal_registry=tmp_goals)
        snap = engine.summary()
        d = snap.to_dict()
        assert "warning_count" in d
        assert "high_drift_count" in d
        assert "overall_drift_health" in d
        assert "generated_at" in d

    def test_summary_generated_at(self, tmp_goals):
        engine = GoalDriftEngine(goal_registry=tmp_goals)
        snap = engine.summary()
        assert snap.generated_at > 0
