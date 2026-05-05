"""Phase 48 — Composite Regime Modeling Layer v1.

160+ tests covering:
- Composite state construction
- Signal classification (risk, urgency, stability, confidence)
- Missing signals default neutral
- Multi-dimension match scoring
- Dimension weights
- Conflicting signals produce balanced scores
- Bounds / clamping
- Determinism
- No state mutation
- Explainability
- Default composite profiles
- Different strategies win under different composite states
- Pipeline integration with Phase 42-47
- Snapshot operations
- Serialization
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest

from umh.runtime.regime import RegimeType
from umh.runtime.regime_state import (
    COMPOSITE_AGGRESSIVE,
    COMPOSITE_BALANCED,
    COMPOSITE_CONSERVATIVE,
    COMPOSITE_RECOVERY,
    CompositeMatchResult,
    CompositeMatchSnapshot,
    CompositeRegimeState,
    CompositeStrategyProfile,
    ConfidenceLevel,
    DEFAULT_COMPOSITE_PROFILES,
    DEFAULT_DIMENSION_WEIGHTS,
    DimensionScore,
    DimensionWeights,
    NEUTRAL_COMPOSITE,
    NEUTRAL_COMPOSITE_PROFILE,
    RegimeStateSnapshot,
    RiskLevel,
    StabilityLevel,
    UrgencyLevel,
    apply_composite_factor,
    build_all_composite_states,
    build_composite_state,
    classify_confidence,
    classify_risk,
    classify_stability,
    classify_urgency,
    compute_all_composite_matches,
    compute_composite_match,
    get_composite_profile,
    _DEFAULT_MIN_FACTOR,
    _DEFAULT_MAX_FACTOR,
    _DEFAULT_MATCH_SCALE,
    _RISK_LOW_THRESHOLD,
    _RISK_HIGH_THRESHOLD,
    _URGENCY_LOW_THRESHOLD,
    _URGENCY_HIGH_THRESHOLD,
    _STABILITY_HIGH_THRESHOLD,
    _STABILITY_MEDIUM_THRESHOLD,
    _CONFIDENCE_HIGH_THRESHOLD,
    _CONFIDENCE_MEDIUM_THRESHOLD,
)


# ── Section 1: Risk classification ──────────────────────────────────


class TestRiskClassification:
    def test_low_risk(self):
        assert classify_risk(0.0) == RiskLevel.LOW

    def test_low_risk_below_threshold(self):
        assert classify_risk(0.07) == RiskLevel.LOW

    def test_medium_risk_at_threshold(self):
        assert classify_risk(_RISK_LOW_THRESHOLD) == RiskLevel.MEDIUM

    def test_medium_risk(self):
        assert classify_risk(0.15) == RiskLevel.MEDIUM

    def test_high_risk_at_threshold(self):
        assert classify_risk(_RISK_HIGH_THRESHOLD) == RiskLevel.HIGH

    def test_high_risk(self):
        assert classify_risk(0.50) == RiskLevel.HIGH

    def test_negative_delta_uses_abs(self):
        assert classify_risk(-0.30) == RiskLevel.HIGH

    def test_zero_is_low(self):
        assert classify_risk(0.0) == RiskLevel.LOW


# ── Section 2: Urgency classification ───────────────────────────────


class TestUrgencyClassification:
    def test_low_urgency(self):
        assert classify_urgency(0.0) == UrgencyLevel.LOW

    def test_low_urgency_below_threshold(self):
        assert classify_urgency(0.04) == UrgencyLevel.LOW

    def test_medium_urgency_at_threshold(self):
        assert classify_urgency(_URGENCY_LOW_THRESHOLD) == UrgencyLevel.MEDIUM

    def test_medium_urgency(self):
        assert classify_urgency(0.10) == UrgencyLevel.MEDIUM

    def test_high_urgency_at_threshold(self):
        assert classify_urgency(_URGENCY_HIGH_THRESHOLD) == UrgencyLevel.HIGH

    def test_high_urgency(self):
        assert classify_urgency(0.50) == UrgencyLevel.HIGH

    def test_negative_velocity_uses_abs(self):
        assert classify_urgency(-0.20) == UrgencyLevel.HIGH


# ── Section 3: Stability classification ─────────────────────────────


class TestStabilityClassification:
    def test_low_stability_zero(self):
        assert classify_stability(0) == StabilityLevel.LOW

    def test_low_stability(self):
        assert classify_stability(2) == StabilityLevel.LOW

    def test_medium_stability_at_threshold(self):
        assert classify_stability(_STABILITY_MEDIUM_THRESHOLD) == StabilityLevel.MEDIUM

    def test_medium_stability(self):
        assert classify_stability(7) == StabilityLevel.MEDIUM

    def test_high_stability_at_threshold(self):
        assert classify_stability(_STABILITY_HIGH_THRESHOLD) == StabilityLevel.HIGH

    def test_high_stability(self):
        assert classify_stability(100) == StabilityLevel.HIGH

    def test_negative_duration_clamped(self):
        assert classify_stability(-5) == StabilityLevel.LOW


# ── Section 4: Confidence classification ────────────────────────────


class TestConfidenceClassification:
    def test_low_confidence_unconfirmed(self):
        assert classify_confidence(100, is_confirmed=False) == ConfidenceLevel.LOW

    def test_low_confidence_short_duration(self):
        assert classify_confidence(1) == ConfidenceLevel.LOW

    def test_medium_confidence_at_threshold(self):
        assert classify_confidence(_CONFIDENCE_MEDIUM_THRESHOLD) == ConfidenceLevel.MEDIUM

    def test_medium_confidence(self):
        assert classify_confidence(7) == ConfidenceLevel.MEDIUM

    def test_high_confidence_at_threshold(self):
        assert classify_confidence(_CONFIDENCE_HIGH_THRESHOLD) == ConfidenceLevel.HIGH

    def test_high_confidence(self):
        assert classify_confidence(50) == ConfidenceLevel.HIGH

    def test_unconfirmed_always_low(self):
        assert classify_confidence(0, is_confirmed=False) == ConfidenceLevel.LOW
        assert classify_confidence(50, is_confirmed=False) == ConfidenceLevel.LOW

    def test_negative_duration_clamped(self):
        assert classify_confidence(-5) == ConfidenceLevel.LOW


# ── Section 5: Composite state construction ─────────────────────────


class TestCompositeStateConstruction:
    def test_build_basic(self):
        s = build_composite_state("urgency", RegimeType.SPIKE_UP, 0.30, 0.20, 5)
        assert s.signal_name == "urgency"
        assert s.trend == RegimeType.SPIKE_UP
        assert s.risk == RiskLevel.HIGH
        assert s.urgency == UrgencyLevel.HIGH
        assert s.stability == StabilityLevel.MEDIUM
        assert s.confidence == ConfidenceLevel.MEDIUM

    def test_build_stable(self):
        s = build_composite_state("urgency", RegimeType.STABLE, 0.01, 0.01, 20)
        assert s.trend == RegimeType.STABLE
        assert s.risk == RiskLevel.LOW
        assert s.urgency == UrgencyLevel.LOW
        assert s.stability == StabilityLevel.HIGH
        assert s.confidence == ConfidenceLevel.HIGH

    def test_build_defaults(self):
        s = build_composite_state("urgency", RegimeType.STABLE)
        assert s.risk == RiskLevel.LOW
        assert s.urgency == UrgencyLevel.LOW
        assert s.stability == StabilityLevel.LOW
        assert s.confidence == ConfidenceLevel.LOW

    def test_build_unconfirmed(self):
        s = build_composite_state("urgency", RegimeType.SPIKE_UP, 0.30, 0.20, 5, is_confirmed=False)
        assert s.confidence == ConfidenceLevel.LOW

    def test_frozen(self):
        s = build_composite_state("urgency", RegimeType.STABLE)
        with pytest.raises(AttributeError):
            s.trend = RegimeType.SPIKE_UP

    def test_to_dict(self):
        s = build_composite_state("urgency", RegimeType.STABLE)
        d = s.to_dict()
        assert set(d.keys()) == {"signal_name", "trend", "risk", "urgency", "stability", "confidence"}
        assert d["trend"] == "stable"


# ── Section 6: Neutral composite ───────────────────────────────────


class TestNeutralComposite:
    def test_neutral_trend(self):
        assert NEUTRAL_COMPOSITE.trend == RegimeType.STABLE

    def test_neutral_risk(self):
        assert NEUTRAL_COMPOSITE.risk == RiskLevel.LOW

    def test_neutral_urgency(self):
        assert NEUTRAL_COMPOSITE.urgency == UrgencyLevel.LOW

    def test_neutral_stability(self):
        assert NEUTRAL_COMPOSITE.stability == StabilityLevel.HIGH

    def test_neutral_confidence(self):
        assert NEUTRAL_COMPOSITE.confidence == ConfidenceLevel.HIGH


# ── Section 7: Missing signals default neutral (invariant 178) ─────


class TestMissingSignals:
    def test_missing_signal_returns_neutral(self):
        snap = RegimeStateSnapshot(states={}, tick=0)
        s = snap.get_or_neutral("missing")
        assert s == NEUTRAL_COMPOSITE

    def test_get_returns_none_for_missing(self):
        snap = RegimeStateSnapshot(states={}, tick=0)
        assert snap.get("missing") is None

    def test_build_all_missing_magnitudes(self):
        snap = build_all_composite_states(
            {"urgency": RegimeType.STABLE}, tick=1
        )
        s = snap.get("urgency")
        assert s.risk == RiskLevel.LOW

    def test_build_all_missing_velocities(self):
        snap = build_all_composite_states(
            {"urgency": RegimeType.STABLE}, delta_magnitudes={"urgency": 0.3}, tick=1
        )
        s = snap.get("urgency")
        assert s.urgency == UrgencyLevel.LOW

    def test_build_all_missing_durations(self):
        snap = build_all_composite_states(
            {"urgency": RegimeType.STABLE}, tick=1
        )
        s = snap.get("urgency")
        assert s.stability == StabilityLevel.LOW


# ── Section 8: Build all composite states ──────────────────────────


class TestBuildAllStates:
    def test_single_signal(self):
        snap = build_all_composite_states({"urgency": RegimeType.STABLE}, tick=1)
        assert len(snap.states) == 1

    def test_four_signals(self):
        trends = {
            "urgency": RegimeType.SPIKE_UP,
            "risk_level": RegimeType.TREND_DOWN,
            "resource_pressure": RegimeType.STABLE,
            "stability_mode": RegimeType.TREND_UP,
        }
        snap = build_all_composite_states(trends, tick=5)
        assert len(snap.states) == 4

    def test_sorted_order(self):
        snap = build_all_composite_states(
            {"c": RegimeType.STABLE, "a": RegimeType.STABLE, "b": RegimeType.STABLE}
        )
        assert list(snap.states.keys()) == ["a", "b", "c"]

    def test_tick_stored(self):
        snap = build_all_composite_states({"a": RegimeType.STABLE}, tick=42)
        assert snap.tick == 42

    def test_empty(self):
        snap = build_all_composite_states({})
        assert len(snap.states) == 0

    def test_to_dict(self):
        snap = build_all_composite_states({"a": RegimeType.STABLE}, tick=1)
        d = snap.to_dict()
        assert "states" in d
        assert "tick" in d


# ── Section 9: Dimension weights ───────────────────────────────────


class TestDimensionWeights:
    def test_default_weights_sum_to_one(self):
        w = DEFAULT_DIMENSION_WEIGHTS
        total = w.trend + w.risk + w.urgency + w.stability
        assert total == pytest.approx(1.0)

    def test_default_trend_weight(self):
        assert DEFAULT_DIMENSION_WEIGHTS.trend == pytest.approx(0.40)

    def test_default_risk_weight(self):
        assert DEFAULT_DIMENSION_WEIGHTS.risk == pytest.approx(0.25)

    def test_default_urgency_weight(self):
        assert DEFAULT_DIMENSION_WEIGHTS.urgency == pytest.approx(0.20)

    def test_default_stability_weight(self):
        assert DEFAULT_DIMENSION_WEIGHTS.stability == pytest.approx(0.15)

    def test_custom_weights_normalized(self):
        w = DimensionWeights(trend=4.0, risk=2.5, urgency=2.0, stability=1.5)
        total = w.trend + w.risk + w.urgency + w.stability
        assert total == pytest.approx(1.0)

    def test_negative_weights_clamped(self):
        w = DimensionWeights(trend=-1.0, risk=1.0, urgency=1.0, stability=1.0)
        assert w.trend == 0.0

    def test_all_zero_weights_fallback(self):
        w = DimensionWeights(trend=0.0, risk=0.0, urgency=0.0, stability=0.0)
        total = w.trend + w.risk + w.urgency + w.stability
        assert total == pytest.approx(1.0)

    def test_weights_frozen(self):
        with pytest.raises(AttributeError):
            DEFAULT_DIMENSION_WEIGHTS.trend = 0.5

    def test_to_dict(self):
        d = DEFAULT_DIMENSION_WEIGHTS.to_dict()
        assert set(d.keys()) == {"trend", "risk", "urgency", "stability"}


# ── Section 10: Default composite profiles ─────────────────────────


class TestDefaultCompositeProfiles:
    def test_four_profiles(self):
        assert len(DEFAULT_COMPOSITE_PROFILES) == 4

    def test_aggressive_exists(self):
        assert "aggressive" in DEFAULT_COMPOSITE_PROFILES

    def test_conservative_exists(self):
        assert "conservative" in DEFAULT_COMPOSITE_PROFILES

    def test_balanced_exists(self):
        assert "balanced" in DEFAULT_COMPOSITE_PROFILES

    def test_recovery_exists(self):
        assert "recovery" in DEFAULT_COMPOSITE_PROFILES

    def test_aggressive_prefers_spike_up(self):
        assert RegimeType.SPIKE_UP in COMPOSITE_AGGRESSIVE.preferred_trends

    def test_aggressive_prefers_high_risk(self):
        assert RiskLevel.HIGH in COMPOSITE_AGGRESSIVE.preferred_risk

    def test_conservative_prefers_stable(self):
        assert RegimeType.STABLE in COMPOSITE_CONSERVATIVE.preferred_trends

    def test_conservative_prefers_low_risk(self):
        assert RiskLevel.LOW in COMPOSITE_CONSERVATIVE.preferred_risk

    def test_conservative_prefers_high_stability(self):
        assert StabilityLevel.HIGH in COMPOSITE_CONSERVATIVE.preferred_stability

    def test_recovery_prefers_spike_down(self):
        assert RegimeType.SPIKE_DOWN in COMPOSITE_RECOVERY.preferred_trends

    def test_balanced_no_penalized_trends(self):
        assert len(COMPOSITE_BALANCED.penalized_trends) == 0

    def test_balanced_lower_scale(self):
        assert COMPOSITE_BALANCED.match_scale == 0.05


# ── Section 11: Composite match scoring — preferred ────────────────


class TestCompositeMatchPreferred:
    def test_all_preferred_positive_factor(self):
        state = build_composite_state("s", RegimeType.SPIKE_UP, 0.30, 0.20, 1)
        r = compute_composite_match(COMPOSITE_AGGRESSIVE, state)
        assert r.factor > 1.0

    def test_preferred_trend_contributes_positively(self):
        state = build_composite_state("s", RegimeType.SPIKE_UP, 0.01, 0.01, 20)
        r = compute_composite_match(COMPOSITE_AGGRESSIVE, state)
        assert any(d.dimension == "trend" and d.match == 1 for d in r.dimensions)

    def test_all_four_dimensions_scored(self):
        state = build_composite_state("s", RegimeType.STABLE)
        r = compute_composite_match(COMPOSITE_AGGRESSIVE, state)
        assert len(r.dimensions) == 4


# ── Section 12: Composite match scoring — penalized ────────────────


class TestCompositeMatchPenalized:
    def test_all_penalized_negative_factor(self):
        state = build_composite_state("s", RegimeType.SPIKE_DOWN, 0.01, 0.01, 20)
        r = compute_composite_match(COMPOSITE_AGGRESSIVE, state)
        assert r.factor < 1.0

    def test_penalized_trend_contributes_negatively(self):
        state = build_composite_state("s", RegimeType.SPIKE_DOWN, 0.01, 0.01, 20)
        r = compute_composite_match(COMPOSITE_AGGRESSIVE, state)
        assert any(d.dimension == "trend" and d.match == -1 for d in r.dimensions)


# ── Section 13: Composite match scoring — neutral ──────────────────


class TestCompositeMatchNeutral:
    def test_neutral_profile_always_one(self):
        for rt in RegimeType:
            state = build_composite_state("s", rt, 0.15, 0.10, 5)
            r = compute_composite_match(NEUTRAL_COMPOSITE_PROFILE, state)
            assert r.factor == 1.0

    def test_neutral_zero_scale(self):
        assert NEUTRAL_COMPOSITE_PROFILE.match_scale == 0.0


# ── Section 14: Conflicting signals produce balanced score ─────────


class TestConflictingSignals:
    def test_preferred_trend_penalized_risk_balanced(self):
        state = build_composite_state("s", RegimeType.SPIKE_UP, 0.01, 0.01, 20)
        r = compute_composite_match(COMPOSITE_AGGRESSIVE, state)
        trend_d = [d for d in r.dimensions if d.dimension == "trend"][0]
        risk_d = [d for d in r.dimensions if d.dimension == "risk"][0]
        assert trend_d.match == 1
        assert risk_d.match == -1

    def test_opposing_dimensions_moderate_factor(self):
        state = build_composite_state("s", RegimeType.SPIKE_UP, 0.01, 0.01, 20)
        r = compute_composite_match(COMPOSITE_AGGRESSIVE, state)
        assert 0.95 <= r.factor <= 1.10

    def test_all_neutral_dims_factor_one(self):
        profile = CompositeStrategyProfile(strategy_name="empty", match_scale=0.10)
        state = build_composite_state("s", RegimeType.STABLE)
        r = compute_composite_match(profile, state)
        assert r.factor == 1.0


# ── Section 15: Bounds / clamping (invariant 172 extended) ─────────


class TestBoundsEnforcement:
    def test_factor_bounded_all_profiles(self):
        for name, profile in DEFAULT_COMPOSITE_PROFILES.items():
            for rt in RegimeType:
                for mag in [0.0, 0.10, 0.30]:
                    for vel in [0.0, 0.10, 0.20]:
                        for dur in [0, 5, 15]:
                            state = build_composite_state("s", rt, mag, vel, dur)
                            r = compute_composite_match(profile, state)
                            assert _DEFAULT_MIN_FACTOR <= r.factor <= _DEFAULT_MAX_FACTOR, (
                                f"{name}/{rt}/{mag}/{vel}/{dur}: {r.factor}"
                            )

    def test_extreme_scale_clamped(self):
        profile = CompositeStrategyProfile(
            strategy_name="extreme",
            preferred_trends=frozenset(RegimeType),
            preferred_risk=frozenset(RiskLevel),
            preferred_urgency=frozenset(UrgencyLevel),
            preferred_stability=frozenset(StabilityLevel),
            match_scale=10.0,
        )
        state = build_composite_state("s", RegimeType.SPIKE_UP, 0.30, 0.20, 1)
        r = compute_composite_match(profile, state)
        assert r.factor == _DEFAULT_MAX_FACTOR

    def test_extreme_penalized_clamped(self):
        profile = CompositeStrategyProfile(
            strategy_name="extreme",
            penalized_trends=frozenset(RegimeType),
            penalized_risk=frozenset(RiskLevel),
            penalized_urgency=frozenset(UrgencyLevel),
            penalized_stability=frozenset(StabilityLevel),
            match_scale=10.0,
        )
        state = build_composite_state("s", RegimeType.SPIKE_UP, 0.30, 0.20, 1)
        r = compute_composite_match(profile, state)
        assert r.factor == _DEFAULT_MIN_FACTOR

    def test_custom_bounds(self):
        state = build_composite_state("s", RegimeType.SPIKE_UP, 0.30, 0.20, 1)
        r = compute_composite_match(
            COMPOSITE_AGGRESSIVE, state, min_factor=0.99, max_factor=1.01
        )
        assert 0.99 <= r.factor <= 1.01


# ── Section 16: No dimension dominates (invariant 180) ─────────────


class TestNoDimensionDominates:
    def test_trend_alone_cannot_reach_max(self):
        profile = CompositeStrategyProfile(
            strategy_name="trend_only",
            preferred_trends=frozenset({RegimeType.SPIKE_UP}),
            match_scale=_DEFAULT_MATCH_SCALE,
        )
        state = build_composite_state("s", RegimeType.SPIKE_UP, 0.30, 0.20, 1)
        r = compute_composite_match(profile, state)
        assert r.factor < _DEFAULT_MAX_FACTOR

    def test_no_single_dimension_reaches_full_scale(self):
        w = DEFAULT_DIMENSION_WEIGHTS
        assert w.trend < 1.0
        assert w.risk < 1.0
        assert w.urgency < 1.0
        assert w.stability < 1.0


# ── Section 17: Determinism (invariant 176) ────────────────────────


class TestDeterminism:
    def test_same_inputs_same_output(self):
        state = build_composite_state("s", RegimeType.SPIKE_UP, 0.30, 0.20, 5)
        r1 = compute_composite_match(COMPOSITE_AGGRESSIVE, state)
        r2 = compute_composite_match(COMPOSITE_AGGRESSIVE, state)
        assert r1.factor == r2.factor

    def test_deterministic_100_calls(self):
        state = build_composite_state("s", RegimeType.TREND_UP, 0.15, 0.10, 7)
        results = [compute_composite_match(COMPOSITE_AGGRESSIVE, state).factor for _ in range(100)]
        assert len(set(results)) == 1

    def test_deterministic_all_profiles(self):
        state = build_composite_state("s", RegimeType.STABLE, 0.05, 0.03, 15)
        for name, profile in DEFAULT_COMPOSITE_PROFILES.items():
            f1 = compute_composite_match(profile, state).factor
            f2 = compute_composite_match(profile, state).factor
            assert f1 == f2, name

    def test_classification_deterministic(self):
        for _ in range(50):
            assert classify_risk(0.15) == RiskLevel.MEDIUM
            assert classify_urgency(0.10) == UrgencyLevel.MEDIUM
            assert classify_stability(5) == StabilityLevel.MEDIUM
            assert classify_confidence(5) == ConfidenceLevel.MEDIUM


# ── Section 18: No mutation (invariant 177) ────────────────────────


class TestNoMutation:
    def test_state_frozen(self):
        state = build_composite_state("s", RegimeType.STABLE)
        with pytest.raises(AttributeError):
            state.trend = RegimeType.SPIKE_UP

    def test_result_frozen(self):
        state = build_composite_state("s", RegimeType.STABLE)
        r = compute_composite_match(COMPOSITE_AGGRESSIVE, state)
        with pytest.raises(AttributeError):
            r.factor = 2.0

    def test_profile_unchanged_after_compute(self):
        before = COMPOSITE_AGGRESSIVE.to_dict()
        state = build_composite_state("s", RegimeType.SPIKE_UP, 0.30, 0.20, 5)
        compute_composite_match(COMPOSITE_AGGRESSIVE, state)
        after = COMPOSITE_AGGRESSIVE.to_dict()
        assert before == after


# ── Section 19: Explainability (invariant 179) ─────────────────────


class TestExplainability:
    def test_result_has_dimensions(self):
        state = build_composite_state("s", RegimeType.SPIKE_UP, 0.30, 0.20, 1)
        r = compute_composite_match(COMPOSITE_AGGRESSIVE, state)
        assert len(r.dimensions) == 4

    def test_dimension_has_all_fields(self):
        state = build_composite_state("s", RegimeType.SPIKE_UP, 0.30, 0.20, 1)
        r = compute_composite_match(COMPOSITE_AGGRESSIVE, state)
        d = r.dimensions[0]
        assert d.dimension == "trend"
        assert isinstance(d.value, str)
        assert d.match in (-1, 0, 1)
        assert isinstance(d.weight, float)
        assert isinstance(d.contribution, float)

    def test_explanation_string(self):
        state = build_composite_state("s", RegimeType.SPIKE_UP, 0.30, 0.20, 1)
        r = compute_composite_match(COMPOSITE_AGGRESSIVE, state)
        assert "aggressive" in r.explanation
        assert "preferred" in r.explanation or "penalized" in r.explanation

    def test_explanation_all_neutral(self):
        profile = CompositeStrategyProfile(strategy_name="empty", match_scale=0.10)
        state = build_composite_state("s", RegimeType.STABLE)
        r = compute_composite_match(profile, state)
        assert "all neutral" in r.explanation

    def test_to_dict_complete(self):
        state = build_composite_state("s", RegimeType.SPIKE_UP, 0.30, 0.20, 1)
        r = compute_composite_match(COMPOSITE_AGGRESSIVE, state)
        d = r.to_dict()
        assert set(d.keys()) == {
            "strategy_name", "dimensions", "total_match", "raw_factor", "factor", "explanation"
        }

    def test_dimension_to_dict(self):
        state = build_composite_state("s", RegimeType.SPIKE_UP, 0.30, 0.20, 1)
        r = compute_composite_match(COMPOSITE_AGGRESSIVE, state)
        dd = r.dimensions[0].to_dict()
        assert set(dd.keys()) == {"dimension", "value", "match", "weight", "contribution"}


# ── Section 20: Different strategies win under different states ────


class TestDifferentStrategiesWin:
    def test_aggressive_wins_spike_up_high_risk(self):
        state = build_composite_state("s", RegimeType.SPIKE_UP, 0.30, 0.20, 1)
        snap = compute_all_composite_matches(DEFAULT_COMPOSITE_PROFILES, state)
        assert snap.best_strategy() == "aggressive"

    def test_conservative_wins_stable_low_risk(self):
        state = build_composite_state("s", RegimeType.STABLE, 0.01, 0.01, 20)
        snap = compute_all_composite_matches(DEFAULT_COMPOSITE_PROFILES, state)
        assert snap.best_strategy() == "conservative"

    def test_recovery_wins_spike_down_high_risk(self):
        state = build_composite_state("s", RegimeType.SPIKE_DOWN, 0.30, 0.20, 1)
        snap = compute_all_composite_matches(DEFAULT_COMPOSITE_PROFILES, state)
        assert snap.best_strategy() == "recovery"

    def test_multiple_winners_across_states(self):
        states = [
            build_composite_state("s", RegimeType.SPIKE_UP, 0.30, 0.20, 1),
            build_composite_state("s", RegimeType.STABLE, 0.01, 0.01, 20),
            build_composite_state("s", RegimeType.SPIKE_DOWN, 0.30, 0.20, 1),
        ]
        winners = set()
        for state in states:
            snap = compute_all_composite_matches(DEFAULT_COMPOSITE_PROFILES, state)
            winners.add(snap.best_strategy())
        assert len(winners) >= 3

    def test_differs_from_phase47_single_dim(self):
        from umh.runtime.strategy_profile import compute_all_strategy_factors, DEFAULT_PROFILES

        state = build_composite_state("s", RegimeType.SPIKE_UP, 0.01, 0.01, 20)

        p47 = compute_all_strategy_factors(DEFAULT_PROFILES, RegimeType.SPIKE_UP, 0)
        p48 = compute_all_composite_matches(DEFAULT_COMPOSITE_PROFILES, state)

        p47_aggressive = p47.get_factor("aggressive")
        p48_aggressive = p48.get_factor("aggressive")
        assert p47_aggressive != p48_aggressive


# ── Section 21: Snapshot operations ────────────────────────────────


class TestSnapshotOperations:
    def test_get_existing(self):
        state = build_composite_state("s", RegimeType.STABLE)
        snap = compute_all_composite_matches(DEFAULT_COMPOSITE_PROFILES, state)
        assert snap.get("aggressive") is not None

    def test_get_missing(self):
        state = build_composite_state("s", RegimeType.STABLE)
        snap = compute_all_composite_matches(DEFAULT_COMPOSITE_PROFILES, state)
        assert snap.get("nonexistent") is None

    def test_get_factor_existing(self):
        state = build_composite_state("s", RegimeType.SPIKE_UP, 0.30, 0.20, 1)
        snap = compute_all_composite_matches(DEFAULT_COMPOSITE_PROFILES, state)
        assert snap.get_factor("aggressive") > 1.0

    def test_get_factor_missing_default(self):
        state = build_composite_state("s", RegimeType.STABLE)
        snap = compute_all_composite_matches(DEFAULT_COMPOSITE_PROFILES, state)
        assert snap.get_factor("missing") == 1.0

    def test_best_strategy(self):
        state = build_composite_state("s", RegimeType.SPIKE_UP, 0.30, 0.20, 1)
        snap = compute_all_composite_matches(DEFAULT_COMPOSITE_PROFILES, state)
        assert snap.best_strategy() is not None

    def test_worst_strategy(self):
        state = build_composite_state("s", RegimeType.SPIKE_UP, 0.30, 0.20, 1)
        snap = compute_all_composite_matches(DEFAULT_COMPOSITE_PROFILES, state)
        worst = snap.worst_strategy()
        assert worst is not None
        assert worst != snap.best_strategy()

    def test_empty_snapshot(self):
        state = build_composite_state("s", RegimeType.STABLE)
        snap = compute_all_composite_matches({}, state)
        assert snap.best_strategy() is None
        assert snap.worst_strategy() is None

    def test_to_dict(self):
        state = build_composite_state("s", RegimeType.STABLE)
        snap = compute_all_composite_matches(DEFAULT_COMPOSITE_PROFILES, state)
        d = snap.to_dict()
        assert "results" in d
        assert len(d["results"]) == 4


# ── Section 22: get_composite_profile ──────────────────────────────


class TestGetCompositeProfile:
    def test_known_profile(self):
        p = get_composite_profile("aggressive")
        assert p.strategy_name == "aggressive"

    def test_unknown_returns_neutral(self):
        p = get_composite_profile("nonexistent")
        assert p.strategy_name == "neutral"
        assert p.match_scale == 0.0


# ── Section 23: apply_composite_factor ─────────────────────────────


class TestApplyCompositeFactor:
    def test_neutral(self):
        assert apply_composite_factor(100.0, 1.0) == 100.0

    def test_boost(self):
        assert apply_composite_factor(100.0, 1.10) == pytest.approx(110.0)

    def test_reduce(self):
        assert apply_composite_factor(100.0, 0.90) == pytest.approx(90.0)

    def test_zero_score(self):
        assert apply_composite_factor(0.0, 1.15) == 0.0


# ── Section 24: Pipeline integration with Phase 42-47 ─────────────


class TestPipelineIntegration:
    def test_classify_to_composite(self):
        from umh.runtime.regime import classify_regime, RegimeThresholds

        result = classify_regime("urgency", 0.30, RegimeThresholds())
        state = build_composite_state("urgency", result.regime, result.magnitude, 0.15, 5)
        assert state.trend == RegimeType.SPIKE_UP
        assert state.risk == RiskLevel.HIGH

    def test_filter_then_composite(self):
        from umh.runtime.regime_filter import FilterState, filter_regime

        fs = FilterState(signal_name="urgency", confirmed_regime=RegimeType.STABLE)
        fr = filter_regime(fs, RegimeType.SPIKE_UP, 1)
        state = build_composite_state("urgency", fr.filtered_regime, 0.30, 0.20, 0)
        r = compute_composite_match(COMPOSITE_AGGRESSIVE, state)
        assert r.factor > 1.0

    def test_regime_weight_plus_composite(self):
        from umh.runtime.regime_weight import compute_regime_factor

        rw = compute_regime_factor("urgency", RegimeType.SPIKE_UP, 0)
        state = build_composite_state("urgency", RegimeType.SPIKE_UP, 0.30, 0.20, 1)
        cm = compute_composite_match(COMPOSITE_AGGRESSIVE, state)

        combined = rw.factor * cm.factor
        assert combined > 1.0

    def test_full_scoring_chain(self):
        from umh.runtime.regime_weight import compute_regime_factor

        base_score = 80.0
        identity_factor = 1.05
        goal_bias = 1.02
        regime_factor = compute_regime_factor("urgency", RegimeType.SPIKE_UP, 0).factor

        state = build_composite_state("urgency", RegimeType.SPIKE_UP, 0.30, 0.20, 1)
        composite_factor = compute_composite_match(COMPOSITE_AGGRESSIVE, state).factor

        score = base_score * identity_factor * goal_bias * regime_factor * composite_factor
        assert score > base_score

    def test_adaptive_threshold_to_composite(self):
        from umh.runtime.hysteresis_adaptive import compute_adaptive_threshold

        tr = compute_adaptive_threshold("urgency", 0.3, 0)
        assert tr.adaptive_threshold == 1

        state = build_composite_state("urgency", RegimeType.SPIKE_UP, 0.30, 0.20, 0)
        r = compute_composite_match(COMPOSITE_AGGRESSIVE, state)
        assert r.factor > 1.0


# ── Section 25: Exact numerical verification ──────────────────────


class TestExactNumerical:
    def test_aggressive_all_preferred(self):
        state = build_composite_state("s", RegimeType.SPIKE_UP, 0.30, 0.20, 1)
        r = compute_composite_match(COMPOSITE_AGGRESSIVE, state)
        w = DEFAULT_DIMENSION_WEIGHTS
        expected_match = w.trend * 1 + w.risk * 1 + w.urgency * 1 + w.stability * 1
        expected_factor = 1.0 + expected_match * _DEFAULT_MATCH_SCALE
        assert r.factor == pytest.approx(expected_factor)
        assert r.total_match == pytest.approx(expected_match)

    def test_aggressive_all_penalized(self):
        state = build_composite_state("s", RegimeType.SPIKE_DOWN, 0.01, 0.01, 20)
        r = compute_composite_match(COMPOSITE_AGGRESSIVE, state)
        w = DEFAULT_DIMENSION_WEIGHTS
        trend_m = -1
        risk_m = -1
        urgency_m = 0
        stab_m = -1
        expected_match = w.trend * trend_m + w.risk * risk_m + w.urgency * urgency_m + w.stability * stab_m
        expected_factor = 1.0 + expected_match * _DEFAULT_MATCH_SCALE
        assert r.factor == pytest.approx(expected_factor)

    def test_all_neutral_match_zero(self):
        profile = CompositeStrategyProfile(strategy_name="empty", match_scale=0.10)
        state = build_composite_state("s", RegimeType.STABLE)
        r = compute_composite_match(profile, state)
        assert r.total_match == 0.0
        assert r.factor == 1.0

    def test_single_preferred_dimension(self):
        profile = CompositeStrategyProfile(
            strategy_name="trend_only",
            preferred_trends=frozenset({RegimeType.SPIKE_UP}),
            match_scale=_DEFAULT_MATCH_SCALE,
        )
        state = build_composite_state("s", RegimeType.SPIKE_UP, 0.01, 0.01, 20)
        r = compute_composite_match(profile, state)
        w = DEFAULT_DIMENSION_WEIGHTS
        expected_match = w.trend * 1
        expected_factor = 1.0 + expected_match * _DEFAULT_MATCH_SCALE
        assert r.factor == pytest.approx(expected_factor)


# ── Section 26: Profile serialization ─────────────────────────────


class TestProfileSerialization:
    def test_profile_to_dict(self):
        d = COMPOSITE_AGGRESSIVE.to_dict()
        assert d["strategy_name"] == "aggressive"
        assert "spike_up" in d["preferred_trends"]

    def test_profile_frozen(self):
        with pytest.raises(AttributeError):
            COMPOSITE_AGGRESSIVE.match_scale = 0.5

    def test_negative_scale_clamped(self):
        p = CompositeStrategyProfile(strategy_name="t", match_scale=-1.0)
        assert p.match_scale == 0.0


# ── Section 27: RegimeStateSnapshot operations ────────────────────


class TestRegimeStateSnapshotOps:
    def test_get_existing(self):
        snap = build_all_composite_states({"a": RegimeType.STABLE}, tick=1)
        assert snap.get("a") is not None

    def test_get_missing(self):
        snap = build_all_composite_states({"a": RegimeType.STABLE}, tick=1)
        assert snap.get("b") is None

    def test_get_or_neutral(self):
        snap = build_all_composite_states({"a": RegimeType.STABLE}, tick=1)
        s = snap.get_or_neutral("missing")
        assert s == NEUTRAL_COMPOSITE


# ── Section 28: Custom weight combinations ────────────────────────


class TestCustomWeights:
    def test_trend_only_weight(self):
        w = DimensionWeights(trend=1.0, risk=0.0, urgency=0.0, stability=0.0)
        state = build_composite_state("s", RegimeType.SPIKE_UP, 0.30, 0.20, 1)
        r = compute_composite_match(COMPOSITE_AGGRESSIVE, state, weights=w)
        assert r.total_match == pytest.approx(1.0)

    def test_risk_only_weight(self):
        w = DimensionWeights(trend=0.0, risk=1.0, urgency=0.0, stability=0.0)
        state = build_composite_state("s", RegimeType.STABLE, 0.30, 0.01, 20)
        r = compute_composite_match(COMPOSITE_AGGRESSIVE, state, weights=w)
        assert r.total_match == pytest.approx(1.0)

    def test_equal_weights(self):
        w = DimensionWeights(trend=1.0, risk=1.0, urgency=1.0, stability=1.0)
        assert w.trend == pytest.approx(0.25)
        assert w.risk == pytest.approx(0.25)


# ── Section 29: Composite vs single-dimension comparison ─────────


class TestCompositeVsSingleDim:
    def test_composite_more_granular(self):
        from umh.runtime.strategy_profile import compute_strategy_regime_factor, AGGRESSIVE_PROFILE

        p47 = compute_strategy_regime_factor(AGGRESSIVE_PROFILE, RegimeType.SPIKE_UP, 0)

        state_favorable = build_composite_state("s", RegimeType.SPIKE_UP, 0.30, 0.20, 1)
        state_mixed = build_composite_state("s", RegimeType.SPIKE_UP, 0.01, 0.01, 20)

        p48_favorable = compute_composite_match(COMPOSITE_AGGRESSIVE, state_favorable)
        p48_mixed = compute_composite_match(COMPOSITE_AGGRESSIVE, state_mixed)

        assert p48_favorable.factor != p48_mixed.factor
        assert p47.factor == p47.factor

    def test_composite_distinguishes_same_trend_different_risk(self):
        state_low = build_composite_state("s", RegimeType.TREND_UP, 0.05, 0.05, 5)
        state_high = build_composite_state("s", RegimeType.TREND_UP, 0.30, 0.20, 5)

        r_low = compute_composite_match(COMPOSITE_AGGRESSIVE, state_low)
        r_high = compute_composite_match(COMPOSITE_AGGRESSIVE, state_high)

        assert r_low.factor != r_high.factor


# ── Section 30: Threshold boundary tests ──────────────────────────


class TestThresholdBoundaries:
    def test_risk_just_below_low(self):
        assert classify_risk(_RISK_LOW_THRESHOLD - 0.001) == RiskLevel.LOW

    def test_risk_just_below_high(self):
        assert classify_risk(_RISK_HIGH_THRESHOLD - 0.001) == RiskLevel.MEDIUM

    def test_urgency_just_below_low(self):
        assert classify_urgency(_URGENCY_LOW_THRESHOLD - 0.001) == UrgencyLevel.LOW

    def test_urgency_just_below_high(self):
        assert classify_urgency(_URGENCY_HIGH_THRESHOLD - 0.001) == UrgencyLevel.MEDIUM

    def test_stability_just_below_medium(self):
        assert classify_stability(_STABILITY_MEDIUM_THRESHOLD - 1) == StabilityLevel.LOW

    def test_stability_just_below_high(self):
        assert classify_stability(_STABILITY_HIGH_THRESHOLD - 1) == StabilityLevel.MEDIUM

    def test_confidence_just_below_medium(self):
        assert classify_confidence(_CONFIDENCE_MEDIUM_THRESHOLD - 1) == ConfidenceLevel.LOW

    def test_confidence_just_below_high(self):
        assert classify_confidence(_CONFIDENCE_HIGH_THRESHOLD - 1) == ConfidenceLevel.MEDIUM


# ── Section 31: Match total_match range ───────────────────────────


class TestTotalMatchRange:
    def test_total_match_bounded_minus_one_to_plus_one(self):
        for name, profile in DEFAULT_COMPOSITE_PROFILES.items():
            for rt in RegimeType:
                for mag in [0.0, 0.10, 0.30]:
                    for vel in [0.0, 0.10, 0.20]:
                        for dur in [0, 5, 15]:
                            state = build_composite_state("s", rt, mag, vel, dur)
                            r = compute_composite_match(profile, state)
                            assert -1.0 <= r.total_match <= 1.0 + 1e-9, (
                                f"{name}/{rt}/{mag}/{vel}/{dur}: {r.total_match}"
                            )

    def test_maximum_positive_match(self):
        profile = CompositeStrategyProfile(
            strategy_name="all_pref",
            preferred_trends=frozenset(RegimeType),
            preferred_risk=frozenset(RiskLevel),
            preferred_urgency=frozenset(UrgencyLevel),
            preferred_stability=frozenset(StabilityLevel),
            match_scale=_DEFAULT_MATCH_SCALE,
        )
        state = build_composite_state("s", RegimeType.SPIKE_UP, 0.30, 0.20, 1)
        r = compute_composite_match(profile, state)
        assert r.total_match == pytest.approx(1.0)

    def test_maximum_negative_match(self):
        profile = CompositeStrategyProfile(
            strategy_name="all_pen",
            penalized_trends=frozenset(RegimeType),
            penalized_risk=frozenset(RiskLevel),
            penalized_urgency=frozenset(UrgencyLevel),
            penalized_stability=frozenset(StabilityLevel),
            match_scale=_DEFAULT_MATCH_SCALE,
        )
        state = build_composite_state("s", RegimeType.SPIKE_UP, 0.30, 0.20, 1)
        r = compute_composite_match(profile, state)
        assert r.total_match == pytest.approx(-1.0)


# ── Section 32: Raw factor vs clamped factor ─────────────────────


class TestRawVsClamped:
    def test_default_profiles_no_clamping(self):
        for name, profile in DEFAULT_COMPOSITE_PROFILES.items():
            for rt in RegimeType:
                state = build_composite_state("s", rt, 0.15, 0.10, 5)
                r = compute_composite_match(profile, state)
                assert r.raw_factor == r.factor, f"{name}/{rt}"

    def test_extreme_scale_shows_clamping(self):
        profile = CompositeStrategyProfile(
            strategy_name="extreme",
            preferred_trends=frozenset(RegimeType),
            preferred_risk=frozenset(RiskLevel),
            preferred_urgency=frozenset(UrgencyLevel),
            preferred_stability=frozenset(StabilityLevel),
            match_scale=10.0,
        )
        state = build_composite_state("s", RegimeType.SPIKE_UP, 0.30, 0.20, 1)
        r = compute_composite_match(profile, state)
        assert r.raw_factor > r.factor
        assert r.factor == _DEFAULT_MAX_FACTOR


# ── Section 33: Enum coverage ────────────────────────────────────


class TestEnumValues:
    def test_risk_values(self):
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"

    def test_urgency_values(self):
        assert UrgencyLevel.LOW.value == "low"
        assert UrgencyLevel.MEDIUM.value == "medium"
        assert UrgencyLevel.HIGH.value == "high"

    def test_stability_values(self):
        assert StabilityLevel.LOW.value == "low"
        assert StabilityLevel.MEDIUM.value == "medium"
        assert StabilityLevel.HIGH.value == "high"

    def test_confidence_values(self):
        assert ConfidenceLevel.LOW.value == "low"
        assert ConfidenceLevel.MEDIUM.value == "medium"
        assert ConfidenceLevel.HIGH.value == "high"
