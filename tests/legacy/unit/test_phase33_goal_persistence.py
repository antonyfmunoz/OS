"""Phase 33 — Goal Persistence + Commitment Engine v1.

Tests: GoalState, GoalStateManager, SwitchingCost, CommitmentDecision,
CommitmentResult, CommitmentEngine, advisor integration, hard invariants 101-105,
boundary checks.

Target: 90-120 tests.
"""

from __future__ import annotations

import ast
import sys

import pytest

sys.path.insert(0, "/opt/OS")

from umh.runtime.arbitration import Objective, ObjectiveEvaluator
from umh.runtime.commitment import (
    CommitmentDecision,
    CommitmentEngine,
    CommitmentResult,
    SwitchingCost,
    _DEFAULT_ABANDON_THRESHOLD,
    _DEFAULT_MAX_TICKS,
    _DEFAULT_MIN_IMPROVEMENT,
    _DEFAULT_PROGRESS_WEIGHT,
    _DEFAULT_SWITCH_THRESHOLD,
    _DEFAULT_TIME_WEIGHT,
)
from umh.runtime.goal_state import (
    GoalState,
    GoalStateManager,
    _DEFAULT_COMMITMENT,
    _DEFAULT_PROGRESS,
    _MAX_PROGRESS,
    _MIN_PROGRESS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _obj(
    oid: str = "obj-1",
    priority: int = 5,
    effort: float = 1.0,
    value: float = 1.0,
    deadline: str = "",
) -> Objective:
    return Objective(
        objective_id=oid,
        description=f"Test objective {oid}",
        priority=priority,
        effort_estimate=effort,
        expected_value=value,
        deadline=deadline,
    )


def _state(
    oid: str = "obj-1",
    start_tick: int = 0,
    progress: float = 0.0,
    commitment: float = 0.5,
    **kw,
) -> GoalState:
    return GoalState(
        active_objective=_obj(oid, **kw),
        start_tick=start_tick,
        progress=progress,
        commitment_score=commitment,
    )


# ===========================================================================
# SECTION 1: GoalState
# ===========================================================================


class TestGoalState:
    def test_creation(self):
        obj = _obj()
        gs = GoalState(
            active_objective=obj,
            start_tick=5,
            progress=0.3,
            commitment_score=0.7,
        )
        assert gs.active_objective is obj
        assert gs.start_tick == 5
        assert gs.progress == pytest.approx(0.3)
        assert gs.commitment_score == pytest.approx(0.7)

    def test_frozen(self):
        gs = _state()
        with pytest.raises(AttributeError):
            gs.progress = 0.9  # type: ignore[misc]

    def test_objective_id_property(self):
        gs = _state(oid="abc")
        assert gs.objective_id == "abc"

    def test_elapsed_ticks(self):
        gs = _state(start_tick=3)
        assert gs.elapsed_ticks(10) == 7

    def test_elapsed_ticks_negative_clamped(self):
        gs = _state(start_tick=10)
        assert gs.elapsed_ticks(5) == 0

    def test_progress_clamped_low(self):
        gs = GoalState(
            active_objective=_obj(),
            start_tick=0,
            progress=-0.5,
            commitment_score=0.5,
        )
        assert gs.progress == pytest.approx(0.0)

    def test_progress_clamped_high(self):
        gs = GoalState(
            active_objective=_obj(),
            start_tick=0,
            progress=1.5,
            commitment_score=0.5,
        )
        assert gs.progress == pytest.approx(1.0)

    def test_commitment_clamped_low(self):
        gs = GoalState(
            active_objective=_obj(),
            start_tick=0,
            progress=0.5,
            commitment_score=-0.3,
        )
        assert gs.commitment_score == pytest.approx(0.0)

    def test_commitment_clamped_high(self):
        gs = GoalState(
            active_objective=_obj(),
            start_tick=0,
            progress=0.5,
            commitment_score=2.0,
        )
        assert gs.commitment_score == pytest.approx(1.0)

    def test_with_progress(self):
        gs = _state(progress=0.2)
        gs2 = gs.with_progress(0.8)
        assert gs2.progress == pytest.approx(0.8)
        assert gs.progress == pytest.approx(0.2)
        assert gs2.start_tick == gs.start_tick

    def test_with_commitment(self):
        gs = _state(commitment=0.5)
        gs2 = gs.with_commitment(0.9)
        assert gs2.commitment_score == pytest.approx(0.9)
        assert gs.commitment_score == pytest.approx(0.5)

    def test_to_dict(self):
        gs = _state(oid="x", progress=0.333)
        d = gs.to_dict()
        assert d["objective_id"] == "x"
        assert "progress" in d
        assert "commitment_score" in d
        assert "start_tick" in d
        assert "objective" in d

    def test_to_dict_rounds(self):
        gs = _state(progress=0.33333)
        d = gs.to_dict()
        assert d["progress"] == round(0.33333, 4)

    def test_default_progress(self):
        assert _DEFAULT_PROGRESS == 0.0

    def test_progress_range(self):
        assert _MIN_PROGRESS == 0.0
        assert _MAX_PROGRESS == 1.0


# ===========================================================================
# SECTION 2: GoalStateManager
# ===========================================================================


class TestGoalStateManager:
    def test_empty(self):
        mgr = GoalStateManager()
        assert mgr.active is None
        assert not mgr.has_active
        assert mgr.history_count == 0

    def test_set_active(self):
        mgr = GoalStateManager()
        obj = _obj("a")
        gs = mgr.set_active(obj, start_tick=5)
        assert mgr.has_active
        assert gs.objective_id == "a"
        assert gs.start_tick == 5
        assert gs.progress == pytest.approx(0.0)

    def test_get_active(self):
        mgr = GoalStateManager()
        assert mgr.get_active() is None
        mgr.set_active(_obj(), start_tick=0)
        assert mgr.get_active() is not None

    def test_set_active_archives_previous(self):
        mgr = GoalStateManager()
        mgr.set_active(_obj("a"), start_tick=0)
        mgr.set_active(_obj("b"), start_tick=5)
        assert mgr.active.objective_id == "b"
        assert mgr.history_count == 1
        assert mgr.get_history()[0].objective_id == "a"

    def test_update_progress(self):
        mgr = GoalStateManager()
        mgr.set_active(_obj(), start_tick=0)
        result = mgr.update_progress(0.6)
        assert result is not None
        assert result.progress == pytest.approx(0.6)
        assert mgr.active.progress == pytest.approx(0.6)

    def test_update_progress_no_active(self):
        mgr = GoalStateManager()
        assert mgr.update_progress(0.5) is None

    def test_update_commitment(self):
        mgr = GoalStateManager()
        mgr.set_active(_obj(), start_tick=0)
        result = mgr.update_commitment(0.9)
        assert result is not None
        assert result.commitment_score == pytest.approx(0.9)

    def test_update_commitment_no_active(self):
        mgr = GoalStateManager()
        assert mgr.update_commitment(0.9) is None

    def test_abandon(self):
        mgr = GoalStateManager()
        mgr.set_active(_obj("x"), start_tick=0)
        abandoned = mgr.abandon()
        assert abandoned is not None
        assert abandoned.objective_id == "x"
        assert mgr.active is None
        assert mgr.history_count == 1

    def test_abandon_no_active(self):
        mgr = GoalStateManager()
        assert mgr.abandon() is None

    def test_clear(self):
        mgr = GoalStateManager()
        mgr.set_active(_obj("a"), start_tick=0)
        mgr.set_active(_obj("b"), start_tick=5)
        mgr.clear()
        assert mgr.active is None
        assert mgr.history_count == 0

    def test_get_history_returns_copy(self):
        mgr = GoalStateManager()
        mgr.set_active(_obj("a"), start_tick=0)
        mgr.set_active(_obj("b"), start_tick=5)
        h = mgr.get_history()
        h.clear()
        assert mgr.history_count == 1

    def test_to_dict(self):
        mgr = GoalStateManager()
        d = mgr.to_dict()
        assert d["active"] is None
        assert d["history_count"] == 0

    def test_to_dict_with_active(self):
        mgr = GoalStateManager()
        mgr.set_active(_obj("z"), start_tick=3)
        d = mgr.to_dict()
        assert d["active"]["objective_id"] == "z"

    def test_custom_commitment(self):
        mgr = GoalStateManager()
        gs = mgr.set_active(_obj(), start_tick=0, commitment_score=0.9)
        assert gs.commitment_score == pytest.approx(0.9)

    def test_multiple_archives(self):
        mgr = GoalStateManager()
        for i in range(5):
            mgr.set_active(_obj(f"obj-{i}"), start_tick=i)
        assert mgr.history_count == 4
        assert mgr.active.objective_id == "obj-4"


# ===========================================================================
# SECTION 3: SwitchingCost
# ===========================================================================


class TestSwitchingCost:
    def test_creation(self):
        sc = SwitchingCost(
            progress_penalty=0.3,
            time_penalty=0.2,
            total_penalty=0.5,
        )
        assert sc.progress_penalty == pytest.approx(0.3)
        assert sc.time_penalty == pytest.approx(0.2)
        assert sc.total_penalty == pytest.approx(0.5)

    def test_frozen(self):
        sc = SwitchingCost(0.1, 0.1, 0.2)
        with pytest.raises(AttributeError):
            sc.total_penalty = 0.9  # type: ignore[misc]

    def test_to_dict(self):
        sc = SwitchingCost(0.123456, 0.234567, 0.358023)
        d = sc.to_dict()
        assert d["progress_penalty"] == round(0.123456, 4)
        assert d["time_penalty"] == round(0.234567, 4)
        assert "total_penalty" in d


# ===========================================================================
# SECTION 4: CommitmentDecision
# ===========================================================================


class TestCommitmentDecision:
    def test_values(self):
        assert CommitmentDecision.CONTINUE.value == "continue"
        assert CommitmentDecision.SWITCH.value == "switch"
        assert CommitmentDecision.ABANDON.value == "abandon"

    def test_all_three(self):
        assert len(CommitmentDecision) == 3


# ===========================================================================
# SECTION 5: CommitmentResult
# ===========================================================================


class TestCommitmentResult:
    def _make(self, decision=CommitmentDecision.CONTINUE, candidate=None):
        active = _obj("active")
        evaluator = ObjectiveEvaluator()
        active_score = evaluator.score(active)
        candidate_score = evaluator.score(candidate) if candidate else None
        return CommitmentResult(
            decision=decision,
            active_objective=active,
            active_score=active_score,
            candidate_objective=candidate,
            candidate_score=candidate_score,
            switching_cost=SwitchingCost(0.1, 0.05, 0.15),
            score_gap=0.1,
            net_improvement=0.05,
            progress=0.4,
            ticks_invested=10,
            reason="test reason",
        )

    def test_creation(self):
        r = self._make()
        assert r.decision == CommitmentDecision.CONTINUE
        assert r.progress == pytest.approx(0.4)

    def test_frozen(self):
        r = self._make()
        with pytest.raises(AttributeError):
            r.decision = CommitmentDecision.SWITCH  # type: ignore[misc]

    def test_to_dict(self):
        r = self._make()
        d = r.to_dict()
        assert d["decision"] == "continue"
        assert "active_objective_id" in d
        assert "switching_cost" in d
        assert "reason" in d

    def test_to_dict_with_candidate(self):
        r = self._make(candidate=_obj("cand"))
        d = r.to_dict()
        assert d["candidate_objective_id"] == "cand"
        assert d["candidate_score"] is not None

    def test_to_dict_no_candidate(self):
        r = self._make()
        d = r.to_dict()
        assert d["candidate_objective_id"] is None
        assert d["candidate_score"] is None

    def test_explanation(self):
        r = self._make(candidate=_obj("cand"))
        lines = r.explanation
        assert len(lines) >= 4
        assert "continue" in lines[0].lower()

    def test_explanation_no_candidate(self):
        r = self._make()
        lines = r.explanation
        assert any("Switching cost" in l for l in lines)


# ===========================================================================
# SECTION 6: CommitmentEngine — Switching Cost
# ===========================================================================


class TestCommitmentEngineSwitchingCost:
    def test_zero_progress_zero_time(self):
        engine = CommitmentEngine()
        sc = engine.compute_switching_cost(0.0, 0)
        assert sc.total_penalty == pytest.approx(0.0)

    def test_full_progress_full_time(self):
        engine = CommitmentEngine()
        sc = engine.compute_switching_cost(1.0, _DEFAULT_MAX_TICKS)
        assert sc.progress_penalty == pytest.approx(engine.progress_weight)
        assert sc.time_penalty == pytest.approx(engine.time_weight)
        assert sc.total_penalty == pytest.approx(1.0)

    def test_half_progress(self):
        engine = CommitmentEngine()
        sc = engine.compute_switching_cost(0.5, 0)
        assert sc.progress_penalty == pytest.approx(engine.progress_weight * 0.5)
        assert sc.time_penalty == pytest.approx(0.0)

    def test_half_time(self):
        engine = CommitmentEngine()
        sc = engine.compute_switching_cost(0.0, _DEFAULT_MAX_TICKS // 2)
        assert sc.progress_penalty == pytest.approx(0.0)
        assert sc.time_penalty > 0

    def test_higher_progress_higher_penalty(self):
        engine = CommitmentEngine()
        low = engine.compute_switching_cost(0.2, 5)
        high = engine.compute_switching_cost(0.8, 5)
        assert high.total_penalty > low.total_penalty

    def test_more_time_higher_penalty(self):
        engine = CommitmentEngine()
        low = engine.compute_switching_cost(0.3, 2)
        high = engine.compute_switching_cost(0.3, 40)
        assert high.total_penalty > low.total_penalty

    def test_progress_clamped(self):
        engine = CommitmentEngine()
        sc = engine.compute_switching_cost(1.5, 0)
        sc_normal = engine.compute_switching_cost(1.0, 0)
        assert sc.progress_penalty == pytest.approx(sc_normal.progress_penalty)

    def test_time_capped(self):
        engine = CommitmentEngine()
        sc = engine.compute_switching_cost(0.0, _DEFAULT_MAX_TICKS * 2)
        sc_max = engine.compute_switching_cost(0.0, _DEFAULT_MAX_TICKS)
        assert sc.time_penalty == pytest.approx(sc_max.time_penalty)


# ===========================================================================
# SECTION 7: CommitmentEngine — decide()
# ===========================================================================


class TestCommitmentEngineDecide:
    def test_continue_no_candidate(self):
        engine = CommitmentEngine()
        state = _state(progress=0.5, start_tick=0)
        result = engine.decide(state, None, 10)
        assert result.decision == CommitmentDecision.CONTINUE

    def test_continue_candidate_not_better_enough(self):
        engine = CommitmentEngine()
        state = _state(oid="a", progress=0.5, start_tick=0, priority=8, value=2.0)
        candidate = _obj("b", priority=8, value=2.0)
        result = engine.decide(state, candidate, 10)
        assert result.decision == CommitmentDecision.CONTINUE

    def test_switch_much_better_candidate(self):
        engine = CommitmentEngine()
        state = _state(oid="a", progress=0.0, start_tick=0, priority=1, value=0.1)
        candidate = _obj("b", priority=10, value=5.0)
        result = engine.decide(state, candidate, 1)
        assert result.decision == CommitmentDecision.SWITCH

    def test_switch_suppressed_by_high_progress(self):
        engine = CommitmentEngine()
        state = _state(oid="a", progress=0.9, start_tick=0, priority=3, value=0.5)
        candidate = _obj("b", priority=7, value=2.0)
        result = engine.decide(state, candidate, 45)
        assert result.decision == CommitmentDecision.CONTINUE

    def test_abandon_low_score_no_progress(self):
        engine = CommitmentEngine()
        state = _state(oid="a", progress=0.0, start_tick=0, priority=1, value=0.05, effort=5.0)
        result = engine.decide(state, None, 10)
        assert result.decision == CommitmentDecision.ABANDON

    def test_abandon_stalled(self):
        engine = CommitmentEngine()
        state = _state(oid="a", progress=0.05, start_tick=0, priority=5, value=1.0)
        result = engine.decide(state, None, 30)
        assert result.decision == CommitmentDecision.ABANDON

    def test_no_abandon_early(self):
        engine = CommitmentEngine()
        state = _state(oid="a", progress=0.0, start_tick=0, priority=1, value=0.1)
        result = engine.decide(state, None, 2)
        assert result.decision == CommitmentDecision.CONTINUE

    def test_no_abandon_with_progress(self):
        engine = CommitmentEngine()
        state = _state(oid="a", progress=0.5, start_tick=0, priority=3, value=0.5)
        result = engine.decide(state, None, 30)
        assert result.decision == CommitmentDecision.CONTINUE

    def test_result_has_switching_cost(self):
        engine = CommitmentEngine()
        state = _state(progress=0.3, start_tick=0)
        result = engine.decide(state, _obj("b"), 10)
        assert isinstance(result.switching_cost, SwitchingCost)
        assert result.switching_cost.total_penalty >= 0

    def test_result_has_score_gap(self):
        engine = CommitmentEngine()
        state = _state(progress=0.0, start_tick=0, priority=3)
        candidate = _obj("b", priority=8)
        result = engine.decide(state, candidate, 5)
        assert result.score_gap != 0.0

    def test_result_reason_not_empty(self):
        engine = CommitmentEngine()
        state = _state()
        result = engine.decide(state, None, 5)
        assert len(result.reason) > 0

    def test_same_objective_as_candidate_continues(self):
        engine = CommitmentEngine()
        obj = _obj("same")
        state = GoalState(
            active_objective=obj,
            start_tick=0,
            progress=0.3,
            commitment_score=0.5,
        )
        result = engine.decide(state, obj, 5)
        assert result.decision == CommitmentDecision.CONTINUE

    def test_deterministic(self):
        engine = CommitmentEngine()
        state = _state(progress=0.3, start_tick=0, priority=5)
        candidate = _obj("b", priority=7)
        r1 = engine.decide(state, candidate, 10)
        r2 = engine.decide(state, candidate, 10)
        assert r1.decision == r2.decision
        assert r1.score_gap == pytest.approx(r2.score_gap)

    def test_explanation_list(self):
        engine = CommitmentEngine()
        state = _state(progress=0.3)
        result = engine.decide(state, _obj("b", priority=9, value=5.0), 5)
        lines = result.explanation
        assert isinstance(lines, list)
        assert len(lines) >= 3


# ===========================================================================
# SECTION 8: CommitmentEngine — Properties
# ===========================================================================


class TestCommitmentEngineProperties:
    def test_default_weights(self):
        engine = CommitmentEngine()
        assert engine.progress_weight == pytest.approx(
            _DEFAULT_PROGRESS_WEIGHT / (_DEFAULT_PROGRESS_WEIGHT + _DEFAULT_TIME_WEIGHT)
        )
        assert engine.time_weight == pytest.approx(
            _DEFAULT_TIME_WEIGHT / (_DEFAULT_PROGRESS_WEIGHT + _DEFAULT_TIME_WEIGHT)
        )

    def test_custom_weights(self):
        engine = CommitmentEngine(progress_weight=0.8, time_weight=0.2)
        assert engine.progress_weight == pytest.approx(0.8)
        assert engine.time_weight == pytest.approx(0.2)

    def test_switch_threshold(self):
        engine = CommitmentEngine(switch_threshold=0.3)
        assert engine.switch_threshold == pytest.approx(0.3)

    def test_abandon_threshold(self):
        engine = CommitmentEngine(abandon_threshold=0.1)
        assert engine.abandon_threshold == pytest.approx(0.1)

    def test_max_ticks(self):
        engine = CommitmentEngine(max_ticks=100)
        assert engine.max_ticks == 100

    def test_min_improvement(self):
        engine = CommitmentEngine(min_improvement=0.1)
        assert engine.min_improvement == pytest.approx(0.1)

    def test_evaluator_default(self):
        engine = CommitmentEngine()
        assert isinstance(engine.evaluator, ObjectiveEvaluator)

    def test_custom_evaluator(self):
        ev = ObjectiveEvaluator()
        engine = CommitmentEngine(evaluator=ev)
        assert engine.evaluator is ev

    def test_threshold_clamped(self):
        engine = CommitmentEngine(switch_threshold=5.0)
        assert engine.switch_threshold == pytest.approx(1.0)

    def test_max_ticks_clamped(self):
        engine = CommitmentEngine(max_ticks=-10)
        assert engine.max_ticks == 1


# ===========================================================================
# SECTION 9: Advisor Integration
# ===========================================================================


class TestAdvisorIntegration:
    def _make_advisor(self, **kw):
        from umh.runtime.advisor import AdvisorRuntime
        from umh.runtime.arbitration import ArbitrationEngine
        from umh.runtime.meta_planner import MetaPlanner

        return AdvisorRuntime(
            arbitration_engine=kw.get("arb", ArbitrationEngine()),
            meta_planner=kw.get("mp", MetaPlanner()),
            commitment_engine=kw.get("ce", CommitmentEngine()),
            goal_state_manager=kw.get("gsm", GoalStateManager()),
        )

    def test_commitment_engine_property(self):
        advisor = self._make_advisor()
        assert advisor.commitment_engine is not None

    def test_goal_state_manager_property(self):
        advisor = self._make_advisor()
        assert advisor.goal_state_manager is not None

    def test_last_commitment_initially_none(self):
        advisor = self._make_advisor()
        assert advisor.last_commitment is None

    def test_tick_goal_committed_key(self):
        advisor = self._make_advisor()
        result = advisor.tick()
        assert "goal_committed" in result
        assert "goal_decision" in result

    def test_tick_no_objectives_no_commit(self):
        advisor = self._make_advisor()
        result = advisor.tick()
        assert result["goal_committed"] is False
        assert result["goal_decision"] is None

    def test_tick_selects_first_objective(self):
        advisor = self._make_advisor()
        advisor.add_objective(_obj("a", priority=8, value=3.0))
        advisor.add_objective(_obj("b", priority=5, value=1.0))
        result = advisor.tick()
        assert result["goal_committed"] is True
        assert result["goal_decision"] == "switch"
        assert advisor.goal_state_manager.has_active

    def test_tick_persists_across_ticks(self):
        advisor = self._make_advisor()
        advisor.add_objective(_obj("a", priority=8, value=3.0))
        advisor.tick()
        active_id = advisor.goal_state_manager.active.objective_id
        advisor.tick()
        assert advisor.goal_state_manager.active.objective_id == active_id

    def test_tick_continues_same_objective(self):
        advisor = self._make_advisor()
        advisor.add_objective(_obj("a", priority=8, value=3.0))
        advisor.tick()
        result2 = advisor.tick()
        assert result2["goal_decision"] == "continue"

    def test_tick_switches_to_much_better(self):
        advisor = self._make_advisor()
        advisor.add_objective(_obj("a", priority=2, value=0.1))
        advisor.tick()
        assert advisor.goal_state_manager.active.objective_id == "a"
        advisor.add_objective(_obj("b", priority=10, value=5.0))
        advisor.remove_objective("a")
        result2 = advisor.tick()
        assert result2["goal_decision"] == "switch"
        assert advisor.goal_state_manager.active.objective_id == "b"

    def test_get_state_with_goal(self):
        advisor = self._make_advisor()
        advisor.add_objective(_obj("a"))
        advisor.tick()
        state = advisor.get_state()
        assert "goal_state" in state

    def test_get_state_with_commitment(self):
        advisor = self._make_advisor()
        advisor.add_objective(_obj("a"))
        advisor.tick()
        advisor.tick()
        state = advisor.get_state()
        assert "commitment" in state

    def test_clear_resets_goal(self):
        advisor = self._make_advisor()
        advisor.add_objective(_obj("a"))
        advisor.tick()
        advisor.clear()
        assert not advisor.goal_state_manager.has_active
        assert advisor.last_commitment is None

    def test_no_commitment_engine_skips(self):
        from umh.runtime.advisor import AdvisorRuntime

        advisor = AdvisorRuntime()
        advisor.add_objective(_obj("a"))
        result = advisor.tick()
        assert result["goal_committed"] is False

    def test_goal_manager_default_created(self):
        from umh.runtime.advisor import AdvisorRuntime

        advisor = AdvisorRuntime()
        assert advisor.goal_state_manager is not None


# ===========================================================================
# SECTION 10: Commitment Suppresses Thrashing
# ===========================================================================


class TestAntiThrashing:
    def test_moderate_candidate_suppressed_by_progress(self):
        engine = CommitmentEngine()
        state = _state(oid="a", progress=0.6, start_tick=0, priority=5, value=1.5)
        candidate = _obj("b", priority=7, value=2.0)
        result = engine.decide(state, candidate, 20)
        assert result.decision == CommitmentDecision.CONTINUE

    def test_near_completion_never_switches(self):
        engine = CommitmentEngine()
        state = _state(oid="a", progress=0.95, start_tick=0, priority=3, value=1.0)
        candidate = _obj("b", priority=9, value=4.0)
        result = engine.decide(state, candidate, 48)
        assert result.decision == CommitmentDecision.CONTINUE

    def test_oscillation_prevented(self):
        engine = CommitmentEngine()
        obj_a = _obj("a", priority=6, value=2.0)
        obj_b = _obj("b", priority=7, value=2.2)

        state_a = GoalState(
            active_objective=obj_a,
            start_tick=0,
            progress=0.3,
            commitment_score=0.5,
        )
        r1 = engine.decide(state_a, obj_b, 10)

        state_b = GoalState(
            active_objective=obj_b,
            start_tick=10,
            progress=0.3,
            commitment_score=0.5,
        )
        r2 = engine.decide(state_b, obj_a, 20)

        both_switch = (
            r1.decision == CommitmentDecision.SWITCH and r2.decision == CommitmentDecision.SWITCH
        )
        assert not both_switch

    def test_low_progress_allows_switch(self):
        engine = CommitmentEngine()
        state = _state(oid="a", progress=0.0, start_tick=0, priority=2, value=0.5)
        candidate = _obj("b", priority=9, value=4.0)
        result = engine.decide(state, candidate, 1)
        assert result.decision == CommitmentDecision.SWITCH


# ===========================================================================
# SECTION 11: Hard Invariants 101-105
# ===========================================================================


class TestHardInvariants:
    def test_inv101_goal_state_isolated_from_execution(self):
        """Goal state module must not import execution-layer modules."""
        import umh.runtime.goal_state as mod

        source = open(mod.__file__).read()
        tree = ast.parse(source)
        forbidden = {"umh.cells", "umh.environments", "umh.adapters"}
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    for prefix in forbidden:
                        assert not node.module.startswith(prefix), (
                            f"goal_state.py imports {node.module}"
                        )

    def test_inv101_commitment_isolated_from_execution(self):
        """Commitment module must not import execution-layer modules."""
        import umh.runtime.commitment as mod

        source = open(mod.__file__).read()
        tree = ast.parse(source)
        forbidden = {"umh.cells", "umh.environments", "umh.adapters"}
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    for prefix in forbidden:
                        assert not node.module.startswith(prefix), (
                            f"commitment.py imports {node.module}"
                        )

    def test_inv102_commitment_deterministic(self):
        """Same inputs always produce the same decision."""
        engine = CommitmentEngine()
        state = _state(progress=0.3, start_tick=0, priority=5)
        candidate = _obj("b", priority=7, value=2.0)
        results = [engine.decide(state, candidate, 10) for _ in range(10)]
        decisions = {r.decision for r in results}
        assert len(decisions) == 1
        gaps = {round(r.score_gap, 8) for r in results}
        assert len(gaps) == 1

    def test_inv103_progress_updates_explicit(self):
        """Progress only changes via explicit update_progress call."""
        mgr = GoalStateManager()
        mgr.set_active(_obj(), start_tick=0)
        p0 = mgr.active.progress

        engine = CommitmentEngine()
        engine.decide(mgr.active, _obj("b"), 5)

        assert mgr.active.progress == pytest.approx(p0)

    def test_inv104_switching_explainable(self):
        """Every CommitmentResult has a non-empty reason and score_gap."""
        engine = CommitmentEngine()
        state = _state(progress=0.0, start_tick=0, priority=1, value=0.1)
        candidate = _obj("b", priority=10, value=5.0)
        result = engine.decide(state, candidate, 1)
        assert result.decision == CommitmentDecision.SWITCH
        assert len(result.reason) > 0
        assert result.score_gap > 0
        assert result.net_improvement > 0

    def test_inv104_continue_explainable(self):
        engine = CommitmentEngine()
        state = _state(progress=0.5, start_tick=0)
        result = engine.decide(state, None, 10)
        assert result.decision == CommitmentDecision.CONTINUE
        assert len(result.reason) > 0

    def test_inv104_abandon_explainable(self):
        engine = CommitmentEngine()
        state = _state(progress=0.0, start_tick=0, priority=1, value=0.05, effort=5.0)
        result = engine.decide(state, None, 10)
        assert result.decision == CommitmentDecision.ABANDON
        assert len(result.reason) > 0

    def test_inv105_no_execution_side_effects(self):
        """decide() must not mutate any state."""
        mgr = GoalStateManager()
        mgr.set_active(_obj("a"), start_tick=0)
        mgr.update_progress(0.3)
        active_before = mgr.active

        engine = CommitmentEngine()
        candidate = _obj("b", priority=10, value=5.0)
        engine.decide(active_before, candidate, 5)

        assert mgr.active.progress == pytest.approx(0.3)
        assert mgr.active.objective_id == "a"

    def test_inv105_no_subprocess_in_goal_state(self):
        import umh.runtime.goal_state as mod

        source = open(mod.__file__).read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    assert "subprocess" not in node.module

    def test_inv105_no_subprocess_in_commitment(self):
        import umh.runtime.commitment as mod

        source = open(mod.__file__).read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    assert "subprocess" not in node.module


# ===========================================================================
# SECTION 12: Boundary / Export Checks
# ===========================================================================


class TestBoundaryChecks:
    def test_import_goal_state(self):
        from umh.runtime.goal_state import GoalState, GoalStateManager

        assert GoalState is not None
        assert GoalStateManager is not None

    def test_import_commitment(self):
        from umh.runtime.commitment import (
            CommitmentDecision,
            CommitmentEngine,
            CommitmentResult,
            SwitchingCost,
        )

        assert CommitmentDecision is not None
        assert CommitmentEngine is not None
        assert CommitmentResult is not None
        assert SwitchingCost is not None

    def test_import_from_runtime(self):
        from umh.runtime import (
            CommitmentDecision,
            CommitmentEngine,
            CommitmentResult,
            GoalState,
            GoalStateManager,
            SwitchingCost,
        )

        assert CommitmentDecision is not None
        assert GoalState is not None

    def test_compile_goal_state(self):
        import py_compile

        py_compile.compile("umh/runtime/goal_state.py", doraise=True)

    def test_compile_commitment(self):
        import py_compile

        py_compile.compile("umh/runtime/commitment.py", doraise=True)

    def test_compile_advisor(self):
        import py_compile

        py_compile.compile("umh/runtime/advisor.py", doraise=True)

    def test_compile_init(self):
        import py_compile

        py_compile.compile("umh/runtime/__init__.py", doraise=True)

    def test_all_exports_in_init(self):
        import umh.runtime as rt

        for name in [
            "CommitmentDecision",
            "CommitmentEngine",
            "CommitmentResult",
            "GoalState",
            "GoalStateManager",
            "SwitchingCost",
        ]:
            assert name in rt.__all__, f"{name} missing from __all__"

    def test_end_to_end_pipeline(self):
        """Full pipeline: set goal → decide → switch → decide → continue."""
        mgr = GoalStateManager()
        engine = CommitmentEngine()

        obj_a = _obj("a", priority=3, value=1.0)
        obj_b = _obj("b", priority=9, value=4.0)

        mgr.set_active(obj_a, start_tick=1)

        r1 = engine.decide(mgr.active, obj_b, 2)
        assert r1.decision == CommitmentDecision.SWITCH

        mgr.set_active(obj_b, start_tick=2)
        mgr.update_progress(0.4)

        r2 = engine.decide(mgr.active, obj_a, 10)
        assert r2.decision == CommitmentDecision.CONTINUE

    def test_end_to_end_advisor(self):
        """Advisor tick with commitment engine — full integration."""
        from umh.runtime.advisor import AdvisorRuntime
        from umh.runtime.arbitration import ArbitrationEngine
        from umh.runtime.meta_planner import MetaPlanner

        advisor = AdvisorRuntime(
            arbitration_engine=ArbitrationEngine(),
            meta_planner=MetaPlanner(),
            commitment_engine=CommitmentEngine(),
        )
        advisor.add_objective(_obj("a", priority=8, value=3.0))
        advisor.add_objective(_obj("b", priority=5, value=1.0))

        r1 = advisor.tick()
        assert r1["goal_committed"] is True
        first_active = advisor.goal_state_manager.active.objective_id

        r2 = advisor.tick()
        assert r2["goal_committed"] is True
        assert advisor.goal_state_manager.active.objective_id == first_active
