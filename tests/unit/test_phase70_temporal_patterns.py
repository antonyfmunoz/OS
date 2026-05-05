"""Phase 70 — Temporal Pattern Weighting Layer v1 tests.

Tests exponential decay for pattern age, floor enforcement, normalization,
dominance cap interaction, determinism, isolation, and explainability.
Covers invariants 344-352.
"""

import sys
import math

sys.path.insert(0, "/opt/OS")

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
    _apply_dominance_cap,
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

LN2 = math.log(2.0)


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


# ═══════════════════════════════════════════════════════════════
# SECTION 1: compute_decay_factor unit tests
# ═══════════════════════════════════════════════════════════════


class TestDecayFactor:
    """Tests for the core decay function (inv 344)."""

    def test_age_zero_returns_one(self) -> None:
        assert compute_decay_factor(0, 50) == 1.0

    def test_negative_age_returns_one(self) -> None:
        assert compute_decay_factor(-10, 50) == 1.0

    def test_half_life_gives_half(self) -> None:
        result = compute_decay_factor(50, 50)
        assert abs(result - 0.5) < 1e-10

    def test_double_half_life_gives_quarter(self) -> None:
        result = compute_decay_factor(100, 50)
        assert abs(result - 0.25) < 1e-10

    def test_triple_half_life(self) -> None:
        result = compute_decay_factor(150, 50)
        assert abs(result - 0.125) < 1e-10

    def test_decay_bounded_zero_one(self) -> None:
        for age in [0, 1, 10, 50, 100, 500, 1000, 10000]:
            d = compute_decay_factor(age, 50)
            assert 0.0 <= d <= 1.0, f"age={age}, decay={d}"

    def test_monotonically_decreasing(self) -> None:
        prev = 1.0
        for age in range(1, 200):
            d = compute_decay_factor(age, 50)
            assert d <= prev, f"age={age}"
            prev = d

    def test_never_reaches_zero(self) -> None:
        d = compute_decay_factor(10000, 50)
        assert d > 0.0

    def test_very_large_age(self) -> None:
        d = compute_decay_factor(100000, 50)
        assert d >= 0.0

    def test_half_life_one(self) -> None:
        d = compute_decay_factor(1, 1)
        assert abs(d - 0.5) < 1e-10

    def test_half_life_zero_returns_one(self) -> None:
        d = compute_decay_factor(10, 0)
        assert d == 1.0

    def test_small_half_life(self) -> None:
        d = compute_decay_factor(10, 5)
        assert abs(d - 0.25) < 1e-10

    def test_large_half_life_slow_decay(self) -> None:
        d = compute_decay_factor(10, 1000)
        assert d > 0.99

    def test_deterministic_same_inputs(self) -> None:
        a = compute_decay_factor(42, 50)
        b = compute_decay_factor(42, 50)
        assert a == b

    def test_age_one(self) -> None:
        d = compute_decay_factor(1, 50)
        expected = math.exp(-LN2 / 50)
        assert abs(d - expected) < 1e-12

    def test_age_equals_half_life_various(self) -> None:
        for hl in [1, 5, 10, 25, 50, 100, 200]:
            d = compute_decay_factor(hl, hl)
            assert abs(d - 0.5) < 1e-10, f"half_life={hl}"


# ═══════════════════════════════════════════════════════════════
# SECTION 2: TemporalPatternConfig tests
# ═══════════════════════════════════════════════════════════════


class TestTemporalPatternConfig:
    """Config validation tests."""

    def test_defaults(self) -> None:
        c = TemporalPatternConfig()
        assert c.enabled is False
        assert c.half_life == 50
        assert c.min_weight == 0.05
        assert c.max_weight == 1.0

    def test_half_life_clamped_to_one(self) -> None:
        c = TemporalPatternConfig(half_life=0)
        assert c.half_life == 1

    def test_negative_half_life_clamped(self) -> None:
        c = TemporalPatternConfig(half_life=-10)
        assert c.half_life == 1

    def test_min_weight_clamped_low(self) -> None:
        c = TemporalPatternConfig(min_weight=-0.5)
        assert c.min_weight == 0.0

    def test_min_weight_clamped_high(self) -> None:
        c = TemporalPatternConfig(min_weight=2.0)
        assert c.min_weight == 1.0

    def test_max_weight_floors_to_min(self) -> None:
        c = TemporalPatternConfig(min_weight=0.3, max_weight=0.1)
        assert c.max_weight >= c.min_weight

    def test_to_dict_roundtrip(self) -> None:
        c = TemporalPatternConfig(enabled=True, half_life=25)
        d = c.to_dict()
        assert d["enabled"] is True
        assert d["half_life"] == 25

    def test_frozen(self) -> None:
        c = TemporalPatternConfig()
        try:
            c.enabled = True  # type: ignore[misc]
            assert False, "should be frozen"
        except AttributeError:
            pass

    def test_custom_values(self) -> None:
        c = TemporalPatternConfig(enabled=True, half_life=100, min_weight=0.1, max_weight=0.9)
        assert c.half_life == 100
        assert c.min_weight == 0.1
        assert c.max_weight == 0.9


# ═══════════════════════════════════════════════════════════════
# SECTION 3: apply_temporal_weights unit tests
# ═══════════════════════════════════════════════════════════════


