"""Phase 30 — Goal Arbitration + Objective Selection Layer v1.

Tests for Objective, ObjectiveScore, ArbitrationWeights, ArbitrationResult,
ObjectiveEvaluator, ObjectiveRanker, ArbitrationEngine, advisor integration,
hard invariants 85-89, and boundary/export checks.

Target: 80-120 tests. Zero tolerance for regressions.
"""

from __future__ import annotations

import ast
import importlib
import sys
import textwrap

import pytest

sys.path.insert(0, "/opt/OS")

from umh.runtime.arbitration import (
    ArbitrationEngine,
    ArbitrationResult,
    ArbitrationWeights,
    Objective,
    ObjectiveEvaluator,
    ObjectiveRanker,
    ObjectiveScore,
    _DEFAULT_EFFORT_WEIGHT,
    _DEFAULT_IMPORTANCE_WEIGHT,
    _DEFAULT_PRIORITY,
    _DEFAULT_URGENCY_WEIGHT,
    _DEFAULT_VALUE_WEIGHT,
    _MAX_PRIORITY,
    _MIN_PRIORITY,
)


# ── Objective ────────────────────────────────────────────────────────


class TestObjective:
    def test_create_defaults(self):
        o = Objective(objective_id="o1", description="test goal")
        assert o.objective_id == "o1"
        assert o.description == "test goal"
        assert o.priority == _DEFAULT_PRIORITY
        assert o.deadline == ""
        assert o.effort_estimate == 1.0
        assert o.expected_value == 1.0
        assert o.source == ""
        assert o.metadata == {}

    def test_create_full(self):
        o = Objective(
            objective_id="o2",
            description="deploy v2",
            priority=8,
            deadline="2026-05-10",
            effort_estimate=3.5,
            expected_value=0.9,
            source="user",
            metadata={"tag": "deploy"},
        )
        assert o.priority == 8
        assert o.deadline == "2026-05-10"
        assert o.effort_estimate == 3.5
        assert o.expected_value == 0.9
        assert o.source == "user"
        assert o.metadata == {"tag": "deploy"}

    def test_frozen(self):
        o = Objective(objective_id="o1", description="x")
        with pytest.raises(AttributeError):
            o.priority = 10  # type: ignore[misc]

    def test_to_dict(self):
        o = Objective(objective_id="o1", description="x", priority=7)
        d = o.to_dict()
        assert d["objective_id"] == "o1"
        assert d["description"] == "x"
        assert d["priority"] == 7
        assert "effort_estimate" in d
        assert "expected_value" in d
        assert "source" in d

    def test_to_dict_rounds(self):
        o = Objective(
            objective_id="o1",
            description="x",
            effort_estimate=1.123456789,
            expected_value=0.987654321,
        )
        d = o.to_dict()
        assert d["effort_estimate"] == round(1.123456789, 4)
        assert d["expected_value"] == round(0.987654321, 4)


# ── ObjectiveScore ───────────────────────────────────────────────────


class TestObjectiveScore:
    def test_create(self):
        s = ObjectiveScore(
            objective_id="o1",
            urgency_score=0.8,
            importance_score=0.7,
            value_score=0.9,
            effort_score=0.5,
            total_score=0.73,
        )
        assert s.objective_id == "o1"
        assert s.urgency_score == 0.8
        assert s.total_score == 0.73
        assert s.factors == ()

    def test_frozen(self):
        s = ObjectiveScore(
            objective_id="o1",
            urgency_score=0.8,
            importance_score=0.7,
            value_score=0.9,
            effort_score=0.5,
            total_score=0.73,
        )
        with pytest.raises(AttributeError):
            s.total_score = 1.0  # type: ignore[misc]

    def test_to_dict(self):
        s = ObjectiveScore(
            objective_id="o1",
            urgency_score=0.8,
            importance_score=0.7,
            value_score=0.9,
            effort_score=0.5,
            total_score=0.73,
            factors=("high urgency", "strong value"),
        )
        d = s.to_dict()
        assert d["objective_id"] == "o1"
        assert isinstance(d["factors"], list)
        assert len(d["factors"]) == 2
        assert d["total_score"] == 0.73

    def test_to_dict_rounds(self):
        s = ObjectiveScore(
            objective_id="o1",
            urgency_score=0.123456789,
            importance_score=0.0,
            value_score=0.0,
            effort_score=0.0,
            total_score=0.999999999,
        )
        d = s.to_dict()
        assert d["urgency_score"] == round(0.123456789, 4)
        assert d["total_score"] == round(0.999999999, 4)

    def test_with_factors(self):
        s = ObjectiveScore(
            objective_id="o1",
            urgency_score=0.8,
            importance_score=0.7,
            value_score=0.9,
            effort_score=0.5,
            total_score=0.73,
            factors=("high urgency — deadline approaching",),
        )
        assert len(s.factors) == 1
        assert "deadline" in s.factors[0]


