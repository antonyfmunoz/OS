"""Phase 32 — Dependency-Aware Meta Planning + Sequence Learning v1.

Tests for ObjectiveDependency, DependencyGraph, ContextSignature,
SequenceRecord, SequenceMemory, extended SequenceGenerator,
extended SequenceEvaluator, extended MetaPlanner, advisor integration,
hard invariants 95-100, and boundary/export checks.

Target: 90-130 tests. Zero tolerance for regressions.
"""

from __future__ import annotations

import ast
import sys

import pytest

sys.path.insert(0, "/opt/OS")

from umh.runtime.arbitration import (
    Objective,
    ObjectiveEvaluator,
)
from umh.runtime.dependency import (
    DependencyGraph,
    DependencyType,
    ObjectiveDependency,
)
from umh.runtime.meta_planner import (
    MetaPlanner,
    MetaPlanWeights,
    SequenceEvaluator,
    SequenceGenerator,
)
from umh.runtime.sequence_memory import (
    ContextSignature,
    SequenceMemory,
    SequenceRecord,
    make_sequence_record,
    _MIN_ADJUSTMENT,
    _MAX_ADJUSTMENT,
    _MIN_RECORDS_FOR_ADJUSTMENT,
)


def _obj(oid: str, priority: int = 5, value: float = 0.5, effort: float = 1.0) -> Objective:
    return Objective(
        objective_id=oid,
        description=f"goal {oid}",
        priority=priority,
        expected_value=value,
        effort_estimate=effort,
    )


# ── ObjectiveDependency ─────────────────────────────────────────────


class TestObjectiveDependency:
    def test_create(self):
        dep = ObjectiveDependency(parent_id="a", child_id="b", strength=0.8)
        assert dep.parent_id == "a"
        assert dep.child_id == "b"
        assert dep.strength == 0.8
        assert dep.dep_type == DependencyType.ENABLES

    def test_create_with_type(self):
        dep = ObjectiveDependency(
            parent_id="a", child_id="b", strength=0.5, dep_type=DependencyType.BLOCKS
        )
        assert dep.dep_type == DependencyType.BLOCKS

    def test_frozen(self):
        dep = ObjectiveDependency(parent_id="a", child_id="b", strength=0.8)
        with pytest.raises(AttributeError):
            dep.strength = 0.5  # type: ignore[misc]

    def test_strength_clamped_high(self):
        dep = ObjectiveDependency(parent_id="a", child_id="b", strength=2.0)
        assert dep.strength == 1.0

    def test_strength_clamped_low(self):
        dep = ObjectiveDependency(parent_id="a", child_id="b", strength=-1.0)
        assert dep.strength == 0.0

    def test_to_dict(self):
        dep = ObjectiveDependency(
            parent_id="a", child_id="b", strength=0.75, dep_type=DependencyType.BOOSTS
        )
        d = dep.to_dict()
        assert d["parent_id"] == "a"
        assert d["child_id"] == "b"
        assert d["strength"] == 0.75
        assert d["dep_type"] == "boosts"

    def test_dependency_types(self):
        assert DependencyType.ENABLES.value == "enables"
        assert DependencyType.BOOSTS.value == "boosts"
        assert DependencyType.BLOCKS.value == "blocks"


# ── DependencyGraph ──────────────────────────────────────────────────


