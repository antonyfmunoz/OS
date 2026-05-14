"""Phase 71 — Adaptive Half-Life Layer v1 tests.

Tests environment-responsive half-life adjustment: volatility computation,
half-life scaling, bounds enforcement, determinism, isolation, explainability,
and integration with temporal weighting. Covers invariants 353-362.
"""

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime.adaptive_half_life import (
    AdaptiveHalfLifeConfig,
    AdaptiveHalfLifeResult,
    _MAX_VARIANCE,
    _compute_variance,
    compute_adaptive_half_life,
    compute_volatility,
)
from umh.runtime.pattern_temporal import (
    TemporalContribution,
    TemporalPatternConfig,
    TemporalWeightingResult,
    apply_temporal_weights,
    compute_decay_factor,
)
from umh.runtime.pattern_aggregation import (
    PatternAggregationResult,
    PatternContribution,
    _DOMINANCE_CAP,
    _FACTOR_CEILING,
    _FACTOR_FLOOR,
    _MAX_PATTERNS,
    compute_pattern_aggregation,
)
from umh.runtime.pattern_influence import (
    PatternInfluenceConfig,
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
        matches = [
            _match(similarity=1.0, key=k1, stats=_stats(key=k1, avg_score=0.8)),
            _match(similarity=0.75, key=k2, stats=_stats(key=k2, avg_score=0.7)),
        ]
    return PatternResult(
        matched=True,
        best_match=matches[0] if matches else None,
        all_matches=tuple(matches),
        confidence=confidence,
        total_patterns_searched=len(matches),
    )


def _enabled_config(**kw) -> PatternInfluenceConfig:
    defaults = {
        "enabled": True,
        "min_samples": 1,
        "min_confidence": 0.1,
        "similarity_threshold": 0.1,
    }
    defaults.update(kw)
    return PatternInfluenceConfig(**defaults)


def _temporal_config(**kw) -> TemporalPatternConfig:
    defaults = {"enabled": True, "half_life": 50, "min_weight": 0.05, "max_weight": 1.0}
    defaults.update(kw)
    return TemporalPatternConfig(**defaults)


def _adaptive_config(**kw) -> AdaptiveHalfLifeConfig:
    defaults = {
        "enabled": True,
        "base_half_life": 50,
        "min_half_life": 10,
        "max_half_life": 200,
        "volatility_window": 20,
        "volatility_sensitivity": 1.0,
    }
    defaults.update(kw)
    return AdaptiveHalfLifeConfig(**defaults)


def _stable_scores(n: int = 20) -> list[float]:
    return [0.8] * n


def _volatile_scores(n: int = 20) -> list[float]:
    return [0.0 if i % 2 == 0 else 1.0 for i in range(n)]


def _moderate_scores(n: int = 20) -> list[float]:
    return [0.5 + (i % 5) * 0.05 for i in range(n)]


# ═══════════════════════════════════════════════════════════════
# SECTION 1: _compute_variance unit tests
# ═══════════════════════════════════════════════════════════════


class TestComputeVariance:
    """Tests for the internal variance computation."""

    def test_constant_scores_zero_variance(self) -> None:
        assert _compute_variance([0.5, 0.5, 0.5, 0.5]) == 0.0

    def test_single_score_zero_variance(self) -> None:
        assert _compute_variance([0.5]) == 0.0

    def test_empty_list_zero_variance(self) -> None:
        assert _compute_variance([]) == 0.0

    def test_two_extreme_values(self) -> None:
        v = _compute_variance([0.0, 1.0])
        assert abs(v - 0.25) < 1e-10

    def test_known_variance(self) -> None:
        v = _compute_variance([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0])
        expected = 4.0
        assert abs(v - expected) < 1e-10

    def test_all_zeros(self) -> None:
        assert _compute_variance([0.0, 0.0, 0.0]) == 0.0

    def test_all_ones(self) -> None:
        assert _compute_variance([1.0, 1.0, 1.0]) == 0.0

    def test_variance_non_negative(self) -> None:
        import random

        rng = random.Random(42)
        for _ in range(50):
            scores = [rng.random() for _ in range(10)]
            assert _compute_variance(scores) >= 0.0

    def test_symmetric_distribution(self) -> None:
        v1 = _compute_variance([0.3, 0.7])
        v2 = _compute_variance([0.7, 0.3])
        assert abs(v1 - v2) < 1e-12


# ═══════════════════════════════════════════════════════════════
# SECTION 2: compute_volatility unit tests
# ═══════════════════════════════════════════════════════════════


class TestComputeVolatility:
    """Tests for normalized volatility computation."""

    def test_stable_scores_zero(self) -> None:
        v = compute_volatility(_stable_scores())
        assert v == 0.0

    def test_volatile_scores_high(self) -> None:
        v = compute_volatility(_volatile_scores())
        assert v == 1.0

    def test_moderate_scores_between(self) -> None:
        v = compute_volatility(_moderate_scores())
        assert 0.0 <= v <= 1.0

    def test_bounded_zero_one(self) -> None:
        import random

        rng = random.Random(42)
        for _ in range(50):
            scores = [rng.random() for _ in range(20)]
            v = compute_volatility(scores)
            assert 0.0 <= v <= 1.0

    def test_single_score_zero(self) -> None:
        assert compute_volatility([0.5]) == 0.0

    def test_empty_list_zero(self) -> None:
        assert compute_volatility([]) == 0.0

    def test_two_identical_scores(self) -> None:
        assert compute_volatility([0.5, 0.5]) == 0.0

    def test_max_variance_override(self) -> None:
        v = compute_volatility([0.0, 1.0], max_variance=1.0)
        assert abs(v - 0.25) < 1e-10

    def test_zero_max_variance(self) -> None:
        v = compute_volatility([0.0, 1.0], max_variance=0.0)
        assert v == 0.0

    def test_increasing_variance_increasing_volatility(self) -> None:
        low = compute_volatility([0.49, 0.50, 0.51])
        high = compute_volatility([0.0, 0.5, 1.0])
        assert high > low

    def test_default_max_variance(self) -> None:
        assert _MAX_VARIANCE == 0.25


# ═══════════════════════════════════════════════════════════════
# SECTION 3: AdaptiveHalfLifeConfig tests
# ═══════════════════════════════════════════════════════════════


class TestAdaptiveHalfLifeConfig:
    """Configuration validation tests."""

    def test_defaults(self) -> None:
        c = AdaptiveHalfLifeConfig()
        assert c.enabled is False
        assert c.base_half_life == 50
        assert c.min_half_life == 10
        assert c.max_half_life == 200
        assert c.volatility_window == 20
        assert c.volatility_sensitivity == 1.0

    def test_base_clamped_to_one(self) -> None:
        c = AdaptiveHalfLifeConfig(base_half_life=0)
        assert c.base_half_life == 1

    def test_negative_base_clamped(self) -> None:
        c = AdaptiveHalfLifeConfig(base_half_life=-10)
        assert c.base_half_life == 1

    def test_min_clamped_to_one(self) -> None:
        c = AdaptiveHalfLifeConfig(min_half_life=0)
        assert c.min_half_life == 1

    def test_max_floors_to_min(self) -> None:
        c = AdaptiveHalfLifeConfig(min_half_life=100, max_half_life=50)
        assert c.max_half_life >= c.min_half_life

    def test_window_clamped_to_two(self) -> None:
        c = AdaptiveHalfLifeConfig(volatility_window=1)
        assert c.volatility_window == 2

    def test_sensitivity_clamped_low(self) -> None:
        c = AdaptiveHalfLifeConfig(volatility_sensitivity=-1.0)
        assert c.volatility_sensitivity == 0.0

    def test_sensitivity_clamped_high(self) -> None:
        c = AdaptiveHalfLifeConfig(volatility_sensitivity=20.0)
        assert c.volatility_sensitivity == 10.0

    def test_to_dict(self) -> None:
        c = AdaptiveHalfLifeConfig(enabled=True, base_half_life=75)
        d = c.to_dict()
        assert d["enabled"] is True
        assert d["base_half_life"] == 75

    def test_frozen(self) -> None:
        c = AdaptiveHalfLifeConfig()
        try:
            c.enabled = True  # type: ignore[misc]
            assert False, "should be frozen"
        except AttributeError:
            pass

    def test_to_dict_all_keys(self) -> None:
        c = AdaptiveHalfLifeConfig()
        d = c.to_dict()
        expected = {
            "enabled",
            "base_half_life",
            "min_half_life",
            "max_half_life",
            "volatility_window",
            "volatility_sensitivity",
        }
        assert set(d.keys()) == expected


# ═══════════════════════════════════════════════════════════════
# SECTION 4: compute_adaptive_half_life tests
# ═══════════════════════════════════════════════════════════════


class TestComputeAdaptiveHalfLife:
    """Tests for the core adaptive half-life computation."""

    def test_disabled_returns_base(self) -> None:
        r = compute_adaptive_half_life(
            _stable_scores(), config=AdaptiveHalfLifeConfig(enabled=False)
        )
        assert not r.applied
        assert r.computed_half_life == 50

    def test_stable_gives_longer(self) -> None:
        r = compute_adaptive_half_life(_stable_scores(), config=_adaptive_config())
        assert r.computed_half_life > 50

    def test_volatile_gives_shorter(self) -> None:
        r = compute_adaptive_half_life(_volatile_scores(), config=_adaptive_config())
        assert r.computed_half_life <= 50

    def test_stable_longer_than_volatile(self) -> None:
        r_stable = compute_adaptive_half_life(_stable_scores(), config=_adaptive_config())
        r_vol = compute_adaptive_half_life(_volatile_scores(), config=_adaptive_config())
        assert r_stable.computed_half_life > r_vol.computed_half_life

    def test_insufficient_data_fallback(self) -> None:
        r = compute_adaptive_half_life([0.5], config=_adaptive_config())
        assert not r.applied
        assert r.computed_half_life == 50
        assert "insufficient" in r.reason_if_not_applied

    def test_empty_data_fallback(self) -> None:
        r = compute_adaptive_half_life([], config=_adaptive_config())
        assert not r.applied
        assert r.computed_half_life == 50

    def test_none_data_fallback(self) -> None:
        r = compute_adaptive_half_life(None, config=_adaptive_config())
        assert not r.applied
        assert r.computed_half_life == 50

    def test_respects_min_half_life(self) -> None:
        cfg = _adaptive_config(
            base_half_life=10,
            min_half_life=15,
            volatility_sensitivity=5.0,
        )
        r = compute_adaptive_half_life(_volatile_scores(), config=cfg)
        assert r.computed_half_life >= 15

    def test_respects_max_half_life(self) -> None:
        cfg = _adaptive_config(
            base_half_life=100,
            max_half_life=120,
            volatility_sensitivity=5.0,
        )
        r = compute_adaptive_half_life(_stable_scores(), config=cfg)
        assert r.computed_half_life <= 120

    def test_result_has_volatility(self) -> None:
        r = compute_adaptive_half_life(_moderate_scores(), config=_adaptive_config())
        assert 0.0 <= r.volatility <= 1.0

    def test_result_has_window_size(self) -> None:
        r = compute_adaptive_half_life(_stable_scores(30), config=_adaptive_config())
        assert r.window_size == 20

    def test_window_truncates_old_data(self) -> None:
        scores = [1.0] * 100 + [0.5] * 20
        r = compute_adaptive_half_life(scores, config=_adaptive_config(volatility_window=20))
        assert r.window_size == 20

    def test_result_has_base_half_life(self) -> None:
        r = compute_adaptive_half_life(_stable_scores(), config=_adaptive_config(base_half_life=75))
        assert r.base_half_life == 75

    def test_applied_flag_set(self) -> None:
        r = compute_adaptive_half_life(_stable_scores(), config=_adaptive_config())
        assert r.applied

    def test_to_dict(self) -> None:
        r = compute_adaptive_half_life(_stable_scores(), config=_adaptive_config())
        d = r.to_dict()
        expected_keys = {
            "computed_half_life",
            "base_half_life",
            "volatility",
            "window_size",
            "applied",
            "reason_if_not_applied",
        }
        assert set(d.keys()) == expected_keys

    def test_sensitivity_zero_returns_base(self) -> None:
        cfg = _adaptive_config(volatility_sensitivity=0.0)
        r = compute_adaptive_half_life(_volatile_scores(), config=cfg)
        assert r.computed_half_life == 50

    def test_higher_sensitivity_wider_range(self) -> None:
        low_sens = compute_adaptive_half_life(
            _stable_scores(), config=_adaptive_config(volatility_sensitivity=0.5)
        )
        high_sens = compute_adaptive_half_life(
            _stable_scores(), config=_adaptive_config(volatility_sensitivity=3.0)
        )
        assert high_sens.computed_half_life >= low_sens.computed_half_life

    def test_exact_formula_stable(self) -> None:
        cfg = _adaptive_config(base_half_life=50, volatility_sensitivity=1.0)
        r = compute_adaptive_half_life(_stable_scores(), config=cfg)
        expected = int(round(50 * (1.0 + 1.0 * 1.0)))
        assert r.computed_half_life == expected

    def test_exact_formula_max_volatility(self) -> None:
        cfg = _adaptive_config(base_half_life=50, volatility_sensitivity=1.0)
        r = compute_adaptive_half_life(_volatile_scores(), config=cfg)
        expected = int(round(50 * (1.0 + 0.0 * 1.0)))
        assert r.computed_half_life == expected

    def test_default_config_disabled(self) -> None:
        r = compute_adaptive_half_life(_stable_scores())
        assert not r.applied


# ═══════════════════════════════════════════════════════════════
# SECTION 5: Integration with apply_temporal_weights
# ═══════════════════════════════════════════════════════════════


class TestTemporalIntegration:
    """Tests for adaptive half-life integration into temporal weighting."""

    def test_no_adaptive_uses_config_half_life(self) -> None:
        cfg = _temporal_config(half_life=50)
        r = apply_temporal_weights([0.8], ["a"], [50], [1.0], config=cfg)
        assert r.applied
        assert r.effective_half_life == 50
        assert not r.adaptive_applied

    def test_adaptive_overrides_config(self) -> None:
        cfg = _temporal_config(half_life=50)
        adaptive = AdaptiveHalfLifeResult(computed_half_life=100, base_half_life=50, applied=True)
        r = apply_temporal_weights([0.8], ["a"], [50], [1.0], config=cfg, adaptive_result=adaptive)
        assert r.applied
        assert r.effective_half_life == 100
        assert r.adaptive_applied

    def test_adaptive_not_applied_uses_config(self) -> None:
        cfg = _temporal_config(half_life=50)
        adaptive = AdaptiveHalfLifeResult(computed_half_life=100, base_half_life=50, applied=False)
        r = apply_temporal_weights([0.8], ["a"], [50], [1.0], config=cfg, adaptive_result=adaptive)
        assert r.effective_half_life == 50
        assert not r.adaptive_applied

    def test_longer_half_life_slower_decay(self) -> None:
        cfg = _temporal_config(half_life=50)
        r_short = apply_temporal_weights([0.8], ["a"], [50], [1.0], config=cfg)

        adaptive = AdaptiveHalfLifeResult(computed_half_life=200, base_half_life=50, applied=True)
        r_long = apply_temporal_weights(
            [0.8], ["a"], [50], [1.0], config=cfg, adaptive_result=adaptive
        )
        assert r_long.weights[0] > r_short.weights[0]

    def test_shorter_half_life_faster_decay(self) -> None:
        cfg = _temporal_config(half_life=50)
        r_base = apply_temporal_weights([0.8], ["a"], [50], [1.0], config=cfg)

        adaptive = AdaptiveHalfLifeResult(computed_half_life=10, base_half_life=50, applied=True)
        r_fast = apply_temporal_weights(
            [0.8], ["a"], [50], [1.0], config=cfg, adaptive_result=adaptive
        )
        assert r_fast.weights[0] < r_base.weights[0]

    def test_effective_half_life_in_to_dict(self) -> None:
        cfg = _temporal_config()
        r = apply_temporal_weights([0.8], ["a"], [0], [1.0], config=cfg)
        d = r.to_dict()
        assert "effective_half_life" in d
        assert "adaptive_applied" in d

    def test_disabled_temporal_reports_config_hl(self) -> None:
        cfg = TemporalPatternConfig(enabled=False, half_life=75)
        r = apply_temporal_weights([0.8], ["a"], [0], [1.0], config=cfg)
        assert r.effective_half_life == 75

    def test_multiple_patterns_same_adaptive(self) -> None:
        cfg = _temporal_config(half_life=50)
        adaptive = AdaptiveHalfLifeResult(computed_half_life=100, base_half_life=50, applied=True)
        r = apply_temporal_weights(
            [0.8, 0.6, 0.4],
            ["a", "b", "c"],
            [0, 50, 100],
            [1.0, 1.0, 1.0],
            config=cfg,
            adaptive_result=adaptive,
        )
        assert r.effective_half_life == 100
        assert r.adaptive_applied
        assert len(r.weights) == 3


# ═══════════════════════════════════════════════════════════════
# SECTION 6: Invariant tests (353-362)
# ═══════════════════════════════════════════════════════════════


class TestInvariant353Bounded:
    """Inv 353: Half-life always bounded."""

    def test_within_bounds_stable(self) -> None:
        cfg = _adaptive_config(min_half_life=10, max_half_life=200)
        r = compute_adaptive_half_life(_stable_scores(), config=cfg)
        assert 10 <= r.computed_half_life <= 200

    def test_within_bounds_volatile(self) -> None:
        cfg = _adaptive_config(min_half_life=10, max_half_life=200)
        r = compute_adaptive_half_life(_volatile_scores(), config=cfg)
        assert 10 <= r.computed_half_life <= 200

    def test_within_bounds_extreme_sensitivity(self) -> None:
        cfg = _adaptive_config(
            min_half_life=5,
            max_half_life=500,
            volatility_sensitivity=10.0,
        )
        for scores in [_stable_scores(), _volatile_scores(), _moderate_scores()]:
            r = compute_adaptive_half_life(scores, config=cfg)
            assert 5 <= r.computed_half_life <= 500

    def test_narrow_bounds(self) -> None:
        cfg = _adaptive_config(min_half_life=49, max_half_life=51)
        r = compute_adaptive_half_life(_stable_scores(), config=cfg)
        assert 49 <= r.computed_half_life <= 51

    def test_equal_min_max(self) -> None:
        cfg = _adaptive_config(min_half_life=50, max_half_life=50)
        r = compute_adaptive_half_life(_volatile_scores(), config=cfg)
        assert r.computed_half_life == 50


class TestInvariant354StableIncreasesMemory:
    """Inv 354: Stable environments increase memory."""

    def test_stable_above_base(self) -> None:
        cfg = _adaptive_config(base_half_life=50)
        r = compute_adaptive_half_life(_stable_scores(), config=cfg)
        assert r.computed_half_life >= 50

    def test_very_stable_very_long(self) -> None:
        cfg = _adaptive_config(base_half_life=50, max_half_life=500, volatility_sensitivity=3.0)
        r = compute_adaptive_half_life(_stable_scores(), config=cfg)
        assert r.computed_half_life > 100


class TestInvariant355VolatileDecreasesMemory:
    """Inv 355: Volatile environments decrease memory."""

    def test_volatile_at_or_below_base(self) -> None:
        cfg = _adaptive_config(base_half_life=50, min_half_life=10)
        r = compute_adaptive_half_life(_volatile_scores(), config=cfg)
        assert r.computed_half_life <= 50

    def test_moderate_between(self) -> None:
        cfg = _adaptive_config(base_half_life=50)
        r_stable = compute_adaptive_half_life(_stable_scores(), config=cfg)
        r_mod = compute_adaptive_half_life(_moderate_scores(), config=cfg)
        r_vol = compute_adaptive_half_life(_volatile_scores(), config=cfg)
        assert r_vol.computed_half_life <= r_mod.computed_half_life <= r_stable.computed_half_life


class TestInvariant356Deterministic:
    """Inv 356: Deterministic (no randomness)."""

    def test_repeat_identical(self) -> None:
        cfg = _adaptive_config()
        scores = _moderate_scores()
        r1 = compute_adaptive_half_life(scores, config=cfg)
        r2 = compute_adaptive_half_life(scores, config=cfg)
        assert r1.computed_half_life == r2.computed_half_life
        assert r1.volatility == r2.volatility

    def test_hundred_repeats(self) -> None:
        cfg = _adaptive_config()
        scores = _volatile_scores()
        ref = compute_adaptive_half_life(scores, config=cfg)
        for _ in range(100):
            r = compute_adaptive_half_life(scores, config=cfg)
            assert r.computed_half_life == ref.computed_half_life

    def test_temporal_integration_deterministic(self) -> None:
        cfg = _temporal_config()
        adaptive = AdaptiveHalfLifeResult(computed_half_life=75, base_half_life=50, applied=True)
        args = ([0.8, 0.6], ["a", "b"], [10, 50], [1.0, 1.0])
        r1 = apply_temporal_weights(*args, config=cfg, adaptive_result=adaptive)
        r2 = apply_temporal_weights(*args, config=cfg, adaptive_result=adaptive)
        assert r1.weights == r2.weights


class TestInvariant357NoMutation:
    """Inv 357: No mutation of historical records."""

    def test_scores_list_unchanged(self) -> None:
        scores = [0.3, 0.5, 0.7, 0.9]
        scores_copy = list(scores)
        compute_adaptive_half_life(scores, config=_adaptive_config())
        assert scores == scores_copy

    def test_pattern_memory_unchanged(self) -> None:
        mem = PatternMemory()
        k = _key()
        for i in range(10):
            mem.append(PatternRecord(key=k, outcome_score=0.5 + i * 0.05, timestamp=i))
        initial_size = mem.size
        initial_records = mem.get_records()

        scores = [r.outcome_score for r in mem.get_records()]
        compute_adaptive_half_life(scores, config=_adaptive_config())

        assert mem.size == initial_size
        assert mem.get_records() == initial_records


class TestInvariant358NoFeedbackFromScoring:
    """Inv 358: No feedback from scoring — uses dispersion, not direction."""

    def test_high_scores_same_variance_as_low(self) -> None:
        high = [0.9, 0.9, 0.9, 0.9, 0.9]
        low = [0.1, 0.1, 0.1, 0.1, 0.1]
        r_high = compute_adaptive_half_life(high, config=_adaptive_config())
        r_low = compute_adaptive_half_life(low, config=_adaptive_config())
        assert r_high.computed_half_life == r_low.computed_half_life

    def test_shifted_scores_same_volatility(self) -> None:
        a = [0.2, 0.4, 0.2, 0.4, 0.2]
        b = [0.6, 0.8, 0.6, 0.8, 0.6]
        v_a = compute_volatility(a)
        v_b = compute_volatility(b)
        assert abs(v_a - v_b) < 1e-10


class TestInvariant359NoAbruptJumps:
    """Inv 359: No abrupt jumps — smooth change."""

    def test_gradual_volatility_gradual_half_life(self) -> None:
        cfg = _adaptive_config(base_half_life=50, volatility_sensitivity=1.0)
        prev_hl = None
        for spread in range(0, 11):
            offset = spread * 0.05
            scores = [0.5 - offset, 0.5 + offset] * 10
            r = compute_adaptive_half_life(scores, config=cfg)
            if prev_hl is not None:
                assert abs(r.computed_half_life - prev_hl) <= 15
            prev_hl = r.computed_half_life

    def test_single_new_observation_bounded_change(self) -> None:
        cfg = _adaptive_config()
        base_scores = [0.5] * 19
        r1 = compute_adaptive_half_life(base_scores + [0.5], config=cfg)
        r2 = compute_adaptive_half_life(base_scores + [1.0], config=cfg)
        assert abs(r1.computed_half_life - r2.computed_half_life) <= 20


class TestInvariant360Explainable:
    """Inv 360: Explainable half-life."""

    def test_result_has_all_fields(self) -> None:
        r = compute_adaptive_half_life(_stable_scores(), config=_adaptive_config())
        assert r.applied
        assert r.computed_half_life > 0
        assert r.base_half_life == 50
        assert 0.0 <= r.volatility <= 1.0
        assert r.window_size > 0

    def test_to_dict_complete(self) -> None:
        r = compute_adaptive_half_life(_stable_scores(), config=_adaptive_config())
        d = r.to_dict()
        assert "computed_half_life" in d
        assert "base_half_life" in d
        assert "volatility" in d
        assert "window_size" in d
        assert "applied" in d

    def test_disabled_has_reason(self) -> None:
        r = compute_adaptive_half_life(
            _stable_scores(), config=AdaptiveHalfLifeConfig(enabled=False)
        )
        assert "disabled" in r.reason_if_not_applied


class TestInvariant361MissingDataFallback:
    """Inv 361: Missing data → fallback to base."""

    def test_none_scores(self) -> None:
        r = compute_adaptive_half_life(None, config=_adaptive_config())
        assert r.computed_half_life == 50
        assert not r.applied

    def test_empty_scores(self) -> None:
        r = compute_adaptive_half_life([], config=_adaptive_config())
        assert r.computed_half_life == 50
        assert not r.applied

    def test_single_score(self) -> None:
        r = compute_adaptive_half_life([0.5], config=_adaptive_config())
        assert r.computed_half_life == 50
        assert not r.applied

    def test_two_scores_sufficient(self) -> None:
        r = compute_adaptive_half_life([0.5, 0.5], config=_adaptive_config())
        assert r.applied

    def test_fallback_uses_base_from_config(self) -> None:
        cfg = _adaptive_config(base_half_life=75)
        r = compute_adaptive_half_life([], config=cfg)
        assert r.computed_half_life == 75


class TestInvariant362NoInstability:
    """Inv 362: No instability introduced."""

    def test_small_input_change_small_output_change(self) -> None:
        cfg = _adaptive_config()
        scores_a = [0.5] * 20
        scores_b = [0.5] * 19 + [0.55]
        r_a = compute_adaptive_half_life(scores_a, config=cfg)
        r_b = compute_adaptive_half_life(scores_b, config=cfg)
        assert abs(r_a.computed_half_life - r_b.computed_half_life) <= 5

    def test_sweep_window_sizes(self) -> None:
        for w in [2, 5, 10, 20, 50]:
            cfg = _adaptive_config(volatility_window=w)
            r = compute_adaptive_half_life(_moderate_scores(50), config=cfg)
            assert cfg.min_half_life <= r.computed_half_life <= cfg.max_half_life


# ═══════════════════════════════════════════════════════════════
# SECTION 7: AdaptiveHalfLifeResult dataclass tests
# ═══════════════════════════════════════════════════════════════


class TestAdaptiveHalfLifeResult:
    """Tests for the result dataclass."""

    def test_defaults(self) -> None:
        r = AdaptiveHalfLifeResult()
        assert r.computed_half_life == 50
        assert r.base_half_life == 50
        assert r.volatility == 0.0
        assert r.window_size == 0
        assert not r.applied

    def test_custom_values(self) -> None:
        r = AdaptiveHalfLifeResult(
            computed_half_life=100,
            base_half_life=50,
            volatility=0.3,
            window_size=20,
            applied=True,
        )
        assert r.computed_half_life == 100
        assert r.volatility == 0.3

    def test_frozen(self) -> None:
        r = AdaptiveHalfLifeResult()
        try:
            r.applied = True  # type: ignore[misc]
            assert False
        except AttributeError:
            pass

    def test_to_dict_roundtrip(self) -> None:
        r = AdaptiveHalfLifeResult(computed_half_life=75, base_half_life=50, volatility=0.25)
        d = r.to_dict()
        assert d["computed_half_life"] == 75
        assert d["volatility"] == 0.25


# ═══════════════════════════════════════════════════════════════
# SECTION 8: End-to-end with pattern aggregation
# ═══════════════════════════════════════════════════════════════


class TestEndToEndAggregation:
    """End-to-end: adaptive half-life → temporal weights → aggregation."""

    def test_stable_environment_longer_memory(self) -> None:
        adaptive = compute_adaptive_half_life(_stable_scores(), config=_adaptive_config())
        cfg = _temporal_config(half_life=50)
        r = apply_temporal_weights([0.8], ["a"], [100], [1.0], config=cfg, adaptive_result=adaptive)
        r_base = apply_temporal_weights([0.8], ["a"], [100], [1.0], config=cfg)
        assert r.weights[0] > r_base.weights[0]

    def test_volatile_environment_shorter_memory(self) -> None:
        adaptive = compute_adaptive_half_life(_volatile_scores(), config=_adaptive_config())
        cfg = _temporal_config(half_life=50)
        r = apply_temporal_weights([0.8], ["a"], [100], [1.0], config=cfg, adaptive_result=adaptive)
        r_base = apply_temporal_weights([0.8], ["a"], [100], [1.0], config=cfg)
        assert r.weights[0] <= r_base.weights[0]

    def test_full_pipeline_deterministic(self) -> None:
        scores = _moderate_scores()
        adaptive = compute_adaptive_half_life(scores, config=_adaptive_config())
        cfg = _temporal_config()
        r1 = apply_temporal_weights(
            [0.5, 0.3],
            ["a", "b"],
            [10, 50],
            [0.9, 0.8],
            config=cfg,
            adaptive_result=adaptive,
        )
        r2 = apply_temporal_weights(
            [0.5, 0.3],
            ["a", "b"],
            [10, 50],
            [0.9, 0.8],
            config=cfg,
            adaptive_result=adaptive,
        )
        assert r1.weights == r2.weights
        assert r1.effective_half_life == r2.effective_half_life

    def test_aggregation_with_adaptive(self) -> None:
        pr = _multi_pattern_result()
        adaptive = compute_adaptive_half_life(_stable_scores(), config=_adaptive_config())
        cfg = _temporal_config(half_life=50)

        k1_str = str(
            _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW).to_tuple()
        )
        k2_str = str(
            _key(
                TrendDirection.UP, RiskLevel.LOW, StabilityLevel.MEDIUM, UrgencyLevel.LOW
            ).to_tuple()
        )

        r = compute_pattern_aggregation(
            pr,
            baseline_score=0.5,
            config=_enabled_config(),
            temporal_config=cfg,
            current_observation_index=100,
            pattern_last_seen={k1_str: 90, k2_str: 50},
        )
        assert r.applied
        assert r.temporal_applied


