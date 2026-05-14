"""
Tests for the regime break detection engine.

Covers:
- Plateau signal computation
- Dominance signal computation
- Confidence mismatch detection
- Full regime signal composition
- Dampening application (compression toward mean)
- Forced trial override selection
- Safety: RECOVER protection
- Adversarial recovery improvement
- No regression on static/noisy scenarios
- No oscillation
- No false positives
- Determinism
"""

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.regime_engine import (
    CONFIDENCE_MISMATCH_THRESHOLD,
    MIN_DAMPENING,
    MIN_HISTORY,
    NO_REGIME_BREAK,
    PEAK_LOOKBACK,
    PLATEAU_WINDOW,
    PROTECTED_STRATEGIES,
    REWARD_DROP_THRESHOLD,
    RegimeSignal,
    _clamp,
    _compute_confidence_mismatch,
    _compute_dominance_signal,
    _compute_plateau_signal,
    apply_regime_dampening,
    compute_regime_signal,
    select_regime_override,
)


# ─── Clamp ──────────────────────────────────────────────────────


def test_clamp_within_bounds():
    assert _clamp(0.5, 0.0, 1.0) == 0.5


def test_clamp_below_floor():
    assert _clamp(-0.1, 0.0, 1.0) == 0.0


def test_clamp_above_ceiling():
    assert _clamp(1.5, 0.0, 1.0) == 1.0


# ─── Plateau signal ────────────────────────────────────────────


def test_plateau_insufficient_history():
    assert _compute_plateau_signal([0.8] * (MIN_HISTORY - 1)) == 0.0


def test_plateau_no_drop():
    history = [0.8] * (MIN_HISTORY + 10)
    assert _compute_plateau_signal(history) == 0.0


def test_plateau_low_rewards_ignored():
    """Below 0.5 average — exploration engine handles this, not regime."""
    history = [0.8] * 20 + [0.3] * PLATEAU_WINDOW
    assert _compute_plateau_signal(history) == 0.0


def test_plateau_fires_on_flat_below_peak():
    peak_rewards = [1.0] * 30
    flat_plateau = [0.75] * PLATEAU_WINDOW
    history = peak_rewards + flat_plateau
    signal = _compute_plateau_signal(history)
    assert signal > 0.0


def test_plateau_stronger_with_larger_drop():
    base = [1.0] * 30
    mild = base + [0.8] * PLATEAU_WINDOW
    severe = base + [0.6] * PLATEAU_WINDOW
    assert _compute_plateau_signal(severe) > _compute_plateau_signal(mild)


def test_plateau_not_flat_variance():
    """High variance in recent window should prevent plateau detection."""
    history = [1.0] * 30 + [0.5, 0.9, 0.5, 0.9, 0.5, 0.9, 0.5, 0.9]
    assert _compute_plateau_signal(history) == 0.0


def test_plateau_lookback_window():
    """Peak must be within PEAK_LOOKBACK to count."""
    old_peak = [1.0] * 10
    gap = [0.6] * (PEAK_LOOKBACK + 5)
    flat = [0.75] * PLATEAU_WINDOW
    history = old_peak + gap + flat
    peak_in_lookback = max(history[-PEAK_LOOKBACK:])
    if peak_in_lookback - 0.75 < REWARD_DROP_THRESHOLD:
        assert _compute_plateau_signal(history) == 0.0


# ─── Dominance signal ──────────────────────────────────────────


def test_dominance_single_strategy():
    assert _compute_dominance_signal({"A": 1.0}) == (0.0, None)


def test_dominance_balanced_scores():
    scores = {"A": 0.5, "B": 0.5}
    strength, name = _compute_dominance_signal(scores)
    assert strength == 0.0


def test_dominance_one_dominant():
    scores = {"A": 0.9, "B": 0.1}
    strength, name = _compute_dominance_signal(scores)
    assert strength > 0.0
    assert name == "A"


def test_dominance_all_zero():
    assert _compute_dominance_signal({"A": 0.0, "B": 0.0}) == (0.0, None)