class TestDependencyGraph:
    def test_empty_graph(self):
        g = DependencyGraph()
        assert g.edge_count == 0
        assert g.get_children("a") == []
        assert g.get_parents("a") == []

    def test_add_dependency(self):
        g = DependencyGraph()
        dep = ObjectiveDependency(parent_id="a", child_id="b", strength=0.8)
        g.add_dependency(dep)
        assert g.edge_count == 1

    def test_add_idempotent(self):
        g = DependencyGraph()
        dep = ObjectiveDependency(parent_id="a", child_id="b", strength=0.8)
        g.add_dependency(dep)
        g.add_dependency(dep)
        assert g.edge_count == 1

    def test_get_children(self):
        g = DependencyGraph()
        g.add_dependency(ObjectiveDependency("a", "b", 0.8))
        g.add_dependency(ObjectiveDependency("a", "c", 0.5))
        children = g.get_children("a")
        assert len(children) == 2
        assert {c.child_id for c in children} == {"b", "c"}

    def test_get_parents(self):
        g = DependencyGraph()
        g.add_dependency(ObjectiveDependency("a", "c", 0.8))
        g.add_dependency(ObjectiveDependency("b", "c", 0.5))
        parents = g.get_parents("c")
        assert len(parents) == 2
        assert {p.parent_id for p in parents} == {"a", "b"}

    def test_has_dependency(self):
        g = DependencyGraph()
        g.add_dependency(ObjectiveDependency("a", "b", 0.8))
        assert g.has_dependency("a", "b") is True
        assert g.has_dependency("b", "a") is False
        assert g.has_dependency("a", "c") is False

    def test_get_dependency(self):
        g = DependencyGraph()
        g.add_dependency(ObjectiveDependency("a", "b", 0.8))
        dep = g.get_dependency("a", "b")
        assert dep is not None
        assert dep.strength == 0.8

    def test_get_dependency_missing(self):
        g = DependencyGraph()
        assert g.get_dependency("a", "b") is None

    def test_dependency_score_enables(self):
        g = DependencyGraph()
        g.add_dependency(ObjectiveDependency("a", "b", 0.8, DependencyType.ENABLES))
        assert g.dependency_score("a", "b") == 0.8

    def test_dependency_score_boosts(self):
        g = DependencyGraph()
        g.add_dependency(ObjectiveDependency("a", "b", 0.6, DependencyType.BOOSTS))
        assert g.dependency_score("a", "b") == 0.6

    def test_dependency_score_blocks(self):
        g = DependencyGraph()
        g.add_dependency(ObjectiveDependency("a", "b", 0.7, DependencyType.BLOCKS))
        assert g.dependency_score("a", "b") == -0.7

    def test_dependency_score_none(self):
        g = DependencyGraph()
        assert g.dependency_score("a", "b") == 0.0

    def test_sequence_dependency_score(self):
        g = DependencyGraph()
        g.add_dependency(ObjectiveDependency("a", "b", 0.8))
        g.add_dependency(ObjectiveDependency("b", "c", 0.6))
        score = g.sequence_dependency_score(["a", "b", "c"])
        assert abs(score - 1.4) < 1e-9

    def test_sequence_dependency_score_single(self):
        g = DependencyGraph()
        assert g.sequence_dependency_score(["a"]) == 0.0

    def test_sequence_dependency_score_empty(self):
        g = DependencyGraph()
        assert g.sequence_dependency_score([]) == 0.0

    def test_sequence_with_block(self):
        g = DependencyGraph()
        g.add_dependency(ObjectiveDependency("a", "b", 0.8, DependencyType.ENABLES))
        g.add_dependency(ObjectiveDependency("b", "c", 0.5, DependencyType.BLOCKS))
        score = g.sequence_dependency_score(["a", "b", "c"])
        assert abs(score - 0.3) < 1e-9

    def test_all_edges(self):
        g = DependencyGraph()
        g.add_dependency(ObjectiveDependency("a", "b", 0.8))
        g.add_dependency(ObjectiveDependency("b", "c", 0.6))
        edges = g.all_edges()
        assert len(edges) == 2

    def test_all_edges_returns_copy(self):
        g = DependencyGraph()
        g.add_dependency(ObjectiveDependency("a", "b", 0.8))
        edges = g.all_edges()
        edges.clear()
        assert g.edge_count == 1

    def test_clear(self):
        g = DependencyGraph()
        g.add_dependency(ObjectiveDependency("a", "b", 0.8))
        g.clear()
        assert g.edge_count == 0
        assert g.get_children("a") == []

    def test_to_dict(self):
        g = DependencyGraph()
        g.add_dependency(ObjectiveDependency("a", "b", 0.8))
        d = g.to_dict()
        assert d["edge_count"] == 1
        assert len(d["edges"]) == 1

    def test_get_children_returns_copy(self):
        g = DependencyGraph()
        g.add_dependency(ObjectiveDependency("a", "b", 0.8))
        children = g.get_children("a")
        children.clear()
        assert len(g.get_children("a")) == 1


# ── ContextSignature ─────────────────────────────────────────────────


class TestContextSignature:
    def test_create(self):
        cs = ContextSignature(features=("signal-a", "state-b"))
        assert len(cs.hash_value) == 16
        assert cs.features == ("signal-a", "state-b")

    def test_frozen(self):
        cs = ContextSignature(features=("a",))
        with pytest.raises(AttributeError):
            cs.hash_value = "x"  # type: ignore[misc]

    def test_deterministic_hash(self):
        cs1 = ContextSignature(features=("a", "b"))
        cs2 = ContextSignature(features=("a", "b"))
        assert cs1.hash_value == cs2.hash_value

    def test_order_independent(self):
        cs1 = ContextSignature(features=("b", "a"))
        cs2 = ContextSignature(features=("a", "b"))
        assert cs1.hash_value == cs2.hash_value

    def test_different_features_different_hash(self):
        cs1 = ContextSignature(features=("a",))
        cs2 = ContextSignature(features=("b",))
        assert cs1.hash_value != cs2.hash_value

    def test_to_dict(self):
        cs = ContextSignature(features=("a", "b"))
        d = cs.to_dict()
        assert d["features"] == ["a", "b"]
        assert len(d["hash_value"]) == 16

    def test_explicit_hash(self):
        cs = ContextSignature(features=("a",), hash_value="custom_hash_1234")
        assert cs.hash_value == "custom_hash_1234"


