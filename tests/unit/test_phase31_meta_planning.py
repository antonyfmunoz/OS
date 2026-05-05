"""Phase 31 — Goal Sequencing + Meta-Planning Layer v1.

Tests for SequenceStep, ObjectiveSequence, MetaPlanResult, MetaPlanWeights,
SequenceGenerator, SequenceEvaluator, MetaPlanner, advisor integration,
hard invariants 90-94, and boundary/export checks.

Target: 80-120 tests. Zero tolerance for regressions.
"""

from __future__ import annotations

import ast
import sys

import pytest

sys.path.insert(0, "/opt/OS")

from umh.runtime.arbitration import (
    ArbitrationWeights,
    Objective,
    ObjectiveEvaluator,
    ObjectiveScore,
)
from umh.runtime.meta_planner import (
    MetaPlanResult,
    MetaPlanWeights,
    MetaPlanner,
    ObjectiveSequence,
    SequenceEvaluator,
    SequenceGenerator,
    SequenceStep,
    _DEFAULT_DEPTH,
    _DEFAULT_DISCOUNT,
    _DEFAULT_TOP_K,
    _MAX_DEPTH,
    _MAX_SEQUENCES,
    _MAX_TOP_K,
    _MIN_DEPTH,
    _MIN_TOP_K,
)


def _obj(oid: str, priority: int = 5, value: float = 0.5, effort: float = 1.0) -> Objective:
    return Objective(
        objective_id=oid,
        description=f"goal {oid}",
        priority=priority,
        expected_value=value,
        effort_estimate=effort,
    )


def _make_score(oid: str, total: float = 0.5) -> ObjectiveScore:
    return ObjectiveScore(
        objective_id=oid,
        urgency_score=0.3,
        importance_score=0.5,
        value_score=0.5,
        effort_score=0.5,
        total_score=total,
    )


# ── SequenceStep ─────────────────────────────────────────────────────


class TestSequenceStep:
    def test_create(self):
        o = _obj("o1")
        sc = _make_score("o1")
        step = SequenceStep(
            step_index=0,
            objective=o,
            score=sc,
            discount=1.0,
            discounted_score=0.5,
        )
        assert step.step_index == 0
        assert step.objective.objective_id == "o1"
        assert step.discount == 1.0
        assert step.discounted_score == 0.5

    def test_frozen(self):
        o = _obj("o1")
        sc = _make_score("o1")
        step = SequenceStep(step_index=0, objective=o, score=sc, discount=1.0, discounted_score=0.5)
        with pytest.raises(AttributeError):
            step.step_index = 1  # type: ignore[misc]

    def test_to_dict(self):
        o = _obj("o1")
        sc = _make_score("o1")
        step = SequenceStep(
            step_index=0, objective=o, score=sc, discount=0.85, discounted_score=0.425
        )
        d = step.to_dict()
        assert d["step_index"] == 0
        assert d["objective_id"] == "o1"
        assert d["discount"] == 0.85
        assert "score" in d
        assert d["discounted_score"] == 0.425


# ── ObjectiveSequence ────────────────────────────────────────────────


class TestObjectiveSequence:
    def _make_seq(self) -> ObjectiveSequence:
        steps = (
            SequenceStep(0, _obj("a"), _make_score("a"), 1.0, 0.5),
            SequenceStep(1, _obj("b"), _make_score("b"), 0.85, 0.425),
        )
        return ObjectiveSequence(
            steps=steps, label="test-seq-0", total_score=0.65, cumulative_effort=2.0
        )

    def test_create(self):
        seq = self._make_seq()
        assert seq.label == "test-seq-0"
        assert seq.total_score == 0.65
        assert seq.cumulative_effort == 2.0

    def test_frozen(self):
        seq = self._make_seq()
        with pytest.raises(AttributeError):
            seq.total_score = 1.0  # type: ignore[misc]

    def test_depth(self):
        seq = self._make_seq()
        assert seq.depth == 2

    def test_first_objective(self):
        seq = self._make_seq()
        assert seq.first_objective.objective_id == "a"

    def test_objectives_list(self):
        seq = self._make_seq()
        objs = seq.objectives
        assert len(objs) == 2
        assert objs[0].objective_id == "a"
        assert objs[1].objective_id == "b"

    def test_to_dict(self):
        seq = self._make_seq()
        d = seq.to_dict()
        assert d["label"] == "test-seq-0"
        assert d["depth"] == 2
        assert d["total_score"] == 0.65
        assert d["cumulative_effort"] == 2.0
        assert len(d["steps"]) == 2

    def test_to_dict_rounds(self):
        steps = (SequenceStep(0, _obj("a"), _make_score("a"), 1.0, 0.123456789),)
        seq = ObjectiveSequence(
            steps=steps,
            label="x",
            total_score=0.987654321,
            cumulative_effort=1.111111111,
        )
        d = seq.to_dict()
        assert d["total_score"] == round(0.987654321, 4)
        assert d["cumulative_effort"] == round(1.111111111, 4)


