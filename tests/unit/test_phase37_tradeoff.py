"""Phase 37 — Multi-Objective Tradeoff Resolution Layer v1.

Tests for:
  - TradeoffDimension (creation, frozen, clamping, to_dict)
  - TradeoffProfile (creation, properties, to_dict)
  - CandidateScore (creation, frozen, to_dict)
  - TradeoffResult (creation, frozen, to_dict)
  - TradeoffInfluence (creation, to_dict)
  - Normalization (maximize, minimize, edge cases)
  - Weighted scoring (balanced, unbalanced, zero weight)
  - Pareto filtering (dominated, frontier, ties)
  - Tolerance filtering
  - TradeoffEngine (resolve, determinism, no dimensions)
  - TradeoffScorer (disabled, enabled, auto-profile, bounds)
  - GoalHierarchy collect_meta_scores
  - Meta-planner integration
  - End-to-end pipeline
  - Stability / determinism
  - Hard invariants 121-125
  - Explainability
  - Boundary / exports / compile
"""

from __future__ import annotations

import ast
import sys
from dataclasses import FrozenInstanceError

import pytest

sys.path.insert(0, "/opt/OS")


# ---------------------------------------------------------------------------
# Section 1: TradeoffDimension
# ---------------------------------------------------------------------------


class TestTradeoffDimension:
    def test_creation(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension

        d = TradeoffDimension(name="latency", direction="minimize", weight=2.0)
        assert d.name == "latency"
        assert d.direction == "minimize"
        assert d.weight == 2.0

    def test_frozen(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension

        d = TradeoffDimension(name="x")
        with pytest.raises(FrozenInstanceError):
            d.name = "y"  # type: ignore[misc]

    def test_defaults(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension

        d = TradeoffDimension(name="x")
        assert d.direction == "maximize"
        assert d.weight == 1.0
        assert d.tolerance == 0.0

    def test_invalid_direction_corrected(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension

        d = TradeoffDimension(name="x", direction="invalid")
        assert d.direction == "maximize"

    def test_weight_clamped_high(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension

        d = TradeoffDimension(name="x", weight=999.0)
        assert d.weight == 10.0

    def test_weight_clamped_low(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension

        d = TradeoffDimension(name="x", weight=-5.0)
        assert d.weight == 0.0

    def test_tolerance_clamped(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension

        d = TradeoffDimension(name="x", tolerance=5.0)
        assert d.tolerance == 1.0

    def test_to_dict(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension

        d = TradeoffDimension(name="success", direction="maximize", weight=1.5, tolerance=0.3)
        dd = d.to_dict()
        assert dd["name"] == "success"
        assert dd["direction"] == "maximize"
        assert dd["weight"] == 1.5
        assert dd["tolerance"] == 0.3


# ---------------------------------------------------------------------------
# Section 2: TradeoffProfile
# ---------------------------------------------------------------------------


class TestTradeoffProfile:
    def test_creation(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile

        p = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="a"),
                TradeoffDimension(name="b"),
            ),
            name="test",
        )
        assert p.dimension_count == 2
        assert p.name == "test"

    def test_frozen(self) -> None:
        from umh.runtime.tradeoff import TradeoffProfile

        p = TradeoffProfile(dimensions=())
        with pytest.raises(FrozenInstanceError):
            p.name = "x"  # type: ignore[misc]

    def test_dimension_names(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile

        p = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="alpha"),
                TradeoffDimension(name="beta"),
            )
        )
        assert p.dimension_names == ["alpha", "beta"]

    def test_total_weight(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile

        p = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="a", weight=2.0),
                TradeoffDimension(name="b", weight=3.0),
            )
        )
        assert p.total_weight() == 5.0

    def test_empty_profile(self) -> None:
        from umh.runtime.tradeoff import TradeoffProfile

        p = TradeoffProfile(dimensions=())
        assert p.dimension_count == 0
        assert p.total_weight() == 0.0

    def test_to_dict(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile

        p = TradeoffProfile(
            dimensions=(TradeoffDimension(name="a"),),
            name="test",
        )
        d = p.to_dict()
        assert d["name"] == "test"
        assert d["dimension_count"] == 1
        assert len(d["dimensions"]) == 1


# ---------------------------------------------------------------------------
# Section 3: CandidateScore
# ---------------------------------------------------------------------------


class TestCandidateScore:
    def test_creation(self) -> None:
        from umh.runtime.tradeoff import CandidateScore

        cs = CandidateScore(
            candidate_id="c1",
            raw_values={"a": 0.8},
            normalized_values={"a": 0.8},
            weighted_score=0.8,
            dimension_contributions={"a": 0.8},
        )
        assert cs.candidate_id == "c1"
        assert cs.weighted_score == 0.8

    def test_frozen(self) -> None:
        from umh.runtime.tradeoff import CandidateScore

        cs = CandidateScore("c1", {}, {}, 0.5, {})
        with pytest.raises(FrozenInstanceError):
            cs.weighted_score = 1.0  # type: ignore[misc]

    def test_to_dict(self) -> None:
        from umh.runtime.tradeoff import CandidateScore

        cs = CandidateScore("c1", {"a": 0.12345}, {"a": 0.67890}, 0.5, {"a": 0.5})
        d = cs.to_dict()
        assert d["candidate_id"] == "c1"
        assert d["raw_values"]["a"] == 0.1235
        assert d["normalized_values"]["a"] == 0.6789

    def test_to_dict_sorted(self) -> None:
        from umh.runtime.tradeoff import CandidateScore

        cs = CandidateScore(
            "c1", {"z": 1.0, "a": 0.5}, {"z": 1.0, "a": 0.5}, 0.75, {"z": 0.5, "a": 0.25}
        )
        d = cs.to_dict()
        assert list(d["raw_values"].keys()) == ["a", "z"]


# ---------------------------------------------------------------------------
# Section 4: TradeoffResult
# ---------------------------------------------------------------------------


class TestTradeoffResult:
    def test_creation(self) -> None:
        from umh.runtime.tradeoff import CandidateScore, TradeoffProfile, TradeoffResult

        best = CandidateScore("c1", {}, {}, 0.8, {})
        r = TradeoffResult(
            best=best,
            ranked=(best,),
            pareto_frontier=("c1",),
            dominated=(),
            profile=TradeoffProfile(dimensions=()),
            reason="test",
        )
        assert r.best.candidate_id == "c1"

    def test_frozen(self) -> None:
        from umh.runtime.tradeoff import CandidateScore, TradeoffProfile, TradeoffResult

        best = CandidateScore("c1", {}, {}, 0.8, {})
        r = TradeoffResult(best, (best,), ("c1",), (), TradeoffProfile(dimensions=()), "r")
        with pytest.raises(FrozenInstanceError):
            r.reason = "x"  # type: ignore[misc]

    def test_to_dict(self) -> None:
        from umh.runtime.tradeoff import CandidateScore, TradeoffProfile, TradeoffResult

        best = CandidateScore("c1", {"a": 0.8}, {"a": 1.0}, 0.8, {"a": 0.8})
        r = TradeoffResult(
            best=best,
            ranked=(best,),
            pareto_frontier=("c1",),
            dominated=("c2",),
            profile=TradeoffProfile(dimensions=()),
            reason="test reason",
        )
        d = r.to_dict()
        assert d["best_candidate"] == "c1"
        assert d["dominated"] == ["c2"]


# ---------------------------------------------------------------------------
# Section 5: TradeoffInfluence
# ---------------------------------------------------------------------------


class TestTradeoffInfluence:
    def test_creation(self) -> None:
        from umh.runtime.tradeoff import TradeoffInfluence

        ti = TradeoffInfluence(factor=1.05, tradeoff_result=None, reason="test")
        assert ti.factor == 1.05

    def test_frozen(self) -> None:
        from umh.runtime.tradeoff import TradeoffInfluence

        ti = TradeoffInfluence(factor=1.0, tradeoff_result=None, reason="r")
        with pytest.raises(FrozenInstanceError):
            ti.factor = 0.9  # type: ignore[misc]

    def test_to_dict_without_result(self) -> None:
        from umh.runtime.tradeoff import TradeoffInfluence

        ti = TradeoffInfluence(factor=1.0, tradeoff_result=None, reason="disabled")
        d = ti.to_dict()
        assert d["factor"] == 1.0
        assert "tradeoff" not in d

    def test_to_dict_with_result(self) -> None:
        from umh.runtime.tradeoff import (
            CandidateScore,
            TradeoffInfluence,
            TradeoffProfile,
            TradeoffResult,
        )

        best = CandidateScore("c1", {}, {}, 0.8, {})
        result = TradeoffResult(best, (best,), ("c1",), (), TradeoffProfile(dimensions=()), "r")
        ti = TradeoffInfluence(factor=1.05, tradeoff_result=result, reason="active")
        d = ti.to_dict()
        assert "tradeoff" in d


# ---------------------------------------------------------------------------
# Section 6: Normalization
# ---------------------------------------------------------------------------


class TestNormalization:
    def test_maximize_basic(self) -> None:
        from umh.runtime.tradeoff import normalize_value

        assert normalize_value(0.5, 0.0, 1.0, "maximize") == 0.5

    def test_maximize_min(self) -> None:
        from umh.runtime.tradeoff import normalize_value

        assert normalize_value(0.0, 0.0, 1.0, "maximize") == 0.0

    def test_maximize_max(self) -> None:
        from umh.runtime.tradeoff import normalize_value

        assert normalize_value(1.0, 0.0, 1.0, "maximize") == 1.0

    def test_minimize_basic(self) -> None:
        from umh.runtime.tradeoff import normalize_value

        assert normalize_value(0.5, 0.0, 1.0, "minimize") == 0.5

    def test_minimize_min_gives_one(self) -> None:
        from umh.runtime.tradeoff import normalize_value

        assert normalize_value(0.0, 0.0, 1.0, "minimize") == 1.0

    def test_minimize_max_gives_zero(self) -> None:
        from umh.runtime.tradeoff import normalize_value

        assert normalize_value(1.0, 0.0, 1.0, "minimize") == 0.0

    def test_equal_range_returns_half(self) -> None:
        from umh.runtime.tradeoff import normalize_value

        assert normalize_value(5.0, 5.0, 5.0, "maximize") == 0.5

    def test_out_of_range_clamped_high(self) -> None:
        from umh.runtime.tradeoff import normalize_value

        assert normalize_value(2.0, 0.0, 1.0, "maximize") == 1.0

    def test_out_of_range_clamped_low(self) -> None:
        from umh.runtime.tradeoff import normalize_value

        assert normalize_value(-1.0, 0.0, 1.0, "maximize") == 0.0

    def test_custom_range(self) -> None:
        from umh.runtime.tradeoff import normalize_value

        result = normalize_value(75.0, 50.0, 100.0, "maximize")
        assert abs(result - 0.5) < 0.001


# ---------------------------------------------------------------------------
# Section 7: Weighted scoring
# ---------------------------------------------------------------------------


class TestWeightedScoring:
    def test_equal_weights(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, compute_weighted_score

        dims = (
            TradeoffDimension(name="a", weight=1.0),
            TradeoffDimension(name="b", weight=1.0),
        )
        score, contribs = compute_weighted_score({"a": 0.8, "b": 0.6}, dims)
        assert abs(score - 0.7) < 0.001

    def test_unequal_weights(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, compute_weighted_score

        dims = (
            TradeoffDimension(name="a", weight=3.0),
            TradeoffDimension(name="b", weight=1.0),
        )
        score, contribs = compute_weighted_score({"a": 1.0, "b": 0.0}, dims)
        assert abs(score - 0.75) < 0.001

    def test_single_dimension(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, compute_weighted_score

        dims = (TradeoffDimension(name="a", weight=2.0),)
        score, contribs = compute_weighted_score({"a": 0.6}, dims)
        assert abs(score - 0.6) < 0.001

    def test_zero_weight_returns_half(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, compute_weighted_score

        dims = (TradeoffDimension(name="a", weight=0.0),)
        score, _ = compute_weighted_score({"a": 1.0}, dims)
        assert score == 0.5

    def test_missing_value_uses_half(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, compute_weighted_score

        dims = (
            TradeoffDimension(name="a", weight=1.0),
            TradeoffDimension(name="b", weight=1.0),
        )
        score, _ = compute_weighted_score({"a": 1.0}, dims)
        assert abs(score - 0.75) < 0.001

    def test_contributions_sum_to_score(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, compute_weighted_score

        dims = (
            TradeoffDimension(name="a", weight=2.0),
            TradeoffDimension(name="b", weight=3.0),
        )
        score, contribs = compute_weighted_score({"a": 0.8, "b": 0.4}, dims)
        assert abs(sum(contribs.values()) - score) < 0.0001


# ---------------------------------------------------------------------------
# Section 8: Pareto filtering
# ---------------------------------------------------------------------------


class TestParetoFilter:
    def test_single_candidate(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, pareto_filter

        dims = (TradeoffDimension(name="a"),)
        frontier, dominated = pareto_filter({"c1": {"a": 0.5}}, dims)
        assert frontier == ["c1"]
        assert dominated == []

    def test_one_dominates(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, pareto_filter

        dims = (
            TradeoffDimension(name="a"),
            TradeoffDimension(name="b"),
        )
        candidates = {
            "c1": {"a": 0.8, "b": 0.9},
            "c2": {"a": 0.3, "b": 0.2},
        }
        frontier, dominated = pareto_filter(candidates, dims)
        assert frontier == ["c1"]
        assert dominated == ["c2"]

    def test_none_dominated(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, pareto_filter

        dims = (
            TradeoffDimension(name="a"),
            TradeoffDimension(name="b"),
        )
        candidates = {
            "c1": {"a": 0.8, "b": 0.3},
            "c2": {"a": 0.3, "b": 0.8},
        }
        frontier, dominated = pareto_filter(candidates, dims)
        assert frontier == ["c1", "c2"]
        assert dominated == []

    def test_multiple_dominated(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, pareto_filter

        dims = (
            TradeoffDimension(name="a"),
            TradeoffDimension(name="b"),
        )
        candidates = {
            "c1": {"a": 0.9, "b": 0.9},
            "c2": {"a": 0.3, "b": 0.2},
            "c3": {"a": 0.1, "b": 0.1},
        }
        frontier, dominated = pareto_filter(candidates, dims)
        assert frontier == ["c1"]
        assert set(dominated) == {"c2", "c3"}

    def test_equal_not_dominated(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, pareto_filter

        dims = (TradeoffDimension(name="a"),)
        candidates = {
            "c1": {"a": 0.5},
            "c2": {"a": 0.5},
        }
        frontier, dominated = pareto_filter(candidates, dims)
        assert frontier == ["c1", "c2"]

    def test_deterministic_ordering(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, pareto_filter

        dims = (TradeoffDimension(name="a"),)
        candidates = {"z": {"a": 0.9}, "a": {"a": 0.1}, "m": {"a": 0.5}}
        frontier, dominated = pareto_filter(candidates, dims)
        assert frontier == sorted(frontier)
        assert dominated == sorted(dominated)

    def test_is_dominated_function(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, is_dominated

        dims = (TradeoffDimension(name="a"), TradeoffDimension(name="b"))
        assert is_dominated({"a": 0.3, "b": 0.2}, {"a": 0.8, "b": 0.9}, dims)
        assert not is_dominated({"a": 0.8, "b": 0.9}, {"a": 0.3, "b": 0.2}, dims)

    def test_partial_dominance_not_dominated(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, is_dominated

        dims = (TradeoffDimension(name="a"), TradeoffDimension(name="b"))
        assert not is_dominated({"a": 0.8, "b": 0.2}, {"a": 0.3, "b": 0.9}, dims)


# ---------------------------------------------------------------------------
# Section 9: Tolerance filtering
# ---------------------------------------------------------------------------


class TestToleranceFiltering:
    def test_no_tolerance_all_pass(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="a", tolerance=0.0),))
        engine = TradeoffEngine(profile=profile)
        result = engine.resolve({"c1": {"a": 0.1}, "c2": {"a": 0.9}})
        assert result is not None
        assert len(result.ranked) == 2

    def test_tolerance_filters_low(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="a", tolerance=0.5),))
        engine = TradeoffEngine(profile=profile)
        result = engine.resolve({"c1": {"a": 0.1}, "c2": {"a": 0.9}})
        assert result is not None
        assert result.best.candidate_id == "c2"

    def test_tolerance_keeps_all_when_all_fail(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="a", tolerance=0.99),
                TradeoffDimension(name="b", tolerance=0.99),
            )
        )
        engine = TradeoffEngine(profile=profile)
        result = engine.resolve(
            {
                "c1": {"a": 0.1, "b": 0.9},
                "c2": {"a": 0.9, "b": 0.1},
            }
        )
        assert result is not None
        assert len(result.ranked) == 2


# ---------------------------------------------------------------------------
# Section 10: TradeoffEngine
# ---------------------------------------------------------------------------


class TestTradeoffEngine:
    def test_empty_candidates(self) -> None:
        from umh.runtime.tradeoff import TradeoffEngine

        engine = TradeoffEngine()
        result = engine.resolve({})
        assert result is None

    def test_single_candidate(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="a"),))
        engine = TradeoffEngine(profile=profile)
        result = engine.resolve({"c1": {"a": 0.8}})
        assert result is not None
        assert result.best.candidate_id == "c1"

    def test_best_wins(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="success", weight=1.0),
                TradeoffDimension(name="speed", weight=1.0),
            )
        )
        engine = TradeoffEngine(profile=profile)
        result = engine.resolve(
            {
                "c1": {"success": 0.9, "speed": 0.8},
                "c2": {"success": 0.3, "speed": 0.2},
            }
        )
        assert result is not None
        assert result.best.candidate_id == "c1"

    def test_deterministic_output(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="a"),
                TradeoffDimension(name="b"),
            )
        )
        engine = TradeoffEngine(profile=profile)
        cands = {"c1": {"a": 0.7, "b": 0.3}, "c2": {"a": 0.3, "b": 0.7}}
        r1 = engine.resolve(cands)
        r2 = engine.resolve(cands)
        assert r1 is not None and r2 is not None
        assert r1.best.candidate_id == r2.best.candidate_id
        assert r1.best.weighted_score == r2.best.weighted_score

    def test_no_dimensions_fallback(self) -> None:
        from umh.runtime.tradeoff import TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(dimensions=())
        engine = TradeoffEngine(profile=profile)
        result = engine.resolve({"c1": {"a": 0.8}, "c2": {"a": 0.2}})
        assert result is not None
        assert result.best.candidate_id == "c1"
        assert "no dimensions" in result.reason

    def test_pareto_disabled(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="a"),))
        engine = TradeoffEngine(profile=profile, enable_pareto=False)
        result = engine.resolve({"c1": {"a": 0.9}, "c2": {"a": 0.1}})
        assert result is not None
        assert len(result.dominated) == 0

    def test_minimize_dimension(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(
            dimensions=(TradeoffDimension(name="latency", direction="minimize"),)
        )
        engine = TradeoffEngine(profile=profile)
        result = engine.resolve(
            {
                "c1": {"latency": 100.0},
                "c2": {"latency": 10.0},
            }
        )
        assert result is not None
        assert result.best.candidate_id == "c2"

    def test_profile_override(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        default_profile = TradeoffProfile(dimensions=(TradeoffDimension(name="a"),))
        override_profile = TradeoffProfile(
            dimensions=(TradeoffDimension(name="b"),),
            name="override",
        )
        engine = TradeoffEngine(profile=default_profile)
        result = engine.resolve(
            {"c1": {"a": 0.9, "b": 0.1}, "c2": {"a": 0.1, "b": 0.9}},
            profile=override_profile,
        )
        assert result is not None
        assert result.best.candidate_id == "c2"

    def test_three_candidates(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="a", weight=1.0),
                TradeoffDimension(name="b", weight=1.0),
            )
        )
        engine = TradeoffEngine(profile=profile)
        result = engine.resolve(
            {
                "c1": {"a": 0.9, "b": 0.9},
                "c2": {"a": 0.5, "b": 0.5},
                "c3": {"a": 0.1, "b": 0.1},
            }
        )
        assert result is not None
        assert result.best.candidate_id == "c1"
        assert "c3" in result.dominated

    def test_weighted_preference(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="a", weight=10.0),
                TradeoffDimension(name="b", weight=1.0),
            )
        )
        engine = TradeoffEngine(profile=profile)
        result = engine.resolve(
            {
                "c1": {"a": 0.9, "b": 0.1},
                "c2": {"a": 0.1, "b": 0.9},
            }
        )
        assert result is not None
        assert result.best.candidate_id == "c1"


# ---------------------------------------------------------------------------
# Section 11: TradeoffScorer
# ---------------------------------------------------------------------------


class TestTradeoffScorer:
    def test_disabled(self) -> None:
        from umh.runtime.tradeoff import TradeoffScorer

        scorer = TradeoffScorer(enabled=False)
        result = scorer.compute_factor(meta_goal_scores={"a": 0.8}, candidate_id="c1")
        assert result.factor == 1.0
        assert "disabled" in result.reason

    def test_no_scores(self) -> None:
        from umh.runtime.tradeoff import TradeoffScorer

        scorer = TradeoffScorer(enabled=True)
        result = scorer.compute_factor(meta_goal_scores={}, candidate_id="c1")
        assert result.factor == 1.0

    def test_no_candidate(self) -> None:
        from umh.runtime.tradeoff import TradeoffScorer

        scorer = TradeoffScorer(enabled=True)
        result = scorer.compute_factor(meta_goal_scores={"a": 0.8})
        assert result.factor == 1.0

    def test_enabled_with_data(self) -> None:
        from umh.runtime.tradeoff import TradeoffScorer

        scorer = TradeoffScorer(enabled=True)
        result = scorer.compute_factor(
            meta_goal_scores={"biz": 0.8, "personal": 0.6},
            candidate_id="c1",
        )
        assert 0.85 <= result.factor <= 1.15

    def test_factor_bounded_min(self) -> None:
        from umh.runtime.tradeoff import TradeoffScorer

        scorer = TradeoffScorer(enabled=True)
        result = scorer.compute_factor(
            meta_goal_scores={"a": 0.0},
            candidate_id="c1",
        )
        assert result.factor >= 0.85

    def test_factor_bounded_max(self) -> None:
        from umh.runtime.tradeoff import TradeoffScorer

        scorer = TradeoffScorer(enabled=True)
        result = scorer.compute_factor(
            meta_goal_scores={"a": 10.0},
            candidate_id="c1",
        )
        assert result.factor <= 1.15

    def test_auto_profile_generated(self) -> None:
        from umh.runtime.tradeoff import TradeoffScorer

        scorer = TradeoffScorer(enabled=True)
        result = scorer.compute_factor(
            meta_goal_scores={"biz": 0.8, "personal": 0.6},
            candidate_id="c1",
        )
        assert result.tradeoff_result is not None

    def test_custom_profile(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile, TradeoffScorer

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="biz", weight=3.0),
                TradeoffDimension(name="personal", weight=1.0),
            ),
            name="custom",
        )
        scorer = TradeoffScorer(profile=profile, enabled=True)
        result = scorer.compute_factor(
            meta_goal_scores={"biz": 0.9, "personal": 0.3},
            candidate_id="c1",
        )
        assert result.tradeoff_result is not None
        assert result.tradeoff_result.profile.name == "custom"
        assert 0.85 <= result.factor <= 1.15

    def test_properties(self) -> None:
        from umh.runtime.tradeoff import TradeoffEngine, TradeoffScorer

        engine = TradeoffEngine()
        scorer = TradeoffScorer(engine=engine, enabled=True)
        assert scorer.engine is engine
        assert scorer.enabled is True
        assert scorer.profile is None


