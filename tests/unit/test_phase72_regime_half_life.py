"""Phase 72 — Regime-Specific Half-Life Layer v1 tests.

Tests per-regime memory speed adjustment: multiplier application, ordering,
bounds enforcement, fallback, determinism, isolation, explainability,
smooth transitions, and integration. Covers invariants 363-372.
"""

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime.regime_half_life import (
    RegimeCategory,
    RegimeHalfLifeConfig,
    RegimeHalfLifeResult,
    _DEFAULT_MULTIPLIERS,
    _REGIME_TYPE_TO_CATEGORY,
    classify_regime_category,
    compute_regime_half_life,
)
from umh.runtime.adaptive_half_life import (
    AdaptiveHalfLifeConfig,
    AdaptiveHalfLifeResult,
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
from umh.runtime.pattern_influence import PatternInfluenceConfig
from umh.runtime.pattern_matching import PatternMatch, PatternResult
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
from umh.runtime.regime import RegimeType


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
        key=key or _key(), count=count, avg_score=avg_score, success_rate=success_rate
    )


def _match(
    similarity: float = 1.0,
    sample_size: int = 20,
    stats: PatternStats | None = None,
    key: PatternKey | None = None,
) -> PatternMatch:
    k = key or _key()
    return PatternMatch(
        matched_key=k, similarity=similarity, stats=stats or _stats(key=k), sample_size=sample_size
    )


