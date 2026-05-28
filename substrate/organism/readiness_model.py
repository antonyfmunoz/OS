"""System Readiness Model — 6-dimension readiness assessment.

Dimensions (0-100 each):
  1. Execution   — can the organism execute tasks reliably?
  2. Governance  — are safety rails active and calibrated?
  3. Deployment  — is the deployed state healthy and current?
  4. Operator    — is the operator loop functioning?
  5. Memory      — is knowledge/state persisted and queryable?
  6. Composition — are subsystems composed and communicating?

Weights are explicit and documented:
  Execution:   0.25 — core value delivery
  Governance:  0.20 — safety prerequisite
  Deployment:  0.20 — must be serving correctly
  Operator:    0.15 — human-in-loop health
  Memory:      0.10 — knowledge persistence
  Composition: 0.10 — subsystem integration

Each score is derived from observable signals with named factors.
No arbitrary numbers — every weight is justified by the organism's
operational priority hierarchy.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


DIMENSION_WEIGHTS: dict[str, float] = {
    "execution": 0.25,
    "governance": 0.20,
    "deployment": 0.20,
    "operator": 0.15,
    "memory": 0.10,
    "composition": 0.10,
}


@dataclass
class DimensionScore:
    dimension: str
    score: float = 0.0
    factors: dict[str, float] = field(default_factory=dict)
    gap_factors: list[str] = field(default_factory=list)
    explanation: str = ""
    weight: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "score": round(self.score, 1),
            "weight": self.weight,
            "weighted_contribution": round(self.score * self.weight, 2),
            "factors": {k: round(v, 3) for k, v in self.factors.items()},
            "gap_factors": self.gap_factors,
            "explanation": self.explanation,
        }


@dataclass
class ReadinessReport:
    composite_score: float = 0.0
    dimensions: list[DimensionScore] = field(default_factory=list)
    computed_at: float = field(default_factory=time.time)
    overall_status: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "composite_score": round(self.composite_score, 1),
            "overall_status": self.overall_status,
            "dimensions": {d.dimension: d.to_dict() for d in self.dimensions},
            "computed_at": self.computed_at,
            "weight_documentation": dict(DIMENSION_WEIGHTS),
        }

    def gaps(self, threshold: float = 60.0) -> list[dict[str, Any]]:
        return [
            d.to_dict()
            for d in sorted(self.dimensions, key=lambda x: x.score)
            if d.score < threshold
        ]


class ReadinessModel:
    """Computes system readiness from observed organism state.

    All scores are 0-100. Each dimension aggregates measurable factors
    weighted equally within the dimension. The composite uses explicit
    cross-dimension weights from DIMENSION_WEIGHTS.
    """

    def __init__(self, event_spine: Any | None = None) -> None:
        self._event_spine = event_spine
        self._last_report: ReadinessReport | None = None

    def compute(
        self,
        execution_state: dict[str, Any] | None = None,
        governance_state: dict[str, Any] | None = None,
        deployment_state: dict[str, Any] | None = None,
        operator_state: dict[str, Any] | None = None,
        memory_state: dict[str, Any] | None = None,
        composition_state: dict[str, Any] | None = None,
    ) -> ReadinessReport:
        dims = [
            self._score_execution(execution_state or {}),
            self._score_governance(governance_state or {}),
            self._score_deployment(deployment_state or {}),
            self._score_operator(operator_state or {}),
            self._score_memory(memory_state or {}),
            self._score_composition(composition_state or {}),
        ]

        composite = sum(d.score * d.weight for d in dims)

        report = ReadinessReport(
            composite_score=composite,
            dimensions=dims,
            overall_status=self._status_label(composite),
        )

        prev_composite = self._last_report.composite_score if self._last_report else 0
        self._last_report = report

        if self._event_spine is not None and abs(composite - prev_composite) > 5.0:
            from substrate.organism.event_spine import EventDomain
            self._event_spine.emit(
                EventDomain.OBSERVABILITY,
                "readiness_changed",
                "readiness_model",
                {
                    "composite": round(composite, 1),
                    "status": report.overall_status,
                    "delta": round(composite - prev_composite, 1),
                },
            )

        return report

    def _score_execution(self, state: dict[str, Any]) -> DimensionScore:
        factors: dict[str, float] = {}
        gaps: list[str] = []

        success_rate = state.get("success_rate", 0.0)
        factors["success_rate"] = success_rate * 100

        spine_registered = state.get("registered_mutations", 0)
        factors["mutation_registry"] = min(100, spine_registered * 5)

        mode = state.get("current_mode", "manual")
        mode_scores = {"autonomous": 100, "supervised": 75, "assisted": 50, "manual": 25}
        factors["execution_mode"] = mode_scores.get(mode, 25)

        pending = state.get("pending_count", 0)
        factors["queue_health"] = max(0, 100 - pending * 5)

        active = state.get("active_count", 0)
        factors["active_throughput"] = min(100, active * 20) if active > 0 else 30

        score = sum(factors.values()) / max(len(factors), 1)

        for name, val in factors.items():
            if val < 50:
                gaps.append(name)

        return DimensionScore(
            dimension="execution",
            score=score,
            weight=DIMENSION_WEIGHTS["execution"],
            factors=factors,
            gap_factors=gaps,
            explanation=self._explain_execution(factors, score),
        )

    def _score_governance(self, state: dict[str, Any]) -> DimensionScore:
        factors: dict[str, float] = {}
        gaps: list[str] = []

        guard_active = state.get("guard_active", False)
        factors["spine_guard"] = 100 if guard_active else 0

        gateway_active = state.get("gateway_active", False)
        factors["autonomous_gateway"] = 100 if gateway_active else 0

        total_submitted = state.get("total_submitted", 0)
        total_blocked = state.get("total_blocked", 0)
        if total_submitted > 0:
            block_rate = total_blocked / total_submitted
            factors["governance_calibration"] = max(0, 100 - abs(block_rate - 0.2) * 200)
        else:
            factors["governance_calibration"] = 50

        violations = state.get("total_violations", 0)
        factors["violation_rate"] = max(0, 100 - violations * 10)

        journal_active = state.get("journal_active", False)
        factors["audit_trail"] = 100 if journal_active else 0

        score = sum(factors.values()) / max(len(factors), 1)
        for name, val in factors.items():
            if val < 50:
                gaps.append(name)

        return DimensionScore(
            dimension="governance",
            score=score,
            weight=DIMENSION_WEIGHTS["governance"],
            factors=factors,
            gap_factors=gaps,
            explanation=self._explain_governance(factors, score),
        )

    def _score_deployment(self, state: dict[str, Any]) -> DimensionScore:
        factors: dict[str, float] = {}
        gaps: list[str] = []

        services_up = state.get("services_up", 0)
        services_total = state.get("services_total", 1)
        factors["service_health"] = (services_up / max(services_total, 1)) * 100

        build_current = state.get("build_current", False)
        factors["build_freshness"] = 100 if build_current else 30

        dns_correct = state.get("dns_correct", False)
        factors["dns_routing"] = 100 if dns_correct else 0

        tls_valid = state.get("tls_valid", True)
        factors["tls_status"] = 100 if tls_valid else 0

        api_responsive = state.get("api_responsive", False)
        factors["api_health"] = 100 if api_responsive else 0

        score = sum(factors.values()) / max(len(factors), 1)
        for name, val in factors.items():
            if val < 50:
                gaps.append(name)

        return DimensionScore(
            dimension="deployment",
            score=score,
            weight=DIMENSION_WEIGHTS["deployment"],
            factors=factors,
            gap_factors=gaps,
            explanation=self._explain_deployment(factors, score),
        )

    def _score_operator(self, state: dict[str, Any]) -> DimensionScore:
        factors: dict[str, float] = {}
        gaps: list[str] = []

        pending_approvals = state.get("pending_approvals", 0)
        factors["approval_backlog"] = max(0, 100 - pending_approvals * 10)

        intervention_rate = state.get("intervention_rate", 0.0)
        factors["autonomy_level"] = max(0, 100 * (1.0 - intervention_rate))

        compression = state.get("operator_compression", {})
        patterns = compression.get("total_patterns", 0)
        factors["pattern_recognition"] = min(100, patterns * 10)

        last_interaction = state.get("last_interaction_seconds_ago", 0)
        if last_interaction > 0:
            factors["operator_presence"] = max(0, 100 - (last_interaction / 36))
        else:
            factors["operator_presence"] = 50

        score = sum(factors.values()) / max(len(factors), 1)
        for name, val in factors.items():
            if val < 50:
                gaps.append(name)

        return DimensionScore(
            dimension="operator",
            score=score,
            weight=DIMENSION_WEIGHTS["operator"],
            factors=factors,
            gap_factors=gaps,
            explanation=self._explain_operator(factors, score),
        )

    def _score_memory(self, state: dict[str, Any]) -> DimensionScore:
        factors: dict[str, float] = {}
        gaps: list[str] = []

        observations = state.get("total_observations", 0)
        factors["observation_store"] = min(100, observations * 2) if observations > 0 else 0

        skills = state.get("total_skills", 0)
        factors["skill_registry"] = min(100, skills * 5) if skills > 0 else 0

        memories = state.get("total_memories", 0)
        factors["memory_store"] = min(100, memories * 5) if memories > 0 else 0

        journal_size = state.get("journal_entries", 0)
        factors["execution_journal"] = min(100, journal_size * 2) if journal_size > 0 else 0

        score = sum(factors.values()) / max(len(factors), 1)
        for name, val in factors.items():
            if val < 50:
                gaps.append(name)

        return DimensionScore(
            dimension="memory",
            score=score,
            weight=DIMENSION_WEIGHTS["memory"],
            factors=factors,
            gap_factors=gaps,
            explanation=self._explain_memory(factors, score),
        )

    def _score_composition(self, state: dict[str, Any]) -> DimensionScore:
        factors: dict[str, float] = {}
        gaps: list[str] = []

        runtimes_available = state.get("runtimes_available", 0)
        runtimes_total = state.get("runtimes_total", 0)
        if runtimes_total > 0:
            factors["runtime_availability"] = (runtimes_available / runtimes_total) * 100
        else:
            factors["runtime_availability"] = 0

        agents_registered = state.get("agents_registered", 0)
        factors["agent_registry"] = min(100, agents_registered * 20)

        event_spine_active = state.get("event_spine_active", False)
        factors["event_spine"] = 100 if event_spine_active else 0

        tick_running = state.get("tick_running", False)
        factors["autonomous_tick"] = 100 if tick_running else 0

        subsystem_count = state.get("connected_subsystems", 0)
        factors["subsystem_integration"] = min(100, subsystem_count * 10)

        score = sum(factors.values()) / max(len(factors), 1)
        for name, val in factors.items():
            if val < 50:
                gaps.append(name)

        return DimensionScore(
            dimension="composition",
            score=score,
            weight=DIMENSION_WEIGHTS["composition"],
            factors=factors,
            gap_factors=gaps,
            explanation=self._explain_composition(factors, score),
        )

    def _status_label(self, composite: float) -> str:
        if composite >= 80:
            return "operational"
        if composite >= 60:
            return "degraded"
        if composite >= 40:
            return "limited"
        return "critical"

    def _explain_execution(self, factors: dict[str, float], score: float) -> str:
        if score >= 80:
            return "Execution pipeline healthy — tasks completing reliably"
        weak = [k for k, v in factors.items() if v < 50]
        if weak:
            return f"Execution limited by: {', '.join(w.replace('_', ' ') for w in weak)}"
        return f"Execution at {score:.0f}% — room for improvement in throughput"

    def _explain_governance(self, factors: dict[str, float], score: float) -> str:
        if score >= 80:
            return "Governance fully active — guard, gateway, and audit trail operational"
        weak = [k for k, v in factors.items() if v < 50]
        if weak:
            return f"Governance gaps: {', '.join(w.replace('_', ' ') for w in weak)}"
        return f"Governance at {score:.0f}% — safety rails partially configured"

    def _explain_deployment(self, factors: dict[str, float], score: float) -> str:
        if score >= 80:
            return "Deployment healthy — services up, DNS correct, build current"
        weak = [k for k, v in factors.items() if v < 50]
        if weak:
            return f"Deployment issues: {', '.join(w.replace('_', ' ') for w in weak)}"
        return f"Deployment at {score:.0f}% — some services need attention"

    def _explain_operator(self, factors: dict[str, float], score: float) -> str:
        if score >= 80:
            return "Operator loop healthy — low backlog, high autonomy"
        weak = [k for k, v in factors.items() if v < 50]
        if weak:
            return f"Operator bottleneck: {', '.join(w.replace('_', ' ') for w in weak)}"
        return f"Operator readiness at {score:.0f}%"

    def _explain_memory(self, factors: dict[str, float], score: float) -> str:
        if score >= 80:
            return "Knowledge persistence healthy — observations, skills, and journal populated"
        weak = [k for k, v in factors.items() if v < 50]
        if weak:
            return f"Memory gaps: {', '.join(w.replace('_', ' ') for w in weak)}"
        return f"Memory readiness at {score:.0f}%"

    def _explain_composition(self, factors: dict[str, float], score: float) -> str:
        if score >= 80:
            return "Subsystems composed — runtimes available, event spine active, tick running"
        weak = [k for k, v in factors.items() if v < 50]
        if weak:
            return f"Composition gaps: {', '.join(w.replace('_', ' ') for w in weak)}"
        return f"Composition at {score:.0f}% — subsystems partially integrated"

    @property
    def last_report(self) -> ReadinessReport | None:
        return self._last_report

    def to_dict(self) -> dict[str, Any]:
        if self._last_report is None:
            return {"composite_score": 0, "status": "not_computed", "dimensions": {}}
        return self._last_report.to_dict()
