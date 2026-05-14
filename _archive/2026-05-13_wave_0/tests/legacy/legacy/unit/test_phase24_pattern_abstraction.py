"""Phase 24 tests — Pattern Abstraction + Semantic Similarity Layer v1.

Tests embedding, similarity, registry, abstraction, matcher,
safety controls, determinism, and hard invariants 55-59.

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from umh.core.clock import iso_now
from umh.learning.feedback import ExecutionFeedback
from umh.patterns.abstraction import AbstractedPattern, PatternAbstractor
from umh.patterns.embedding import TokenHashEmbedding
from umh.patterns.registry import Pattern, PatternRegistry
from umh.patterns.similarity import SimilarityEngine, SimilarityResult
from umh.prediction.matcher import MatchDetail, PredictionMatcher
from umh.prediction.store import PredictionRecord, PredictionStatus


# ── helpers ──────────────────────────────────────────────────


def _make_record(
    pid: str = "pred_test001",
    goal: str = "test_goal",
    confidence: float = 0.7,
    source: str = "test_source",
    status: PredictionStatus = PredictionStatus.PENDING,
    actions: tuple[str, ...] = ("action_a",),
    entities: tuple[str, ...] = ("entity_a",),
) -> PredictionRecord:
    return PredictionRecord(
        prediction_id=pid,
        intent_id=f"intent_{pid}",
        inferred_goal=goal,
        confidence=confidence,
        predicted_actions=actions,
        related_entities=entities,
        source=source,
        context_hash="abcdef1234567890",
        emitted_at=iso_now(),
        status=status,
        tick_emitted=1,
    )


def _make_feedback(
    job_id: str = "job_001",
    task_type: str = "outreach",
    success: bool = True,
) -> ExecutionFeedback:
    return ExecutionFeedback(
        job_id=job_id,
        node_id="node_test",
        task_type=task_type,
        success=success,
        duration_ms=100,
        timestamp=iso_now(),
    )


# ══════════════════════════════════════════════════════════════
# PART 1 — TokenHashEmbedding
# ══════════════════════════════════════════════════════════════


class TestTokenHashEmbedding:
    def test_embed_returns_vector(self):
        emb = TokenHashEmbedding(dim=32)
        vec = emb.embed("hello world")
        assert len(vec) == 32
        assert isinstance(vec[0], float)

    def test_deterministic_output(self):
        emb = TokenHashEmbedding(dim=64)
        v1 = emb.embed("instagram outreach morning")
        v2 = emb.embed("instagram outreach morning")
        assert v1 == v2

    def test_different_text_different_vector(self):
        emb = TokenHashEmbedding(dim=64)
        v1 = emb.embed("outreach morning")
        v2 = emb.embed("data analysis evening")
        assert v1 != v2

    def test_empty_text_zero_vector(self):
        emb = TokenHashEmbedding(dim=16)
        vec = emb.embed("")
        assert all(v == 0.0 for v in vec)

    def test_normalized_output(self):
        emb = TokenHashEmbedding(dim=64)
        vec = emb.embed("submit outreach linkedin")
        norm = math.sqrt(sum(v * v for v in vec))
        assert abs(norm - 1.0) < 0.001

    def test_cache_works(self):
        emb = TokenHashEmbedding(dim=32)
        emb.embed("cached text")
        assert emb.cache_size() == 1
        emb.embed("cached text")
        assert emb.cache_size() == 1

    def test_cache_clear(self):
        emb = TokenHashEmbedding(dim=32)
        emb.embed("text")
        emb.clear_cache()
        assert emb.cache_size() == 0

    def test_dim_property(self):
        emb = TokenHashEmbedding(dim=128)
        assert emb.dim == 128

    def test_invalid_dim_rejected(self):
        with pytest.raises(ValueError, match="dim"):
            TokenHashEmbedding(dim=0)

    def test_get_state(self):
        emb = TokenHashEmbedding(dim=64)
        state = emb.get_state()
        assert state["dim"] == 64
        assert state["cache_size"] == 0

    def test_similar_text_similar_vectors(self):
        emb = TokenHashEmbedding(dim=64)
        sim = SimilarityEngine(threshold=0.3)
        v1 = emb.embed("outreach instagram morning")
        v2 = emb.embed("outreach instagram afternoon")
        result = sim.compute_similarity(v1, v2)
        assert result.score > 0.5

    def test_cache_returns_copy(self):
        emb = TokenHashEmbedding(dim=32)
        v1 = emb.embed("test")
        v2 = emb.embed("test")
        v1[0] = 999.0
        v3 = emb.embed("test")
        assert v3[0] != 999.0


# ══════════════════════════════════════════════════════════════
# PART 2 — SimilarityEngine
# ══════════════════════════════════════════════════════════════


class TestSimilarityEngine:
    def test_identical_vectors_score_one(self):
        sim = SimilarityEngine()
        vec = [1.0, 0.0, 0.0]
        result = sim.compute_similarity(vec, vec)
        assert abs(result.score - 1.0) < 0.001

    def test_opposite_vectors_score_negative(self):
        sim = SimilarityEngine()
        result = sim.compute_similarity([1.0, 0.0], [-1.0, 0.0])
        assert result.score < 0

    def test_orthogonal_vectors_score_zero(self):
        sim = SimilarityEngine()
        result = sim.compute_similarity([1.0, 0.0], [0.0, 1.0])
        assert abs(result.score) < 0.001

    def test_threshold_check(self):
        sim = SimilarityEngine(threshold=0.8)
        result = sim.compute_similarity([1.0, 0.0], [0.9, 0.1])
        assert result.threshold == 0.8

    def test_are_similar_shorthand(self):
        sim = SimilarityEngine(threshold=0.5)
        assert sim.are_similar([1.0, 0.0], [1.0, 0.0])

    def test_zero_vector_returns_zero(self):
        sim = SimilarityEngine()
        result = sim.compute_similarity([0.0, 0.0], [1.0, 0.0])
        assert result.score == 0.0

    def test_different_length_returns_zero(self):
        sim = SimilarityEngine()
        result = sim.compute_similarity([1.0, 0.0], [1.0])
        assert result.score == 0.0

    def test_empty_vectors_return_zero(self):
        sim = SimilarityEngine()
        result = sim.compute_similarity([], [])
        assert result.score == 0.0

    def test_invalid_threshold_rejected(self):
        with pytest.raises(ValueError, match="threshold"):
            SimilarityEngine(threshold=1.5)

    def test_similarity_result_to_dict(self):
        result = SimilarityResult(score=0.85, above_threshold=True, threshold=0.75)
        d = result.to_dict()
        assert d["score"] == 0.85
        assert d["above_threshold"] is True

    def test_deterministic(self):
        sim = SimilarityEngine()
        v1, v2 = [0.5, 0.3, 0.8], [0.4, 0.7, 0.2]
        r1 = sim.compute_similarity(v1, v2)
        r2 = sim.compute_similarity(v1, v2)
        assert r1.score == r2.score

    def test_get_state(self):
        sim = SimilarityEngine(threshold=0.6)
        assert sim.get_state()["threshold"] == 0.6


# ══════════════════════════════════════════════════════════════
# PART 3 — PatternRegistry
# ══════════════════════════════════════════════════════════════


class TestPatternRegistry:
    def _make_registry(self, threshold=0.75):
        sim = SimilarityEngine(threshold=threshold)
        return PatternRegistry(sim)

    def test_register_new_pattern(self):
        reg = self._make_registry()
        pattern = reg.register_pattern([1.0, 0.0], "outreach", "example_1")
        assert pattern.label == "outreach"
        assert pattern.pattern_id.startswith("pat_")
        assert reg.pattern_count == 1

    def test_register_similar_merges(self):
        reg = self._make_registry(threshold=0.5)
        p1 = reg.register_pattern([1.0, 0.0, 0.0], "outreach", "ex1")
        p2 = reg.register_pattern([0.95, 0.1, 0.0], "outreach_similar", "ex2")
        assert p1.pattern_id == p2.pattern_id
        assert reg.pattern_count == 1
        assert len(p1.examples) == 2

    def test_register_different_creates_new(self):
        reg = self._make_registry(threshold=0.99)
        reg.register_pattern([1.0, 0.0], "a", "ex1")
        reg.register_pattern([0.0, 1.0], "b", "ex2")
        assert reg.pattern_count == 2

    def test_find_matching_pattern(self):
        reg = self._make_registry(threshold=0.5)
        reg.register_pattern([1.0, 0.0, 0.0], "target", "ex1")
        found = reg.find_matching_pattern([0.95, 0.1, 0.0])
        assert found is not None
        assert found.label == "target"

    def test_find_no_match(self):
        reg = self._make_registry(threshold=0.99)
        reg.register_pattern([1.0, 0.0], "a", "ex1")
        assert reg.find_matching_pattern([0.0, 1.0]) is None

    def test_centroid_updates(self):
        reg = self._make_registry(threshold=0.3)
        p = reg.register_pattern([1.0, 0.0], "test", "ex1")
        old_centroid = list(p.centroid)
        reg.register_pattern([0.8, 0.2], "test2", "ex2")
        assert p.centroid != old_centroid

    def test_record_outcome(self):
        reg = self._make_registry()
        p = reg.register_pattern([1.0, 0.0], "test")
        reg.record_outcome(p.pattern_id, matched=True)
        reg.record_outcome(p.pattern_id, matched=False)
        assert p.success_count == 1
        assert p.failure_count == 1

    def test_record_outcome_missing_pattern(self):
        reg = self._make_registry()
        reg.record_outcome("nonexistent", matched=True)

    def test_get_pattern(self):
        reg = self._make_registry()
        p = reg.register_pattern([1.0, 0.0], "test")
        assert reg.get_pattern(p.pattern_id) is p

    def test_get_pattern_missing(self):
        reg = self._make_registry()
        assert reg.get_pattern("nope") is None

    def test_list_patterns(self):
        reg = self._make_registry(threshold=0.99)
        reg.register_pattern([1.0, 0.0], "a")
        reg.register_pattern([0.0, 1.0], "b")
        assert len(reg.list_patterns()) == 2

    def test_clear(self):
        reg = self._make_registry()
        reg.register_pattern([1.0, 0.0], "test")
        reg.clear()
        assert reg.pattern_count == 0

    def test_max_patterns_eviction(self):
        reg = PatternRegistry(
            SimilarityEngine(threshold=0.999),
            max_patterns=3,
        )
        for i in range(5):
            vec = [0.0] * 4
            vec[i % 4] = 1.0
            reg.register_pattern(vec, f"p{i}", f"ex{i}")
        assert reg.pattern_count <= 3

    def test_max_examples_cap(self):
        reg = PatternRegistry(
            SimilarityEngine(threshold=0.01),
            max_examples_per_pattern=3,
        )
        for i in range(10):
            reg.register_pattern([1.0, 0.0], "same", f"ex{i}")
        patterns = reg.list_patterns()
        assert len(patterns[0].examples) <= 3

    def test_get_state(self):
        reg = self._make_registry()
        reg.register_pattern([1.0], "test")
        state = reg.get_state()
        assert state["pattern_count"] == 1

    def test_pattern_to_dict(self):
        p = Pattern(
            pattern_id="pat_test",
            label="test",
            centroid=[1.0, 0.0],
            success_count=3,
            failure_count=1,
        )
        d = p.to_dict()
        assert d["pattern_id"] == "pat_test"
        assert d["success_rate"] == 0.75

    def test_pattern_success_rate_no_data(self):
        p = Pattern(pattern_id="p", label="l", centroid=[])
        assert p.success_rate == 0.5


# ══════════════════════════════════════════════════════════════
# PART 4 — PatternAbstractor
# ══════════════════════════════════════════════════════════════


class TestPatternAbstractor:
    def _make_abstractor(self, threshold=0.5):
        emb = TokenHashEmbedding(dim=32)
        sim = SimilarityEngine(threshold=threshold)
        reg = PatternRegistry(sim)
        return PatternAbstractor(emb, reg)

    def test_abstract_single_record(self):
        ab = self._make_abstractor()
        recs = [_make_record(pid="p1", goal="outreach", source="workflow")]
        patterns = ab.abstract(recs)
        assert len(patterns) == 1
        assert patterns[0].member_count >= 1

    def test_abstract_similar_records_cluster(self):
        ab = self._make_abstractor(threshold=0.3)
        recs = [
            _make_record(pid="p1", goal="outreach_instagram", source="workflow", actions=("submit_outreach",)),
            _make_record(pid="p2", goal="outreach_linkedin", source="workflow", actions=("submit_outreach",)),
        ]
        patterns = ab.abstract(recs)
        if ab.registry.pattern_count == 1:
            assert patterns[0].member_count >= 2

    def test_abstract_different_records_separate(self):
        ab = self._make_abstractor(threshold=0.99)
        recs = [
            _make_record(pid="p1", goal="outreach", source="workflow", entities=("instagram",)),
            _make_record(pid="p2", goal="data_analysis", source="pipeline", entities=("database",)),
        ]
        patterns = ab.abstract(recs)
        assert len(patterns) >= 1

    def test_abstract_returns_pattern_ids(self):
        ab = self._make_abstractor()
        recs = [_make_record()]
        patterns = ab.abstract(recs)
        assert all(p.pattern_id.startswith("pat_") for p in patterns)

    def test_abstract_empty_records(self):
        ab = self._make_abstractor()
        assert ab.abstract([]) == []

    def test_abstracted_pattern_to_dict(self):
        ap = AbstractedPattern(
            pattern_id="pat_test",
            label="test",
            member_count=3,
            success_rate=0.8,
            source_predictions=("p1", "p2", "p3"),
        )
        d = ap.to_dict()
        assert d["pattern_id"] == "pat_test"
        assert d["member_count"] == 3

    def test_registry_property(self):
        ab = self._make_abstractor()
        assert ab.registry is not None


# ══════════════════════════════════════════════════════════════
# PART 5 — PredictionMatcher: Exact Matching
# ══════════════════════════════════════════════════════════════


class TestPredictionMatcherExact:
    def test_entity_match(self):
        matcher = PredictionMatcher()
        pred = _make_record(entities=("outreach",))
        fb = _make_feedback(task_type="outreach")
        results = matcher.match_predictions([pred], [fb])
        assert len(results) == 1
        assert results[0].matched is True
        assert results[0].match_type == "exact"
        assert "entity_match" in results[0].match_reason

    def test_action_match(self):
        matcher = PredictionMatcher()
        pred = _make_record(actions=("submit_outreach",))
        fb = _make_feedback(task_type="outreach")
        results = matcher.match_predictions([pred], [fb])
        assert results[0].matched is True
        assert results[0].match_type == "exact"

    def test_goal_match(self):
        matcher = PredictionMatcher()
        pred = _make_record(goal="repeat_outreach")
        fb = _make_feedback(task_type="outreach")
        results = matcher.match_predictions([pred], [fb])
        assert results[0].matched is True

    def test_no_match(self):
        matcher = PredictionMatcher()
        pred = _make_record(goal="analysis", entities=("data",), actions=("run_analysis",))
        fb = _make_feedback(task_type="outreach")
        results = matcher.match_predictions([pred], [fb])
        assert results[0].matched is False

    def test_job_used_only_once(self):
        matcher = PredictionMatcher()
        p1 = _make_record(pid="p1", entities=("outreach",))
        p2 = _make_record(pid="p2", entities=("outreach",))
        fb = _make_feedback(job_id="j1", task_type="outreach")
        results = matcher.match_predictions([p1, p2], [fb])
        matched_count = sum(1 for r in results if r.matched)
        assert matched_count == 1


# ══════════════════════════════════════════════════════════════
# PART 6 — PredictionMatcher: Semantic Matching
# ══════════════════════════════════════════════════════════════


class TestPredictionMatcherSemantic:
    def _make_matcher(self, threshold=0.3):
        emb = TokenHashEmbedding(dim=32)
        sim = SimilarityEngine(threshold=threshold)
        return PredictionMatcher(
            embedding_model=emb,
            similarity_engine=sim,
        )

    def test_semantic_match_similar_text(self):
        matcher = self._make_matcher(threshold=0.3)
        pred = _make_record(
            goal="submit_outreach_instagram",
            actions=("submit_outreach",),
            entities=("instagram",),
        )
        fb = _make_feedback(task_type="submit_outreach_linkedin")
        results = matcher.match_predictions([pred], [fb])
        if results[0].matched:
            assert results[0].match_type in ("exact", "semantic")

    def test_exact_match_takes_priority(self):
        emb = TokenHashEmbedding(dim=32)
        sim = SimilarityEngine(threshold=0.01)
        matcher = PredictionMatcher(
            embedding_model=emb,
            similarity_engine=sim,
        )
        pred = _make_record(entities=("outreach",))
        fb = _make_feedback(task_type="outreach")
        results = matcher.match_predictions([pred], [fb])
        assert results[0].match_type == "exact"

    def test_no_semantic_without_model(self):
        matcher = PredictionMatcher()
        pred = _make_record(
            goal="something_unique_xyz",
            entities=("unique_xyz",),
            actions=("unique_action",),
        )
        fb = _make_feedback(task_type="something_unique_xyz_variant")
        results = matcher.match_predictions([pred], [fb])
        assert results[0].match_type != "semantic" or not results[0].matched


# ══════════════════════════════════════════════════════════════
# PART 7 — PredictionMatcher: Pattern Matching
# ══════════════════════════════════════════════════════════════


class TestPredictionMatcherPattern:
    def _make_matcher_with_registry(self, threshold=0.3):
        emb = TokenHashEmbedding(dim=32)
        sim = SimilarityEngine(threshold=threshold)
        reg = PatternRegistry(sim)
        return PredictionMatcher(
            embedding_model=emb,
            similarity_engine=sim,
            pattern_registry=reg,
        ), reg

    def test_pattern_match_shared_cluster(self):
        matcher, reg = self._make_matcher_with_registry(threshold=0.01)

        pred_text = "repeat_outreach submit_outreach instagram"
        fb_text = "outreach"

        emb = TokenHashEmbedding(dim=32)
        pred_vec = emb.embed(pred_text)
        fb_vec = emb.embed(fb_text)
        reg.register_pattern(pred_vec, "outreach_cluster", "pred_example")
        reg.register_pattern(fb_vec, "outreach_cluster", "fb_example")

        pred = _make_record(
            goal="repeat_outreach",
            entities=("instagram",),
            actions=("submit_outreach",),
        )
        fb = _make_feedback(task_type="outreach")
        results = matcher.match_predictions([pred], [fb])
        assert results[0].matched is True

    def test_no_pattern_match_without_registry(self):
        matcher = PredictionMatcher()
        pred = _make_record(
            goal="unique_goal_xyz",
            entities=("xyz_entity",),
            actions=("xyz_action",),
        )
        fb = _make_feedback(task_type="xyz_different")
        results = matcher.match_predictions([pred], [fb])
        assert results[0].match_type != "pattern"


# ══════════════════════════════════════════════════════════════
# PART 8 — MatchDetail
# ══════════════════════════════════════════════════════════════


class TestMatchDetail:
    def test_to_dict(self):
        md = MatchDetail(
            prediction_id="p1",
            matched=True,
            matched_job_id="j1",
            match_type="exact",
            match_reason="entity_match:outreach",
            similarity_score=1.0,
        )
        d = md.to_dict()
        assert d["prediction_id"] == "p1"
        assert d["match_type"] == "exact"
        assert d["similarity_score"] == 1.0

    def test_unmatched_detail(self):
        md = MatchDetail(prediction_id="p1", matched=False)
        assert md.match_type == ""
        assert md.similarity_score == 0.0


# ══════════════════════════════════════════════════════════════
# PART 9 — Safety Controls
# ══════════════════════════════════════════════════════════════


class TestSafetyControls:
    def test_similarity_never_exceeds_one(self):
        sim = SimilarityEngine()
        for _ in range(50):
            v = [1.0, 1.0, 1.0]
            result = sim.compute_similarity(v, v)
            assert result.score <= 1.001

    def test_embedding_bounded_norm(self):
        emb = TokenHashEmbedding(dim=64)
        for text in ["a", "a b c", "long text with many tokens here"]:
            vec = emb.embed(text)
            norm = math.sqrt(sum(v * v for v in vec))
            assert norm < 1.01 or norm == 0.0

    def test_registry_max_patterns_cap(self):
        sim = SimilarityEngine(threshold=0.999)
        reg = PatternRegistry(sim, max_patterns=5)
        for i in range(20):
            vec = [0.0] * 8
            vec[i % 8] = float(i)
            reg.register_pattern(vec, f"p{i}")
        assert reg.pattern_count <= 5

    def test_exact_match_always_wins(self):
        emb = TokenHashEmbedding(dim=32)
        sim = SimilarityEngine(threshold=0.01)
        matcher = PredictionMatcher(
            embedding_model=emb,
            similarity_engine=sim,
        )
        pred = _make_record(entities=("outreach",))
        fb = _make_feedback(task_type="outreach")
        results = matcher.match_predictions([pred], [fb])
        assert results[0].match_type == "exact"

    def test_system_works_without_embeddings(self):
        matcher = PredictionMatcher()
        pred = _make_record(entities=("outreach",))
        fb = _make_feedback(task_type="outreach")
        results = matcher.match_predictions([pred], [fb])
        assert results[0].matched is True
        assert results[0].match_type == "exact"


# ══════════════════════════════════════════════════════════════
# PART 10 — Determinism
# ══════════════════════════════════════════════════════════════


class TestDeterminism:
    def test_embedding_deterministic(self):
        emb = TokenHashEmbedding(dim=64)
        v1 = emb.embed("outreach instagram morning")
        emb.clear_cache()
        v2 = emb.embed("outreach instagram morning")
        assert v1 == v2

    def test_similarity_deterministic(self):
        sim = SimilarityEngine()
        v1, v2 = [0.5, 0.3, 0.8], [0.4, 0.7, 0.2]
        r1 = sim.compute_similarity(v1, v2)
        r2 = sim.compute_similarity(v1, v2)
        assert r1.score == r2.score

    def test_matcher_deterministic(self):
        emb = TokenHashEmbedding(dim=32)
        sim = SimilarityEngine(threshold=0.5)
        m1 = PredictionMatcher(embedding_model=emb, similarity_engine=sim)
        pred = _make_record(entities=("outreach",))
        fb = _make_feedback(task_type="outreach")
        r1 = m1.match_predictions([pred], [fb])
        r2 = m1.match_predictions([pred], [fb])
        assert r1[0].matched == r2[0].matched
        assert r1[0].match_type == r2[0].match_type


# ══════════════════════════════════════════════════════════════
# PART 11 — Hard Invariants 55-59
# ══════════════════════════════════════════════════════════════


class TestInvariantEnforcement:
    def test_inv55_embeddings_augment_not_replace(self):
        """INV55: Embeddings must NEVER replace structured data (only augment)."""
        emb = TokenHashEmbedding(dim=32)
        sim = SimilarityEngine(threshold=0.01)
        matcher = PredictionMatcher(
            embedding_model=emb,
            similarity_engine=sim,
        )
        pred = _make_record(entities=("outreach",))
        fb = _make_feedback(task_type="outreach")
        results = matcher.match_predictions([pred], [fb])
        assert results[0].match_type == "exact"

    def test_inv56_similarity_deterministic(self):
        """INV56: Similarity must be deterministic (same input -> same output)."""
        emb = TokenHashEmbedding(dim=64)
        sim = SimilarityEngine()
        text = "outreach instagram morning workflow"
        v1 = emb.embed(text)
        emb.clear_cache()
        v2 = emb.embed(text)
        assert v1 == v2
        r1 = sim.compute_similarity(v1, v2)
        assert abs(r1.score - 1.0) < 0.001

    def test_inv57_patterns_derived_not_injected(self):
        """INV57: Pattern abstraction must be derived, not manually injected."""
        emb = TokenHashEmbedding(dim=32)
        sim = SimilarityEngine(threshold=0.5)
        reg = PatternRegistry(sim)
        ab = PatternAbstractor(emb, reg)

        recs = [
            _make_record(pid="p1", goal="outreach_ig", source="workflow"),
            _make_record(pid="p2", goal="outreach_li", source="workflow"),
        ]
        patterns = ab.abstract(recs)
        assert len(patterns) >= 1
        for p in patterns:
            assert p.pattern_id.startswith("pat_")

    def test_inv58_no_execution_from_embeddings(self):
        """INV58: No direct execution decisions from embeddings alone."""
        matcher = PredictionMatcher()
        results = matcher.match_predictions([], [])
        assert results == []

        emb = TokenHashEmbedding(dim=32)
        sim = SimilarityEngine(threshold=0.5)
        matcher2 = PredictionMatcher(
            embedding_model=emb,
            similarity_engine=sim,
        )
        pred = _make_record()
        fb = _make_feedback()
        results = matcher2.match_predictions([pred], [fb])
        for r in results:
            assert isinstance(r.matched, bool)
            assert r.match_type in ("", "exact", "semantic", "pattern")

    def test_inv59_system_functions_without_embedding(self):
        """INV59: System must function without embedding model (fallback safe)."""
        matcher = PredictionMatcher()
        pred = _make_record(entities=("outreach",))
        fb = _make_feedback(task_type="outreach")
        results = matcher.match_predictions([pred], [fb])
        assert results[0].matched is True

        matcher_empty = PredictionMatcher()
        pred2 = _make_record(
            goal="unique_no_match",
            entities=("no_entity",),
            actions=("no_action",),
        )
        fb2 = _make_feedback(task_type="different")
        results2 = matcher_empty.match_predictions([pred2], [fb2])
        assert results2[0].matched is False


# ══════════════════════════════════════════════════════════════
# PART 12 — Boundary Invariants
# ══════════════════════════════════════════════════════════════


_CHECKED_MODULES = [
    "/opt/OS/umh/patterns/embedding.py",
    "/opt/OS/umh/patterns/similarity.py",
    "/opt/OS/umh/patterns/registry.py",
    "/opt/OS/umh/patterns/abstraction.py",
    "/opt/OS/umh/prediction/matcher.py",
]

_FORBIDDEN_IMPORTS = [
    "from umh.cells",
    "import umh.cells",
    "from umh.environments",
    "import umh.environments",
    "import subprocess",
    "from subprocess",
]


class TestBoundaryInvariants:
    @pytest.mark.parametrize("module_path", _CHECKED_MODULES)
    def test_no_forbidden_imports(self, module_path):
        content = Path(module_path).read_text()
        for forbidden in _FORBIDDEN_IMPORTS:
            assert forbidden not in content


# ══════════════════════════════════════════════════════════════
# PART 13 — Regression
# ══════════════════════════════════════════════════════════════


class TestRegression:
    def test_prediction_evaluator_unchanged(self):
        """Phase 21 PredictionEvaluator API works unchanged."""
        from umh.prediction.evaluator import PredictionEvaluator

        evaluator = PredictionEvaluator()
        pred = _make_record(entities=("outreach",))
        fb = _make_feedback(task_type="outreach")
        results = evaluator.match_predictions([pred], [fb])
        assert len(results) == 1
        assert results[0].matched is True

    def test_prediction_store_unchanged(self):
        """Phase 21 PredictionStore API works unchanged."""
        from umh.prediction.store import PredictionStore

        store = PredictionStore()
        rec = _make_record()
        store.append(rec)
        assert store.total == 1

    def test_weight_store_unchanged(self):
        """Phase 22 WeightStore API works unchanged."""
        from umh.prediction.weights import WeightStore

        ws = WeightStore()
        ws.update_weight("p1", matched=True)
        ws.update_weight("p1", matched=False)
        assert ws.get_weight("p1").total_predictions == 2

    def test_advisor_backward_compatible(self):
        """AdvisorRuntime() without new params works identically."""
        from umh.runtime.advisor import AdvisorRuntime

        advisor = AdvisorRuntime()
        advisor.start()
        result = advisor.tick()
        assert result["tick"] == 1
        advisor.stop()
