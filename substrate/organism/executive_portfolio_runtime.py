"""C14.2 — Executive Portfolio Runtime.

Portfolio-level executive health. Aggregates resource allocation,
tradeoff intelligence, and all upstream subsystem health into a
unified executive view.

No execution authority. No mutation authority. Synthesis only.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ────────────────────────────────────────────────────────────


class ExecutiveHealth(str, Enum):
    OPTIMIZED = "optimized"
    FOCUSED = "focused"
    FRAGMENTED = "fragmented"
    OVERCOMMITTED = "overcommitted"
    CRITICAL = "critical"


class ExecutiveDriftType(str, Enum):
    ALLOCATION_DRIFT = "allocation_drift"
    TRADEOFF_BLINDNESS = "tradeoff_blindness"
    STRATEGIC_SCATTER = "strategic_scatter"
    DECISION_STALENESS = "decision_staleness"
    PREDICTION_IGNORANCE = "prediction_ignorance"


@dataclass
class ExecutiveDriftWarning:
    drift_type: str = ExecutiveDriftType.ALLOCATION_DRIFT.value
    severity: str = "low"
    description: str = ""
    affected_ids: list[str] = field(default_factory=list)
    recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "drift_type": self.drift_type,
            "severity": self.severity,
            "description": self.description,
            "affected_ids": self.affected_ids,
            "recommendation": self.recommendation,
        }


@dataclass
class ExecutivePortfolioSnapshot:
    executive_health: str = ExecutiveHealth.FOCUSED.value
    allocation_health: str = "balanced"
    tradeoff_severity: str = "negligible"
    work_health: str = "unknown"
    prediction_health: str = "unknown"
    learning_health: str = "unknown"
    decision_health: str = "unknown"
    capability_health: str = "unknown"
    goal_alignment_health: str = "unknown"
    drift_warnings: list[dict[str, Any]] = field(default_factory=list)
    top_recommendations: list[dict[str, Any]] = field(default_factory=list)
    resource_summary: dict[str, Any] = field(default_factory=dict)
    focus_score: float = 0.5
    overcommitment_index: float = 0.0
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "executive_health": self.executive_health,
            "allocation_health": self.allocation_health,
            "tradeoff_severity": self.tradeoff_severity,
            "work_health": self.work_health,
            "prediction_health": self.prediction_health,
            "learning_health": self.learning_health,
            "decision_health": self.decision_health,
            "capability_health": self.capability_health,
            "goal_alignment_health": self.goal_alignment_health,
            "drift_warnings": self.drift_warnings,
            "top_recommendations": self.top_recommendations,
            "resource_summary": self.resource_summary,
            "focus_score": round(self.focus_score, 4),
            "overcommitment_index": round(self.overcommitment_index, 4),
            "generated_at": self.generated_at,
        }


# ── Runtime ──────────────────────────────────────────────────────────


class ExecutivePortfolioRuntime:
    """Portfolio-level executive health aggregation.

    Composes C14.0 (allocation) + C14.1 (tradeoff) + 7 existing
    subsystems into a unified executive health view.

    No execution authority. No mutation authority. Synthesis only.
    """

    def __init__(
        self,
        resource_allocation: Any | None = None,
        tradeoff_engine: Any | None = None,
        work_portfolio: Any | None = None,
        prediction_portfolio: Any | None = None,
        learning_portfolio: Any | None = None,
        decision_impact: Any | None = None,
        capability_gap: Any | None = None,
        goal_alignment: Any | None = None,
        strategic_planning: Any | None = None,
    ) -> None:
        self._resource_allocation = resource_allocation
        self._tradeoff_engine = tradeoff_engine
        self._work_portfolio = work_portfolio
        self._prediction_portfolio = prediction_portfolio
        self._learning_portfolio = learning_portfolio
        self._decision_impact = decision_impact
        self._capability_gap = capability_gap
        self._goal_alignment = goal_alignment
        self._strategic_planning = strategic_planning

    # ── Lazy subsystem access ─────────────────────────────────────

    @property
    def _allocation(self) -> Any | None:
        if self._resource_allocation is None:
            try:
                from substrate.organism.resource_allocation_runtime import ResourceAllocationRuntime
                self._resource_allocation = ResourceAllocationRuntime()
            except Exception:
                logger.debug("executive_portfolio: could not lazy-load resource_allocation")
        return self._resource_allocation

    @property
    def _tradeoff(self) -> Any | None:
        if self._tradeoff_engine is None:
            try:
                from substrate.organism.tradeoff_intelligence_engine import TradeoffIntelligenceEngine
                self._tradeoff_engine = TradeoffIntelligenceEngine()
            except Exception:
                logger.debug("executive_portfolio: could not lazy-load tradeoff_engine")
        return self._tradeoff_engine

    @property
    def _work(self) -> Any | None:
        if self._work_portfolio is None:
            try:
                from substrate.organism.work_portfolio_runtime import WorkPortfolioRuntime
                self._work_portfolio = WorkPortfolioRuntime()
            except Exception:
                logger.debug("executive_portfolio: could not lazy-load work_portfolio")
        return self._work_portfolio

    @property
    def _prediction(self) -> Any | None:
        if self._prediction_portfolio is None:
            try:
                from substrate.organism.prediction_portfolio_runtime import PredictionPortfolioRuntime
                self._prediction_portfolio = PredictionPortfolioRuntime()
            except Exception:
                logger.debug("executive_portfolio: could not lazy-load prediction_portfolio")
        return self._prediction_portfolio

    @property
    def _learning(self) -> Any | None:
        if self._learning_portfolio is None:
            try:
                from substrate.organism.learning_portfolio_runtime import LearningPortfolioRuntime
                self._learning_portfolio = LearningPortfolioRuntime()
            except Exception:
                logger.debug("executive_portfolio: could not lazy-load learning_portfolio")
        return self._learning_portfolio

    @property
    def _decisions(self) -> Any | None:
        if self._decision_impact is None:
            try:
                from substrate.organism.decision_impact_engine import DecisionImpactEngine
                self._decision_impact = DecisionImpactEngine()
            except Exception:
                logger.debug("executive_portfolio: could not lazy-load decision_impact")
        return self._decision_impact

    @property
    def _caps(self) -> Any | None:
        if self._capability_gap is None:
            try:
                from substrate.organism.capability_gap_engine import CapabilityGapEngine
                self._capability_gap = CapabilityGapEngine()
            except Exception:
                logger.debug("executive_portfolio: could not lazy-load capability_gap")
        return self._capability_gap

    @property
    def _goals(self) -> Any | None:
        if self._goal_alignment is None:
            try:
                from substrate.organism.goal_alignment_engine import GoalAlignmentEngine
                self._goal_alignment = GoalAlignmentEngine()
            except Exception:
                logger.debug("executive_portfolio: could not lazy-load goal_alignment")
        return self._goal_alignment

    @property
    def _planning(self) -> Any | None:
        if self._strategic_planning is None:
            try:
                from substrate.organism.strategic_planning_engine import StrategicPlanningEngine
                self._strategic_planning = StrategicPlanningEngine()
            except Exception:
                logger.debug("executive_portfolio: could not lazy-load strategic_planning")
        return self._strategic_planning

    # ── Signal extraction ─────────────────────────────────────────

    def _get_allocation_health(self) -> str:
        try:
            if self._allocation is None:
                return "unknown"
            h = self._allocation.health()
            return h.value if hasattr(h, "value") else str(h)
        except Exception:
            logger.debug("executive_portfolio: allocation health failed")
            return "unknown"

    def _get_allocation_summary(self) -> dict[str, Any]:
        try:
            if self._allocation is None:
                return {}
            return self._allocation.summary()
        except Exception:
            logger.debug("executive_portfolio: allocation summary failed")
            return {}

    def _get_allocation_budgets(self) -> list[Any]:
        try:
            if self._allocation is None:
                return []
            return list(self._allocation.budgets())
        except Exception:
            logger.debug("executive_portfolio: budgets failed")
            return []

    def _get_top_recommendations(self, limit: int = 5) -> list[Any]:
        try:
            if self._allocation is None:
                return []
            return list(self._allocation.top_leverage(limit=limit))
        except Exception:
            logger.debug("executive_portfolio: top_leverage failed")
            return []

    def _get_unallocated_goals(self) -> list[str]:
        try:
            if self._allocation is None:
                return []
            return list(self._allocation.unallocated_goals())
        except Exception:
            logger.debug("executive_portfolio: unallocated_goals failed")
            return []

    def _get_tradeoff_severity(self) -> str:
        try:
            if self._tradeoff is None:
                return "unknown"
            snap = self._tradeoff.snapshot()
            if hasattr(snap, "overall_severity"):
                return snap.overall_severity
            return snap.get("overall_severity", "unknown") if isinstance(snap, dict) else "unknown"
        except Exception:
            logger.debug("executive_portfolio: tradeoff severity failed")
            return "unknown"

    def _get_contention_map(self) -> dict[str, list[str]]:
        try:
            if self._tradeoff is None:
                return {}
            return self._tradeoff.contention_map()
        except Exception:
            logger.debug("executive_portfolio: contention_map failed")
            return {}

    def _get_work_health(self) -> str:
        try:
            if self._work is None:
                return "unknown"
            h = self._work.health()
            return h.value if hasattr(h, "value") else str(h)
        except Exception:
            logger.debug("executive_portfolio: work health failed")
            return "unknown"

    def _get_work_snapshot(self) -> dict[str, Any]:
        try:
            if self._work is None:
                return {}
            snap = self._work.snapshot()
            if hasattr(snap, "to_dict"):
                return snap.to_dict()
            return snap if isinstance(snap, dict) else {}
        except Exception:
            logger.debug("executive_portfolio: work snapshot failed")
            return {}

    def _get_prediction_health(self) -> str:
        try:
            if self._prediction is None:
                return "unknown"
            h = self._prediction.health()
            return h.value if hasattr(h, "value") else str(h)
        except Exception:
            logger.debug("executive_portfolio: prediction health failed")
            return "unknown"

    def _get_prediction_drift_warnings(self) -> list[Any]:
        try:
            if self._prediction is None:
                return []
            return list(self._prediction.drift_warnings())
        except Exception:
            logger.debug("executive_portfolio: prediction drift_warnings failed")
            return []

    def _get_learning_health(self) -> str:
        try:
            if self._learning is None:
                return "unknown"
            h = self._learning.health()
            return h.value if hasattr(h, "value") else str(h)
        except Exception:
            logger.debug("executive_portfolio: learning health failed")
            return "unknown"

    def _get_decision_summary(self) -> dict[str, Any]:
        try:
            if self._decisions is None:
                return {}
            return self._decisions.summary()
        except Exception:
            logger.debug("executive_portfolio: decision summary failed")
            return {}

    def _get_decision_health(self) -> str:
        dec_summary = self._get_decision_summary()
        total = dec_summary.get("total_decisions", 0)
        at_risk = dec_summary.get("at_risk_count", 0)
        invalid = dec_summary.get("invalid_count", 0)
        if total == 0:
            return "unknown"
        if invalid > 0:
            return "degraded"
        if at_risk > total * 0.3:
            return "watch"
        return "healthy"

    def _get_capability_health(self) -> str:
        try:
            if self._caps is None:
                return "unknown"
            h = self._caps.gap_summary()
            gap_count = h.get("critical_gap_count", 0) if isinstance(h, dict) else 0
            if gap_count == 0:
                return "healthy"
            if gap_count <= 2:
                return "watch"
            return "degraded"
        except Exception:
            logger.debug("executive_portfolio: capability health failed")
            return "unknown"

    def _get_goal_alignment_health(self) -> str:
        try:
            if self._goals is None:
                return "unknown"
            score = float(self._goals.alignment_score())
            if score >= 0.8:
                return "healthy"
            if score >= 0.5:
                return "watch"
            return "degraded"
        except Exception:
            logger.debug("executive_portfolio: goal alignment health failed")
            return "unknown"

    def _get_active_goal_count(self) -> int:
        try:
            if self._planning is None:
                return 0
            rm = self._planning.roadmap()
            return len(rm) if isinstance(rm, dict) else 0
        except Exception:
            logger.debug("executive_portfolio: active goal count failed")
            return 0

    def _get_allocation_risk_target_ids(self) -> set[str]:
        try:
            recs = self._get_top_recommendations(limit=100)
            risk_ids: set[str] = set()
            for r in recs:
                tid = getattr(r, "target_id", "")
                rationale = getattr(r, "rationale", "")
                if "at-risk" in rationale.lower():
                    risk_ids.add(tid)
            return risk_ids
        except Exception:
            return set()

    # ── Focus score ───────────────────────────────────────────────

    def _base_focus_score(self) -> float:
        goal_count = self._get_active_goal_count()

        if goal_count <= 3:
            return 1.0
        elif goal_count <= 5:
            return 0.7
        elif goal_count <= 8:
            return 0.4
        else:
            return max(0.1, 1.0 - goal_count * 0.08)

    def focus_score(self) -> float:
        base = self._base_focus_score()

        drift_count = len(self.drift_warnings())
        budgets = self._get_allocation_budgets()
        overcommitted_count = sum(
            1 for b in budgets
            if getattr(b, "overcommitted", False)
        )

        adjusted = base - (drift_count * 0.05) - (overcommitted_count * 0.1)
        return max(0.0, min(1.0, round(adjusted, 4)))

    # ── Overcommitment index ──────────────────────────────────────

    def overcommitment_index(self) -> float:
        budgets = self._get_allocation_budgets()
        total = len(budgets) if budgets else 1
        overcommitted = sum(
            1 for b in budgets
            if getattr(b, "overcommitted", False)
        )
        base = overcommitted / max(total, 1)

        work_snap = self._get_work_snapshot()
        block_rate = work_snap.get("block_rate", 0.0)
        if isinstance(block_rate, str):
            try:
                block_rate = float(block_rate)
            except ValueError:
                block_rate = 0.0

        boosted = base + float(block_rate) * 0.3
        return max(0.0, min(1.0, round(boosted, 4)))

    # ── Drift detectors ───────────────────────────────────────────

    def drift_warnings(self) -> list[ExecutiveDriftWarning]:
        warnings: list[ExecutiveDriftWarning] = []

        self._detect_allocation_drift(warnings)
        self._detect_tradeoff_blindness(warnings)
        self._detect_strategic_scatter(warnings)
        self._detect_decision_staleness(warnings)
        self._detect_prediction_ignorance(warnings)

        return warnings

    def _detect_allocation_drift(self, warnings: list[ExecutiveDriftWarning]) -> None:
        unallocated = self._get_unallocated_goals()
        if unallocated:
            warnings.append(ExecutiveDriftWarning(
                drift_type=ExecutiveDriftType.ALLOCATION_DRIFT.value,
                severity="high" if len(unallocated) > 3 else "medium",
                description=f"{len(unallocated)} goals have no allocation recommendation",
                affected_ids=unallocated[:10],
                recommendation="Review allocation coverage — unallocated goals receive no resources",
            ))

    def _detect_tradeoff_blindness(self, warnings: list[ExecutiveDriftWarning]) -> None:
        contention = self._get_contention_map()
        blind_resources: list[str] = []
        affected: list[str] = []
        for resource, targets in contention.items():
            if len(targets) >= 3:
                blind_resources.append(resource)
                affected.extend(targets)
        if blind_resources:
            warnings.append(ExecutiveDriftWarning(
                drift_type=ExecutiveDriftType.TRADEOFF_BLINDNESS.value,
                severity="high" if len(blind_resources) >= 2 else "medium",
                description=(
                    f"{len(blind_resources)} resources have 3+ competing targets: "
                    f"{', '.join(blind_resources)}"
                ),
                affected_ids=list(set(affected))[:10],
                recommendation="Active tradeoff analysis needed — resource contention is high",
            ))

    def _detect_strategic_scatter(self, warnings: list[ExecutiveDriftWarning]) -> None:
        goal_count = self._get_active_goal_count()
        focus = self._base_focus_score()
        if focus < 0.3 and goal_count > 8:
            warnings.append(ExecutiveDriftWarning(
                drift_type=ExecutiveDriftType.STRATEGIC_SCATTER.value,
                severity="critical" if goal_count > 12 else "high",
                description=(
                    f"Focus score {focus:.2f} with {goal_count} active goals — "
                    f"organization is strategically scattered"
                ),
                affected_ids=[],
                recommendation="Reduce active goals to 3-5 for strategic focus",
            ))

    def _detect_decision_staleness(self, warnings: list[ExecutiveDriftWarning]) -> None:
        dec_summary = self._get_decision_summary()
        at_risk = dec_summary.get("at_risk_count", 0)
        invalid = dec_summary.get("invalid_count", 0)
        if at_risk > 3 or invalid > 0:
            severity = "critical" if invalid > 0 else "high"
            affected: list[str] = []
            desc_parts = []
            if at_risk > 3:
                desc_parts.append(f"{at_risk} at-risk decisions")
            if invalid > 0:
                desc_parts.append(f"{invalid} INVALID decisions")
            warnings.append(ExecutiveDriftWarning(
                drift_type=ExecutiveDriftType.DECISION_STALENESS.value,
                severity=severity,
                description="; ".join(desc_parts),
                affected_ids=affected,
                recommendation="Review and revalidate stale decisions before allocating resources",
            ))

    def _detect_prediction_ignorance(self, warnings: list[ExecutiveDriftWarning]) -> None:
        pred_drift = self._get_prediction_drift_warnings()
        if not pred_drift:
            return

        alloc_risk_ids = self._get_allocation_risk_target_ids()
        pred_risk_ids: set[str] = set()
        for w in pred_drift:
            affected = getattr(w, "affected_ids", [])
            if isinstance(affected, list):
                pred_risk_ids.update(affected)

        unacknowledged = pred_risk_ids - alloc_risk_ids
        if unacknowledged or (pred_drift and not alloc_risk_ids):
            warnings.append(ExecutiveDriftWarning(
                drift_type=ExecutiveDriftType.PREDICTION_IGNORANCE.value,
                severity="high",
                description=(
                    f"Prediction system has {len(pred_drift)} drift warnings "
                    f"but allocations don't reference prediction risk targets"
                ),
                affected_ids=list(unacknowledged)[:10],
                recommendation="Ensure allocation recommendations incorporate prediction risk signals",
            ))

    # ── Health classification ─────────────────────────────────────

    def health(self) -> ExecutiveHealth:
        focus = self.focus_score()
        overcommit = self.overcommitment_index()
        drift_count = len(self.drift_warnings())

        subsystem_healths = [
            self._get_work_health(),
            self._get_prediction_health(),
            self._get_learning_health(),
            self._get_decision_health(),
            self._get_capability_health(),
            self._get_goal_alignment_health(),
        ]
        degraded_count = sum(
            1 for h in subsystem_healths
            if h in ("degraded", "critical", "blind", "volatile")
        )

        if overcommit > 0.7 or degraded_count >= 5:
            return ExecutiveHealth.CRITICAL
        if overcommit > 0.5 or focus < 0.3:
            return ExecutiveHealth.OVERCOMMITTED
        if focus >= 0.3 or overcommit <= 0.5:
            if focus < 0.5 or overcommit > 0.3:
                return ExecutiveHealth.FRAGMENTED
        if focus >= 0.5 and overcommit <= 0.3:
            if drift_count > 0 or degraded_count > 0:
                return ExecutiveHealth.FOCUSED
        if focus >= 0.7 and overcommit <= 0.2 and drift_count == 0:
            return ExecutiveHealth.OPTIMIZED
        return ExecutiveHealth.FOCUSED

    # ── Public API ────────────────────────────────────────────────

    def top_recommendations(self, limit: int = 5) -> list[dict[str, Any]]:
        recs = self._get_top_recommendations(limit=limit)
        return [
            r.to_dict() if hasattr(r, "to_dict") else r
            for r in recs
        ]

    def snapshot(self) -> ExecutivePortfolioSnapshot:
        drift = self.drift_warnings()
        recs = self._get_top_recommendations(limit=5)
        alloc_summary = self._get_allocation_summary()
        budgets = self._get_allocation_budgets()

        resource_summary = {
            "budget_count": len(budgets),
            "overcommitted_count": sum(
                1 for b in budgets if getattr(b, "overcommitted", False)
            ),
            "allocation_summary": alloc_summary,
        }

        return ExecutivePortfolioSnapshot(
            executive_health=self.health().value,
            allocation_health=self._get_allocation_health(),
            tradeoff_severity=self._get_tradeoff_severity(),
            work_health=self._get_work_health(),
            prediction_health=self._get_prediction_health(),
            learning_health=self._get_learning_health(),
            decision_health=self._get_decision_health(),
            capability_health=self._get_capability_health(),
            goal_alignment_health=self._get_goal_alignment_health(),
            drift_warnings=[w.to_dict() for w in drift],
            top_recommendations=[
                r.to_dict() if hasattr(r, "to_dict") else r
                for r in recs
            ],
            resource_summary=resource_summary,
            focus_score=self.focus_score(),
            overcommitment_index=self.overcommitment_index(),
            generated_at=time.time(),
        )

    def summary(self) -> dict[str, Any]:
        h = self.health()
        return {
            "executive_health": h.value,
            "allocation_health": self._get_allocation_health(),
            "tradeoff_severity": self._get_tradeoff_severity(),
            "focus_score": self.focus_score(),
            "overcommitment_index": self.overcommitment_index(),
            "drift_count": len(self.drift_warnings()),
            "active_goal_count": self._get_active_goal_count(),
            "subsystem_health": {
                "work": self._get_work_health(),
                "prediction": self._get_prediction_health(),
                "learning": self._get_learning_health(),
                "decisions": self._get_decision_health(),
                "capabilities": self._get_capability_health(),
                "goal_alignment": self._get_goal_alignment_health(),
            },
        }