# ── MetaPlanResult ───────────────────────────────────────────────────


class TestMetaPlanResult:
    def _make_result(self) -> MetaPlanResult:
        s1 = SequenceStep(0, _obj("a", priority=8), _make_score("a", 0.7), 1.0, 0.7)
        s2 = SequenceStep(1, _obj("b"), _make_score("b", 0.5), 0.85, 0.425)
        selected = ObjectiveSequence(
            steps=(s1, s2), label="seq-0", total_score=0.8, cumulative_effort=2.0
        )
        other = ObjectiveSequence(
            steps=(
                SequenceStep(0, _obj("b"), _make_score("b", 0.5), 1.0, 0.5),
                SequenceStep(1, _obj("a"), _make_score("a", 0.7), 0.85, 0.595),
            ),
            label="seq-1",
            total_score=0.75,
            cumulative_effort=2.0,
        )
        return MetaPlanResult(
            sequences=(selected, other),
            selected=selected,
            next_objective=_obj("a", priority=8),
            reason="strong first objective; manageable total effort",
            depth=2,
        )

    def test_create(self):
        r = self._make_result()
        assert r.selected.label == "seq-0"
        assert r.next_objective.objective_id == "a"
        assert r.depth == 2
        assert len(r.sequences) == 2

    def test_frozen(self):
        r = self._make_result()
        with pytest.raises(AttributeError):
            r.reason = "new"  # type: ignore[misc]

    def test_to_dict(self):
        r = self._make_result()
        d = r.to_dict()
        assert d["sequences_evaluated"] == 2
        assert d["next_objective"]["objective_id"] == "a"
        assert d["reason"] == "strong first objective; manageable total effort"
        assert d["depth"] == 2
        assert len(d["all_sequences"]) == 2

    def test_explanation(self):
        r = self._make_result()
        lines = r.explanation
        assert len(lines) >= 3
        assert "seq-0" in lines[0]
        assert "0.8" in lines[0]
        assert "a" in lines[1]

    def test_explanation_markers(self):
        r = self._make_result()
        lines = r.explanation
        marker_lines = [l for l in lines if l.startswith(">>>") or l.startswith("   ")]
        assert any(">>>" in l and "seq-0" in l for l in marker_lines)
        assert any(l.startswith("   ") and "seq-1" in l for l in marker_lines)

    def test_explanation_shows_arrow_chain(self):
        r = self._make_result()
        lines = r.explanation
        arrow_lines = [l for l in lines if "→" in l]
        assert len(arrow_lines) >= 1


# ── MetaPlanWeights ──────────────────────────────────────────────────


class TestMetaPlanWeights:
    def test_defaults(self):
        w = MetaPlanWeights()
        assert w.score_weight == 0.70
        assert w.effort_weight == 0.30

    def test_custom(self):
        w = MetaPlanWeights(score_weight=0.9, effort_weight=0.1)
        assert w.score_weight == 0.9

    def test_frozen(self):
        w = MetaPlanWeights()
        with pytest.raises(AttributeError):
            w.score_weight = 0.5  # type: ignore[misc]

    def test_to_dict(self):
        w = MetaPlanWeights()
        d = w.to_dict()
        assert set(d.keys()) == {"score_weight", "effort_weight"}
        assert all(isinstance(v, float) for v in d.values())


# ── SequenceGenerator ────────────────────────────────────────────────