class TestApplyTemporalWeights:
    """Tests for the temporal weight application layer."""

    def test_disabled_returns_original(self) -> None:
        cfg = TemporalPatternConfig(enabled=False)
        r = apply_temporal_weights([0.5, 0.3], ["a", "b"], [10, 20], [0.9, 0.8], config=cfg)
        assert not r.applied
        assert r.weights == (0.5, 0.3)
        assert "disabled" in r.reason_if_not_applied

    def test_empty_patterns(self) -> None:
        cfg = _temporal_config()
        r = apply_temporal_weights([], [], [], [], config=cfg)
        assert not r.applied
        assert r.weights == ()

    def test_length_mismatch_keys(self) -> None:
        cfg = _temporal_config()
        r = apply_temporal_weights([0.5], ["a", "b"], [10], [0.9], config=cfg)
        assert not r.applied

    def test_length_mismatch_ages(self) -> None:
        cfg = _temporal_config()
        r = apply_temporal_weights([0.5], ["a"], [10, 20], [0.9], config=cfg)
        assert not r.applied

    def test_length_mismatch_similarities(self) -> None:
        cfg = _temporal_config()
        r = apply_temporal_weights([0.5], ["a"], [10], [0.9, 0.8], config=cfg)
        assert not r.applied

    def test_recent_pattern_full_weight(self) -> None:
        cfg = _temporal_config()
        r = apply_temporal_weights([0.8], ["a"], [0], [1.0], config=cfg)
        assert r.applied
        assert abs(r.weights[0] - 0.8) < 1e-10

    def test_older_pattern_decayed(self) -> None:
        cfg = _temporal_config(half_life=50)
        r = apply_temporal_weights([0.8], ["a"], [50], [1.0], config=cfg)
        assert r.applied
        assert abs(r.weights[0] - 0.4) < 1e-10

    def test_newer_greater_than_older(self) -> None:
        cfg = _temporal_config(half_life=50)
        r = apply_temporal_weights([0.8, 0.8], ["a", "b"], [10, 100], [1.0, 1.0], config=cfg)
        assert r.applied
        assert r.weights[0] > r.weights[1]

    def test_equal_age_equal_weights(self) -> None:
        cfg = _temporal_config(half_life=50)
        r = apply_temporal_weights([0.8, 0.8], ["a", "b"], [30, 30], [1.0, 1.0], config=cfg)
        assert r.applied
        assert abs(r.weights[0] - r.weights[1]) < 1e-12

    def test_floor_prevents_zeroing(self) -> None:
        cfg = _temporal_config(half_life=5, min_weight=0.05)
        r = apply_temporal_weights([0.001], ["a"], [10000], [0.9], config=cfg)
        assert r.applied
        floor = 0.05 * 0.9
        assert r.weights[0] >= floor - 1e-12

    def test_floor_with_zero_similarity(self) -> None:
        cfg = _temporal_config(half_life=5, min_weight=0.05)
        r = apply_temporal_weights([0.001], ["a"], [10000], [0.0], config=cfg)
        assert r.applied
        assert r.weights[0] >= 0.0

    def test_negative_age_treated_as_zero(self) -> None:
        cfg = _temporal_config()
        r = apply_temporal_weights([0.8], ["a"], [-5], [1.0], config=cfg)
        assert r.applied
        assert abs(r.weights[0] - 0.8) < 1e-10

    def test_contributions_populated(self) -> None:
        cfg = _temporal_config()
        r = apply_temporal_weights([0.5], ["k1"], [25], [0.9], config=cfg)
        assert len(r.contributions) == 1
        c = r.contributions[0]
        assert c.key == "k1"
        assert c.age == 25
        assert c.pre_decay_weight == 0.5

    def test_contributions_count_matches_patterns(self) -> None:
        cfg = _temporal_config()
        r = apply_temporal_weights(
            [0.5, 0.3, 0.2], ["a", "b", "c"], [10, 20, 30], [1.0, 0.9, 0.8], config=cfg
        )
        assert len(r.contributions) == 3

    def test_decay_factor_in_contributions(self) -> None:
        cfg = _temporal_config(half_life=50)
        r = apply_temporal_weights([0.8], ["a"], [50], [1.0], config=cfg)
        assert abs(r.contributions[0].decay_factor - 0.5) < 1e-10

    def test_five_patterns(self) -> None:
        cfg = _temporal_config()
        r = apply_temporal_weights(
            [0.5] * 5,
            [f"k{i}" for i in range(5)],
            [i * 10 for i in range(5)],
            [0.9] * 5,
            config=cfg,
        )
        assert r.applied
        assert len(r.weights) == 5

    def test_single_pattern(self) -> None:
        cfg = _temporal_config()
        r = apply_temporal_weights([0.8], ["a"], [0], [1.0], config=cfg)
        assert r.applied
        assert len(r.weights) == 1

    def test_to_dict(self) -> None:
        cfg = _temporal_config()
        r = apply_temporal_weights([0.5], ["a"], [25], [0.9], config=cfg)
        d = r.to_dict()
        assert "applied" in d
        assert "weights" in d
        assert "contributions" in d

    def test_default_config_disabled(self) -> None:
        r = apply_temporal_weights([0.5], ["a"], [10], [0.9])
        assert not r.applied


# ═══════════════════════════════════════════════════════════════
# SECTION 4: Integration with compute_pattern_aggregation
# ═══════════════════════════════════════════════════════════════


