"""Temporal weighting — time-aware decay for prediction pattern weights.

Applies exponential decay to weights based on time elapsed since last update.
Older patterns decay toward baseline (1.0). Recent patterns retain weight.

Decay formula:
  decayed = baseline + (weight - baseline) * exp(-decay_rate * age_hours)

Deterministic: same (weight, age) -> same result.

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

_DEFAULT_DECAY_RATE = 0.005
_DEFAULT_BASELINE = 1.0
_MIN_WEIGHT = 0.1
_MAX_WEIGHT = 3.0


@dataclass(frozen=True)
class DecayResult:
    """Result of applying temporal decay to a weight."""

    original_weight: float
    decayed_weight: float
    age_hours: float
    decay_factor: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_weight": round(self.original_weight, 4),
            "decayed_weight": round(self.decayed_weight, 4),
            "age_hours": round(self.age_hours, 2),
            "decay_factor": round(self.decay_factor, 4),
        }


class TemporalWeighter:
    """Applies time-based exponential decay to prediction weights.

    decay_rate controls how fast weights decay toward baseline:
      - 0.005 (default): ~50% decay at ~139 hours (~6 days)
      - Higher values = faster decay
      - 0 = no decay
    """

    def __init__(
        self,
        *,
        decay_rate: float = _DEFAULT_DECAY_RATE,
        baseline: float = _DEFAULT_BASELINE,
        min_weight: float = _MIN_WEIGHT,
        max_weight: float = _MAX_WEIGHT,
    ) -> None:
        if decay_rate < 0:
            raise ValueError("decay_rate must be >= 0")
        self._decay_rate = decay_rate
        self._baseline = baseline
        self._min_weight = min_weight
        self._max_weight = max_weight

    @property
    def decay_rate(self) -> float:
        return self._decay_rate

    @property
    def baseline(self) -> float:
        return self._baseline

    def apply_decay(
        self,
        weight: float,
        age_hours: float,
    ) -> DecayResult:
        """Apply exponential decay based on age in hours.

        The weight decays toward baseline, not toward zero.
        decayed = baseline + (weight - baseline) * exp(-rate * age)
        """
        if age_hours <= 0:
            clamped = max(self._min_weight, min(self._max_weight, weight))
            return DecayResult(
                original_weight=weight,
                decayed_weight=clamped,
                age_hours=0.0,
                decay_factor=1.0,
            )

        decay_factor = math.exp(-self._decay_rate * age_hours)
        decayed = self._baseline + (weight - self._baseline) * decay_factor

        clamped = max(self._min_weight, min(self._max_weight, decayed))

        return DecayResult(
            original_weight=weight,
            decayed_weight=clamped,
            age_hours=age_hours,
            decay_factor=decay_factor,
        )

    def compute_age_hours(
        self,
        last_updated: str,
        now: str,
    ) -> float:
        """Compute age in hours between two ISO timestamps.

        Returns 0.0 if parsing fails or timestamps are out of order.
        """
        from datetime import datetime, timezone

        try:
            t_last = datetime.fromisoformat(last_updated)
            t_now = datetime.fromisoformat(now)
            if t_last.tzinfo is None:
                t_last = t_last.replace(tzinfo=timezone.utc)
            if t_now.tzinfo is None:
                t_now = t_now.replace(tzinfo=timezone.utc)
            delta = (t_now - t_last).total_seconds()
            if delta < 0:
                return 0.0
            return delta / 3600.0
        except (ValueError, TypeError):
            return 0.0

    def get_state(self) -> dict[str, Any]:
        return {
            "decay_rate": self._decay_rate,
            "baseline": self._baseline,
            "min_weight": self._min_weight,
            "max_weight": self._max_weight,
        }
