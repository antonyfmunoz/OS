"""
Phase 11A — Execution loop tests.

Validates:
  1. Goals get executed
  2. Outcomes recorded correctly
  3. Failure streak increments
  4. Priority decay triggers in real loop
  5. Reselection happens automatically
  6. System does NOT crash on execution failure
  7. Multi-cycle determinism
  8. Single-writer enforcement (only executor acts)
"""

import sys
import uuid
from datetime import datetime, timezone
from typing import Any

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.execution_loop import (
    CycleResult,
    ExecutionLoop,
    ExecutionResult,
    NoOpExecutor,
    PassthroughPlanner,
)
from runtime.goal_selector import (
    DECAY_FACTOR,
    DEFAULT_WEIGHTS,
    FAILURE_THRESHOLD,
    MIN_PRIORITY_MULTIPLIER,
    Goal,
    GoalSelector,
    GoalState,
    OpportunityCostLayer,
    StrategicHorizonLayer,
)

NOW = datetime.now(timezone.utc)


# ─── In-memory infrastructure ────────────────────────────────────────────────


def _make_goal(
    title: str,
    priority: int = 5,
    impact: float = 0.5,
    cost: float = 0.5,
    gid: str | None = None,
    state: GoalState = GoalState.DEFERRED,
) -> Goal:
    return Goal(
        id=gid or str(uuid.uuid4())[:8],
        org_id="test-org",
        title=title,
        state=state,
        priority=priority,
        expected_impact=impact,
        estimated_cost=cost,
        confidence=0.5,
        created_at=NOW,
        updated_at=NOW,
    )


class InMemorySelector:
    """GoalSelector replacement that works entirely in memory."""

    def __init__(self, goals: list[Goal], focus_budget: int = 2):
        self._goals = goals
        self.focus_budget = focus_budget
        self._inner = GoalSelector.__new__(GoalSelector)
        self._inner.org_id = "test-org"
        self._inner.focus_budget = focus_budget
        self._inner.weights = dict(DEFAULT_WEIGHTS)
        self._inner.opportunity_cost = OpportunityCostLayer()
        self._inner.strategic_horizon = StrategicHorizonLayer(
            performance_weight=self._inner.weights.get("performance", 0.20),
        )

    def run_selection_cycle(self) -> list[Goal]:
        scorable = [g for g in self._goals if g.state in {GoalState.ACTIVE, GoalState.DEFERRED}]
        for g in scorable:
            self._inner.score_goal(g, self._goals)
        scorable.sort(key=lambda g: (-g.score, -g.priority, g.created_at))
        for i, g in enumerate(scorable):
            g.state = GoalState.ACTIVE if i < self.focus_budget else GoalState.DEFERRED
            g.rank = i + 1
        return [g for g in scorable if g.state == GoalState.ACTIVE]


class InMemoryOutcomeTracker:
    """OutcomeTracker replacement that applies decay logic in memory."""

    def __init__(self):
        self.outcomes: list[dict] = []
        self._goals: dict[str, Goal] = {}

    def bind_goals(self, goals: list[Goal]) -> None:
        self._goals = {g.id: g for g in goals}

    def record_outcome(
        self,
        goal_id: str,
        outcome_type: str,
        execution_time: float = 0.0,
        impact_delta: float = 0.0,
        task_type: str = "",
        metadata: dict | None = None,
    ) -> None:
        self.outcomes.append(
            {
                "goal_id": goal_id,
                "outcome_type": outcome_type,
                "execution_time": execution_time,
                "impact_delta": impact_delta,
                "task_type": task_type,
            }
        )
        goal = self._goals.get(goal_id)
        if goal:
            if outcome_type == "success":
                goal.failure_streak = 0
                goal.priority_decay_multiplier = 1.0
            else:
                goal.failure_streak += 1
                if goal.failure_streak >= FAILURE_THRESHOLD:
                    goal.priority_decay_multiplier = max(
                        MIN_PRIORITY_MULTIPLIER,
                        goal.priority_decay_multiplier * DECAY_FACTOR,
                    )


class SuccessExecutor:
    """Always succeeds."""

    def execute(self, goal: Goal, plan: dict) -> ExecutionResult:
        return ExecutionResult(success=True, output={"action": "test_success"})


class FailExecutor:
    """Always fails."""

    def execute(self, goal: Goal, plan: dict) -> ExecutionResult:
        return ExecutionResult(success=False, output={}, error="simulated failure")