# ═══════════════════════════════════════════════════════════════
# SECTION 9: Volatility sensitivity sweep
# ═══════════════════════════════════════════════════════════════


class TestSensitivitySweep:
    """Systematic tests across sensitivity values."""

    def test_zero_sensitivity_always_base(self) -> None:
        for scores in [_stable_scores(), _volatile_scores(), _moderate_scores()]:
            cfg = _adaptive_config(volatility_sensitivity=0.0)
            r = compute_adaptive_half_life(scores, config=cfg)
            assert r.computed_half_life == 50

    def test_increasing_sensitivity_widens_range(self) -> None:
        stable_hls = []
        for sens in [0.5, 1.0, 2.0, 3.0]:
            cfg = _adaptive_config(volatility_sensitivity=sens, max_half_life=1000)
            r = compute_adaptive_half_life(_stable_scores(), config=cfg)
            stable_hls.append(r.computed_half_life)
        for i in range(len(stable_hls) - 1):
            assert stable_hls[i + 1] >= stable_hls[i]

    def test_sensitivity_one_doubles_for_stable(self) -> None:
        cfg = _adaptive_config(base_half_life=50, volatility_sensitivity=1.0)
        r = compute_adaptive_half_life(_stable_scores(), config=cfg)
        assert r.computed_half_life == 100