class TestTemporalAggregationIntegration:
    """Tests for temporal weighting integrated into pattern aggregation."""

    def test_temporal_disabled_by_default(self) -> None:
        pr = _multi_pattern_result()
        r = compute_pattern_aggregation(pr, baseline_score=0.5, config=_enabled_config())
        assert r.applied
        assert not r.temporal_applied

    def test_temporal_enabled_applies(self) -> None:
        k1 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k2 = _key(TrendDirection.DOWN, RiskLevel.HIGH, StabilityLevel.LOW, UrgencyLevel.HIGH)
        matches = [
            _match(similarity=1.0, key=k1, stats=_stats(key=k1, avg_score=0.8)),
            _match(similarity=0.75, key=k2, stats=_stats(key=k2, avg_score=0.7)),
        ]
        pr = _multi_pattern_result(matches)
        k1_str = str(k1.to_tuple())
        k2_str = str(k2.to_tuple())

        r = compute_pattern_aggregation(
            pr,
            baseline_score=0.5,
            config=_enabled_config(),
            temporal_config=_temporal_config(half_life=50),
            current_observation_index=100,
            pattern_last_seen={k1_str: 90, k2_str: 50},
        )
        assert r.applied
        assert r.temporal_applied

    def test_newer_pattern_dominates(self) -> None:
        k1 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k2 = _key(TrendDirection.DOWN, RiskLevel.HIGH, StabilityLevel.LOW, UrgencyLevel.HIGH)
        matches = [
            _match(similarity=1.0, key=k1, stats=_stats(key=k1, avg_score=0.8)),
            _match(similarity=1.0, key=k2, stats=_stats(key=k2, avg_score=0.8)),
        ]
        pr = _multi_pattern_result(matches)
        k1_str = str(k1.to_tuple())
        k2_str = str(k2.to_tuple())

        r = compute_pattern_aggregation(
            pr,
            baseline_score=0.5,
            config=_enabled_config(),
            temporal_config=_temporal_config(half_life=50),
            current_observation_index=100,
            pattern_last_seen={k1_str: 99, k2_str: 0},
        )
        assert r.applied
        c1 = [c for c in r.contributions if c.key == k1_str][0]
        c2 = [c for c in r.contributions if c.key == k2_str][0]
        assert c1.normalized_weight > c2.normalized_weight

    def test_without_temporal_args_backward_compat(self) -> None:
        pr = _multi_pattern_result()
        r = compute_pattern_aggregation(pr, baseline_score=0.5, config=_enabled_config())
        assert r.applied
        assert not r.temporal_applied

    def test_temporal_with_no_last_seen_defaults(self) -> None:
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

    def test_dominance_cap_after_temporal(self) -> None:
        k1 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k2 = _key(TrendDirection.DOWN, RiskLevel.HIGH, StabilityLevel.LOW, UrgencyLevel.HIGH)
        matches = [
            _match(similarity=1.0, key=k1, stats=_stats(key=k1, avg_score=0.8)),
            _match(similarity=0.5, key=k2, stats=_stats(key=k2, avg_score=0.7)),
        ]
        pr = _multi_pattern_result(matches)
        k1_str = str(k1.to_tuple())
        k2_str = str(k2.to_tuple())

        r = compute_pattern_aggregation(
            pr,
            baseline_score=0.5,
            config=_enabled_config(),
            temporal_config=_temporal_config(half_life=5),
            current_observation_index=100,
            pattern_last_seen={k1_str: 99, k2_str: 0},
        )
        assert r.applied
        for c in r.contributions:
            assert c.normalized_weight <= _DOMINANCE_CAP + 1e-10

    def test_max_five_patterns_still_enforced(self) -> None:
        keys = []
        matches = []
        for i in range(8):
            k = _key(
                TrendDirection.UP if i % 2 == 0 else TrendDirection.DOWN,
                RiskLevel.LOW if i < 4 else RiskLevel.HIGH,
                StabilityLevel.HIGH if i % 3 == 0 else StabilityLevel.MEDIUM,
                UrgencyLevel.LOW if i < 2 else UrgencyLevel.MEDIUM,
            )
            keys.append(k)
            matches.append(_match(similarity=max(0.5, 1.0 - i * 0.05), key=k, stats=_stats(key=k)))

        pr = _multi_pattern_result(matches)
        r = compute_pattern_aggregation(
            pr,
            baseline_score=0.5,
            config=_enabled_config(),
            temporal_config=_temporal_config(),
            current_observation_index=100,
        )
        assert r.patterns_used <= _MAX_PATTERNS

    def test_factor_bounded_with_temporal(self) -> None:
        pr = _multi_pattern_result()
        r = compute_pattern_aggregation(
            pr,
            baseline_score=0.5,
            config=_enabled_config(),
            temporal_config=_temporal_config(),
            current_observation_index=100,
        )
        assert _FACTOR_FLOOR <= r.final_factor <= _FACTOR_CEILING

    def test_contribution_has_temporal_fields(self) -> None:
        k1 = _key()
        matches = [_match(similarity=1.0, key=k1)]
        pr = _multi_pattern_result(matches)
        k1_str = str(k1.to_tuple())

        r = compute_pattern_aggregation(
            pr,
            baseline_score=0.5,
            config=_enabled_config(),
            temporal_config=_temporal_config(half_life=50),
            current_observation_index=100,
            pattern_last_seen={k1_str: 50},
        )
        assert r.applied
        c = r.contributions[0]
        assert c.age == 50
        assert abs(c.decay_factor - 0.5) < 1e-10
        assert c.pre_decay_weight > 0

    def test_contribution_to_dict_has_temporal(self) -> None:
        k1 = _key()
        matches = [_match(similarity=1.0, key=k1)]
        pr = _multi_pattern_result(matches)
        k1_str = str(k1.to_tuple())

        r = compute_pattern_aggregation(
            pr,
            baseline_score=0.5,
            config=_enabled_config(),
            temporal_config=_temporal_config(),
            current_observation_index=50,
            pattern_last_seen={k1_str: 25},
        )
        d = r.contributions[0].to_dict()
        assert "age" in d
        assert "decay_factor" in d
        assert "pre_decay_weight" in d

    def test_result_to_dict_has_temporal_applied(self) -> None:
        pr = _multi_pattern_result()
        r = compute_pattern_aggregation(
            pr,
            baseline_score=0.5,
            config=_enabled_config(),
            temporal_config=_temporal_config(),
            current_observation_index=100,
        )
        d = r.to_dict()
        assert "temporal_applied" in d

    def test_weights_sum_to_one(self) -> None:
        k1 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k2 = _key(TrendDirection.DOWN, RiskLevel.HIGH, StabilityLevel.LOW, UrgencyLevel.HIGH)
        k3 = _key(
            TrendDirection.NEUTRAL, RiskLevel.MEDIUM, StabilityLevel.MEDIUM, UrgencyLevel.MEDIUM
        )
        matches = [
            _match(similarity=1.0, key=k1),
            _match(similarity=0.75, key=k2),
            _match(similarity=0.5, key=k3),
        ]
        pr = _multi_pattern_result(matches)

        r = compute_pattern_aggregation(
            pr,
            baseline_score=0.5,
            config=_enabled_config(),
            temporal_config=_temporal_config(),
            current_observation_index=100,
            pattern_last_seen={
                str(k1.to_tuple()): 90,
                str(k2.to_tuple()): 50,
                str(k3.to_tuple()): 10,
            },
        )
        total = sum(c.normalized_weight for c in r.contributions)
        assert abs(total - 1.0) < 1e-10


