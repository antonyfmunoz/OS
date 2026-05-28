"""Leverage Engine — determines highest-impact actions.

Answers: "What single action creates the largest improvement?"

Consumes:
  - active bottlenecks (from BottleneckEngine)
  - workload state (from WorkloadRunner)
  - pending approvals (from ApprovalStore)
  - active failures (from execution journal)
  - missing integrations (from deployment checks)
  - operator backlog (from OperatorCompression)

Outputs top-N leverage opportunities ranked by estimated impact,
each with confidence score and evidence trail.

Scoring is fully deterministic — no LLM dependency.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class LeverageEvidence:
    source: str
    signal: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "signal": self.signal,
            "detail": self.detail,
        }


@dataclass
class LeverageOpportunity:
    opportunity_id: str = field(default_factory=lambda: f"lev-{uuid4().hex[:8]}")
    action: str = ""
    impact_description: str = ""
    impact_score: float = 0.0
    confidence: float = 0.0
    category: str = ""
    evidence: list[LeverageEvidence] = field(default_factory=list)
    reasoning: str = ""
    detected_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "action": self.action,
            "impact_description": self.impact_description,
            "impact_score": round(self.impact_score, 3),
            "confidence": round(self.confidence, 3),
            "category": self.category,
            "evidence": [e.to_dict() for e in self.evidence],
            "reasoning": self.reasoning,
            "detected_at": self.detected_at,
        }


_SEVERITY_IMPACT = {
    "critical": 1.0,
    "high": 0.75,
    "medium": 0.5,
    "low": 0.25,
}

_CATEGORY_WEIGHTS = {
    "high_failure_rate": 0.95,
    "failing_reconciliation": 0.90,
    "governance_block": 0.85,
    "queue_buildup": 0.80,
    "approval_backlog": 0.75,
    "stalled_objective": 0.70,
    "retry_storm": 0.65,
    "deployment_mismatch": 0.60,
    "high_latency": 0.55,
    "repetitive_intervention": 0.50,
    "slow_runtime": 0.40,
    "missing_dependency": 0.35,
    "unused_runtime": 0.20,
    "overloaded_workcell": 0.70,
    "dead_chain": 0.65,
    "expensive_route": 0.45,
}


class LeverageEngine:
    """Ranks actions by operational leverage — what should you fix first?

    Deterministic scoring. Every opportunity traces back to observed
    system state via bottlenecks, workload metrics, approvals, and
    deployment checks.
    """

    def __init__(self, event_spine: Any | None = None) -> None:
        self._event_spine = event_spine
        self._opportunities: list[LeverageOpportunity] = []
        self._last_computed: float = 0.0

    def compute(
        self,
        bottlenecks: list[dict[str, Any]] | None = None,
        workload_state: dict[str, Any] | None = None,
        pending_approvals: int = 0,
        active_failures: list[dict[str, Any]] | None = None,
        execution_mode: dict[str, Any] | None = None,
        leverage_summary: dict[str, Any] | None = None,
    ) -> list[LeverageOpportunity]:
        opportunities: list[LeverageOpportunity] = []

        if bottlenecks:
            for bn in bottlenecks:
                opp = self._opportunity_from_bottleneck(bn)
                if opp is not None:
                    opportunities.append(opp)

        if pending_approvals > 0:
            opportunities.append(LeverageOpportunity(
                action=f"Process {pending_approvals} pending approvals",
                impact_description=f"Unblock {pending_approvals} queued actions waiting for operator review",
                impact_score=min(1.0, 0.3 + 0.05 * pending_approvals),
                confidence=1.0,
                category="approval_processing",
                evidence=[LeverageEvidence(
                    source="approval_store",
                    signal="pending_count",
                    detail=f"{pending_approvals} approvals awaiting review",
                )],
                reasoning=f"Each unprocessed approval blocks downstream execution. "
                          f"{pending_approvals} items create cumulative delay.",
            ))

        if active_failures:
            failure_count = len(active_failures)
            if failure_count > 0:
                top_failure = active_failures[0]
                opportunities.append(LeverageOpportunity(
                    action=f"Investigate {failure_count} active failure(s)",
                    impact_description="Resolve execution failures to restore throughput",
                    impact_score=min(1.0, 0.5 + 0.1 * failure_count),
                    confidence=0.85,
                    category="failure_resolution",
                    evidence=[LeverageEvidence(
                        source="execution_journal",
                        signal="active_failures",
                        detail=f"{failure_count} failures; most recent: {top_failure.get('intent', 'unknown')}",
                    )],
                    reasoning="Active failures consume retry budget and block dependent work. "
                              "Resolving root cause prevents recurrence.",
                ))

        if workload_state:
            success_rate = workload_state.get("success_rate", 1.0)
            if success_rate < 0.7:
                opportunities.append(LeverageOpportunity(
                    action="Improve workload success rate",
                    impact_description=f"Workload success rate at {success_rate:.0%} — below 70% target",
                    impact_score=0.7 * (1.0 - success_rate),
                    confidence=0.8,
                    category="workload_reliability",
                    evidence=[LeverageEvidence(
                        source="workload_runner",
                        signal="success_rate",
                        detail=f"Current: {success_rate:.1%}, target: >70%",
                    )],
                    reasoning="Low workload success rate reduces operator trust and increases "
                              "manual intervention. Improving it compounds autonomy.",
                ))

        if execution_mode:
            mode = execution_mode.get("current_mode", "")
            reliability = execution_mode.get("reliability", 1.0)
            if mode == "assisted" and reliability > 0.85:
                opportunities.append(LeverageOpportunity(
                    action="Promote execution mode from ASSISTED to AUTONOMOUS",
                    impact_description="Reliability supports autonomous mode — reduce operator friction",
                    impact_score=0.65,
                    confidence=min(1.0, reliability),
                    category="mode_promotion",
                    evidence=[LeverageEvidence(
                        source="execution_mode_manager",
                        signal="reliability",
                        detail=f"Current reliability {reliability:.1%} exceeds 85% threshold",
                    )],
                    reasoning="System has demonstrated sufficient reliability for autonomous execution. "
                              "Promotion removes approval overhead for low-risk actions.",
                ))

        if leverage_summary:
            dims = leverage_summary.get("dimensions", {})
            composite = dims.get("composite", 0)
            if composite < 0.3:
                weakest_dim = min(
                    ((k, v) for k, v in dims.items() if k != "composite"),
                    key=lambda x: x[1],
                    default=("unknown", 0),
                )
                opportunities.append(LeverageOpportunity(
                    action=f"Improve {weakest_dim[0].replace('_', ' ')}",
                    impact_description=f"Weakest leverage dimension at {weakest_dim[1]:.1%}",
                    impact_score=0.6 * (1.0 - weakest_dim[1]),
                    confidence=0.7,
                    category="leverage_improvement",
                    evidence=[LeverageEvidence(
                        source="leverage_metrics",
                        signal=f"dimensions.{weakest_dim[0]}",
                        detail=f"Score: {weakest_dim[1]:.3f}, composite: {composite:.3f}",
                    )],
                    reasoning=f"The {weakest_dim[0]} dimension drags the composite leverage score. "
                              f"Improving it from {weakest_dim[1]:.1%} has outsized impact on overall leverage.",
                ))

        opportunities.sort(key=lambda o: o.impact_score, reverse=True)

        previous = self._opportunities
        self._opportunities = opportunities
        self._last_computed = time.time()

        if self._event_spine is not None and opportunities != previous:
            from substrate.organism.event_spine import EventDomain
            self._event_spine.emit(
                EventDomain.LEVERAGE,
                "leverage_changed",
                "leverage_engine",
                {
                    "count": len(opportunities),
                    "top": opportunities[0].to_dict() if opportunities else None,
                },
            )

        return opportunities

    def _opportunity_from_bottleneck(self, bn: dict[str, Any]) -> LeverageOpportunity | None:
        category = bn.get("category", "")
        severity = bn.get("severity", "low")
        recommendation = bn.get("recommendation", bn.get("suggested_correction", ""))
        if not recommendation:
            return None

        category_weight = _CATEGORY_WEIGHTS.get(category, 0.5)
        severity_weight = _SEVERITY_IMPACT.get(severity, 0.25)
        recurrence = bn.get("recurrence_count", 1)
        recurrence_bonus = min(0.15, 0.03 * recurrence)

        impact = min(1.0, (0.5 * category_weight + 0.3 * severity_weight + 0.2 * recurrence_bonus))
        confidence = bn.get("confidence", 0.8)

        evidence_items = []
        for ev in bn.get("evidence", []):
            evidence_items.append(LeverageEvidence(
                source=bn.get("source", "bottleneck_engine"),
                signal=ev.get("signal", category),
                detail=f"observed={ev.get('observed', '?')}, expected={ev.get('expected', '?')}",
            ))
        if not evidence_items:
            evidence_items.append(LeverageEvidence(
                source=bn.get("source", "bottleneck_engine"),
                signal=category,
                detail=f"metric={bn.get('metric_value', 0)}, threshold={bn.get('threshold', 0)}",
            ))

        return LeverageOpportunity(
            action=recommendation,
            impact_description=bn.get("description", ""),
            impact_score=impact,
            confidence=confidence,
            category=f"bottleneck:{category}",
            evidence=evidence_items,
            reasoning=f"Bottleneck detected: {bn.get('description', '')}. "
                      f"Severity {severity}, recurrence {recurrence}x. "
                      f"Resolving this removes a {category.replace('_', ' ')} constraint.",
        )

    @property
    def opportunities(self) -> list[LeverageOpportunity]:
        return list(self._opportunities)

    def top(self, n: int = 5) -> list[dict[str, Any]]:
        return [o.to_dict() for o in self._opportunities[:n]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_opportunities": len(self._opportunities),
            "last_computed": self._last_computed,
            "top_opportunities": self.top(5),
        }
