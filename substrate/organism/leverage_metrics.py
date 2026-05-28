"""Operational Leverage Metrics — measures actual organism value.

Tracks the concrete value the organism delivers:
  - operator time saved
  - execution throughput
  - automation completion rate
  - task latency and queue wait times
  - intervention and escalation frequency
  - autonomous resolution count

LeverageScore is a composite of six dimensions:
  1. time_compression       — how much faster vs manual
  2. cognitive_compression  — decisions automated
  3. operational_reliability — uptime, success rate
  4. execution_autonomy     — % tasks needing no human
  5. economic_efficiency    — cost per task
  6. failure_recovery_speed — MTTR

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TaskRecord:
    task_id: str
    started_at: float
    completed_at: float = 0.0
    autonomous: bool = True
    required_approval: bool = False
    required_intervention: bool = False
    success: bool = True
    retries: int = 0
    estimated_manual_seconds: float = 0.0
    actual_seconds: float = 0.0
    cost_usd: float = 0.0
    escalated: bool = False

    @property
    def duration_seconds(self) -> float:
        if self.completed_at <= 0:
            return 0.0
        return self.completed_at - self.started_at


@dataclass
class LeverageDimensions:
    time_compression: float = 0.0
    cognitive_compression: float = 0.0
    operational_reliability: float = 0.0
    execution_autonomy: float = 0.0
    economic_efficiency: float = 0.0
    failure_recovery_speed: float = 0.0

    @property
    def composite(self) -> float:
        return (
            0.25 * self.time_compression
            + 0.20 * self.cognitive_compression
            + 0.20 * self.operational_reliability
            + 0.15 * self.execution_autonomy
            + 0.10 * self.economic_efficiency
            + 0.10 * self.failure_recovery_speed
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "time_compression": round(self.time_compression, 4),
            "cognitive_compression": round(self.cognitive_compression, 4),
            "operational_reliability": round(self.operational_reliability, 4),
            "execution_autonomy": round(self.execution_autonomy, 4),
            "economic_efficiency": round(self.economic_efficiency, 4),
            "failure_recovery_speed": round(self.failure_recovery_speed, 4),
            "composite": round(self.composite, 4),
        }


_MAX_RECORDS = 5000
_WINDOW_SECONDS = 3600


class LeverageMetrics:
    """Measures actual operational leverage delivered by the organism.

    Records task executions and computes leverage dimensions from
    observed data. All metrics are derived from real task records,
    never synthetic.
    """

    def __init__(self, event_spine: Any | None = None) -> None:
        self._records: deque[TaskRecord] = deque(maxlen=_MAX_RECORDS)
        self._event_spine = event_spine
        self._total_operator_seconds_saved: float = 0.0
        self._total_autonomous_resolutions: int = 0
        self._total_interventions: int = 0
        self._total_escalations: int = 0
        self._total_approvals: int = 0
        self._total_tasks: int = 0
        self._total_failures: int = 0
        self._total_retries: int = 0
        self._total_cost_usd: float = 0.0
        self._failure_recovery_times: deque[float] = deque(maxlen=500)

    def record_task(self, record: TaskRecord) -> None:
        self._records.append(record)
        self._total_tasks += 1

        if record.success and record.autonomous and not record.required_intervention:
            self._total_autonomous_resolutions += 1

        if record.required_intervention:
            self._total_interventions += 1

        if record.escalated:
            self._total_escalations += 1

        if record.required_approval:
            self._total_approvals += 1

        if not record.success:
            self._total_failures += 1

        self._total_retries += record.retries
        self._total_cost_usd += record.cost_usd

        time_saved = record.estimated_manual_seconds - record.duration_seconds
        if time_saved > 0:
            self._total_operator_seconds_saved += time_saved

    def record_failure_recovery(self, recovery_seconds: float) -> None:
        self._failure_recovery_times.append(recovery_seconds)

    def compute_dimensions(self) -> LeverageDimensions:
        dims = LeverageDimensions()

        recent = self._recent_records()
        if not recent:
            return dims

        dims.time_compression = self._compute_time_compression(recent)
        dims.cognitive_compression = self._compute_cognitive_compression(recent)
        dims.operational_reliability = self._compute_reliability(recent)
        dims.execution_autonomy = self._compute_autonomy(recent)
        dims.economic_efficiency = self._compute_economic_efficiency(recent)
        dims.failure_recovery_speed = self._compute_recovery_speed()

        return dims

    def _recent_records(self) -> list[TaskRecord]:
        cutoff = time.time() - _WINDOW_SECONDS
        return [r for r in self._records if r.started_at >= cutoff]

    def _compute_time_compression(self, records: list[TaskRecord]) -> float:
        total_manual = sum(r.estimated_manual_seconds for r in records)
        total_actual = sum(r.duration_seconds for r in records)
        if total_manual <= 0:
            return 0.0
        ratio = 1.0 - (total_actual / total_manual)
        return max(0.0, min(1.0, ratio))

    def _compute_cognitive_compression(self, records: list[TaskRecord]) -> float:
        if not records:
            return 0.0
        autonomous_decisions = sum(1 for r in records if r.autonomous and not r.required_approval)
        return min(1.0, autonomous_decisions / len(records))

    def _compute_reliability(self, records: list[TaskRecord]) -> float:
        if not records:
            return 0.0
        successes = sum(1 for r in records if r.success)
        return successes / len(records)

    def _compute_autonomy(self, records: list[TaskRecord]) -> float:
        if not records:
            return 0.0
        fully_autonomous = sum(
            1 for r in records
            if r.autonomous and not r.required_intervention and not r.required_approval
        )
        return fully_autonomous / len(records)

    def _compute_economic_efficiency(self, records: list[TaskRecord]) -> float:
        total_cost = sum(r.cost_usd for r in records)
        total_value = sum(r.estimated_manual_seconds for r in records)
        if total_value <= 0:
            return 0.5
        cost_per_hour = (total_cost / (total_value / 3600)) if total_value > 0 else 0
        return max(0.0, min(1.0, 1.0 - (cost_per_hour / 50.0)))

    def _compute_recovery_speed(self) -> float:
        if not self._failure_recovery_times:
            return 0.5
        avg_recovery = sum(self._failure_recovery_times) / len(self._failure_recovery_times)
        return max(0.0, min(1.0, 1.0 - (avg_recovery / 600.0)))

    def summary(self) -> dict[str, Any]:
        dims = self.compute_dimensions()
        recent = self._recent_records()
        return {
            "dimensions": dims.to_dict(),
            "totals": {
                "tasks": self._total_tasks,
                "autonomous_resolutions": self._total_autonomous_resolutions,
                "interventions": self._total_interventions,
                "escalations": self._total_escalations,
                "approvals": self._total_approvals,
                "failures": self._total_failures,
                "retries": self._total_retries,
                "operator_seconds_saved": round(self._total_operator_seconds_saved, 1),
                "cost_usd": round(self._total_cost_usd, 4),
            },
            "recent_window": {
                "tasks": len(recent),
                "window_seconds": _WINDOW_SECONDS,
            },
        }

    def bottleneck_inputs(self) -> dict[str, float]:
        recent = self._recent_records()
        if not recent:
            return {
                "intervention_rate": 0.0,
                "escalation_rate": 0.0,
                "retry_rate": 0.0,
                "failure_rate": 0.0,
                "avg_latency_seconds": 0.0,
            }

        n = len(recent)
        return {
            "intervention_rate": sum(1 for r in recent if r.required_intervention) / n,
            "escalation_rate": sum(1 for r in recent if r.escalated) / n,
            "retry_rate": sum(r.retries for r in recent) / n,
            "failure_rate": sum(1 for r in recent if not r.success) / n,
            "avg_latency_seconds": (
                sum(r.duration_seconds for r in recent) / n if n > 0 else 0.0
            ),
        }

    def leverage_tick(self) -> dict[str, Any]:
        result = self.summary()
        if self._event_spine is not None:
            from substrate.organism.event_spine import EventDomain
            self._event_spine.emit(
                EventDomain.LEVERAGE,
                "leverage_measured",
                "leverage_metrics",
                result,
            )
        return result

    def to_dict(self) -> dict[str, Any]:
        return self.summary()
