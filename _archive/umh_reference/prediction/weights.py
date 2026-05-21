"""Prediction weights — adaptive pattern-level weighting for predictions.

Tracks per-pattern success rates and applies learned weights to
future prediction confidence. Weights are bounded and deterministic.

Update rule: exponential moving average (EMA) — naturally bounded,
converges rather than diverges.

Supports temporal decay via last_updated timestamp (Phase 23).

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from umh.core.clock import iso_now as _iso_now


_MIN_WEIGHT = 0.1
_MAX_WEIGHT = 3.0
_DEFAULT_WEIGHT = 1.0
_DEFAULT_LEARNING_RATE = 0.1
_MAX_DELTA = 0.3
_MIN_SAMPLES = 2


@dataclass
class PredictionWeight:
    """Adaptive weight for a prediction pattern."""

    pattern_key: str
    weight: float = _DEFAULT_WEIGHT
    success_count: int = 0
    failure_count: int = 0
    last_updated: str = ""

    @property
    def total_predictions(self) -> int:
        return self.success_count + self.failure_count

    @property
    def success_rate(self) -> float:
        total = self.total_predictions
        if total == 0:
            return 0.5
        return self.success_count / total

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_key": self.pattern_key,
            "weight": round(self.weight, 4),
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "total_predictions": self.total_predictions,
            "success_rate": round(self.success_rate, 4),
            "last_updated": self.last_updated,
        }


class WeightStore:
    """Stores and updates prediction weights per pattern key.

    Thread-safe. Deterministic: same sequence of updates produces
    same weights regardless of timing.
    """

    def __init__(
        self,
        *,
        learning_rate: float = _DEFAULT_LEARNING_RATE,
        min_weight: float = _MIN_WEIGHT,
        max_weight: float = _MAX_WEIGHT,
        max_delta: float = _MAX_DELTA,
    ) -> None:
        if not 0.0 < learning_rate <= 1.0:
            raise ValueError("learning_rate must be in (0.0, 1.0]")
        self._lock = threading.Lock()
        self._weights: dict[str, PredictionWeight] = {}
        self._learning_rate = learning_rate
        self._min_weight = min_weight
        self._max_weight = max_weight
        self._max_delta = max_delta

    @property
    def learning_rate(self) -> float:
        return self._learning_rate

    def get_weight(self, pattern_key: str) -> PredictionWeight:
        """Get weight for a pattern. Creates default if missing."""
        with self._lock:
            if pattern_key not in self._weights:
                self._weights[pattern_key] = PredictionWeight(
                    pattern_key=pattern_key
                )
            return self._weights[pattern_key]

    def get_weight_value(self, pattern_key: str) -> float:
        """Get the numeric weight for a pattern key."""
        return self.get_weight(pattern_key).weight

    def update_weight(self, pattern_key: str, *, matched: bool) -> float:
        """Update weight based on outcome. Returns new weight.

        Uses EMA: weight = weight + lr * (target - weight), clamped.
        matched=True targets max_weight, matched=False targets min_weight.
        Delta per update is clamped to max_delta.
        """
        with self._lock:
            if pattern_key not in self._weights:
                self._weights[pattern_key] = PredictionWeight(
                    pattern_key=pattern_key
                )

            pw = self._weights[pattern_key]

            if matched:
                pw.success_count += 1
            else:
                pw.failure_count += 1

            if pw.total_predictions < _MIN_SAMPLES:
                pw.last_updated = _iso_now()
                return pw.weight

            target = self._max_weight if matched else self._min_weight
            raw_delta = self._learning_rate * (target - pw.weight)

            clamped_delta = max(-self._max_delta, min(self._max_delta, raw_delta))

            new_weight = pw.weight + clamped_delta
            pw.weight = max(self._min_weight, min(self._max_weight, new_weight))
            pw.last_updated = _iso_now()

            return pw.weight

    def restore_weight(
        self,
        pattern_key: str,
        weight: float,
        success_count: int,
        failure_count: int,
        last_updated: str = "",
    ) -> None:
        """Restore a weight from persistence. Used during bootstrap rehydration."""
        clamped = max(self._min_weight, min(self._max_weight, weight))
        with self._lock:
            self._weights[pattern_key] = PredictionWeight(
                pattern_key=pattern_key,
                weight=clamped,
                success_count=max(0, success_count),
                failure_count=max(0, failure_count),
                last_updated=last_updated,
            )

    def list_weights(self) -> list[PredictionWeight]:
        with self._lock:
            return list(self._weights.values())

    def get_state(self) -> dict[str, Any]:
        with self._lock:
            return {
                "learning_rate": self._learning_rate,
                "min_weight": self._min_weight,
                "max_weight": self._max_weight,
                "max_delta": self._max_delta,
                "patterns": len(self._weights),
                "weights": {k: v.to_dict() for k, v in sorted(self._weights.items())},
            }

    def clear(self) -> None:
        with self._lock:
            self._weights.clear()