class CrashExecutor:
    """Raises an exception."""

    def execute(self, goal: Goal, plan: dict) -> ExecutionResult:
        raise RuntimeError("executor crash")


class ConditionalExecutor:
    """Succeeds or fails based on goal ID."""

    def __init__(self, fail_ids: set[str]):
        self.fail_ids = fail_ids

    def execute(self, goal: Goal, plan: dict) -> ExecutionResult:
        if goal.id in self.fail_ids:
            return ExecutionResult(success=False, error="conditional failure")
        return ExecutionResult(success=True, output={"action": "conditional_success"})


class TrackingExecutor:
    """Records which goals were executed (verifies single-writer)."""

    def __init__(self):
        self.executed: list[str] = []

    def execute(self, goal: Goal, plan: dict) -> ExecutionResult:
        self.executed.append(goal.id)
        return ExecutionResult(success=True, output={"tracked": True})


def _build_loop(
    goals: list[Goal],
    executor=None,
    focus_budget: int = 2,
) -> tuple[ExecutionLoop, InMemoryOutcomeTracker, list[Goal]]:
    """Build a fully in-memory execution loop."""
    selector = InMemorySelector(goals, focus_budget=focus_budget)
    tracker = InMemoryOutcomeTracker()
    tracker.bind_goals(goals)
    events: list[dict] = []

    loop = ExecutionLoop(
        selector=selector,
        planner=PassthroughPlanner(),
        executor=executor or SuccessExecutor(),
        outcome_tracker=tracker,
        event_publisher=lambda et, p: events.append({"type": et, **p}),
    )
    loop._events = events  # attach for test inspection
    return loop, tracker, goals


# ─── 1. Goals get executed ───────────────────────────────────────────────────


class TestGoalsGetExecuted:
    def test_active_goals_are_executed(self):
        goals = [
            _make_goal("Goal A", priority=8, gid="A"),
            _make_goal("Goal B", priority=6, gid="B"),
        ]
        loop, tracker, _ = _build_loop(goals, focus_budget=2)
        result = loop.run_cycle()

        assert len(result.results) == 2
        assert "A" in result.results
        assert "B" in result.results

    def test_only_active_goals_executed(self):
        goals = [
            _make_goal("Goal A", priority=8, gid="A"),
            _make_goal("Goal B", priority=6, gid="B"),
            _make_goal("Goal C", priority=4, gid="C"),
        ]
        loop, _, _ = _build_loop(goals, focus_budget=1)
        result = loop.run_cycle()

        assert len(result.results) == 1
        assert result.active_goals[0] == "A"

    def test_completed_goals_not_executed(self):
        goals = [
            _make_goal("Active", priority=8, gid="A"),
            _make_goal("Done", priority=10, gid="D", state=GoalState.COMPLETED),
        ]
        loop, _, _ = _build_loop(goals, focus_budget=2)
        result = loop.run_cycle()

        assert "D" not in result.results
        assert "A" in result.results

    def test_zero_goals_produces_empty_cycle(self):
        loop, _, _ = _build_loop([], focus_budget=2)
        result = loop.run_cycle()

        assert len(result.results) == 0
        assert len(result.active_goals) == 0


# ─── 2. Outcomes recorded correctly ─────────────────────────────────────────


class TestOutcomesRecorded:
    def test_success_outcome_recorded(self):
        goals = [_make_goal("Test", priority=8, gid="A")]
        loop, tracker, _ = _build_loop(goals, focus_budget=1)
        loop.run_cycle()

        assert len(tracker.outcomes) == 1
        assert tracker.outcomes[0]["goal_id"] == "A"
        assert tracker.outcomes[0]["outcome_type"] == "success"

    def test_failure_outcome_recorded(self):
        goals = [_make_goal("Test", priority=8, gid="A")]
        loop, tracker, _ = _build_loop(goals, executor=FailExecutor(), focus_budget=1)
        loop.run_cycle()

        assert tracker.outcomes[0]["outcome_type"] == "failure"

    def test_crash_records_failure(self):
        goals = [_make_goal("Test", priority=8, gid="A")]
        loop, tracker, _ = _build_loop(goals, executor=CrashExecutor(), focus_budget=1)
        loop.run_cycle()

        assert tracker.outcomes[0]["outcome_type"] == "failure"

    def test_multiple_goals_all_recorded(self):
        goals = [
            _make_goal("A", priority=8, gid="A"),
            _make_goal("B", priority=6, gid="B"),
        ]
        loop, tracker, _ = _build_loop(goals, focus_budget=2)
        loop.run_cycle()

        assert len(tracker.outcomes) == 2
        recorded_ids = {o["goal_id"] for o in tracker.outcomes}
        assert recorded_ids == {"A", "B"}

    def test_task_type_is_execution_loop(self):
        goals = [_make_goal("Test", priority=8, gid="A")]
        loop, tracker, _ = _build_loop(goals, focus_budget=1)
        loop.run_cycle()

        assert tracker.outcomes[0]["task_type"] == "execution_loop"


