"""
UMH Goal Engine — adaptive objective weight tuning.

Dynamically adjusts objective dimension weights based on long-horizon outcomes,
regime shifts, and performance patterns. Sits before objective evaluation.

Default weights (from objective_engine.py):
    goal_progress=0.30, plan_execution=0.25, stability=0.20,
    confidence=0.15, policy_coherence=0.10

This module adapts them within bounded ranges (±MAX_ADJUSTMENT_RATIO of
default) using EMA-smoothed signals. Weights always sum to 1.0.

This is NOT letting the system "choose any goal." This is controlled,
bounded, evidence-based objective adaptation.

Deterministic. Bounded. No LLM calls. No state mutation (except EMA).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ─── Default weights (mirrors objective_engine.py) ───────────────

DEFAULT_WEIGHTS: dict[str, float] = {
    "goal_progress": 0.30,
    "plan_execution": 0.25,
    "stability": 0.20,
    "confidence": 0.15,
    "policy_coherence": 0.10,
}

DIMENSIONS = tuple(DEFAULT_WEIGHTS.keys())

# ─── Constants ────────────────────────────────────────────────────

MAX_ADJUSTMENT_RATIO = 0.20
EMA_ALPHA = 0.08
MIN_HISTORY = 5
REGRET_LOOKBACK = 10
PLATEAU_WINDOW = 8
PLATEAU_VARIANCE_THRESHOLD = 0.02**2
INSTABILITY_STREAK_THRESHOLD = 2
RISK_SPIKE_THRESHOLD = 0.6
CORRELATION_MIN_SAMPLES = 5

EPSILON = 1e-9


# ─── Helpers ──────────────────────────────────────────────────────


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def _normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    """Normalize weights to sum to 1.0. Preserves relative proportions."""
    total = sum(weights.values())
    if total <= EPSILON:
        return dict(DEFAULT_WEIGHTS)
    return {k: v / total for k, v in weights.items()}


# ─── Data structures ─────────────────────────────────────────────


@dataclass(frozen=True)
class GoalWeightAdjustment:
    """Single weight adjustment with reasoning."""

    dimension: str
    default_weight: float
    adjusted_weight: float
    delta: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "default_weight": round(self.default_weight, 4),
            "adjusted_weight": round(self.adjusted_weight, 4),
            "delta": round(self.delta, 6),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class GoalAdaptationResult:
    """Output of goal engine: adapted weights + reasoning."""

    active: bool
    weights: dict[str, float]
    adjustments: tuple[GoalWeightAdjustment, ...]
    regime_alignment: str
    reasoning: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "weights": {k: round(v, 6) for k, v in self.weights.items()},
            "adjustments": [a.to_dict() for a in self.adjustments],
            "regime_alignment": self.regime_alignment,
            "reasoning": self.reasoning,
        }


NO_ADAPTATION = GoalAdaptationResult(
    active=False,
    weights=dict(DEFAULT_WEIGHTS),
    adjustments=(),
    regime_alignment="neutral",
    reasoning="insufficient_history",
)


# ─── Signal extraction ───────────────────────────────────────────


def _compute_dimension_correlation(
    component_history: dict[str, list[float]],
    reward_history: list[float],
) -> dict[str, float]:
    """Compute correlation between each dimension and long-term reward.

    Returns a dict of {dimension: correlation} where correlation ∈ [-1, 1].
    Uses simplified Pearson-like correlation: covariance / (std_a × std_b).
    """
    n = len(reward_history)
    if n < CORRELATION_MIN_SAMPLES:
        return {}

    reward_mean = sum(reward_history) / n
    reward_var = sum((r - reward_mean) ** 2 for r in reward_history) / n
    reward_std = reward_var**0.5 if reward_var > 0 else 0.0

    if reward_std < EPSILON:
        return {}

    correlations: dict[str, float] = {}
    for dim in DIMENSIONS:
        values = component_history.get(dim, [])
        if len(values) < n:
            continue
        values = values[-n:]

        dim_mean = sum(values) / n
        dim_var = sum((v - dim_mean) ** 2 for v in values) / n
        dim_std = dim_var**0.5 if dim_var > 0 else 0.0

        if dim_std < EPSILON:
            correlations[dim] = 0.0
            continue

        cov = sum((values[i] - dim_mean) * (reward_history[i] - reward_mean) for i in range(n)) / n

        correlations[dim] = _clamp(cov / (dim_std * reward_std), -1.0, 1.0)

    return correlations


def _compute_regret(
    reward_history: list[float],
    component_history: dict[str, list[float]],
) -> dict[str, float]:
    """Compute regret per dimension: how much performance was left on the table.

    Regret for a dimension = average gap between its peak and actual,
    weighted by how much that dimension was contributing when rewards dropped.
    """
    n = min(len(reward_history), REGRET_LOOKBACK)
    if n < CORRELATION_MIN_SAMPLES:
        return {}

    recent_rewards = reward_history[-n:]
    peak_reward = max(recent_rewards)

    regret: dict[str, float] = {}
    for dim in DIMENSIONS:
        values = component_history.get(dim, [])
        if len(values) < n:
            continue
        recent = values[-n:]

        dim_regret = 0.0
        for i in range(n):
            reward_gap = peak_reward - recent_rewards[i]
            dim_value = recent[i]
            dim_regret += reward_gap * (1.0 - dim_value)

        regret[dim] = _clamp(dim_regret / max(n, 1), 0.0, 1.0)

    return regret


def _detect_regime(
    failure_streak: int,
    regime_active: bool,
    regime_strength: float,
    reward_history: list[float],
    risk_level: float,
) -> str:
    """Classify the current regime for weight adaptation.

    Returns one of: "stable", "unstable", "plateau", "recovery", "risk_spike".
    """
    if failure_streak >= INSTABILITY_STREAK_THRESHOLD:
        return "unstable"

    if risk_level >= RISK_SPIKE_THRESHOLD:
        return "risk_spike"

    if regime_active and regime_strength >= 0.3:
        return "plateau"

    if len(reward_history) >= PLATEAU_WINDOW:
        recent = reward_history[-PLATEAU_WINDOW:]
        mean = sum(recent) / len(recent)
        variance = sum((r - mean) ** 2 for r in recent) / len(recent)
        if variance < PLATEAU_VARIANCE_THRESHOLD:
            return "plateau"

    if failure_streak == 0 and len(reward_history) >= 3:
        recent_3 = reward_history[-3:]
        if all(recent_3[i] > recent_3[i - 1] for i in range(1, len(recent_3))):
            return "recovery"

    return "stable"


# ─── Regime-specific weight pressures ────────────────────────────


def _regime_pressure(regime: str) -> dict[str, float]:
    """Compute regime-specific pressure on each dimension.

    Returns pressure values ∈ [-1, 1] where positive = increase weight,
    negative = decrease weight. These are scaled by MAX_ADJUSTMENT_RATIO
    before application.
    """
    if regime == "unstable":
        return {
            "goal_progress": -0.3,
            "plan_execution": 0.0,
            "stability": 1.0,
            "confidence": 0.3,
            "policy_coherence": 0.4,
        }

    if regime == "plateau":
        return {
            "goal_progress": 0.5,
            "plan_execution": -0.2,
            "stability": -0.3,
            "confidence": -0.2,
            "policy_coherence": -0.3,
        }

    if regime == "risk_spike":
        return {
            "goal_progress": -0.4,
            "plan_execution": -0.2,
            "stability": 0.8,
            "confidence": 0.5,
            "policy_coherence": 0.2,
        }

    if regime == "recovery":
        return {
            "goal_progress": 0.3,
            "plan_execution": 0.4,
            "stability": -0.1,
            "confidence": 0.2,
            "policy_coherence": -0.2,
        }

    return {dim: 0.0 for dim in DIMENSIONS}


# ─── Core adaptation ─────────────────────────────────────────────


def compute_weight_adjustments(
    reward_history: list[float],
    component_history: dict[str, list[float]],
    failure_streak: int = 0,
    regime_active: bool = False,
    regime_strength: float = 0.0,
    risk_level: float = 0.0,
    current_weights: dict[str, float] | None = None,
) -> GoalAdaptationResult:
    """Compute adaptive weight adjustments based on long-horizon signals.

    Combines three signal sources:
    1. Dimension-reward correlation: increase weight on dimensions that
       correlate with reward, decrease on those that anti-correlate.
    2. Regret signals: increase weight on dimensions with high regret.
    3. Regime pressure: shift weights based on current regime classification.

    All adjustments are bounded to ±MAX_ADJUSTMENT_RATIO of default weight,
    then normalized to sum to 1.0.
    """
    if len(reward_history) < MIN_HISTORY:
        return NO_ADAPTATION

    base = current_weights if current_weights else dict(DEFAULT_WEIGHTS)

    regime = _detect_regime(
        failure_streak=failure_streak,
        regime_active=regime_active,
        regime_strength=regime_strength,
        reward_history=reward_history,
        risk_level=risk_level,
    )

    correlations = _compute_dimension_correlation(component_history, reward_history)
    regret = _compute_regret(reward_history, component_history)
    pressure = _regime_pressure(regime)

    adjustments: list[GoalWeightAdjustment] = []
    raw_weights: dict[str, float] = {}

    for dim in DIMENSIONS:
        default_w = DEFAULT_WEIGHTS[dim]
        current_w = base.get(dim, default_w)
        max_delta = default_w * MAX_ADJUSTMENT_RATIO

        corr_signal = correlations.get(dim, 0.0) * 0.4
        regret_signal = regret.get(dim, 0.0) * 0.3
        regime_signal = pressure.get(dim, 0.0) * 0.3

        raw_delta = (corr_signal + regret_signal + regime_signal) * max_delta

        clamped_delta = _clamp(raw_delta, -max_delta, max_delta)

        new_weight = max(current_w + clamped_delta, EPSILON)
        raw_weights[dim] = new_weight

        reasons: list[str] = []
        if abs(correlations.get(dim, 0.0)) > 0.1:
            reasons.append(f"corr={correlations[dim]:.2f}")
        if regret.get(dim, 0.0) > 0.1:
            reasons.append(f"regret={regret[dim]:.2f}")
        if abs(pressure.get(dim, 0.0)) > 0.1:
            reasons.append(f"regime={regime}")

        adjustments.append(
            GoalWeightAdjustment(
                dimension=dim,
                default_weight=default_w,
                adjusted_weight=new_weight,
                delta=clamped_delta,
                reason="+".join(reasons) if reasons else "no_signal",
            )
        )

    normalized = _normalize_weights(raw_weights)

    final_adjustments: list[GoalWeightAdjustment] = []
    for adj in adjustments:
        final_w = normalized[adj.dimension]
        final_adjustments.append(
            GoalWeightAdjustment(
                dimension=adj.dimension,
                default_weight=adj.default_weight,
                adjusted_weight=final_w,
                delta=final_w - adj.default_weight,
                reason=adj.reason,
            )
        )

    has_meaningful_change = any(abs(a.delta) > EPSILON for a in final_adjustments)

    return GoalAdaptationResult(
        active=has_meaningful_change,
        weights=normalized,
        adjustments=tuple(final_adjustments),
        regime_alignment=regime,
        reasoning=f"regime={regime},dims_adjusted={sum(1 for a in final_adjustments if abs(a.delta) > EPSILON)}",
    )


# ─── EMA-smoothed state ──────────────────────────────────────────


@dataclass
class GoalEngineState:
    """Persistent state for EMA-smoothed weight adaptation across turns.

    The goal engine updates weights slowly via EMA to prevent oscillation.
    New computed weights are blended with prior weights each turn.
    """

    current_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    turn_count: int = 0
    reward_history: list[float] = field(default_factory=list)
    component_history: dict[str, list[float]] = field(default_factory=dict)
    _max_history: int = 50

    def record_turn(
        self,
        reward: float,
        components: dict[str, float],
    ) -> None:
        """Record a turn's objective data for long-horizon analysis."""
        self.reward_history.append(reward)
        if len(self.reward_history) > self._max_history:
            self.reward_history = self.reward_history[-self._max_history :]

        for dim in DIMENSIONS:
            if dim not in self.component_history:
                self.component_history[dim] = []
            self.component_history[dim].append(components.get(dim, 0.0))
            if len(self.component_history[dim]) > self._max_history:
                self.component_history[dim] = self.component_history[dim][-self._max_history :]

        self.turn_count += 1

    def update_weights(
        self,
        target_weights: dict[str, float],
    ) -> dict[str, float]:
        """EMA-blend target weights with current weights.

        Slow update prevents oscillation: new_weight = α × target + (1-α) × current.
        """
        blended: dict[str, float] = {}
        for dim in DIMENSIONS:
            current = self.current_weights.get(dim, DEFAULT_WEIGHTS.get(dim, 0.0))
            target = target_weights.get(dim, current)
            blended[dim] = EMA_ALPHA * target + (1.0 - EMA_ALPHA) * current

        self.current_weights = _normalize_weights(blended)
        return dict(self.current_weights)

    def adapt(
        self,
        failure_streak: int = 0,
        regime_active: bool = False,
        regime_strength: float = 0.0,
        risk_level: float = 0.0,
    ) -> GoalAdaptationResult:
        """Run full adaptation cycle using accumulated history.

        Computes target weights, EMA-blends with current, and returns result.
        """
        result = compute_weight_adjustments(
            reward_history=self.reward_history,
            component_history=self.component_history,
            failure_streak=failure_streak,
            regime_active=regime_active,
            regime_strength=regime_strength,
            risk_level=risk_level,
            current_weights=self.current_weights,
        )

        if result.active:
            self.update_weights(result.weights)
            return GoalAdaptationResult(
                active=True,
                weights=dict(self.current_weights),
                adjustments=result.adjustments,
                regime_alignment=result.regime_alignment,
                reasoning=result.reasoning,
            )

        return GoalAdaptationResult(
            active=False,
            weights=dict(self.current_weights),
            adjustments=result.adjustments,
            regime_alignment=result.regime_alignment,
            reasoning=result.reasoning,
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "current_weights": {k: round(v, 6) for k, v in self.current_weights.items()},
            "turn_count": self.turn_count,
            "reward_history": [round(r, 6) for r in self.reward_history],
            "component_history": {
                k: [round(v, 6) for v in vs] for k, vs in self.component_history.items()
            },
        }

    def restore(self, data: dict | None) -> None:
        if not data or not isinstance(data, dict):
            return
        weights = data.get("current_weights")
        if weights and isinstance(weights, dict):
            self.current_weights = {k: float(v) for k, v in weights.items() if k in DIMENSIONS}
            self.current_weights = _normalize_weights(self.current_weights)
        try:
            self.turn_count = int(data.get("turn_count", 0))
        except (ValueError, TypeError):
            self.turn_count = 0
        self.reward_history = [float(r) for r in data.get("reward_history", [])]
        ch = data.get("component_history", {})
        if isinstance(ch, dict):
            self.component_history = {
                k: [float(v) for v in vs]
                for k, vs in ch.items()
                if k in DIMENSIONS and isinstance(vs, list)
            }


# ─── Integration with ObjectiveEngine ────────────────────────────


def apply_adapted_weights(
    weights: dict[str, float],
    components: dict[str, float],
) -> float:
    """Compute objective value using adapted weights instead of defaults.

    Drop-in replacement for the weighted sum in compute_objective().
    """
    value = sum(
        components.get(dim, 0.0) * weights.get(dim, DEFAULT_WEIGHTS.get(dim, 0.0))
        for dim in DIMENSIONS
    )
    return _clamp(value, 0.0, 1.0)