# ═══════════════════════════════════════════════════════════════
# SECTION 5: Invariant tests (344-352)
# ═══════════════════════════════════════════════════════════════


class TestInvariant344DecayBounded:
    """Inv 344: Temporal decay bounded [0, 1]."""

    def test_boundary_ages(self) -> None:
        for age in [0, 1, 5, 10, 50, 100, 500, 1000]:
            d = compute_decay_factor(age, 50)
            assert 0.0 <= d <= 1.0

    def test_extreme_half_life(self) -> None:
        for hl in [1, 2, 5, 10, 100, 1000]:
            d = compute_decay_factor(50, hl)
            assert 0.0 <= d <= 1.0

    def test_applied_weights_bounded(self) -> None:
        cfg = _temporal_config(half_life=50)
        r = apply_temporal_weights([1.0, 1.0], ["a", "b"], [0, 100], [1.0, 1.0], config=cfg)
        for w in r.weights:
            assert w >= 0.0


class TestInvariant345NoDeletion:
    """Inv 345: No hard deletion of patterns."""

    def test_very_old_pattern_survives(self) -> None:
        cfg = _temporal_config(half_life=5, min_weight=0.05)
        r = apply_temporal_weights([0.5], ["a"], [100000], [0.9], config=cfg)
        assert r.weights[0] > 0.0

    def test_pattern_memory_unchanged(self) -> None:
        mem = PatternMemory()
        k = _key()
        mem.append(PatternRecord(key=k, outcome_score=0.8, timestamp=0))
        mem.append(PatternRecord(key=k, outcome_score=0.9, timestamp=10))
        initial_size = mem.size
        initial_records = mem.get_records()

        cfg = _temporal_config()
        apply_temporal_weights([0.5], ["k"], [100], [1.0], config=cfg)

        assert mem.size == initial_size
        assert mem.get_records() == initial_records


class TestInvariant346NewerGeqOlder:
    """Inv 346: Newer patterns have >= weight than older (given equal stats)."""

    def test_newer_geq_older_single_pair(self) -> None:
        cfg = _temporal_config(half_life=50)
        r = apply_temporal_weights([0.8, 0.8], ["a", "b"], [10, 100], [1.0, 1.0], config=cfg)
        assert r.weights[0] >= r.weights[1]

    def test_newer_geq_older_five_patterns(self) -> None:
        cfg = _temporal_config(half_life=50)
        ages = [0, 25, 50, 75, 100]
        r = apply_temporal_weights(
            [0.8] * 5, [f"k{i}" for i in range(5)], ages, [1.0] * 5, config=cfg
        )
        for i in range(len(ages) - 1):
            assert r.weights[i] >= r.weights[i + 1]

    def test_same_age_same_weight(self) -> None:
        cfg = _temporal_config(half_life=50)
        r = apply_temporal_weights([0.8, 0.8], ["a", "b"], [42, 42], [1.0, 1.0], config=cfg)
        assert abs(r.weights[0] - r.weights[1]) < 1e-12


class TestInvariant347Deterministic:
    """Inv 347: Deterministic (no wall-clock time, use index)."""

    def test_repeat_identical(self) -> None:
        cfg = _temporal_config(half_life=50)
        args = ([0.5, 0.3], ["a", "b"], [10, 50], [0.9, 0.8])
        r1 = apply_temporal_weights(*args, config=cfg)
        r2 = apply_temporal_weights(*args, config=cfg)
        assert r1.weights == r2.weights

    def test_aggregation_deterministic(self) -> None:
        pr = _multi_pattern_result()
        kwargs = dict(
            baseline_score=0.5,
            config=_enabled_config(),
            temporal_config=_temporal_config(),
            current_observation_index=100,
        )
        r1 = compute_pattern_aggregation(pr, **kwargs)
        r2 = compute_pattern_aggregation(pr, **kwargs)
        assert r1.final_factor == r2.final_factor
        assert r1.temporal_applied == r2.temporal_applied

    def test_hundred_repeats(self) -> None:
        cfg = _temporal_config(half_life=50)
        args = ([0.8], ["a"], [25], [1.0])
        ref = apply_temporal_weights(*args, config=cfg)
        for _ in range(100):
            r = apply_temporal_weights(*args, config=cfg)
            assert r.weights == ref.weights


class TestInvariant348NoMutation:
    """Inv 348: No mutation of stored records."""

    def test_input_lists_unchanged(self) -> None:
        cfg = _temporal_config()
        rw = [0.5, 0.3]
        keys = ["a", "b"]
        ages = [10, 50]
        sims = [0.9, 0.8]
        rw_copy = list(rw)
        keys_copy = list(keys)
        ages_copy = list(ages)
        sims_copy = list(sims)

        apply_temporal_weights(rw, keys, ages, sims, config=cfg)

        assert rw == rw_copy
        assert keys == keys_copy
        assert ages == ages_copy
        assert sims == sims_copy

    def test_pattern_result_unchanged(self) -> None:
        pr = _multi_pattern_result()
        original_matches = pr.all_matches
        original_conf = pr.confidence

        compute_pattern_aggregation(
            pr,
            baseline_score=0.5,
            config=_enabled_config(),
            temporal_config=_temporal_config(),
            current_observation_index=100,
        )

        assert pr.all_matches == original_matches
        assert pr.confidence == original_conf


