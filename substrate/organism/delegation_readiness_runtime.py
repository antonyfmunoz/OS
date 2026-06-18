"""Delegation Readiness Runtime — pre-assignment feasibility + outcome prediction.

Campaign 11.1. UMH substrate layer. Instance-agnostic.

Composes (does not replace):
  - AgentFleetRuntime (C23) — capability+risk-aware assignment
  - AgentCapabilityModel (Organism) — per-agent reliability scores
  - CapabilityGapEngine (C10.1) — required vs available capabilities
  - ProjectionEngine (Phase 6) — trend/risk forecasting
  - DecisionValidityEngine (C9.3) — decision health
  - OutcomeTrackingRuntime (C8.2) — goal progress/health
  - WorkReadinessRuntime (C11.0) — readiness classification

Authority remains with AgentFleetRuntime (delegation), ExecutionCoordinator
(execution), DelegationRuntime (mission lifecycle). This runtime ONLY
classifies delegation feasibility and predicts outcomes.

Read-only. No mutation. No execution. Deterministic. Zero LLM calls.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────


@dataclass
class DelegationReadiness:
    work_id: str = ""
    delegatable: bool = False
    recommended_executor: str = ""
    executor_label: str = ""
    confidence: float = 0.0
    success_probability: float = 0.0
    capabilities_required: list[str] = field(default_factory=list)
    capabilities_matched: list[str] = field(default_factory=list)
    capabilities_missing: list[str] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    blocking_decisions: list[str] = field(default_factory=list)
    rationale: str = ""
    alternatives: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "work_id": self.work_id,
            "delegatable": self.delegatable,
            "recommended_executor": self.recommended_executor,
            "executor_label": self.executor_label,
            "confidence": round(self.confidence, 4),
            "success_probability": round(self.success_probability, 4),
            "capabilities_required": self.capabilities_required,
            "capabilities_matched": self.capabilities_matched,
            "capabilities_missing": self.capabilities_missing,
            "risk_factors": self.risk_factors,
            "blocking_decisions": self.blocking_decisions,
            "rationale": self.rationale,
            "alternatives": self.alternatives,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DelegationReadiness:
        return cls(
            work_id=d.get("work_id", ""),
            delegatable=d.get("delegatable", False),
            recommended_executor=d.get("recommended_executor", ""),
            executor_label=d.get("executor_label", ""),
            confidence=d.get("confidence", 0.0),
            success_probability=d.get("success_probability", 0.0),
            capabilities_required=d.get("capabilities_required", []),
            capabilities_matched=d.get("capabilities_matched", []),
            capabilities_missing=d.get("capabilities_missing", []),
            risk_factors=d.get("risk_factors", []),
            blocking_decisions=d.get("blocking_decisions", []),
            rationale=d.get("rationale", ""),
            alternatives=d.get("alternatives", []),
        )


@dataclass
class DelegationReadinessSnapshot:
    total_assessed: int = 0
    delegatable: int = 0
    not_delegatable: int = 0
    avg_confidence: float = 0.0
    avg_success_probability: float = 0.0
    top_missing_capabilities: list[str] = field(default_factory=list)
    top_risk_factors: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_assessed": self.total_assessed,
            "delegatable": self.delegatable,
            "not_delegatable": self.not_delegatable,
            "avg_confidence": round(self.avg_confidence, 4),
            "avg_success_probability": round(self.avg_success_probability, 4),
            "top_missing_capabilities": self.top_missing_capabilities,
            "top_risk_factors": self.top_risk_factors,
            "timestamp": self.timestamp,
        }


# ── Runtime ───────────────────────────────────────────────────────────────


class DelegationReadinessRuntime:
    """Read-only delegation feasibility + outcome prediction.

    Composes:
      - AgentFleetRuntime (C23) — assignment scoring
      - AgentCapabilityModel — per-agent reliability
      - CapabilityGapEngine (C10.1) — capability gaps
      - ProjectionEngine (Phase 6) — trend/risk data
      - DecisionValidityEngine (C9.3) — decision validity
      - OutcomeTrackingRuntime (C8.2) — goal health
      - WorkReadinessRuntime (C11.0) — readiness state

    Owns nothing. Mutates nothing. Authority stays with source systems.
    """

    def __init__(
        self,
        fleet_runtime: Any | None = None,
        capability_model: Any | None = None,
        capability_gap: Any | None = None,
        projection_engine: Any | None = None,
        decision_validity: Any | None = None,
        outcome_tracking: Any | None = None,
        work_readiness: Any | None = None,
    ) -> None:
        self._fleet = fleet_runtime
        self._cap_model = capability_model
        self._cap_gap = capability_gap
        self._projection = projection_engine
        self._decision = decision_validity
        self._outcome = outcome_tracking
        self._readiness = work_readiness

    # ── Lazy subsystem access ─────────────────────────────────────

    @property
    def fleet(self) -> Any | None:
        if self._fleet is None:
            try:
                from substrate.organism.agent_fleet_runtime import AgentFleetRuntime
                from substrate.organism.agent_capability_model import AgentCapabilityModel
                cap = AgentCapabilityModel()
                self._fleet = AgentFleetRuntime(
                    capability_model=cap, compute_fabric=None,
                )
            except Exception:
                logger.debug("AgentFleetRuntime unavailable")
        return self._fleet

    @property
    def cap_model(self) -> Any | None:
        if self._cap_model is None:
            try:
                from substrate.organism.agent_capability_model import AgentCapabilityModel
                self._cap_model = AgentCapabilityModel()
            except Exception:
                logger.debug("AgentCapabilityModel unavailable")
        return self._cap_model

    @property
    def cap_gap(self) -> Any | None:
        if self._cap_gap is None:
            try:
                from substrate.organism.capability_gap_engine import CapabilityGapEngine
                self._cap_gap = CapabilityGapEngine()
            except Exception:
                logger.debug("CapabilityGapEngine unavailable")
        return self._cap_gap

    @property
    def projection(self) -> Any | None:
        if self._projection is None:
            try:
                from substrate.organism.projection_engine import ProjectionEngine
                self._projection = ProjectionEngine()
            except Exception:
                logger.debug("ProjectionEngine unavailable")
        return self._projection

    @property
    def decision(self) -> Any | None:
        if self._decision is None:
            try:
                from substrate.organism.decision_validity_engine import DecisionValidityEngine
                self._decision = DecisionValidityEngine()
            except Exception:
                logger.debug("DecisionValidityEngine unavailable")
        return self._decision

    @property
    def outcome(self) -> Any | None:
        if self._outcome is None:
            try:
                from substrate.organism.outcome_tracking_runtime import OutcomeTrackingRuntime
                self._outcome = OutcomeTrackingRuntime()
            except Exception:
                logger.debug("OutcomeTrackingRuntime unavailable")
        return self._outcome

    @property
    def readiness(self) -> Any | None:
        if self._readiness is None:
            try:
                from substrate.organism.work_readiness_runtime import WorkReadinessRuntime
                self._readiness = WorkReadinessRuntime()
            except Exception:
                logger.debug("WorkReadinessRuntime unavailable")
        return self._readiness

    # ── Core assessment ───────────────────────────────────────────

    def _try_fleet_assign(
        self,
        capabilities: list[str],
        risk_class: str,
    ) -> tuple[str, str, float, list[str], list[str], str]:
        """Try AgentFleetRuntime.assign(). Returns (executor, label, confidence, matched, alternatives, rationale)."""
        if self.fleet is None:
            return ("", "", 0.0, [], [], "fleet runtime unavailable")
        try:
            assignment = self.fleet.assign(
                capabilities_required=capabilities,
                risk_class=risk_class,
            )
            executor = getattr(assignment, "agent_type_id", "")
            label = getattr(assignment, "agent_label", executor)
            confidence = getattr(assignment, "score", 0.0)
            matched = getattr(assignment, "matched_capabilities", [])
            alternatives = getattr(assignment, "alternatives", [])
            rationale = ""
            r = getattr(assignment, "rationale", None)
            if r is not None:
                rationale = getattr(r, "summary", str(r))
            return (executor, label, confidence, matched, alternatives, rationale)
        except Exception as exc:
            logger.debug("Fleet assign failed: %s", exc)
            return ("", "", 0.0, [], [], f"assignment failed: {exc}")

    def _get_executor_reliability(self, executor_type: str) -> float:
        """Get historical reliability for an executor from AgentCapabilityModel."""
        if self.cap_model is None or not executor_type:
            return 0.5
        try:
            profile = self.cap_model.get_profile(executor_type)
            if profile is not None:
                total = getattr(profile, "total_attempts", 0)
                if total > 0:
                    return getattr(profile, "overall_reliability", 0.5)
            return 0.5
        except Exception:
            return 0.5

    def _get_risk_factors(self, goal_id: str) -> list[str]:
        """Collect risk factors from projection engine and decision validity."""
        factors: list[str] = []
        self._fill_projection_risks(factors, goal_id)
        self._fill_decision_risks(factors, goal_id)
        self._fill_outcome_risks(factors, goal_id)
        return factors

    def _fill_projection_risks(self, factors: list[str], goal_id: str) -> None:
        if self.projection is None:
            return
        try:
            risk_detector = getattr(self.projection, "_risk_detector", None)
            if risk_detector is None:
                return
            risks = risk_detector.detect_risks()
            if isinstance(risks, list):
                for risk in risks[:3]:
                    desc = getattr(risk, "description", "")
                    if desc:
                        factors.append(f"projection: {desc}")
        except Exception:
            logger.debug("Projection risk fetch failed")

    def _fill_decision_risks(self, factors: list[str], goal_id: str) -> None:
        if self.decision is None:
            return
        try:
            at_risk = self.decision.at_risk()
            if isinstance(at_risk, list):
                for dv in at_risk[:3]:
                    did = getattr(dv, "decision_id", "")
                    rec = getattr(dv, "recommendation", "")
                    if did:
                        factors.append(f"decision at risk: {did} - {rec}")
        except Exception:
            logger.debug("Decision validity fetch failed")

    def _fill_outcome_risks(self, factors: list[str], goal_id: str) -> None:
        if self.outcome is None:
            return
        try:
            at_risk_goals = self.outcome.goals_at_risk()
            if isinstance(at_risk_goals, list):
                for g in at_risk_goals[:3]:
                    gid = ""
                    if hasattr(g, "goal_id"):
                        gid = g.goal_id
                    elif isinstance(g, dict):
                        gid = g.get("goal_id", "")
                    if gid:
                        factors.append(f"goal at risk: {gid}")
        except Exception:
            logger.debug("Outcome tracking fetch failed")

    def _get_blocking_decisions(self) -> list[str]:
        """Get IDs of invalid or expired decisions."""
        if self.decision is None:
            return []
        try:
            invalid = self.decision.invalid()
            if isinstance(invalid, list):
                return [
                    getattr(dv, "decision_id", "")
                    for dv in invalid
                    if getattr(dv, "decision_id", "")
                ]
            return []
        except Exception:
            return []

    def _compute_success_probability(
        self,
        confidence: float,
        reliability: float,
        risk_factor_count: int,
        blocking_decision_count: int,
        capability_gap_count: int,
    ) -> float:
        """Deterministic success probability from component scores.

        Base = (confidence * 0.3) + (reliability * 0.4) + (0.3 baseline)
        Penalties: -0.1 per risk factor, -0.15 per blocking decision, -0.2 per cap gap
        Floor at 0.0, ceiling at 1.0.
        """
        base = (confidence * 0.3) + (reliability * 0.4) + 0.3
        penalty = (
            risk_factor_count * 0.1
            + blocking_decision_count * 0.15
            + capability_gap_count * 0.2
        )
        return max(0.0, min(1.0, base - penalty))

    # ── Public API ────────────────────────────────────────────────

    def assess(
        self,
        work_id: str,
        capabilities_required: list[str] | None = None,
        risk_class: str = "low",
        goal_id: str = "",
    ) -> DelegationReadiness:
        """Full delegation feasibility assessment for one work item."""
        if capabilities_required is None:
            capabilities_required = []

        caps_missing: list[str] = []
        if goal_id and self.cap_gap is not None:
            try:
                gaps = self.cap_gap.gaps_for_goal(goal_id)
                if isinstance(gaps, list):
                    caps_missing = [
                        getattr(g, "required_capability", "")
                        for g in gaps
                        if getattr(g, "required_capability", "")
                    ]
            except Exception:
                logger.debug("Cap gap fetch failed for goal %s", goal_id)

        executor, label, confidence, matched, alts, rationale = self._try_fleet_assign(
            capabilities_required, risk_class,
        )

        reliability = self._get_executor_reliability(executor)
        risk_factors = self._get_risk_factors(goal_id)
        blocking_decisions = self._get_blocking_decisions()

        success_prob = self._compute_success_probability(
            confidence=confidence,
            reliability=reliability,
            risk_factor_count=len(risk_factors),
            blocking_decision_count=len(blocking_decisions),
            capability_gap_count=len(caps_missing),
        )

        delegatable = bool(executor) and confidence > 0.2 and not caps_missing

        if not rationale:
            if delegatable:
                rationale = (
                    f"executor={executor} confidence={confidence:.2f} "
                    f"reliability={reliability:.2f} success_prob={success_prob:.2f}"
                )
            else:
                reasons: list[str] = []
                if not executor:
                    reasons.append("no suitable executor found")
                if caps_missing:
                    reasons.append(f"missing capabilities: {', '.join(caps_missing[:3])}")
                if confidence <= 0.2:
                    reasons.append(f"low confidence ({confidence:.2f})")
                rationale = "; ".join(reasons) if reasons else "not delegatable"

        return DelegationReadiness(
            work_id=work_id,
            delegatable=delegatable,
            recommended_executor=executor,
            executor_label=label,
            confidence=confidence,
            success_probability=success_prob,
            capabilities_required=capabilities_required,
            capabilities_matched=matched if isinstance(matched, list) else [],
            capabilities_missing=caps_missing,
            risk_factors=risk_factors,
            blocking_decisions=blocking_decisions,
            rationale=rationale,
            alternatives=alts if isinstance(alts, list) else [],
        )

    def assess_batch(self, work_ids: list[str]) -> list[DelegationReadiness]:
        """Batch assessment for multiple work items."""
        return [self.assess(wid) for wid in work_ids]

    def best_executor_for(
        self,
        capabilities: list[str],
        risk_class: str = "low",
    ) -> DelegationReadiness:
        """Find best executor for a capability set (no specific work item)."""
        return self.assess(
            work_id="",
            capabilities_required=capabilities,
            risk_class=risk_class,
        )

    def success_probability(
        self,
        work_id: str,
        goal_id: str = "",
    ) -> float:
        """Standalone outcome prediction for a work item."""
        dr = self.assess(work_id=work_id, goal_id=goal_id)
        return dr.success_probability

    def snapshot(self) -> DelegationReadinessSnapshot:
        """Aggregate delegation readiness across all active work."""
        assessments: list[DelegationReadiness] = []

        if self.readiness is not None:
            try:
                all_work = self.readiness.assess_all()
                for wa in all_work:
                    dr = self.assess(
                        work_id=wa.work_id,
                        goal_id=wa.goal_ids[0] if wa.goal_ids else "",
                    )
                    assessments.append(dr)
            except Exception:
                logger.debug("Failed to enumerate work for delegation snapshot")

        if not assessments:
            return DelegationReadinessSnapshot(timestamp=time.time())

        delegatable_count = sum(1 for a in assessments if a.delegatable)
        confs = [a.confidence for a in assessments if a.confidence > 0]
        probs = [a.success_probability for a in assessments]

        cap_counts: dict[str, int] = {}
        risk_counts: dict[str, int] = {}
        for a in assessments:
            for c in a.capabilities_missing:
                cap_counts[c] = cap_counts.get(c, 0) + 1
            for r in a.risk_factors:
                risk_counts[r] = risk_counts.get(r, 0) + 1

        top_caps = sorted(cap_counts, key=cap_counts.get, reverse=True)[:5]
        top_risks = sorted(risk_counts, key=risk_counts.get, reverse=True)[:5]

        return DelegationReadinessSnapshot(
            total_assessed=len(assessments),
            delegatable=delegatable_count,
            not_delegatable=len(assessments) - delegatable_count,
            avg_confidence=sum(confs) / len(confs) if confs else 0.0,
            avg_success_probability=sum(probs) / len(probs) if probs else 0.0,
            top_missing_capabilities=top_caps,
            top_risk_factors=top_risks,
            timestamp=time.time(),
        )

    def summary(self) -> dict[str, Any]:
        """Compact dict for API."""
        snap = self.snapshot()
        return {
            "total_assessed": snap.total_assessed,
            "delegatable": snap.delegatable,
            "not_delegatable": snap.not_delegatable,
            "avg_confidence": round(snap.avg_confidence, 4),
            "avg_success_probability": round(snap.avg_success_probability, 4),
            "top_missing_capabilities": snap.top_missing_capabilities,
            "top_risk_factors": snap.top_risk_factors,
        }