# ── ArbitrationWeights ───────────────────────────────────────────────


class TestArbitrationWeights:
    def test_defaults(self):
        w = ArbitrationWeights()
        assert w.urgency == _DEFAULT_URGENCY_WEIGHT
        assert w.importance == _DEFAULT_IMPORTANCE_WEIGHT
        assert w.value == _DEFAULT_VALUE_WEIGHT
        assert w.effort == _DEFAULT_EFFORT_WEIGHT

    def test_custom(self):
        w = ArbitrationWeights(urgency=0.5, importance=0.2, value=0.2, effort=0.1)
        assert w.urgency == 0.5
        assert w.effort == 0.1

    def test_frozen(self):
        w = ArbitrationWeights()
        with pytest.raises(AttributeError):
            w.urgency = 0.9  # type: ignore[misc]

    def test_to_dict(self):
        w = ArbitrationWeights()
        d = w.to_dict()
        assert set(d.keys()) == {"urgency", "importance", "value", "effort"}
        assert all(isinstance(v, float) for v in d.values())


# ── ArbitrationResult ────────────────────────────────────────────────


class TestArbitrationResult:
    def _make_result(self) -> ArbitrationResult:
        obj = Objective(objective_id="o1", description="goal A")
        score = ObjectiveScore(
            objective_id="o1",
            urgency_score=0.8,
            importance_score=0.5,
            value_score=0.7,
            effort_score=0.4,
            total_score=0.62,
            factors=("high urgency",),
        )
        other = ObjectiveScore(
            objective_id="o2",
            urgency_score=0.3,
            importance_score=0.5,
            value_score=0.5,
            effort_score=0.5,
            total_score=0.44,
        )
        return ArbitrationResult(
            selected=obj,
            selected_score=score,
            all_scores=(score, other),
            reason="high urgency",
        )

    def test_create(self):
        r = self._make_result()
        assert r.selected.objective_id == "o1"
        assert r.reason == "high urgency"
        assert len(r.all_scores) == 2

    def test_frozen(self):
        r = self._make_result()
        with pytest.raises(AttributeError):
            r.reason = "new"  # type: ignore[misc]

    def test_to_dict(self):
        r = self._make_result()
        d = r.to_dict()
        assert d["candidates_evaluated"] == 2
        assert d["selected"]["objective_id"] == "o1"
        assert d["reason"] == "high urgency"
        assert len(d["all_scores"]) == 2

    def test_explanation(self):
        r = self._make_result()
        lines = r.explanation
        assert len(lines) >= 2
        assert "goal A" in lines[0]
        assert "0.62" in lines[0]

    def test_explanation_markers(self):
        r = self._make_result()
        lines = r.explanation
        marker_lines = [l for l in lines if l.startswith(">>>") or l.startswith("   ")]
        assert any(">>>" in l and "o1" in l for l in marker_lines)
        assert any(l.startswith("   ") and "o2" in l for l in marker_lines)


# ── ObjectiveEvaluator ───────────────────────────────────────────────