class TestInvariant349DecayIndependentOfScoring:
    """Inv 349: Decay independent of scoring."""

    def test_decay_same_regardless_of_raw_weight(self) -> None:
        cfg = _temporal_config(half_life=50)
        r1 = apply_temporal_weights([0.2], ["a"], [50], [1.0], config=cfg)
        r2 = apply_temporal_weights([0.8], ["a"], [50], [1.0], config=cfg)
        d1 = r1.contributions[0].decay_factor
        d2 = r2.contributions[0].decay_factor
        assert abs(d1 - d2) < 1e-12

    def test_decay_same_regardless_of_similarity(self) -> None:
        cfg = _temporal_config(half_life=50)
        r1 = apply_temporal_weights([0.5], ["a"], [50], [0.3], config=cfg)
        r2 = apply_temporal_weights([0.5], ["a"], [50], [0.9], config=cfg)
        d1 = r1.contributions[0].decay_factor
        d2 = r2.contributions[0].decay_factor
        assert abs(d1 - d2) < 1e-12


class TestInvariant350FloorPreventsZeroing:
    """Inv 350: Floor prevents zeroing."""

    def test_extreme_age_floored(self) -> None:
        cfg = _temporal_config(half_life=5, min_weight=0.05)
        r = apply_temporal_weights([0.001], ["a"], [100000], [0.9], config=cfg)
        assert r.weights[0] >= 0.05 * 0.9 - 1e-12

    def test_various_ages_floored(self) -> None:
        cfg = _temporal_config(half_life=10, min_weight=0.1)
        for age in [100, 500, 1000, 5000]:
            r = apply_temporal_weights([0.5], ["a"], [age], [0.8], config=cfg)
            assert r.weights[0] >= 0.1 * 0.8 - 1e-12

    def test_floor_with_low_similarity(self) -> None:
        cfg = _temporal_config(half_life=5, min_weight=0.05)
        r = apply_temporal_weights([0.1], ["a"], [10000], [0.1], config=cfg)
        assert r.weights[0] >= 0.05 * 0.1 - 1e-12

    def test_floor_zero_min_weight(self) -> None:
        cfg = _temporal_config(half_life=5, min_weight=0.0)
        r = apply_temporal_weights([0.001], ["a"], [100000], [0.9], config=cfg)
        assert r.weights[0] >= 0.0


class TestInvariant351Explainability:
    """Inv 351: Explainable decay contribution."""

    def test_contribution_has_all_fields(self) -> None:
        cfg = _temporal_config(half_life=50)
        r = apply_temporal_weights([0.5], ["k1"], [25], [0.9], config=cfg)
        c = r.contributions[0]
        assert c.key == "k1"
        assert c.age == 25
        assert 0 < c.decay_factor <= 1.0
        assert c.pre_decay_weight == 0.5
        assert c.final_weight > 0

    def test_contribution_to_dict(self) -> None:
        cfg = _temporal_config()
        r = apply_temporal_weights([0.5], ["k1"], [25], [0.9], config=cfg)
        d = r.contributions[0].to_dict()
        assert set(d.keys()) == {"key", "age", "decay_factor", "pre_decay_weight", "final_weight"}

    def test_aggregation_contributions_have_temporal(self) -> None:
        k1 = _key()
        matches = [_match(similarity=1.0, key=k1)]
        pr = _multi_pattern_result(matches)
        k1_str = str(k1.to_tuple())

        r = compute_pattern_aggregation(
            pr,
            baseline_score=0.5,
            config=_enabled_config(),
            temporal_config=_temporal_config(half_life=50),
            current_observation_index=100,
            pattern_last_seen={k1_str: 50},
        )
        c = r.contributions[0]
        d = c.to_dict()
        assert d["age"] == 50
        assert abs(d["decay_factor"] - 0.5) < 0.01


class TestInvariant352NoInstability:
    """Inv 352: No instability introduced."""

    def test_small_perturbation_small_output_change(self) -> None:
        cfg = _temporal_config(half_life=50)
        r1 = apply_temporal_weights([0.8], ["a"], [50], [1.0], config=cfg)
        r2 = apply_temporal_weights([0.8], ["a"], [51], [1.0], config=cfg)
        assert abs(r1.weights[0] - r2.weights[0]) < 0.02

    def test_continuous_age_sweep(self) -> None:
        cfg = _temporal_config(half_life=50)
        prev_w = None
        for age in range(0, 200):
            r = apply_temporal_weights([0.8], ["a"], [age], [1.0], config=cfg)
            w = r.weights[0]
            if prev_w is not None:
                assert abs(w - prev_w) < 0.02
            prev_w = w

    def test_aggregation_stable_across_ages(self) -> None:
        k1 = _key()
        matches = [_match(similarity=1.0, key=k1)]
        pr = _multi_pattern_result(matches)
        k1_str = str(k1.to_tuple())

        factors = []
        for idx in range(50, 150):
            r = compute_pattern_aggregation(
                pr,
                baseline_score=0.5,
                config=_enabled_config(),
                temporal_config=_temporal_config(),
                current_observation_index=idx,
                pattern_last_seen={k1_str: 50},
            )
            factors.append(r.final_factor)

        for i in range(len(factors) - 1):
            assert abs(factors[i] - factors[i + 1]) < 0.05


# ═══════════════════════════════════════════════════════════════
# SECTION 6: Half-life specific tests
# ═══════════════════════════════════════════════════════════════


class TestHalfLifeBehavior:
    """Detailed half-life verification."""

    def test_weight_halves_exactly(self) -> None:
        for hl in [10, 25, 50, 100]:
            d_0 = compute_decay_factor(0, hl)
            d_hl = compute_decay_factor(hl, hl)
            assert abs(d_hl / d_0 - 0.5) < 1e-10

    def test_two_half_lives_quarter(self) -> None:
        d = compute_decay_factor(100, 50)
        assert abs(d - 0.25) < 1e-10

    def test_half_life_proportional(self) -> None:
        d_short = compute_decay_factor(50, 25)
        d_long = compute_decay_factor(50, 100)
        assert d_short < d_long

    def test_effective_weight_at_half_life(self) -> None:
        cfg = _temporal_config(half_life=50)
        r = apply_temporal_weights([1.0], ["a"], [50], [1.0], config=cfg)
        assert abs(r.weights[0] - 0.5) < 1e-10