# ═══════════════════════════════════════════════════════════════
# SECTION 10: Window size tests
# ═══════════════════════════════════════════════════════════════


class TestWindowSize:
    """Tests for the volatility window parameter."""

    def test_window_smaller_than_data(self) -> None:
        cfg = _adaptive_config(volatility_window=5)
        scores = [0.5] * 100
        r = compute_adaptive_half_life(scores, config=cfg)
        assert r.window_size == 5

    def test_window_larger_than_data(self) -> None:
        cfg = _adaptive_config(volatility_window=100)
        scores = [0.5] * 10
        r = compute_adaptive_half_life(scores, config=cfg)
        assert r.window_size == 10

    def test_window_equals_data(self) -> None:
        cfg = _adaptive_config(volatility_window=20)
        scores = [0.5] * 20
        r = compute_adaptive_half_life(scores, config=cfg)
        assert r.window_size == 20

    def test_uses_most_recent(self) -> None:
        cfg = _adaptive_config(volatility_window=5)
        volatile_then_stable = [0.0, 1.0] * 50 + [0.5] * 5
        r = compute_adaptive_half_life(volatile_then_stable, config=cfg)
        assert r.volatility < 0.01

    def test_ignores_old_volatility(self) -> None:
        cfg = _adaptive_config(volatility_window=5)
        stable_then_volatile = [0.5] * 50 + [0.0, 1.0, 0.0, 1.0, 0.0]
        r = compute_adaptive_half_life(stable_then_volatile, config=cfg)
        assert r.volatility > 0.5