# ── SequenceRecord ───────────────────────────────────────────────────


class TestSequenceRecord:
    def test_create(self):
        r = SequenceRecord(
            record_id="r1",
            objective_ids=("a", "b"),
            predicted_score=0.7,
            actual_score=0.8,
            delta=0.1,
            timestamp="2026-04-30T12:00:00Z",
        )
        assert r.record_id == "r1"
        assert r.delta == 0.1
        assert r.context_signature is None

    def test_frozen(self):
        r = SequenceRecord(
            record_id="r1",
            objective_ids=("a",),
            predicted_score=0.5,
            actual_score=0.5,
            delta=0.0,
            timestamp="2026-04-30T12:00:00Z",
        )
        with pytest.raises(AttributeError):
            r.delta = 0.5  # type: ignore[misc]

    def test_to_dict(self):
        r = SequenceRecord(
            record_id="r1",
            objective_ids=("a", "b"),
            predicted_score=0.7,
            actual_score=0.8,
            delta=0.1,
            timestamp="2026-04-30T12:00:00Z",
        )
        d = r.to_dict()
        assert d["record_id"] == "r1"
        assert d["objective_ids"] == ["a", "b"]
        assert d["delta"] == 0.1

    def test_to_dict_rounds(self):
        r = SequenceRecord(
            record_id="r1",
            objective_ids=("a",),
            predicted_score=0.123456789,
            actual_score=0.987654321,
            delta=0.864197532,
            timestamp="2026-04-30T12:00:00Z",
        )
        d = r.to_dict()
        assert d["predicted_score"] == round(0.123456789, 4)
        assert d["actual_score"] == round(0.987654321, 4)
        assert d["delta"] == round(0.864197532, 4)

    def test_with_context(self):
        cs = ContextSignature(features=("signal-a",))
        r = SequenceRecord(
            record_id="r1",
            objective_ids=("a",),
            predicted_score=0.5,
            actual_score=0.5,
            delta=0.0,
            timestamp="2026-04-30T12:00:00Z",
            context_signature=cs,
        )
        d = r.to_dict()
        assert d["context_signature"] is not None
        assert d["context_signature"]["features"] == ["signal-a"]


class TestMakeSequenceRecord:
    def test_basic(self):
        r = make_sequence_record("r1", ["a", "b"], 0.7, 0.8)
        assert r.record_id == "r1"
        assert r.objective_ids == ("a", "b")
        assert r.predicted_score == 0.7
        assert r.actual_score == 0.8
        assert abs(r.delta - 0.1) < 1e-9
        assert len(r.timestamp) > 0

    def test_delta_computed(self):
        r = make_sequence_record("r1", ["a"], 0.9, 0.6)
        assert abs(r.delta - (-0.3)) < 1e-9

    def test_with_context(self):
        cs = ContextSignature(features=("x",))
        r = make_sequence_record("r1", ["a"], 0.5, 0.5, context_signature=cs)
        assert r.context_signature is not None

    def test_with_timestamp(self):
        r = make_sequence_record("r1", ["a"], 0.5, 0.5, timestamp="2026-04-30")
        assert r.timestamp == "2026-04-30"


# ── SequenceMemory ───────────────────────────────────────────────────