# ═══════════════════════════════════════════════════════════════
# SECTION 7: Edge cases
# ═══════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Edge cases for temporal weighting."""

    def test_all_same_age(self) -> None:
        cfg = _temporal_config(half_life=50)
        r = apply_temporal_weights(
            [0.5, 0.3, 0.2], ["a", "b", "c"], [30, 30, 30], [1.0, 1.0, 1.0], config=cfg
        )
        d = compute_decay_factor(30, 50)
        for i in range(3):
            expected = [0.5, 0.3, 0.2][i] * d
            assert abs(r.weights[i] - expected) < 1e-10

    def test_all_age_zero(self) -> None:
        cfg = _temporal_config()
        r = apply_temporal_weights([0.5, 0.3], ["a", "b"], [0, 0], [1.0, 1.0], config=cfg)
        assert r.weights == (0.5, 0.3)

    def test_very_small_raw_weight(self) -> None:
        cfg = _temporal_config(half_life=50, min_weight=0.05)
        r = apply_temporal_weights([0.001], ["a"], [0], [0.9], config=cfg)
        assert r.weights[0] >= 0.0

    def test_min_weight_equals_max_weight(self) -> None:
        cfg = _temporal_config(half_life=50, min_weight=0.5, max_weight=0.5)
        r = apply_temporal_weights([0.8], ["a"], [100], [1.0], config=cfg)
        assert r.applied

    def test_half_life_one_rapid_decay(self) -> None:
        cfg = _temporal_config(half_life=1, min_weight=0.0)
        r = apply_temporal_weights([0.8], ["a"], [10], [1.0], config=cfg)
        assert r.weights[0] < 0.01

    def test_observation_index_zero(self) -> None:
        k1 = _key()
        matches = [_match(similarity=1.0, key=k1)]
        pr = _multi_pattern_result(matches)

        r = compute_pattern_aggregation(
            pr,
            baseline_score=0.5,
            config=_enabled_config(),
            temporal_config=_temporal_config(),
            current_observation_index=0,
        )
        assert r.applied

    def test_last_seen_in_future(self) -> None:
        cfg = _temporal_config()
        r = apply_temporal_weights([0.8], ["a"], [-5], [1.0], config=cfg)
        assert r.weights[0] == 0.8

    def test_temporal_contribution_frozen(self) -> None:
        tc = TemporalContribution(key="k", age=10, decay_factor=0.5)
        try:
            tc.age = 20  # type: ignore[misc]
            assert False, "should be frozen"
        except AttributeError:
            pass


# ═══════════════════════════════════════════════════════════════
# SECTION 8: TemporalWeightingResult tests
# ═══════════════════════════════════════════════════════════════


class TestTemporalWeightingResult:
    """Tests for the result dataclass."""

    def test_defaults(self) -> None:
        r = TemporalWeightingResult()
        assert not r.applied
        assert r.weights == ()
        assert r.contributions == ()
        assert r.reason_if_not_applied == ""

    def test_to_dict(self) -> None:
        r = TemporalWeightingResult(applied=True, weights=(0.5, 0.3))
        d = r.to_dict()
        assert d["applied"] is True
        assert len(d["weights"]) == 2

    def test_frozen(self) -> None:
        r = TemporalWeightingResult()
        try:
            r.applied = True  # type: ignore[misc]
            assert False
        except AttributeError:
            pass


# ═══════════════════════════════════════════════════════════════
# SECTION 9: Backward compatibility — Phase 69 behavior preserved
# ═══════════════════════════════════════════════════════════════


class TestPhase69BackwardCompat:
    """Ensure Phase 69 behavior unchanged when temporal is off."""

    def test_no_temporal_args(self) -> None:
        pr = _multi_pattern_result()
        r = compute_pattern_aggregation(pr, baseline_score=0.5, config=_enabled_config())
        assert r.applied
        assert not r.temporal_applied
        assert r.final_factor != 1.0 or not r.applied

    def test_temporal_disabled_explicit(self) -> None:
        pr = _multi_pattern_result()
        r = compute_pattern_aggregation(
            pr,
            baseline_score=0.5,
            config=_enabled_config(),
            temporal_config=TemporalPatternConfig(enabled=False),
        )
        assert r.applied
        assert not r.temporal_applied

    def test_gating_unchanged(self) -> None:
        pr = _multi_pattern_result()
        r = compute_pattern_aggregation(
            pr,
            baseline_score=0.5,
            config=PatternInfluenceConfig(enabled=False),
        )
        assert not r.applied
        assert "disabled" in r.reason_if_not_applied

    def test_dominance_cap_unchanged_without_temporal(self) -> None:
        k1 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k2 = _key(TrendDirection.DOWN, RiskLevel.HIGH, StabilityLevel.LOW, UrgencyLevel.HIGH)
        matches = [
            _match(similarity=1.0, key=k1, stats=_stats(key=k1, avg_score=0.8)),
            _match(similarity=0.1, key=k2, stats=_stats(key=k2, avg_score=0.7)),
        ]
        pr = _multi_pattern_result(matches)

        r = compute_pattern_aggregation(pr, baseline_score=0.5, config=_enabled_config())
        for c in r.contributions:
            assert c.normalized_weight <= _DOMINANCE_CAP + 1e-10

    def test_contribution_default_temporal_fields(self) -> None:
        pr = _multi_pattern_result()
        r = compute_pattern_aggregation(pr, baseline_score=0.5, config=_enabled_config())
        for c in r.contributions:
            assert c.decay_factor == 1.0
            assert c.age == 0

    def test_factor_clamped_without_temporal(self) -> None:
        pr = _multi_pattern_result()
        r = compute_pattern_aggregation(pr, baseline_score=0.5, config=_enabled_config())
        assert _FACTOR_FLOOR <= r.final_factor <= _FACTOR_CEILING


# ═══════════════════════════════════════════════════════════════
# SECTION 10: Normalization tests
# ═══════════════════════════════════════════════════════════════


