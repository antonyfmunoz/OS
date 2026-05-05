"""
Tests for eos_ai.objective_decision_adapter — Decision Adaptation Layer.

Verifies: bounded outputs, stable ordering, monotonic behavior,
no oscillation, disabled = no effect.

No LLM calls.  No randomness.  No external deps.  Deterministic.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.objective_decision_adapter import (
    MAX_PLAN_BIAS,
    MAX_STRATEGY_SHIFT,
    MIN_GOAL_SCALE,
    MAX_GOAL_SCALE,
    MIN_HISTORY,
    NO_SIGNAL,
    ObjectiveDecisionSignal,
    apply_goal_scale,
    apply_plan_bias,
    apply_strategy_shift,
    compute_decision_signal,
)


# ---------------------------------------------------------------------------
# Section 1: NO_SIGNAL sentinel
# ---------------------------------------------------------------------------


def test_no_signal_is_neutral():
    assert NO_SIGNAL.trend == "flat"
    assert NO_SIGNAL.ema_delta == 0.0
    assert NO_SIGNAL.strategy_shift == 0.0
    assert NO_SIGNAL.goal_scale == 1.0
    assert NO_SIGNAL.plan_bias == 0.0
    assert not NO_SIGNAL.is_active


def test_no_signal_to_dict():
    d = NO_SIGNAL.to_dict()
    assert d == {
        "trend": "flat",
        "ema_delta": 0.0,
        "strategy_shift": 0.0,
        "goal_scale": 1.0,
        "plan_bias": 0.0,
    }


# ---------------------------------------------------------------------------
# Section 2: Insufficient history returns NO_SIGNAL
# ---------------------------------------------------------------------------


def test_empty_history():
    assert compute_decision_signal([]) is NO_SIGNAL


def test_one_entry():
    assert compute_decision_signal([0.5]) is NO_SIGNAL


def test_two_entries():
    assert compute_decision_signal([0.5, 0.6]) is NO_SIGNAL


def test_exactly_min_history():
    result = compute_decision_signal([0.5, 0.6, 0.7])
    assert isinstance(result, ObjectiveDecisionSignal)
    assert result is not NO_SIGNAL


# ---------------------------------------------------------------------------
# Section 3: Improving trend — reinforce behavior
# ---------------------------------------------------------------------------


def test_improving_positive_strategy_shift():
    history = [0.3, 0.4, 0.5, 0.6, 0.7]
    result = compute_decision_signal(history, objective_trend="improving")
    assert result.strategy_shift > 0.0


def test_improving_goal_scale_above_one():
    history = [0.3, 0.4, 0.5, 0.6, 0.7]
    result = compute_decision_signal(history, objective_trend="improving")
    assert result.goal_scale >= 1.0


def test_improving_positive_plan_bias():
    history = [0.3, 0.4, 0.5, 0.6, 0.7]
    result = compute_decision_signal(history, objective_trend="improving")
    assert result.plan_bias >= 0.0


# ---------------------------------------------------------------------------
# Section 4: Degrading trend — explore behavior
# ---------------------------------------------------------------------------


def test_degrading_negative_strategy_shift():
    history = [0.7, 0.6, 0.5, 0.4, 0.3]
    result = compute_decision_signal(history, objective_trend="degrading")
    assert result.strategy_shift < 0.0


def test_degrading_goal_scale_below_one():
    history = [0.7, 0.6, 0.5, 0.4, 0.3]
    result = compute_decision_signal(history, objective_trend="degrading")
    assert result.goal_scale <= 1.0


def test_degrading_negative_plan_bias():
    history = [0.7, 0.6, 0.5, 0.4, 0.3]
    result = compute_decision_signal(history, objective_trend="degrading")
    assert result.plan_bias <= 0.0


# ---------------------------------------------------------------------------
# Section 5: Flat trend — diversify behavior
# ---------------------------------------------------------------------------


def test_flat_neutral_goal_scale():
    history = [0.5, 0.5, 0.5, 0.5]
    result = compute_decision_signal(history, objective_trend="flat")
    assert result.goal_scale == 1.0


def test_flat_no_plan_bias():
    history = [0.5, 0.5, 0.5, 0.5]
    result = compute_decision_signal(history, objective_trend="flat")
    assert result.plan_bias == 0.0


def test_flat_small_strategy_shift():
    history = [0.5, 0.5, 0.5, 0.5]
    result = compute_decision_signal(history, objective_trend="flat")
    assert result.strategy_shift >= 0.0
    assert result.strategy_shift <= MAX_STRATEGY_SHIFT * 0.25 + 0.001


# ---------------------------------------------------------------------------
# Section 6: Bounded outputs — extreme inputs
# ---------------------------------------------------------------------------


def test_bounded_extreme_improving():
    history = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    result = compute_decision_signal(history, objective_trend="improving")
    assert -MAX_STRATEGY_SHIFT <= result.strategy_shift <= MAX_STRATEGY_SHIFT
    assert MIN_GOAL_SCALE <= result.goal_scale <= MAX_GOAL_SCALE
    assert -MAX_PLAN_BIAS <= result.plan_bias <= MAX_PLAN_BIAS


def test_bounded_extreme_degrading():
    history = [1.0, 0.8, 0.6, 0.4, 0.2, 0.0]
    result = compute_decision_signal(history, objective_trend="degrading")
    assert -MAX_STRATEGY_SHIFT <= result.strategy_shift <= MAX_STRATEGY_SHIFT
    assert MIN_GOAL_SCALE <= result.goal_scale <= MAX_GOAL_SCALE
    assert -MAX_PLAN_BIAS <= result.plan_bias <= MAX_PLAN_BIAS


def test_bounded_large_jump():
    history = [0.0, 0.0, 0.0, 1.0]
    result = compute_decision_signal(history)
    assert -MAX_STRATEGY_SHIFT <= result.strategy_shift <= MAX_STRATEGY_SHIFT
    assert MIN_GOAL_SCALE <= result.goal_scale <= MAX_GOAL_SCALE
    assert -MAX_PLAN_BIAS <= result.plan_bias <= MAX_PLAN_BIAS


def test_bounded_large_drop():
    history = [1.0, 1.0, 1.0, 0.0]
    result = compute_decision_signal(history)
    assert -MAX_STRATEGY_SHIFT <= result.strategy_shift <= MAX_STRATEGY_SHIFT
    assert MIN_GOAL_SCALE <= result.goal_scale <= MAX_GOAL_SCALE
    assert -MAX_PLAN_BIAS <= result.plan_bias <= MAX_PLAN_BIAS


# ---------------------------------------------------------------------------
# Section 7: Deterministic behavior
# ---------------------------------------------------------------------------


def test_same_input_same_output():
    history = [0.4, 0.5, 0.6, 0.55, 0.6]
    r1 = compute_decision_signal(history, objective_trend="improving")
    r2 = compute_decision_signal(history, objective_trend="improving")
    assert r1.strategy_shift == r2.strategy_shift
    assert r1.goal_scale == r2.goal_scale
    assert r1.plan_bias == r2.plan_bias
    assert r1.ema_delta == r2.ema_delta


def test_deterministic_100_runs():
    history = [0.5, 0.55, 0.6, 0.58, 0.62, 0.65]
    ref = compute_decision_signal(history)
    for _ in range(100):
        result = compute_decision_signal(history)
        assert result.strategy_shift == ref.strategy_shift
        assert result.goal_scale == ref.goal_scale
        assert result.plan_bias == ref.plan_bias


# ---------------------------------------------------------------------------
# Section 8: Stability over 1000 runs
# ---------------------------------------------------------------------------


def test_stability_1000_runs():
    history = [0.4 + i * 0.01 for i in range(50)]
    ref = compute_decision_signal(history, objective_trend="improving")
    for _ in range(1000):
        result = compute_decision_signal(history, objective_trend="improving")
        assert result.strategy_shift == ref.strategy_shift
        assert result.goal_scale == ref.goal_scale
        assert result.plan_bias == ref.plan_bias
        assert -MAX_STRATEGY_SHIFT <= result.strategy_shift <= MAX_STRATEGY_SHIFT
        assert MIN_GOAL_SCALE <= result.goal_scale <= MAX_GOAL_SCALE
        assert -MAX_PLAN_BIAS <= result.plan_bias <= MAX_PLAN_BIAS


# ---------------------------------------------------------------------------
# Section 9: No oscillation
# ---------------------------------------------------------------------------


def test_no_oscillation_alternating():
    history = []
    for i in range(100):
        history.append(0.6 if i % 2 == 0 else 0.4)
    history.append(0.5)
    result = compute_decision_signal(history)
    assert abs(result.strategy_shift) <= MAX_STRATEGY_SHIFT
    assert MIN_GOAL_SCALE <= result.goal_scale <= MAX_GOAL_SCALE
    assert abs(result.plan_bias) <= MAX_PLAN_BIAS


def test_no_oscillation_sawtooth():
    history = []
    for i in range(100):
        cycle = i % 10
        if cycle < 5:
            history.append(0.5 + cycle * 0.02)
        else:
            history.append(0.5 + (10 - cycle) * 0.02)
    result = compute_decision_signal(history)
    assert abs(result.strategy_shift) <= MAX_STRATEGY_SHIFT


# ---------------------------------------------------------------------------
# Section 10: Monotonic behavior
# ---------------------------------------------------------------------------


def test_stronger_improvement_stronger_shift():
    mild = [0.5, 0.51, 0.52, 0.53, 0.54]
    strong = [0.5, 0.55, 0.60, 0.65, 0.70]
    r_mild = compute_decision_signal(mild, objective_trend="improving")
    r_strong = compute_decision_signal(strong, objective_trend="improving")
    assert r_strong.strategy_shift >= r_mild.strategy_shift
    assert r_strong.goal_scale >= r_mild.goal_scale
    assert r_strong.plan_bias >= r_mild.plan_bias


def test_stronger_degradation_stronger_signal():
    mild = [0.5, 0.49, 0.48, 0.47, 0.46]
    strong = [0.5, 0.45, 0.40, 0.35, 0.30]
    r_mild = compute_decision_signal(mild, objective_trend="degrading")
    r_strong = compute_decision_signal(strong, objective_trend="degrading")
    assert r_strong.strategy_shift <= r_mild.strategy_shift
    assert r_strong.goal_scale <= r_mild.goal_scale
    assert r_strong.plan_bias <= r_mild.plan_bias


# ---------------------------------------------------------------------------
# Section 11: apply_strategy_shift
# ---------------------------------------------------------------------------


def test_apply_shift_positive():
    scores = {"a": 0.5, "b": 0.3, "c": 0.2}
    result = apply_strategy_shift(scores, 0.04, "a")
    assert result["a"] > 0.5
    assert result["b"] < 0.3
    assert result["c"] < 0.2


def test_apply_shift_preserves_ordering():
    scores = {"a": 0.6, "b": 0.3, "c": 0.1}
    result = apply_strategy_shift(scores, 0.04, "a")
    assert result["a"] > result["b"]
    assert result["b"] > result["c"]


def test_apply_shift_negative():
    scores = {"a": 0.5, "b": 0.3, "c": 0.2}
    result = apply_strategy_shift(scores, -0.04, "a")
    assert result["a"] < 0.5
    assert result["b"] > 0.3


def test_apply_shift_zero_no_change():
    scores = {"a": 0.5, "b": 0.3}
    result = apply_strategy_shift(scores, 0.0, "a")
    assert result == scores


def test_apply_shift_empty_scores():
    result = apply_strategy_shift({}, 0.04, "a")
    assert result == {}


def test_apply_shift_missing_strategy():
    scores = {"a": 0.5, "b": 0.3}
    result = apply_strategy_shift(scores, 0.04, "nonexistent")
    assert result["a"] < 0.5
    assert result["b"] < 0.3


def test_apply_shift_single_strategy():
    scores = {"a": 0.5}
    result = apply_strategy_shift(scores, 0.04, "a")
    assert result["a"] == 0.54


def test_apply_shift_floors_at_zero():
    scores = {"a": 0.01, "b": 0.01}
    result = apply_strategy_shift(scores, -0.04, "a")
    assert result["a"] >= 0.0
    assert result["b"] >= 0.0


# ---------------------------------------------------------------------------
# Section 12: apply_goal_scale
# ---------------------------------------------------------------------------


def test_goal_scale_neutral():
    assert apply_goal_scale(0.5, 1.0) == 0.5


def test_goal_scale_up():
    assert apply_goal_scale(0.5, 1.1) > 0.5


def test_goal_scale_down():
    assert apply_goal_scale(0.5, 0.9) < 0.5


def test_goal_scale_clamped_above():
    assert apply_goal_scale(0.95, 1.1) == 1.0


def test_goal_scale_clamped_below():
    assert apply_goal_scale(0.0, 0.9) == 0.0


# ---------------------------------------------------------------------------
# Section 13: apply_plan_bias
# ---------------------------------------------------------------------------


def test_plan_bias_positive():
    assert apply_plan_bias(0.5, 0.03) > 0.5


def test_plan_bias_negative():
    assert apply_plan_bias(0.5, -0.03) < 0.5


def test_plan_bias_zero():
    assert apply_plan_bias(0.5, 0.0) == 0.5


def test_plan_bias_clamped_above():
    assert apply_plan_bias(0.99, 0.03) == 1.0


def test_plan_bias_clamped_below():
    assert apply_plan_bias(0.01, -0.03) == 0.0


# ---------------------------------------------------------------------------
# Section 14: is_active property
# ---------------------------------------------------------------------------


def test_is_active_when_strategy_shift():
    sig = ObjectiveDecisionSignal("improving", 0.01, 0.02, 1.0, 0.0)
    assert sig.is_active


def test_is_active_when_goal_scale():
    sig = ObjectiveDecisionSignal("degrading", -0.01, 0.0, 0.95, 0.0)
    assert sig.is_active


def test_is_active_when_plan_bias():
    sig = ObjectiveDecisionSignal("improving", 0.01, 0.0, 1.0, 0.01)
    assert sig.is_active


def test_not_active_when_neutral():
    sig = ObjectiveDecisionSignal("flat", 0.0, 0.0, 1.0, 0.0)
    assert not sig.is_active


# ---------------------------------------------------------------------------
# Section 15: Trend override vs auto-detection
# ---------------------------------------------------------------------------


def test_explicit_trend_used():
    history = [0.7, 0.6, 0.5, 0.4, 0.3]
    result = compute_decision_signal(history, objective_trend="improving")
    assert result.trend == "improving"
    assert result.strategy_shift > 0.0


def test_auto_detect_when_no_trend():
    history = [0.3, 0.4, 0.5, 0.6, 0.7]
    result = compute_decision_signal(history, objective_trend=None)
    assert result.trend == "improving"


def test_auto_detect_degrading():
    history = [0.7, 0.6, 0.5, 0.4, 0.3]
    result = compute_decision_signal(history, objective_trend=None)
    assert result.trend == "degrading"


# ---------------------------------------------------------------------------
# Section 16: Frozen dataclass
# ---------------------------------------------------------------------------


def test_frozen():
    result = compute_decision_signal([0.4, 0.5, 0.6])
    try:
        result.strategy_shift = 0.99  # type: ignore[misc]
        raise AssertionError("Should have raised")
    except AttributeError:
        pass


# ---------------------------------------------------------------------------
# Section 17: Serialization
# ---------------------------------------------------------------------------


def test_to_dict_structure():
    history = [0.4, 0.5, 0.6, 0.7]
    result = compute_decision_signal(history)
    d = result.to_dict()
    assert set(d.keys()) == {
        "trend",
        "ema_delta",
        "strategy_shift",
        "goal_scale",
        "plan_bias",
    }


def test_to_dict_rounds():
    history = [0.4, 0.5, 0.6, 0.7]
    result = compute_decision_signal(history)
    d = result.to_dict()
    assert isinstance(d["strategy_shift"], float)
    assert isinstance(d["goal_scale"], float)
    assert isinstance(d["plan_bias"], float)


# ---------------------------------------------------------------------------
# Section 18: Disabled = no effect
# ---------------------------------------------------------------------------


def test_disabled_no_effect_insufficient_history():
    for n in range(MIN_HISTORY):
        history = [0.5 + i * 0.1 for i in range(n)]
        result = compute_decision_signal(history)
        assert result is NO_SIGNAL
        assert not result.is_active


def test_no_signal_identity():
    assert NO_SIGNAL is compute_decision_signal([])
    assert NO_SIGNAL is compute_decision_signal([0.5])
    assert NO_SIGNAL is compute_decision_signal([0.5, 0.6])


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
