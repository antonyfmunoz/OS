"""Campaign 7.3 — Recommendation Engine tests.

Tests unified recommendation synthesis: source merging, deduplication,
priority boosting, ordering, graceful degradation.
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.organism.recommendation_engine import (
    RecommendationEngine,
    UnifiedRecommendation,
    _token_overlap,
)


# ── Lightweight mocks ────────────────────────────────────────────────


class _MockRec:
    def __init__(self, title: str = "", priority_score: float = 0.5) -> None:
        self.title = title
        self.priority_score = priority_score

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "rationale": f"reason for {self.title}",
            "priority_score": self.priority_score,
            "dependency_chain": [],
            "created_at": time.time(),
        }


class _MockGapEngine:
    def __init__(self, recs: list | None = None) -> None:
        self._recs = recs or []

    def get_top_recommendations(self, limit: int = 10) -> list:
        return self._recs[:limit]


class _MockAction:
    def __init__(self, action: str = "", priority_score: float = 0.5) -> None:
        self.action = action
        self.priority_score = priority_score

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "reason": f"because {self.action}",
            "priority_score": self.priority_score,
            "generated_at": time.time(),
        }


class _MockNextActionEngine:
    def __init__(self, actions: list | None = None) -> None:
        self._actions = actions or []

    @property
    def actions(self) -> list:
        return self._actions


class _MockTickLoop:
    def __init__(self, candidates: list | None = None) -> None:
        self._candidates = candidates or []

    def get_strategic_state(self) -> dict:
        return {"candidate_queue": {"items": self._candidates}}


class _MockPrioritizedItem:
    def __init__(self, title: str = "", score: float = 0.5) -> None:
        self.title = title
        self.score = score


class _MockPriorityEngine:
    def __init__(self, priorities: list | None = None) -> None:
        self._priorities = priorities or []

    def top(self, limit: int = 5) -> list:
        return self._priorities[:limit]


def _make_engine(**kwargs) -> RecommendationEngine:
    return RecommendationEngine(**kwargs)


# ── UnifiedRecommendation tests ─────────────────────────────────────


class TestUnifiedRecommendation:
    def test_default_values(self) -> None:
        rec = UnifiedRecommendation()
        assert rec.recommendation_id.startswith("urec-")
        assert rec.confidence == 0.5
        assert rec.source == ""

    def test_to_dict_keys(self) -> None:
        rec = UnifiedRecommendation(action="test")
        d = rec.to_dict()
        expected = {
            "recommendation_id", "action", "reason", "confidence",
            "priority_score", "source", "entity_refs", "created_at",
        }
        assert set(d.keys()) == expected

    def test_confidence_rounding(self) -> None:
        rec = UnifiedRecommendation(confidence=0.123456789)
        assert rec.to_dict()["confidence"] == 0.1235


# ── Token overlap tests ────────────────────────────────────────────


class TestTokenOverlap:
    def test_identical(self) -> None:
        assert _token_overlap("deploy auth system", "deploy auth system") == 1.0

    def test_no_overlap(self) -> None:
        assert _token_overlap("deploy auth", "fix bugs now") == 0.0

    def test_partial_overlap(self) -> None:
        score = _token_overlap("deploy auth system", "deploy auth migration")
        assert 0.3 < score < 0.8

    def test_empty_string(self) -> None:
        assert _token_overlap("", "something") == 0.0
        assert _token_overlap("", "") == 0.0


# ── Source extraction tests ─────────────────────────────────────────


class TestSourceExtraction:
    def test_gap_engine_recs(self) -> None:
        recs = [_MockRec("fix auth", 0.8)]
        engine = _make_engine(gap_engine=_MockGapEngine(recs=recs))
        result = engine.generate_recommendations()
        assert len(result) == 1
        assert result[0].source == "gap_engine"
        assert "auth" in result[0].action

    def test_next_action_recs(self) -> None:
        actions = [_MockAction("deploy system", 0.7)]
        engine = _make_engine(next_action_engine=_MockNextActionEngine(actions=actions))
        result = engine.generate_recommendations()
        assert len(result) == 1
        assert result[0].source == "next_action"

    def test_tick_candidate_recs(self) -> None:
        candidates = [{"title": "candidate-1", "priority_score": 0.6, "domain": "infra"}]
        engine = _make_engine(tick_loop=_MockTickLoop(candidates=candidates))
        result = engine.generate_recommendations()
        assert len(result) == 1
        assert result[0].source == "tick_candidate"

    def test_all_sources_merged(self) -> None:
        engine = _make_engine(
            gap_engine=_MockGapEngine(recs=[_MockRec("gap rec")]),
            next_action_engine=_MockNextActionEngine(actions=[_MockAction("action rec")]),
            tick_loop=_MockTickLoop(candidates=[{"title": "tick rec", "priority_score": 0.3}]),
        )
        result = engine.generate_recommendations()
        sources = {r.source for r in result}
        assert sources == {"gap_engine", "next_action", "tick_candidate"}


# ── Deduplication tests ─────────────────────────────────────────────


class TestDeduplication:
    def test_similar_actions_merged(self) -> None:
        recs = [_MockRec("deploy auth system", 0.6)]
        actions = [_MockAction("deploy auth system now", 0.8)]
        engine = _make_engine(
            gap_engine=_MockGapEngine(recs=recs),
            next_action_engine=_MockNextActionEngine(actions=actions),
        )
        result = engine.generate_recommendations()
        assert len(result) == 1
        assert result[0].confidence >= 0.8

    def test_different_actions_kept(self) -> None:
        recs = [_MockRec("fix auth", 0.6)]
        actions = [_MockAction("deploy infrastructure", 0.8)]
        engine = _make_engine(
            gap_engine=_MockGapEngine(recs=recs),
            next_action_engine=_MockNextActionEngine(actions=actions),
        )
        result = engine.generate_recommendations()
        assert len(result) == 2

    def test_dedup_keeps_highest_confidence(self) -> None:
        recs = [_MockRec("deploy auth system", 0.3)]
        actions = [_MockAction("deploy auth system upgrade", 0.9)]
        engine = _make_engine(
            gap_engine=_MockGapEngine(recs=recs),
            next_action_engine=_MockNextActionEngine(actions=actions),
        )
        result = engine.generate_recommendations()
        assert len(result) == 1
        assert result[0].confidence >= 0.9

    def test_dedup_merges_entity_refs(self) -> None:
        r1 = UnifiedRecommendation(action="deploy auth", entity_refs=["ref-a"])
        r2 = UnifiedRecommendation(action="deploy auth system", entity_refs=["ref-b"])
        engine = _make_engine()
        deduped = engine._deduplicate([r1, r2])
        assert "ref-a" in deduped[0].entity_refs
        assert "ref-b" in deduped[0].entity_refs


# ── Priority boost tests ───────────────────────────────────────────


class TestPriorityBoost:
    def test_aligned_recommendation_boosted(self) -> None:
        recs = [_MockRec("fix auth migration", 0.5)]
        priorities = [_MockPrioritizedItem("auth migration needed", 0.9)]
        engine = _make_engine(
            gap_engine=_MockGapEngine(recs=recs),
            priority_engine=_MockPriorityEngine(priorities=priorities),
        )
        result = engine.generate_recommendations()
        assert result[0].priority_score > 0.5

    def test_unaligned_recommendation_not_boosted(self) -> None:
        recs = [_MockRec("deploy infrastructure", 0.5)]
        priorities = [_MockPrioritizedItem("auth migration", 0.9)]
        engine = _make_engine(
            gap_engine=_MockGapEngine(recs=recs),
            priority_engine=_MockPriorityEngine(priorities=priorities),
        )
        result = engine.generate_recommendations()
        assert result[0].priority_score == 0.5


# ── Ordering tests ──────────────────────────────────────────────────


class TestOrdering:
    def test_sorted_by_priority_score(self) -> None:
        recs = [_MockRec("low", 0.2), _MockRec("high", 0.9)]
        engine = _make_engine(gap_engine=_MockGapEngine(recs=recs))
        result = engine.generate_recommendations()
        scores = [r.priority_score for r in result]
        assert scores == sorted(scores, reverse=True)


# ── top() and next() tests ─────────────────────────────────────────


class TestTopAndNext:
    def test_top_limits(self) -> None:
        recs = [_MockRec(f"r-{i}", 0.1 * i) for i in range(8)]
        engine = _make_engine(gap_engine=_MockGapEngine(recs=recs))
        result = engine.top(limit=3)
        assert len(result) == 3

    def test_next_returns_highest(self) -> None:
        recs = [_MockRec("low", 0.2), _MockRec("high", 0.9)]
        engine = _make_engine(gap_engine=_MockGapEngine(recs=recs))
        best = engine.next()
        assert best is not None
        assert best.priority_score >= 0.9

    def test_next_returns_none_when_empty(self) -> None:
        engine = _make_engine()
        assert engine.next() is None

    def test_top_auto_generates(self) -> None:
        recs = [_MockRec("auto")]
        engine = _make_engine(gap_engine=_MockGapEngine(recs=recs))
        result = engine.top()
        assert len(result) == 1


# ── Graceful degradation ───────────────────────────────────────────


class TestGracefulDegradation:
    def test_no_engines(self) -> None:
        engine = _make_engine()
        assert engine.generate_recommendations() == []

    def test_broken_gap_engine(self) -> None:
        class _Broken:
            def get_top_recommendations(self, limit=10):
                raise RuntimeError("down")
        engine = _make_engine(gap_engine=_Broken())
        assert engine.generate_recommendations() == []

    def test_broken_next_action(self) -> None:
        class _Broken:
            @property
            def actions(self):
                raise RuntimeError("down")
        engine = _make_engine(next_action_engine=_Broken())
        assert engine.generate_recommendations() == []
