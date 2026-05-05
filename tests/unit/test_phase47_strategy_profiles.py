"""Phase 47 — Regime-Conditioned Strategy Selection Layer v1.

155+ tests covering:
- Default profile existence and structure
- Compatibility classification
- Preferred regime boosts
- Penalized regime suppresses
- Neutral regime stays 1.0
- Duration scaling for TREND regimes
- No duration scaling for SPIKE/STABLE
- Bounds / clamping enforcement
- Determinism
- No state mutation
- Regime cannot dominate score
- Missing profile defaults neutral
- Scoring chain integration
- Pipeline integration
- Different strategies win under different regimes
- Explainability
- Snapshot operations
- Serialization
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest

from umh.runtime.regime import RegimeType
from umh.runtime.strategy_profile import (
    AGGRESSIVE_PROFILE,
    BALANCED_PROFILE,
    CONSERVATIVE_PROFILE,
    DEFAULT_PROFILES,
    NEUTRAL_PROFILE,
    RECOVERY_PROFILE,
    StrategyRegimeProfile,
    StrategyRegimeResult,
    StrategyRegimeSnapshot,
    apply_strategy_regime_factor,
    compute_all_strategy_factors,
    compute_strategy_regime_factor,
    get_profile,
    _DEFAULT_DURATION_SCALE_CAP,
    _DEFAULT_MAX_BONUS,
    _DEFAULT_MAX_PENALTY,
    _DEFAULT_MIN_FACTOR,
    _DEFAULT_MAX_FACTOR,
)


# ── Section 1: Default profiles exist ───────────────────────────────


class TestDefaultProfilesExist:
    def test_aggressive_profile_exists(self):
        assert "aggressive" in DEFAULT_PROFILES

    def test_conservative_profile_exists(self):
        assert "conservative" in DEFAULT_PROFILES

    def test_balanced_profile_exists(self):
        assert "balanced" in DEFAULT_PROFILES

    def test_recovery_profile_exists(self):
        assert "recovery" in DEFAULT_PROFILES

    def test_four_default_profiles(self):
        assert len(DEFAULT_PROFILES) == 4

    def test_neutral_profile_separate(self):
        assert "neutral" not in DEFAULT_PROFILES
        assert NEUTRAL_PROFILE.strategy_name == "neutral"


# ── Section 2: Aggressive profile ──────────────────────────────────


class TestAggressiveProfile:
    def test_preferred_spike_up(self):
        assert RegimeType.SPIKE_UP in AGGRESSIVE_PROFILE.preferred_regimes

    def test_preferred_trend_up(self):
        assert RegimeType.TREND_UP in AGGRESSIVE_PROFILE.preferred_regimes

    def test_penalized_spike_down(self):
        assert RegimeType.SPIKE_DOWN in AGGRESSIVE_PROFILE.penalized_regimes

    def test_penalized_trend_down(self):
        assert RegimeType.TREND_DOWN in AGGRESSIVE_PROFILE.penalized_regimes

    def test_neutral_stable(self):
        assert RegimeType.STABLE in AGGRESSIVE_PROFILE.neutral_regimes

    def test_boost_under_spike_up(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.SPIKE_UP, 0)
        assert r.factor > 1.0

    def test_penalty_under_spike_down(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.SPIKE_DOWN, 0)
        assert r.factor < 1.0

    def test_neutral_under_stable(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.STABLE, 0)
        assert r.factor == 1.0


# ── Section 3: Conservative profile ────────────────────────────────


class TestConservativeProfile:
    def test_preferred_stable(self):
        assert RegimeType.STABLE in CONSERVATIVE_PROFILE.preferred_regimes

    def test_preferred_trend_down(self):
        assert RegimeType.TREND_DOWN in CONSERVATIVE_PROFILE.preferred_regimes

    def test_penalized_spike_up(self):
        assert RegimeType.SPIKE_UP in CONSERVATIVE_PROFILE.penalized_regimes

    def test_penalized_spike_down(self):
        assert RegimeType.SPIKE_DOWN in CONSERVATIVE_PROFILE.penalized_regimes

    def test_neutral_trend_up(self):
        assert RegimeType.TREND_UP in CONSERVATIVE_PROFILE.neutral_regimes

    def test_boost_under_stable(self):
        r = compute_strategy_regime_factor(CONSERVATIVE_PROFILE, RegimeType.STABLE, 0)
        assert r.factor > 1.0

    def test_penalty_under_spike_up(self):
        r = compute_strategy_regime_factor(CONSERVATIVE_PROFILE, RegimeType.SPIKE_UP, 0)
        assert r.factor < 1.0


# ── Section 4: Balanced profile ────────────────────────────────────


class TestBalancedProfile:
    def test_preferred_stable(self):
        assert RegimeType.STABLE in BALANCED_PROFILE.preferred_regimes

    def test_preferred_trend_up(self):
        assert RegimeType.TREND_UP in BALANCED_PROFILE.preferred_regimes

    def test_no_penalized(self):
        assert len(BALANCED_PROFILE.penalized_regimes) == 0

    def test_lower_bonus(self):
        assert BALANCED_PROFILE.max_bonus == 0.05

    def test_lower_penalty(self):
        assert BALANCED_PROFILE.max_penalty == 0.05

    def test_never_penalized(self):
        for rt in RegimeType:
            r = compute_strategy_regime_factor(BALANCED_PROFILE, rt, 0)
            assert r.factor >= 1.0


# ── Section 5: Recovery profile ────────────────────────────────────


class TestRecoveryProfile:
    def test_preferred_spike_down(self):
        assert RegimeType.SPIKE_DOWN in RECOVERY_PROFILE.preferred_regimes

    def test_preferred_trend_down(self):
        assert RegimeType.TREND_DOWN in RECOVERY_PROFILE.preferred_regimes

    def test_penalized_spike_up(self):
        assert RegimeType.SPIKE_UP in RECOVERY_PROFILE.penalized_regimes

    def test_penalized_trend_up(self):
        assert RegimeType.TREND_UP in RECOVERY_PROFILE.penalized_regimes

    def test_neutral_stable(self):
        assert RegimeType.STABLE in RECOVERY_PROFILE.neutral_regimes

    def test_boost_under_spike_down(self):
        r = compute_strategy_regime_factor(RECOVERY_PROFILE, RegimeType.SPIKE_DOWN, 0)
        assert r.factor > 1.0

    def test_penalty_under_spike_up(self):
        r = compute_strategy_regime_factor(RECOVERY_PROFILE, RegimeType.SPIKE_UP, 0)
        assert r.factor < 1.0


# ── Section 6: Compatibility classification ────────────────────────


class TestCompatibilityClass:
    def test_preferred_class(self):
        assert AGGRESSIVE_PROFILE.compatibility_class(RegimeType.SPIKE_UP) == "preferred"

    def test_penalized_class(self):
        assert AGGRESSIVE_PROFILE.compatibility_class(RegimeType.SPIKE_DOWN) == "penalized"

    def test_neutral_class(self):
        assert AGGRESSIVE_PROFILE.compatibility_class(RegimeType.STABLE) == "neutral"

    def test_unlisted_regime_is_neutral(self):
        profile = StrategyRegimeProfile(
            strategy_name="test",
            preferred_regimes=frozenset({RegimeType.SPIKE_UP}),
        )
        assert profile.compatibility_class(RegimeType.TREND_DOWN) == "neutral"


# ── Section 7: Preferred regime boosts factor ──────────────────────


class TestPreferredBoost:
    def test_preferred_spike_boost(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.SPIKE_UP, 0)
        assert r.factor == pytest.approx(1.0 + _DEFAULT_MAX_BONUS)

    def test_preferred_stable_boost_conservative(self):
        r = compute_strategy_regime_factor(CONSERVATIVE_PROFILE, RegimeType.STABLE, 0)
        assert r.factor == pytest.approx(1.0 + _DEFAULT_MAX_BONUS)

    def test_preferred_trend_at_cap_duration(self):
        r = compute_strategy_regime_factor(
            AGGRESSIVE_PROFILE, RegimeType.TREND_UP, _DEFAULT_DURATION_SCALE_CAP
        )
        assert r.factor == pytest.approx(1.0 + _DEFAULT_MAX_BONUS)

    def test_preferred_trend_at_zero_duration(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.TREND_UP, 0)
        assert r.factor == 1.0

    def test_compatibility_is_preferred(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.SPIKE_UP, 0)
        assert r.compatibility == "preferred"


# ── Section 8: Penalized regime suppresses factor ──────────────────


class TestPenalizedSuppression:
    def test_penalized_spike_suppresses(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.SPIKE_DOWN, 0)
        assert r.factor == pytest.approx(1.0 - _DEFAULT_MAX_PENALTY)

    def test_penalized_trend_at_cap(self):
        r = compute_strategy_regime_factor(
            AGGRESSIVE_PROFILE, RegimeType.TREND_DOWN, _DEFAULT_DURATION_SCALE_CAP
        )
        assert r.factor == pytest.approx(1.0 - _DEFAULT_MAX_PENALTY)

    def test_penalized_trend_at_zero(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.TREND_DOWN, 0)
        assert r.factor == 1.0

    def test_compatibility_is_penalized(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.SPIKE_DOWN, 0)
        assert r.compatibility == "penalized"


# ── Section 9: Neutral stays 1.0 ──────────────────────────────────


class TestNeutralFactor:
    def test_neutral_factor_is_one(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.STABLE, 0)
        assert r.factor == 1.0

    def test_neutral_factor_any_duration(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.STABLE, 100)
        assert r.factor == 1.0

    def test_neutral_compatibility(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.STABLE, 0)
        assert r.compatibility == "neutral"


# ── Section 10: Duration scaling for TREND ─────────────────────────


class TestTrendDurationScaling:
    def test_trend_preferred_scales_with_duration(self):
        factors = []
        for d in range(_DEFAULT_DURATION_SCALE_CAP + 1):
            r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.TREND_UP, d)
            factors.append(r.factor)
        for i in range(1, len(factors)):
            assert factors[i] >= factors[i - 1]

    def test_trend_penalized_scales_with_duration(self):
        factors = []
        for d in range(_DEFAULT_DURATION_SCALE_CAP + 1):
            r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.TREND_DOWN, d)
            factors.append(r.factor)
        for i in range(1, len(factors)):
            assert factors[i] <= factors[i - 1]

    def test_trend_preferred_zero_at_start(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.TREND_UP, 0)
        assert r.factor == 1.0

    def test_trend_preferred_full_at_cap(self):
        r = compute_strategy_regime_factor(
            AGGRESSIVE_PROFILE, RegimeType.TREND_UP, _DEFAULT_DURATION_SCALE_CAP
        )
        assert r.factor == pytest.approx(1.0 + _DEFAULT_MAX_BONUS)

    def test_trend_preferred_mid_duration(self):
        mid = _DEFAULT_DURATION_SCALE_CAP // 2
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.TREND_UP, mid)
        expected_scale = mid / _DEFAULT_DURATION_SCALE_CAP
        expected = 1.0 + _DEFAULT_MAX_BONUS * expected_scale
        assert r.factor == pytest.approx(expected)

    def test_trend_capped_past_duration_cap(self):
        r1 = compute_strategy_regime_factor(
            AGGRESSIVE_PROFILE, RegimeType.TREND_UP, _DEFAULT_DURATION_SCALE_CAP
        )
        r2 = compute_strategy_regime_factor(
            AGGRESSIVE_PROFILE, RegimeType.TREND_UP, _DEFAULT_DURATION_SCALE_CAP * 5
        )
        assert r1.factor == r2.factor

    def test_trend_penalized_zero_at_start(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.TREND_DOWN, 0)
        assert r.factor == 1.0

    def test_trend_penalized_full_at_cap(self):
        r = compute_strategy_regime_factor(
            AGGRESSIVE_PROFILE, RegimeType.TREND_DOWN, _DEFAULT_DURATION_SCALE_CAP
        )
        assert r.factor == pytest.approx(1.0 - _DEFAULT_MAX_PENALTY)


# ── Section 11: No duration scaling for SPIKE ──────────────────────


class TestSpikeFlatFactor:
    def test_spike_up_flat_duration_0(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.SPIKE_UP, 0)
        assert r.factor == pytest.approx(1.0 + _DEFAULT_MAX_BONUS)

    def test_spike_up_flat_duration_100(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.SPIKE_UP, 100)
        assert r.factor == pytest.approx(1.0 + _DEFAULT_MAX_BONUS)

    def test_spike_up_same_any_duration(self):
        r0 = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.SPIKE_UP, 0)
        r50 = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.SPIKE_UP, 50)
        assert r0.factor == r50.factor

    def test_spike_down_flat(self):
        r0 = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.SPIKE_DOWN, 0)
        r50 = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.SPIKE_DOWN, 50)
        assert r0.factor == r50.factor

    def test_stable_flat(self):
        r0 = compute_strategy_regime_factor(CONSERVATIVE_PROFILE, RegimeType.STABLE, 0)
        r50 = compute_strategy_regime_factor(CONSERVATIVE_PROFILE, RegimeType.STABLE, 50)
        assert r0.factor == r50.factor


# ── Section 12: Bounds / clamping enforcement ──────────────────────


class TestBoundsEnforcement:
    def test_factor_never_below_min(self):
        for profile in DEFAULT_PROFILES.values():
            for rt in RegimeType:
                for d in [0, 5, 10, 50, 100]:
                    r = compute_strategy_regime_factor(profile, rt, d)
                    assert r.factor >= _DEFAULT_MIN_FACTOR

    def test_factor_never_above_max(self):
        for profile in DEFAULT_PROFILES.values():
            for rt in RegimeType:
                for d in [0, 5, 10, 50, 100]:
                    r = compute_strategy_regime_factor(profile, rt, d)
                    assert r.factor <= _DEFAULT_MAX_FACTOR

    def test_extreme_bonus_clamped(self):
        profile = StrategyRegimeProfile(
            strategy_name="extreme",
            preferred_regimes=frozenset({RegimeType.SPIKE_UP}),
            max_bonus=5.0,
        )
        r = compute_strategy_regime_factor(profile, RegimeType.SPIKE_UP, 0)
        assert r.factor == _DEFAULT_MAX_FACTOR
        assert r.raw_factor == pytest.approx(6.0)

    def test_extreme_penalty_clamped(self):
        profile = StrategyRegimeProfile(
            strategy_name="extreme",
            penalized_regimes=frozenset({RegimeType.SPIKE_DOWN}),
            max_penalty=5.0,
        )
        r = compute_strategy_regime_factor(profile, RegimeType.SPIKE_DOWN, 0)
        assert r.factor == _DEFAULT_MIN_FACTOR
        assert r.raw_factor == pytest.approx(-4.0)

    def test_custom_bounds(self):
        r = compute_strategy_regime_factor(
            AGGRESSIVE_PROFILE, RegimeType.SPIKE_UP, 0,
            min_factor=0.99, max_factor=1.01,
        )
        assert r.factor == 1.01

    def test_regime_compatibility_bounded_invariant_172(self):
        for profile in DEFAULT_PROFILES.values():
            for rt in RegimeType:
                for d in range(20):
                    r = compute_strategy_regime_factor(profile, rt, d)
                    assert _DEFAULT_MIN_FACTOR <= r.factor <= _DEFAULT_MAX_FACTOR


# ── Section 13: Determinism (invariant 171) ────────────────────────


class TestDeterminism:
    def test_same_inputs_same_output(self):
        r1 = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.SPIKE_UP, 0)
        r2 = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.SPIKE_UP, 0)
        assert r1.factor == r2.factor

    def test_deterministic_across_100_calls(self):
        results = [
            compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.TREND_UP, 5).factor
            for _ in range(100)
        ]
        assert len(set(results)) == 1

    def test_deterministic_all_profiles(self):
        for name, profile in DEFAULT_PROFILES.items():
            for rt in RegimeType:
                f1 = compute_strategy_regime_factor(profile, rt, 5).factor
                f2 = compute_strategy_regime_factor(profile, rt, 5).factor
                assert f1 == f2, f"{name}/{rt}"


# ── Section 14: No state mutation (invariant 174) ──────────────────


class TestNoStateMutation:
    def test_profile_unchanged_after_compute(self):
        before = AGGRESSIVE_PROFILE.to_dict()
        compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.SPIKE_UP, 10)
        after = AGGRESSIVE_PROFILE.to_dict()
        assert before == after

    def test_result_frozen(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.STABLE, 0)
        with pytest.raises(AttributeError):
            r.factor = 2.0

    def test_profile_frozen(self):
        with pytest.raises(AttributeError):
            AGGRESSIVE_PROFILE.max_bonus = 0.5


# ── Section 15: Regime cannot dominate score (invariant 173) ───────


class TestRegimeCannotDominate:
    def test_max_influence_bounded(self):
        for profile in DEFAULT_PROFILES.values():
            for rt in RegimeType:
                for d in range(20):
                    r = compute_strategy_regime_factor(profile, rt, d)
                    deviation = abs(r.factor - 1.0)
                    assert deviation <= 0.15 + 1e-9

    def test_strategy_regime_factor_preserves_score_ordering(self):
        base_high = 100.0
        base_low = 50.0
        for profile in DEFAULT_PROFILES.values():
            for rt in RegimeType:
                f = compute_strategy_regime_factor(profile, rt, 5).factor
                assert apply_strategy_regime_factor(base_high, f) > apply_strategy_regime_factor(base_low, f)


# ── Section 16: Missing profile defaults neutral (invariant 175) ──


class TestMissingProfileDefault:
    def test_get_profile_known(self):
        p = get_profile("aggressive")
        assert p.strategy_name == "aggressive"

    def test_get_profile_unknown(self):
        p = get_profile("nonexistent")
        assert p.strategy_name == "neutral"

    def test_neutral_factor_all_regimes(self):
        for rt in RegimeType:
            r = compute_strategy_regime_factor(NEUTRAL_PROFILE, rt, 50)
            assert r.factor == 1.0

    def test_neutral_zero_bonus(self):
        assert NEUTRAL_PROFILE.max_bonus == 0.0

    def test_neutral_zero_penalty(self):
        assert NEUTRAL_PROFILE.max_penalty == 0.0

    def test_neutral_all_regimes_classified_neutral(self):
        for rt in RegimeType:
            assert NEUTRAL_PROFILE.compatibility_class(rt) == "neutral"


# ── Section 17: Different strategies win under different regimes ───


class TestDifferentStrategiesWin:
    def test_aggressive_wins_in_spike_up(self):
        snap = compute_all_strategy_factors(DEFAULT_PROFILES, RegimeType.SPIKE_UP, 0)
        assert snap.best_strategy() == "aggressive"

    def test_recovery_wins_in_spike_down(self):
        snap = compute_all_strategy_factors(DEFAULT_PROFILES, RegimeType.SPIKE_DOWN, 0)
        assert snap.best_strategy() == "recovery"

    def test_conservative_wins_in_stable(self):
        snap = compute_all_strategy_factors(DEFAULT_PROFILES, RegimeType.STABLE, 0)
        best = snap.best_strategy()
        assert best in ("conservative", "balanced")

    def test_recovery_or_conservative_wins_in_trend_down_at_cap(self):
        snap = compute_all_strategy_factors(
            DEFAULT_PROFILES, RegimeType.TREND_DOWN, _DEFAULT_DURATION_SCALE_CAP
        )
        assert snap.best_strategy() in ("recovery", "conservative")

    def test_aggressive_wins_in_trend_up_at_cap(self):
        snap = compute_all_strategy_factors(
            DEFAULT_PROFILES, RegimeType.TREND_UP, _DEFAULT_DURATION_SCALE_CAP
        )
        assert snap.best_strategy() == "aggressive"

    def test_different_winners_across_regimes(self):
        winners = set()
        for rt in RegimeType:
            snap = compute_all_strategy_factors(DEFAULT_PROFILES, rt, _DEFAULT_DURATION_SCALE_CAP)
            winners.add(snap.best_strategy())
        assert len(winners) >= 2


# ── Section 18: Scoring chain integration ──────────────────────────


class TestScoringChainIntegration:
    def test_full_chain(self):
        base_score = 80.0
        identity_factor = 1.05
        goal_bias = 1.02
        from umh.runtime.regime_weight import compute_regime_factor

        regime_factor = compute_regime_factor("urgency", RegimeType.SPIKE_UP, 0).factor
        strategy_factor = compute_strategy_regime_factor(
            AGGRESSIVE_PROFILE, RegimeType.SPIKE_UP, 0
        ).factor

        score = base_score * identity_factor * goal_bias * regime_factor * strategy_factor
        assert score > base_score

    def test_stable_chain_neutral(self):
        base_score = 80.0
        identity = 1.0
        goal = 1.0
        from umh.runtime.regime_weight import compute_regime_factor

        regime_f = compute_regime_factor("urgency", RegimeType.STABLE, 0).factor
        strategy_f = compute_strategy_regime_factor(
            AGGRESSIVE_PROFILE, RegimeType.STABLE, 0
        ).factor

        score = base_score * identity * goal * regime_f * strategy_f
        assert score == pytest.approx(base_score)

    def test_chain_bounded_total_influence(self):
        base = 100.0
        from umh.runtime.regime_weight import compute_regime_factor

        for profile in DEFAULT_PROFILES.values():
            for rt in RegimeType:
                rf = compute_regime_factor("s", rt, 10).factor
                sf = compute_strategy_regime_factor(profile, rt, 10).factor
                combined = base * rf * sf
                assert combined >= base * 0.85 * 0.85 - 0.01
                assert combined <= base * 1.15 * 1.15 + 0.01


# ── Section 19: apply_strategy_regime_factor ───────────────────────


class TestApplyFactor:
    def test_neutral(self):
        assert apply_strategy_regime_factor(100.0, 1.0) == 100.0

    def test_boost(self):
        assert apply_strategy_regime_factor(100.0, 1.10) == pytest.approx(110.0)

    def test_reduction(self):
        assert apply_strategy_regime_factor(100.0, 0.90) == pytest.approx(90.0)

    def test_zero_score(self):
        assert apply_strategy_regime_factor(0.0, 1.15) == 0.0

    def test_negative_score(self):
        assert apply_strategy_regime_factor(-10.0, 1.10) == pytest.approx(-11.0)


# ── Section 20: Explainability ─────────────────────────────────────


class TestExplainability:
    def test_result_has_strategy_name(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.SPIKE_UP, 0)
        assert r.strategy_name == "aggressive"

    def test_result_has_regime(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.SPIKE_UP, 0)
        assert r.regime == RegimeType.SPIKE_UP

    def test_result_has_compatibility(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.SPIKE_UP, 0)
        assert r.compatibility == "preferred"

    def test_result_has_reason(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.SPIKE_UP, 0)
        assert len(r.reason) > 0
        assert "aggressive" in r.reason
        assert "spike_up" in r.reason

    def test_result_has_duration(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.TREND_UP, 7)
        assert r.duration == 7

    def test_to_dict_keys(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.SPIKE_UP, 0)
        d = r.to_dict()
        assert set(d.keys()) == {
            "strategy_name", "regime", "duration", "compatibility",
            "raw_factor", "factor", "reason"
        }

    def test_to_dict_regime_is_string(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.SPIKE_UP, 0)
        assert r.to_dict()["regime"] == "spike_up"

    def test_penalized_reason_mentions_penalized(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.SPIKE_DOWN, 0)
        assert "penalized" in r.reason

    def test_neutral_reason_mentions_neutral(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.STABLE, 0)
        assert "neutral" in r.reason


# ── Section 21: Snapshot operations ────────────────────────────────


class TestSnapshotOperations:
    def test_get_existing(self):
        snap = compute_all_strategy_factors(DEFAULT_PROFILES, RegimeType.STABLE, 0)
        assert snap.get("aggressive") is not None

    def test_get_missing(self):
        snap = compute_all_strategy_factors(DEFAULT_PROFILES, RegimeType.STABLE, 0)
        assert snap.get("nonexistent") is None

    def test_get_factor_existing(self):
        snap = compute_all_strategy_factors(DEFAULT_PROFILES, RegimeType.SPIKE_UP, 0)
        assert snap.get_factor("aggressive") > 1.0

    def test_get_factor_missing_default(self):
        snap = compute_all_strategy_factors(DEFAULT_PROFILES, RegimeType.STABLE, 0)
        assert snap.get_factor("missing") == 1.0

    def test_get_factor_custom_default(self):
        snap = compute_all_strategy_factors(DEFAULT_PROFILES, RegimeType.STABLE, 0)
        assert snap.get_factor("missing", default=0.5) == 0.5

    def test_best_strategy(self):
        snap = compute_all_strategy_factors(DEFAULT_PROFILES, RegimeType.SPIKE_UP, 0)
        assert snap.best_strategy() is not None

    def test_worst_strategy(self):
        snap = compute_all_strategy_factors(DEFAULT_PROFILES, RegimeType.SPIKE_UP, 0)
        worst = snap.worst_strategy()
        assert worst is not None
        assert worst != snap.best_strategy()

    def test_preferred_strategies(self):
        snap = compute_all_strategy_factors(DEFAULT_PROFILES, RegimeType.SPIKE_UP, 0)
        preferred = snap.preferred_strategies()
        assert "aggressive" in preferred

    def test_penalized_strategies(self):
        snap = compute_all_strategy_factors(DEFAULT_PROFILES, RegimeType.SPIKE_UP, 0)
        penalized = snap.penalized_strategies()
        assert "conservative" in penalized

    def test_empty_snapshot(self):
        snap = compute_all_strategy_factors({}, RegimeType.STABLE, 0)
        assert snap.best_strategy() is None
        assert snap.worst_strategy() is None
        assert snap.preferred_strategies() == []
        assert snap.penalized_strategies() == []

    def test_to_dict(self):
        snap = compute_all_strategy_factors(DEFAULT_PROFILES, RegimeType.STABLE, 0)
        d = snap.to_dict()
        assert "results" in d
        assert len(d["results"]) == 4

    def test_sorted_in_dict(self):
        snap = compute_all_strategy_factors(DEFAULT_PROFILES, RegimeType.STABLE, 0)
        keys = list(snap.to_dict()["results"].keys())
        assert keys == sorted(keys)


# ── Section 22: Profile serialization ──────────────────────────────


class TestProfileSerialization:
    def test_profile_to_dict(self):
        d = AGGRESSIVE_PROFILE.to_dict()
        assert d["strategy_name"] == "aggressive"
        assert "spike_up" in d["preferred_regimes"]
        assert "spike_down" in d["penalized_regimes"]

    def test_profile_to_dict_sorted_regimes(self):
        d = AGGRESSIVE_PROFILE.to_dict()
        assert d["preferred_regimes"] == sorted(d["preferred_regimes"])
        assert d["penalized_regimes"] == sorted(d["penalized_regimes"])

    def test_profile_to_dict_has_bonus_penalty(self):
        d = AGGRESSIVE_PROFILE.to_dict()
        assert "max_bonus" in d
        assert "max_penalty" in d


# ── Section 23: Config edge cases ─────────────────────────────────


class TestConfigEdgeCases:
    def test_negative_bonus_clamped(self):
        p = StrategyRegimeProfile(strategy_name="t", max_bonus=-1.0)
        assert p.max_bonus == 0.0

    def test_negative_penalty_clamped(self):
        p = StrategyRegimeProfile(strategy_name="t", max_penalty=-1.0)
        assert p.max_penalty == 0.0

    def test_zero_bonus_profile(self):
        p = StrategyRegimeProfile(
            strategy_name="t",
            preferred_regimes=frozenset({RegimeType.SPIKE_UP}),
            max_bonus=0.0,
        )
        r = compute_strategy_regime_factor(p, RegimeType.SPIKE_UP, 0)
        assert r.factor == 1.0

    def test_zero_penalty_profile(self):
        p = StrategyRegimeProfile(
            strategy_name="t",
            penalized_regimes=frozenset({RegimeType.SPIKE_DOWN}),
            max_penalty=0.0,
        )
        r = compute_strategy_regime_factor(p, RegimeType.SPIKE_DOWN, 0)
        assert r.factor == 1.0

    def test_negative_duration_clamped(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.TREND_UP, -5)
        r0 = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.TREND_UP, 0)
        assert r.factor == r0.factor
        assert r.duration == 0


# ── Section 24: Pipeline integration with Phase 42-46 ─────────────


class TestPipelineIntegration:
    def test_classify_to_strategy_profile(self):
        from umh.runtime.regime import classify_regime, RegimeThresholds

        result = classify_regime("urgency", 0.30, RegimeThresholds())
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, result.regime, 0)
        assert r.factor > 1.0

    def test_filter_then_strategy_profile(self):
        from umh.runtime.regime_filter import FilterState, filter_regime

        state = FilterState(signal_name="urgency", confirmed_regime=RegimeType.STABLE)
        fr = filter_regime(state, RegimeType.SPIKE_UP, 1)
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, fr.filtered_regime, 0)
        assert r.factor > 1.0

    def test_filter_suppressed_stays_neutral(self):
        from umh.runtime.regime_filter import FilterState, filter_regime

        state = FilterState(signal_name="urgency", confirmed_regime=RegimeType.STABLE)
        fr = filter_regime(state, RegimeType.SPIKE_UP, 3)
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, fr.filtered_regime, 10)
        assert r.compatibility == "neutral"
        assert r.factor == 1.0

    def test_regime_weight_plus_strategy_profile(self):
        from umh.runtime.regime_weight import compute_regime_factor

        rw = compute_regime_factor("urgency", RegimeType.SPIKE_UP, 0)
        sp = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.SPIKE_UP, 0)
        combined = rw.factor * sp.factor
        assert combined > 1.0
        assert combined <= 1.15 * 1.15 + 0.01

    def test_full_pipeline_chain(self):
        from umh.runtime.regime import classify_regime, RegimeThresholds
        from umh.runtime.regime_weight import compute_regime_factor

        classified = classify_regime("urgency", 0.30, RegimeThresholds())
        regime_wt = compute_regime_factor("urgency", classified.regime, 0)
        strategy_wt = compute_strategy_regime_factor(
            AGGRESSIVE_PROFILE, classified.regime, 0
        )

        base = 80.0
        score = base * regime_wt.factor * strategy_wt.factor
        assert score > base


# ── Section 25: Exact numerical verification ──────────────────────


class TestExactNumerical:
    def test_aggressive_spike_up_exact(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.SPIKE_UP, 0)
        assert r.factor == pytest.approx(1.10)

    def test_aggressive_spike_down_exact(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.SPIKE_DOWN, 0)
        assert r.factor == pytest.approx(0.90)

    def test_aggressive_trend_up_dur5_exact(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.TREND_UP, 5)
        scale = 5.0 / _DEFAULT_DURATION_SCALE_CAP
        expected = 1.0 + _DEFAULT_MAX_BONUS * scale
        assert r.factor == pytest.approx(expected)

    def test_aggressive_trend_down_dur5_exact(self):
        r = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.TREND_DOWN, 5)
        scale = 5.0 / _DEFAULT_DURATION_SCALE_CAP
        expected = 1.0 - _DEFAULT_MAX_PENALTY * scale
        assert r.factor == pytest.approx(expected)

    def test_balanced_stable_exact(self):
        r = compute_strategy_regime_factor(BALANCED_PROFILE, RegimeType.STABLE, 0)
        assert r.factor == pytest.approx(1.05)

    def test_balanced_trend_up_dur10_exact(self):
        r = compute_strategy_regime_factor(BALANCED_PROFILE, RegimeType.TREND_UP, 10)
        assert r.factor == pytest.approx(1.05)

    def test_recovery_spike_down_exact(self):
        r = compute_strategy_regime_factor(RECOVERY_PROFILE, RegimeType.SPIKE_DOWN, 0)
        assert r.factor == pytest.approx(1.10)

    def test_recovery_spike_up_exact(self):
        r = compute_strategy_regime_factor(RECOVERY_PROFILE, RegimeType.SPIKE_UP, 0)
        assert r.factor == pytest.approx(0.90)

    def test_conservative_stable_exact(self):
        r = compute_strategy_regime_factor(CONSERVATIVE_PROFILE, RegimeType.STABLE, 0)
        assert r.factor == pytest.approx(1.10)

    def test_conservative_spike_up_exact(self):
        r = compute_strategy_regime_factor(CONSERVATIVE_PROFILE, RegimeType.SPIKE_UP, 0)
        assert r.factor == pytest.approx(0.90)


# ── Section 26: Raw factor vs clamped factor ──────────────────────


class TestRawVsClamped:
    def test_default_profiles_no_clamping(self):
        for name, profile in DEFAULT_PROFILES.items():
            for rt in RegimeType:
                r = compute_strategy_regime_factor(profile, rt, _DEFAULT_DURATION_SCALE_CAP)
                assert r.raw_factor == r.factor, f"{name}/{rt}"

    def test_extreme_bonus_shows_clamping(self):
        p = StrategyRegimeProfile(
            strategy_name="x",
            preferred_regimes=frozenset({RegimeType.SPIKE_UP}),
            max_bonus=5.0,
        )
        r = compute_strategy_regime_factor(p, RegimeType.SPIKE_UP, 0)
        assert r.raw_factor != r.factor
        assert r.raw_factor > r.factor


# ── Section 27: All regime types produce results ──────────────────


class TestAllRegimesCovered:
    def test_every_regime_every_profile(self):
        for name, profile in DEFAULT_PROFILES.items():
            for rt in RegimeType:
                r = compute_strategy_regime_factor(profile, rt, 5)
                assert isinstance(r, StrategyRegimeResult)
                assert r.strategy_name == name

    def test_every_result_has_reason(self):
        for profile in DEFAULT_PROFILES.values():
            for rt in RegimeType:
                r = compute_strategy_regime_factor(profile, rt, 0)
                assert len(r.reason) > 0


# ── Section 28: Compute all with custom profiles ─────────────────


class TestComputeAllCustom:
    def test_single_profile(self):
        snap = compute_all_strategy_factors(
            {"test": NEUTRAL_PROFILE}, RegimeType.SPIKE_UP, 0
        )
        assert len(snap.results) == 1

    def test_custom_profile_in_snapshot(self):
        custom = StrategyRegimeProfile(
            strategy_name="custom",
            preferred_regimes=frozenset({RegimeType.SPIKE_UP}),
            max_bonus=0.12,
        )
        snap = compute_all_strategy_factors(
            {"custom": custom}, RegimeType.SPIKE_UP, 0
        )
        assert snap.get_factor("custom") == pytest.approx(1.12)

    def test_sorted_output(self):
        profiles = {"z": NEUTRAL_PROFILE, "a": NEUTRAL_PROFILE, "m": NEUTRAL_PROFILE}
        snap = compute_all_strategy_factors(profiles, RegimeType.STABLE, 0)
        assert list(snap.results.keys()) == ["a", "m", "z"]


# ── Section 29: Invariant sweep tests ────────────────────────────


class TestInvariantSweep:
    def test_invariant_171_deterministic_selection(self):
        for _ in range(50):
            snap = compute_all_strategy_factors(DEFAULT_PROFILES, RegimeType.SPIKE_UP, 5)
            assert snap.best_strategy() == "aggressive"

    def test_invariant_173_regime_profile_weaker_than_base(self):
        base = 100.0
        for profile in DEFAULT_PROFILES.values():
            for rt in RegimeType:
                f = compute_strategy_regime_factor(profile, rt, _DEFAULT_DURATION_SCALE_CAP).factor
                adjusted = base * f
                assert adjusted >= 85.0
                assert adjusted <= 115.0

    def test_invariant_175_missing_profile_neutral(self):
        p = get_profile("nonexistent_strategy_xyz")
        for rt in RegimeType:
            r = compute_strategy_regime_factor(p, rt, 50)
            assert r.factor == 1.0
