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
  - approval backlogs
  - governance blocks
  - deployment mismatches

Emits bottleneck_detected / bottleneck_resolved events with severity,
confidence, evidence trail, and actionable recommendations.
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
from uuid import uuid4

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
    APPROVAL_BACKLOG = "approval_backlog"
    GOVERNANCE_BLOCK = "governance_block"
    DEPLOYMENT_MISMATCH = "deployment_mismatch"
    MISSING_DEPENDENCY = "missing_dependency"


@dataclass
class BottleneckEvidence:
    signal: str
    observed: str
    expected: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"signal": self.signal, "observed": self.observed}
        if self.expected:
            d["expected"] = self.expected
        return d


@dataclass
class Bottleneck:
    category: BottleneckCategory
    severity: BottleneckSeverity
    source: str
    description: str
    bottleneck_id: str = field(default_factory=lambda: f"bn-{uuid4().hex[:8]}")
    confidence: float = 1.0
    metric_value: float = 0.0
    threshold: float = 0.0
    evidence: list[BottleneckEvidence] = field(default_factory=list)
    recommendation: str = ""
    suggested_correction: str = ""
    detected_at: float = field(default_factory=time.time)
    recurrence_count: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "bottleneck_id": self.bottleneck_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "confidence": round(self.confidence, 3),
            "source": self.source,
            "description": self.description,
            "metric_value": round(self.metric_value, 4),
            "threshold": round(self.threshold, 4),
            "evidence": [e.to_dict() for e in self.evidence],
            "recommendation": self.recommendation or self.suggested_correction,
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
        pending_approvals: int = 0,
        governance_state: dict[str, Any] | None = None,
        deployment_state: dict[str, Any] | None = None,
    ) -> list[Bottleneck]:
        previous_ids = {b.bottleneck_id for b in self._active_bottlenecks}
        detected: list[Bottleneck] = []
        t = self._thresholds

        if leverage_inputs:
            fr = leverage_inputs.get("failure_rate", 0)
            if fr > t.failure_rate_max:
                overshoot = fr / t.failure_rate_max
                detected.append(Bottleneck(
                    category=BottleneckCategory.HIGH_FAILURE_RATE,
                    severity=BottleneckSeverity.HIGH,
                    source="leverage_metrics",
                    description="Task failure rate exceeds threshold",
                    confidence=min(1.0, 0.7 + 0.1 * overshoot),
                    metric_value=fr,
                    threshold=t.failure_rate_max,
                    evidence=[BottleneckEvidence(
                        signal="failure_rate",
                        observed=f"{fr:.1%}",
                        expected=f"<{t.failure_rate_max:.1%}",
                    )],
                    recommendation="Investigate failing tasks; check runtime health and error patterns",
                ))

            rr = leverage_inputs.get("retry_rate", 0)
            if rr > t.retry_rate_max:
                detected.append(Bottleneck(
                    category=BottleneckCategory.RETRY_STORM,
                    severity=BottleneckSeverity.MEDIUM,
                    source="leverage_metrics",
                    description="Excessive retries indicate unstable execution",
                    confidence=min(1.0, 0.6 + 0.15 * (rr / t.retry_rate_max)),
                    metric_value=rr,
                    threshold=t.retry_rate_max,
                    evidence=[BottleneckEvidence(
                        signal="retry_rate",
                        observed=f"{rr:.2f} retries/task",
                        expected=f"<{t.retry_rate_max:.2f}",
                    )],
                    recommendation="Check error patterns; consider circuit breaker on failing runtimes",
                ))

            ir = leverage_inputs.get("intervention_rate", 0)
            if ir > t.intervention_rate_max:
                detected.append(Bottleneck(
                    category=BottleneckCategory.REPETITIVE_INTERVENTION,
                    severity=BottleneckSeverity.MEDIUM,
                    source="leverage_metrics",
                    description="High operator intervention rate — automation gap",
                    confidence=min(1.0, 0.65 + 0.1 * (ir / t.intervention_rate_max)),
                    metric_value=ir,
                    threshold=t.intervention_rate_max,
                    evidence=[BottleneckEvidence(
                        signal="intervention_rate",
                        observed=f"{ir:.1%}",
                        expected=f"<{t.intervention_rate_max:.1%}",
                    )],
                    recommendation="Promote repeated interventions to automated policies",
                ))

            er = leverage_inputs.get("escalation_rate", 0)
            if er > t.escalation_rate_max:
                detected.append(Bottleneck(
                    category=BottleneckCategory.REPETITIVE_INTERVENTION,
                    severity=BottleneckSeverity.HIGH,
                    source="leverage_metrics",
                    description="High escalation rate — governance too restrictive or tasks misclassified",
                    confidence=min(1.0, 0.7 + 0.1 * (er / t.escalation_rate_max)),
                    metric_value=er,
                    threshold=t.escalation_rate_max,
                    evidence=[BottleneckEvidence(
                        signal="escalation_rate",
                        observed=f"{er:.1%}",
                        expected=f"<{t.escalation_rate_max:.1%}",
                    )],
                    recommendation="Review risk classification; tune governance thresholds",
                ))

            al = leverage_inputs.get("avg_latency_seconds", 0)
            if al > t.latency_max_seconds:
                detected.append(Bottleneck(
                    category=BottleneckCategory.HIGH_LATENCY,
                    severity=BottleneckSeverity.MEDIUM,
                    source="leverage_metrics",
                    description="Average task latency too high",
                    confidence=min(1.0, 0.6 + 0.1 * (al / t.latency_max_seconds)),
                    metric_value=al,
                    threshold=t.latency_max_seconds,
                    evidence=[BottleneckEvidence(
                        signal="avg_latency_seconds",
                        observed=f"{al:.1f}s",
                        expected=f"<{t.latency_max_seconds:.1f}s",
                    )],
                    recommendation="Profile slow tasks; check runtime selection and queue depth",
                ))

        if runtime_stats:
            for rt in runtime_stats:
                rid = rt.get("runtime_id", "unknown")
                avg_latency = rt.get("avg_latency_ms", 0)
                if avg_latency > t.slow_runtime_ms:
                    detected.append(Bottleneck(
                        category=BottleneckCategory.SLOW_RUNTIME,
                        severity=BottleneckSeverity.MEDIUM,
                        source=f"runtime:{rid}",
                        description=f"Runtime avg latency {avg_latency:.0f}ms exceeds {t.slow_runtime_ms:.0f}ms",
                        confidence=min(1.0, 0.7 + 0.05 * (avg_latency / t.slow_runtime_ms)),
                        metric_value=avg_latency,
                        threshold=t.slow_runtime_ms,
                        evidence=[BottleneckEvidence(
                            signal=f"runtime.{rid}.avg_latency_ms",
                            observed=f"{avg_latency:.0f}ms",
                            expected=f"<{t.slow_runtime_ms:.0f}ms",
                        )],
                        recommendation=f"Deprioritize {rid} in routing; investigate latency source",
                    ))

                idle_cycles = rt.get("idle_cycles", 0)
                if idle_cycles > t.idle_runtime_cycles:
                    detected.append(Bottleneck(
                        category=BottleneckCategory.UNUSED_RUNTIME,
                        severity=BottleneckSeverity.LOW,
                        source=f"runtime:{rid}",
                        description=f"Runtime idle for {idle_cycles} cycles",
                        confidence=0.8,
                        metric_value=idle_cycles,
                        threshold=t.idle_runtime_cycles,
                        evidence=[BottleneckEvidence(
                            signal=f"runtime.{rid}.idle_cycles",
                            observed=str(idle_cycles),
                            expected=f"<{t.idle_runtime_cycles}",
                        )],
                        recommendation=f"Consider removing or reconfiguring idle runtime {rid}",
                    ))

        if queue_depth > t.queue_depth_max:
            detected.append(Bottleneck(
                category=BottleneckCategory.QUEUE_BUILDUP,
                severity=BottleneckSeverity.HIGH,
                source="objective_queue",
                description=f"Queue depth {queue_depth} exceeds {t.queue_depth_max}",
                confidence=1.0,
                metric_value=queue_depth,
                threshold=t.queue_depth_max,
                evidence=[BottleneckEvidence(
                    signal="objective_queue.depth",
                    observed=str(queue_depth),
                    expected=f"<{t.queue_depth_max}",
                )],
                recommendation="Scale execution capacity or prioritize queue",
            ))

        if stalled_objectives:
            now = time.time()
            for obj in stalled_objectives:
                stalled_seconds = now - obj.get("last_progress_at", now)
                if stalled_seconds > t.stall_seconds:
                    oid = obj.get("objective_id", "unknown")
                    detected.append(Bottleneck(
                        category=BottleneckCategory.STALLED_OBJECTIVE,
                        severity=BottleneckSeverity.HIGH,
                        source=f"objective:{oid}",
                        description=f"Objective stalled for {stalled_seconds:.0f}s",
                        confidence=min(1.0, 0.7 + 0.1 * (stalled_seconds / t.stall_seconds)),
                        metric_value=stalled_seconds,
                        threshold=t.stall_seconds,
                        evidence=[BottleneckEvidence(
                            signal=f"objective.{oid}.stall_seconds",
                            observed=f"{stalled_seconds:.0f}s",
                            expected=f"<{t.stall_seconds:.0f}s",
                        )],
                        recommendation="Check blocked dependencies; reassign or decompose objective",
                    ))

        if tick_metrics:
            fail_count = tick_metrics.get("total_stages_failed", 0)
            total = tick_metrics.get("total_stages_executed", 0)
            if total > 0 and fail_count / total > 0.3:
                rate = fail_count / total
                detected.append(Bottleneck(
                    category=BottleneckCategory.FAILING_RECONCILIATION,
                    severity=BottleneckSeverity.HIGH,
                    source="tick_engine",
                    description=f"Tick stage failure rate {fail_count}/{total}",
                    confidence=min(1.0, 0.7 + 0.1 * (rate / 0.3)),
                    metric_value=rate,
                    threshold=0.3,
                    evidence=[BottleneckEvidence(
                        signal="tick_engine.stage_failure_rate",
                        observed=f"{rate:.1%} ({fail_count}/{total})",
                        expected="<30%",
                    )],
                    recommendation="Investigate failing tick stages; check subsystem health",
                ))

        if pending_approvals > t.queue_depth_max // 2:
            detected.append(Bottleneck(
                category=BottleneckCategory.APPROVAL_BACKLOG,
                severity=BottleneckSeverity.MEDIUM if pending_approvals < t.queue_depth_max else BottleneckSeverity.HIGH,
                source="approval_store",
                description=f"{pending_approvals} approvals pending operator review",
                confidence=1.0,
                metric_value=pending_approvals,
                threshold=t.queue_depth_max // 2,
                evidence=[BottleneckEvidence(
                    signal="approval_store.pending_count",
                    observed=str(pending_approvals),
                    expected=f"<{t.queue_depth_max // 2}",
                )],
                recommendation="Review and process pending approvals; consider promoting safe actions to autonomous",
            ))

        if governance_state:
            blocked = governance_state.get("total_blocked", 0)
            submitted = governance_state.get("total_submitted", 0)
            if submitted > 5 and blocked / submitted > 0.5:
                detected.append(Bottleneck(
                    category=BottleneckCategory.GOVERNANCE_BLOCK,
                    severity=BottleneckSeverity.HIGH,
                    source="governance",
                    description=f"Governance blocking {blocked}/{submitted} submissions ({blocked/submitted:.0%})",
                    confidence=min(1.0, 0.75 + 0.05 * (blocked / max(submitted, 1))),
                    metric_value=blocked / submitted,
                    threshold=0.5,
                    evidence=[BottleneckEvidence(
                        signal="governance.block_rate",
                        observed=f"{blocked}/{submitted} blocked",
                        expected="<50% block rate",
                    )],
                    recommendation="Review governance policies; tune risk classification for over-blocked action types",
                ))

        if deployment_state:
            for check in deployment_state.get("checks", []):
                if not check.get("pass", True):
                    detected.append(Bottleneck(
                        category=BottleneckCategory.DEPLOYMENT_MISMATCH,
                        severity=BottleneckSeverity(check.get("severity", "medium")),
                        source=f"deployment:{check.get('name', 'unknown')}",
                        description=check.get("description", "Deployment check failed"),
                        confidence=check.get("confidence", 0.9),
                        evidence=[BottleneckEvidence(
                            signal=check.get("signal", "deployment_check"),
                            observed=check.get("observed", "failed"),
                            expected=check.get("expected", "pass"),
                        )],
                        recommendation=check.get("recommendation", "Investigate deployment state"),
                    ))

        for b in detected:
            key = f"{b.category.value}:{b.source}"
            self._recurrence_tracker[key] = self._recurrence_tracker.get(key, 0) + 1
            b.recurrence_count = self._recurrence_tracker[key]
            if b.recurrence_count > 5:
                b.severity = BottleneckSeverity.CRITICAL
                b.confidence = min(1.0, b.confidence + 0.1)

        resolved_keys = previous_ids - {b.bottleneck_id for b in detected}
        self._active_bottlenecks = detected
        for b in detected:
            self._history.append(b)

        if self._event_spine is not None:
            from substrate.organism.event_spine import EventDomain, EventPriority
            if detected:
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
            if resolved_keys:
                self._event_spine.emit(
                    EventDomain.OBSERVABILITY,
                    "bottleneck_resolved",
                    "bottleneck_engine",
                    {"resolved_count": len(resolved_keys)},
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
