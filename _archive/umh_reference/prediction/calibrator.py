"""Confidence calibrator — adjusts raw prediction confidence using observed accuracy.

Compares predicted confidence against actual success rates per source
and pattern, producing a calibrated confidence value. Also manages
adaptive threshold adjustment based on overall accuracy.

Pure computation on read-only inputs. Never mutates prediction records.

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from umh.prediction.weights import WeightStore


_DEFAULT_THRESHOLD = 0.6
_MIN_THRESHOLD = 0.4
_MAX_THRESHOLD = 0.9
_THRESHOLD_STEP = 0.02
_ACCURACY_LOW = 0.3
_ACCURACY_HIGH = 0.7
_MIN_CALIBRATED_CONFIDENCE = 0.01
_MAX_CALIBRATED_CONFIDENCE = 0.99
_MIN_SAMPLES_FOR_CALIBRATION = 3


@dataclass(frozen=True)
class CalibrationResult:
    """Result of confidence calibration."""

    raw_confidence: float
    pattern_weight: float
    calibrated_confidence: float
    pattern_key: str
    adjustments_applied: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_confidence": round(self.raw_confidence, 4),
            "pattern_weight": round(self.pattern_weight, 4),
            "calibrated_confidence": round(self.calibrated_confidence, 4),
            "pattern_key": self.pattern_key,
            "adjustments_applied": list(self.adjustments_applied),
        }


class ConfidenceCalibrator:
    """Adjusts prediction confidence using learned weights and accuracy history.

    Calibration formula:
      calibrated = raw_confidence * pattern_weight

    Clamped to [0.01, 0.99] — never produces 0.0 or 1.0
    (epistemic humility: no prediction is certain or impossible).
    """

    def __init__(self, weight_store: WeightStore | None = None) -> None:
        self._weight_store = weight_store or WeightStore()

    @property
    def weight_store(self) -> WeightStore:
        return self._weight_store

    def adjust_confidence(
        self,
        raw_confidence: float,
        pattern_key: str,
    ) -> CalibrationResult:
        """Apply calibration to a raw confidence score."""
        pw = self._weight_store.get_weight(pattern_key)
        weight = pw.weight
        adjustments: list[str] = []

        calibrated = raw_confidence * weight
        adjustments.append(f"weight_{weight:.3f}")

        if pw.total_predictions >= _MIN_SAMPLES_FOR_CALIBRATION:
            sr = pw.success_rate
            if sr < raw_confidence and pw.total_predictions >= _MIN_SAMPLES_FOR_CALIBRATION:
                correction = (sr + raw_confidence) / 2.0
                calibrated = min(calibrated, correction)
                adjustments.append(f"success_rate_correction_{sr:.3f}")

        calibrated = max(
            _MIN_CALIBRATED_CONFIDENCE,
            min(_MAX_CALIBRATED_CONFIDENCE, calibrated),
        )

        return CalibrationResult(
            raw_confidence=raw_confidence,
            pattern_weight=weight,
            calibrated_confidence=calibrated,
            pattern_key=pattern_key,
            adjustments_applied=tuple(adjustments),
        )


class ThresholdAdapter:
    """Dynamically adjusts the prediction confidence threshold.

    Adaptation rule:
      - accuracy < ACCURACY_LOW  → raise threshold (be more selective)
      - accuracy > ACCURACY_HIGH → lower threshold (allow more predictions)
      - otherwise → no change

    Threshold clamped to [MIN_THRESHOLD, MAX_THRESHOLD].
    Step size clamped to THRESHOLD_STEP per update.
    """

    def __init__(
        self,
        *,
        initial_threshold: float = _DEFAULT_THRESHOLD,
        min_threshold: float = _MIN_THRESHOLD,
        max_threshold: float = _MAX_THRESHOLD,
        step: float = _THRESHOLD_STEP,
        accuracy_low: float = _ACCURACY_LOW,
        accuracy_high: float = _ACCURACY_HIGH,
    ) -> None:
        self._threshold = max(min_threshold, min(max_threshold, initial_threshold))
        self._min = min_threshold
        self._max = max_threshold
        self._step = step
        self._accuracy_low = accuracy_low
        self._accuracy_high = accuracy_high
        self._update_count: int = 0

    @property
    def threshold(self) -> float:
        return self._threshold

    @property
    def update_count(self) -> int:
        return self._update_count

    def adapt(self, accuracy_rate: float) -> float:
        """Adjust threshold based on overall accuracy. Returns new threshold."""
        self._update_count += 1

        if accuracy_rate < self._accuracy_low:
            self._threshold = min(self._max, self._threshold + self._step)
        elif accuracy_rate > self._accuracy_high:
            self._threshold = max(self._min, self._threshold - self._step)

        return self._threshold

    def get_state(self) -> dict[str, Any]:
        return {
            "threshold": round(self._threshold, 4),
            "min": self._min,
            "max": self._max,
            "step": self._step,
            "update_count": self._update_count,
        }

    def reset(self) -> None:
        self._threshold = _DEFAULT_THRESHOLD
        self._update_count = 0