def test_dominance_protected_strategy_immune():
    scores = {"RECOVER": 0.9, "B": 0.1}
    strength, name = _compute_dominance_signal(scores)
    assert strength == 0.0
    assert name is None


def test_dominance_threshold():
    """Equal scores should not fire dominance."""
    equal = {"A": 0.5, "B": 0.5}
    strength, _ = _compute_dominance_signal(equal)
    assert strength == 0.0


# ─── Confidence mismatch ───────────────────────────────────────


def test_confidence_mismatch_no_confidence():
    assert _compute_confidence_mismatch(None, [0.5] * 10) == 0.0


def test_confidence_mismatch_short_history():
    assert _compute_confidence_mismatch(0.9, [0.3] * (PLATEAU_WINDOW - 1)) == 0.0


def test_confidence_mismatch_aligned():
    """Confidence matches rewards — no mismatch."""
    assert _compute_confidence_mismatch(0.7, [0.7] * PLATEAU_WINDOW) == 0.0


def test_confidence_mismatch_high_confidence_low_rewards():
    mismatch = _compute_confidence_mismatch(0.9, [0.5] * PLATEAU_WINDOW)
    assert mismatch > 0.0


def test_confidence_mismatch_below_threshold():
    mismatch = _compute_confidence_mismatch(0.6, [0.5] * PLATEAU_WINDOW)
    if 0.6 - 0.5 < CONFIDENCE_MISMATCH_THRESHOLD:
        assert mismatch == 0.0


# ─── Full regime signal ────────────────────────────────────────


def test_regime_insufficient_strategies():
    signal = compute_regime_signal(
        reward_history=[0.8] * 20,
        strategy_scores={"A": 1.0},
    )
    assert not signal.active


def test_regime_empty_scores():
    signal = compute_regime_signal(
        reward_history=[0.8] * 20,
        strategy_scores={},
    )
    assert not signal.active


def test_regime_no_plateau_no_trigger():
    """Without plateau, regime should not fire."""
    signal = compute_regime_signal(
        reward_history=[0.8] * 20,
        strategy_scores={"A": 1.0, "B": 0.0},
    )
    assert not signal.active


def test_regime_fires_on_plateau_with_dominance():
    peak = [1.0] * 30
    flat = [0.75] * PLATEAU_WINDOW
    history = peak + flat
    scores = {"A": 0.9, "B": 0.1}
    signal = compute_regime_signal(
        reward_history=history,
        strategy_scores=scores,
    )
    assert signal.active
    assert signal.strength > 0.0
    assert "reward_plateau" in signal.reason
    assert "strategy_dominance" in signal.reason


def test_regime_fires_on_plateau_with_trend_pressure():
    peak = [1.0] * 30
    flat = [0.75] * PLATEAU_WINDOW
    history = peak + flat
    scores = {"A": 0.5, "B": 0.5}
    signal = compute_regime_signal(
        reward_history=history,
        strategy_scores=scores,
        objective_trend="degrading",
    )
    assert signal.active
    assert "trend_pressure" in signal.reason


def test_regime_dampening_factor_bounded():
    peak = [1.0] * 30
    flat = [0.6] * PLATEAU_WINDOW
    history = peak + flat
    scores = {"A": 0.9, "B": 0.1}
    signal = compute_regime_signal(
        reward_history=history,
        strategy_scores=scores,
        objective_trend="degrading",
    )
    assert signal.dampening_factor >= MIN_DAMPENING
    assert signal.dampening_factor <= 1.0


def test_regime_exploration_boost_bounded():
    peak = [1.0] * 30
    flat = [0.6] * PLATEAU_WINDOW
    history = peak + flat
    scores = {"A": 0.9, "B": 0.1}
    signal = compute_regime_signal(
        reward_history=history,
        strategy_scores=scores,
    )
    assert 0.0 <= signal.exploration_boost <= 0.5


def test_regime_current_action_fallback():
    """When dominance signal doesn't identify a strategy, use current_action."""
    peak = [1.0] * 30
    flat = [0.75] * PLATEAU_WINDOW
    history = peak + flat
    scores = {"A": 0.4, "B": 0.3, "C": 0.3}
    signal = compute_regime_signal(
        reward_history=history,
        strategy_scores=scores,
        objective_trend="degrading",
        current_action="C",
    )
    assert signal.active
    assert signal.dampened_strategy == "C"


