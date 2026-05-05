"""Calibration — simulation vs reality comparison and weight adjustment.

Captures real execution outcomes, compares them to simulated predictions,
computes error metrics, and produces calibration adjustments. All data
is append-only — no destructive overwrites.

Pure computation — no I/O, no subprocess, no state mutation of execution.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from umh.core.clock import iso_now as _iso_now
from umh.runtime.simulation import SimulatedOutcome


@dataclass(frozen=True)
class ExecutionOutcome:
    """Immutable record of real execution results."""

    actual_completion_rate: float
    actual_latency: float
    actual_failure_rate: float
    actual_effort: float
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            object.__setattr__(self, "timestamp", _iso_now())

    def to_dict(self) -> dict[str, Any]:
        return {
            "actual_completion_rate": round(self.actual_completion_rate, 4),
            "actual_latency": round(self.actual_latency, 4),
            "actual_failure_rate": round(self.actual_failure_rate, 4),
            "actual_effort": round(self.actual_effort, 4),
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class CalibrationError:
    """Signed error between simulated and real metrics."""

    completion_error: float
    latency_error: float
    failure_error: float
    effort_error: float

    @property
    def total_error(self) -> float:
        return (
            abs(self.completion_error)
            + abs(self.latency_error)
            + abs(self.failure_error)
            + abs(self.effort_error)
        )

    @property
    def mean_absolute_error(self) -> float:
        return self.total_error / 4.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "completion_error": round(self.completion_error, 4),
            "latency_error": round(self.latency_error, 4),
            "failure_error": round(self.failure_error, 4),
            "effort_error": round(self.effort_error, 4),
            "total_error": round(self.total_error, 4),
            "mean_absolute_error": round(self.mean_absolute_error, 4),
        }


@dataclass(frozen=True)
class CalibrationRecord:
    """One predicted-vs-actual comparison. Immutable and append-only."""

    predicted_completion: float
    predicted_latency: float
    predicted_failure_risk: float
    predicted_effort: float
    actual_completion: float
    actual_latency: float
    actual_failure_rate: float
    actual_effort: float
    error: CalibrationError
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "predicted_completion": round(self.predicted_completion, 4),
            "predicted_latency": round(self.predicted_latency, 4),
            "predicted_failure_risk": round(self.predicted_failure_risk, 4),
            "predicted_effort": round(self.predicted_effort, 4),
            "actual_completion": round(self.actual_completion, 4),
            "actual_latency": round(self.actual_latency, 4),
            "actual_failure_rate": round(self.actual_failure_rate, 4),
            "actual_effort": round(self.actual_effort, 4),
            "error": self.error.to_dict(),
            "timestamp": self.timestamp,
        }


_MIN_FACTOR = 0.1
_MAX_FACTOR = 2.0
_LEARNING_RATE = 0.1


@dataclass(frozen=True)
class CalibrationFactors:
    """Multiplicative correction factors for simulation estimates."""

    completion_factor: float = 1.0
    latency_factor: float = 1.0
    failure_factor: float = 1.0
    effort_factor: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "completion_factor": round(self.completion_factor, 4),
            "latency_factor": round(self.latency_factor, 4),
            "failure_factor": round(self.failure_factor, 4),
            "effort_factor": round(self.effort_factor, 4),
        }


@dataclass(frozen=True)
class CalibrationAdjustment:
    """One explainable calibration adjustment."""

    metric: str
    direction: str
    magnitude: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "direction": self.direction,
            "magnitude": round(self.magnitude, 4),
            "reason": self.reason,
        }


class CalibrationEngine:
    """Compares simulated outcomes to real outcomes and computes error."""

    def compare(
        self,
        simulated: SimulatedOutcome,
        real: ExecutionOutcome,
    ) -> CalibrationError:
        """Compute signed error (predicted - actual) for each metric."""
        return CalibrationError(
            completion_error=simulated.expected_completion_rate - real.actual_completion_rate,
            latency_error=simulated.expected_latency - real.actual_latency,
            failure_error=simulated.expected_failure_risk - real.actual_failure_rate,
            effort_error=simulated.estimated_effort - real.actual_effort,
        )

    def build_record(
        self,
        simulated: SimulatedOutcome,
        real: ExecutionOutcome,
    ) -> CalibrationRecord:
        """Create an immutable calibration record from predicted and actual."""
        error = self.compare(simulated, real)
        return CalibrationRecord(
            predicted_completion=simulated.expected_completion_rate,
            predicted_latency=simulated.expected_latency,
            predicted_failure_risk=simulated.expected_failure_risk,
            predicted_effort=simulated.estimated_effort,
            actual_completion=real.actual_completion_rate,
            actual_latency=real.actual_latency,
            actual_failure_rate=real.actual_failure_rate,
            actual_effort=real.actual_effort,
            error=error,
            timestamp=real.timestamp,
        )


class CalibrationStore:
    """Append-only store for calibration records. Thread-safe."""

    def __init__(self, *, max_records: int = 500) -> None:
        self._lock = threading.Lock()
        self._records: list[CalibrationRecord] = []
        self._max_records = max(10, max_records)

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._records)

    def append(self, record: CalibrationRecord) -> None:
        """Append a calibration record. Evicts oldest if at capacity."""
        with self._lock:
            self._records.append(record)
            if len(self._records) > self._max_records:
                self._records = self._records[-self._max_records :]

    def list_records(self) -> list[CalibrationRecord]:
        with self._lock:
            return list(self._records)

    def recent(self, n: int = 10) -> list[CalibrationRecord]:
        with self._lock:
            return list(self._records[-n:])

    def mean_errors(self, n: int | None = None) -> CalibrationError | None:
        """Compute mean signed error across recent records."""
        with self._lock:
            records = self._records[-n:] if n else list(self._records)
        if not records:
            return None

        count = len(records)
        return CalibrationError(
            completion_error=sum(r.error.completion_error for r in records) / count,
            latency_error=sum(r.error.latency_error for r in records) / count,
            failure_error=sum(r.error.failure_error for r in records) / count,
            effort_error=sum(r.error.effort_error for r in records) / count,
        )

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            records = list(self._records)
        if not records:
            return {"total_records": 0, "mean_errors": None}
        count = len(records)
        mean = CalibrationError(
            completion_error=sum(r.error.completion_error for r in records) / count,
            latency_error=sum(r.error.latency_error for r in records) / count,
            failure_error=sum(r.error.failure_error for r in records) / count,
            effort_error=sum(r.error.effort_error for r in records) / count,
        )
        return {
            "total_records": count,
            "mean_errors": mean.to_dict(),
        }


class SimulationCalibrator:
    """Adjusts calibration factors based on accumulated error.

    Uses bounded multiplicative corrections: if simulation
    overestimates a metric, the corresponding factor is reduced.
    All adjustments are deterministic and inspectable.
    """

    def __init__(self, *, learning_rate: float = _LEARNING_RATE) -> None:
        self._learning_rate = max(0.01, min(0.5, learning_rate))

    @property
    def learning_rate(self) -> float:
        return self._learning_rate

    def calibrate(
        self,
        current: CalibrationFactors,
        mean_error: CalibrationError,
    ) -> tuple[CalibrationFactors, list[CalibrationAdjustment]]:
        """Compute adjusted factors from mean error. Deterministic."""
        adjustments: list[CalibrationAdjustment] = []

        cf = self._adjust_factor(
            current.completion_factor,
            mean_error.completion_error,
            "completion",
            adjustments,
        )
        lf = self._adjust_factor(
            current.latency_factor,
            mean_error.latency_error,
            "latency",
            adjustments,
        )
        ff = self._adjust_factor(
            current.failure_factor,
            -mean_error.failure_error,
            "failure",
            adjustments,
        )
        ef = self._adjust_factor(
            current.effort_factor,
            mean_error.effort_error,
            "effort",
            adjustments,
        )

        return CalibrationFactors(
            completion_factor=cf,
            latency_factor=lf,
            failure_factor=ff,
            effort_factor=ef,
        ), adjustments

    def _adjust_factor(
        self,
        current: float,
        error: float,
        metric: str,
        adjustments: list[CalibrationAdjustment],
    ) -> float:
        if abs(error) < 0.01:
            return current

        correction = -error * self._learning_rate
        new_factor = max(_MIN_FACTOR, min(_MAX_FACTOR, current + correction))
        delta = new_factor - current

        if abs(delta) > 0.001:
            direction = "increase" if delta > 0 else "decrease"
            if error > 0:
                reason = f"Simulation overestimates {metric} by {abs(error):.2f} — reducing factor"
            else:
                reason = (
                    f"Simulation underestimates {metric} by {abs(error):.2f} — increasing factor"
                )

            adjustments.append(
                CalibrationAdjustment(
                    metric=metric,
                    direction=direction,
                    magnitude=abs(delta),
                    reason=reason,
                )
            )

        return new_factor
