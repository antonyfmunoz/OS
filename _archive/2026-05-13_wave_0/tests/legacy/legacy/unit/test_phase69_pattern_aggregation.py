"""Phase 69 — Multi-Pattern Aggregation Layer v1 tests.

Tests weighted blending of multiple pattern influences: normalization,
dominance capping, gating, safety, determinism, explainability, and
orchestrator integration. Covers invariants 334-343.
"""

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime.pattern_aggregation import (
    PatternAggregationResult,
    PatternContribution,
    _DOMINANCE_CAP,
    _FACTOR_CEILING,
    _FACTOR_FLOOR,
    _MAX_PATTERNS,
    _apply_dominance_cap,
    _compute_individual_factor,
    compute_pattern_aggregation,
)
from umh.runtime.pattern_influence import (
    PatternInfluenceConfig,
    compute_pattern_influence,
)
from umh.runtime.pattern_matching import (
    PatternMatch,
    PatternResult,
)
from umh.runtime.pattern_memory import (
    PatternKey,
    PatternMemory,
    PatternRecord,
    PatternStats,
    RiskLevel,
    StabilityLevel,
    TrendDirection,
    UrgencyLevel,
)
from umh.runtime.strategy_orchestrator import (
    StrategyCandidate,
    StrategySelectionResult,
    orchestrate_selection,
)


# ── Helpers ──────────────────────────────────────────────────────


def _key(
    trend: TrendDirection = TrendDirection.UP,
    risk: RiskLevel = RiskLevel.LOW,
    stability: StabilityLevel = StabilityLevel.HIGH,
    urgency: UrgencyLevel = UrgencyLevel.LOW,
) -> PatternKey:
    return PatternKey(
        trend_direction=trend,
        risk_level=risk,
        stability_level=stability,
        urgency_level=urgency,
    )


def _stats(
    key: PatternKey | None = None,
    count: int = 20,
    avg_score: float = 0.8,
    success_rate: float = 0.75,
) -> PatternStats:
    return PatternStats(
        key=key or _key(),
        count=count,
        avg_score=avg_score,
        success_rate=success_rate,
    )


def _match(
    similarity: float = 1.0,
    sample_size: int = 20,
    stats: PatternStats | None = None,
    key: PatternKey | None = None,
) -> PatternMatch:
    k = key or _key()
    return PatternMatch(
        matched_key=k,
        similarity=similarity,
        stats=stats or _stats(key=k),
        sample_size=sample_size,
    )


def _multi_pattern_result(
    matches: list[PatternMatch] | None = None,
    confidence: float = 0.8,
) -> PatternResult:
    if matches is None:
        k1 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k2 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.MEDIUM, UrgencyLevel.LOW)
        k3 = _key(TrendDirection.UP, RiskLevel.MEDIUM, StabilityLevel.HIGH, UrgencyLevel.LOW)
        matches = [
            _match(similarity=1.0, key=k1, stats=_stats(key=k1, avg_score=0.85)),
            _match(similarity=0.75, key=k2, stats=_stats(key=k2, avg_score=0.80)),
            _match(similarity=0.75, key=k3, stats=_stats(key=k3, avg_score=0.70)),
        ]
    best = matches[0] if matches else _match()
    return PatternResult(
        matched=True,
        best_match=best,
        all_matches=tuple(matches),
        query_key=_key(),
        confidence=confidence,
        total_patterns_searched=len(matches),
        explanation="test multi-pattern",
    )


def _single_pattern_result(
    confidence: float = 0.8,
    avg_score: float = 0.85,
) -> PatternResult:
    m = _match(similarity=1.0, stats=_stats(avg_score=avg_score))
    return PatternResult(
        matched=True,
        best_match=m,
        all_matches=(m,),
        query_key=_key(),
        confidence=confidence,
        total_patterns_searched=1,
        explanation="test single",
    )


def _enabled_config(**overrides) -> PatternInfluenceConfig:
    defaults = {
        "enabled": True,
        "min_samples": 10,
        "min_confidence": 0.6,
        "max_adjustment": 0.10,
        "similarity_threshold": 0.75,
    }
    defaults.update(overrides)
    return PatternInfluenceConfig(**defaults)


# ── GATING TESTS ─────────────────────────────────────────────────