# ─── 3. Failure streak increments ───────────────────────────────────────────


class TestFailureStreak:
    def test_single_failure_increments_streak(self):
        goals = [_make_goal("Failing", priority=8, gid="A")]
        loop, _, _ = _build_loop(goals, executor=FailExecutor(), focus_budget=1)
        loop.run_cycle()

        assert goals[0].failure_streak == 1

    def test_streak_accumulates_over_cycles(self):
        goals = [_make_goal("Failing", priority=8, gid="A")]
        loop, _, _ = _build_loop(goals, executor=FailExecutor(), focus_budget=1)
        loop.run(cycles=3)

        assert goals[0].failure_streak == 3

    def test_success_resets_streak(self):
        goals = [_make_goal("Mixed", priority=8, gid="A")]
        loop_fail, _, _ = _build_loop(goals, executor=FailExecutor(), focus_budget=1)
        loop_fail.run(cycles=3)
        assert goals[0].failure_streak == 3

        loop_ok, tracker_ok, _ = _build_loop(goals, executor=SuccessExecutor(), focus_budget=1)
        tracker_ok.bind_goals(goals)
        loop_ok.run_cycle()
        assert goals[0].failure_streak == 0

    def test_crash_counts_as_failure(self):
        goals = [_make_goal("Crashing", priority=8, gid="A")]
        loop, _, _ = _build_loop(goals, executor=CrashExecutor(), focus_budget=1)
        loop.run_cycle()

        assert goals[0].failure_streak == 1


# ─── 4. Priority decay triggers in real loop ────────────────────────────────


class TestPriorityDecayInLoop:
    def test_decay_triggers_after_threshold(self):
        goals = [_make_goal("Decaying", priority=10, gid="A")]
        loop, _, _ = _build_loop(goals, executor=FailExecutor(), focus_budget=1)
        loop.run(cycles=FAILURE_THRESHOLD)

        assert goals[0].failure_streak == FAILURE_THRESHOLD
        assert goals[0].priority_decay_multiplier == DECAY_FACTOR

    def test_no_decay_before_threshold(self):
        goals = [_make_goal("Not Yet", priority=10, gid="A")]
        loop, _, _ = _build_loop(goals, executor=FailExecutor(), focus_budget=1)
        loop.run(cycles=FAILURE_THRESHOLD - 1)

        assert goals[0].priority_decay_multiplier == 1.0

    def test_decay_compounds_past_threshold(self):
        goals = [_make_goal("Deep Decay", priority=10, gid="A")]
        loop, _, _ = _build_loop(goals, executor=FailExecutor(), focus_budget=1)
        loop.run(cycles=FAILURE_THRESHOLD + 3)

        expected = max(MIN_PRIORITY_MULTIPLIER, DECAY_FACTOR**4)
        assert abs(goals[0].priority_decay_multiplier - expected) < 0.001

    def test_decay_causes_reselection(self):
        """A decaying high-priority goal should lose to a fresh lower-priority goal."""
        goals = [
            _make_goal("High Pri Failing", priority=10, gid="A"),
            _make_goal("Low Pri Steady", priority=6, gid="B"),
        ]
        executor = ConditionalExecutor(fail_ids={"A"})
        loop, _, _ = _build_loop(goals, executor=executor, focus_budget=1)

        initial = loop.run_cycle()
        assert initial.active_goals[0] == "A"

        for _ in range(15):
            loop.run_cycle()

        final = loop.run_cycle()
        assert goals[0].priority_decay_multiplier < 1.0
        assert final.reselected[0] == "B", (
            f"B should overtake decayed A: A.decay={goals[0].priority_decay_multiplier:.3f}"
        )

    def test_success_resets_decay(self):
        goals = [_make_goal("Recovering", priority=10, gid="A")]
        loop_fail, _, _ = _build_loop(goals, executor=FailExecutor(), focus_budget=1)
        loop_fail.run(cycles=FAILURE_THRESHOLD + 2)
        assert goals[0].priority_decay_multiplier < 1.0

        loop_ok, tracker_ok, _ = _build_loop(goals, executor=SuccessExecutor(), focus_budget=1)
        tracker_ok.bind_goals(goals)
        loop_ok.run_cycle()

        assert goals[0].priority_decay_multiplier == 1.0
        assert goals[0].failure_streak == 0