# ═══════════════════════════════════════════════════════════════
# SECTION 11: Edge cases
# ═══════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Edge cases for adaptive half-life."""

    def test_all_same_score(self) -> None:
        r = compute_adaptive_half_life([0.5] * 100, config=_adaptive_config())
        assert r.volatility == 0.0

    def test_two_scores_only(self) -> None:
        r = compute_adaptive_half_life([0.0, 1.0], config=_adaptive_config())
        assert r.applied
        assert r.volatility == 1.0

    def test_scores_all_zero(self) -> None:
        r = compute_adaptive_half_life([0.0] * 20, config=_adaptive_config())
        assert r.volatility == 0.0

    def test_scores_all_one(self) -> None:
        r = compute_adaptive_half_life([1.0] * 20, config=_adaptive_config())
        assert r.volatility == 0.0

    def test_min_equals_max_half_life(self) -> None:
        cfg = _adaptive_config(min_half_life=50, max_half_life=50)
        r = compute_adaptive_half_life(_volatile_scores(), config=cfg)
        assert r.computed_half_life == 50

    def test_very_small_base(self) -> None:
        cfg = _adaptive_config(base_half_life=1, min_half_life=1, max_half_life=10)
        r = compute_adaptive_half_life(_stable_scores(), config=cfg)
        assert 1 <= r.computed_half_life <= 10

    def test_very_large_base(self) -> None:
        cfg = _adaptive_config(base_half_life=1000, min_half_life=500, max_half_life=5000)
        r = compute_adaptive_half_life(_stable_scores(), config=cfg)
        assert 500 <= r.computed_half_life <= 5000

    def test_negative_scores(self) -> None:
        scores = [-0.5, 0.5, -0.5, 0.5, -0.5]
        r = compute_adaptive_half_life(scores, config=_adaptive_config())
        assert r.applied
        assert 0.0 <= r.volatility <= 1.0