def test_regime_protected_strategy_not_dampened():
    peak = [1.0] * 30
    flat = [0.75] * PLATEAU_WINDOW
    history = peak + flat
    scores = {"RECOVER": 0.9, "B": 0.1}
    signal = compute_regime_signal(
        reward_history=history,
        strategy_scores=scores,
        objective_trend="degrading",
        current_action="RECOVER",
    )
    assert not signal.active or signal.dampened_strategy not in PROTECTED_STRATEGIES


def test_regime_to_dict_roundtrip():
    peak = [1.0] * 30
    flat = [0.75] * PLATEAU_WINDOW
    history = peak + flat
    signal = compute_regime_signal(
        reward_history=history,
        strategy_scores={"A": 0.9, "B": 0.1},
    )
    d = signal.to_dict()
    assert "active" in d
    assert "strength" in d
    assert "dampening_factor" in d
    assert isinstance(d["strength"], float)


# ─── Dampening application ──────────────────────────────────────


def test_dampening_inactive_signal():
    scores = {"A": 1.0, "B": 0.5}
    result = apply_regime_dampening(scores, NO_REGIME_BREAK)
    assert result == scores


def test_dampening_compresses_toward_mean():
    signal = RegimeSignal(
        active=True,
        strength=0.5,
        reason="reward_plateau",
        dampened_strategy="A",
        dampening_factor=0.5,
        exploration_boost=0.25,
    )
    scores = {"A": 1.0, "B": 0.0}
    result = apply_regime_dampening(scores, signal)
    assert result["A"] < scores["A"]
    assert result["B"] > scores["B"]


def test_dampening_preserves_budget_direction():
    """High scores decrease, low scores increase."""
    signal = RegimeSignal(
        active=True,
        strength=0.6,
        reason="reward_plateau",
        dampened_strategy="A",
        dampening_factor=0.5,
        exploration_boost=0.3,
    )
    scores = {"A": 1.0, "B": 0.3, "C": 0.1}
    result = apply_regime_dampening(scores, signal)
    assert result["A"] < scores["A"]
    assert result["C"] > scores["C"]


def test_dampening_protected_strategy_unchanged():
    signal = RegimeSignal(
        active=True,
        strength=0.5,
        reason="reward_plateau",
        dampened_strategy="A",
        dampening_factor=0.5,
        exploration_boost=0.25,
    )
    scores = {"A": 1.0, "RECOVER": 0.8, "B": 0.2}
    result = apply_regime_dampening(scores, signal)
    assert result["RECOVER"] == scores["RECOVER"]


def test_dampening_never_negative():
    signal = RegimeSignal(
        active=True,
        strength=0.9,
        reason="reward_plateau",
        dampened_strategy="A",
        dampening_factor=0.3,
        exploration_boost=0.45,
    )
    scores = {"A": 0.1, "B": -0.5, "C": 0.0}
    result = apply_regime_dampening(scores, signal)
    for v in result.values():
        assert v >= 0.0


def test_dampening_does_not_mutate_input():
    signal = RegimeSignal(
        active=True,
        strength=0.5,
        reason="reward_plateau",
        dampened_strategy="A",
        dampening_factor=0.5,
        exploration_boost=0.25,
    )
    scores = {"A": 1.0, "B": 0.0}
    original = dict(scores)
    apply_regime_dampening(scores, signal)
    assert scores == original


def test_dampening_target_not_in_scores():
    signal = RegimeSignal(
        active=True,
        strength=0.5,
        reason="reward_plateau",
        dampened_strategy="X",
        dampening_factor=0.5,
        exploration_boost=0.25,
    )
    scores = {"A": 1.0, "B": 0.5}
    result = apply_regime_dampening(scores, signal)
    assert result == scores


def test_dampening_protected_target():
    signal = RegimeSignal(
        active=True,
        strength=0.5,
        reason="reward_plateau",
        dampened_strategy="RECOVER",
        dampening_factor=0.5,
        exploration_boost=0.25,
    )
    scores = {"RECOVER": 1.0, "B": 0.5}
    result = apply_regime_dampening(scores, signal)
    assert result == scores


