"""
Tests for runtime.analytics_adapter — Analytics Adapter Layer.

Verifies: bounded outputs, deterministic behavior, no regressions,
disabled flag = no effect, stress test (repeated runs stable).

No LLM calls.  No randomness.  No external deps.  Deterministic.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.analytics_adapter import (
    NO_SIGNAL,
    MAX_CONFIDENCE_ADJUSTMENT,
    MAX_DIRECTIVE_BIAS,
    MAX_POLICY_BIAS,
    MAX_STRATEGY_BIAS,
    MIN_OBSERVATIONS,
    AnalyticsSignal,
    apply_analytics_to_policy,
    build_analytics_signal,
)
from umh.runtime_engine.policy_engine import (
    Policy,
    PolicySignals,
    select_policy,
)


# ---------------------------------------------------------------------------
# Section 1: NO_SIGNAL sentinel
# ---------------------------------------------------------------------------


def test_no_signal_is_zero():
    assert NO_SIGNAL.strategy_bias == 0.0
    assert NO_SIGNAL.policy_bias == 0.0
    assert NO_SIGNAL.directive_bias == 0.0
    assert NO_SIGNAL.confidence_adjustment == 0.0
    assert not NO_SIGNAL.is_active


def test_no_signal_to_dict():
    d = NO_SIGNAL.to_dict()
    assert d == {
        "strategy_bias": 0.0,
        "policy_bias": 0.0,
        "directive_bias": 0.0,
        "confidence_adjustment": 0.0,
    }


# ---------------------------------------------------------------------------
# Section 2: build_analytics_signal — None / empty / insufficient
# ---------------------------------------------------------------------------


def test_none_summary_returns_no_signal():
    assert build_analytics_signal(None) is NO_SIGNAL


def test_empty_summary_returns_no_signal():
    assert build_analytics_signal({}) is NO_SIGNAL


def test_insufficient_entries_returns_no_signal():
    summary = {"total_entries": MIN_OBSERVATIONS - 1}
    assert build_analytics_signal(summary) is NO_SIGNAL


def test_exactly_min_observations_produces_signal():
    summary = {
        "total_entries": MIN_OBSERVATIONS,
        "top_strategies": {"s1": 0.8, "s2": 0.4},
        "top_signal_correlations": {"sig1": 0.5},
        "directive_success": {"d1": 0.7},
        "plan_count": 5,
        "goal_count": 3,
    }
    sig = build_analytics_signal(summary)
    assert isinstance(sig, AnalyticsSignal)
    assert sig is not NO_SIGNAL


# ---------------------------------------------------------------------------
# Section 3: build_analytics_signal — bounded outputs
# ---------------------------------------------------------------------------


def test_strategy_bias_bounded():
    summary = {
        "total_entries": 100,
        "top_strategies": {"s1": 100.0, "s2": 0.0},
    }
    sig = build_analytics_signal(summary)
    assert -MAX_STRATEGY_BIAS <= sig.strategy_bias <= MAX_STRATEGY_BIAS


def test_policy_bias_bounded():
    summary = {
        "total_entries": 100,
        "top_signal_correlations": {"sig1": 999.0, "sig2": -999.0},
    }
    sig = build_analytics_signal(summary)
    assert -MAX_POLICY_BIAS <= sig.policy_bias <= MAX_POLICY_BIAS


def test_directive_bias_bounded():
    summary = {
        "total_entries": 100,
        "directive_success": {"d1": 999.0},
    }
    sig = build_analytics_signal(summary)
    assert -MAX_DIRECTIVE_BIAS <= sig.directive_bias <= MAX_DIRECTIVE_BIAS


def test_confidence_adjustment_bounded():
    summary = {
        "total_entries": 100,
        "plan_count": 1,
        "goal_count": 999,
    }
    sig = build_analytics_signal(summary)
    assert (
        -MAX_CONFIDENCE_ADJUSTMENT
        <= sig.confidence_adjustment
        <= MAX_CONFIDENCE_ADJUSTMENT
    )


def test_all_fields_bounded_extreme_input():
    summary = {
        "total_entries": 10000,
        "top_strategies": {f"s{i}": float(i * 100) for i in range(20)},
        "top_signal_correlations": {f"sig{i}": float(i * 50) for i in range(10)},
        "directive_success": {f"d{i}": float(i * 200) for i in range(10)},
        "plan_count": 1,
        "goal_count": 10000,
    }
    sig = build_analytics_signal(summary)
    assert -MAX_STRATEGY_BIAS <= sig.strategy_bias <= MAX_STRATEGY_BIAS
    assert -MAX_POLICY_BIAS <= sig.policy_bias <= MAX_POLICY_BIAS
    assert -MAX_DIRECTIVE_BIAS <= sig.directive_bias <= MAX_DIRECTIVE_BIAS
    assert (
        -MAX_CONFIDENCE_ADJUSTMENT
        <= sig.confidence_adjustment
        <= MAX_CONFIDENCE_ADJUSTMENT
    )


def test_negative_extreme_input_bounded():
    summary = {
        "total_entries": 10000,
        "top_strategies": {"s1": -1000.0, "s2": -999.0},
        "top_signal_correlations": {"sig1": -999.0},
        "directive_success": {"d1": -999.0},
        "plan_count": 10000,
        "goal_count": 1,
    }
    sig = build_analytics_signal(summary)
    assert -MAX_STRATEGY_BIAS <= sig.strategy_bias <= MAX_STRATEGY_BIAS
    assert -MAX_POLICY_BIAS <= sig.policy_bias <= MAX_POLICY_BIAS
    assert -MAX_DIRECTIVE_BIAS <= sig.directive_bias <= MAX_DIRECTIVE_BIAS
    assert (
        -MAX_CONFIDENCE_ADJUSTMENT
        <= sig.confidence_adjustment
        <= MAX_CONFIDENCE_ADJUSTMENT
    )


# ---------------------------------------------------------------------------
# Section 4: build_analytics_signal — individual compute functions
# ---------------------------------------------------------------------------


def test_strategy_bias_high_spread_positive():
    summary = {
        "total_entries": 100,
        "top_strategies": {"s1": 0.9, "s2": 0.1},
    }
    sig = build_analytics_signal(summary)
    assert sig.strategy_bias > 0.0


def test_strategy_bias_no_spread_zero():
    summary = {
        "total_entries": 100,
        "top_strategies": {"s1": 0.5, "s2": 0.5},
    }
    sig = build_analytics_signal(summary)
    assert sig.strategy_bias == 0.0


def test_strategy_bias_single_value_zero():
    summary = {
        "total_entries": 100,
        "top_strategies": {"s1": 0.9},
    }
    sig = build_analytics_signal(summary)
    assert sig.strategy_bias == 0.0


def test_strategy_bias_missing_key_zero():
    summary = {"total_entries": 100}
    sig = build_analytics_signal(summary)
    assert sig.strategy_bias == 0.0


def test_policy_bias_positive_correlations():
    summary = {
        "total_entries": 100,
        "top_signal_correlations": {"sig1": 0.5, "sig2": 0.3},
    }
    sig = build_analytics_signal(summary)
    assert sig.policy_bias > 0.0


def test_policy_bias_negative_correlations():
    summary = {
        "total_entries": 100,
        "top_signal_correlations": {"sig1": -0.5, "sig2": -0.3},
    }
    sig = build_analytics_signal(summary)
    assert sig.policy_bias < 0.0


def test_policy_bias_missing_key_zero():
    summary = {"total_entries": 100}
    sig = build_analytics_signal(summary)
    assert sig.policy_bias == 0.0


def test_directive_bias_above_baseline():
    summary = {
        "total_entries": 100,
        "directive_success": {"d1": 0.8, "d2": 0.7},
    }
    sig = build_analytics_signal(summary)
    assert sig.directive_bias > 0.0


def test_directive_bias_below_baseline():
    summary = {
        "total_entries": 100,
        "directive_success": {"d1": 0.2, "d2": 0.1},
    }
    sig = build_analytics_signal(summary)
    assert sig.directive_bias < 0.0


def test_directive_bias_at_baseline_zero():
    summary = {
        "total_entries": 100,
        "directive_success": {"d1": 0.5},
    }
    sig = build_analytics_signal(summary)
    assert sig.directive_bias == 0.0


def test_directive_bias_missing_key_zero():
    summary = {"total_entries": 100}
    sig = build_analytics_signal(summary)
    assert sig.directive_bias == 0.0


def test_confidence_adjustment_good_ratio():
    summary = {
        "total_entries": 100,
        "plan_count": 10,
        "goal_count": 5,
    }
    sig = build_analytics_signal(summary)
    assert sig.confidence_adjustment == 0.01


def test_confidence_adjustment_bad_ratio():
    summary = {
        "total_entries": 100,
        "plan_count": 10,
        "goal_count": 2,
    }
    sig = build_analytics_signal(summary)
    assert sig.confidence_adjustment == -0.01


def test_confidence_adjustment_no_plans_zero():
    summary = {
        "total_entries": 100,
        "plan_count": 0,
        "goal_count": 5,
    }
    sig = build_analytics_signal(summary)
    assert sig.confidence_adjustment == 0.0


def test_confidence_adjustment_no_goals_zero():
    summary = {
        "total_entries": 100,
        "plan_count": 5,
        "goal_count": 0,
    }
    sig = build_analytics_signal(summary)
    assert sig.confidence_adjustment == 0.0


# ---------------------------------------------------------------------------
# Section 5: build_analytics_signal — non-numeric values ignored
# ---------------------------------------------------------------------------


def test_non_numeric_strategy_values_skipped():
    summary = {
        "total_entries": 100,
        "top_strategies": {"s1": "bad", "s2": None},
    }
    sig = build_analytics_signal(summary)
    assert sig.strategy_bias == 0.0


def test_non_numeric_correlation_values_skipped():
    summary = {
        "total_entries": 100,
        "top_signal_correlations": {"sig1": "bad"},
    }
    sig = build_analytics_signal(summary)
    assert sig.policy_bias == 0.0


def test_non_numeric_directive_values_skipped():
    summary = {
        "total_entries": 100,
        "directive_success": {"d1": [1, 2, 3]},
    }
    sig = build_analytics_signal(summary)
    assert sig.directive_bias == 0.0


def test_non_dict_strategy_key_zero():
    summary = {
        "total_entries": 100,
        "top_strategies": "not_a_dict",
    }
    sig = build_analytics_signal(summary)
    assert sig.strategy_bias == 0.0


def test_non_dict_correlations_key_zero():
    summary = {
        "total_entries": 100,
        "top_signal_correlations": [1, 2, 3],
    }
    sig = build_analytics_signal(summary)
    assert sig.policy_bias == 0.0


# ---------------------------------------------------------------------------
# Section 6: apply_analytics_to_policy
# ---------------------------------------------------------------------------


def test_apply_no_signal_no_change():
    result = apply_analytics_to_policy(0.5, NO_SIGNAL)
    assert result == 0.5


def test_apply_positive_adjustment():
    sig = AnalyticsSignal(
        strategy_bias=0.0,
        policy_bias=0.0,
        directive_bias=0.0,
        confidence_adjustment=0.05,
    )
    result = apply_analytics_to_policy(0.5, sig)
    assert result == 0.55


def test_apply_negative_adjustment():
    sig = AnalyticsSignal(
        strategy_bias=0.0,
        policy_bias=0.0,
        directive_bias=0.0,
        confidence_adjustment=-0.05,
    )
    result = apply_analytics_to_policy(0.5, sig)
    assert result == 0.45


def test_apply_clamped_above_one():
    sig = AnalyticsSignal(
        strategy_bias=0.0,
        policy_bias=0.0,
        directive_bias=0.0,
        confidence_adjustment=0.05,
    )
    result = apply_analytics_to_policy(0.99, sig)
    assert result == 1.0


def test_apply_clamped_below_zero():
    sig = AnalyticsSignal(
        strategy_bias=0.0,
        policy_bias=0.0,
        directive_bias=0.0,
        confidence_adjustment=-0.05,
    )
    result = apply_analytics_to_policy(0.01, sig)
    assert result == 0.0


# ---------------------------------------------------------------------------
# Section 7: AnalyticsSignal — is_active
# ---------------------------------------------------------------------------


def test_is_active_all_zero():
    sig = AnalyticsSignal(0.0, 0.0, 0.0, 0.0)
    assert not sig.is_active


def test_is_active_strategy_nonzero():
    sig = AnalyticsSignal(0.01, 0.0, 0.0, 0.0)
    assert sig.is_active


def test_is_active_policy_nonzero():
    sig = AnalyticsSignal(0.0, 0.01, 0.0, 0.0)
    assert sig.is_active


def test_is_active_directive_nonzero():
    sig = AnalyticsSignal(0.0, 0.0, 0.01, 0.0)
    assert sig.is_active


def test_is_active_confidence_nonzero():
    sig = AnalyticsSignal(0.0, 0.0, 0.0, 0.01)
    assert sig.is_active


# ---------------------------------------------------------------------------
# Section 8: AnalyticsSignal — to_dict rounding
# ---------------------------------------------------------------------------


def test_to_dict_rounds_to_4_decimals():
    sig = AnalyticsSignal(0.123456789, 0.00001, -0.0299999, 0.04999)
    d = sig.to_dict()
    assert d["strategy_bias"] == 0.1235
    assert d["policy_bias"] == 0.0
    assert d["directive_bias"] == -0.03
    assert d["confidence_adjustment"] == 0.05


# ---------------------------------------------------------------------------
# Section 9: Deterministic behavior
# ---------------------------------------------------------------------------


def test_same_input_same_output():
    summary = {
        "total_entries": 50,
        "top_strategies": {"s1": 0.8, "s2": 0.3, "s3": 0.5},
        "top_signal_correlations": {"sig1": 0.4, "sig2": -0.2},
        "directive_success": {"d1": 0.7, "d2": 0.3},
        "plan_count": 8,
        "goal_count": 5,
    }
    sig1 = build_analytics_signal(summary)
    sig2 = build_analytics_signal(summary)
    assert sig1.strategy_bias == sig2.strategy_bias
    assert sig1.policy_bias == sig2.policy_bias
    assert sig1.directive_bias == sig2.directive_bias
    assert sig1.confidence_adjustment == sig2.confidence_adjustment


def test_deterministic_across_100_runs():
    summary = {
        "total_entries": 200,
        "top_strategies": {"a": 0.9, "b": 0.1, "c": 0.5},
        "top_signal_correlations": {"x": 0.6, "y": -0.4},
        "directive_success": {"d1": 0.8},
        "plan_count": 20,
        "goal_count": 12,
    }
    reference = build_analytics_signal(summary)
    for _ in range(100):
        result = build_analytics_signal(summary)
        assert result.strategy_bias == reference.strategy_bias
        assert result.policy_bias == reference.policy_bias
        assert result.directive_bias == reference.directive_bias
        assert result.confidence_adjustment == reference.confidence_adjustment


# ---------------------------------------------------------------------------
# Section 10: Policy engine — no regressions (None signal)
# ---------------------------------------------------------------------------


def test_policy_engine_none_signal_exploit():
    signals = PolicySignals(plan_confidence=0.5)
    result = select_policy(signals, analytics_signal=None)
    assert result.policy == Policy.EXPLOIT


def test_policy_engine_none_signal_recover():
    signals = PolicySignals(failure_streak=3)
    result = select_policy(signals, analytics_signal=None)
    assert result.policy == Policy.RECOVER


def test_policy_engine_none_signal_pivot():
    signals = PolicySignals(plan_confidence=0.1, state_similarity_delta=-0.3)
    result = select_policy(signals, analytics_signal=None)
    assert result.policy == Policy.PIVOT


def test_policy_engine_none_signal_commit():
    signals = PolicySignals(persistence_streak=4, plan_confidence=0.8)
    result = select_policy(signals, analytics_signal=None)
    assert result.policy == Policy.COMMIT


def test_policy_engine_none_signal_explore():
    signals = PolicySignals(exploration_rate=0.7)
    result = select_policy(signals, analytics_signal=None)
    assert result.policy == Policy.EXPLORE


def test_policy_engine_no_arg_same_as_none():
    signals = PolicySignals(plan_confidence=0.5)
    r1 = select_policy(signals)
    r2 = select_policy(signals, analytics_signal=None)
    assert r1.policy == r2.policy
    assert r1.reason == r2.reason


# ---------------------------------------------------------------------------
# Section 11: Policy engine — analytics signal integration
# ---------------------------------------------------------------------------


def test_analytics_nudges_confidence_up():
    signals = PolicySignals(plan_confidence=0.22, state_similarity_delta=-0.2)
    without = select_policy(signals, analytics_signal=None)
    assert without.policy == Policy.PIVOT

    sig = AnalyticsSignal(
        strategy_bias=0.0,
        policy_bias=0.0,
        directive_bias=0.0,
        confidence_adjustment=0.05,
    )
    with_sig = select_policy(signals, analytics_signal=sig)
    assert with_sig.policy != Policy.PIVOT


def test_analytics_nudges_exploration_down():
    signals = PolicySignals(exploration_rate=0.62, plan_confidence=0.5)
    without = select_policy(signals, analytics_signal=None)
    assert without.policy == Policy.EXPLORE

    sig = AnalyticsSignal(
        strategy_bias=0.03,
        policy_bias=0.0,
        directive_bias=0.0,
        confidence_adjustment=0.0,
    )
    with_sig = select_policy(signals, analytics_signal=sig)
    assert with_sig.policy == Policy.EXPLOIT


def test_analytics_cannot_override_recover():
    signals = PolicySignals(failure_streak=5, plan_confidence=0.1)
    sig = AnalyticsSignal(
        strategy_bias=0.03,
        policy_bias=0.02,
        directive_bias=0.02,
        confidence_adjustment=0.05,
    )
    result = select_policy(signals, analytics_signal=sig)
    assert result.policy == Policy.RECOVER


def test_no_signal_object_no_effect():
    signals = PolicySignals(plan_confidence=0.5)
    result = select_policy(signals, analytics_signal=NO_SIGNAL)
    assert result.policy == Policy.EXPLOIT


# ---------------------------------------------------------------------------
# Section 12: Stress test — repeated runs stable
# ---------------------------------------------------------------------------


def test_stress_1000_runs_bounded_stable():
    summary = {
        "total_entries": 500,
        "top_strategies": {f"s{i}": float(i) * 0.1 for i in range(10)},
        "top_signal_correlations": {f"sig{i}": (i - 5) * 0.1 for i in range(10)},
        "directive_success": {f"d{i}": i * 0.1 for i in range(10)},
        "plan_count": 100,
        "goal_count": 60,
    }
    reference = build_analytics_signal(summary)
    for _ in range(1000):
        sig = build_analytics_signal(summary)
        assert sig.strategy_bias == reference.strategy_bias
        assert sig.policy_bias == reference.policy_bias
        assert sig.directive_bias == reference.directive_bias
        assert sig.confidence_adjustment == reference.confidence_adjustment
        assert -MAX_STRATEGY_BIAS <= sig.strategy_bias <= MAX_STRATEGY_BIAS
        assert -MAX_POLICY_BIAS <= sig.policy_bias <= MAX_POLICY_BIAS
        assert -MAX_DIRECTIVE_BIAS <= sig.directive_bias <= MAX_DIRECTIVE_BIAS
        assert (
            -MAX_CONFIDENCE_ADJUSTMENT
            <= sig.confidence_adjustment
            <= MAX_CONFIDENCE_ADJUSTMENT
        )


def test_stress_policy_engine_stable_with_signal():
    signals = PolicySignals(
        failure_streak=0,
        persistence_streak=1,
        exploration_rate=0.3,
        plan_confidence=0.5,
        state_similarity_delta=0.0,
    )
    sig = AnalyticsSignal(
        strategy_bias=0.02,
        policy_bias=0.01,
        directive_bias=0.01,
        confidence_adjustment=0.03,
    )
    reference = select_policy(signals, analytics_signal=sig)
    for _ in range(1000):
        result = select_policy(signals, analytics_signal=sig)
        assert result.policy == reference.policy
        assert result.reason == reference.reason


# ---------------------------------------------------------------------------
# Section 13: Edge cases
# ---------------------------------------------------------------------------


def test_frozen_dataclass_immutable():
    sig = AnalyticsSignal(0.01, 0.02, 0.03, 0.04)
    try:
        sig.strategy_bias = 0.99  # type: ignore[misc]
        raise AssertionError("Should have raised FrozenInstanceError")
    except AttributeError:
        pass


def test_zero_total_entries():
    summary = {"total_entries": 0}
    assert build_analytics_signal(summary) is NO_SIGNAL


def test_negative_total_entries():
    summary = {"total_entries": -5}
    assert build_analytics_signal(summary) is NO_SIGNAL


def test_non_int_plan_count():
    summary = {
        "total_entries": 100,
        "plan_count": "bad",
        "goal_count": 5,
    }
    sig = build_analytics_signal(summary)
    assert sig.confidence_adjustment == 0.0


def test_empty_strategy_dict():
    summary = {
        "total_entries": 100,
        "top_strategies": {},
    }
    sig = build_analytics_signal(summary)
    assert sig.strategy_bias == 0.0


def test_empty_correlations_dict():
    summary = {
        "total_entries": 100,
        "top_signal_correlations": {},
    }
    sig = build_analytics_signal(summary)
    assert sig.policy_bias == 0.0


def test_empty_directive_dict():
    summary = {
        "total_entries": 100,
        "directive_success": {},
    }
    sig = build_analytics_signal(summary)
    assert sig.directive_bias == 0.0


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