class TestGatingDisabled:
    def test_disabled_returns_neutral(self):
        cfg = PatternInfluenceConfig(enabled=False)
        r = compute_pattern_aggregation(
            pattern_result=_multi_pattern_result(),
            baseline_score=0.5,
            config=cfg,
        )
        assert r.final_factor == 1.0
        assert not r.applied

    def test_default_config_disabled(self):
        r = compute_pattern_aggregation(
            pattern_result=_multi_pattern_result(),
            baseline_score=0.5,
        )
        assert not r.applied

    def test_no_pattern_result(self):
        cfg = _enabled_config()
        r = compute_pattern_aggregation(pattern_result=None, config=cfg)
        assert not r.applied
        assert "no pattern result" in r.reason_if_not_applied

    def test_no_match(self):
        pr = PatternResult(matched=False)
        cfg = _enabled_config()
        r = compute_pattern_aggregation(pattern_result=pr, config=cfg)
        assert not r.applied

    def test_empty_matches(self):
        pr = PatternResult(matched=True, all_matches=())
        cfg = _enabled_config()
        r = compute_pattern_aggregation(pattern_result=pr, config=cfg)
        assert not r.applied


class TestGatingPerPattern:
    def test_low_samples_filtered(self):
        k = _key()
        m = _match(similarity=1.0, sample_size=3, key=k, stats=_stats(key=k))
        pr = _multi_pattern_result(matches=[m])
        cfg = _enabled_config(min_samples=10)
        r = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.5, config=cfg)
        assert not r.applied
        assert "no qualifying" in r.reason_if_not_applied

    def test_low_similarity_filtered(self):
        k = _key()
        m = _match(similarity=0.5, key=k, stats=_stats(key=k))
        pr = _multi_pattern_result(matches=[m])
        cfg = _enabled_config(similarity_threshold=0.75)
        r = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.5, config=cfg)
        assert not r.applied

    def test_no_stats_filtered(self):
        m = PatternMatch(matched_key=_key(), similarity=1.0, sample_size=20, stats=None)
        pr = _multi_pattern_result(matches=[m])
        cfg = _enabled_config()
        r = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.5, config=cfg)
        assert not r.applied

    def test_low_confidence_filtered(self):
        pr = _multi_pattern_result(confidence=0.3)
        cfg = _enabled_config(min_confidence=0.6)
        r = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.5, config=cfg)
        assert not r.applied
        assert "confidence" in r.reason_if_not_applied


# ── MATCHING TESTS ───────────────────────────────────────────────


class TestMultiplePatterns:
    def test_multiple_patterns_returned(self):
        pr = _multi_pattern_result()
        cfg = _enabled_config()
        r = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.5, config=cfg)
        assert r.applied
        assert r.patterns_used >= 2

    def test_sorted_by_similarity(self):
        pr = _multi_pattern_result()
        cfg = _enabled_config()
        r = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.5, config=cfg)
        sims = [c.similarity for c in r.contributions]
        assert sims == sorted(sims, reverse=True)

    def test_max_patterns_capped(self):
        keys = (
            [
                _key(t, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
                for t in [TrendDirection.UP, TrendDirection.DOWN, TrendDirection.NEUTRAL]
            ]
            + [
                _key(TrendDirection.UP, r, StabilityLevel.HIGH, UrgencyLevel.LOW)
                for r in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]
            ]
            + [
                _key(TrendDirection.UP, RiskLevel.LOW, s, UrgencyLevel.LOW)
                for s in [StabilityLevel.LOW, StabilityLevel.MEDIUM, StabilityLevel.HIGH]
            ]
        )
        unique_keys = list({k.to_tuple(): k for k in keys}.values())
        matches = [
            _match(similarity=0.75, key=k, stats=_stats(key=k, avg_score=0.8))
            for k in unique_keys[:8]
        ]
        pr = _multi_pattern_result(matches=matches)
        cfg = _enabled_config()
        r = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.5, config=cfg)
        assert r.patterns_used <= _MAX_PATTERNS

    def test_single_match_still_works(self):
        k = _key()
        m = _match(similarity=1.0, key=k, stats=_stats(key=k, avg_score=0.85))
        pr = _multi_pattern_result(matches=[m])
        cfg = _enabled_config()
        r = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.5, config=cfg)
        assert r.applied
        assert r.patterns_used == 1