# ---------------------------------------------------------------------------
# Section 12: GoalHierarchy collect_meta_scores
# ---------------------------------------------------------------------------


class TestCollectMetaScores:
    def test_disabled_returns_empty(self) -> None:
        from umh.runtime.goal_hierarchy import HierarchyScorer

        scorer = HierarchyScorer(enabled=False)
        assert scorer.collect_meta_scores(goal_type="revenue") == {}

    def test_no_hierarchy_returns_empty(self) -> None:
        from umh.runtime.goal_hierarchy import HierarchyScorer

        scorer = HierarchyScorer(enabled=True)
        assert scorer.collect_meta_scores(goal_type="revenue") == {}

    def test_no_goal_type_returns_empty(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue",)))
        scorer = HierarchyScorer(hierarchy=h, enabled=True)
        assert scorer.collect_meta_scores(goal_type="") == {}

    def test_type_not_in_hierarchy(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue",)))
        scorer = HierarchyScorer(hierarchy=h, enabled=True)
        assert scorer.collect_meta_scores(goal_type="health") == {}

    def test_with_data(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import ReinforcementScorer

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue",)))
        mem = GoalMemory()
        mem.append(
            make_goal_record(
                goal_id="g1",
                goal_type="revenue",
                duration_ticks=100,
                completed=True,
                success_rate=0.8,
                identity_alignment=0.7,
                reward=0.5,
            )
        )
        scorer = HierarchyScorer(
            hierarchy=h,
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        scores = scorer.collect_meta_scores(goal_type="revenue")
        assert "biz" in scores
        assert 0.5 <= scores["biz"] <= 1.5

    def test_multiple_meta_goals(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import ReinforcementScorer

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue",)))
        h.register_meta_goal(MetaGoal(name="growth", child_goal_types=("revenue",)))
        mem = GoalMemory()
        mem.append(
            make_goal_record(
                goal_id="g1",
                goal_type="revenue",
                duration_ticks=100,
                completed=True,
                success_rate=0.8,
                identity_alignment=0.7,
                reward=0.5,
            )
        )
        scorer = HierarchyScorer(
            hierarchy=h,
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        scores = scorer.collect_meta_scores(goal_type="revenue")
        assert "biz" in scores
        assert "growth" in scores


# ---------------------------------------------------------------------------
# Section 13: Meta-planner integration
# ---------------------------------------------------------------------------


class TestMetaPlannerIntegration:
    def _make_objective(self, oid: str, priority: int = 5, goal_type: str = ""):
        from umh.runtime.arbitration import Objective

        metadata = {}
        if goal_type:
            metadata["goal_type"] = goal_type
        return Objective(
            objective_id=oid,
            description=f"Obj {oid}",
            priority=priority,
            effort_estimate=1.0,
            expected_value=1.0,
            metadata=metadata,
        )

    def test_evaluator_tradeoff_property(self) -> None:
        from umh.runtime.meta_planner import SequenceEvaluator
        from umh.runtime.tradeoff import TradeoffScorer

        scorer = TradeoffScorer(enabled=True)
        ev = SequenceEvaluator(tradeoff_scorer=scorer)
        assert ev.tradeoff_scorer is scorer

    def test_evaluator_tradeoff_none_default(self) -> None:
        from umh.runtime.meta_planner import SequenceEvaluator

        ev = SequenceEvaluator()
        assert ev.tradeoff_scorer is None

    def test_planner_tradeoff_property(self) -> None:
        from umh.runtime.meta_planner import MetaPlanner
        from umh.runtime.tradeoff import TradeoffScorer

        scorer = TradeoffScorer(enabled=True)
        planner = MetaPlanner(tradeoff_scorer=scorer)
        assert planner.tradeoff_scorer is scorer

    def test_score_affected_by_tradeoff(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import ReinforcementScorer
        from umh.runtime.meta_planner import SequenceEvaluator
        from umh.runtime.tradeoff import (
            TradeoffDimension,
            TradeoffProfile,
            TradeoffScorer,
        )

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue", "growth")))
        mem = GoalMemory()
        for _ in range(5):
            mem.append(
                make_goal_record(
                    goal_id="g1",
                    goal_type="revenue",
                    duration_ticks=100,
                    completed=True,
                    success_rate=0.6,
                    identity_alignment=0.7,
                    reward=0.3,
                )
            )
            mem.append(
                make_goal_record(
                    goal_id="g2",
                    goal_type="growth",
                    duration_ticks=50,
                    completed=True,
                    success_rate=0.3,
                    identity_alignment=0.4,
                    reward=0.1,
                )
            )
        h_scorer = HierarchyScorer(
            hierarchy=h,
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )

        meta_scores = h_scorer.collect_meta_scores(goal_type="revenue")
        assert len(meta_scores) > 0

        t_scorer = TradeoffScorer(enabled=True)
        influence = t_scorer.compute_factor(
            meta_goal_scores=meta_scores,
            candidate_id="o1",
        )
        assert 0.85 <= influence.factor <= 1.15

        ev_with = SequenceEvaluator(hierarchy_scorer=h_scorer, tradeoff_scorer=t_scorer)
        objs = [self._make_objective("o1", goal_type="revenue")]
        result = ev_with.score_sequence(objs, label="test")
        assert result.total_score > 0

    def test_no_effect_when_disabled(self) -> None:
        from umh.runtime.meta_planner import SequenceEvaluator
        from umh.runtime.tradeoff import TradeoffScorer

        scorer = TradeoffScorer(enabled=False)
        ev_with = SequenceEvaluator(tradeoff_scorer=scorer)
        ev_without = SequenceEvaluator()

        objs = [self._make_objective("o1")]
        s1 = ev_with.score_sequence(objs, label="with")
        s2 = ev_without.score_sequence(objs, label="without")
        assert abs(s1.total_score - s2.total_score) < 0.0001

    def test_reason_includes_tradeoff(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="biz", weight=2.0),
                TradeoffDimension(name="personal", weight=1.0),
            )
        )
        engine = TradeoffEngine(profile=profile)
        result = engine.resolve(
            {
                "opt_a": {"biz": 0.9, "personal": 0.2},
                "opt_b": {"biz": 0.2, "personal": 0.9},
            }
        )
        assert result is not None
        assert result.best.candidate_id in result.reason
        assert "top contributions" in result.reason

    def test_planner_tradeoff_wiring(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import ReinforcementScorer
        from umh.runtime.meta_planner import MetaPlanner, SequenceEvaluator
        from umh.runtime.tradeoff import TradeoffScorer

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue",)))
        mem = GoalMemory()
        for _ in range(5):
            mem.append(
                make_goal_record(
                    goal_id="g1",
                    goal_type="revenue",
                    duration_ticks=100,
                    completed=True,
                    success_rate=0.5,
                    identity_alignment=0.5,
                    reward=0.3,
                )
            )
        h_scorer = HierarchyScorer(
            hierarchy=h,
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        t_scorer = TradeoffScorer(enabled=True)
        ev = SequenceEvaluator(hierarchy_scorer=h_scorer, tradeoff_scorer=t_scorer)
        planner = MetaPlanner(
            sequence_evaluator=ev,
            hierarchy_scorer=h_scorer,
            tradeoff_scorer=t_scorer,
        )
        assert planner.tradeoff_scorer is t_scorer
        assert planner.sequence_evaluator.tradeoff_scorer is t_scorer
        objs = [
            self._make_objective("o1", priority=8, goal_type="revenue"),
            self._make_objective("o2", priority=6, goal_type="revenue"),
            self._make_objective("o3", priority=4, goal_type="revenue"),
        ]
        result = planner.plan(objs)
        assert result is not None
        assert result.selected.total_score > 0


# ---------------------------------------------------------------------------
# Section 14: End-to-end pipeline
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def _make_objective(self, oid: str, priority: int = 5, goal_type: str = ""):
        from umh.runtime.arbitration import Objective

        metadata = {}
        if goal_type:
            metadata["goal_type"] = goal_type
        return Objective(
            objective_id=oid,
            description=f"Obj {oid}",
            priority=priority,
            effort_estimate=1.0,
            expected_value=1.0,
            metadata=metadata,
        )

    def test_e2e_full_chain(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import GoalBiasScorer, ReinforcementScorer
        from umh.runtime.identity import IdentityScorer, IdentityStore
        from umh.runtime.meta_planner import SequenceEvaluator
        from umh.runtime.tradeoff import TradeoffScorer

        id_store = IdentityStore()
        id_scorer = IdentityScorer(identity_store=id_store, enabled=False)

        mem = GoalMemory()
        for _ in range(5):
            mem.append(
                make_goal_record(
                    goal_id="g1",
                    goal_type="revenue",
                    duration_ticks=100,
                    completed=True,
                    success_rate=0.7,
                    identity_alignment=0.8,
                    reward=0.5,
                )
            )
        reinf_scorer = ReinforcementScorer(max_duration=100)
        goal_scorer = GoalBiasScorer(
            goal_memory=mem,
            reinforcement_scorer=reinf_scorer,
            enabled=False,
        )

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue",)))
        h_scorer = HierarchyScorer(
            hierarchy=h,
            goal_memory=mem,
            reinforcement_scorer=reinf_scorer,
            enabled=True,
        )
        t_scorer = TradeoffScorer(enabled=True)

        ev = SequenceEvaluator(
            identity_scorer=id_scorer,
            goal_bias_scorer=goal_scorer,
            hierarchy_scorer=h_scorer,
            tradeoff_scorer=t_scorer,
        )
        objs = [self._make_objective("o1", priority=7, goal_type="revenue")]
        result = ev.score_sequence(objs, label="test")
        assert result.total_score > 0

    def test_e2e_conflicting_meta_goals_resolved(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="biz", direction="maximize", weight=2.0),
                TradeoffDimension(name="personal", direction="maximize", weight=1.0),
            )
        )
        engine = TradeoffEngine(profile=profile)
        result = engine.resolve(
            {
                "option_a": {"biz": 0.9, "personal": 0.2},
                "option_b": {"biz": 0.3, "personal": 0.9},
                "option_c": {"biz": 0.6, "personal": 0.6},
            }
        )
        assert result is not None
        assert result.best.candidate_id == "option_a"
        assert len(result.pareto_frontier) >= 2

    def test_e2e_unrelated_type_neutral(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import ReinforcementScorer
        from umh.runtime.meta_planner import SequenceEvaluator
        from umh.runtime.tradeoff import TradeoffScorer

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue",)))
        mem = GoalMemory()
        mem.append(
            make_goal_record(
                goal_id="g1",
                goal_type="revenue",
                duration_ticks=100,
                completed=True,
                success_rate=1.0,
                identity_alignment=1.0,
                reward=1.0,
            )
        )
        h_scorer = HierarchyScorer(
            hierarchy=h,
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        t_scorer = TradeoffScorer(enabled=True)
        ev = SequenceEvaluator(hierarchy_scorer=h_scorer, tradeoff_scorer=t_scorer)

        objs = [self._make_objective("o1", goal_type="health")]
        result = ev.score_sequence(objs, label="test")
        ev_none = SequenceEvaluator()
        result_none = ev_none.score_sequence(objs, label="test")
        assert abs(result.total_score - result_none.total_score) < 0.001


# ---------------------------------------------------------------------------
# Section 15: Stability / Determinism
# ---------------------------------------------------------------------------


class TestStability:
    def test_repeated_resolve_identical(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="a"),
                TradeoffDimension(name="b"),
            )
        )
        engine = TradeoffEngine(profile=profile)
        cands = {"c1": {"a": 0.7, "b": 0.3}, "c2": {"a": 0.4, "b": 0.8}}
        results = [engine.resolve(cands) for _ in range(10)]
        for r in results:
            assert r is not None
            assert r.best.candidate_id == results[0].best.candidate_id
            assert r.best.weighted_score == results[0].best.weighted_score

    def test_tie_break_by_id(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="a"),))
        engine = TradeoffEngine(profile=profile)
        result = engine.resolve(
            {
                "beta": {"a": 0.5},
                "alpha": {"a": 0.5},
            }
        )
        assert result is not None
        assert result.best.candidate_id == "alpha"

    def test_scorer_deterministic(self) -> None:
        from umh.runtime.tradeoff import TradeoffScorer

        scorer = TradeoffScorer(enabled=True)
        scores = {"biz": 0.7, "ops": 0.5}
        results = [
            scorer.compute_factor(meta_goal_scores=scores, candidate_id="c1") for _ in range(10)
        ]
        for r in results:
            assert r.factor == results[0].factor

    def test_order_independence(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="a"),
                TradeoffDimension(name="b"),
            )
        )
        engine = TradeoffEngine(profile=profile)
        r1 = engine.resolve({"c1": {"a": 0.9, "b": 0.1}, "c2": {"a": 0.1, "b": 0.9}})
        r2 = engine.resolve({"c2": {"a": 0.1, "b": 0.9}, "c1": {"a": 0.9, "b": 0.1}})
        assert r1 is not None and r2 is not None
        assert r1.best.candidate_id == r2.best.candidate_id


# ---------------------------------------------------------------------------
# Section 16: Hard Invariants 121-125
# ---------------------------------------------------------------------------


class TestHardInvariants:
    def test_inv121_resolve_pure(self) -> None:
        """INV 121: TradeoffEngine.resolve does not mutate state."""
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="a"),))
        engine = TradeoffEngine(profile=profile)
        state_before = engine.profile.to_dict()

        for _ in range(10):
            engine.resolve({"c1": {"a": 0.5}, "c2": {"a": 0.8}})

        assert engine.profile.to_dict() == state_before

    def test_inv121_scorer_pure(self) -> None:
        """INV 121: TradeoffScorer.compute_factor does not mutate state."""
        from umh.runtime.tradeoff import TradeoffScorer

        scorer = TradeoffScorer(enabled=True)
        for _ in range(10):
            scorer.compute_factor(meta_goal_scores={"a": 0.5}, candidate_id="c1")
        assert scorer.enabled is True

    def test_inv122_no_randomness(self) -> None:
        """INV 122: No stochastic decision making."""
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="a"),
                TradeoffDimension(name="b"),
            )
        )
        engine = TradeoffEngine(profile=profile)
        cands = {"c1": {"a": 0.6, "b": 0.4}, "c2": {"a": 0.4, "b": 0.6}}
        results = [engine.resolve(cands) for _ in range(50)]
        winners = {r.best.candidate_id for r in results if r is not None}
        assert len(winners) == 1

    def test_inv123_deterministic_tie_break(self) -> None:
        """INV 123: Deterministic tie-breaking required."""
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="a"),))
        engine = TradeoffEngine(profile=profile)
        result = engine.resolve(
            {
                "z_candidate": {"a": 0.5},
                "a_candidate": {"a": 0.5},
                "m_candidate": {"a": 0.5},
            }
        )
        assert result is not None
        assert result.best.candidate_id == "a_candidate"

    def test_inv124_no_base_override(self) -> None:
        """INV 124: No override of base score (only weighting)."""
        from umh.runtime.tradeoff import TradeoffScorer

        scorer = TradeoffScorer(enabled=True)
        result = scorer.compute_factor(
            meta_goal_scores={"a": 0.0},
            candidate_id="c1",
        )
        assert result.factor >= 0.85
        assert result.factor <= 1.15

    def test_inv124_extreme_values_bounded(self) -> None:
        """INV 124: Even extreme inputs stay within factor bounds."""
        from umh.runtime.tradeoff import TradeoffScorer

        scorer = TradeoffScorer(enabled=True)
        for val in [0.0, 0.1, 0.5, 1.0, 2.0, 10.0]:
            result = scorer.compute_factor(
                meta_goal_scores={"a": val},
                candidate_id="c1",
            )
            assert 0.85 <= result.factor <= 1.15

    def test_inv125_explainable(self) -> None:
        """INV 125: Tradeoff layer must be explainable."""
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="a"),
                TradeoffDimension(name="b"),
            )
        )
        engine = TradeoffEngine(profile=profile)
        result = engine.resolve({"c1": {"a": 0.8, "b": 0.3}, "c2": {"a": 0.2, "b": 0.9}})
        assert result is not None
        assert len(result.reason) > 0
        assert result.best.candidate_id in result.reason

    def test_inv125_scorer_reason(self) -> None:
        """INV 125: Scorer provides explanation."""
        from umh.runtime.tradeoff import TradeoffScorer

        scorer = TradeoffScorer(enabled=True)
        result = scorer.compute_factor(
            meta_goal_scores={"biz": 0.8},
            candidate_id="c1",
        )
        assert len(result.reason) > 0

    def test_inv115_no_execution_imports(self) -> None:
        """No imports from umh/cells, umh/environments, umh/adapters."""
        with open("/opt/OS/umh/runtime/tradeoff.py") as f:
            tree = ast.parse(f.read())

        forbidden = ["umh.cells", "umh.environments", "umh.adapters"]
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                for fb in forbidden:
                    assert not node.module.startswith(fb), f"Forbidden import: {node.module}"


