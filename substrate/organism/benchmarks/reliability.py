"""Reliability Benchmark — consistency across repeated builds.

Campaign 23B. Category R. Tier 2: Production Benchmark.
Measures success variance, failure frequency, recovery rate, and
consistency. Build the same thing N times, measure variance.
Low variance + high success = reliable.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ReliabilityTrial:
    trial_id: str = ""
    task_description: str = ""
    success: bool = False
    duration_seconds: float = 0.0
    defect_count: int = 0
    recovery_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReliabilityResult:
    trials_run: int = 0
    success_rate: float = 0.0
    success_variance: float = 0.0
    mean_duration: float = 0.0
    duration_variance: float = 0.0
    failure_frequency: float = 0.0
    recovery_success_rate: float = 0.0
    mean_defect_count: float = 0.0
    consistency_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _population_variance(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return sum((x - mean) ** 2 for x in values) / len(values)


class ReliabilityBenchmark:
    """Evaluates reliability from repeated trial records."""

    def evaluate(self, trials: list[ReliabilityTrial]) -> ReliabilityResult:
        if not trials:
            return ReliabilityResult()

        count = len(trials)
        successes = [1.0 if t.success else 0.0 for t in trials]
        durations = [t.duration_seconds for t in trials]
        defects = [t.defect_count for t in trials]
        recoveries = [t.recovery_count for t in trials]

        success_rate = sum(successes) / count
        success_var = _population_variance(successes)
        mean_dur = sum(durations) / count
        dur_var = _population_variance(durations)
        mean_defects = sum(defects) / count

        total_defects = sum(defects)
        total_recoveries = sum(recoveries)
        unrecovered = total_defects - total_recoveries
        recovery_rate = total_recoveries / (total_recoveries + max(unrecovered, 0)) if (total_recoveries + max(unrecovered, 0)) > 0 else 0.0

        if mean_dur > 0:
            consistency = max(0.0, 1.0 - (dur_var / mean_dur))
        else:
            consistency = 0.0
        consistency = min(consistency, 1.0)

        return ReliabilityResult(
            trials_run=count,
            success_rate=success_rate,
            success_variance=success_var,
            mean_duration=mean_dur,
            duration_variance=dur_var,
            failure_frequency=1.0 - success_rate,
            recovery_success_rate=recovery_rate,
            mean_defect_count=mean_defects,
            consistency_score=consistency,
        )