# ── WEIGHTING TESTS ──────────────────────────────────────────────


class TestWeighting:
    def test_weights_normalize_to_one(self):
        pr = _multi_pattern_result()
        cfg = _enabled_config()
        r = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.5, config=cfg)
        total = sum(c.normalized_weight for c in r.contributions)
        assert abs(total - 1.0) < 1e-9

    def test_higher_similarity_gets_more_weight(self):
        pr = _multi_pattern_result()
        cfg = _enabled_config()
        r = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.5, config=cfg)
        if len(r.contributions) >= 2:
            assert r.contributions[0].normalized_weight >= r.contributions[1].normalized_weight

    def test_low_confidence_low_weight(self):
        k1 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k2 = _key(TrendDirection.DOWN, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        m1 = _match(similarity=1.0, key=k1, stats=_stats(key=k1, avg_score=0.9))
        m2 = _match(similarity=0.75, key=k2, stats=_stats(key=k2, avg_score=0.3))
        pr = _multi_pattern_result(matches=[m1, m2], confidence=0.7)
        cfg = _enabled_config()
        r = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.5, config=cfg)
        assert r.contributions[0].normalized_weight > r.contributions[1].normalized_weight

    def test_equal_similarity_equal_weight(self):
        k1 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k2 = _key(TrendDirection.DOWN, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        m1 = _match(similarity=0.75, key=k1, stats=_stats(key=k1, avg_score=0.8))
        m2 = _match(similarity=0.75, key=k2, stats=_stats(key=k2, avg_score=0.6))
        pr = _multi_pattern_result(matches=[m1, m2])
        cfg = _enabled_config()
        r = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.5, config=cfg)
        assert (
            abs(r.contributions[0].normalized_weight - r.contributions[1].normalized_weight) < 1e-9
        )


# ── AGGREGATION TESTS ────────────────────────────────────────────


class TestAggregation:
    def test_multiple_patterns_influence_result(self):
        pr = _multi_pattern_result()
        cfg = _enabled_config()
        r = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.5, config=cfg)
        assert r.applied
        assert r.final_factor != 1.0

    def test_result_bounded_high(self):
        k1 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k2 = _key(TrendDirection.DOWN, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        matches = [
            _match(similarity=1.0, key=k1, stats=_stats(key=k1, avg_score=1.0)),
            _match(similarity=0.75, key=k2, stats=_stats(key=k2, avg_score=1.0)),
        ]
        pr = _multi_pattern_result(matches=matches)
        cfg = _enabled_config(max_adjustment=0.20)
        r = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.0, config=cfg)
        assert r.final_factor <= _FACTOR_CEILING

    def test_result_bounded_low(self):
        k1 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k2 = _key(TrendDirection.DOWN, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        matches = [
            _match(similarity=1.0, key=k1, stats=_stats(key=k1, avg_score=0.0)),
            _match(similarity=0.75, key=k2, stats=_stats(key=k2, avg_score=0.0)),
        ]
        pr = _multi_pattern_result(matches=matches)
        cfg = _enabled_config(max_adjustment=0.20)
        r = compute_pattern_aggregation(pattern_result=pr, baseline_score=1.0, config=cfg)
        assert r.final_factor >= _FACTOR_FLOOR

    def test_contributions_sum_to_factor(self):
        pr = _multi_pattern_result()
        cfg = _enabled_config()
        r = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.5, config=cfg)
        contrib_sum = sum(c.contribution for c in r.contributions)
        assert abs(contrib_sum - r.final_factor) < 1e-6

    def test_neutral_patterns_produce_neutral(self):
        k1 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k2 = _key(TrendDirection.DOWN, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        matches = [
            _match(similarity=1.0, key=k1, stats=_stats(key=k1, avg_score=0.5)),
            _match(similarity=0.75, key=k2, stats=_stats(key=k2, avg_score=0.5)),
        ]
        pr = _multi_pattern_result(matches=matches)
        cfg = _enabled_config()
        r = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.5, config=cfg)
        assert abs(r.final_factor - 1.0) < 1e-6


# ── DOMINANCE TESTS ──────────────────────────────────────────────