class TestSequenceGenerator:
    def test_generate_basic(self):
        gen = SequenceGenerator()
        objs = [_obj("a", 7), _obj("b", 5), _obj("c", 3)]
        seqs = gen.generate(objs)
        assert len(seqs) > 0
        for seq in seqs:
            assert len(seq) >= _MIN_DEPTH

    def test_generate_empty(self):
        gen = SequenceGenerator()
        seqs = gen.generate([])
        assert seqs == []

    def test_generate_single_objective(self):
        gen = SequenceGenerator()
        objs = [_obj("a")]
        seqs = gen.generate(objs)
        assert len(seqs) == 0 or all(len(s) == 1 for s in seqs)

    def test_generate_two_objectives(self):
        gen = SequenceGenerator()
        objs = [_obj("a", 7), _obj("b", 5)]
        seqs = gen.generate(objs, depth=2)
        assert len(seqs) == 2
        ids_0 = [o.objective_id for o in seqs[0]]
        ids_1 = [o.objective_id for o in seqs[1]]
        assert ids_0 != ids_1

    def test_generate_respects_depth(self):
        gen = SequenceGenerator()
        objs = [_obj("a", 7), _obj("b", 5), _obj("c", 3)]
        seqs = gen.generate(objs, depth=2)
        for seq in seqs:
            assert len(seq) == 2

    def test_generate_clamps_depth_min(self):
        gen = SequenceGenerator()
        objs = [_obj("a"), _obj("b"), _obj("c")]
        seqs = gen.generate(objs, depth=1)
        for seq in seqs:
            assert len(seq) >= _MIN_DEPTH

    def test_generate_clamps_depth_max(self):
        gen = SequenceGenerator()
        objs = [_obj(f"o{i}", priority=i) for i in range(1, 7)]
        seqs = gen.generate(objs, depth=10)
        for seq in seqs:
            assert len(seq) <= _MAX_DEPTH

    def test_generate_top_k(self):
        gen = SequenceGenerator(top_k=2)
        objs = [_obj("a", 9), _obj("b", 7), _obj("c", 5), _obj("d", 3)]
        seqs = gen.generate(objs, depth=2)
        all_ids = set()
        for seq in seqs:
            for o in seq:
                all_ids.add(o.objective_id)
        assert len(all_ids) <= 2

    def test_generate_max_sequences_cap(self):
        gen = SequenceGenerator(top_k=5, max_sequences=10)
        objs = [_obj(f"o{i}", priority=10 - i) for i in range(6)]
        seqs = gen.generate(objs, depth=4)
        assert len(seqs) <= 10

    def test_generate_deterministic(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        gen = SequenceGenerator(evaluator=ev)
        objs = [_obj("a", 7), _obj("b", 5), _obj("c", 3)]
        s1 = gen.generate(objs, depth=3)
        s2 = gen.generate(objs, depth=3)
        assert len(s1) == len(s2)
        for seq1, seq2 in zip(s1, s2):
            ids1 = [o.objective_id for o in seq1]
            ids2 = [o.objective_id for o in seq2]
            assert ids1 == ids2

    def test_generate_no_duplicates_in_sequence(self):
        gen = SequenceGenerator()
        objs = [_obj("a", 7), _obj("b", 5), _obj("c", 3)]
        seqs = gen.generate(objs, depth=3)
        for seq in seqs:
            ids = [o.objective_id for o in seq]
            assert len(ids) == len(set(ids))

    def test_label_sequence(self):
        gen = SequenceGenerator()
        seq = [_obj("a", priority=9), _obj("b", priority=3)]
        label = gen.label_sequence(0, seq)
        assert "0" in label
        assert len(label) > 0

    def test_label_high_priority_lead(self):
        gen = SequenceGenerator()
        seq = [_obj("a", priority=9), _obj("b", priority=3)]
        label = gen.label_sequence(0, seq)
        assert "high-priority-lead" in label

    def test_label_moderate_lead(self):
        gen = SequenceGenerator()
        seq = [_obj("a", priority=5), _obj("b", priority=3)]
        label = gen.label_sequence(0, seq)
        assert "moderate-lead" in label

    def test_label_low_priority_lead(self):
        gen = SequenceGenerator()
        seq = [_obj("a", priority=2), _obj("b", priority=3)]
        label = gen.label_sequence(0, seq)
        assert "low-priority-lead" in label

    def test_label_empty(self):
        gen = SequenceGenerator()
        label = gen.label_sequence(5, [])
        assert "5" in label

    def test_properties(self):
        gen = SequenceGenerator(top_k=4, max_sequences=20)
        assert gen.top_k == 4
        assert gen.max_sequences == 20
        assert gen.evaluator is not None

    def test_top_k_clamped_min(self):
        gen = SequenceGenerator(top_k=0)
        assert gen.top_k == _MIN_TOP_K

    def test_top_k_clamped_max(self):
        gen = SequenceGenerator(top_k=100)
        assert gen.top_k == _MAX_TOP_K

    def test_max_sequences_clamped(self):
        gen = SequenceGenerator(max_sequences=1)
        assert gen.max_sequences == 5


# ── SequenceEvaluator ────────────────────────────────────────────────


class TestSequenceEvaluator:
    def test_score_basic(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        se = SequenceEvaluator(evaluator=ev)
        objs = [_obj("a", 7, value=0.8), _obj("b", 5, value=0.5)]
        result = se.score_sequence(objs, label="test")
        assert result.label == "test"
        assert result.total_score > 0
        assert result.depth == 2

    def test_score_empty_sequence(self):
        se = SequenceEvaluator()
        result = se.score_sequence([], label="empty")
        assert result.depth == 0
        assert result.total_score > 0  # effort component: 1/(1+0) = 1.0

    def test_discount_applied(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        se = SequenceEvaluator(evaluator=ev, discount=0.5)
        objs = [_obj("a", 5), _obj("b", 5)]
        result = se.score_sequence(objs, label="test")
        assert result.steps[0].discount == 1.0
        assert result.steps[1].discount == 0.5

    def test_discount_step_0_always_1(self):
        se = SequenceEvaluator(discount=0.7)
        objs = [_obj("a", 5)]
        result = se.score_sequence(objs)
        assert result.steps[0].discount == 1.0

    def test_discount_compounds(self):
        se = SequenceEvaluator(discount=0.8)
        objs = [_obj("a"), _obj("b"), _obj("c")]
        result = se.score_sequence(objs)
        assert abs(result.steps[0].discount - 1.0) < 1e-9
        assert abs(result.steps[1].discount - 0.8) < 1e-9
        assert abs(result.steps[2].discount - 0.64) < 1e-9

    def test_discounted_score_correct(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        se = SequenceEvaluator(evaluator=ev, discount=0.85)
        objs = [_obj("a", 5)]
        result = se.score_sequence(objs)
        step = result.steps[0]
        expected_discounted = step.score.total_score * 1.0
        assert abs(step.discounted_score - expected_discounted) < 1e-9

    def test_cumulative_effort(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        se = SequenceEvaluator(evaluator=ev)
        objs = [_obj("a", effort=2.0), _obj("b", effort=3.0)]
        result = se.score_sequence(objs)
        assert abs(result.cumulative_effort - 5.0) < 1e-9

    def test_higher_discount_values_future_more(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        se_high = SequenceEvaluator(evaluator=ev, discount=0.95)
        se_low = SequenceEvaluator(evaluator=ev, discount=0.5)
        objs = [_obj("a", 3, value=0.3), _obj("b", 9, value=0.9)]
        high_result = se_high.score_sequence(objs)
        low_result = se_low.score_sequence(objs)
        assert high_result.total_score > low_result.total_score

    def test_discount_clamped_min(self):
        se = SequenceEvaluator(discount=0.1)
        assert se.discount == 0.5

    def test_discount_clamped_max(self):
        se = SequenceEvaluator(discount=2.0)
        assert se.discount == 1.0

    def test_rank_basic(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        se = SequenceEvaluator(evaluator=ev)
        seq_a = se.score_sequence([_obj("a", 9, value=0.9)], label="strong")
        seq_b = se.score_sequence([_obj("b", 2, value=0.2)], label="weak")
        ranked = se.rank([seq_b, seq_a])
        assert ranked[0].label == "strong"
        assert ranked[1].label == "weak"

    def test_rank_deterministic_tiebreak(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        se = SequenceEvaluator(evaluator=ev)
        seq_a = se.score_sequence([_obj("x", 5)], label="beta")
        seq_b = se.score_sequence([_obj("x", 5)], label="alpha")
        ranked = se.rank([seq_a, seq_b])
        assert ranked[0].label == "alpha"

    def test_score_deterministic(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        se = SequenceEvaluator(evaluator=ev)
        objs = [_obj("a", 7), _obj("b", 5)]
        r1 = se.score_sequence(objs)
        r2 = se.score_sequence(objs)
        assert r1.total_score == r2.total_score

    def test_weights_property(self):
        se = SequenceEvaluator(weights=MetaPlanWeights(score_weight=0.8, effort_weight=0.2))
        w = se.weights
        assert abs(w.score_weight - 0.8) < 1e-9
        assert abs(w.effort_weight - 0.2) < 1e-9

    def test_weights_zero_total(self):
        se = SequenceEvaluator(weights=MetaPlanWeights(score_weight=0.0, effort_weight=0.0))
        objs = [_obj("a", 5)]
        result = se.score_sequence(objs)
        assert result.total_score == 0.0

    def test_custom_evaluator(self):
        ev = ObjectiveEvaluator(
            weights=ArbitrationWeights(urgency=0.0, importance=1.0, value=0.0, effort=0.0),
            reference_time="2026-04-30T12:00:00Z",
        )
        se = SequenceEvaluator(evaluator=ev)
        assert se.evaluator is ev


# ── MetaPlanner ──────────────────────────────────────────────────────


class TestMetaPlanner:
    def test_plan_basic(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        gen = SequenceGenerator(evaluator=ev)
        se = SequenceEvaluator(evaluator=ev)
        mp = MetaPlanner(generator=gen, sequence_evaluator=se)
        objs = [_obj("a", 8, value=0.9), _obj("b", 5), _obj("c", 3)]
        result = mp.plan(objs)
        assert result is not None
        assert result.next_objective is not None
        assert result.depth >= _MIN_DEPTH

    def test_plan_empty(self):
        mp = MetaPlanner()
        result = mp.plan([])
        assert result is None

    def test_plan_single(self):
        mp = MetaPlanner()
        result = mp.plan([_obj("only")])
        assert result is not None
        assert result.depth == 1
        assert result.next_objective.objective_id == "only"

    def test_plan_two_objectives(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        gen = SequenceGenerator(evaluator=ev)
        se = SequenceEvaluator(evaluator=ev)
        mp = MetaPlanner(generator=gen, sequence_evaluator=se)
        objs = [_obj("a", 8, value=0.9), _obj("b", 3, value=0.3)]
        result = mp.plan(objs, depth=2)
        assert result is not None
        assert result.depth == 2

    def test_plan_selects_best(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        gen = SequenceGenerator(evaluator=ev)
        se = SequenceEvaluator(evaluator=ev)
        mp = MetaPlanner(generator=gen, sequence_evaluator=se)
        objs = [
            _obj("strong", 9, value=0.9, effort=0.5),
            _obj("weak", 2, value=0.2, effort=5.0),
            _obj("mid", 5, value=0.5),
        ]
        result = mp.plan(objs)
        assert result is not None
        assert result.selected.total_score >= result.sequences[-1].total_score

    def test_plan_next_is_first_in_sequence(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        gen = SequenceGenerator(evaluator=ev)
        se = SequenceEvaluator(evaluator=ev)
        mp = MetaPlanner(generator=gen, sequence_evaluator=se)
        objs = [_obj("a", 8), _obj("b", 5), _obj("c", 3)]
        result = mp.plan(objs)
        assert result is not None
        assert result.next_objective.objective_id == result.selected.first_objective.objective_id

    def test_plan_deterministic(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        gen = SequenceGenerator(evaluator=ev)
        se = SequenceEvaluator(evaluator=ev)
        mp = MetaPlanner(generator=gen, sequence_evaluator=se)
        objs = [_obj("a", 8), _obj("b", 5), _obj("c", 3)]
        r1 = mp.plan(objs)
        r2 = mp.plan(objs)
        assert r1 is not None and r2 is not None
        assert r1.selected.label == r2.selected.label
        assert r1.next_objective.objective_id == r2.next_objective.objective_id

    def test_plan_reason_present(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        gen = SequenceGenerator(evaluator=ev)
        se = SequenceEvaluator(evaluator=ev)
        mp = MetaPlanner(generator=gen, sequence_evaluator=se)
        objs = [_obj("a", 8), _obj("b", 5)]
        result = mp.plan(objs, depth=2)
        assert result is not None
        assert len(result.reason) > 0

    def test_plan_explanation_present(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        gen = SequenceGenerator(evaluator=ev)
        se = SequenceEvaluator(evaluator=ev)
        mp = MetaPlanner(generator=gen, sequence_evaluator=se)
        objs = [_obj("a", 8), _obj("b", 5)]
        result = mp.plan(objs, depth=2)
        assert result is not None
        lines = result.explanation
        assert len(lines) >= 3

    def test_plan_all_scored(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        gen = SequenceGenerator(evaluator=ev)
        se = SequenceEvaluator(evaluator=ev)
        mp = MetaPlanner(generator=gen, sequence_evaluator=se)
        objs = [_obj("a", 8), _obj("b", 5), _obj("c", 3)]
        result = mp.plan(objs)
        assert result is not None
        for seq in result.sequences:
            assert seq.total_score > 0

    def test_plan_to_dict(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        gen = SequenceGenerator(evaluator=ev)
        se = SequenceEvaluator(evaluator=ev)
        mp = MetaPlanner(generator=gen, sequence_evaluator=se)
        objs = [_obj("a", 8), _obj("b", 5)]
        result = mp.plan(objs, depth=2)
        assert result is not None
        d = result.to_dict()
        assert d["sequences_evaluated"] >= 1
        assert "next_objective" in d
        assert "reason" in d

    def test_plan_bounded_sequences(self):
        gen = SequenceGenerator(top_k=3, max_sequences=10)
        mp = MetaPlanner(generator=gen)
        objs = [_obj(f"o{i}", priority=10 - i) for i in range(6)]
        result = mp.plan(objs)
        assert result is not None
        assert len(result.sequences) <= 10

    def test_properties(self):
        gen = SequenceGenerator()
        se = SequenceEvaluator()
        mp = MetaPlanner(generator=gen, sequence_evaluator=se)
        assert mp.generator is gen
        assert mp.sequence_evaluator is se

    def test_plan_respects_depth_param(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        gen = SequenceGenerator(evaluator=ev)
        se = SequenceEvaluator(evaluator=ev)
        mp = MetaPlanner(generator=gen, sequence_evaluator=se)
        objs = [_obj("a", 8), _obj("b", 5), _obj("c", 3), _obj("d", 4)]
        result = mp.plan(objs, depth=4)
        assert result is not None
        assert result.depth <= _MAX_DEPTH

    def test_plan_reason_narrow_margin(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        gen = SequenceGenerator(evaluator=ev)
        se = SequenceEvaluator(evaluator=ev)
        mp = MetaPlanner(generator=gen, sequence_evaluator=se)
        objs = [_obj("a", 5, value=0.5), _obj("b", 5, value=0.5)]
        result = mp.plan(objs, depth=2)
        assert result is not None
        # Two objectives with identical scores → narrow margin
        if len(result.sequences) > 1:
            margin = result.sequences[0].total_score - result.sequences[1].total_score
            if margin < 0.02:
                assert "narrow margin" in result.reason


# ── Advisor Integration ──────────────────────────────────────────────


class TestAdvisorIntegration:
    def _make_advisor(self, *, with_planner: bool = True):
        from umh.runtime.advisor import AdvisorRuntime

        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        gen = SequenceGenerator(evaluator=ev)
        se = SequenceEvaluator(evaluator=ev)
        planner = MetaPlanner(generator=gen, sequence_evaluator=se) if with_planner else None
        return AdvisorRuntime(meta_planner=planner)

    def test_meta_planner_property(self):
        adv = self._make_advisor()
        assert adv.meta_planner is not None

    def test_no_planner_property(self):
        adv = self._make_advisor(with_planner=False)
        assert adv.meta_planner is None

    def test_last_meta_plan_none_initially(self):
        adv = self._make_advisor()
        assert adv.last_meta_plan is None

    def test_tick_meta_plan_key(self):
        adv = self._make_advisor()
        adv.add_objective(_obj("a", 8))
        adv.add_objective(_obj("b", 5))
        result = adv.tick()
        assert "meta_plan_selected" in result

    def test_tick_runs_meta_plan(self):
        adv = self._make_advisor()
        adv.add_objective(_obj("a", 8))
        adv.add_objective(_obj("b", 5))
        result = adv.tick()
        assert result["meta_plan_selected"] is True
        assert adv.last_meta_plan is not None
        assert adv.last_meta_plan.next_objective is not None

    def test_tick_no_planner_no_plan(self):
        adv = self._make_advisor(with_planner=False)
        adv.add_objective(_obj("a", 8))
        adv.add_objective(_obj("b", 5))
        result = adv.tick()
        assert result["meta_plan_selected"] is False

    def test_tick_no_objectives_no_plan(self):
        adv = self._make_advisor()
        result = adv.tick()
        assert result["meta_plan_selected"] is False

    def test_tick_single_objective_still_plans(self):
        adv = self._make_advisor()
        adv.add_objective(_obj("only"))
        result = adv.tick()
        assert result["meta_plan_selected"] is True
        assert adv.last_meta_plan is not None
        assert adv.last_meta_plan.depth == 1

    def test_get_state_with_meta_plan(self):
        adv = self._make_advisor()
        adv.add_objective(_obj("a", 8))
        adv.add_objective(_obj("b", 5))
        adv.tick()
        state = adv.get_state()
        assert "meta_plan" in state

    def test_get_state_no_meta_plan(self):
        adv = self._make_advisor(with_planner=False)
        state = adv.get_state()
        assert "meta_plan" not in state

    def test_clear_resets_meta_plan(self):
        adv = self._make_advisor()
        adv.add_objective(_obj("a", 8))
        adv.add_objective(_obj("b", 5))
        adv.tick()
        assert adv.last_meta_plan is not None
        adv.clear()
        assert adv.last_meta_plan is None


# ── Hard Invariants 90-94 ────────────────────────────────────────────


class TestHardInvariants:
    def test_inv90_meta_planning_read_only(self):
        """INV 90: Meta-planning must not mutate execution state."""
        objs = [_obj("a", 8), _obj("b", 5), _obj("c", 3)]
        original_ids = [o.objective_id for o in objs]
        original_len = len(objs)

        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        gen = SequenceGenerator(evaluator=ev)
        se = SequenceEvaluator(evaluator=ev)
        mp = MetaPlanner(generator=gen, sequence_evaluator=se)
        mp.plan(objs)

        assert [o.objective_id for o in objs] == original_ids
        assert len(objs) == original_len

    def test_inv90_no_io_in_meta_planner(self):
        """INV 90: No file I/O, no network in meta_planner module."""
        source_path = "/opt/OS/umh/runtime/meta_planner.py"
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
            assert forbidden not in imported_names
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "open":
                    raise AssertionError("Found open() call in meta_planner.py")

    def test_inv91_only_next_objective_committed(self):
        """INV 91: MetaPlanResult exposes next_objective as the commit point."""
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        gen = SequenceGenerator(evaluator=ev)
        se = SequenceEvaluator(evaluator=ev)
        mp = MetaPlanner(generator=gen, sequence_evaluator=se)
        objs = [_obj("a", 8), _obj("b", 5), _obj("c", 3)]
        result = mp.plan(objs)
        assert result is not None
        assert result.next_objective.objective_id == result.selected.steps[0].objective.objective_id
        assert result.selected.depth >= 2

    def test_inv92_deterministic(self):
        """INV 92: Same inputs always produce same result."""
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        gen = SequenceGenerator(evaluator=ev)
        se = SequenceEvaluator(evaluator=ev)
        mp = MetaPlanner(generator=gen, sequence_evaluator=se)
        objs = [_obj("a", 8, value=0.9), _obj("b", 5, value=0.5), _obj("c", 3, value=0.3)]
        results = [mp.plan(objs) for _ in range(10)]
        labels = [r.selected.label for r in results if r is not None]
        scores = [r.selected.total_score for r in results if r is not None]
        assert len(set(labels)) == 1
        assert len(set(scores)) == 1

    def test_inv93_bounded_search(self):
        """INV 93: Sequence count never exceeds _MAX_SEQUENCES."""
        gen = SequenceGenerator(top_k=_MAX_TOP_K, max_sequences=_MAX_SEQUENCES)
        objs = [_obj(f"o{i}", priority=10 - i) for i in range(10)]
        seqs = gen.generate(objs, depth=_MAX_DEPTH)
        assert len(seqs) <= _MAX_SEQUENCES

    def test_inv93_top_k_limits_branching(self):
        """INV 93: Only top K objectives are used in generation."""
        gen = SequenceGenerator(top_k=2)
        objs = [_obj(f"o{i}", priority=10 - i) for i in range(8)]
        seqs = gen.generate(objs, depth=2)
        all_ids = set()
        for seq in seqs:
            for o in seq:
                all_ids.add(o.objective_id)
        assert len(all_ids) <= 2

    def test_inv94_no_execution_during_planning(self):
        """INV 94: No imports from umh/cells, umh/environments, umh/adapters."""
        source_path = "/opt/OS/umh/runtime/meta_planner.py"
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
                for forbidden in [
                    "umh.cells",
                    "umh.environments",
                    "umh.adapters",
                    "subprocess",
                ]:
                    assert not mod_name.startswith(forbidden), (
                        f"Forbidden import '{mod_name}' in meta_planner.py"
                    )


# ── Boundary / Export Checks ─────────────────────────────────────────


class TestBoundaryChecks:
    def test_import_from_runtime(self):
        from umh.runtime import (
            MetaPlanResult,
            MetaPlanWeights,
            MetaPlanner,
            ObjectiveSequence,
            SequenceEvaluator,
            SequenceGenerator,
            SequenceStep,
        )

        assert MetaPlanner is not None
        assert ObjectiveSequence is not None

    def test_import_direct(self):
        from umh.runtime.meta_planner import (
            MetaPlanResult,
            MetaPlanWeights,
            MetaPlanner,
            ObjectiveSequence,
            SequenceEvaluator,
            SequenceGenerator,
            SequenceStep,
        )

        assert MetaPlanner is not None

    def test_compile_meta_planner(self):
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/meta_planner.py", doraise=True)

    def test_compile_advisor(self):
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/advisor.py", doraise=True)

    def test_compile_init(self):
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/__init__.py", doraise=True)

    def test_all_exports_in_init(self):
        from umh.runtime import __all__

        expected = [
            "MetaPlanResult",
            "MetaPlanWeights",
            "MetaPlanner",
            "ObjectiveSequence",
            "SequenceEvaluator",
            "SequenceGenerator",
            "SequenceStep",
        ]
        for name in expected:
            assert name in __all__, f"{name} missing from __all__"

    def test_end_to_end_full_pipeline(self):
        """Full pipeline: objectives → meta-plan → next objective."""
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        gen = SequenceGenerator(evaluator=ev, top_k=3)
        se = SequenceEvaluator(evaluator=ev, discount=0.85)
        mp = MetaPlanner(generator=gen, sequence_evaluator=se)

        objs = [
            _obj("ship-v2", 9, value=0.9, effort=2.0),
            _obj("fix-auth", 10, value=0.7, effort=0.5),
            _obj("refactor", 3, value=0.3, effort=4.0),
        ]
        result = mp.plan(objs)
        assert result is not None
        assert result.next_objective.objective_id in {"ship-v2", "fix-auth", "refactor"}
        d = result.to_dict()
        assert d["sequences_evaluated"] >= 1

    def test_end_to_end_advisor(self):
        """Full pipeline through advisor: add objectives → tick → check state."""
        from umh.runtime.advisor import AdvisorRuntime

        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        gen = SequenceGenerator(evaluator=ev)
        se = SequenceEvaluator(evaluator=ev)
        mp = MetaPlanner(generator=gen, sequence_evaluator=se)
        adv = AdvisorRuntime(meta_planner=mp)
        adv.add_objective(_obj("primary", 9, value=0.9))
        adv.add_objective(_obj("secondary", 4, value=0.4))
        adv.add_objective(_obj("tertiary", 6, value=0.6))
        result = adv.tick()
        assert result["meta_plan_selected"] is True
        assert adv.last_meta_plan is not None
        state = adv.get_state()
        assert "meta_plan" in state
        assert state["meta_plan"]["sequences_evaluated"] >= 1