class TestSequenceMemory:
    def _mem_with_records(self) -> SequenceMemory:
        mem = SequenceMemory()
        mem.append(make_sequence_record("r1", ["a", "b"], 0.7, 0.8, timestamp="2026-04-01"))
        mem.append(make_sequence_record("r2", ["a", "b"], 0.6, 0.7, timestamp="2026-04-02"))
        mem.append(make_sequence_record("r3", ["a", "b"], 0.5, 0.4, timestamp="2026-04-03"))
        mem.append(make_sequence_record("r4", ["b", "a"], 0.6, 0.5, timestamp="2026-04-04"))
        return mem

    def test_empty(self):
        mem = SequenceMemory()
        assert mem.count == 0

    def test_append(self):
        mem = SequenceMemory()
        mem.append(make_sequence_record("r1", ["a", "b"], 0.7, 0.8))
        assert mem.count == 1

    def test_query_exact(self):
        mem = self._mem_with_records()
        results = mem.query_exact(["a", "b"])
        assert len(results) == 3

    def test_query_exact_miss(self):
        mem = self._mem_with_records()
        results = mem.query_exact(["c", "d"])
        assert len(results) == 0

    def test_query_prefix(self):
        mem = self._mem_with_records()
        results = mem.query_prefix(["a"])
        assert len(results) == 3

    def test_query_prefix_full(self):
        mem = self._mem_with_records()
        results = mem.query_prefix(["a", "b"])
        assert len(results) == 3

    def test_query_contains(self):
        mem = self._mem_with_records()
        results = mem.query_contains("a")
        assert len(results) == 4

    def test_query_contains_miss(self):
        mem = self._mem_with_records()
        results = mem.query_contains("z")
        assert len(results) == 0

    def test_success_rate(self):
        mem = self._mem_with_records()
        rate = mem.get_success_rate(["a", "b"])
        assert rate is not None
        assert abs(rate - 2.0 / 3.0) < 1e-9

    def test_success_rate_none(self):
        mem = SequenceMemory()
        assert mem.get_success_rate(["a"]) is None

    def test_avg_delta(self):
        mem = self._mem_with_records()
        avg = mem.get_avg_delta(["a", "b"])
        assert avg is not None
        expected = (0.1 + 0.1 + (-0.1)) / 3
        assert abs(avg - expected) < 1e-9

    def test_avg_delta_none(self):
        mem = SequenceMemory()
        assert mem.get_avg_delta(["a"]) is None

    def test_recency_weighted_delta(self):
        mem = self._mem_with_records()
        delta = mem.get_recency_weighted_delta(["a", "b"])
        assert delta is not None

    def test_recency_weighted_delta_none(self):
        mem = SequenceMemory()
        assert mem.get_recency_weighted_delta(["a"]) is None

    def test_adjustment_factor_insufficient_data(self):
        mem = SequenceMemory()
        mem.append(make_sequence_record("r1", ["a"], 0.7, 0.8))
        assert mem.compute_adjustment_factor(["a"]) == 1.0

    def test_adjustment_factor_with_data(self):
        mem = self._mem_with_records()
        factor = mem.compute_adjustment_factor(["a", "b"])
        assert _MIN_ADJUSTMENT <= factor <= _MAX_ADJUSTMENT

    def test_adjustment_factor_all_success(self):
        mem = SequenceMemory()
        for i in range(5):
            mem.append(make_sequence_record(f"r{i}", ["x", "y"], 0.5, 0.7))
        factor = mem.compute_adjustment_factor(["x", "y"])
        assert factor > 1.0

    def test_adjustment_factor_all_failure(self):
        mem = SequenceMemory()
        for i in range(5):
            mem.append(make_sequence_record(f"r{i}", ["x", "y"], 0.7, 0.3))
        factor = mem.compute_adjustment_factor(["x", "y"])
        assert factor < 1.0

    def test_adjustment_factor_clamped_min(self):
        mem = SequenceMemory()
        for i in range(5):
            mem.append(make_sequence_record(f"r{i}", ["x"], 1.0, 0.0))
        factor = mem.compute_adjustment_factor(["x"])
        assert factor >= _MIN_ADJUSTMENT

    def test_adjustment_factor_clamped_max(self):
        mem = SequenceMemory()
        for i in range(5):
            mem.append(make_sequence_record(f"r{i}", ["x"], 0.0, 1.0))
        factor = mem.compute_adjustment_factor(["x"])
        assert factor <= _MAX_ADJUSTMENT

    def test_list_all(self):
        mem = self._mem_with_records()
        all_records = mem.list_all()
        assert len(all_records) == 4

    def test_list_all_returns_copy(self):
        mem = self._mem_with_records()
        all_records = mem.list_all()
        all_records.clear()
        assert mem.count == 4

    def test_clear(self):
        mem = self._mem_with_records()
        mem.clear()
        assert mem.count == 0

    def test_to_dict(self):
        mem = self._mem_with_records()
        d = mem.to_dict()
        assert d["count"] == 4
        assert len(d["records"]) == 4

    def test_recency_decay_property(self):
        mem = SequenceMemory(recency_decay=0.8)
        assert mem.recency_decay == 0.8

    def test_recency_decay_clamped(self):
        mem = SequenceMemory(recency_decay=0.1)
        assert mem.recency_decay == 0.5


# ── Dependency-Aware SequenceGenerator ───────────────────────────────