class TestObjectiveEvaluator:
    def test_score_basic(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        o = Objective(objective_id="o1", description="test")
        s = ev.score(o)
        assert 0.0 <= s.total_score <= 1.0
        assert s.objective_id == "o1"

    def test_urgency_no_deadline(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        o = Objective(objective_id="o1", description="test")
        s = ev.score(o)
        assert s.urgency_score == 0.3

    def test_urgency_past_deadline(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        o = Objective(objective_id="o1", description="test", deadline="2026-04-29")
        s = ev.score(o)
        assert s.urgency_score == 1.0

    def test_urgency_same_day_deadline(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        o = Objective(objective_id="o1", description="test", deadline="2026-04-30")
        s = ev.score(o)
        assert s.urgency_score == 1.0

    def test_urgency_near_deadline(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-20T12:00:00Z")
        o = Objective(objective_id="o1", description="test", deadline="2026-04-25")
        s = ev.score(o)
        assert s.urgency_score == 0.8

    def test_urgency_far_deadline(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-01T12:00:00Z")
        o = Objective(objective_id="o1", description="test", deadline="2026-06-01")
        s = ev.score(o)
        assert s.urgency_score == 0.5

    def test_importance_min_priority(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        o = Objective(objective_id="o1", description="test", priority=1)
        s = ev.score(o)
        assert s.importance_score == 1 / _MAX_PRIORITY

    def test_importance_max_priority(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        o = Objective(objective_id="o1", description="test", priority=10)
        s = ev.score(o)
        assert s.importance_score == 1.0

    def test_importance_clamped_below(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        o = Objective(objective_id="o1", description="test", priority=-5)
        s = ev.score(o)
        assert s.importance_score == _MIN_PRIORITY / _MAX_PRIORITY

    def test_importance_clamped_above(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        o = Objective(objective_id="o1", description="test", priority=99)
        s = ev.score(o)
        assert s.importance_score == 1.0

    def test_value_normal(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        o = Objective(objective_id="o1", description="test", expected_value=0.7)
        s = ev.score(o)
        assert s.value_score == 0.7

    def test_value_clamped_high(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        o = Objective(objective_id="o1", description="test", expected_value=5.0)
        s = ev.score(o)
        assert s.value_score == 1.0

    def test_value_clamped_low(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        o = Objective(objective_id="o1", description="test", expected_value=-1.0)
        s = ev.score(o)
        assert s.value_score == 0.0

    def test_effort_low(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        o = Objective(objective_id="o1", description="test", effort_estimate=0.0)
        s = ev.score(o)
        assert s.effort_score == 1.0

    def test_effort_high(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        o = Objective(objective_id="o1", description="test", effort_estimate=9.0)
        s = ev.score(o)
        assert s.effort_score == 0.1

    def test_effort_negative_clamped(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        o = Objective(objective_id="o1", description="test", effort_estimate=-5.0)
        s = ev.score(o)
        assert s.effort_score == 1.0

    def test_weights_property(self):
        w = ArbitrationWeights(urgency=0.5, importance=0.2, value=0.2, effort=0.1)
        ev = ObjectiveEvaluator(weights=w, reference_time="2026-04-30T12:00:00Z")
        rw = ev.weights
        total = 0.5 + 0.2 + 0.2 + 0.1
        assert abs(rw.urgency - 0.5 / total) < 1e-9
        assert abs(rw.effort - 0.1 / total) < 1e-9

    def test_weights_normalized(self):
        w = ArbitrationWeights(urgency=2.0, importance=2.0, value=2.0, effort=2.0)
        ev = ObjectiveEvaluator(weights=w, reference_time="2026-04-30T12:00:00Z")
        rw = ev.weights
        assert abs(rw.urgency - 0.25) < 1e-9

    def test_weights_zero_total(self):
        w = ArbitrationWeights(urgency=0.0, importance=0.0, value=0.0, effort=0.0)
        ev = ObjectiveEvaluator(weights=w, reference_time="2026-04-30T12:00:00Z")
        o = Objective(objective_id="o1", description="test")
        s = ev.score(o)
        assert s.total_score == 0.0

    def test_factors_high_urgency(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        o = Objective(objective_id="o1", description="test", deadline="2026-04-29")
        s = ev.score(o)
        assert any("high urgency" in f for f in s.factors)
        assert any("deadline" in f for f in s.factors)

    def test_factors_moderate_urgency(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-01T12:00:00Z")
        o = Objective(objective_id="o1", description="test", deadline="2026-06-01")
        s = ev.score(o)
        assert any("moderate urgency" in f for f in s.factors)

    def test_factors_high_priority(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        o = Objective(objective_id="o1", description="test", priority=8)
        s = ev.score(o)
        assert any("high priority" in f for f in s.factors)

    def test_factors_strong_value(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        o = Objective(objective_id="o1", description="test", expected_value=0.9)
        s = ev.score(o)
        assert any("strong expected value" in f for f in s.factors)

    def test_factors_low_effort(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        o = Objective(objective_id="o1", description="test", effort_estimate=0.5)
        s = ev.score(o)
        assert any("low effort" in f for f in s.factors)

    def test_factors_high_effort(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        o = Objective(objective_id="o1", description="test", effort_estimate=5.0)
        s = ev.score(o)
        assert any("high effort" in f for f in s.factors)

    def test_score_deterministic(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        o = Objective(objective_id="o1", description="test", priority=7, expected_value=0.6)
        s1 = ev.score(o)
        s2 = ev.score(o)
        assert s1.total_score == s2.total_score

    def test_score_weighted_sum(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        o = Objective(objective_id="o1", description="test")
        s = ev.score(o)
        w = ev.weights
        expected = (
            w.urgency * s.urgency_score
            + w.importance * s.importance_score
            + w.value * s.value_score
            + w.effort * s.effort_score
        )
        assert abs(s.total_score - expected) < 1e-9


# ── ObjectiveRanker ──────────────────────────────────────────────────


class TestObjectiveRanker:
    def test_rank_basic(self):
        ranker = ObjectiveRanker()
        objs = [
            Objective(objective_id="low", description="low", priority=2),
            Objective(objective_id="high", description="high", priority=9, expected_value=0.9),
        ]
        ranked = ranker.rank(objs)
        assert ranked[0].objective_id == "high"

    def test_rank_empty(self):
        ranker = ObjectiveRanker()
        ranked = ranker.rank([])
        assert ranked == []

    def test_rank_single(self):
        ranker = ObjectiveRanker()
        objs = [Objective(objective_id="only", description="only one")]
        ranked = ranker.rank(objs)
        assert len(ranked) == 1
        assert ranked[0].objective_id == "only"

    def test_rank_order_descending(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        ranker = ObjectiveRanker(evaluator=ev)
        objs = [
            Objective(objective_id="a", description="a", priority=3, expected_value=0.2),
            Objective(objective_id="b", description="b", priority=9, expected_value=0.9),
            Objective(objective_id="c", description="c", priority=5, expected_value=0.5),
        ]
        ranked = ranker.rank(objs)
        scores = [s.total_score for s in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_rank_tie_break_by_id(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        ranker = ObjectiveRanker(evaluator=ev)
        objs = [
            Objective(objective_id="beta", description="beta"),
            Objective(objective_id="alpha", description="alpha"),
        ]
        ranked = ranker.rank(objs)
        assert ranked[0].objective_id == "alpha"
        assert ranked[1].objective_id == "beta"

    def test_rank_deterministic(self):
        ranker = ObjectiveRanker()
        objs = [
            Objective(objective_id="x", description="x", priority=7),
            Objective(objective_id="y", description="y", priority=3),
            Objective(objective_id="z", description="z", priority=5),
        ]
        r1 = ranker.rank(objs)
        r2 = ranker.rank(objs)
        assert [s.objective_id for s in r1] == [s.objective_id for s in r2]

    def test_evaluator_property(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        ranker = ObjectiveRanker(evaluator=ev)
        assert ranker.evaluator is ev


# ── ArbitrationEngine ────────────────────────────────────────────────


class TestArbitrationEngine:
    def test_select_basic(self):
        engine = ArbitrationEngine()
        objs = [
            Objective(objective_id="o1", description="low priority", priority=2),
            Objective(
                objective_id="o2", description="high priority", priority=9, expected_value=0.9
            ),
        ]
        result = engine.select(objs)
        assert result is not None
        assert result.selected.objective_id == "o2"

    def test_select_empty(self):
        engine = ArbitrationEngine()
        result = engine.select([])
        assert result is None

    def test_select_single(self):
        engine = ArbitrationEngine()
        objs = [Objective(objective_id="only", description="sole objective", priority=5)]
        result = engine.select(objs)
        assert result is not None
        assert result.selected.objective_id == "only"

    def test_select_returns_all_scores(self):
        engine = ArbitrationEngine()
        objs = [
            Objective(objective_id="o1", description="a", priority=3),
            Objective(objective_id="o2", description="b", priority=7),
            Objective(objective_id="o3", description="c", priority=5),
        ]
        result = engine.select(objs)
        assert result is not None
        assert len(result.all_scores) == 3

    def test_select_deterministic(self):
        engine = ArbitrationEngine()
        objs = [
            Objective(objective_id="o1", description="a", priority=5),
            Objective(objective_id="o2", description="b", priority=5),
        ]
        r1 = engine.select(objs)
        r2 = engine.select(objs)
        assert r1 is not None and r2 is not None
        assert r1.selected.objective_id == r2.selected.objective_id

    def test_reason_has_factors(self):
        engine = ArbitrationEngine()
        objs = [
            Objective(
                objective_id="o1",
                description="urgent",
                priority=9,
                deadline="2026-04-29",
                expected_value=0.9,
            ),
        ]
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        engine_custom = ArbitrationEngine(evaluator=ev)
        result = engine_custom.select(objs)
        assert result is not None
        assert len(result.reason) > 0

    def test_reason_narrow_margin(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        engine = ArbitrationEngine(evaluator=ev)
        objs = [
            Objective(objective_id="o1", description="a", priority=5, expected_value=0.5),
            Objective(objective_id="o2", description="b", priority=5, expected_value=0.5),
        ]
        result = engine.select(objs)
        assert result is not None
        assert "narrow margin" in result.reason

    def test_reason_high_user_priority(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        engine = ArbitrationEngine(evaluator=ev)
        objs = [
            Objective(objective_id="o1", description="critical", priority=9),
        ]
        result = engine.select(objs)
        assert result is not None
        assert "user-assigned high priority" in result.reason

    def test_explanation_lines(self):
        engine = ArbitrationEngine()
        objs = [
            Objective(objective_id="o1", description="a", priority=7),
            Objective(objective_id="o2", description="b", priority=3),
        ]
        result = engine.select(objs)
        assert result is not None
        lines = result.explanation
        assert len(lines) >= 4

    def test_custom_evaluator(self):
        ev = ObjectiveEvaluator(
            weights=ArbitrationWeights(urgency=0.0, importance=1.0, value=0.0, effort=0.0),
            reference_time="2026-04-30T12:00:00Z",
        )
        engine = ArbitrationEngine(evaluator=ev)
        objs = [
            Objective(objective_id="o1", description="low", priority=2),
            Objective(objective_id="o2", description="high", priority=9),
        ]
        result = engine.select(objs)
        assert result is not None
        assert result.selected.objective_id == "o2"

    def test_custom_ranker(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        ranker = ObjectiveRanker(evaluator=ev)
        engine = ArbitrationEngine(ranker=ranker)
        assert engine.ranker is ranker
        assert engine.evaluator is ev

    def test_properties(self):
        engine = ArbitrationEngine()
        assert engine.evaluator is not None
        assert engine.ranker is not None

    def test_select_high_urgency_wins(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        engine = ArbitrationEngine(evaluator=ev)
        objs = [
            Objective(
                objective_id="overdue",
                description="overdue task",
                priority=5,
                deadline="2026-04-28",
            ),
            Objective(
                objective_id="future", description="future task", priority=5, deadline="2026-12-31"
            ),
        ]
        result = engine.select(objs)
        assert result is not None
        assert result.selected.objective_id == "overdue"

    def test_select_effort_matters(self):
        ev = ObjectiveEvaluator(
            weights=ArbitrationWeights(urgency=0.0, importance=0.0, value=0.0, effort=1.0),
            reference_time="2026-04-30T12:00:00Z",
        )
        engine = ArbitrationEngine(evaluator=ev)
        objs = [
            Objective(objective_id="easy", description="easy", effort_estimate=0.1),
            Objective(objective_id="hard", description="hard", effort_estimate=10.0),
        ]
        result = engine.select(objs)
        assert result is not None
        assert result.selected.objective_id == "easy"

    def test_to_dict(self):
        engine = ArbitrationEngine()
        objs = [
            Objective(objective_id="o1", description="a"),
            Objective(objective_id="o2", description="b"),
        ]
        result = engine.select(objs)
        assert result is not None
        d = result.to_dict()
        assert "selected" in d
        assert "reason" in d
        assert "candidates_evaluated" in d
        assert d["candidates_evaluated"] == 2

    def test_multiple_objectives(self):
        engine = ArbitrationEngine()
        objs = [
            Objective(objective_id=f"o{i}", description=f"goal {i}", priority=i)
            for i in range(1, 11)
        ]
        result = engine.select(objs)
        assert result is not None
        assert len(result.all_scores) == 10


# ── Advisor Integration ──────────────────────────────────────────────


class TestAdvisorIntegration:
    def _make_advisor(self, *, with_engine: bool = True):
        from umh.runtime.advisor import AdvisorRuntime

        engine = ArbitrationEngine() if with_engine else None
        return AdvisorRuntime(arbitration_engine=engine)

    def test_arbitration_engine_property(self):
        adv = self._make_advisor()
        assert adv.arbitration_engine is not None

    def test_no_engine_property(self):
        adv = self._make_advisor(with_engine=False)
        assert adv.arbitration_engine is None

    def test_objectives_empty(self):
        adv = self._make_advisor()
        assert adv.objectives == []

    def test_add_objective(self):
        adv = self._make_advisor()
        o = Objective(objective_id="o1", description="test")
        adv.add_objective(o)
        assert len(adv.objectives) == 1
        assert adv.objectives[0].objective_id == "o1"

    def test_add_multiple_objectives(self):
        adv = self._make_advisor()
        for i in range(5):
            adv.add_objective(Objective(objective_id=f"o{i}", description=f"goal {i}"))
        assert len(adv.objectives) == 5

    def test_remove_objective(self):
        adv = self._make_advisor()
        adv.add_objective(Objective(objective_id="o1", description="test"))
        adv.add_objective(Objective(objective_id="o2", description="test2"))
        removed = adv.remove_objective("o1")
        assert removed is True
        assert len(adv.objectives) == 1
        assert adv.objectives[0].objective_id == "o2"

    def test_remove_nonexistent(self):
        adv = self._make_advisor()
        removed = adv.remove_objective("nope")
        assert removed is False

    def test_last_arbitration_none_initially(self):
        adv = self._make_advisor()
        assert adv.last_arbitration is None

    def test_tick_objective_selected_key(self):
        adv = self._make_advisor()
        adv.add_objective(Objective(objective_id="o1", description="goal", priority=7))
        result = adv.tick()
        assert "objective_selected" in result

    def test_tick_selects_objective(self):
        adv = self._make_advisor()
        adv.add_objective(Objective(objective_id="o1", description="goal", priority=7))
        result = adv.tick()
        assert result["objective_selected"] is True
        assert adv.last_arbitration is not None
        assert adv.last_arbitration.selected.objective_id == "o1"

    def test_tick_no_engine_no_selection(self):
        adv = self._make_advisor(with_engine=False)
        adv.add_objective(Objective(objective_id="o1", description="goal"))
        result = adv.tick()
        assert result["objective_selected"] is False

    def test_tick_no_objectives_no_selection(self):
        adv = self._make_advisor()
        result = adv.tick()
        assert result["objective_selected"] is False

    def test_get_state_with_arbitration(self):
        adv = self._make_advisor()
        adv.add_objective(Objective(objective_id="o1", description="goal"))
        adv.tick()
        state = adv.get_state()
        assert "arbitration" in state
        assert "objectives_count" in state
        assert state["objectives_count"] == 1

    def test_get_state_no_arbitration(self):
        adv = self._make_advisor(with_engine=False)
        state = adv.get_state()
        assert "arbitration" not in state

    def test_clear_resets_arbitration(self):
        adv = self._make_advisor()
        adv.add_objective(Objective(objective_id="o1", description="goal"))
        adv.tick()
        assert adv.last_arbitration is not None
        adv.clear()
        assert adv.last_arbitration is None
        assert adv.objectives == []

    def test_objectives_returns_copy(self):
        adv = self._make_advisor()
        adv.add_objective(Objective(objective_id="o1", description="test"))
        objs = adv.objectives
        objs.append(Objective(objective_id="o2", description="test2"))
        assert len(adv.objectives) == 1


# ── Hard Invariants 85-89 ────────────────────────────────────────────


class TestHardInvariants:
    def test_inv85_arbitration_is_pure(self):
        """INV 85: Arbitration evaluation must be pure — no I/O."""
        engine = ArbitrationEngine()
        objs = [
            Objective(objective_id="o1", description="a", priority=5),
            Objective(objective_id="o2", description="b", priority=8),
        ]
        r1 = engine.select(objs)
        r2 = engine.select(objs)
        assert r1 is not None and r2 is not None
        assert r1.selected.objective_id == r2.selected.objective_id
        assert r1.selected_score.total_score == r2.selected_score.total_score

    def test_inv85_no_io_in_arbitration(self):
        """INV 85: No file I/O, no network, no subprocess in arbitration module."""
        source_path = "/opt/OS/umh/runtime/arbitration.py"
        with open(source_path) as f:
            source = f.read()
        tree = ast.parse(source)
        imported_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported_names.add(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.add(alias.name)
        for forbidden in ["subprocess", "socket", "urllib", "requests", "http"]:
            assert forbidden not in imported_names, (
                f"Forbidden import '{forbidden}' in arbitration.py"
            )
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "open":
                    raise AssertionError("Found open() call in arbitration.py")

    def test_inv86_no_side_effects(self):
        """INV 86: Arbitration must not mutate input objectives."""
        objs = [
            Objective(objective_id="o1", description="a", priority=5),
            Objective(objective_id="o2", description="b", priority=8),
        ]
        original_ids = [o.objective_id for o in objs]
        engine = ArbitrationEngine()
        engine.select(objs)
        assert [o.objective_id for o in objs] == original_ids
        assert len(objs) == 2

    def test_inv87_deterministic(self):
        """INV 87: Same inputs always produce same result."""
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        engine = ArbitrationEngine(evaluator=ev)
        objs = [
            Objective(objective_id="o1", description="a", priority=5, expected_value=0.7),
            Objective(objective_id="o2", description="b", priority=8, expected_value=0.4),
            Objective(objective_id="o3", description="c", priority=3, expected_value=0.9),
        ]
        results = [engine.select(objs) for _ in range(10)]
        ids = [r.selected.objective_id for r in results if r is not None]
        scores = [r.selected_score.total_score for r in results if r is not None]
        assert len(set(ids)) == 1
        assert len(set(scores)) == 1

    def test_inv88_no_mutation_of_state(self):
        """INV 88: ArbitrationEngine.select() doesn't store any state."""
        engine = ArbitrationEngine()
        objs_a = [Objective(objective_id="a", description="a", priority=9)]
        objs_b = [Objective(objective_id="b", description="b", priority=2)]
        r1 = engine.select(objs_a)
        r2 = engine.select(objs_b)
        assert r1 is not None and r2 is not None
        assert r1.selected.objective_id == "a"
        assert r2.selected.objective_id == "b"

    def test_inv89_no_forbidden_imports(self):
        """INV 89: No imports from umh/cells, umh/environments, umh/adapters."""
        source_path = "/opt/OS/umh/runtime/arbitration.py"
        with open(source_path) as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mod_name = ""
                if isinstance(node, ast.ImportFrom) and node.module:
                    mod_name = node.module
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        mod_name = alias.name
                for forbidden in ["umh.cells", "umh.environments", "umh.adapters", "subprocess"]:
                    assert not mod_name.startswith(forbidden), (
                        f"Forbidden import '{mod_name}' found in arbitration.py"
                    )


# ── Boundary / Export Checks ─────────────────────────────────────────


class TestBoundaryChecks:
    def test_import_from_runtime(self):
        from umh.runtime import (
            ArbitrationEngine,
            ArbitrationResult,
            ArbitrationWeights,
            Objective,
            ObjectiveEvaluator,
            ObjectiveRanker,
            ObjectiveScore,
        )

        assert ArbitrationEngine is not None
        assert Objective is not None

    def test_import_direct(self):
        from umh.runtime.arbitration import (
            ArbitrationEngine,
            ArbitrationResult,
            ArbitrationWeights,
            Objective,
            ObjectiveEvaluator,
            ObjectiveRanker,
            ObjectiveScore,
        )

        assert ArbitrationEngine is not None

    def test_compile_arbitration(self):
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/arbitration.py", doraise=True)

    def test_compile_advisor(self):
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/advisor.py", doraise=True)

    def test_compile_init(self):
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/__init__.py", doraise=True)

    def test_all_exports_in_init(self):
        from umh.runtime import __all__

        expected = [
            "ArbitrationEngine",
            "ArbitrationResult",
            "ArbitrationWeights",
            "Objective",
            "ObjectiveEvaluator",
            "ObjectiveRanker",
            "ObjectiveScore",
        ]
        for name in expected:
            assert name in __all__, f"{name} missing from __all__"

    def test_end_to_end_basic(self):
        """Full pipeline: create objectives → arbitrate → get result."""
        engine = ArbitrationEngine()
        objs = [
            Objective(
                objective_id="ship-feature",
                description="Ship v2 feature",
                priority=8,
                expected_value=0.9,
            ),
            Objective(
                objective_id="fix-bug",
                description="Fix critical bug",
                priority=10,
                deadline="2026-04-29",
                expected_value=0.7,
            ),
            Objective(
                objective_id="refactor",
                description="Refactor auth",
                priority=3,
                expected_value=0.4,
                effort_estimate=5.0,
            ),
        ]
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        engine = ArbitrationEngine(evaluator=ev)
        result = engine.select(objs)
        assert result is not None
        assert result.selected.objective_id in {"ship-feature", "fix-bug"}
        d = result.to_dict()
        assert d["candidates_evaluated"] == 3

    def test_end_to_end_advisor(self):
        """Full pipeline through advisor: add objectives → tick → check state."""
        from umh.runtime.advisor import AdvisorRuntime

        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        engine = ArbitrationEngine(evaluator=ev)
        adv = AdvisorRuntime(arbitration_engine=engine)
        adv.add_objective(Objective(objective_id="goal-1", description="Primary goal", priority=9))
        adv.add_objective(
            Objective(objective_id="goal-2", description="Secondary goal", priority=4)
        )
        result = adv.tick()
        assert result["objective_selected"] is True
        assert adv.last_arbitration is not None
        assert adv.last_arbitration.selected.objective_id == "goal-1"
        state = adv.get_state()
        assert state["objectives_count"] == 2
        assert "arbitration" in state
