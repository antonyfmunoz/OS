"""
Context disambiguation engine — classifies environment state.

Distinguishes between:
- Normal regime transitions
- Adversarial traps
- Noise / stochastic fluctuation
- Slow drift

Does NOT modify decisions directly. Produces a ContextSignal
that gates or scales downstream correction signals.

Deterministic. Bounded. EMA-smoothed. No randomness.
"""

from __future__ import annotations

from dataclasses import dataclass

CONTEXT_WINDOW = 20
LONG_WINDOW = 100
EMA_ALPHA = 0.15
MIN_OBSERVATIONS = 10


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def _linear_slope(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    num = 0.0
    den = 0.0
    for i, y in enumerate(values):
        dx = i - x_mean
        num += dx * (y - y_mean)
        den += dx * dx
    if den == 0.0:
        return 0.0
    return num / den


def _variance(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((v - mean) ** 2 for v in values) / len(values)


def _switch_rate(actions: list[str]) -> float:
    if len(actions) < 2:
        return 0.0
    switches = sum(1 for i in range(1, len(actions)) if actions[i] != actions[i - 1])
    return switches / (len(actions) - 1)


def _lag_correlation(values: list[float], lag: int) -> float:
    """Simple autocorrelation at given lag. Returns [-1, 1]."""
    n = len(values)
    if n < lag + 2:
        return 0.0
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values)
    if var == 0.0:
        return 0.0
    cov = sum((values[i] - mean) * (values[i - lag] - mean) for i in range(lag, n))
    return cov / var


@dataclass(frozen=True)
class ContextSignal:
    """Immutable context classification."""

    regime_change_likelihood: float
    adversarial_likelihood: float
    noise_level: float
    drift_strength: float
    dominant_type: str

    def to_dict(self) -> dict:
        return {
            "regime_change_likelihood": round(self.regime_change_likelihood, 4),
            "adversarial_likelihood": round(self.adversarial_likelihood, 4),
            "noise_level": round(self.noise_level, 4),
            "drift_strength": round(self.drift_strength, 4),
            "dominant_type": self.dominant_type,
        }


NO_CONTEXT_SIGNAL = ContextSignal(
    regime_change_likelihood=0.0,
    adversarial_likelihood=0.0,
    noise_level=0.0,
    drift_strength=0.0,
    dominant_type="unknown",
)


class ContextClassifier:
    """Stateful context classifier with EMA smoothing.

    Consumes action + reward history. Produces a ContextSignal
    classifying the current environment state.
    """

    def __init__(self) -> None:
        self._regime_ema: float = 0.0
        self._adversarial_ema: float = 0.0
        self._noise_ema: float = 0.0
        self._drift_ema: float = 0.0
        self._observations: int = 0

    def classify(
        self,
        recent_actions: list[str],
        recent_rewards: list[float],
    ) -> ContextSignal:
        if len(recent_rewards) < MIN_OBSERVATIONS:
            return NO_CONTEXT_SIGNAL

        window_rewards = recent_rewards[-CONTEXT_WINDOW:]
        window_actions = recent_actions[-CONTEXT_WINDOW:]
        long_rewards = recent_rewards[-LONG_WINDOW:]

        slope = _linear_slope(window_rewards)
        var = _variance(window_rewards)
        sr = _switch_rate(window_actions)

        peak = max(recent_rewards) if recent_rewards else 1.0
        if peak <= 0.0:
            peak = 1.0
        current_avg = sum(window_rewards) / len(window_rewards)
        peak_drop = _clamp(1.0 - (current_avg / peak), 0.0, 1.0)

        periodicity = 0.0
        if len(long_rewards) >= 20:
            best_corr = 0.0
            for lag in range(5, min(len(long_rewards) // 2, 30)):
                corr = abs(_lag_correlation(long_rewards, lag))
                if corr > best_corr:
                    best_corr = corr
            periodicity = best_corr

        raw_adversarial = self._compute_adversarial(
            slope, var, sr, peak_drop, periodicity
        )
        raw_regime = self._compute_regime(slope, var, sr, peak_drop, periodicity)
        raw_noise = self._compute_noise(slope, var)
        raw_drift = self._compute_drift(long_rewards)

        self._regime_ema = EMA_ALPHA * raw_regime + (1.0 - EMA_ALPHA) * self._regime_ema
        self._adversarial_ema = (
            EMA_ALPHA * raw_adversarial + (1.0 - EMA_ALPHA) * self._adversarial_ema
        )
        self._noise_ema = EMA_ALPHA * raw_noise + (1.0 - EMA_ALPHA) * self._noise_ema
        self._drift_ema = EMA_ALPHA * raw_drift + (1.0 - EMA_ALPHA) * self._drift_ema
        self._observations += 1

        regime = _clamp(self._regime_ema, 0.0, 1.0)
        adversarial = _clamp(self._adversarial_ema, 0.0, 1.0)
        noise = _clamp(self._noise_ema, 0.0, 1.0)
        drift = _clamp(self._drift_ema, 0.0, 1.0)

        scores = {
            "regime_change": regime,
            "adversarial": adversarial,
            "noise": noise,
            "drift": drift,
        }
        dominant = max(scores, key=scores.get)
        if all(v < 0.05 for v in scores.values()):
            dominant = "stable"

        return ContextSignal(
            regime_change_likelihood=regime,
            adversarial_likelihood=adversarial,
            noise_level=noise,
            drift_strength=drift,
            dominant_type=dominant,
        )

    def _compute_adversarial(
        self, slope: float, var: float, sr: float, peak_drop: float, periodicity: float
    ) -> float:
        drop_signal = _clamp(peak_drop * 3.0, 0.0, 1.0)
        if drop_signal < 0.1:
            return 0.0
        sharp_drop = _clamp(-slope * 15.0, 0.0, 1.0)
        low_var = _clamp(1.0 - var * 5.0, 0.0, 1.0)
        low_switch = _clamp(1.0 - sr * 2.0, 0.0, 1.0)
        not_periodic = _clamp(1.0 - periodicity * 2.0, 0.0, 1.0)

        modifiers = (sharp_drop + low_var + low_switch + not_periodic) / 4.0
        return _clamp(drop_signal * modifiers, 0.0, 1.0)

    def _compute_regime(
        self,
        slope: float,
        var: float,
        sr: float,
        peak_drop: float,
        periodicity: float,
    ) -> float:
        drop_present = _clamp(peak_drop * 3.0, 0.0, 1.0)
        if drop_present < 0.1:
            return 0.0
        reward_drop = _clamp(-slope * 10.0, 0.0, 1.0)
        high_switch = _clamp(sr * 2.0, 0.0, 1.0)
        periodic = _clamp(periodicity * 2.0, 0.0, 1.0)

        raw = (
            drop_present * 0.3
            + periodic * 0.4
            + high_switch * 0.15
            + reward_drop * 0.15
        )
        return _clamp(raw, 0.0, 1.0)

    def _compute_noise(self, slope: float, var: float) -> float:
        high_var = _clamp(var * 10.0, 0.0, 1.0)
        no_slope = _clamp(1.0 - abs(slope) * 20.0, 0.0, 1.0)
        return _clamp(high_var * no_slope, 0.0, 1.0)

    def _compute_drift(self, long_rewards: list[float]) -> float:
        if len(long_rewards) < LONG_WINDOW:
            return 0.0
        window = long_rewards[-LONG_WINDOW:]
        slope = _linear_slope(window)
        if slope >= 0.0:
            return 0.0
        return _clamp(-slope * 50.0, 0.0, 1.0)

    def snapshot(self) -> dict:
        return {
            "regime_ema": self._regime_ema,
            "adversarial_ema": self._adversarial_ema,
            "noise_ema": self._noise_ema,
            "drift_ema": self._drift_ema,
            "observations": self._observations,
        }

    def restore(self, data: dict) -> None:
        if not data or not isinstance(data, dict):
            return
        self._regime_ema = float(data.get("regime_ema", 0.0))
        self._adversarial_ema = float(data.get("adversarial_ema", 0.0))
        self._noise_ema = float(data.get("noise_ema", 0.0))
        self._drift_ema = float(data.get("drift_ema", 0.0))
        self._observations = int(data.get("observations", 0))

    def reset(self) -> None:
        self.__init__()


def gate_trap_adjustment(
    trap_adjustment: float,
    context: ContextSignal,
) -> float:
    non_adversarial = max(
        context.regime_change_likelihood,
        context.noise_level,
        context.drift_strength,
    )
    if non_adversarial < 0.01:
        return trap_adjustment
    ratio = context.adversarial_likelihood / (
        context.adversarial_likelihood + non_adversarial + 1e-9
    )
    return trap_adjustment * _clamp(ratio * 2.0, 0.0, 1.0)


def gate_stability_effect(
    exploration_adj: float,
    confidence_adj: float,
    context: ContextSignal,
) -> tuple[float, float]:
    suppress = max(
        context.noise_level,
        context.drift_strength,
        context.regime_change_likelihood,
    )
    if suppress > 0.15:
        dampen = _clamp(1.0 - suppress, 0.0, 1.0)
        return exploration_adj * dampen, confidence_adj * dampen
    return exploration_adj, confidence_adj


def boost_exploration_for_regime(
    plan_confidence: float | None,
    context: ContextSignal,
) -> float | None:
    if plan_confidence is None:
        return None
    if context.regime_change_likelihood > 0.1:
        boost = context.regime_change_likelihood * 0.5
        return max(0.0, min(1.0, plan_confidence - boost))
    return plan_confidence


def gate_failure_streak_for_regime(
    failure_streak: int,
    context: ContextSignal,
) -> int:
    """During regime changes, suppress failure streak to prevent exploration activation.

    Consecutive failures after a regime shift are expected behavior, not a broken
    strategy. The exploration engine uses failure_streak to trigger redistribution,
    but during transitions this introduces random bias among tied actions.
    """
    if context.regime_change_likelihood > 0.15:
        return 0
    return failure_streak


def gate_exploration_inputs(
    failure_streak: int,
    objective_trend: str | None,
    recent_rewards: list[float],
    context: ContextSignal,
) -> tuple[int, str | None]:
    """Gate exploration engine inputs during detected or suspected regime changes.

    Two detection paths:
    1. Context engine detects regime_change (EMA-smoothed, ~5 step lag)
    2. Sharp reward drop from recent average (instant, catches first step)

    During transitions, failure streaks and degrading trends are expected —
    they should not trigger exploration redistribution.
    """
    if context.regime_change_likelihood > 0.15:
        return 0, "flat"

    if len(recent_rewards) >= 6:
        recent_avg = sum(recent_rewards[-3:]) / 3
        prior_avg = sum(recent_rewards[-6:-3]) / 3
        if prior_avg > 0.7 and recent_avg < prior_avg * 0.85:
            return 0, "flat"

    return failure_streak, objective_trend


def diversify_scores_for_regime(
    strategy_scores: dict[str, float],
    context: ContextSignal,
) -> dict[str, float]:
    """During regime changes, flatten score distribution to encourage exploration.

    Pulls all scores toward the mean proportionally to regime_change_likelihood.
    """
    if context.regime_change_likelihood < 0.2:
        return strategy_scores
    if not strategy_scores:
        return strategy_scores

    mean = sum(strategy_scores.values()) / len(strategy_scores)
    blend = _clamp(context.regime_change_likelihood * 0.5, 0.0, 0.4)

    result: dict[str, float] = {}
    for name, score in strategy_scores.items():
        result[name] = score * (1.0 - blend) + mean * blend

    return result