class TestNormalization:
    """Verify weight normalization after temporal decay."""

    def test_two_patterns_sum_one(self) -> None:
        k1 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k2 = _key(TrendDirection.DOWN, RiskLevel.HIGH, StabilityLevel.LOW, UrgencyLevel.HIGH)
        matches = [
            _match(similarity=1.0, key=k1),
            _match(similarity=0.75, key=k2),
        ]
        pr = _multi_pattern_result(matches)

        r = compute_pattern_aggregation(
            pr,
            baseline_score=0.5,
            config=_enabled_config(),
            temporal_config=_temporal_config(),
            current_observation_index=100,
            pattern_last_seen={
                str(k1.to_tuple()): 90,
                str(k2.to_tuple()): 10,
            },
        )
        total = sum(c.normalized_weight for c in r.contributions)
        assert abs(total - 1.0) < 1e-10

    def test_five_patterns_sum_one(self) -> None:
        keys = [
            _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW),
            _key(TrendDirection.DOWN, RiskLevel.HIGH, StabilityLevel.LOW, UrgencyLevel.HIGH),
            _key(
                TrendDirection.NEUTRAL, RiskLevel.MEDIUM, StabilityLevel.MEDIUM, UrgencyLevel.MEDIUM
            ),
            _key(TrendDirection.UP, RiskLevel.HIGH, StabilityLevel.HIGH, UrgencyLevel.LOW),
            _key(TrendDirection.DOWN, RiskLevel.LOW, StabilityLevel.LOW, UrgencyLevel.LOW),
        ]
        matches = [_match(similarity=max(0.5, 1.0 - i * 0.1), key=k) for i, k in enumerate(keys)]
        pr = _multi_pattern_result(matches)

        last_seen = {str(k.to_tuple()): 100 - i * 20 for i, k in enumerate(keys)}
        r = compute_pattern_aggregation(
            pr,
            baseline_score=0.5,
            config=_enabled_config(),
            temporal_config=_temporal_config(),
            current_observation_index=100,
            pattern_last_seen=last_seen,
        )
        total = sum(c.normalized_weight for c in r.contributions)
        assert abs(total - 1.0) < 1e-10

    def test_single_pattern_weight_one(self) -> None:
        k1 = _key()
        matches = [_match(similarity=1.0, key=k1)]
        pr = _multi_pattern_result(matches)

        r = compute_pattern_aggregation(
            pr,
            baseline_score=0.5,
            config=_enabled_config(),
            temporal_config=_temporal_config(),
            current_observation_index=100,
            pattern_last_seen={str(k1.to_tuple()): 50},
        )
        assert abs(r.contributions[0].normalized_weight - 1.0) < 1e-10


# ═══════════════════════════════════════════════════════════════
# SECTION 11: Comprehensive decay sweep
# ═══════════════════════════════════════════════════════════════


class TestDecaySweep:
    """Systematic sweep across ages and half-lives."""

    def test_decay_matrix(self) -> None:
        for hl in [5, 10, 25, 50, 100]:
            for age in [0, 1, 5, 10, 25, 50, 100, 200]:
                d = compute_decay_factor(age, hl)
                assert 0.0 <= d <= 1.0
                if age == 0:
                    assert d == 1.0
                if age == hl:
                    assert abs(d - 0.5) < 1e-10

    def test_weight_ratios(self) -> None:
        cfg = _temporal_config(half_life=50)
        r1 = apply_temporal_weights([1.0], ["a"], [0], [1.0], config=cfg)
        r2 = apply_temporal_weights([1.0], ["a"], [50], [1.0], config=cfg)
        r3 = apply_temporal_weights([1.0], ["a"], [100], [1.0], config=cfg)

        assert abs(r2.weights[0] / r1.weights[0] - 0.5) < 1e-10
        assert abs(r3.weights[0] / r1.weights[0] - 0.25) < 1e-10


# ═══════════════════════════════════════════════════════════════
# SECTION 12: Recent bias collapse prevention
# ═══════════════════════════════════════════════════════════════


class TestRecentBiasCollapse:
    """Verify old patterns maintain influence via floor."""

    def test_old_patterns_have_nonzero_normalized_weight(self) -> None:
        k1 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k2 = _key(TrendDirection.DOWN, RiskLevel.HIGH, StabilityLevel.LOW, UrgencyLevel.HIGH)
        matches = [
            _match(similarity=1.0, key=k1),
            _match(similarity=1.0, key=k2),
        ]
        pr = _multi_pattern_result(matches)

        r = compute_pattern_aggregation(
            pr,
            baseline_score=0.5,
            config=_enabled_config(),
            temporal_config=_temporal_config(half_life=5, min_weight=0.1),
            current_observation_index=1000,
            pattern_last_seen={
                str(k1.to_tuple()): 999,
                str(k2.to_tuple()): 0,
            },
        )
        old_c = [c for c in r.contributions if c.key == str(k2.to_tuple())][0]
        assert old_c.normalized_weight > 0.0

    def test_floor_prevents_single_pattern_monopoly(self) -> None:
        k1 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k2 = _key(TrendDirection.DOWN, RiskLevel.HIGH, StabilityLevel.LOW, UrgencyLevel.HIGH)
        matches = [
            _match(similarity=1.0, key=k1),
            _match(similarity=1.0, key=k2),
        ]
        pr = _multi_pattern_result(matches)

        r = compute_pattern_aggregation(
            pr,
            baseline_score=0.5,
            config=_enabled_config(),
            temporal_config=_temporal_config(half_life=5, min_weight=0.15),
            current_observation_index=1000,
            pattern_last_seen={
                str(k1.to_tuple()): 999,
                str(k2.to_tuple()): 0,
            },
        )
        weights = [c.normalized_weight for c in r.contributions]
        assert max(weights) < 1.0


# ═══════════════════════════════════════════════════════════════
# SECTION 13: TemporalContribution dataclass tests
# ═══════════════════════════════════════════════════════════════