# ═══════════════════════════════════════════════════════════════
# SECTION 12: Import and module structure tests
# ═══════════════════════════════════════════════════════════════


class TestImports:
    """Verify clean imports from the public API."""

    def test_import_from_adaptive_half_life(self) -> None:
        from umh.runtime.adaptive_half_life import (
            AdaptiveHalfLifeConfig,
            AdaptiveHalfLifeResult,
            compute_adaptive_half_life,
            compute_volatility,
        )

        assert callable(compute_adaptive_half_life)
        assert callable(compute_volatility)

    def test_import_from_runtime_init(self) -> None:
        from umh.runtime import (
            AdaptiveHalfLifeConfig,
            AdaptiveHalfLifeResult,
            compute_adaptive_half_life,
            compute_volatility,
        )

        assert callable(compute_adaptive_half_life)
        assert callable(compute_volatility)

    def test_temporal_result_has_new_fields(self) -> None:
        r = TemporalWeightingResult()
        assert hasattr(r, "effective_half_life")
        assert hasattr(r, "adaptive_applied")


# ═══════════════════════════════════════════════════════════════
# SECTION 13: Backward compatibility — Phase 70 unchanged
# ═══════════════════════════════════════════════════════════════


class TestPhase70BackwardCompat:
    """Ensure Phase 70 behavior unchanged when adaptive is off."""

    def test_no_adaptive_arg(self) -> None:
        cfg = _temporal_config(half_life=50)
        r = apply_temporal_weights([0.8], ["a"], [50], [1.0], config=cfg)
        assert r.applied
        assert abs(r.weights[0] - 0.4) < 1e-10
        assert not r.adaptive_applied
        assert r.effective_half_life == 50

    def test_disabled_temporal(self) -> None:
        cfg = TemporalPatternConfig(enabled=False)
        r = apply_temporal_weights([0.8], ["a"], [0], [1.0], config=cfg)
        assert not r.applied
        assert r.weights == (0.8,)

    def test_decay_factor_unchanged(self) -> None:
        d = compute_decay_factor(50, 50)
        assert abs(d - 0.5) < 1e-10

    def test_floor_still_works(self) -> None:
        cfg = _temporal_config(half_life=5, min_weight=0.05)
        r = apply_temporal_weights([0.001], ["a"], [10000], [0.9], config=cfg)
        assert r.weights[0] >= 0.05 * 0.9 - 1e-12

    def test_contributions_preserved(self) -> None:
        cfg = _temporal_config()
        r = apply_temporal_weights([0.5], ["k1"], [25], [0.9], config=cfg)
        assert len(r.contributions) == 1
        assert r.contributions[0].key == "k1"


