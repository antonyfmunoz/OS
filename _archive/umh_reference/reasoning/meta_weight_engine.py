"""
MetaWeightEngine — deterministic weight adaptation for influence signals.

Tracks per-signal EMA performance based on outcome quality and adjusts
the base influence weights accordingly.  Weights are bounded, normalized
to sum to 1.0, and applied additively to the base weights.

Learning rule per signal::

    contribution_i = signal_value_i * outcome_quality
    ema_i = alpha * contribution_i + (1 - alpha) * ema_i
    adjustment_i = (ema_i - baseline_i) * META_WEIGHT_SCALE
    final_weight_i = base_weight_i + adjustment_i
    final_weights = normalize(final_weights)  # sum to 1.0

No LLM calls.  No randomness.  Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass


META_WEIGHT_ALPHA = 0.15
META_WEIGHT_SCALE = 0.30
MAX_ADJUSTMENT = 0.10
MIN_WEIGHT = 0.02
MIN_OBSERVATIONS = 3
META_SIGNAL_K = 0.5
META_SIGNAL_MIN_OBS = 10

SIGNAL_NAMES = (
    "goal",
    "plan",
    "strategy",
    "state_bias",
    "credit",
    "exploration",
    "commitment",
)


@dataclass
class SignalPerformance:
    """Per-signal EMA tracker for outcome-correlated performance."""

    ema: float = 0.0
    observations: int = 0
    last_contribution: float = 0.0
    ema_variance: float = 0.0
    direction_consistency: float = 0.0
    _last_delta: float = 0.0

    def update(self, contribution: float, alpha: float = META_WEIGHT_ALPHA) -> None:
        old_ema = self.ema
        self.last_contribution = contribution
        self.observations += 1
        self.ema = alpha * contribution + (1.0 - alpha) * self.ema

        delta = contribution - old_ema
        self.ema_variance = alpha * (delta * delta) + (1.0 - alpha) * self.ema_variance

        if self.observations > 1:
            same_direction = 1.0 if (delta * self._last_delta >= 0) else 0.0
            self.direction_consistency = (
                alpha * same_direction + (1.0 - alpha) * self.direction_consistency
            )
        self._last_delta = delta

    def to_dict(self) -> dict:
        return {
            "ema": round(self.ema, 6),
            "observations": self.observations,
            "last_contribution": round(self.last_contribution, 6),
            "ema_variance": round(self.ema_variance, 6),
            "direction_consistency": round(self.direction_consistency, 6),
        }


@dataclass(frozen=True)
class MetaWeightResult:
    """Immutable snapshot of adapted weights for a single turn."""

    adapted_weights: dict[str, float]
    adjustments: dict[str, float]
    signal_performance: dict[str, dict]
    observations: int
    adapted: bool

    def to_dict(self) -> dict:
        return {
            "adapted_weights": {
                k: round(v, 4) for k, v in self.adapted_weights.items()
            },
            "adjustments": {k: round(v, 4) for k, v in self.adjustments.items()},
            "signal_performance": self.signal_performance,
            "observations": self.observations,
            "adapted": self.adapted,
        }


NO_META_WEIGHT_RESULT = MetaWeightResult(
    adapted_weights={},
    adjustments={},
    signal_performance={},
    observations=0,
    adapted=False,
)


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def _normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    """Normalize weights to sum to 1.0. If total is zero, return uniform."""
    total = sum(weights.values())
    if total <= 0:
        n = len(weights)
        if n == 0:
            return {}
        uniform = 1.0 / n
        return {k: uniform for k in weights}
    return {k: v / total for k, v in weights.items()}


class MetaWeightEngine:
    """Deterministic weight adaptation engine.

    Tracks per-signal EMA of (signal_value * outcome_quality) and
    computes bounded, normalized adjustments to base influence weights.
    """

    def __init__(self) -> None:
        self._performance: dict[str, SignalPerformance] = {
            name: SignalPerformance() for name in SIGNAL_NAMES
        }

    @property
    def total_observations(self) -> int:
        if not self._performance:
            return 0
        return min(p.observations for p in self._performance.values())

    def record_outcome(
        self,
        signal_values: dict[str, float],
        outcome_quality: float,
    ) -> None:
        """Record signal contributions for a completed turn.

        signal_values: dict mapping signal name → signal value [0, 1]
        outcome_quality: quality score of the turn's outcome [0, 1]
        """
        quality = _clamp(outcome_quality, 0.0, 1.0)
        for name in SIGNAL_NAMES:
            raw = signal_values.get(name, 0.0)
            value = _clamp(raw, 0.0, 1.0)
            contribution = value * quality
            self._performance[name].update(contribution)

    def get_adapted_weights(
        self,
        base_weights: dict[str, float],
    ) -> MetaWeightResult:
        """Compute adapted weights from base weights + learned adjustments.

        Returns base weights unchanged until MIN_OBSERVATIONS are met.
        After that, adjustments are bounded by MAX_ADJUSTMENT per signal,
        floored by MIN_WEIGHT, and normalized to sum to 1.0.
        """
        if self.total_observations < MIN_OBSERVATIONS:
            return MetaWeightResult(
                adapted_weights=dict(base_weights),
                adjustments={name: 0.0 for name in SIGNAL_NAMES},
                signal_performance={
                    n: self._performance[n].to_dict() for n in SIGNAL_NAMES
                },
                observations=self.total_observations,
                adapted=False,
            )

        baselines = self._compute_baselines(base_weights)
        adjustments: dict[str, float] = {}
        raw_weights: dict[str, float] = {}
        signal_strength = self.compute_meta_signal_strength()

        for name in SIGNAL_NAMES:
            perf = self._performance[name]
            base = base_weights.get(name, 0.0)
            baseline = baselines.get(name, 0.0)
            adj = (perf.ema - baseline) * META_WEIGHT_SCALE
            adj *= 1.0 + META_SIGNAL_K * signal_strength
            adj = _clamp(adj, -MAX_ADJUSTMENT, MAX_ADJUSTMENT)
            adjustments[name] = adj
            raw_weights[name] = max(base + adj, MIN_WEIGHT)

        adapted = _normalize_weights(raw_weights)

        return MetaWeightResult(
            adapted_weights=adapted,
            adjustments=adjustments,
            signal_performance={
                n: self._performance[n].to_dict() for n in SIGNAL_NAMES
            },
            observations=self.total_observations,
            adapted=True,
        )

    def compute_meta_signal_strength(self) -> float:
        """Second-order signal strength from variance and consistency.

        Strong, consistent signals → higher strength → faster adaptation.
        Noisy or contradictory signals → near zero → damped.
        Returns [0, 1].
        """
        if self.total_observations < META_SIGNAL_MIN_OBS:
            return 0.0

        total_var = 0.0
        total_consistency = 0.0
        n = len(SIGNAL_NAMES)

        for name in SIGNAL_NAMES:
            perf = self._performance[name]
            total_var += perf.ema_variance
            total_consistency += perf.direction_consistency

        avg_var = total_var / max(n, 1)
        avg_consistency = total_consistency / max(n, 1)

        var_signal = _clamp(avg_var * 4.0, 0.0, 1.0)
        strength = var_signal * avg_consistency
        return _clamp(strength, 0.0, 1.0)

    def _compute_baselines(self, base_weights: dict[str, float]) -> dict[str, float]:
        """Baseline expected contribution per signal = 0.25.

        Neutral expectation: average signal (0.5) * average outcome (0.5) = 0.25.
        Weight-independent so uniform performance produces zero adjustment.
        """
        return {name: 0.25 for name in SIGNAL_NAMES}

    def snapshot(self) -> dict:
        """Serialize engine state for persistence."""
        return {
            name: {
                "ema": perf.ema,
                "observations": perf.observations,
                "last_contribution": perf.last_contribution,
                "ema_variance": perf.ema_variance,
                "direction_consistency": perf.direction_consistency,
                "_last_delta": perf._last_delta,
            }
            for name, perf in self._performance.items()
        }

    def restore(self, data: dict) -> None:
        """Restore engine state from snapshot. Backward compatible."""
        if not data or not isinstance(data, dict):
            return
        for name in SIGNAL_NAMES:
            entry = data.get(name)
            if entry and isinstance(entry, dict):
                perf = self._performance[name]
                perf.ema = float(entry.get("ema", 0.0))
                perf.observations = int(entry.get("observations", 0))
                perf.last_contribution = float(entry.get("last_contribution", 0.0))
                perf.ema_variance = float(entry.get("ema_variance", 0.0))
                perf.direction_consistency = float(
                    entry.get("direction_consistency", 0.0)
                )
                perf._last_delta = float(entry.get("_last_delta", 0.0))

    def reset(self) -> None:
        """Reset all signal performance trackers."""
        self._performance = {name: SignalPerformance() for name in SIGNAL_NAMES}


_engine: MetaWeightEngine | None = None


def get_meta_weight_engine() -> MetaWeightEngine:
    """Singleton accessor for the global MetaWeightEngine.

    On first access, attempts to restore from persisted state.
    Falls back cleanly to empty state if persistence is unavailable.
    """
    global _engine
    if _engine is None:
        _engine = MetaWeightEngine()
        try:
            from umh.persistence_layer.persistence import load_meta_weights

            data = load_meta_weights()
            if data is not None:
                _engine.restore(data)
        except Exception:
            pass
    return _engine