# ---------------------------------------------------------------------------
# Section 17: Explainability
# ---------------------------------------------------------------------------


class TestExplainability:
    def test_result_has_reason(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="a"),))
        engine = TradeoffEngine(profile=profile)
        result = engine.resolve({"c1": {"a": 0.8}})
        assert result is not None
        assert len(result.reason) > 0

    def test_result_has_contributions(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="a"),
                TradeoffDimension(name="b"),
            )
        )
        engine = TradeoffEngine(profile=profile)
        result = engine.resolve({"c1": {"a": 0.8, "b": 0.3}})
        assert result is not None
        assert "a" in result.best.dimension_contributions

    def test_result_has_pareto_info(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="a"),
                TradeoffDimension(name="b"),
            )
        )
        engine = TradeoffEngine(profile=profile)
        result = engine.resolve(
            {
                "c1": {"a": 0.9, "b": 0.9},
                "c2": {"a": 0.1, "b": 0.1},
            }
        )
        assert result is not None
        assert len(result.pareto_frontier) > 0

    def test_influence_has_full_to_dict(self) -> None:
        from umh.runtime.tradeoff import TradeoffScorer

        scorer = TradeoffScorer(enabled=True)
        result = scorer.compute_factor(
            meta_goal_scores={"biz": 0.7},
            candidate_id="c1",
        )
        d = result.to_dict()
        assert "factor" in d
        assert "reason" in d