class TestDominance:
    def test_no_dominance_below_cap(self):
        k1 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k2 = _key(TrendDirection.DOWN, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        m1 = _match(similarity=0.75, key=k1, stats=_stats(key=k1, avg_score=0.8))
        m2 = _match(similarity=0.75, key=k2, stats=_stats(key=k2, avg_score=0.6))
        pr = _multi_pattern_result(matches=[m1, m2])
        cfg = _enabled_config()
        r = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.5, config=cfg)
        assert not r.dominance_capped
        for c in r.contributions:
            assert c.normalized_weight <= _DOMINANCE_CAP + 1e-9

    def test_dominance_capped_when_high(self):
        k1 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k2 = _key(TrendDirection.DOWN, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        m1 = _match(similarity=1.0, key=k1, stats=_stats(key=k1, avg_score=0.8))
        m2 = _match(similarity=0.75, key=k2, stats=_stats(key=k2, avg_score=0.6))
        pr = _multi_pattern_result(matches=[m1, m2], confidence=0.9)
        cfg = _enabled_config()
        r = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.5, config=cfg)
        for c in r.contributions:
            assert c.normalized_weight <= _DOMINANCE_CAP + 1e-9

    def test_dominance_cap_constant(self):
        assert _DOMINANCE_CAP == 0.7

    def test_apply_dominance_cap_no_change(self):
        weights = [0.5, 0.3, 0.2]
        capped, was_capped = _apply_dominance_cap(weights)
        assert not was_capped

    def test_apply_dominance_cap_triggers(self):
        weights = [0.9, 0.05, 0.05]
        capped, was_capped = _apply_dominance_cap(weights)
        assert was_capped
        assert max(capped) <= _DOMINANCE_CAP + 1e-9
        assert abs(sum(capped) - 1.0) < 1e-9

    def test_apply_dominance_cap_empty(self):
        capped, was_capped = _apply_dominance_cap([])
        assert capped == []
        assert not was_capped


# ── SAFETY TESTS ─────────────────────────────────────────────────


class TestSafety:
    def test_cannot_flip_strong_winner(self):
        pr = _multi_pattern_result()
        cfg = _enabled_config()
        r1 = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.9, config=cfg)
        r2 = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.5, config=cfg)
        final_high = 0.9 * r1.final_factor
        final_low = 0.5 * r2.final_factor
        assert final_high > final_low

    def test_factor_always_in_bounds(self):
        for baseline in [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]:
            pr = _multi_pattern_result()
            cfg = _enabled_config()
            r = compute_pattern_aggregation(pattern_result=pr, baseline_score=baseline, config=cfg)
            assert _FACTOR_FLOOR <= r.final_factor <= _FACTOR_CEILING

    def test_max_patterns_limit(self):
        assert _MAX_PATTERNS == 5


# ── NEUTRAL TESTS ────────────────────────────────────────────────


class TestNeutral:
    def test_no_patterns_returns_one(self):
        cfg = _enabled_config()
        r = compute_pattern_aggregation(pattern_result=None, config=cfg)
        assert r.final_factor == 1.0

    def test_all_filtered_returns_neutral(self):
        k = _key()
        m = _match(similarity=0.5, key=k, stats=_stats(key=k))
        pr = _multi_pattern_result(matches=[m])
        cfg = _enabled_config(similarity_threshold=0.75)
        r = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.5, config=cfg)
        assert r.final_factor == 1.0
        assert not r.applied


# ── DETERMINISM TESTS ────────────────────────────────────────────


class TestDeterminism:
    def test_repeat_runs_identical(self):
        pr = _multi_pattern_result()
        cfg = _enabled_config()
        results = []
        for _ in range(50):
            r = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.5, config=cfg)
            results.append(r.final_factor)
        assert len(set(results)) == 1

    def test_ordering_deterministic(self):
        pr = _multi_pattern_result()
        cfg = _enabled_config()
        r1 = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.5, config=cfg)
        r2 = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.5, config=cfg)
        keys1 = [c.key for c in r1.contributions]
        keys2 = [c.key for c in r2.contributions]
        assert keys1 == keys2


# ── EXPLAINABILITY TESTS ────────────────────────────────────────