# ─── Select regime override ────────────────────────────────────


def test_override_inactive_signal():
    signal = NO_REGIME_BREAK
    assert select_regime_override(signal, {"A": 0.0, "B": 1.0}, step=0) is None


def test_override_low_strength():
    signal = RegimeSignal(
        active=True,
        strength=0.3,
        reason="",
        dampened_strategy="A",
        dampening_factor=0.7,
        exploration_boost=0.15,
    )
    assert select_regime_override(signal, {"A": 1.0, "B": 0.0}, step=0) is None


def test_override_no_untried():
    signal = RegimeSignal(
        active=True,
        strength=0.5,
        reason="",
        dampened_strategy="A",
        dampening_factor=0.5,
        exploration_boost=0.25,
    )
    scores = {"A": 1.0, "B": 0.5}
    assert select_regime_override(signal, scores, step=0) is None


def test_override_selects_untried():
    signal = RegimeSignal(
        active=True,
        strength=0.5,
        reason="",
        dampened_strategy="A",
        dampening_factor=0.5,
        exploration_boost=0.25,
    )
    scores = {"A": 1.0, "B": 0.0, "C": 0.5}
    result = select_regime_override(signal, scores, step=0)
    assert result == "B"


def test_override_rotates_through_untried():
    signal = RegimeSignal(
        active=True,
        strength=0.5,
        reason="",
        dampened_strategy="A",
        dampening_factor=0.5,
        exploration_boost=0.25,
    )
    scores = {"A": 1.0, "B": 0.0, "C": 0.0}
    r0 = select_regime_override(signal, scores, step=0)
    r1 = select_regime_override(signal, scores, step=1)
    assert {r0, r1} == {"B", "C"}


def test_override_skips_protected():
    signal = RegimeSignal(
        active=True,
        strength=0.5,
        reason="",
        dampened_strategy="A",
        dampening_factor=0.5,
        exploration_boost=0.25,
    )
    scores = {"A": 1.0, "RECOVER": 0.0, "B": 0.0}
    result = select_regime_override(signal, scores, step=0)
    assert result == "B"
    assert result not in PROTECTED_STRATEGIES


def test_override_negative_score_not_untried():
    """Negative-scored strategies were tried and failed — not untried."""
    signal = RegimeSignal(
        active=True,
        strength=0.5,
        reason="",
        dampened_strategy="A",
        dampening_factor=0.5,
        exploration_boost=0.25,
    )
    scores = {"A": 1.0, "B": -0.5, "C": 0.0}
    result = select_regime_override(signal, scores, step=0)
    assert result == "C"


def test_override_deterministic():
    signal = RegimeSignal(
        active=True,
        strength=0.5,
        reason="",
        dampened_strategy="A",
        dampening_factor=0.5,
        exploration_boost=0.25,
    )
    scores = {"A": 1.0, "B": 0.0, "C": 0.0}
    results = [select_regime_override(signal, scores, step=5) for _ in range(10)]
    assert len(set(results)) == 1


# ─── Determinism ────────────────────────────────────────────────


def test_regime_signal_deterministic():
    peak = [1.0] * 30
    flat = [0.75] * PLATEAU_WINDOW
    history = peak + flat
    scores = {"A": 0.9, "B": 0.1}
    kwargs = dict(
        reward_history=history,
        strategy_scores=scores,
        plan_confidence=0.8,
        objective_trend="degrading",
    )
    s1 = compute_regime_signal(**kwargs)
    s2 = compute_regime_signal(**kwargs)
    assert s1 == s2


def test_dampening_deterministic():
    signal = RegimeSignal(
        active=True,
        strength=0.5,
        reason="plateau",
        dampened_strategy="A",
        dampening_factor=0.5,
        exploration_boost=0.25,
    )
    scores = {"A": 1.0, "B": 0.3, "C": 0.1}
    r1 = apply_regime_dampening(scores, signal)
    r2 = apply_regime_dampening(scores, signal)
    assert r1 == r2