def _multi_pattern_result(
    matches: list[PatternMatch] | None = None, confidence: float = 0.8
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


def _regime_config(**kw) -> RegimeHalfLifeConfig:
    defaults = {
        "enabled": True,
        "base_half_life": 50,
        "min_half_life": 10,
        "max_half_life": 200,
    }
    defaults.update(kw)
    return RegimeHalfLifeConfig(**defaults)


def _adaptive_result(
    computed: int = 80, base: int = 50, volatility: float = 0.2, applied: bool = True
) -> AdaptiveHalfLifeResult:
    return AdaptiveHalfLifeResult(
        computed_half_life=computed,
        base_half_life=base,
        volatility=volatility,
        window_size=20,
        applied=applied,
    )


# ═══════════════════════════════════════════════════════════════
# SECTION 1: RegimeCategory enum tests
# ═══════════════════════════════════════════════════════════════


class TestRegimeCategory:
    """Tests for the RegimeCategory enum."""

    def test_four_categories(self) -> None:
        assert len(RegimeCategory) == 4

    def test_values(self) -> None:
        assert RegimeCategory.STABLE.value == "stable"
        assert RegimeCategory.TREND.value == "trend"
        assert RegimeCategory.SPIKE.value == "spike"
        assert RegimeCategory.CHAOS.value == "chaos"

    def test_default_multipliers_exist(self) -> None:
        for cat in RegimeCategory:
            assert cat in _DEFAULT_MULTIPLIERS

    def test_multiplier_ordering(self) -> None:
        assert (
            _DEFAULT_MULTIPLIERS[RegimeCategory.STABLE]
            >= _DEFAULT_MULTIPLIERS[RegimeCategory.TREND]
        )
        assert (
            _DEFAULT_MULTIPLIERS[RegimeCategory.TREND] >= _DEFAULT_MULTIPLIERS[RegimeCategory.SPIKE]
        )
        assert (
            _DEFAULT_MULTIPLIERS[RegimeCategory.SPIKE] >= _DEFAULT_MULTIPLIERS[RegimeCategory.CHAOS]
        )


# ═══════════════════════════════════════════════════════════════
# SECTION 2: classify_regime_category tests
# ═══════════════════════════════════════════════════════════════


class TestClassifyRegimeCategory:
    """Tests for mapping RegimeType → RegimeCategory."""

    def test_stable(self) -> None:
        assert classify_regime_category(RegimeType.STABLE) == RegimeCategory.STABLE

    def test_trend_up(self) -> None:
        assert classify_regime_category(RegimeType.TREND_UP) == RegimeCategory.TREND

    def test_trend_down(self) -> None:
        assert classify_regime_category(RegimeType.TREND_DOWN) == RegimeCategory.TREND

    def test_spike_up(self) -> None:
        assert classify_regime_category(RegimeType.SPIKE_UP) == RegimeCategory.SPIKE

    def test_spike_down(self) -> None:
        assert classify_regime_category(RegimeType.SPIKE_DOWN) == RegimeCategory.SPIKE

    def test_label_stable(self) -> None:
        assert classify_regime_category(regime_label="stable") == RegimeCategory.STABLE

    def test_label_trend(self) -> None:
        assert classify_regime_category(regime_label="trend") == RegimeCategory.TREND

    def test_label_spike(self) -> None:
        assert classify_regime_category(regime_label="spike") == RegimeCategory.SPIKE

    def test_label_chaos(self) -> None:
        assert classify_regime_category(regime_label="chaos") == RegimeCategory.CHAOS

    def test_label_spike_up(self) -> None:
        assert classify_regime_category(regime_label="spike_up") == RegimeCategory.SPIKE

    def test_label_trend_down(self) -> None:
        assert classify_regime_category(regime_label="trend_down") == RegimeCategory.TREND

    def test_label_case_insensitive(self) -> None:
        assert classify_regime_category(regime_label="STABLE") == RegimeCategory.STABLE
        assert classify_regime_category(regime_label="Chaos") == RegimeCategory.CHAOS

    def test_none_defaults_to_trend(self) -> None:
        assert classify_regime_category() == RegimeCategory.TREND

    def test_unknown_label_defaults_to_trend(self) -> None:
        assert classify_regime_category(regime_label="unknown") == RegimeCategory.TREND

    def test_regime_type_takes_priority(self) -> None:
        result = classify_regime_category(RegimeType.STABLE, "chaos")
        assert result == RegimeCategory.STABLE

    def test_all_regime_types_mapped(self) -> None:
        for rt in RegimeType:
            cat = classify_regime_category(rt)
            assert isinstance(cat, RegimeCategory)


# ═══════════════════════════════════════════════════════════════
# SECTION 3: RegimeHalfLifeConfig tests
# ═══════════════════════════════════════════════════════════════


class TestRegimeHalfLifeConfig:
    """Config validation tests."""

    def test_defaults(self) -> None:
        c = RegimeHalfLifeConfig()
        assert c.enabled is False
        assert c.base_half_life == 50
        assert c.min_half_life == 10
        assert c.max_half_life == 200

    def test_default_multipliers(self) -> None:
        c = RegimeHalfLifeConfig()
        assert c.regime_multipliers[RegimeCategory.STABLE] == 1.5
        assert c.regime_multipliers[RegimeCategory.TREND] == 1.0
        assert c.regime_multipliers[RegimeCategory.SPIKE] == 0.6
        assert c.regime_multipliers[RegimeCategory.CHAOS] == 0.4

    def test_base_clamped_to_one(self) -> None:
        c = RegimeHalfLifeConfig(base_half_life=0)
        assert c.base_half_life == 1

    def test_min_clamped_to_one(self) -> None:
        c = RegimeHalfLifeConfig(min_half_life=0)
        assert c.min_half_life == 1

    def test_max_floors_to_min(self) -> None:
        c = RegimeHalfLifeConfig(min_half_life=100, max_half_life=50)
        assert c.max_half_life >= c.min_half_life

    def test_multiplier_clamped_low(self) -> None:
        c = RegimeHalfLifeConfig(
            regime_multipliers={
                RegimeCategory.STABLE: -1.0,
                RegimeCategory.TREND: 1.0,
                RegimeCategory.SPIKE: 0.5,
                RegimeCategory.CHAOS: 0.3,
            }
        )
        assert c.regime_multipliers[RegimeCategory.STABLE] == 0.01

    def test_multiplier_clamped_high(self) -> None:
        c = RegimeHalfLifeConfig(
            regime_multipliers={
                RegimeCategory.STABLE: 50.0,
                RegimeCategory.TREND: 1.0,
                RegimeCategory.SPIKE: 0.5,
                RegimeCategory.CHAOS: 0.3,
            }
        )
        assert c.regime_multipliers[RegimeCategory.STABLE] == 10.0

    def test_custom_multipliers(self) -> None:
        mults = {
            RegimeCategory.STABLE: 2.0,
            RegimeCategory.TREND: 1.5,
            RegimeCategory.SPIKE: 0.8,
            RegimeCategory.CHAOS: 0.3,
        }
        c = RegimeHalfLifeConfig(regime_multipliers=mults)
        assert c.regime_multipliers[RegimeCategory.STABLE] == 2.0

    def test_to_dict(self) -> None:
        c = RegimeHalfLifeConfig(enabled=True, base_half_life=75)
        d = c.to_dict()
        assert d["enabled"] is True
        assert d["base_half_life"] == 75
        assert "regime_multipliers" in d
        assert "stable" in d["regime_multipliers"]

    def test_frozen(self) -> None:
        c = RegimeHalfLifeConfig()
        try:
            c.enabled = True  # type: ignore[misc]
            assert False, "should be frozen"
        except AttributeError:
            pass

    def test_to_dict_all_keys(self) -> None:
        c = RegimeHalfLifeConfig()
        d = c.to_dict()
        expected = {
            "enabled",
            "base_half_life",
            "regime_multipliers",
            "min_half_life",
            "max_half_life",
        }
        assert set(d.keys()) == expected


# ═══════════════════════════════════════════════════════════════
# SECTION 4: compute_regime_half_life core tests
# ═══════════════════════════════════════════════════════════════


class TestComputeRegimeHalfLife:
    """Tests for the core regime half-life computation."""

    def test_disabled_returns_vol_hl(self) -> None:
        adaptive = _adaptive_result(computed=80)
        r = compute_regime_half_life(
            adaptive_result=adaptive,
            regime_type=RegimeType.STABLE,
            config=RegimeHalfLifeConfig(enabled=False),
        )
        assert not r.applied
        assert r.final_half_life == 80

    def test_disabled_no_adaptive_returns_base(self) -> None:
        r = compute_regime_half_life(config=RegimeHalfLifeConfig(enabled=False, base_half_life=60))
        assert r.final_half_life == 60

    def test_stable_longer_than_base(self) -> None:
        adaptive = _adaptive_result(computed=80)
        r = compute_regime_half_life(
            adaptive_result=adaptive, regime_type=RegimeType.STABLE, config=_regime_config()
        )
        assert r.final_half_life > 80

    def test_spike_shorter_than_base(self) -> None:
        adaptive = _adaptive_result(computed=80)
        r = compute_regime_half_life(
            adaptive_result=adaptive, regime_type=RegimeType.SPIKE_UP, config=_regime_config()
        )
        assert r.final_half_life < 80

    def test_trend_neutral(self) -> None:
        adaptive = _adaptive_result(computed=80)
        r = compute_regime_half_life(
            adaptive_result=adaptive, regime_type=RegimeType.TREND_UP, config=_regime_config()
        )
        assert r.final_half_life == 80

    def test_chaos_shortest(self) -> None:
        adaptive = _adaptive_result(computed=100)
        r = compute_regime_half_life(
            adaptive_result=adaptive, regime_label="chaos", config=_regime_config()
        )
        assert r.final_half_life < 50

    def test_stable_gt_trend_gt_spike_gt_chaos(self) -> None:
        adaptive = _adaptive_result(computed=100)
        cfg = _regime_config(max_half_life=500)
        r_stable = compute_regime_half_life(adaptive, RegimeType.STABLE, config=cfg)
        r_trend = compute_regime_half_life(adaptive, RegimeType.TREND_UP, config=cfg)
        r_spike = compute_regime_half_life(adaptive, RegimeType.SPIKE_UP, config=cfg)
        r_chaos = compute_regime_half_life(adaptive, regime_label="chaos", config=cfg)
        assert r_stable.final_half_life >= r_trend.final_half_life
        assert r_trend.final_half_life >= r_spike.final_half_life
        assert r_spike.final_half_life >= r_chaos.final_half_life

    def test_multiplier_applied_correctly(self) -> None:
        adaptive = _adaptive_result(computed=100)
        cfg = _regime_config(max_half_life=500)
        r = compute_regime_half_life(adaptive, RegimeType.STABLE, config=cfg)
        expected = int(round(100 * 1.5))
        assert r.final_half_life == expected

    def test_no_adaptive_uses_base(self) -> None:
        cfg = _regime_config(base_half_life=50)
        r = compute_regime_half_life(regime_type=RegimeType.STABLE, config=cfg)
        expected = int(round(50 * 1.5))
        assert r.final_half_life == expected

    def test_unapplied_adaptive_uses_base(self) -> None:
        adaptive = _adaptive_result(computed=80, applied=False)
        cfg = _regime_config(base_half_life=50)
        r = compute_regime_half_life(adaptive, RegimeType.STABLE, config=cfg)
        expected = int(round(50 * 1.5))
        assert r.final_half_life == expected

    def test_result_has_regime(self) -> None:
        adaptive = _adaptive_result()
        r = compute_regime_half_life(adaptive, RegimeType.SPIKE_DOWN, config=_regime_config())
        assert r.regime == "spike_down"
        assert r.regime_category == "spike"

    def test_result_has_multiplier(self) -> None:
        adaptive = _adaptive_result()
        r = compute_regime_half_life(adaptive, RegimeType.STABLE, config=_regime_config())
        assert r.regime_multiplier == 1.5

    def test_result_has_volatility(self) -> None:
        adaptive = _adaptive_result(volatility=0.3)
        r = compute_regime_half_life(adaptive, RegimeType.STABLE, config=_regime_config())
        assert r.volatility == 0.3

    def test_result_applied(self) -> None:
        adaptive = _adaptive_result()
        r = compute_regime_half_life(adaptive, RegimeType.STABLE, config=_regime_config())
        assert r.applied

    def test_to_dict(self) -> None:
        adaptive = _adaptive_result()
        r = compute_regime_half_life(adaptive, RegimeType.STABLE, config=_regime_config())
        d = r.to_dict()
        expected = {
            "final_half_life",
            "base_half_life",
            "volatility_half_life",
            "regime_multiplier",
            "regime",
            "regime_category",
            "volatility",
            "applied",
            "reason_if_not_applied",
        }
        assert set(d.keys()) == expected

    def test_default_config_disabled(self) -> None:
        r = compute_regime_half_life(regime_type=RegimeType.STABLE)
        assert not r.applied

    def test_label_override(self) -> None:
        adaptive = _adaptive_result(computed=100)
        r = compute_regime_half_life(adaptive, regime_label="chaos", config=_regime_config())
        assert r.regime_category == "chaos"
        assert r.regime == "chaos"


# ═══════════════════════════════════════════════════════════════
# SECTION 5: Invariant tests (363-372)
# ═══════════════════════════════════════════════════════════════


class TestInvariant363Multiplicative:
    """Inv 363: Regime modifies half-life multiplicatively."""

    def test_multiplier_applied(self) -> None:
        adaptive = _adaptive_result(computed=100)
        for rt, expected_mult in [
            (RegimeType.STABLE, 1.5),
            (RegimeType.TREND_UP, 1.0),
            (RegimeType.SPIKE_UP, 0.6),
        ]:
            cfg = _regime_config(max_half_life=500)
            r = compute_regime_half_life(adaptive, rt, config=cfg)
            expected = int(round(100 * expected_mult))
            assert r.final_half_life == expected, f"regime={rt.value}"

    def test_chaos_multiplier(self) -> None:
        adaptive = _adaptive_result(computed=100)
        cfg = _regime_config(max_half_life=500)
        r = compute_regime_half_life(adaptive, regime_label="chaos", config=cfg)
        assert r.final_half_life == int(round(100 * 0.4))


class TestInvariant364Ordering:
    """Inv 364: STABLE >= TREND >= SPIKE >= CHAOS memory."""

    def test_ordering_with_same_adaptive(self) -> None:
        adaptive = _adaptive_result(computed=100)
        cfg = _regime_config(max_half_life=500)
        hls = {}
        for label in ["stable", "trend", "spike", "chaos"]:
            r = compute_regime_half_life(adaptive, regime_label=label, config=cfg)
            hls[label] = r.final_half_life
        assert hls["stable"] >= hls["trend"]
        assert hls["trend"] >= hls["spike"]
        assert hls["spike"] >= hls["chaos"]

    def test_ordering_multiple_bases(self) -> None:
        for base in [50, 100, 150]:
            adaptive = _adaptive_result(computed=base)
            cfg = _regime_config(max_half_life=1000)
            prev_hl = None
            for label in ["stable", "trend", "spike", "chaos"]:
                r = compute_regime_half_life(adaptive, regime_label=label, config=cfg)
                if prev_hl is not None:
                    assert r.final_half_life <= prev_hl
                prev_hl = r.final_half_life


class TestInvariant365NoNegativeOrZero:
    """Inv 365: No regime produces negative or zero half-life."""

    def test_all_regimes_positive(self) -> None:
        for rt in RegimeType:
            r = compute_regime_half_life(_adaptive_result(computed=10), rt, config=_regime_config())
            assert r.final_half_life > 0

    def test_chaos_positive(self) -> None:
        r = compute_regime_half_life(
            _adaptive_result(computed=10), regime_label="chaos", config=_regime_config()
        )
        assert r.final_half_life > 0

    def test_very_small_adaptive_positive(self) -> None:
        adaptive = _adaptive_result(computed=1)
        for label in ["stable", "trend", "spike", "chaos"]:
            r = compute_regime_half_life(
                adaptive, regime_label=label, config=_regime_config(min_half_life=1)
            )
            assert r.final_half_life >= 1


class TestInvariant366Deterministic:
    """Inv 366: Deterministic."""

    def test_repeat_identical(self) -> None:
        adaptive = _adaptive_result()
        cfg = _regime_config()
        r1 = compute_regime_half_life(adaptive, RegimeType.STABLE, config=cfg)
        r2 = compute_regime_half_life(adaptive, RegimeType.STABLE, config=cfg)
        assert r1.final_half_life == r2.final_half_life
        assert r1.regime_multiplier == r2.regime_multiplier

    def test_hundred_repeats(self) -> None:
        adaptive = _adaptive_result()
        cfg = _regime_config()
        ref = compute_regime_half_life(adaptive, RegimeType.SPIKE_UP, config=cfg)
        for _ in range(100):
            r = compute_regime_half_life(adaptive, RegimeType.SPIKE_UP, config=cfg)
            assert r.final_half_life == ref.final_half_life

    def test_temporal_integration_deterministic(self) -> None:
        regime = RegimeHalfLifeResult(
            final_half_life=75,
            base_half_life=50,
            volatility_half_life=80,
            regime_multiplier=0.94,
            applied=True,
        )
        cfg = _temporal_config()
        args = ([0.8, 0.6], ["a", "b"], [10, 50], [1.0, 1.0])
        r1 = apply_temporal_weights(*args, config=cfg, regime_result=regime)
        r2 = apply_temporal_weights(*args, config=cfg, regime_result=regime)
        assert r1.weights == r2.weights


class TestInvariant367NoMutation:
    """Inv 367: No mutation of past records."""

    def test_adaptive_result_unchanged(self) -> None:
        adaptive = _adaptive_result(computed=80)
        original_hl = adaptive.computed_half_life
        original_vol = adaptive.volatility
        compute_regime_half_life(adaptive, RegimeType.STABLE, config=_regime_config())
        assert adaptive.computed_half_life == original_hl
        assert adaptive.volatility == original_vol

    def test_pattern_memory_unchanged(self) -> None:
        mem = PatternMemory()
        k = _key()
        for i in range(10):
            mem.append(PatternRecord(key=k, outcome_score=0.5, timestamp=i))
        initial_size = mem.size
        compute_regime_half_life(_adaptive_result(), RegimeType.STABLE, config=_regime_config())
        assert mem.size == initial_size


class TestInvariant368NoFeedbackCoupling:
    """Inv 368: No feedback coupling."""

    def test_regime_independent_of_scores(self) -> None:
        a1 = _adaptive_result(computed=80, volatility=0.2)
        a2 = _adaptive_result(computed=80, volatility=0.2)
        cfg = _regime_config()
        r1 = compute_regime_half_life(a1, RegimeType.STABLE, config=cfg)
        r2 = compute_regime_half_life(a2, RegimeType.STABLE, config=cfg)
        assert r1.final_half_life == r2.final_half_life


class TestInvariant369MissingRegime:
    """Inv 369: Missing regime → neutral."""

    def test_none_regime(self) -> None:
        adaptive = _adaptive_result(computed=80)
        r = compute_regime_half_life(adaptive, config=_regime_config())
        assert r.regime_multiplier == 1.0

    def test_unknown_label(self) -> None:
        adaptive = _adaptive_result(computed=80)
        r = compute_regime_half_life(
            adaptive, regime_label="unknown_regime", config=_regime_config()
        )
        assert r.regime_multiplier == 1.0

    def test_empty_label(self) -> None:
        adaptive = _adaptive_result(computed=80)
        r = compute_regime_half_life(adaptive, regime_label="", config=_regime_config())
        assert r.regime_multiplier == 1.0


class TestInvariant370Explainable:
    """Inv 370: Fully explainable per step."""

    def test_result_has_all_fields(self) -> None:
        adaptive = _adaptive_result(computed=80, volatility=0.25)
        r = compute_regime_half_life(adaptive, RegimeType.STABLE, config=_regime_config())
        assert r.applied
        assert r.base_half_life == 50
        assert r.volatility_half_life == 80
        assert r.regime_multiplier == 1.5
        assert r.regime == "stable"
        assert r.regime_category == "stable"
        assert r.volatility == 0.25
        assert r.final_half_life > 0

    def test_disabled_has_reason(self) -> None:
        r = compute_regime_half_life(config=RegimeHalfLifeConfig(enabled=False))
        assert "disabled" in r.reason_if_not_applied


class TestInvariant371SmoothTransitions:
    """Inv 371: Smooth transitions across regime switches."""

    def test_stable_to_trend_bounded_change(self) -> None:
        adaptive = _adaptive_result(computed=80)
        cfg = _regime_config()
        r_stable = compute_regime_half_life(adaptive, RegimeType.STABLE, config=cfg)
        r_trend = compute_regime_half_life(adaptive, RegimeType.TREND_UP, config=cfg)
        ratio = r_stable.final_half_life / max(1, r_trend.final_half_life)
        assert ratio <= 2.0

    def test_trend_to_spike_bounded_change(self) -> None:
        adaptive = _adaptive_result(computed=80)
        cfg = _regime_config()
        r_trend = compute_regime_half_life(adaptive, RegimeType.TREND_UP, config=cfg)
        r_spike = compute_regime_half_life(adaptive, RegimeType.SPIKE_UP, config=cfg)
        ratio = r_trend.final_half_life / max(1, r_spike.final_half_life)
        assert ratio <= 2.0

    def test_spike_to_chaos_bounded_change(self) -> None:
        adaptive = _adaptive_result(computed=80)
        cfg = _regime_config()
        r_spike = compute_regime_half_life(adaptive, RegimeType.SPIKE_UP, config=cfg)
        r_chaos = compute_regime_half_life(adaptive, regime_label="chaos", config=cfg)
        ratio = r_spike.final_half_life / max(1, r_chaos.final_half_life)
        assert ratio <= 2.0

    def test_no_adjacent_regime_ratio_exceeds_two(self) -> None:
        adaptive = _adaptive_result(computed=100)
        cfg = _regime_config(max_half_life=1000)
        labels = ["stable", "trend", "spike", "chaos"]
        hls = []
        for label in labels:
            r = compute_regime_half_life(adaptive, regime_label=label, config=cfg)
            hls.append(r.final_half_life)
        for i in range(len(hls) - 1):
            ratio = hls[i] / max(1, hls[i + 1])
            assert ratio <= 2.0, f"{labels[i]} to {labels[i + 1]}: ratio={ratio}"


class TestInvariant372Bounded:
    """Inv 372: Bounded output."""

    def test_within_bounds_all_regimes(self) -> None:
        adaptive = _adaptive_result(computed=100)
        cfg = _regime_config(min_half_life=10, max_half_life=200)
        for rt in RegimeType:
            r = compute_regime_half_life(adaptive, rt, config=cfg)
            assert 10 <= r.final_half_life <= 200

    def test_chaos_respects_min(self) -> None:
        adaptive = _adaptive_result(computed=10)
        cfg = _regime_config(min_half_life=5)
        r = compute_regime_half_life(adaptive, regime_label="chaos", config=cfg)
        assert r.final_half_life >= 5

    def test_stable_respects_max(self) -> None:
        adaptive = _adaptive_result(computed=200)
        cfg = _regime_config(max_half_life=250)
        r = compute_regime_half_life(adaptive, RegimeType.STABLE, config=cfg)
        assert r.final_half_life <= 250

    def test_extreme_multiplier_bounded(self) -> None:
        mults = {
            RegimeCategory.STABLE: 10.0,
            RegimeCategory.TREND: 1.0,
            RegimeCategory.SPIKE: 0.01,
            RegimeCategory.CHAOS: 0.01,
        }
        cfg = _regime_config(regime_multipliers=mults, min_half_life=5, max_half_life=500)
        adaptive = _adaptive_result(computed=100)
        for label in ["stable", "chaos"]:
            r = compute_regime_half_life(adaptive, regime_label=label, config=cfg)
            assert 5 <= r.final_half_life <= 500


# ═══════════════════════════════════════════════════════════════
# SECTION 6: Integration with apply_temporal_weights
# ═══════════════════════════════════════════════════════════════


class TestTemporalIntegration:
    """Tests for regime half-life integration into temporal weighting."""

    def test_regime_overrides_adaptive(self) -> None:
        adaptive = _adaptive_result(computed=80)
        regime = RegimeHalfLifeResult(
            final_half_life=120,
            base_half_life=50,
            volatility_half_life=80,
            regime_multiplier=1.5,
            applied=True,
        )
        cfg = _temporal_config(half_life=50)
        r = apply_temporal_weights(
            [0.8], ["a"], [50], [1.0], config=cfg, adaptive_result=adaptive, regime_result=regime
        )
        assert r.effective_half_life == 120
        assert r.regime_applied

    def test_regime_not_applied_falls_to_adaptive(self) -> None:
        adaptive = _adaptive_result(computed=80)
        regime = RegimeHalfLifeResult(final_half_life=120, base_half_life=50, applied=False)
        cfg = _temporal_config(half_life=50)
        r = apply_temporal_weights(
            [0.8], ["a"], [50], [1.0], config=cfg, adaptive_result=adaptive, regime_result=regime
        )
        assert r.effective_half_life == 80
        assert r.adaptive_applied
        assert not r.regime_applied

    def test_no_regime_no_adaptive_uses_config(self) -> None:
        cfg = _temporal_config(half_life=50)
        r = apply_temporal_weights([0.8], ["a"], [50], [1.0], config=cfg)
        assert r.effective_half_life == 50
        assert not r.adaptive_applied
        assert not r.regime_applied

    def test_regime_stable_slower_decay(self) -> None:
        cfg = _temporal_config(half_life=50)
        regime_stable = RegimeHalfLifeResult(
            final_half_life=150,
            base_half_life=50,
            volatility_half_life=100,
            regime_multiplier=1.5,
            applied=True,
        )
        regime_spike = RegimeHalfLifeResult(
            final_half_life=30,
            base_half_life=50,
            volatility_half_life=50,
            regime_multiplier=0.6,
            applied=True,
        )
        r_stable = apply_temporal_weights(
            [0.8], ["a"], [100], [1.0], config=cfg, regime_result=regime_stable
        )
        r_spike = apply_temporal_weights(
            [0.8], ["a"], [100], [1.0], config=cfg, regime_result=regime_spike
        )
        assert r_stable.weights[0] > r_spike.weights[0]

    def test_regime_applied_flag_in_to_dict(self) -> None:
        cfg = _temporal_config()
        r = apply_temporal_weights([0.8], ["a"], [0], [1.0], config=cfg)
        d = r.to_dict()
        assert "regime_applied" in d

    def test_multiple_patterns_regime(self) -> None:
        regime = RegimeHalfLifeResult(
            final_half_life=75,
            base_half_life=50,
            volatility_half_life=80,
            regime_multiplier=0.94,
            applied=True,
        )
        cfg = _temporal_config()
        r = apply_temporal_weights(
            [0.8, 0.6, 0.4],
            ["a", "b", "c"],
            [0, 50, 100],
            [1.0, 1.0, 1.0],
            config=cfg,
            regime_result=regime,
        )
        assert r.regime_applied
        assert len(r.weights) == 3


# ═══════════════════════════════════════════════════════════════
# SECTION 7: RegimeHalfLifeResult dataclass tests
# ═══════════════════════════════════════════════════════════════


class TestRegimeHalfLifeResult:
    """Tests for the result dataclass."""

    def test_defaults(self) -> None:
        r = RegimeHalfLifeResult()
        assert r.final_half_life == 50
        assert r.base_half_life == 50
        assert r.volatility_half_life == 50
        assert r.regime_multiplier == 1.0
        assert r.regime == ""
        assert r.regime_category == ""
        assert r.volatility == 0.0
        assert not r.applied

    def test_frozen(self) -> None:
        r = RegimeHalfLifeResult()
        try:
            r.applied = True  # type: ignore[misc]
            assert False
        except AttributeError:
            pass

    def test_to_dict_roundtrip(self) -> None:
        r = RegimeHalfLifeResult(
            final_half_life=75,
            regime="spike_up",
            regime_category="spike",
            regime_multiplier=0.6,
            applied=True,
        )
        d = r.to_dict()
        assert d["final_half_life"] == 75
        assert d["regime"] == "spike_up"
        assert d["regime_category"] == "spike"


# ═══════════════════════════════════════════════════════════════
# SECTION 8: End-to-end pipeline
# ═══════════════════════════════════════════════════════════════


class TestEndToEnd:
    """End-to-end: adaptive → regime → temporal weights."""

    def test_stable_regime_longer_memory(self) -> None:
        adaptive = _adaptive_result(computed=80)
        regime = compute_regime_half_life(adaptive, RegimeType.STABLE, config=_regime_config())
        cfg = _temporal_config()
        r = apply_temporal_weights([0.8], ["a"], [100], [1.0], config=cfg, regime_result=regime)
        r_base = apply_temporal_weights([0.8], ["a"], [100], [1.0], config=cfg)
        assert r.weights[0] > r_base.weights[0]

    def test_spike_regime_shorter_memory(self) -> None:
        adaptive = _adaptive_result(computed=80)
        regime = compute_regime_half_life(adaptive, RegimeType.SPIKE_UP, config=_regime_config())
        cfg = _temporal_config()
        r = apply_temporal_weights([0.8], ["a"], [100], [1.0], config=cfg, regime_result=regime)
        r_base = apply_temporal_weights(
            [0.8], ["a"], [100], [1.0], config=cfg, adaptive_result=adaptive
        )
        assert r.weights[0] < r_base.weights[0]

    def test_full_pipeline_deterministic(self) -> None:
        adaptive = _adaptive_result()
        regime = compute_regime_half_life(adaptive, RegimeType.STABLE, config=_regime_config())
        cfg = _temporal_config()
        r1 = apply_temporal_weights(
            [0.5, 0.3], ["a", "b"], [10, 50], [0.9, 0.8], config=cfg, regime_result=regime
        )
        r2 = apply_temporal_weights(
            [0.5, 0.3], ["a", "b"], [10, 50], [0.9, 0.8], config=cfg, regime_result=regime
        )
        assert r1.weights == r2.weights

    def test_all_regimes_different_weights(self) -> None:
        adaptive = _adaptive_result(computed=100)
        cfg_t = _temporal_config()
        cfg_r = _regime_config(max_half_life=500)
        weights_by_regime = {}
        for label in ["stable", "trend", "spike", "chaos"]:
            regime = compute_regime_half_life(adaptive, regime_label=label, config=cfg_r)
            r = apply_temporal_weights(
                [0.8], ["a"], [100], [1.0], config=cfg_t, regime_result=regime
            )
            weights_by_regime[label] = r.weights[0]
        assert weights_by_regime["stable"] >= weights_by_regime["trend"]
        assert weights_by_regime["trend"] >= weights_by_regime["spike"]
        assert weights_by_regime["spike"] >= weights_by_regime["chaos"]


# ═══════════════════════════════════════════════════════════════
# SECTION 9: Multiplier sweep
# ═══════════════════════════════════════════════════════════════


class TestMultiplierSweep:
    """Systematic tests across multiplier values."""

    def test_multiplier_one_neutral(self) -> None:
        mults = {c: 1.0 for c in RegimeCategory}
        cfg = _regime_config(regime_multipliers=mults)
        adaptive = _adaptive_result(computed=80)
        for rt in RegimeType:
            r = compute_regime_half_life(adaptive, rt, config=cfg)
            assert r.final_half_life == 80

    def test_all_multipliers_equal(self) -> None:
        mults = {c: 1.5 for c in RegimeCategory}
        cfg = _regime_config(regime_multipliers=mults, max_half_life=500)
        adaptive = _adaptive_result(computed=100)
        results = []
        for label in ["stable", "trend", "spike", "chaos"]:
            r = compute_regime_half_life(adaptive, regime_label=label, config=cfg)
            results.append(r.final_half_life)
        assert all(hl == results[0] for hl in results)

    def test_increasing_multipliers(self) -> None:
        for mult in [0.2, 0.5, 1.0, 1.5, 2.0, 3.0]:
            mults = {c: mult for c in RegimeCategory}
            cfg = _regime_config(regime_multipliers=mults, min_half_life=1, max_half_life=1000)
            adaptive = _adaptive_result(computed=100)
            r = compute_regime_half_life(adaptive, RegimeType.STABLE, config=cfg)
            assert r.final_half_life == max(1, min(1000, int(round(100 * mult))))


# ═══════════════════════════════════════════════════════════════
# SECTION 10: Edge cases
# ═══════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Edge cases for regime half-life."""

    def test_min_equals_max(self) -> None:
        cfg = _regime_config(min_half_life=50, max_half_life=50)
        r = compute_regime_half_life(_adaptive_result(), RegimeType.STABLE, config=cfg)
        assert r.final_half_life == 50

    def test_very_small_multiplier(self) -> None:
        mults = {c: 0.01 for c in RegimeCategory}
        cfg = _regime_config(regime_multipliers=mults, min_half_life=1)
        r = compute_regime_half_life(_adaptive_result(computed=10), RegimeType.STABLE, config=cfg)
        assert r.final_half_life >= 1

    def test_very_large_multiplier(self) -> None:
        mults = {c: 10.0 for c in RegimeCategory}
        cfg = _regime_config(regime_multipliers=mults, max_half_life=500)
        r = compute_regime_half_life(_adaptive_result(computed=100), RegimeType.STABLE, config=cfg)
        assert r.final_half_life <= 500

    def test_adaptive_computed_one(self) -> None:
        adaptive = _adaptive_result(computed=1)
        cfg = _regime_config(min_half_life=1)
        r = compute_regime_half_life(adaptive, RegimeType.STABLE, config=cfg)
        assert r.final_half_life >= 1

    def test_label_with_whitespace(self) -> None:
        r = compute_regime_half_life(
            _adaptive_result(), regime_label="  stable  ", config=_regime_config()
        )
        assert r.regime_category == "stable"


# ═══════════════════════════════════════════════════════════════
# SECTION 11: Import and module structure tests
# ═══════════════════════════════════════════════════════════════


class TestImports:
    """Verify clean imports from the public API."""

    def test_import_from_regime_half_life(self) -> None:
        from umh.runtime.regime_half_life import (
            RegimeCategory,
            RegimeHalfLifeConfig,
            RegimeHalfLifeResult,
            classify_regime_category,
            compute_regime_half_life,
        )

        assert callable(compute_regime_half_life)
        assert callable(classify_regime_category)

    def test_import_from_runtime_init(self) -> None:
        from umh.runtime import (
            RegimeCategory,
            RegimeHalfLifeConfig,
            RegimeHalfLifeResult,
            classify_regime_category,
            compute_regime_half_life,
        )

        assert callable(compute_regime_half_life)

    def test_temporal_result_has_regime_applied(self) -> None:
        r = TemporalWeightingResult()
        assert hasattr(r, "regime_applied")


# ═══════════════════════════════════════════════════════════════
# SECTION 12: Backward compatibility — Phase 70/71 unchanged
# ═══════════════════════════════════════════════════════════════


class TestBackwardCompat:
    """Ensure Phase 70/71 behavior unchanged when regime is off."""

    def test_no_regime_arg(self) -> None:
        cfg = _temporal_config(half_life=50)
        r = apply_temporal_weights([0.8], ["a"], [50], [1.0], config=cfg)
        assert r.applied
        assert abs(r.weights[0] - 0.4) < 1e-10
        assert not r.regime_applied
        assert r.effective_half_life == 50

    def test_adaptive_only(self) -> None:
        cfg = _temporal_config(half_life=50)
        adaptive = _adaptive_result(computed=100)
        r = apply_temporal_weights([0.8], ["a"], [50], [1.0], config=cfg, adaptive_result=adaptive)
        assert r.adaptive_applied
        assert not r.regime_applied
        assert r.effective_half_life == 100

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

    def test_temporal_result_default_regime(self) -> None:
        r = TemporalWeightingResult()
        assert r.regime_applied is False


# ═══════════════════════════════════════════════════════════════
# SECTION 13: Phase 69/70/71 regression guard
# ═══════════════════════════════════════════════════════════════


class TestRegression:
    """Ensure Phase 69-71 behaviors still work."""

    def test_aggregation_without_temporal(self) -> None:
        pr = _multi_pattern_result()
        r = compute_pattern_aggregation(pr, baseline_score=0.5, config=_enabled_config())
        assert r.applied
        assert not r.temporal_applied

    def test_aggregation_with_temporal(self) -> None:
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

    def test_dominance_cap_enforced(self) -> None:
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

    def test_adaptive_half_life_still_works(self) -> None:
        from umh.runtime.adaptive_half_life import (
            compute_adaptive_half_life,
            AdaptiveHalfLifeConfig,
        )

        r = compute_adaptive_half_life(
            [0.8] * 20,
            config=AdaptiveHalfLifeConfig(enabled=True, base_half_life=50),
        )
        assert r.applied
        assert r.computed_half_life >= 50


# ═══════════════════════════════════════════════════════════════
# SECTION 14: TemporalWeightingResult new field tests
# ═══════════════════════════════════════════════════════════════


class TestTemporalResultNewField:
    """Tests for regime_applied field on TemporalWeightingResult."""

    def test_default_false(self) -> None:
        r = TemporalWeightingResult()
        assert r.regime_applied is False

    def test_set_true(self) -> None:
        r = TemporalWeightingResult(regime_applied=True)
        assert r.regime_applied is True

    def test_to_dict_includes_regime_applied(self) -> None:
        r = TemporalWeightingResult(regime_applied=True)
        d = r.to_dict()
        assert d["regime_applied"] is True

    def test_frozen(self) -> None:
        r = TemporalWeightingResult()
        try:
            r.regime_applied = True  # type: ignore[misc]
            assert False
        except AttributeError:
            pass


# ═══════════════════════════════════════════════════════════════
# SECTION 15: Parameter sweep
# ═══════════════════════════════════════════════════════════════


class TestParameterSweep:
    """Sweep across combinations of parameters."""

    def test_base_half_life_sweep(self) -> None:
        for base in [10, 25, 50, 100]:
            cfg = _regime_config(base_half_life=base, max_half_life=1000)
            for rt in RegimeType:
                r = compute_regime_half_life(_adaptive_result(computed=base), rt, config=cfg)
                assert r.final_half_life > 0

    def test_adaptive_sweep(self) -> None:
        cfg = _regime_config(max_half_life=1000)
        for computed in [10, 50, 100, 200]:
            adaptive = _adaptive_result(computed=computed)
            r = compute_regime_half_life(adaptive, RegimeType.STABLE, config=cfg)
            assert r.final_half_life == int(round(computed * 1.5))

    def test_bounds_sweep(self) -> None:
        for mn, mx in [(1, 10), (10, 50), (50, 200), (100, 500)]:
            cfg = _regime_config(min_half_life=mn, max_half_life=mx)
            for label in ["stable", "trend", "spike", "chaos"]:
                r = compute_regime_half_life(
                    _adaptive_result(computed=100), regime_label=label, config=cfg
                )
                assert mn <= r.final_half_life <= mx
