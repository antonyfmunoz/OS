"""Phase 8C — Refinement engine tests."""

import sys

sys.path.insert(0, "/opt/OS")

import pytest
from umh.strategy.history import (
    PerformanceMetrics,
    StrategyVersion,
    get_strategy_history,
    record_strategy_version,
    record_task_outcome,
    reset_strategy_history,
)
from umh.strategy.models import (
    Strategy,
    StrategyStep,
    StepComplexity,
    StepStatus,
)
from umh.strategy.refiner import (
    RefinementIssue,
    RefinementProposal,
    clear_proposal,
    get_proposal,
    refine_strategy,
    reset_proposals,
    store_proposal,
)
from umh.events.stream import reset_event_stream, get_event_stream


class TestRefinementProposal:
    def test_auto_ids(self):
        p = RefinementProposal(goal_id="g1")
        assert p.id.startswith("ref_")
        assert p.created_at != ""

    def test_to_dict(self):
        p = RefinementProposal(
            goal_id="g1",
            issues_detected=[RefinementIssue(issue_type="test", description="test issue")],
            suggested_changes=["fix it"],
            confidence=0.7,
        )
        d = p.to_dict()
        assert d["goal_id"] == "g1"
        assert len(d["issues_detected"]) == 1
        assert len(d["suggested_changes"]) == 1
        assert d["confidence"] == 0.7


class TestRefineStrategy:
    def setup_method(self):
        reset_strategy_history()
        reset_proposals()
        reset_event_stream()

    def test_no_active_version(self):
        result = refine_strategy("nonexistent")
        assert result is None

    def test_insufficient_evaluations(self):
        steps = [StrategyStep(description="a")]
        s = Strategy(goal_id="g1", objective="test", steps=steps)
        record_strategy_version("g1", s)
        record_task_outcome("g1", completed=True)
        result = refine_strategy("g1")
        assert result is None

    def test_no_issues_detected(self):
        steps = [StrategyStep(description="a", status=StepStatus.COMPLETED)]
        s = Strategy(goal_id="g1", objective="test", steps=steps)
        v = record_strategy_version("g1", s)
        v.performance = PerformanceMetrics(
            tasks_completed=10,
            tasks_failed=0,
            evaluations=10,
        )
        result = refine_strategy("g1")
        assert result is None

    def test_high_failure_detected(self):
        steps = [StrategyStep(description="failing step", id="s1", status=StepStatus.FAILED)]
        s = Strategy(goal_id="g1", objective="test", steps=steps)
        v = record_strategy_version("g1", s)
        v.performance = PerformanceMetrics(
            tasks_completed=2,
            tasks_failed=5,
            evaluations=7,
        )
        result = refine_strategy("g1")
        assert result is not None
        assert any(i.issue_type == "high_failure_rate" for i in result.issues_detected)

    def test_frequent_retries_detected(self):
        steps = [StrategyStep(description="retry step")]
        s = Strategy(goal_id="g1", objective="test", steps=steps)
        v = record_strategy_version("g1", s)
        v.performance = PerformanceMetrics(
            tasks_completed=5,
            tasks_failed=0,
            tasks_retried=5,
            evaluations=5,
        )
        result = refine_strategy("g1")
        assert result is not None
        assert any(i.issue_type == "frequent_retries" for i in result.issues_detected)

    def test_bottleneck_detected(self):
        steps = [
            StrategyStep(
                description="bottleneck step",
                id="s1",
                estimated_complexity=StepComplexity.HIGH,
                task_ids=["t1", "t2", "t3"],
                status=StepStatus.IN_PROGRESS,
            )
        ]
        s = Strategy(goal_id="g1", objective="test", steps=steps)
        v = record_strategy_version("g1", s)
        v.performance = PerformanceMetrics(
            tasks_completed=3,
            tasks_failed=2,
            evaluations=5,
        )
        result = refine_strategy("g1")
        assert result is not None
        assert any(i.issue_type == "bottleneck" for i in result.issues_detected)

    def test_dead_step_detected(self):
        steps = [
            StrategyStep(
                description="dead step",
                id="s1",
                generates_tasks=True,
                status=StepStatus.PENDING,
            )
        ]
        s = Strategy(goal_id="g1", objective="test", steps=steps)
        v = record_strategy_version("g1", s)
        v.performance = PerformanceMetrics(
            tasks_completed=3,
            tasks_failed=2,
            evaluations=7,
        )
        result = refine_strategy("g1")
        assert result is not None
        assert any(i.issue_type == "dead_step" for i in result.issues_detected)

    def test_proposal_has_new_strategy(self):
        steps = [StrategyStep(description="failing", id="s1", status=StepStatus.FAILED)]
        s = Strategy(goal_id="g1", objective="test", steps=steps)
        v = record_strategy_version("g1", s)
        v.performance = PerformanceMetrics(tasks_completed=2, tasks_failed=5, evaluations=7)
        result = refine_strategy("g1")
        assert result is not None
        assert result.new_strategy is not None
        assert result.new_strategy.id != s.id

    def test_emits_event(self):
        steps = [StrategyStep(description="failing", id="s1", status=StepStatus.FAILED)]
        s = Strategy(goal_id="g1", objective="test", steps=steps)
        v = record_strategy_version("g1", s)
        v.performance = PerformanceMetrics(tasks_completed=2, tasks_failed=5, evaluations=7)
        refine_strategy("g1")
        events = get_event_stream().list_events()
        types = [e.type for e in events]
        assert "strategy.refinement_proposed" in types

    def test_deterministic_given_same_input(self):
        steps = [StrategyStep(description="failing", id="s1", status=StepStatus.FAILED)]
        s = Strategy(goal_id="g1", objective="test", steps=steps)
        v = record_strategy_version("g1", s)
        v.performance = PerformanceMetrics(tasks_completed=2, tasks_failed=5, evaluations=7)
        r1 = refine_strategy("g1")
        r2 = refine_strategy("g1")
        assert r1 is not None and r2 is not None
        assert len(r1.issues_detected) == len(r2.issues_detected)
        assert len(r1.suggested_changes) == len(r2.suggested_changes)


class TestProposalStore:
    def setup_method(self):
        reset_proposals()

    def test_store_and_get(self):
        p = RefinementProposal(goal_id="g1")
        store_proposal(p)
        got = get_proposal("g1")
        assert got is not None
        assert got.id == p.id

    def test_get_nonexistent(self):
        assert get_proposal("nonexistent") is None

    def test_clear(self):
        p = RefinementProposal(goal_id="g1")
        store_proposal(p)
        assert clear_proposal("g1") is True
        assert get_proposal("g1") is None

    def test_clear_nonexistent(self):
        assert clear_proposal("nonexistent") is False

    def test_reset(self):
        store_proposal(RefinementProposal(goal_id="g1"))
        reset_proposals()
        assert get_proposal("g1") is None