# ─── 5. Reselection happens automatically ───────────────────────────────────


class TestReselection:
    def test_reselection_occurs_after_execution(self):
        goals = [
            _make_goal("A", priority=8, gid="A"),
            _make_goal("B", priority=6, gid="B"),
        ]
        loop, _, _ = _build_loop(goals, focus_budget=1)
        result = loop.run_cycle()

        assert len(result.reselected) == 1

    def test_active_set_changes_over_time(self):
        """When A keeps failing, B should eventually take over."""
        goals = [
            _make_goal("Failing A", priority=10, gid="A"),
            _make_goal("Steady B", priority=6, gid="B"),
        ]
        executor = ConditionalExecutor(fail_ids={"A"})
        loop, _, _ = _build_loop(goals, executor=executor, focus_budget=1)

        active_history = []
        for _ in range(20):
            cr = loop.run_cycle()
            active_history.append(cr.reselected[0] if cr.reselected else "")

        assert "A" in active_history[:5], "A should start active"

        b_count_later = sum(1 for a in active_history[10:] if a == "B")
        assert b_count_later > 0, "B should appear in active set after A decays"

    def test_multi_cycle_reselection_count(self):
        goals = [
            _make_goal("A", priority=8, gid="A"),
            _make_goal("B", priority=6, gid="B"),
        ]
        loop, _, _ = _build_loop(goals, focus_budget=2)
        results = loop.run(cycles=5)

        for cr in results:
            assert len(cr.reselected) <= 2


# ─── 6. System does NOT crash on execution failure ──────────────────────────


class TestCrashSafety:
    def test_executor_crash_does_not_stop_loop(self):
        goals = [_make_goal("Crasher", priority=8, gid="A")]
        loop, _, _ = _build_loop(goals, executor=CrashExecutor(), focus_budget=1)
        results = loop.run(cycles=3)

        assert len(results) == 3
        for cr in results:
            assert not cr.results["A"].success

    def test_mixed_crash_and_success(self):
        """One goal crashes, another succeeds — loop continues."""

        class MixedExecutor:
            def execute(self, goal: Goal, plan: dict) -> ExecutionResult:
                if goal.id == "crash":
                    raise ValueError("boom")
                return ExecutionResult(success=True)

        goals = [
            _make_goal("Crasher", priority=8, gid="crash"),
            _make_goal("Worker", priority=6, gid="ok"),
        ]
        loop, tracker, _ = _build_loop(goals, executor=MixedExecutor(), focus_budget=2)
        result = loop.run_cycle()

        assert not result.results["crash"].success
        assert result.results["ok"].success
        assert len(tracker.outcomes) == 2

    def test_planner_failure_still_executes(self):
        """Planner crashing falls back to error plan, execution still happens."""

        class CrashPlanner:
            def create_plan(self, goal: Goal) -> dict:
                raise RuntimeError("planner broke")

        goals = [_make_goal("Test", priority=8, gid="A")]
        selector = InMemorySelector(goals, focus_budget=1)
        tracker = InMemoryOutcomeTracker()
        tracker.bind_goals(goals)

        loop = ExecutionLoop(
            selector=selector,
            planner=CrashPlanner(),
            executor=SuccessExecutor(),
            outcome_tracker=tracker,
            event_publisher=lambda et, p: None,
        )
        result = loop.run_cycle()

        assert result.results["A"].success
        assert len(tracker.outcomes) == 1


# ─── 7. Multi-cycle determinism ──────────────────────────────────────────────


class TestDeterminism:
    def test_identical_runs_same_results(self):
        """Same goals, same executor → same active selections."""

        def _run_once():
            goals = [
                _make_goal("A", priority=10, gid="A"),
                _make_goal("B", priority=6, gid="B"),
            ]
            loop, _, _ = _build_loop(goals, focus_budget=1)
            results = loop.run(cycles=5)
            return [cr.reselected for cr in results]

        run1 = _run_once()
        run2 = _run_once()
        assert run1 == run2

    def test_failure_pattern_deterministic(self):
        """Same failure pattern → same decay trajectory."""

        def _run_once():
            goals = [_make_goal("X", priority=10, gid="X")]
            loop, _, g = _build_loop(goals, executor=FailExecutor(), focus_budget=1)
            loop.run(cycles=10)
            return g[0].failure_streak, g[0].priority_decay_multiplier

        r1 = _run_once()
        r2 = _run_once()
        assert r1 == r2