# ═══════════════════════════════════════════════════════════════
# SECTION 14: Volatility from PatternMemory records
# ═══════════════════════════════════════════════════════════════


class TestVolatilityFromMemory:
    """Test extracting scores from PatternMemory for volatility."""

    def test_extract_scores_from_records(self) -> None:
        mem = PatternMemory()
        k = _key()
        for i in range(10):
            mem.append(PatternRecord(key=k, outcome_score=0.5 + i * 0.05, timestamp=i))
        scores = [r.outcome_score for r in mem.get_records()]
        v = compute_volatility(scores)
        assert 0.0 <= v <= 1.0

    def test_stable_memory(self) -> None:
        mem = PatternMemory()
        k = _key()
        for i in range(20):
            mem.append(PatternRecord(key=k, outcome_score=0.5, timestamp=i))
        scores = [r.outcome_score for r in mem.get_records()]
        v = compute_volatility(scores)
        assert v == 0.0

    def test_volatile_memory(self) -> None:
        mem = PatternMemory()
        k = _key()
        for i in range(20):
            mem.append(
                PatternRecord(
                    key=k,
                    outcome_score=0.0 if i % 2 == 0 else 1.0,
                    timestamp=i,
                )
            )
        scores = [r.outcome_score for r in mem.get_records()]
        v = compute_volatility(scores)
        assert v == 1.0


