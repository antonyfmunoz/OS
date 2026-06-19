"""Campaign 7.1 — Priority Engine tests.

Tests deterministic priority synthesis: scoring formula, source merging,
ordering, constraint boosting, graceful degradation.
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.organism.priority_engine import (
    PrioritizedItem,
    PriorityEngine,
)


# ── Lightweight mocks ────────────────────────────────────────────────


class _MockGapEngine:
    def __init__(self, gaps: list | None = None) -> None:
        self._gaps = gaps or []

    def analyze(self) -> dict:
        return {"gaps": self._gaps, "gap_count": len(self._gaps)}


class _MockRuntimeAwareness:
    def __init__(self, blocked: list | None = None) -> None:
        self._blocked = blocked or []

    def blocked_work(self) -> list:
        return self._blocked


class _MockTickLoop:
    def __init__(self, drift: list | None = None) -> None:
        self._drift = drift or []

    def get_strategic_state(self) -> dict:
        return {"drift_warnings": self._drift}


class _MockKnowledgeEntry:
    def __init__(self, summary: str = "") -> None:
        self.summary = summary


class _MockKnowledgeAwareness:
    def __init__(self, constraints: list | None = None) -> None:
        self._constraints = constraints or []

    def find_constraints(self) -> list:
        return self._constraints


def _make_engine(**kwargs) -> PriorityEngine:
    return PriorityEngine(**kwargs)


def _old_gap(title: str = "gap", severity: str = "medium", days_old: int = 0) -> dict:
    return {
        "title": title,
        "severity": severity,
        "description": f"test gap: {title}",
        "created_at": time.time() - (days_old * 86400),
        "blocking_goals": [],
    }


# ── PrioritizedItem tests ───────────────────────────────────────────


class TestPrioritizedItem:
    def test_default_values(self) -> None:
        item = PrioritizedItem()
        assert item.priority_id.startswith("pri-")
        assert item.score == 0.0
        assert item.source == ""

    def test_to_dict_keys(self) -> None:
        item = PrioritizedItem(title="test", score=0.5)
        d = item.to_dict()
        expected = {
            "priority_id", "title", "rationale", "score",
            "impact_score", "urgency_score", "source",
            "entity_refs", "created_at",
        }
        assert set(d.keys()) == expected

    def test_score_rounding(self) -> None:
        item = PrioritizedItem(score=0.123456789)
        assert item.to_dict()["score"] == 0.1235


# ── Scoring formula tests ───────────────────────────────────────────


class TestScoringFormula:
    def test_critical_gap_scores_high(self) -> None:
        gaps = [_old_gap("critical-gap", "critical", days_old=15)]
        engine = _make_engine(gap_engine=_MockGapEngine(gaps=gaps))
        priorities = engine.compute_priorities()
        assert len(priorities) == 1
        assert priorities[0].impact_score == 1.0
        assert priorities[0].score > 0.3

    def test_low_gap_scores_low(self) -> None:
        gaps = [_old_gap("low-gap", "low", days_old=0)]
        engine = _make_engine(gap_engine=_MockGapEngine(gaps=gaps))
        priorities = engine.compute_priorities()
        assert priorities[0].impact_score == 0.25
        assert priorities[0].score < 0.2

    def test_blocker_gets_blocker_weight(self) -> None:
        blocked = [{"title": "auth-blocked", "reason": "missing dep"}]
        engine = _make_engine(
            runtime_awareness=_MockRuntimeAwareness(blocked=blocked),
        )
        priorities = engine.compute_priorities()
        assert priorities[0].source == "blocker"
        assert priorities[0].score > 0.4

    def test_older_items_more_urgent(self) -> None:
        gaps = [
            _old_gap("new-gap", "medium", days_old=0),
            _old_gap("old-gap", "medium", days_old=25),
        ]
        engine = _make_engine(gap_engine=_MockGapEngine(gaps=gaps))
        priorities = engine.compute_priorities()
        old = next(p for p in priorities if p.title == "old-gap")
        new = next(p for p in priorities if p.title == "new-gap")
        assert old.urgency_score > new.urgency_score
        assert old.score > new.score

    def test_score_clamped_to_1(self) -> None:
        gaps = [_old_gap("extreme", "critical", days_old=60)]
        blocked = [{"title": "extreme", "reason": "blocked"}]
        engine = _make_engine(
            gap_engine=_MockGapEngine(gaps=gaps),
            runtime_awareness=_MockRuntimeAwareness(blocked=blocked),
        )
        priorities = engine.compute_priorities()
        for p in priorities:
            assert p.score <= 1.0

    def test_determinism(self) -> None:
        gaps = [_old_gap("gap-a", "high", days_old=10)]
        engine = _make_engine(gap_engine=_MockGapEngine(gaps=gaps))
        r1 = engine.compute_priorities()
        r2 = engine.compute_priorities()
        assert r1[0].impact_score == r2[0].impact_score
        assert r1[0].source == r2[0].source


# ── Source merging tests ─────────────────────────────────────────────


class TestSourceMerging:
    def test_multiple_sources_merged(self) -> None:
        gaps = [_old_gap("gap-1", "high")]
        blocked = [{"title": "blocked-1"}]
        drift = [{"severity": "alert", "goal_title": "drift-1", "days_stagnant": 10}]
        engine = _make_engine(
            gap_engine=_MockGapEngine(gaps=gaps),
            runtime_awareness=_MockRuntimeAwareness(blocked=blocked),
            tick_loop=_MockTickLoop(drift=drift),
        )
        priorities = engine.compute_priorities()
        sources = {p.source for p in priorities}
        assert "gap" in sources
        assert "blocker" in sources
        assert "drift" in sources

    def test_sorted_by_score_descending(self) -> None:
        gaps = [
            _old_gap("critical-gap", "critical"),
            _old_gap("low-gap", "low"),
        ]
        engine = _make_engine(gap_engine=_MockGapEngine(gaps=gaps))
        priorities = engine.compute_priorities()
        scores = [p.score for p in priorities]
        assert scores == sorted(scores, reverse=True)


# ── by_source filter tests ──────────────────────────────────────────


class TestBySource:
    def test_filter_by_gap(self) -> None:
        gaps = [_old_gap("gap-1")]
        blocked = [{"title": "blocked-1"}]
        engine = _make_engine(
            gap_engine=_MockGapEngine(gaps=gaps),
            runtime_awareness=_MockRuntimeAwareness(blocked=blocked),
        )
        engine.compute_priorities()
        gap_only = engine.by_source("gap")
        assert all(p.source == "gap" for p in gap_only)
        assert len(gap_only) == 1

    def test_filter_returns_empty_for_missing_source(self) -> None:
        engine = _make_engine()
        engine.compute_priorities()
        assert engine.by_source("nonexistent") == []


# ── top() tests ─────────────────────────────────────────────────────


class TestTop:
    def test_top_limits_results(self) -> None:
        gaps = [_old_gap(f"gap-{i}", "medium") for i in range(10)]
        engine = _make_engine(gap_engine=_MockGapEngine(gaps=gaps))
        result = engine.top(limit=3)
        assert len(result) == 3

    def test_top_auto_computes(self) -> None:
        gaps = [_old_gap("auto")]
        engine = _make_engine(gap_engine=_MockGapEngine(gaps=gaps))
        result = engine.top()
        assert len(result) == 1

    def test_top_empty(self) -> None:
        engine = _make_engine()
        assert engine.top() == []


# ── Constraint boost tests ──────────────────────────────────────────


class TestConstraintBoost:
    def test_constraint_keyword_boosts_score(self) -> None:
        gaps = [_old_gap("authentication migration needed", "medium")]
        constraints = [_MockKnowledgeEntry("authentication must use oauth")]
        engine = _make_engine(
            gap_engine=_MockGapEngine(gaps=gaps),
            knowledge_awareness=_MockKnowledgeAwareness(constraints=constraints),
        )
        boosted = engine.compute_priorities()

        engine2 = _make_engine(gap_engine=_MockGapEngine(gaps=gaps))
        unboosted = engine2.compute_priorities()

        assert boosted[0].score >= unboosted[0].score


# ── Graceful degradation tests ──────────────────────────────────────


class TestGracefulDegradation:
    def test_no_engines(self) -> None:
        engine = _make_engine()
        assert engine.compute_priorities() == []

    def test_partial_engines(self) -> None:
        engine = _make_engine(
            gap_engine=_MockGapEngine(gaps=[_old_gap("only-gap")]),
        )
        priorities = engine.compute_priorities()
        assert len(priorities) == 1

    def test_broken_engine(self) -> None:
        class _Broken:
            def analyze(self):
                raise RuntimeError("down")

        engine = _make_engine(gap_engine=_Broken())
        assert engine.compute_priorities() == []

    def test_broken_runtime_awareness(self) -> None:
        class _Broken:
            def blocked_work(self):
                raise RuntimeError("down")

        engine = _make_engine(runtime_awareness=_Broken())
        assert engine.compute_priorities() == []


# ── Edge cases ──────────────────────────────────────────────────────


class TestEdgeCases:
    def test_drift_with_zero_days_stagnant(self) -> None:
        drift = [{"severity": "warning", "goal_title": "new-drift", "days_stagnant": 0}]
        engine = _make_engine(tick_loop=_MockTickLoop(drift=drift))
        priorities = engine.compute_priorities()
        assert priorities[0].urgency_score == 0.0

    def test_drift_with_high_days_stagnant(self) -> None:
        drift = [{"severity": "critical", "goal_title": "old-drift", "days_stagnant": 60}]
        engine = _make_engine(tick_loop=_MockTickLoop(drift=drift))
        priorities = engine.compute_priorities()
        assert priorities[0].urgency_score == 1.0

    def test_many_items_cap(self) -> None:
        gaps = [_old_gap(f"gap-{i}", "low") for i in range(25)]
        engine = _make_engine(gap_engine=_MockGapEngine(gaps=gaps))
        priorities = engine.compute_priorities()
        assert len(priorities) <= 20
