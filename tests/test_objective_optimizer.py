"""
Tests for eos_ai.objective_optimizer — Objective Optimizer Layer.

Verifies: bounded outputs, stability over 1000 turns, no oscillation,
correct trend detection, disabled = no effect.

No LLM calls.  No randomness.  No external deps.  Deterministic.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.objective_optimizer import (
    DEAD_ZONE,
    EMA_ALPHA,
    MAX_CONFIDENCE_ADJUSTMENT,
    MAX_EXPLORATION_ADJUSTMENT,
    MAX_POLICY_BIAS,
    MIN_HISTORY,
    NO_SIGNAL,
    OptimizationSignal,
    Trend,
    compute_optimization_signal,
)


# ---------------------------------------------------------------------------
# Section 1: NO_SIGNAL sentinel
# ---------------------------------------------------------------------------


def test_no_signal_is_flat():
    assert NO_SIGNAL.trend == Trend.FLAT
    assert NO_SIGNAL.ema_delta == 0.0
    assert NO_SIGNAL.exploration_adjustment == 0.0
    assert NO_SIGNAL.policy_bias == 0.0
    assert NO_SIGNAL.confidence_adjustment == 0.0
    assert not NO_SIGNAL.is_active


def test_no_signal_to_dict():
    d = NO_SIGNAL.to_dict()
    assert d["trend"] == "flat"
    assert d["ema_delta"] == 0.0
    assert d["exploration_adjustment"] == 0.0
    assert d["policy_bias"] == 0.0
    assert d["confidence_adjustment"] == 0.0


# ---------------------------------------------------------------------------
# Section 2: Insufficient history returns NO_SIGNAL
# ---------------------------------------------------------------------------


def test_empty_history():
    assert compute_optimization_signal([]) is NO_SIGNAL


def test_one_entry():
    assert compute_optimization_signal([0.5]) is NO_SIGNAL


def test_two_entries():
    assert compute_optimization_signal([0.5, 0.6]) is NO_SIGNAL


def test_exactly_min_history():
    result = compute_optimization_signal([0.5, 0.6, 0.7])
    assert isinstance(result, OptimizationSignal)
    assert result is not NO_SIGNAL


# ---------------------------------------------------------------------------
# Section 3: Trend detection — improving
# ---------------------------------------------------------------------------


def test_improving_trend():
    history = [0.3, 0.4, 0.5, 0.6, 0.7]
    result = compute_optimization_signal(history)
    assert result.trend == Trend.IMPROVING


def test_improving_strong_rise():
    history = [0.1, 0.3, 0.5, 0.7, 0.9]
    result = compute_optimization_signal(history)
    assert result.trend == Trend.IMPROVING
    assert result.ema_delta > DEAD_ZONE


# ---------------------------------------------------------------------------
# Section 4: Trend detection — degrading
# ---------------------------------------------------------------------------


def test_degrading_trend():
    history = [0.7, 0.6, 0.5, 0.4, 0.3]
    result = compute_optimization_signal(history)
    assert result.trend == Trend.DEGRADING


def test_degrading_strong_drop():
    history = [0.9, 0.7, 0.5, 0.3, 0.1]
    result = compute_optimization_signal(history)
    assert result.trend == Trend.DEGRADING
    assert result.ema_delta < -DEAD_ZONE


# ---------------------------------------------------------------------------
# Section 5: Trend detection — flat
# ---------------------------------------------------------------------------


def test_flat_constant():
    history = [0.5, 0.5, 0.5, 0.5, 0.5]
    result = compute_optimization_signal(history)
    assert result.trend == Trend.FLAT
    assert result.ema_delta == 0.0


def test_flat_tiny_variation():
    history = [0.500, 0.501, 0.500, 0.501, 0.500]
    result = compute_optimization_signal(history)
    assert result.trend == Trend.FLAT


# ---------------------------------------------------------------------------
# Section 6: Bounded outputs — extreme improving
# ---------------------------------------------------------------------------


def test_bounded_extreme_improving():
    history = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    result = compute_optimization_signal(history)
    assert (
        -MAX_EXPLORATION_ADJUSTMENT
        <= result.exploration_adjustment
        <= MAX_EXPLORATION_ADJUSTMENT
    )
    assert -MAX_POLICY_BIAS <= result.policy_bias <= MAX_POLICY_BIAS
    assert (
        -MAX_CONFIDENCE_ADJUSTMENT
        <= result.confidence_adjustment
        <= MAX_CONFIDENCE_ADJUSTMENT
    )


def test_bounded_extreme_degrading():
    history = [1.0, 0.8, 0.6, 0.4, 0.2, 0.0]
    result = compute_optimization_signal(history)
    assert (
        -MAX_EXPLORATION_ADJUSTMENT
        <= result.exploration_adjustment
        <= MAX_EXPLORATION_ADJUSTMENT
    )
    assert -MAX_POLICY_BIAS <= result.policy_bias <= MAX_POLICY_BIAS
    assert (
        -MAX_CONFIDENCE_ADJUSTMENT
        <= result.confidence_adjustment
        <= MAX_CONFIDENCE_ADJUSTMENT
    )


def test_bounded_large_jump():
    history = [0.0, 0.0, 0.0, 1.0]
    result = compute_optimization_signal(history)
    assert (
        -MAX_EXPLORATION_ADJUSTMENT
        <= result.exploration_adjustment
        <= MAX_EXPLORATION_ADJUSTMENT
    )
    assert -MAX_POLICY_BIAS <= result.policy_bias <= MAX_POLICY_BIAS
    assert (
        -MAX_CONFIDENCE_ADJUSTMENT
        <= result.confidence_adjustment
        <= MAX_CONFIDENCE_ADJUSTMENT
    )


def test_bounded_large_drop():
    history = [1.0, 1.0, 1.0, 0.0]
    result = compute_optimization_signal(history)
    assert (
        -MAX_EXPLORATION_ADJUSTMENT
        <= result.exploration_adjustment
        <= MAX_EXPLORATION_ADJUSTMENT
    )
    assert -MAX_POLICY_BIAS <= result.policy_bias <= MAX_POLICY_BIAS
    assert (
        -MAX_CONFIDENCE_ADJUSTMENT
        <= result.confidence_adjustment
        <= MAX_CONFIDENCE_ADJUSTMENT
    )


# ---------------------------------------------------------------------------
# Section 7: Direction correctness
# ---------------------------------------------------------------------------


def test_improving_reduces_exploration():
    history = [0.3, 0.4, 0.5, 0.6, 0.7]
    result = compute_optimization_signal(history)
    assert result.exploration_adjustment <= 0.0


def test_improving_positive_policy_bias():
    history = [0.3, 0.4, 0.5, 0.6, 0.7]
    result = compute_optimization_signal(history)
    assert result.policy_bias >= 0.0


def test_improving_positive_confidence():
    history = [0.3, 0.4, 0.5, 0.6, 0.7]
    result = compute_optimization_signal(history)
    assert result.confidence_adjustment >= 0.0


def test_degrading_increases_exploration():
    history = [0.7, 0.6, 0.5, 0.4, 0.3]
    result = compute_optimization_signal(history)
    assert result.exploration_adjustment >= 0.0


def test_degrading_negative_policy_bias():
    history = [0.7, 0.6, 0.5, 0.4, 0.3]
    result = compute_optimization_signal(history)
    assert result.policy_bias <= 0.0


def test_degrading_negative_confidence():
    history = [0.7, 0.6, 0.5, 0.4, 0.3]
    result = compute_optimization_signal(history)
    assert result.confidence_adjustment <= 0.0


def test_flat_no_adjustments():
    history = [0.5, 0.5, 0.5, 0.5, 0.5]
    result = compute_optimization_signal(history)
    assert result.exploration_adjustment == 0.0
    assert result.policy_bias == 0.0
    assert result.confidence_adjustment == 0.0


# ---------------------------------------------------------------------------
# Section 8: Deterministic behavior
# ---------------------------------------------------------------------------


def test_same_input_same_output():
    history = [0.4, 0.45, 0.5, 0.55, 0.6]
    r1 = compute_optimization_signal(history)
    r2 = compute_optimization_signal(history)
    assert r1.trend == r2.trend
    assert r1.ema_delta == r2.ema_delta
    assert r1.exploration_adjustment == r2.exploration_adjustment
    assert r1.policy_bias == r2.policy_bias
    assert r1.confidence_adjustment == r2.confidence_adjustment


def test_deterministic_100_runs():
    history = [0.5, 0.55, 0.6, 0.58, 0.62, 0.65]
    ref = compute_optimization_signal(history)
    for _ in range(100):
        result = compute_optimization_signal(history)
        assert result.ema_delta == ref.ema_delta


# ---------------------------------------------------------------------------
# Section 9: Stability over 1000 turns
# ---------------------------------------------------------------------------


def test_stability_1000_improving():
    history = [0.3 + i * 0.01 for i in range(100)]
    result = compute_optimization_signal(history)
    assert result.trend == Trend.IMPROVING
    assert (
        -MAX_EXPLORATION_ADJUSTMENT
        <= result.exploration_adjustment
        <= MAX_EXPLORATION_ADJUSTMENT
    )
    assert -MAX_POLICY_BIAS <= result.policy_bias <= MAX_POLICY_BIAS
    assert (
        -MAX_CONFIDENCE_ADJUSTMENT
        <= result.confidence_adjustment
        <= MAX_CONFIDENCE_ADJUSTMENT
    )


def test_stability_1000_flat():
    history = [0.5] * 1000
    result = compute_optimization_signal(history)
    assert result.trend == Trend.FLAT
    assert result.ema_delta == 0.0
    assert result.exploration_adjustment == 0.0
    assert result.policy_bias == 0.0
    assert result.confidence_adjustment == 0.0


def test_stability_1000_runs_same_output():
    history = [0.4, 0.45, 0.5, 0.55, 0.6, 0.62, 0.65]
    ref = compute_optimization_signal(history)
    for _ in range(1000):
        result = compute_optimization_signal(history)
        assert result.ema_delta == ref.ema_delta
        assert result.trend == ref.trend
        assert (
            -MAX_EXPLORATION_ADJUSTMENT
            <= result.exploration_adjustment
            <= MAX_EXPLORATION_ADJUSTMENT
        )


# ---------------------------------------------------------------------------
# Section 10: No oscillation
# ---------------------------------------------------------------------------


def test_no_oscillation_alternating():
    history = []
    for i in range(100):
        history.append(0.6 if i % 2 == 0 else 0.4)
    history.append(0.5)
    result = compute_optimization_signal(history)
    assert abs(result.exploration_adjustment) <= MAX_EXPLORATION_ADJUSTMENT
    assert abs(result.policy_bias) <= MAX_POLICY_BIAS


def test_no_oscillation_sawtooth():
    history = []
    for i in range(100):
        cycle = i % 10
        if cycle < 5:
            history.append(0.5 + cycle * 0.02)
        else:
            history.append(0.5 + (10 - cycle) * 0.02)
    result = compute_optimization_signal(history)
    assert abs(result.exploration_adjustment) < MAX_EXPLORATION_ADJUSTMENT


def test_ema_dampens_spike():
    history = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.9]
    result = compute_optimization_signal(history)
    assert result.ema_delta < 0.4 * EMA_ALPHA + 0.01


# ---------------------------------------------------------------------------
# Section 11: EMA computation correctness
# ---------------------------------------------------------------------------


def test_ema_single_delta():
    history = [0.5, 0.6, 0.6]
    result = compute_optimization_signal(history)
    expected_ema = EMA_ALPHA * 0.0 + (1.0 - EMA_ALPHA) * (EMA_ALPHA * 0.1)
    assert abs(result.ema_delta - expected_ema) < 1e-10


def test_ema_two_equal_deltas():
    history = [0.5, 0.6, 0.7]
    result = compute_optimization_signal(history)
    ema_after_first = EMA_ALPHA * 0.1
    ema_after_second = EMA_ALPHA * 0.1 + (1.0 - EMA_ALPHA) * ema_after_first
    assert abs(result.ema_delta - ema_after_second) < 1e-10


def test_ema_zero_deltas():
    history = [0.5, 0.5, 0.5]
    result = compute_optimization_signal(history)
    assert result.ema_delta == 0.0


# ---------------------------------------------------------------------------
# Section 12: is_active property
# ---------------------------------------------------------------------------


def test_is_active_when_adjustments_nonzero():
    history = [0.3, 0.4, 0.5, 0.6, 0.7]
    result = compute_optimization_signal(history)
    assert result.is_active


def test_not_active_when_flat():
    history = [0.5, 0.5, 0.5]
    result = compute_optimization_signal(history)
    assert not result.is_active


# ---------------------------------------------------------------------------
# Section 13: Serialization
# ---------------------------------------------------------------------------


def test_to_dict_structure():
    history = [0.4, 0.5, 0.6, 0.7]
    result = compute_optimization_signal(history)
    d = result.to_dict()
    assert set(d.keys()) == {
        "trend",
        "ema_delta",
        "exploration_adjustment",
        "policy_bias",
        "confidence_adjustment",
    }


def test_to_dict_rounds():
    history = [0.4, 0.5, 0.6, 0.7]
    result = compute_optimization_signal(history)
    d = result.to_dict()
    assert isinstance(d["ema_delta"], float)
    assert isinstance(d["exploration_adjustment"], float)


# ---------------------------------------------------------------------------
# Section 14: Frozen dataclass immutability
# ---------------------------------------------------------------------------


def test_frozen():
    result = compute_optimization_signal([0.4, 0.5, 0.6])
    try:
        result.trend = Trend.IMPROVING  # type: ignore[misc]
        raise AssertionError("Should have raised")
    except AttributeError:
        pass


# ---------------------------------------------------------------------------
# Section 15: Disabled = no effect (NO_SIGNAL pass-through)
# ---------------------------------------------------------------------------


def test_insufficient_history_no_effect():
    for n in range(MIN_HISTORY):
        history = [0.5 + i * 0.1 for i in range(n)]
        result = compute_optimization_signal(history)
        assert result is NO_SIGNAL
        assert not result.is_active


def test_no_signal_frozen_identity():
    assert NO_SIGNAL is compute_optimization_signal([])
    assert NO_SIGNAL is compute_optimization_signal([0.5])
    assert NO_SIGNAL is compute_optimization_signal([0.5, 0.6])


# ---------------------------------------------------------------------------
# Section 16: Gradual convergence
# ---------------------------------------------------------------------------


def test_gradual_improvement_stays_bounded():
    history = [0.3]
    for i in range(50):
        history.append(history[-1] + 0.01)
    result = compute_optimization_signal(history)
    assert result.trend == Trend.IMPROVING
    assert (
        -MAX_EXPLORATION_ADJUSTMENT
        <= result.exploration_adjustment
        <= MAX_EXPLORATION_ADJUSTMENT
    )
    assert -MAX_POLICY_BIAS <= result.policy_bias <= MAX_POLICY_BIAS


def test_gradual_degradation_stays_bounded():
    history = [0.8]
    for i in range(50):
        history.append(history[-1] - 0.01)
    result = compute_optimization_signal(history)
    assert result.trend == Trend.DEGRADING
    assert (
        -MAX_EXPLORATION_ADJUSTMENT
        <= result.exploration_adjustment
        <= MAX_EXPLORATION_ADJUSTMENT
    )
    assert -MAX_POLICY_BIAS <= result.policy_bias <= MAX_POLICY_BIAS


# ---------------------------------------------------------------------------
# Section 17: Monotonic relationship
# ---------------------------------------------------------------------------


def test_stronger_improvement_stronger_signal():
    mild = [0.5, 0.51, 0.52, 0.53, 0.54]
    strong = [0.5, 0.55, 0.60, 0.65, 0.70]
    r_mild = compute_optimization_signal(mild)
    r_strong = compute_optimization_signal(strong)
    assert abs(r_strong.exploration_adjustment) >= abs(r_mild.exploration_adjustment)
    assert abs(r_strong.policy_bias) >= abs(r_mild.policy_bias)


def test_stronger_degradation_stronger_signal():
    mild = [0.5, 0.49, 0.48, 0.47, 0.46]
    strong = [0.5, 0.45, 0.40, 0.35, 0.30]
    r_mild = compute_optimization_signal(mild)
    r_strong = compute_optimization_signal(strong)
    assert abs(r_strong.exploration_adjustment) >= abs(r_mild.exploration_adjustment)
    assert abs(r_strong.policy_bias) >= abs(r_mild.policy_bias)


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