# ---------------------------------------------------------------------------
# Section 18: Boundary / Exports / Compile
# ---------------------------------------------------------------------------


class TestBoundaryExports:
    def test_import_tradeoff(self) -> None:
        from umh.runtime.tradeoff import (
            CandidateScore,
            TradeoffDimension,
            TradeoffEngine,
            TradeoffInfluence,
            TradeoffProfile,
            TradeoffResult,
            TradeoffScorer,
        )

        assert TradeoffDimension is not None
        assert TradeoffProfile is not None
        assert TradeoffEngine is not None
        assert TradeoffScorer is not None
        assert CandidateScore is not None
        assert TradeoffResult is not None
        assert TradeoffInfluence is not None

    def test_compile_tradeoff(self) -> None:
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/tradeoff.py", doraise=True)

    def test_compile_meta_planner(self) -> None:
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/meta_planner.py", doraise=True)

    def test_compile_goal_hierarchy(self) -> None:
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/goal_hierarchy.py", doraise=True)

    def test_compile_init(self) -> None:
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/__init__.py", doraise=True)

    def test_runtime_exports_tradeoff(self) -> None:
        from umh.runtime import (
            CandidateScore,
            TradeoffDimension,
            TradeoffEngine,
            TradeoffInfluence,
            TradeoffProfile,
            TradeoffResult,
            TradeoffScorer,
        )

        assert TradeoffEngine is not None
        assert TradeoffScorer is not None

    def test_all_exports_present(self) -> None:
        import umh.runtime as rt

        expected = [
            "CandidateScore",
            "TradeoffDimension",
            "TradeoffEngine",
            "TradeoffInfluence",
            "TradeoffProfile",
            "TradeoffResult",
            "TradeoffScorer",
        ]
        for name in expected:
            assert name in rt.__all__, f"{name} not in __all__"

    def test_tradeoff_dimension_to_dict_round_trip(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension

        d = TradeoffDimension(name="x", direction="minimize", weight=2.5, tolerance=0.3)
        dd = d.to_dict()
        assert dd["name"] == "x"
        assert dd["direction"] == "minimize"

    def test_tradeoff_profile_to_dict(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile

        p = TradeoffProfile(
            dimensions=(TradeoffDimension(name="a"),),
            name="test",
        )
        d = p.to_dict()
        assert d["name"] == "test"
        assert d["dimension_count"] == 1

    def test_tradeoff_result_to_dict(self) -> None:
        from umh.runtime.tradeoff import CandidateScore, TradeoffProfile, TradeoffResult

        best = CandidateScore("c1", {"a": 0.8}, {"a": 1.0}, 0.8, {"a": 0.8})
        r = TradeoffResult(best, (best,), ("c1",), (), TradeoffProfile(dimensions=()), "reason")
        d = r.to_dict()
        assert d["best_candidate"] == "c1"
        assert d["best_score"] == 0.8


# ---------------------------------------------------------------------------
# Section 19: Additional coverage
# ---------------------------------------------------------------------------


class TestAdditionalCoverage:
    def test_normalize_midpoint(self) -> None:
        from umh.runtime.tradeoff import normalize_value

        result = normalize_value(50.0, 0.0, 100.0, "maximize")
        assert abs(result - 0.5) < 0.001

    def test_normalize_minimize_midpoint(self) -> None:
        from umh.runtime.tradeoff import normalize_value

        result = normalize_value(50.0, 0.0, 100.0, "minimize")
        assert abs(result - 0.5) < 0.001

    def test_normalize_negative_range(self) -> None:
        from umh.runtime.tradeoff import normalize_value

        result = normalize_value(-5.0, -10.0, 0.0, "maximize")
        assert abs(result - 0.5) < 0.001

    def test_pareto_three_way_frontier(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, pareto_filter

        dims = (
            TradeoffDimension(name="a"),
            TradeoffDimension(name="b"),
            TradeoffDimension(name="c"),
        )
        candidates = {
            "c1": {"a": 1.0, "b": 0.0, "c": 0.0},
            "c2": {"a": 0.0, "b": 1.0, "c": 0.0},
            "c3": {"a": 0.0, "b": 0.0, "c": 1.0},
        }
        frontier, dominated = pareto_filter(candidates, dims)
        assert frontier == ["c1", "c2", "c3"]
        assert dominated == []

    def test_engine_many_candidates(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="score"),))
        engine = TradeoffEngine(profile=profile)
        cands = {f"c{i}": {"score": i / 10.0} for i in range(10)}
        result = engine.resolve(cands)
        assert result is not None
        assert result.best.candidate_id == "c9"

    def test_engine_single_dimension_ranking(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="quality"),))
        engine = TradeoffEngine(profile=profile)
        result = engine.resolve(
            {
                "high": {"quality": 0.9},
                "mid": {"quality": 0.5},
                "low": {"quality": 0.1},
            }
        )
        assert result is not None
        assert result.ranked[0].candidate_id == "high"
        assert result.ranked[1].candidate_id == "mid"
        assert result.ranked[2].candidate_id == "low"

    def test_engine_mixed_directions(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="quality", direction="maximize"),
                TradeoffDimension(name="cost", direction="minimize"),
            )
        )
        engine = TradeoffEngine(profile=profile)
        result = engine.resolve(
            {
                "cheap_good": {"quality": 0.8, "cost": 10.0},
                "expensive_bad": {"quality": 0.2, "cost": 100.0},
            }
        )
        assert result is not None
        assert result.best.candidate_id == "cheap_good"

    def test_scorer_factor_formula(self) -> None:
        from umh.runtime.tradeoff import TradeoffScorer

        scorer = TradeoffScorer(enabled=True)
        result = scorer.compute_factor(
            meta_goal_scores={"a": 0.8},
            candidate_id="c1",
        )
        assert result.factor == 1.0

    def test_scorer_with_none_scores(self) -> None:
        from umh.runtime.tradeoff import TradeoffScorer

        scorer = TradeoffScorer(enabled=True)
        result = scorer.compute_factor(meta_goal_scores=None, candidate_id="c1")
        assert result.factor == 1.0
        assert "no meta-goal scores" in result.reason

    def test_profile_dimension_access(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile

        dims = (
            TradeoffDimension(name="a", weight=1.0),
            TradeoffDimension(name="b", weight=2.0),
            TradeoffDimension(name="c", weight=3.0),
        )
        p = TradeoffProfile(dimensions=dims, name="test")
        assert p.dimension_count == 3
        assert p.dimension_names == ["a", "b", "c"]
        assert p.total_weight() == 6.0

    def test_candidate_score_empty_values(self) -> None:
        from umh.runtime.tradeoff import CandidateScore

        cs = CandidateScore("empty", {}, {}, 0.0, {})
        d = cs.to_dict()
        assert d["weighted_score"] == 0.0
        assert d["raw_values"] == {}

    def test_result_dominated_list(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="a"),
                TradeoffDimension(name="b"),
            )
        )
        engine = TradeoffEngine(profile=profile)
        result = engine.resolve(
            {
                "winner": {"a": 1.0, "b": 1.0},
                "loser1": {"a": 0.1, "b": 0.1},
                "loser2": {"a": 0.2, "b": 0.2},
            }
        )
        assert result is not None
        assert "loser1" in result.dominated
        assert "loser2" in result.dominated

    def test_influence_factor_rounding(self) -> None:
        from umh.runtime.tradeoff import TradeoffInfluence

        ti = TradeoffInfluence(factor=1.12345, tradeoff_result=None, reason="test")
        d = ti.to_dict()
        assert d["factor"] == 1.1235

    def test_engine_properties(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="x"),))
        engine = TradeoffEngine(profile=profile, enable_pareto=False)
        assert engine.profile is profile
        assert engine.pareto_enabled is False

    def test_dimension_post_init_clamp_negative_tolerance(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension

        d = TradeoffDimension(name="x", tolerance=-0.5)
        assert d.tolerance == 0.0

    def test_weighted_score_three_dimensions(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, compute_weighted_score

        dims = (
            TradeoffDimension(name="a", weight=1.0),
            TradeoffDimension(name="b", weight=1.0),
            TradeoffDimension(name="c", weight=1.0),
        )
        score, contribs = compute_weighted_score({"a": 0.9, "b": 0.6, "c": 0.3}, dims)
        assert abs(score - 0.6) < 0.001

    def test_pareto_all_equal(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, pareto_filter

        dims = (TradeoffDimension(name="a"), TradeoffDimension(name="b"))
        candidates = {
            "c1": {"a": 0.5, "b": 0.5},
            "c2": {"a": 0.5, "b": 0.5},
            "c3": {"a": 0.5, "b": 0.5},
        }
        frontier, dominated = pareto_filter(candidates, dims)
        assert frontier == ["c1", "c2", "c3"]
        assert dominated == []

    def test_resolve_returns_none_for_empty(self) -> None:
        from umh.runtime.tradeoff import TradeoffEngine

        engine = TradeoffEngine()
        assert engine.resolve({}) is None