# ═══════════════════════════════════════════════════════════════
# SECTION 15: TemporalWeightingResult new fields
# ═══════════════════════════════════════════════════════════════


class TestTemporalResultNewFields:
    """Tests for new fields added to TemporalWeightingResult."""

    def test_defaults(self) -> None:
        r = TemporalWeightingResult()
        assert r.effective_half_life == 50
        assert r.adaptive_applied is False

    def test_custom(self) -> None:
        r = TemporalWeightingResult(effective_half_life=100, adaptive_applied=True)
        assert r.effective_half_life == 100
        assert r.adaptive_applied is True

    def test_to_dict_includes_new_fields(self) -> None:
        r = TemporalWeightingResult(effective_half_life=75, adaptive_applied=True)
        d = r.to_dict()
        assert d["effective_half_life"] == 75
        assert d["adaptive_applied"] is True

    def test_frozen(self) -> None:
        r = TemporalWeightingResult()
        try:
            r.effective_half_life = 100  # type: ignore[misc]
            assert False
        except AttributeError:
            pass


# ═══════════════════════════════════════════════════════════════
# SECTION 16: Comprehensive parameter sweep
# ═══════════════════════════════════════════════════════════════


class TestParameterSweep:
    """Sweep across combinations of parameters."""

    def test_base_half_life_sweep(self) -> None:
        for base in [10, 25, 50, 100, 200]:
            cfg = _adaptive_config(base_half_life=base)
            r = compute_adaptive_half_life(_stable_scores(), config=cfg)
            assert r.computed_half_life >= base

    def test_window_sweep(self) -> None:
        for w in [2, 5, 10, 20, 50]:
            cfg = _adaptive_config(volatility_window=w)
            r = compute_adaptive_half_life(_moderate_scores(100), config=cfg)
            assert r.applied
            assert r.window_size == w

    def test_sensitivity_sweep(self) -> None:
        prev_hl = None
        for s in [0.0, 0.5, 1.0, 2.0, 5.0]:
            cfg = _adaptive_config(volatility_sensitivity=s, max_half_life=1000)
            r = compute_adaptive_half_life(_stable_scores(), config=cfg)
            if prev_hl is not None:
                assert r.computed_half_life >= prev_hl
            prev_hl = r.computed_half_life

    def test_bounds_sweep(self) -> None:
        for mn, mx in [(1, 10), (10, 50), (50, 200), (100, 500)]:
            cfg = _adaptive_config(min_half_life=mn, max_half_life=mx)
            for scores in [_stable_scores(), _volatile_scores()]:
                r = compute_adaptive_half_life(scores, config=cfg)
                assert mn <= r.computed_half_life <= mx