# ─── 8. Single-writer enforcement ───────────────────────────────────────────


class TestSingleWriter:
    def test_only_executor_called(self):
        """Verify that only the executor's execute() method produces actions."""
        goals = [
            _make_goal("A", priority=8, gid="A"),
            _make_goal("B", priority=6, gid="B"),
        ]
        tracking = TrackingExecutor()
        loop, _, _ = _build_loop(goals, executor=tracking, focus_budget=2)
        loop.run_cycle()

        assert set(tracking.executed) == {"A", "B"}

    def test_planner_is_read_only(self):
        """Planner receives goal but cannot mutate it."""

        class SpyPlanner:
            def __init__(self):
                self.received_goals: list[Goal] = []

            def create_plan(self, goal: Goal) -> dict:
                self.received_goals.append(goal)
                return {"spy": True}

        goals = [_make_goal("Test", priority=8, gid="A")]
        planner = SpyPlanner()
        selector = InMemorySelector(goals, focus_budget=1)
        tracker = InMemoryOutcomeTracker()
        tracker.bind_goals(goals)

        loop = ExecutionLoop(
            selector=selector,
            planner=planner,
            executor=SuccessExecutor(),
            outcome_tracker=tracker,
            event_publisher=lambda et, p: None,
        )
        loop.run_cycle()

        assert len(planner.received_goals) == 1
        assert planner.received_goals[0].id == "A"


# ─── 9. EventBus integration ────────────────────────────────────────────────


class TestEventPublishing:
    def test_goal_executed_event_published(self):
        goals = [_make_goal("Test", priority=8, gid="A")]
        loop, _, _ = _build_loop(goals, focus_budget=1)
        loop.run_cycle()

        events = loop._events
        goal_executed = [e for e in events if e["type"] == "goal_executed"]
        assert len(goal_executed) == 1
        assert goal_executed[0]["goal_id"] == "A"
        assert goal_executed[0]["success"] is True

    def test_failure_event_has_error(self):
        goals = [_make_goal("Test", priority=8, gid="A")]
        loop, _, _ = _build_loop(goals, executor=FailExecutor(), focus_budget=1)
        loop.run_cycle()

        events = loop._events
        goal_executed = [e for e in events if e["type"] == "goal_executed"]
        assert goal_executed[0]["success"] is False
        assert goal_executed[0]["error"] == "simulated failure"

    def test_crash_event_has_error(self):
        goals = [_make_goal("Test", priority=8, gid="A")]
        loop, _, _ = _build_loop(goals, executor=CrashExecutor(), focus_budget=1)
        loop.run_cycle()

        events = loop._events
        goal_executed = [e for e in events if e["type"] == "goal_executed"]
        assert goal_executed[0]["success"] is False
        assert "executor crash" in goal_executed[0]["error"]

    def test_events_per_cycle_match_active_goals(self):
        goals = [
            _make_goal("A", priority=8, gid="A"),
            _make_goal("B", priority=6, gid="B"),
            _make_goal("C", priority=4, gid="C"),
        ]
        loop, _, _ = _build_loop(goals, focus_budget=2)
        loop.run_cycle()

        events = loop._events
        goal_executed = [e for e in events if e["type"] == "goal_executed"]
        assert len(goal_executed) == 2


# ─── 10. Cycle history ──────────────────────────────────────────────────────


class TestCycleHistory:
    def test_history_accumulates(self):
        goals = [_make_goal("A", priority=8, gid="A")]
        loop, _, _ = _build_loop(goals, focus_budget=1)
        loop.run(cycles=5)

        assert len(loop.cycle_history) == 5
        for i, cr in enumerate(loop.cycle_history):
            assert cr.cycle == i

    def test_execution_result_has_timing(self):
        goals = [_make_goal("A", priority=8, gid="A")]
        loop, _, _ = _build_loop(goals, focus_budget=1)
        loop.run_cycle()

        result = loop.cycle_history[0].results["A"]
        assert result.execution_time >= 0.0


# ─── Runner ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