class TestExplainability:
    def test_contributions_have_all_fields(self):
        pr = _multi_pattern_result()
        cfg = _enabled_config()
        r = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.5, config=cfg)
        for c in r.contributions:
            assert c.key != ""
            assert c.similarity > 0
            assert c.confidence > 0
            assert c.normalized_weight > 0
            assert c.individual_factor > 0

    def test_contributions_to_dict(self):
        pr = _multi_pattern_result()
        cfg = _enabled_config()
        r = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.5, config=cfg)
        d = r.to_dict()
        assert "contributions" in d
        assert len(d["contributions"]) == r.patterns_used

    def test_result_to_dict_all_keys(self):
        r = PatternAggregationResult()
        d = r.to_dict()
        expected_keys = {
            "final_factor",
            "applied",
            "contributions",
            "patterns_used",
            "dominance_capped",
            "temporal_applied",
            "reason_if_not_applied",
        }
        assert set(d.keys()) == expected_keys

    def test_contribution_to_dict_keys(self):
        c = PatternContribution(key="test", similarity=0.8, confidence=0.9)
        d = c.to_dict()
        expected = {
            "key",
            "similarity",
            "confidence",
            "raw_weight",
            "normalized_weight",
            "individual_factor",
            "contribution",
            "age",
            "decay_factor",
            "pre_decay_weight",
        }
        assert set(d.keys()) == expected

    def test_gated_result_has_reason(self):
        cfg = _enabled_config(min_confidence=0.99)
        pr = _multi_pattern_result(confidence=0.5)
        r = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.5, config=cfg)
        assert not r.applied
        assert r.reason_if_not_applied != ""


# ── INDIVIDUAL FACTOR TESTS ──────────────────────────────────────


class TestIndividualFactor:
    def test_positive_signal(self):
        f = _compute_individual_factor(0.8, 0.5, 0.1)
        assert f == 1.1

    def test_negative_signal(self):
        f = _compute_individual_factor(0.4, 0.5, 0.1)
        assert f == 0.9

    def test_neutral_signal(self):
        f = _compute_individual_factor(0.5, 0.5, 0.1)
        assert f == 1.0

    def test_clamped_high(self):
        f = _compute_individual_factor(1.0, 0.0, 0.05)
        assert f == 1.05

    def test_clamped_low(self):
        f = _compute_individual_factor(0.0, 1.0, 0.05)
        assert f == 0.95

    def test_hard_ceiling(self):
        f = _compute_individual_factor(1.0, 0.0, 0.20)
        assert f <= _FACTOR_CEILING

    def test_hard_floor(self):
        f = _compute_individual_factor(0.0, 1.0, 0.20)
        assert f >= _FACTOR_FLOOR


# ── ISOLATION TESTS ──────────────────────────────────────────────