# ─── No false positives ────────────────────────────────────────


def test_no_false_positive_improving_rewards():
    """Steadily improving rewards should not trigger regime."""
    history = [0.5 + i * 0.01 for i in range(30)]
    scores = {"A": 0.6, "B": 0.4}
    signal = compute_regime_signal(
        reward_history=history,
        strategy_scores=scores,
        objective_trend="improving",
    )
    assert not signal.active


def test_no_false_positive_early_history():
    """Short history should never trigger."""
    history = [0.7] * 10
    scores = {"A": 0.8, "B": 0.2}
    signal = compute_regime_signal(
        reward_history=history,
        strategy_scores=scores,
    )
    assert not signal.active


def test_no_false_positive_high_variance():
    """High-variance rewards are not a plateau."""
    import random

    rng = random.Random(42)
    history = [1.0] * 20 + [rng.uniform(0.3, 1.0) for _ in range(PLATEAU_WINDOW)]
    scores = {"A": 0.7, "B": 0.3}
    signal = compute_regime_signal(
        reward_history=history,
        strategy_scores=scores,
    )
    assert not signal.active


# ─── No oscillation ────────────────────────────────────────────


def test_no_oscillation_stable_regime():
    """Regime should produce stable output for stable inputs."""
    peak = [1.0] * 30
    flat = [0.75] * PLATEAU_WINDOW
    history = peak + flat
    scores = {"A": 0.9, "B": 0.1}
    signals = []
    for _ in range(10):
        sig = compute_regime_signal(
            reward_history=history,
            strategy_scores=scores,
        )
        signals.append(sig.strength)
    assert len(set(signals)) == 1


def test_no_oscillation_gradual_recovery():
    """As rewards improve, regime signal should weaken monotonically."""
    base = [1.0] * 20
    scores = {"A": 0.8, "B": 0.2}
    strengths = []
    for r in [0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9]:
        history = base + [r] * PLATEAU_WINDOW
        sig = compute_regime_signal(
            reward_history=history,
            strategy_scores=scores,
            objective_trend="flat",
        )
        strengths.append(sig.strength)
    for i in range(1, len(strengths)):
        assert strengths[i] <= strengths[i - 1] + 0.01


# ─── Benchmark integration ─────────────────────────────────────


def test_benchmark_adversarial_improvement():
    """Regime engine must improve adversarial over exploration-only."""
    from umh.runtime_engine.benchmark_env import run_full_benchmark

    result = run_full_benchmark()
    exploration = result.results["eos_exploration"]["AdversarialScenario"]
    regime = result.results["eos_regime"]["AdversarialScenario"]
    assert regime.avg_reward >= exploration.avg_reward


def test_benchmark_static_no_regression():
    from umh.runtime_engine.benchmark_env import run_full_benchmark

    result = run_full_benchmark()
    regime = result.results["eos_regime"]["StaticScenario"]
    assert regime.avg_reward >= 0.99


def test_benchmark_noisy_no_regression():
    from umh.runtime_engine.benchmark_env import run_full_benchmark

    result = run_full_benchmark()
    exploration = result.results["eos_exploration"]["NoisyScenario"]
    regime = result.results["eos_regime"]["NoisyScenario"]
    assert regime.avg_reward >= exploration.avg_reward - 0.01


def test_benchmark_shifting_no_regression():
    from umh.runtime_engine.benchmark_env import run_full_benchmark

    result = run_full_benchmark()
    exploration = result.results["eos_exploration"]["ShiftingScenario"]
    regime = result.results["eos_regime"]["ShiftingScenario"]
    assert regime.avg_reward >= exploration.avg_reward - 0.01


def test_benchmark_deterministic():
    from umh.runtime_engine.benchmark_env import run_full_benchmark

    r1 = run_full_benchmark()
    r2 = run_full_benchmark()
    for scenario in [
        "StaticScenario",
        "ShiftingScenario",
        "NoisyScenario",
        "AdversarialScenario",
    ]:
        assert (
            r1.results["eos_regime"][scenario].avg_reward
            == r2.results["eos_regime"][scenario].avg_reward
        )
