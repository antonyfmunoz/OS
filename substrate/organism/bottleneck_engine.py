"""Bottleneck Detection Engine — organism operational self-optimization.

Detects what actually slows execution:
  - slow runtimes
  - overloaded workcells
  - stalled objectives
  - queue buildup
  - failed retries
  - dead execution chains
  - expensive routing paths
  - unused runtimes
  - repetitive operator interventions
  - failing reconciliations

Emits bottleneck_detected events with severity and corrections.
Tracks recurrence to identify systemic issues vs transient spikes.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class BottleneckSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BottleneckCategory(str, Enum):
    SLOW_RUNTIME = "slow_runtime"
    OVERLOADED_WORKCELL = "overloaded_workcell"
    STALLED_OBJECTIVE = "stalled_objective"
    QUEUE_BUILDUP = "queue_buildup"
    RETRY_STORM = "retry_storm"
    DEAD_CHAIN = "dead_chain"
    EXPENSIVE_ROUTE = "expensive_route"
    UNUSED_RUNTIME = "unused_runtime"
    REPETITIVE_INTERVENTION = "repetitive_intervention"
    FAILING_RECONCILIATION = "failing_reconciliation"
    HIGH_LATENCY = "high_latency"
    HIGH_FAILURE_RATE = "high_failure_rate"


@dataclass
class Bottleneck:
    category: BottleneckCategory
    severity: BottleneckSeverity
    source: str
    description: str
    metric_value: float = 0.0
    threshold: float = 0.0
    suggested_correction: str = ""
    detected_at: float = field(default_factory=time.time)
    recurrence_count: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "source": self.source,
            "description": self.description,
            "metric_value": round(self.metric_value, 4),
            "threshold": round(self.threshold, 4),
            "suggested_correction": self.suggested_correction,
            "detected_at": self.detected_at,
            "recurrence_count": self.recurrence_count,
        }


@dataclass
class BottleneckThresholds:
    slow_runtime_ms: float = 5000.0
    queue_depth_max: int = 50
    retry_rate_max: float = 0.3
    failure_rate_max: float = 0.2
    intervention_rate_max: float = 0.4
    escalation_rate_max: float = 0.2
    stall_seconds: float = 300.0
    latency_max_seconds: float = 60.0
    idle_runtime_cycles: int = 10


_MAX_HISTORY = 500
_RECURRENCE_WINDOW_SECONDS = 3600


class BottleneckEngine:
    """Detects operational bottlenecks from organism state.

    Consumes metrics from LeverageMetrics, RuntimeGraph, and
    AutonomousTick. Emits bottleneck_detected events through
    the EventSpine. Tracks recurrence patterns.
    """

    def __init__(
        self,
        event_spine: Any | None = None,
        thresholds: BottleneckThresholds | None = None,
    ) -> None:
        self._event_spine = event_spine
        self._thresholds = thresholds or BottleneckThresholds()
        self._active_bottlenecks: list[Bottleneck] = []
        self._history: deque[Bottleneck] = deque(maxlen=_MAX_HISTORY)
        self._recurrence_tracker: dict[str, int] = {}

    def detect(
        self,
        leverage_inputs: dict[str, float] | None = None,
        runtime_stats: list[dict[str, Any]] | None = None,
        tick_metrics: dict[str, Any] | None = None,
        queue_depth: int = 0,
        stalled_objectives: list[dict[str, Any]] | None = None,
    ) -> list[Bottleneck]:
        detected: list[Bottleneck] = []
        t = self._thresholds

        if leverage_inputs:
            if leverage_inputs.get("failure_rate", 0) > t.failure_rate_max:
                detected.append(Bottleneck(
                    category=BottleneckCategory.HIGH_FAILURE_RATE,
                    severity=BottleneckSeverity.HIGH,
                    source="leverage_metrics",
                    description="Task failure rate exceeds threshold",
                    metric_value=leverage_inputs["failure_rate"],
                    threshold=t.failure_rate_max,
                    suggested_correction="Investigate failing tasks; check runtime health",
                ))

            if leverage_inputs.get("retry_rate", 0) > t.retry_rate_max:
                detected.append(Bottleneck(
                    category=BottleneckCategory.RETRY_STORM,
                    severity=BottleneckSeverity.MEDIUM,
                    source="leverage_metrics",
                    description="Excessive retries indicate unstable execution",
                    metric_value=leverage_inputs["retry_rate"],
                    threshold=t.retry_rate_max,
                    suggested_correction="Check error patterns; consider circuit breaker",
                ))

            if leverage_inputs.get("intervention_rate", 0) > t.intervention_rate_max:
                detected.append(Bottleneck(
                    category=BottleneckCategory.REPETITIVE_INTERVENTION,
                    severity=BottleneckSeverity.MEDIUM,
                    source="leverage_metrics",
                    description="High operator intervention rate — automation gap",
                    metric_value=leverage_inputs["intervention_rate"],
                    threshold=t.intervention_rate_max,
                    suggested_correction="Promote repeated interventions to automated policies",
                ))

            if leverage_inputs.get("escalation_rate", 0) > t.escalation_rate_max:
                detected.append(Bottleneck(
                    category=BottleneckCategory.REPETITIVE_INTERVENTION,
                    severity=BottleneckSeverity.HIGH,
                    source="leverage_metrics",
                    description="High escalation rate — governance too restrictive or tasks misclassified",
                    metric_value=leverage_inputs["escalation_rate"],
                    threshold=t.escalation_rate_max,
                    suggested_correction="Review risk classification; tune governance thresholds",
                ))

            if leverage_inputs.get("avg_latency_seconds", 0) > t.latency_max_seconds:
                detected.append(Bottleneck(
                    category=BottleneckCategory.HIGH_LATENCY,
                    severity=BottleneckSeverity.MEDIUM,
                    source="leverage_metrics",
                    description="Average task latency too high",
                    metric_value=leverage_inputs["avg_latency_seconds"],
                    threshold=t.latency_max_seconds,
                    suggested_correction="Profile slow tasks; check runtime selection",
                ))

        if runtime_stats:
            for rt in runtime_stats:
                avg_latency = rt.get("avg_latency_ms", 0)
                if avg_latency > t.slow_runtime_ms:
                    detected.append(Bottleneck(
                        category=BottleneckCategory.SLOW_RUNTIME,
                        severity=BottleneckSeverity.MEDIUM,
                        source=f"runtime:{rt.get('runtime_id', 'unknown')}",
                        description=f"Runtime avg latency {avg_latency:.0f}ms exceeds {t.slow_runtime_ms:.0f}ms",
                        metric_value=avg_latency,
                        threshold=t.slow_runtime_ms,
                        suggested_correction="Deprioritize slow runtime in routing",
                    ))

                idle_cycles = rt.get("idle_cycles", 0)
                if idle_cycles > t.idle_runtime_cycles:
                    detected.append(Bottleneck(
                        category=BottleneckCategory.UNUSED_RUNTIME,
                        severity=BottleneckSeverity.LOW,
                        source=f"runtime:{rt.get('runtime_id', 'unknown')}",
                        description=f"Runtime idle for {idle_cycles} cycles",
                        metric_value=idle_cycles,
                        threshold=t.idle_runtime_cycles,
                        suggested_correction="Consider removing or reconfiguring idle runtime",
                    ))

        if queue_depth > t.queue_depth_max:
            detected.append(Bottleneck(
                category=BottleneckCategory.QUEUE_BUILDUP,
                severity=BottleneckSeverity.HIGH,
                source="objective_queue",
                description=f"Queue depth {queue_depth} exceeds {t.queue_depth_max}",
                metric_value=queue_depth,
                threshold=t.queue_depth_max,
                suggested_correction="Scale execution capacity or prioritize queue",
            ))

        if stalled_objectives:
            now = time.time()
            for obj in stalled_objectives:
                stalled_seconds = now - obj.get("last_progress_at", now)
                if stalled_seconds > t.stall_seconds:
                    detected.append(Bottleneck(
                        category=BottleneckCategory.STALLED_OBJECTIVE,
                        severity=BottleneckSeverity.HIGH,
                        source=f"objective:{obj.get('objective_id', 'unknown')}",
                        description=f"Objective stalled for {stalled_seconds:.0f}s",
                        metric_value=stalled_seconds,
                        threshold=t.stall_seconds,
                        suggested_correction="Check blocked dependencies; reassign or decompose",
                    ))

        if tick_metrics:
            fail_rate = tick_metrics.get("total_stages_failed", 0)
            total = tick_metrics.get("total_stages_executed", 0)
            if total > 0 and fail_rate / total > 0.3:
                detected.append(Bottleneck(
                    category=BottleneckCategory.FAILING_RECONCILIATION,
                    severity=BottleneckSeverity.HIGH,
                    source="tick_engine",
                    description=f"Tick stage failure rate {fail_rate}/{total}",
                    metric_value=fail_rate / total,
                    threshold=0.3,
                    suggested_correction="Investigate failing tick stages",
                ))

        for b in detected:
            key = f"{b.category.value}:{b.source}"
            self._recurrence_tracker[key] = self._recurrence_tracker.get(key, 0) + 1
            b.recurrence_count = self._recurrence_tracker[key]
            if b.recurrence_count > 5:
                b.severity = BottleneckSeverity.CRITICAL

        self._active_bottlenecks = detected
        for b in detected:
            self._history.append(b)

        if detected and self._event_spine is not None:
            from substrate.organism.event_spine import EventDomain, EventPriority
            self._event_spine.emit(
                EventDomain.OBSERVABILITY,
                "bottleneck_detected",
                "bottleneck_engine",
                {
                    "count": len(detected),
                    "bottlenecks": [b.to_dict() for b in detected[:10]],
                    "critical": sum(1 for b in detected if b.severity == BottleneckSeverity.CRITICAL),
                },
                priority=EventPriority.HIGH if any(
                    b.severity in (BottleneckSeverity.HIGH, BottleneckSeverity.CRITICAL)
                    for b in detected
                ) else EventPriority.NORMAL,
            )

        return detected

    @property
    def active(self) -> list[Bottleneck]:
        return list(self._active_bottlenecks)

    def recurrence_report(self) -> dict[str, int]:
        return dict(
            sorted(self._recurrence_tracker.items(), key=lambda x: x[1], reverse=True)
        )

    def clear_recurrence(self, key: str) -> None:
        self._recurrence_tracker.pop(key, None)

    def history(self, limit: int = 50) -> list[dict[str, Any]]:
        items = list(self._history)
        return [b.to_dict() for b in items[-limit:]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_count": len(self._active_bottlenecks),
            "active": [b.to_dict() for b in self._active_bottlenecks],
            "history_size": len(self._history),
            "recurrence_top": dict(
                sorted(self._recurrence_tracker.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
            "by_severity": self._count_by_severity(),
            "by_category": self._count_by_category(),
        }

    def _count_by_severity(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for b in self._active_bottlenecks:
            counts[b.severity.value] = counts.get(b.severity.value, 0) + 1
        return counts

    def _count_by_category(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for b in self._active_bottlenecks:
            counts[b.category.value] = counts.get(b.category.value, 0) + 1
        return counts
