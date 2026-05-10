"""
CalibrationEngine — self-tuning threshold layer for EOS.

Reads persisted session summaries (quality_score, confidence) and computes
distribution-based thresholds that replace hardcoded constants across
control_layer, adaptive_prompt, signal_router, and strategy_memory.

All computation is deterministic. No LLM calls. No randomness.
EMA smoothing prevents wild swings between recalibrations.

Disabled by default. Enable via ``CalibrationEngine(enabled=True)``.

Usage::

    from umh.reasoning.calibration import CalibrationEngine, CalibratedThresholds

    engine = CalibrationEngine(enabled=True)
    thresholds = engine.calibrate()

    # Consumers read thresholds instead of module-level constants:
    if score < thresholds.low_quality_threshold:
        ...
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass

_log = logging.getLogger(__name__)

MIN_SAMPLES = 10
DEFAULT_WINDOW = 100

EMA_ALPHA = 0.2

FLOOR_LOW_QUALITY = 0.25
CEILING_LOW_QUALITY = 0.60
FLOOR_HIGH_CONFIDENCE = 0.45
CEILING_HIGH_CONFIDENCE = 0.85
FLOOR_HALLUCINATION_CONFIDENCE = 0.25
CEILING_HALLUCINATION_CONFIDENCE = 0.55
FLOOR_BLOCK_CONFIDENCE = 0.10
CEILING_BLOCK_CONFIDENCE = 0.30
FLOOR_WORLD_MODEL_CONFIDENCE = 0.45
CEILING_WORLD_MODEL_CONFIDENCE = 0.80
FLOOR_MIN_CONFIDENCE = 0.40
CEILING_MIN_CONFIDENCE = 0.75

PERSISTENCE_KEY = "persistence:calibration_thresholds"


@dataclass
class CalibratedThresholds:
    """Current threshold values. Replaces hardcoded constants when calibration is active."""

    low_quality_threshold: float = 0.45
    high_confidence_threshold: float = 0.60
    hallucination_confidence_threshold: float = 0.40
    block_confidence_threshold: float = 0.20
    world_model_confidence_threshold: float = 0.60
    min_confidence: float = 0.60
    sample_count: int = 0
    calibrated: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> CalibratedThresholds:
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in known}
        return cls(**filtered)


DEFAULT_THRESHOLDS = CalibratedThresholds()


def _percentile(values: list[float], pct: float) -> float:
    """Compute percentile from sorted values. Linear interpolation."""
    if not values:
        return 0.0
    sorted_v = sorted(values)
    n = len(sorted_v)
    k = (pct / 100.0) * (n - 1)
    f = int(k)
    c = f + 1
    if c >= n:
        return sorted_v[-1]
    d = k - f
    return sorted_v[f] + d * (sorted_v[c] - sorted_v[f])


def _clamp(value: float, floor: float, ceiling: float) -> float:
    return max(floor, min(ceiling, value))


def _ema_smooth(computed: float, previous: float, alpha: float = EMA_ALPHA) -> float:
    return alpha * computed + (1.0 - alpha) * previous


class CalibrationEngine:
    """Self-tuning threshold engine. Disabled by default.

    When enabled, reads recent session summaries and computes thresholds
    from score/confidence distributions. EMA smoothing prevents jumps.
    All values are bounded by floor/ceiling constants.

    When disabled, ``calibrate()`` returns ``DEFAULT_THRESHOLDS``.
    """

    def __init__(
        self,
        enabled: bool = False,
        window: int = DEFAULT_WINDOW,
    ) -> None:
        self.enabled = enabled
        self.window = window
        self._previous: CalibratedThresholds | None = None
        self._recalibration_count: int = 0

        if enabled:
            self._load_persisted()

    def calibrate(
        self,
        summaries: list[dict] | None = None,
    ) -> CalibratedThresholds:
        """Compute thresholds from session summaries.

        If ``summaries`` is None, reads from the persistence layer.
        Falls back to defaults when insufficient data or disabled.
        """
        if not self.enabled:
            return DEFAULT_THRESHOLDS

        if summaries is None:
            summaries = self._load_summaries()

        windowed = summaries[-self.window :]

        quality_scores = [
            s["quality_score"]
            for s in windowed
            if isinstance(s.get("quality_score"), (int, float))
        ]
        confidences = [
            s["confidence"]
            for s in windowed
            if isinstance(s.get("confidence"), (int, float))
        ]

        if len(quality_scores) < MIN_SAMPLES or len(confidences) < MIN_SAMPLES:
            _log.debug(
                "Calibration: insufficient data (%d quality, %d confidence), using defaults",
                len(quality_scores),
                len(confidences),
            )
            return self._previous or DEFAULT_THRESHOLDS

        computed = self._compute_raw(quality_scores, confidences, len(windowed))

        if self._previous is not None:
            smoothed = self._smooth(computed, self._previous)
        else:
            smoothed = computed

        self._previous = smoothed
        self._recalibration_count += 1
        self._persist(smoothed)

        _log.info(
            "Calibration: recalibrated (n=%d, gen=%d) — "
            "low_quality=%.3f, high_conf=%.3f, halluc_conf=%.3f",
            smoothed.sample_count,
            self._recalibration_count,
            smoothed.low_quality_threshold,
            smoothed.high_confidence_threshold,
            smoothed.hallucination_confidence_threshold,
        )

        return smoothed

    @property
    def current(self) -> CalibratedThresholds:
        """Return the most recently computed thresholds, or defaults."""
        return self._previous or DEFAULT_THRESHOLDS

    @property
    def recalibration_count(self) -> int:
        return self._recalibration_count

    def _compute_raw(
        self,
        quality_scores: list[float],
        confidences: list[float],
        sample_count: int,
    ) -> CalibratedThresholds:
        """Compute raw thresholds from distributions before smoothing."""
        low_quality = _clamp(
            _percentile(quality_scores, 25),
            FLOOR_LOW_QUALITY,
            CEILING_LOW_QUALITY,
        )

        high_confidence = _clamp(
            _percentile(confidences, 75),
            FLOOR_HIGH_CONFIDENCE,
            CEILING_HIGH_CONFIDENCE,
        )

        halluc_conf = _clamp(
            _percentile(confidences, 25),
            FLOOR_HALLUCINATION_CONFIDENCE,
            CEILING_HALLUCINATION_CONFIDENCE,
        )

        block_conf = _clamp(
            _percentile(confidences, 10),
            FLOOR_BLOCK_CONFIDENCE,
            CEILING_BLOCK_CONFIDENCE,
        )

        wm_conf = _clamp(
            _percentile(confidences, 50),
            FLOOR_WORLD_MODEL_CONFIDENCE,
            CEILING_WORLD_MODEL_CONFIDENCE,
        )

        min_conf = _clamp(
            _percentile(confidences, 40),
            FLOOR_MIN_CONFIDENCE,
            CEILING_MIN_CONFIDENCE,
        )

        return CalibratedThresholds(
            low_quality_threshold=round(low_quality, 4),
            high_confidence_threshold=round(high_confidence, 4),
            hallucination_confidence_threshold=round(halluc_conf, 4),
            block_confidence_threshold=round(block_conf, 4),
            world_model_confidence_threshold=round(wm_conf, 4),
            min_confidence=round(min_conf, 4),
            sample_count=sample_count,
            calibrated=True,
        )

    def _smooth(
        self,
        computed: CalibratedThresholds,
        previous: CalibratedThresholds,
    ) -> CalibratedThresholds:
        """Apply EMA smoothing between computed and previous thresholds."""
        return CalibratedThresholds(
            low_quality_threshold=round(
                _ema_smooth(
                    computed.low_quality_threshold, previous.low_quality_threshold
                ),
                4,
            ),
            high_confidence_threshold=round(
                _ema_smooth(
                    computed.high_confidence_threshold,
                    previous.high_confidence_threshold,
                ),
                4,
            ),
            hallucination_confidence_threshold=round(
                _ema_smooth(
                    computed.hallucination_confidence_threshold,
                    previous.hallucination_confidence_threshold,
                ),
                4,
            ),
            block_confidence_threshold=round(
                _ema_smooth(
                    computed.block_confidence_threshold,
                    previous.block_confidence_threshold,
                ),
                4,
            ),
            world_model_confidence_threshold=round(
                _ema_smooth(
                    computed.world_model_confidence_threshold,
                    previous.world_model_confidence_threshold,
                ),
                4,
            ),
            min_confidence=round(
                _ema_smooth(computed.min_confidence, previous.min_confidence),
                4,
            ),
            sample_count=computed.sample_count,
            calibrated=True,
        )

    def _load_summaries(self) -> list[dict]:
        """Load recent session summaries from persistence."""
        try:
            from umh.persistence_layer.persistence import load_recent_summaries

            return load_recent_summaries(limit=self.window)
        except Exception as e:
            _log.debug("Calibration: failed to load summaries: %s", e)
            return []

    def _persist(self, thresholds: CalibratedThresholds) -> None:
        """Save calibrated thresholds for cross-restart continuity."""
        try:
            from umh.persistence_layer.persistence import _get_storage_safe

            storage = _get_storage_safe()
            if storage is not None:
                storage.put(PERSISTENCE_KEY, thresholds.to_dict())
        except Exception as e:
            _log.debug("Calibration: persist failed: %s", e)

    def _load_persisted(self) -> None:
        """Restore last calibrated thresholds on cold start."""
        try:
            from umh.persistence_layer.persistence import _get_storage_safe

            storage = _get_storage_safe()
            if storage is None:
                return
            data = storage.get(PERSISTENCE_KEY)
            if isinstance(data, dict) and data.get("calibrated"):
                self._previous = CalibratedThresholds.from_dict(data)
                _log.info(
                    "Calibration: restored persisted thresholds (n=%d)",
                    self._previous.sample_count,
                )
        except Exception as e:
            _log.debug("Calibration: restore failed: %s", e)


def get_thresholds(engine: CalibrationEngine | None = None) -> CalibratedThresholds:
    """Convenience accessor. Returns calibrated or default thresholds.

    When no engine is provided (calibration disabled), returns
    ``DEFAULT_THRESHOLDS`` — identical to the hardcoded constants.
    """
    if engine is None:
        return DEFAULT_THRESHOLDS
    return engine.current