# ═══════════════════════════════════════════════════════════════
# SECTION 17: Phase 69/70 regression guard
# ═══════════════════════════════════════════════════════════════


class TestPhase69_70Regression:
    """Ensure Phase 69 and 70 behaviors still work."""

    def test_aggregation_without_temporal(self) -> None:
        pr = _multi_pattern_result()
        r = compute_pattern_aggregation(pr, baseline_score=0.5, config=_enabled_config())
        assert r.applied
        assert not r.temporal_applied

    def test_aggregation_with_temporal_no_adaptive(self) -> None:
        pr = _multi_pattern_result()
        r = compute_pattern_aggregation(
            pr,
            baseline_score=0.5,
            config=_enabled_config(),
            temporal_config=_temporal_config(),
            current_observation_index=100,
        )
        assert r.applied
        assert r.temporal_applied

    def test_neutral_when_disabled(self) -> None:
        r = compute_pattern_aggregation(None, config=PatternInfluenceConfig(enabled=False))
        assert not r.applied

    def test_factor_bounded(self) -> None:
        pr = _multi_pattern_result()
        r = compute_pattern_aggregation(
            pr,
            baseline_score=0.5,
            config=_enabled_config(),
            temporal_config=_temporal_config(),
            current_observation_index=100,
        )
        assert _FACTOR_FLOOR <= r.final_factor <= _FACTOR_CEILING

    def test_dominance_cap_still_enforced(self) -> None:
        k1 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k2 = _key(TrendDirection.DOWN, RiskLevel.HIGH, StabilityLevel.LOW, UrgencyLevel.HIGH)
        matches = [
            _match(similarity=1.0, key=k1),
            _match(similarity=0.1, key=k2),
        ]
        pr = _multi_pattern_result(matches)
        r = compute_pattern_aggregation(pr, baseline_score=0.5, config=_enabled_config())
        for c in r.contributions:
            assert c.normalized_weight <= _DOMINANCE_CAP + 1e-10

    def test_max_patterns_enforced(self) -> None:
        keys = [
            _key(
                TrendDirection.UP if i % 2 == 0 else TrendDirection.DOWN,
                RiskLevel.LOW if i < 4 else RiskLevel.HIGH,
                StabilityLevel.HIGH if i % 3 == 0 else StabilityLevel.MEDIUM,
                UrgencyLevel.LOW if i < 2 else UrgencyLevel.MEDIUM,
            )
            for i in range(8)
        ]
        matches = [_match(similarity=max(0.5, 1.0 - i * 0.05), key=k) for i, k in enumerate(keys)]
        pr = _multi_pattern_result(matches)
        r = compute_pattern_aggregation(pr, baseline_score=0.5, config=_enabled_config())
        assert r.patterns_used <= _MAX_PATTERNS

    def test_weights_sum_to_one(self) -> None:
        pr = _multi_pattern_result()
        r = compute_pattern_aggregation(
            pr,
            baseline_score=0.5,
            config=_enabled_config(),
            temporal_config=_temporal_config(),
            current_observation_index=100,
        )
        total = sum(c.normalized_weight for c in r.contributions)
        assert abs(total - 1.0) < 1e-10