class TestDependencyAwareGenerator:
    def test_dependency_graph_property(self):
        g = DependencyGraph()
        gen = SequenceGenerator(dependency_graph=g)
        assert gen.dependency_graph is g

    def test_no_graph_still_works(self):
        gen = SequenceGenerator()
        objs = [_obj("a", 7), _obj("b", 5)]
        seqs = gen.generate(objs, depth=2)
        assert len(seqs) > 0

    def test_dependency_sorting(self):
        g = DependencyGraph()
        g.add_dependency(ObjectiveDependency("a", "b", 0.9, DependencyType.ENABLES))
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        gen = SequenceGenerator(evaluator=ev, dependency_graph=g)
        objs = [_obj("a", 5), _obj("b", 5)]
        seqs = gen.generate(objs, depth=2)
        assert len(seqs) == 2
        first_ids = [o.objective_id for o in seqs[0]]
        assert first_ids == ["a", "b"]

    def test_block_dependency_penalized(self):
        g = DependencyGraph()
        g.add_dependency(ObjectiveDependency("a", "b", 0.9, DependencyType.BLOCKS))
        g.add_dependency(ObjectiveDependency("b", "a", 0.5, DependencyType.ENABLES))
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        gen = SequenceGenerator(evaluator=ev, dependency_graph=g)
        objs = [_obj("a", 5), _obj("b", 5)]
        seqs = gen.generate(objs, depth=2)
        first_ids = [o.objective_id for o in seqs[0]]
        assert first_ids == ["b", "a"]

    def test_empty_graph_no_change(self):
        g = DependencyGraph()
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        gen_with = SequenceGenerator(evaluator=ev, dependency_graph=g)
        gen_without = SequenceGenerator(evaluator=ev)
        objs = [_obj("a", 7), _obj("b", 5)]
        seqs_with = gen_with.generate(objs, depth=2)
        seqs_without = gen_without.generate(objs, depth=2)
        ids_with = [[o.objective_id for o in s] for s in seqs_with]
        ids_without = [[o.objective_id for o in s] for s in seqs_without]
        assert ids_with == ids_without

    def test_three_way_dependency_chain(self):
        g = DependencyGraph()
        g.add_dependency(ObjectiveDependency("a", "b", 0.8))
        g.add_dependency(ObjectiveDependency("b", "c", 0.7))
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        gen = SequenceGenerator(evaluator=ev, dependency_graph=g, top_k=3)
        objs = [_obj("a", 5), _obj("b", 5), _obj("c", 5)]
        seqs = gen.generate(objs, depth=3)
        first_ids = [o.objective_id for o in seqs[0]]
        assert first_ids == ["a", "b", "c"]


# ── Memory-Informed SequenceEvaluator ────────────────────────────────