class TestIsolation:
    def test_no_mutation_of_pattern_memory(self):
        mem = PatternMemory()
        k1 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k2 = _key(TrendDirection.DOWN, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        for i in range(15):
            mem.append(PatternRecord(key=k1, outcome_score=0.85, confidence=0.9, timestamp=i))
            mem.append(PatternRecord(key=k2, outcome_score=0.70, confidence=0.8, timestamp=i + 100))
        size_before = mem.size
        from umh.runtime.pattern_matching import match_pattern

        pr = match_pattern(query_key=k1, memory=mem, min_similarity=0.5, min_samples=5)
        cfg = _enabled_config()
        compute_pattern_aggregation(pattern_result=pr, baseline_score=0.5, config=cfg)
        assert mem.size == size_before

    def test_no_mutation_of_pattern_result(self):
        pr = _multi_pattern_result()
        original_confidence = pr.confidence
        original_count = len(pr.all_matches)
        cfg = _enabled_config()
        compute_pattern_aggregation(pattern_result=pr, baseline_score=0.5, config=cfg)
        assert pr.confidence == original_confidence
        assert len(pr.all_matches) == original_count


# ── STRATEGY CANDIDATE TESTS ────────────────────────────────────


class TestStrategyCandidateCompat:
    def test_pattern_factor_from_aggregation(self):
        c = StrategyCandidate(
            strategy_id="A",
            base_score=1.0,
            pattern_factor=1.05,
        )
        assert abs(c.final_score - 1.05) < 1e-6

    def test_pattern_factor_default_neutral(self):
        c = StrategyCandidate(strategy_id="A", base_score=1.0)
        assert c.pattern_factor == 1.0


# ── ORCHESTRATOR INTEGRATION TESTS ──────────────────────────────


class TestOrchestratorMultiPattern:
    def test_multi_pattern_uses_aggregation(self):
        pr = _multi_pattern_result()
        cfg = _enabled_config()
        r = orchestrate_selection(
            strategy_ids=["A", "B"],
            base_scores=[0.8, 0.7],
            pattern_result=pr,
            pattern_influence_config=cfg,
        )
        assert r.used_pattern
        assert r.pattern_aggregation_result is not None
        assert r.pattern_aggregation_result.applied

    def test_single_pattern_uses_single_influence(self):
        pr = _single_pattern_result()
        cfg = _enabled_config()
        r = orchestrate_selection(
            strategy_ids=["A", "B"],
            base_scores=[0.8, 0.7],
            pattern_result=pr,
            pattern_influence_config=cfg,
        )
        assert r.used_pattern
        assert r.pattern_influence_result is not None
        assert r.pattern_aggregation_result is None

    def test_disabled_no_effect(self):
        pr = _multi_pattern_result()
        cfg = PatternInfluenceConfig(enabled=False)
        r = orchestrate_selection(
            strategy_ids=["A", "B"],
            base_scores=[0.8, 0.7],
            pattern_result=pr,
            pattern_influence_config=cfg,
        )
        assert not r.used_pattern
        for c in r.candidates:
            assert c.pattern_factor == 1.0

    def test_aggregation_result_in_to_dict(self):
        pr = _multi_pattern_result()
        cfg = _enabled_config()
        r = orchestrate_selection(
            strategy_ids=["A", "B"],
            base_scores=[0.8, 0.7],
            pattern_result=pr,
            pattern_influence_config=cfg,
        )
        d = r.to_dict()
        assert "pattern_aggregation_result" in d

    def test_pattern_in_explanation(self):
        pr = _multi_pattern_result()
        cfg = _enabled_config()
        r = orchestrate_selection(
            strategy_ids=["A", "B"],
            base_scores=[0.8, 0.7],
            pattern_result=pr,
            pattern_influence_config=cfg,
        )
        assert "pattern" in r.explanation.lower()

    def test_aggregation_does_not_break_regime(self):
        pr = _multi_pattern_result()
        cfg = _enabled_config()
        r = orchestrate_selection(
            strategy_ids=["A", "B"],
            base_scores=[0.8, 0.7],
            regime_factors=[1.1, 0.9],
            pattern_result=pr,
            pattern_influence_config=cfg,
        )
        assert r.used_regime
        assert r.base_winner == "A"

    def test_all_six_factors_compose(self):
        pr = _multi_pattern_result()
        cfg = _enabled_config()
        r = orchestrate_selection(
            strategy_ids=["A"],
            base_scores=[0.8],
            regime_factors=[1.05],
            pattern_result=pr,
            pattern_influence_config=cfg,
        )
        c = r.candidates[0]
        expected = (
            c.base_score
            * c.regime_factor
            * c.feedback_factor
            * c.weight_factor
            * c.interaction_factor
            * c.pattern_factor
        )
        assert abs(c.final_score - expected) < 1e-9

    def test_no_config_no_aggregation(self):
        r = orchestrate_selection(
            strategy_ids=["A", "B"],
            base_scores=[0.8, 0.7],
        )
        assert not r.used_pattern
        assert r.pattern_aggregation_result is None


# ── EDGE CASE TESTS ─────────────────────────────────────────────


class TestEdgeCases:
    def test_all_patterns_same_similarity(self):
        k1 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k2 = _key(TrendDirection.DOWN, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k3 = _key(TrendDirection.NEUTRAL, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        matches = [
            _match(similarity=0.75, key=k1, stats=_stats(key=k1, avg_score=0.8)),
            _match(similarity=0.75, key=k2, stats=_stats(key=k2, avg_score=0.7)),
            _match(similarity=0.75, key=k3, stats=_stats(key=k3, avg_score=0.6)),
        ]
        pr = _multi_pattern_result(matches=matches)
        cfg = _enabled_config()
        r = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.5, config=cfg)
        assert r.applied
        weights = [c.normalized_weight for c in r.contributions]
        for w in weights:
            assert abs(w - weights[0]) < 1e-9

    def test_zero_baseline(self):
        pr = _multi_pattern_result()
        cfg = _enabled_config()
        r = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.0, config=cfg)
        assert r.applied
        assert r.final_factor <= _FACTOR_CEILING

    def test_high_baseline(self):
        k1 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k2 = _key(TrendDirection.DOWN, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        matches = [
            _match(similarity=1.0, key=k1, stats=_stats(key=k1, avg_score=0.3)),
            _match(similarity=0.75, key=k2, stats=_stats(key=k2, avg_score=0.2)),
        ]
        pr = _multi_pattern_result(matches=matches)
        cfg = _enabled_config()
        r = compute_pattern_aggregation(pattern_result=pr, baseline_score=1.0, config=cfg)
        assert r.final_factor >= _FACTOR_FLOOR

    def test_mixed_direction_patterns(self):
        k1 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k2 = _key(TrendDirection.DOWN, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        matches = [
            _match(similarity=1.0, key=k1, stats=_stats(key=k1, avg_score=0.9)),
            _match(similarity=0.75, key=k2, stats=_stats(key=k2, avg_score=0.3)),
        ]
        pr = _multi_pattern_result(matches=matches)
        cfg = _enabled_config()
        r = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.6, config=cfg)
        assert r.applied
        assert _FACTOR_FLOOR <= r.final_factor <= _FACTOR_CEILING


# ── FULL E2E WITH REAL MEMORY ────────────────────────────────────


class TestEndToEnd:
    def test_e2e_multi_pattern_from_memory(self):
        mem = PatternMemory()
        k1 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k2 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.MEDIUM, UrgencyLevel.LOW)
        for i in range(20):
            mem.append(PatternRecord(key=k1, outcome_score=0.85, confidence=0.9, timestamp=i))
            mem.append(PatternRecord(key=k2, outcome_score=0.75, confidence=0.8, timestamp=i + 100))

        from umh.runtime.pattern_matching import match_pattern

        pr = match_pattern(query_key=k1, memory=mem, min_similarity=0.5, min_samples=5)
        assert pr.matched
        assert len(pr.all_matches) >= 2

        cfg = _enabled_config()
        r = compute_pattern_aggregation(pattern_result=pr, baseline_score=0.7, config=cfg)
        assert r.applied
        assert r.patterns_used >= 2
        assert _FACTOR_FLOOR <= r.final_factor <= _FACTOR_CEILING

    def test_e2e_orchestrator_multi_pattern(self):
        mem = PatternMemory()
        k1 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k2 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.MEDIUM, UrgencyLevel.LOW)
        for i in range(25):
            mem.append(PatternRecord(key=k1, outcome_score=0.85, confidence=0.9, timestamp=i))
            mem.append(PatternRecord(key=k2, outcome_score=0.75, confidence=0.8, timestamp=i + 100))

        from umh.runtime.pattern_matching import match_pattern

        pr = match_pattern(query_key=k1, memory=mem, min_similarity=0.5, min_samples=5)
        cfg = _enabled_config()
        r = orchestrate_selection(
            strategy_ids=["X", "Y"],
            base_scores=[0.6, 0.55],
            pattern_result=pr,
            pattern_influence_config=cfg,
        )
        assert r.used_pattern
        assert r.selected_strategy == "X"
        assert r.pattern_aggregation_result is not None
        assert r.pattern_aggregation_result.patterns_used >= 2


# ── BACKWARD COMPAT WITH PHASE 68 ───────────────────────────────


class TestPhase68Compat:
    def test_single_pattern_still_uses_phase68(self):
        pr = _single_pattern_result(avg_score=0.85)
        cfg = _enabled_config()
        r = orchestrate_selection(
            strategy_ids=["A", "B"],
            base_scores=[0.8, 0.7],
            pattern_result=pr,
            pattern_influence_config=cfg,
        )
        assert r.pattern_influence_result is not None
        assert r.pattern_aggregation_result is None

    def test_phase68_and_69_same_bounds(self):
        from umh.runtime.pattern_influence import (
            _FACTOR_CEILING as P68_CEIL,
            _FACTOR_FLOOR as P68_FLOOR,
        )

        assert P68_FLOOR == _FACTOR_FLOOR
        assert P68_CEIL == _FACTOR_CEILING