class TestTemporalContribution:
    """Tests for the TemporalContribution dataclass."""

    def test_defaults(self) -> None:
        tc = TemporalContribution()
        assert tc.key == ""
        assert tc.age == 0
        assert tc.decay_factor == 1.0
        assert tc.pre_decay_weight == 0.0
        assert tc.final_weight == 0.0

    def test_custom_values(self) -> None:
        tc = TemporalContribution(
            key="k1", age=25, decay_factor=0.707, pre_decay_weight=0.8, final_weight=0.566
        )
        assert tc.key == "k1"
        assert tc.age == 25

    def test_to_dict(self) -> None:
        tc = TemporalContribution(
            key="k1", age=25, decay_factor=0.5, pre_decay_weight=0.8, final_weight=0.4
        )
        d = tc.to_dict()
        assert d["key"] == "k1"
        assert d["age"] == 25
        assert d["decay_factor"] == 0.5
        assert d["final_weight"] == 0.4


# ═══════════════════════════════════════════════════════════════
# SECTION 14: PatternContribution extended field tests
# ═══════════════════════════════════════════════════════════════


class TestPatternContributionTemporalFields:
    """Tests for temporal fields added to PatternContribution."""

    def test_default_temporal_fields(self) -> None:
        pc = PatternContribution()
        assert pc.age == 0
        assert pc.decay_factor == 1.0
        assert pc.pre_decay_weight == 0.0

    def test_custom_temporal_fields(self) -> None:
        pc = PatternContribution(age=50, decay_factor=0.5, pre_decay_weight=0.8)
        assert pc.age == 50
        assert pc.decay_factor == 0.5

    def test_to_dict_includes_temporal(self) -> None:
        pc = PatternContribution(age=50, decay_factor=0.5, pre_decay_weight=0.8)
        d = pc.to_dict()
        assert "age" in d
        assert "decay_factor" in d
        assert "pre_decay_weight" in d


# ═══════════════════════════════════════════════════════════════
# SECTION 15: PatternAggregationResult temporal_applied field
# ═══════════════════════════════════════════════════════════════


class TestAggregationResultTemporalField:
    """Tests for temporal_applied field."""

    def test_default_false(self) -> None:
        r = PatternAggregationResult()
        assert r.temporal_applied is False

    def test_set_true(self) -> None:
        r = PatternAggregationResult(temporal_applied=True)
        assert r.temporal_applied is True

    def test_to_dict(self) -> None:
        r = PatternAggregationResult(temporal_applied=True)
        d = r.to_dict()
        assert d["temporal_applied"] is True


# ═══════════════════════════════════════════════════════════════
# SECTION 16: Import and module structure tests
# ═══════════════════════════════════════════════════════════════


class TestImports:
    """Verify clean imports from the public API."""

    def test_import_from_pattern_temporal(self) -> None:
        from umh.runtime.pattern_temporal import (
            TemporalContribution,
            TemporalPatternConfig,
            TemporalWeightingResult,
            apply_temporal_weights,
            compute_decay_factor,
        )

        assert TemporalContribution is not None
        assert TemporalPatternConfig is not None
        assert TemporalWeightingResult is not None
        assert callable(apply_temporal_weights)
        assert callable(compute_decay_factor)

    def test_import_from_runtime_init(self) -> None:
        from umh.runtime import (
            TemporalContribution,
            TemporalPatternConfig,
            TemporalWeightingResult,
            apply_temporal_weights,
            compute_decay_factor,
        )

        assert callable(apply_temporal_weights)
        assert callable(compute_decay_factor)


# ═══════════════════════════════════════════════════════════════
# SECTION 17: Multi-pattern temporal ordering
# ═══════════════════════════════════════════════════════════════


class TestMultiPatternOrdering:
    """Verify temporal decay preserves ordering invariants."""

    def test_sorted_by_age_weight_decreasing(self) -> None:
        cfg = _temporal_config(half_life=50)
        ages = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        raw = [0.8] * len(ages)
        keys = [f"k{i}" for i in range(len(ages))]
        sims = [1.0] * len(ages)

        r = apply_temporal_weights(raw, keys, ages, sims, config=cfg)
        for i in range(len(ages) - 1):
            assert r.weights[i] >= r.weights[i + 1]

    def test_different_raw_weights_temporal_can_reorder(self) -> None:
        cfg = _temporal_config(half_life=10)
        r = apply_temporal_weights([0.3, 0.8], ["a", "b"], [0, 100], [1.0, 1.0], config=cfg)
        assert r.weights[0] > r.weights[1]


# ═══════════════════════════════════════════════════════════════
# SECTION 18: Regression guard — Phase 69 tests still pass
# ═══════════════════════════════════════════════════════════════


class TestPhase69Regression:
    """Ensure all Phase 69 behaviors still work."""

    def test_neutral_when_disabled(self) -> None:
        r = compute_pattern_aggregation(None, config=PatternInfluenceConfig(enabled=False))
        assert not r.applied

    def test_neutral_no_pattern_result(self) -> None:
        r = compute_pattern_aggregation(None, config=_enabled_config())
        assert not r.applied

    def test_neutral_no_matches(self) -> None:
        pr = PatternResult(matched=False)
        r = compute_pattern_aggregation(pr, config=_enabled_config())
        assert not r.applied

    def test_neutral_empty_matches(self) -> None:
        pr = PatternResult(matched=True, all_matches=())
        r = compute_pattern_aggregation(pr, config=_enabled_config())
        assert not r.applied

    def test_neutral_low_confidence(self) -> None:
        pr = _multi_pattern_result(confidence=0.01)
        r = compute_pattern_aggregation(
            pr, config=PatternInfluenceConfig(enabled=True, min_confidence=0.5)
        )
        assert not r.applied

    def test_dominance_cap_preserved(self) -> None:
        w, capped = _apply_dominance_cap([0.9, 0.1])
        assert capped
        assert max(w) <= _DOMINANCE_CAP + 1e-10

    def test_individual_factor_computation(self) -> None:
        from umh.runtime.pattern_aggregation import _compute_individual_factor

        f = _compute_individual_factor(0.8, 0.5, 0.1)
        assert _FACTOR_FLOOR <= f <= _FACTOR_CEILING