class TestMemoryInformedEvaluator:
    def test_no_memory_no_change(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        se = SequenceEvaluator(evaluator=ev)
        objs = [_obj("a", 7), _obj("b", 5)]
        result = se.score_sequence(objs)
        assert result.total_score > 0

    def test_learning_disabled_no_change(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        mem = SequenceMemory()
        for i in range(5):
            mem.append(make_sequence_record(f"r{i}", ["a", "b"], 0.5, 0.9))
        se_no_learn = SequenceEvaluator(evaluator=ev, sequence_memory=mem, enable_learning=False)
        se_learn = SequenceEvaluator(evaluator=ev, sequence_memory=mem, enable_learning=True)
        objs = [_obj("a", 7), _obj("b", 5)]
        score_no = se_no_learn.score_sequence(objs)
        score_yes = se_learn.score_sequence(objs)
        assert score_no.total_score != score_yes.total_score

    def test_learning_boosts_successful(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        mem = SequenceMemory()
        for i in range(5):
            mem.append(make_sequence_record(f"r{i}", ["a", "b"], 0.5, 0.8))
        se_base = SequenceEvaluator(evaluator=ev)
        se_learn = SequenceEvaluator(evaluator=ev, sequence_memory=mem, enable_learning=True)
        objs = [_obj("a", 7), _obj("b", 5)]
        base_score = se_base.score_sequence(objs).total_score
        learn_score = se_learn.score_sequence(objs).total_score
        assert learn_score > base_score

    def test_learning_penalizes_failed(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        mem = SequenceMemory()
        for i in range(5):
            mem.append(make_sequence_record(f"r{i}", ["a", "b"], 0.8, 0.3))
        se_base = SequenceEvaluator(evaluator=ev)
        se_learn = SequenceEvaluator(evaluator=ev, sequence_memory=mem, enable_learning=True)
        objs = [_obj("a", 7), _obj("b", 5)]
        base_score = se_base.score_sequence(objs).total_score
        learn_score = se_learn.score_sequence(objs).total_score
        assert learn_score < base_score

    def test_dependency_bonus_applied(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        g = DependencyGraph()
        g.add_dependency(ObjectiveDependency("a", "b", 0.9))
        se_dep = SequenceEvaluator(evaluator=ev, dependency_graph=g)
        se_base = SequenceEvaluator(evaluator=ev)
        objs = [_obj("a", 7), _obj("b", 5)]
        dep_score = se_dep.score_sequence(objs).total_score
        base_score = se_base.score_sequence(objs).total_score
        assert dep_score > base_score

    def test_block_dependency_penalizes(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        g = DependencyGraph()
        g.add_dependency(ObjectiveDependency("a", "b", 0.9, DependencyType.BLOCKS))
        se_dep = SequenceEvaluator(evaluator=ev, dependency_graph=g)
        se_base = SequenceEvaluator(evaluator=ev)
        objs = [_obj("a", 7), _obj("b", 5)]
        dep_score = se_dep.score_sequence(objs).total_score
        base_score = se_base.score_sequence(objs).total_score
        assert dep_score < base_score

    def test_single_item_no_dep_bonus(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        g = DependencyGraph()
        g.add_dependency(ObjectiveDependency("a", "b", 0.9))
        se_dep = SequenceEvaluator(evaluator=ev, dependency_graph=g)
        se_base = SequenceEvaluator(evaluator=ev)
        objs = [_obj("a", 7)]
        dep_score = se_dep.score_sequence(objs).total_score
        base_score = se_base.score_sequence(objs).total_score
        assert dep_score == base_score

    def test_properties(self):
        g = DependencyGraph()
        mem = SequenceMemory()
        se = SequenceEvaluator(dependency_graph=g, sequence_memory=mem, enable_learning=True)
        assert se.dependency_graph is g
        assert se.sequence_memory is mem
        assert se.learning_enabled is True

    def test_learning_disabled_by_default(self):
        se = SequenceEvaluator()
        assert se.learning_enabled is False


# ── Extended MetaPlanner ─────────────────────────────────────────────


class TestExtendedMetaPlanner:
    def test_plan_with_dependencies(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        g = DependencyGraph()
        g.add_dependency(ObjectiveDependency("a", "b", 0.9))
        gen = SequenceGenerator(evaluator=ev, dependency_graph=g)
        se = SequenceEvaluator(evaluator=ev, dependency_graph=g)
        mp = MetaPlanner(generator=gen, sequence_evaluator=se, dependency_graph=g)
        objs = [_obj("a", 5), _obj("b", 5)]
        result = mp.plan(objs, depth=2)
        assert result is not None
        first_ids = [s.objective.objective_id for s in result.selected.steps]
        assert first_ids == ["a", "b"]

    def test_plan_with_memory(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        mem = SequenceMemory()
        for i in range(5):
            mem.append(make_sequence_record(f"r{i}", ["a", "b"], 0.5, 0.8))
        se = SequenceEvaluator(evaluator=ev, sequence_memory=mem, enable_learning=True)
        mp = MetaPlanner(sequence_evaluator=se, sequence_memory=mem)
        objs = [_obj("a", 5), _obj("b", 5)]
        result = mp.plan(objs, depth=2)
        assert result is not None

    def test_reason_includes_dependency(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        g = DependencyGraph()
        g.add_dependency(ObjectiveDependency("a", "b", 0.9))
        gen = SequenceGenerator(evaluator=ev, dependency_graph=g)
        se = SequenceEvaluator(evaluator=ev, dependency_graph=g)
        mp = MetaPlanner(generator=gen, sequence_evaluator=se, dependency_graph=g)
        objs = [_obj("a", 5), _obj("b", 5)]
        result = mp.plan(objs, depth=2)
        assert result is not None
        assert "dependency" in result.reason.lower()

    def test_reason_includes_history(self):
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        mem = SequenceMemory()
        for i in range(5):
            mem.append(make_sequence_record(f"r{i}", ["a", "b"], 0.5, 0.8))
        gen = SequenceGenerator(evaluator=ev)
        se = SequenceEvaluator(evaluator=ev, sequence_memory=mem, enable_learning=True)
        mp = MetaPlanner(generator=gen, sequence_evaluator=se, sequence_memory=mem)
        objs = [_obj("a", 5), _obj("b", 5)]
        result = mp.plan(objs, depth=2)
        assert result is not None
        assert "success rate" in result.reason.lower()

    def test_properties(self):
        g = DependencyGraph()
        mem = SequenceMemory()
        mp = MetaPlanner(dependency_graph=g, sequence_memory=mem)
        assert mp.dependency_graph is g
        assert mp.sequence_memory is mem


# ── Advisor Integration ──────────────────────────────────────────────


class TestAdvisorIntegration:
    def _make_advisor(self, *, with_graph: bool = True, with_memory: bool = True):
        from umh.runtime.advisor import AdvisorRuntime

        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        g = DependencyGraph() if with_graph else None
        mem = SequenceMemory() if with_memory else None
        gen = SequenceGenerator(evaluator=ev, dependency_graph=g)
        se = SequenceEvaluator(evaluator=ev, dependency_graph=g, sequence_memory=mem)
        mp = MetaPlanner(
            generator=gen, sequence_evaluator=se, dependency_graph=g, sequence_memory=mem
        )
        return AdvisorRuntime(
            meta_planner=mp,
            dependency_graph=g,
            sequence_memory=mem,
        )

    def test_dependency_graph_property(self):
        adv = self._make_advisor()
        assert adv.dependency_graph is not None

    def test_sequence_memory_property(self):
        adv = self._make_advisor()
        assert adv.sequence_memory is not None

    def test_no_graph_property(self):
        adv = self._make_advisor(with_graph=False)
        assert adv.dependency_graph is None

    def test_no_memory_property(self):
        adv = self._make_advisor(with_memory=False)
        assert adv.sequence_memory is None

    def test_get_state_with_graph(self):
        adv = self._make_advisor()
        adv.dependency_graph.add_dependency(ObjectiveDependency("a", "b", 0.8))
        state = adv.get_state()
        assert "dependency_edges" in state
        assert state["dependency_edges"] == 1

    def test_get_state_with_memory(self):
        adv = self._make_advisor()
        adv.sequence_memory.append(make_sequence_record("r1", ["a", "b"], 0.5, 0.7))
        state = adv.get_state()
        assert "sequence_memory_count" in state
        assert state["sequence_memory_count"] == 1

    def test_clear_resets_graph_and_memory(self):
        adv = self._make_advisor()
        adv.dependency_graph.add_dependency(ObjectiveDependency("a", "b", 0.8))
        adv.sequence_memory.append(make_sequence_record("r1", ["a", "b"], 0.5, 0.7))
        adv.clear()
        assert adv.dependency_graph.edge_count == 0
        assert adv.sequence_memory.count == 0

    def test_tick_with_dependencies(self):
        adv = self._make_advisor()
        adv.dependency_graph.add_dependency(ObjectiveDependency("a", "b", 0.9))
        adv.add_objective(_obj("a", 7))
        adv.add_objective(_obj("b", 5))
        result = adv.tick()
        assert result["meta_plan_selected"] is True


# ── Hard Invariants 95-100 ───────────────────────────────────────────


class TestHardInvariants:
    def test_inv95_sequence_memory_append_only(self):
        """INV 95: SequenceMemory is append-only — records are never modified."""
        mem = SequenceMemory()
        r = make_sequence_record("r1", ["a", "b"], 0.7, 0.8)
        mem.append(r)
        records = mem.list_all()
        assert records[0].delta == r.delta
        with pytest.raises(AttributeError):
            records[0].delta = 999  # type: ignore[misc]

    def test_inv96_no_mutation_of_records(self):
        """INV 96: SequenceRecord is frozen — cannot be mutated."""
        r = make_sequence_record("r1", ["a", "b"], 0.7, 0.8)
        with pytest.raises(AttributeError):
            r.actual_score = 0.0  # type: ignore[misc]

    def test_inv97_learning_disabled_deterministic(self):
        """INV 97: Without learning enabled, scoring is deterministic."""
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        mem = SequenceMemory()
        for i in range(5):
            mem.append(make_sequence_record(f"r{i}", ["a", "b"], 0.5, 0.9))
        se = SequenceEvaluator(evaluator=ev, sequence_memory=mem, enable_learning=False)
        objs = [_obj("a", 7), _obj("b", 5)]
        s1 = se.score_sequence(objs)
        s2 = se.score_sequence(objs)
        assert s1.total_score == s2.total_score

        se_no_mem = SequenceEvaluator(evaluator=ev)
        s3 = se_no_mem.score_sequence(objs)
        assert s1.total_score == s3.total_score

    def test_inv98_dependency_graph_read_only_during_planning(self):
        """INV 98: Planning does not modify the dependency graph."""
        g = DependencyGraph()
        g.add_dependency(ObjectiveDependency("a", "b", 0.8))
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        gen = SequenceGenerator(evaluator=ev, dependency_graph=g)
        se = SequenceEvaluator(evaluator=ev, dependency_graph=g)
        mp = MetaPlanner(generator=gen, sequence_evaluator=se, dependency_graph=g)

        edges_before = g.edge_count
        mp.plan([_obj("a", 7), _obj("b", 5)])
        assert g.edge_count == edges_before

    def test_inv99_no_execution_state_mutation(self):
        """INV 99: Meta-planning does not mutate input objectives."""
        objs = [_obj("a", 8), _obj("b", 5), _obj("c", 3)]
        original_ids = [o.objective_id for o in objs]
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        gen = SequenceGenerator(evaluator=ev)
        se = SequenceEvaluator(evaluator=ev)
        mp = MetaPlanner(generator=gen, sequence_evaluator=se)
        mp.plan(objs)
        assert [o.objective_id for o in objs] == original_ids

    def test_inv100_meta_planning_side_effect_free(self):
        """INV 100: No I/O, no network, no subprocess in meta_planner."""
        for path, mod_name in [
            ("/opt/OS/umh/runtime/meta_planner.py", "meta_planner"),
            ("/opt/OS/umh/runtime/dependency.py", "dependency"),
            ("/opt/OS/umh/runtime/sequence_memory.py", "sequence_memory"),
        ]:
            with open(path) as f:
                source = f.read()
            tree = ast.parse(source)
            imported: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imported.add(alias.name)
            for forbidden in ["subprocess", "socket", "urllib", "requests", "http"]:
                assert forbidden not in imported, f"Forbidden import '{forbidden}' in {mod_name}.py"

    def test_inv100_no_forbidden_module_imports(self):
        """INV 100: No imports from umh/cells, umh/environments, umh/adapters."""
        for path in [
            "/opt/OS/umh/runtime/meta_planner.py",
            "/opt/OS/umh/runtime/dependency.py",
            "/opt/OS/umh/runtime/sequence_memory.py",
        ]:
            with open(path) as f:
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
                    for forbidden in ["umh.cells", "umh.environments", "umh.adapters"]:
                        assert not mod_name.startswith(forbidden)


# ── Boundary / Export Checks ─────────────────────────────────────────


class TestBoundaryChecks:
    def test_import_from_runtime(self):
        from umh.runtime import (
            ContextSignature,
            DependencyGraph,
            DependencyType,
            ObjectiveDependency,
            SequenceMemory,
            SequenceRecord,
            make_sequence_record,
        )

        assert DependencyGraph is not None
        assert SequenceMemory is not None

    def test_import_direct_dependency(self):
        from umh.runtime.dependency import (
            DependencyGraph,
            DependencyType,
            ObjectiveDependency,
        )

        assert DependencyGraph is not None

    def test_import_direct_memory(self):
        from umh.runtime.sequence_memory import (
            ContextSignature,
            SequenceMemory,
            SequenceRecord,
            make_sequence_record,
        )

        assert SequenceMemory is not None

    def test_compile_dependency(self):
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/dependency.py", doraise=True)

    def test_compile_sequence_memory(self):
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/sequence_memory.py", doraise=True)

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
            "ContextSignature",
            "DependencyGraph",
            "DependencyType",
            "ObjectiveDependency",
            "SequenceMemory",
            "SequenceRecord",
            "make_sequence_record",
        ]
        for name in expected:
            assert name in __all__, f"{name} missing from __all__"

    def test_end_to_end_full_pipeline(self):
        """Full pipeline with dependencies + memory."""
        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        g = DependencyGraph()
        g.add_dependency(ObjectiveDependency("deploy", "monitor", 0.9))
        g.add_dependency(ObjectiveDependency("monitor", "iterate", 0.7))

        mem = SequenceMemory()
        for i in range(5):
            mem.append(make_sequence_record(f"r{i}", ["deploy", "monitor", "iterate"], 0.5, 0.7))

        gen = SequenceGenerator(evaluator=ev, dependency_graph=g, top_k=3)
        se = SequenceEvaluator(
            evaluator=ev,
            dependency_graph=g,
            sequence_memory=mem,
            enable_learning=True,
        )
        mp = MetaPlanner(
            generator=gen,
            sequence_evaluator=se,
            dependency_graph=g,
            sequence_memory=mem,
        )

        objs = [
            _obj("deploy", 8, value=0.8, effort=1.0),
            _obj("monitor", 6, value=0.6, effort=0.5),
            _obj("iterate", 4, value=0.4, effort=2.0),
        ]
        result = mp.plan(objs, depth=3)
        assert result is not None
        first_ids = [s.objective.objective_id for s in result.selected.steps]
        assert first_ids[0] == "deploy"
        assert result.next_objective.objective_id == "deploy"
        d = result.to_dict()
        assert d["sequences_evaluated"] >= 1

    def test_end_to_end_advisor(self):
        """Full pipeline through advisor."""
        from umh.runtime.advisor import AdvisorRuntime

        ev = ObjectiveEvaluator(reference_time="2026-04-30T12:00:00Z")
        g = DependencyGraph()
        g.add_dependency(ObjectiveDependency("a", "b", 0.9))
        mem = SequenceMemory()
        gen = SequenceGenerator(evaluator=ev, dependency_graph=g)
        se = SequenceEvaluator(evaluator=ev, dependency_graph=g, sequence_memory=mem)
        mp = MetaPlanner(
            generator=gen,
            sequence_evaluator=se,
            dependency_graph=g,
            sequence_memory=mem,
        )
        adv = AdvisorRuntime(meta_planner=mp, dependency_graph=g, sequence_memory=mem)
        adv.add_objective(_obj("a", 8))
        adv.add_objective(_obj("b", 5))
        result = adv.tick()
        assert result["meta_plan_selected"] is True
        state = adv.get_state()
        assert "dependency_edges" in state
        assert "sequence_memory_count" in state
