"""C14.0 — Resource Allocation Runtime.

Determines where finite resources should be invested. Produces ranked
allocation recommendations with strategic leverage scoring.

No execution authority. No mutation authority. Recommendations only.
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ────────────────────────────────────────────────────────────


class ResourceType(str, Enum):
    TIME = "time"
    ATTENTION = "attention"
    CAPITAL = "capital"
    CAPABILITY_BUILDING = "capability_building"
    EXECUTION_CAPACITY = "execution_capacity"


class AllocationPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    DEFER = "defer"


class AllocationHealth(str, Enum):
    OPTIMIZED = "optimized"
    BALANCED = "balanced"
    CONSTRAINED = "constrained"
    OVERCOMMITTED = "overcommitted"
    CRITICAL = "critical"


@dataclass
class AllocationRecommendation:
    recommendation_id: str = ""
    resource_type: str = ResourceType.TIME.value
    target_id: str = ""
    target_name: str = ""
    target_type: str = ""
    priority: str = AllocationPriority.MEDIUM.value
    leverage_score: float = 0.0
    allocation_confidence: float = 0.0
    rationale: str = ""
    competing_targets: list[str] = field(default_factory=list)
    source_signals: list[str] = field(default_factory=list)
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "resource_type": self.resource_type,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "target_type": self.target_type,
            "priority": self.priority,
            "leverage_score": round(self.leverage_score, 4),
            "allocation_confidence": round(self.allocation_confidence, 4),
            "rationale": self.rationale,
            "competing_targets": self.competing_targets,
            "source_signals": self.source_signals,
            "generated_at": self.generated_at,
        }


@dataclass
class ResourceBudget:
    resource_type: str = ResourceType.TIME.value
    total_capacity: float = 1.0
    allocated: float = 0.0
    available: float = 1.0
    overcommitted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_type": self.resource_type,
            "total_capacity": round(self.total_capacity, 4),
            "allocated": round(self.allocated, 4),
            "available": round(self.available, 4),
            "overcommitted": self.overcommitted,
        }


@dataclass
class AllocationSnapshot:
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    resource_budgets: list[dict[str, Any]] = field(default_factory=list)
    top_leverage_targets: list[dict[str, Any]] = field(default_factory=list)
    overcommitted_resources: list[str] = field(default_factory=list)
    unallocated_goals: list[str] = field(default_factory=list)
    allocation_health: str = AllocationHealth.BALANCED.value
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendations": self.recommendations,
            "resource_budgets": self.resource_budgets,
            "top_leverage_targets": self.top_leverage_targets,
            "overcommitted_resources": self.overcommitted_resources,
            "unallocated_goals": self.unallocated_goals,
            "allocation_health": self.allocation_health,
            "generated_at": self.generated_at,
        }


# ── Runtime ──────────────────────────────────────────────────────────


class ResourceAllocationRuntime:
    """Determines where finite resources should be invested.

    Composes 7 existing subsystems (C8-C13) into ranked allocation
    recommendations with strategic leverage scoring.

    No execution authority. No mutation authority. Recommendations only.
    """

    MAX_PARALLEL_GOALS = 5
    ATTENTION_THRESHOLD = 5
    LEVERAGE_WEIGHTS = {
        "goal_alignment": 0.30,
        "prediction_risk": 0.20,
        "capability_gap": 0.15,
        "work_velocity": 0.15,
        "decision_impact": 0.10,
        "learning_compound": 0.10,
    }

    def __init__(
        self,
        strategic_planning: Any | None = None,
        goal_alignment: Any | None = None,
        capability_gap: Any | None = None,
        work_portfolio: Any | None = None,
        prediction_portfolio: Any | None = None,
        learning_portfolio: Any | None = None,
        decision_impact: Any | None = None,
    ) -> None:
        self._strategic_planning = strategic_planning
        self._goal_alignment = goal_alignment
        self._capability_gap = capability_gap
        self._work_portfolio = work_portfolio
        self._prediction_portfolio = prediction_portfolio
        self._learning_portfolio = learning_portfolio
        self._decision_impact = decision_impact

    # ── Lazy subsystem access ─────────────────────────────────────

    @property
    def _planning(self) -> Any | None:
        if self._strategic_planning is None:
            try:
                from substrate.organism.strategic_planning_engine import StrategicPlanningEngine
                self._strategic_planning = StrategicPlanningEngine()
            except Exception:
                logger.debug("resource_allocation: could not lazy-load strategic_planning")
        return self._strategic_planning

    @property
    def _goals(self) -> Any | None:
        if self._goal_alignment is None:
            try:
                from substrate.organism.goal_alignment_engine import GoalAlignmentEngine
                self._goal_alignment = GoalAlignmentEngine()
            except Exception:
                logger.debug("resource_allocation: could not lazy-load goal_alignment")
        return self._goal_alignment

    @property
    def _caps(self) -> Any | None:
        if self._capability_gap is None:
            try:
                from substrate.organism.capability_gap_engine import CapabilityGapEngine
                self._capability_gap = CapabilityGapEngine()
            except Exception:
                logger.debug("resource_allocation: could not lazy-load capability_gap")
        return self._capability_gap

    @property
    def _work(self) -> Any | None:
        if self._work_portfolio is None:
            try:
                from substrate.organism.work_portfolio_runtime import WorkPortfolioRuntime
                self._work_portfolio = WorkPortfolioRuntime()
            except Exception:
                logger.debug("resource_allocation: could not lazy-load work_portfolio")
        return self._work_portfolio

    @property
    def _prediction(self) -> Any | None:
        if self._prediction_portfolio is None:
            try:
                from substrate.organism.prediction_portfolio_runtime import PredictionPortfolioRuntime
                self._prediction_portfolio = PredictionPortfolioRuntime()
            except Exception:
                logger.debug("resource_allocation: could not lazy-load prediction_portfolio")
        return self._prediction_portfolio

    @property
    def _learning(self) -> Any | None:
        if self._learning_portfolio is None:
            try:
                from substrate.organism.learning_portfolio_runtime import LearningPortfolioRuntime
                self._learning_portfolio = LearningPortfolioRuntime()
            except Exception:
                logger.debug("resource_allocation: could not lazy-load learning_portfolio")
        return self._learning_portfolio

    @property
    def _decisions(self) -> Any | None:
        if self._decision_impact is None:
            try:
                from substrate.organism.decision_impact_engine import DecisionImpactEngine
                self._decision_impact = DecisionImpactEngine()
            except Exception:
                logger.debug("resource_allocation: could not lazy-load decision_impact")
        return self._decision_impact

    # ── Signal extraction ─────────────────────────────────────────

    def _get_roadmap_goals(self) -> list[dict[str, Any]]:
        try:
            if self._planning is None:
                return []
            rm = self._planning.roadmap()
            if isinstance(rm, dict):
                return [
                    {"id": k, "name": k, "type": "goal", **v}
                    for k, v in rm.items()
                ]
            return list(rm) if rm else []
        except Exception:
            logger.debug("resource_allocation: roadmap extraction failed")
            return []

    def _get_alignment_score(self) -> float:
        try:
            if self._goals is None:
                return 0.5
            return float(self._goals.alignment_score())
        except Exception:
            logger.debug("resource_allocation: alignment_score failed")
            return 0.5

    def _get_coverage(self) -> dict[str, int]:
        try:
            if self._goals is None:
                return {}
            return self._goals.coverage()
        except Exception:
            logger.debug("resource_allocation: coverage failed")
            return {}

    def _get_orphan_goals(self) -> list[Any]:
        try:
            if self._goals is None:
                return []
            return list(self._goals.orphan_goals())
        except Exception:
            logger.debug("resource_allocation: orphan_goals failed")
            return []

    def _get_critical_gaps(self) -> list[Any]:
        try:
            if self._caps is None:
                return []
            return list(self._caps.critical_gaps())
        except Exception:
            logger.debug("resource_allocation: critical_gaps failed")
            return []

    def _get_all_gaps(self) -> list[Any]:
        try:
            if self._caps is None:
                return []
            return list(self._caps.analyze_gaps())
        except Exception:
            logger.debug("resource_allocation: analyze_gaps failed")
            return []

    def _get_work_velocity(self) -> dict[str, Any]:
        try:
            if self._work is None:
                return {}
            v = self._work.velocity()
            return v if isinstance(v, dict) else {"completions_per_day": float(v)}
        except Exception:
            logger.debug("resource_allocation: velocity failed")
            return {}

    def _get_at_risk_work(self) -> list[Any]:
        try:
            if self._work is None:
                return []
            return list(self._work.at_risk_work())
        except Exception:
            logger.debug("resource_allocation: at_risk_work failed")
            return []

    def _get_work_snapshot(self) -> dict[str, Any]:
        try:
            if self._work is None:
                return {}
            snap = self._work.snapshot()
            if hasattr(snap, "to_dict"):
                return snap.to_dict()
            return snap if isinstance(snap, dict) else {}
        except Exception:
            logger.debug("resource_allocation: work snapshot failed")
            return {}

    def _get_prediction_snapshot(self) -> dict[str, Any]:
        try:
            if self._prediction is None:
                return {}
            snap = self._prediction.snapshot()
            if hasattr(snap, "to_dict"):
                return snap.to_dict()
            return snap if isinstance(snap, dict) else {}
        except Exception:
            logger.debug("resource_allocation: prediction snapshot failed")
            return {}

    def _get_highest_risk_forecasts(self) -> list[Any]:
        try:
            if self._prediction is None:
                return []
            return list(self._prediction.highest_risk_forecasts(limit=10))
        except Exception:
            logger.debug("resource_allocation: highest_risk_forecasts failed")
            return []

    def _get_prediction_health(self) -> str:
        try:
            if self._prediction is None:
                return "unknown"
            h = self._prediction.health()
            return h.value if hasattr(h, "value") else str(h)
        except Exception:
            logger.debug("resource_allocation: prediction health failed")
            return "unknown"

    def _get_compounding_score(self) -> float:
        try:
            if self._learning is None:
                return 0.5
            return float(self._learning.compounding_score())
        except Exception:
            logger.debug("resource_allocation: compounding_score failed")
            return 0.5

    def _get_learning_health(self) -> str:
        try:
            if self._learning is None:
                return "unknown"
            h = self._learning.health()
            return h.value if hasattr(h, "value") else str(h)
        except Exception:
            logger.debug("resource_allocation: learning health failed")
            return "unknown"

    def _get_highest_impact_decisions(self) -> list[Any]:
        try:
            if self._decisions is None:
                return []
            return list(self._decisions.highest_impact(limit=10))
        except Exception:
            logger.debug("resource_allocation: highest_impact failed")
            return []

    def _get_decision_summary(self) -> dict[str, Any]:
        try:
            if self._decisions is None:
                return {}
            return self._decisions.summary()
        except Exception:
            logger.debug("resource_allocation: decision summary failed")
            return {}

    # ── Confidence computation ────────────────────────────────────

    def _compute_allocation_confidence(self) -> float:
        pred_snap = self._get_prediction_snapshot()
        pred_conf = pred_snap.get("average_confidence", 0.5)

        dec_summary = self._get_decision_summary()
        total_decisions = dec_summary.get("total_decisions", 0)
        valid_decisions = dec_summary.get("valid_decisions", total_decisions)
        dec_conf = (valid_decisions / max(total_decisions, 1))

        learning_conf = self._get_compounding_score()

        result = min(pred_conf, dec_conf, learning_conf)
        return max(0.0, min(1.0, result))

    # ── Leverage scoring ──────────────────────────────────────────

    def _compute_leverage_for_goal(self, goal_id: str) -> tuple[float, list[str]]:
        signals: list[str] = []
        w = self.LEVERAGE_WEIGHTS

        alignment = self._get_alignment_score()
        coverage = self._get_coverage()
        goal_coverage = coverage.get(goal_id, 0)
        goal_alignment_weight = alignment * (1.0 if goal_coverage > 0 else 0.5)
        signals.append(f"goal_alignment={alignment:.2f}")

        risk_forecasts = self._get_highest_risk_forecasts()
        risk_ids = set()
        for f in risk_forecasts:
            eid = getattr(f, "entity_id", "") if hasattr(f, "entity_id") else ""
            if eid:
                risk_ids.add(eid)
        pred_risk_weight = 1.0 if goal_id in risk_ids else 0.3
        signals.append(f"prediction_risk={'HIGH' if goal_id in risk_ids else 'low'}")

        critical_gaps = self._get_critical_gaps()
        all_gaps = self._get_all_gaps()
        gap_ratio = len(critical_gaps) / max(len(all_gaps), 1)
        cap_gap_weight = gap_ratio
        signals.append(f"capability_gap_ratio={gap_ratio:.2f}")

        velocity = self._get_work_velocity()
        cpd = velocity.get("completions_per_day", 0.0)
        work_vel_weight = min(cpd / 5.0, 1.0)
        signals.append(f"work_velocity={cpd:.2f}")

        impact_decisions = self._get_highest_impact_decisions()
        impact_weight = min(len(impact_decisions) / 10.0, 1.0)
        signals.append(f"decision_impact_count={len(impact_decisions)}")

        compound = self._get_compounding_score()
        learning_weight = compound
        signals.append(f"learning_compound={compound:.2f}")

        leverage = (
            goal_alignment_weight * w["goal_alignment"]
            + pred_risk_weight * w["prediction_risk"]
            + cap_gap_weight * w["capability_gap"]
            + work_vel_weight * w["work_velocity"]
            + impact_weight * w["decision_impact"]
            + learning_weight * w["learning_compound"]
        )

        return max(0.0, min(1.0, leverage)), signals

    # ── Priority classification ───────────────────────────────────

    def _classify_priority(self, leverage: float, is_at_risk: bool) -> AllocationPriority:
        if is_at_risk and leverage >= 0.6:
            return AllocationPriority.CRITICAL
        if leverage >= 0.7:
            return AllocationPriority.HIGH
        if leverage >= 0.4:
            return AllocationPriority.MEDIUM
        if leverage >= 0.2:
            return AllocationPriority.LOW
        return AllocationPriority.DEFER

    # ── Resource budget computation ───────────────────────────────

    def _compute_budgets(self) -> list[ResourceBudget]:
        budgets: list[ResourceBudget] = []
        goals = self._get_roadmap_goals()
        goal_count = len(goals)

        time_allocated = goal_count / max(self.MAX_PARALLEL_GOALS, 1)
        budgets.append(ResourceBudget(
            resource_type=ResourceType.TIME.value,
            total_capacity=1.0,
            allocated=min(time_allocated, 1.5),
            available=max(0.0, 1.0 - time_allocated),
            overcommitted=time_allocated > 1.0,
        ))

        orphans = self._get_orphan_goals()
        at_risk = self._get_at_risk_work()
        attention_load = (len(orphans) + len(at_risk)) / max(self.ATTENTION_THRESHOLD, 1)
        budgets.append(ResourceBudget(
            resource_type=ResourceType.ATTENTION.value,
            total_capacity=1.0,
            allocated=min(attention_load, 1.5),
            available=max(0.0, 1.0 - attention_load),
            overcommitted=attention_load > 1.0,
        ))

        work_snap = self._get_work_snapshot()
        block_rate = work_snap.get("block_rate", 0.0)
        if isinstance(block_rate, str):
            try:
                block_rate = float(block_rate)
            except ValueError:
                block_rate = 0.0
        budgets.append(ResourceBudget(
            resource_type=ResourceType.CAPITAL.value,
            total_capacity=1.0,
            allocated=min(block_rate, 1.5),
            available=max(0.0, 1.0 - block_rate),
            overcommitted=block_rate > 0.7,
        ))

        critical_gaps = self._get_critical_gaps()
        all_gaps = self._get_all_gaps()
        gap_load = len(critical_gaps) / max(len(all_gaps), 1)
        budgets.append(ResourceBudget(
            resource_type=ResourceType.CAPABILITY_BUILDING.value,
            total_capacity=1.0,
            allocated=min(gap_load, 1.5),
            available=max(0.0, 1.0 - gap_load),
            overcommitted=gap_load > 0.8,
        ))

        velocity = self._get_work_velocity()
        cpd = velocity.get("completions_per_day", 0.0)
        total_work = work_snap.get("active_count", max(goal_count, 1))
        if isinstance(total_work, str):
            try:
                total_work = float(total_work)
            except ValueError:
                total_work = 1.0
        total_work = max(float(total_work), 1.0)
        exec_load = (total_work - cpd) / total_work
        exec_load = max(0.0, min(1.5, exec_load))
        budgets.append(ResourceBudget(
            resource_type=ResourceType.EXECUTION_CAPACITY.value,
            total_capacity=1.0,
            allocated=exec_load,
            available=max(0.0, 1.0 - exec_load),
            overcommitted=exec_load > 0.9,
        ))

        return budgets

    # ── Recommendation generation ─────────────────────────────────

    def _build_recommendations(self) -> list[AllocationRecommendation]:
        goals = self._get_roadmap_goals()
        if not goals:
            return []

        risk_forecasts = self._get_highest_risk_forecasts()
        at_risk_ids = set()
        for f in risk_forecasts:
            eid = getattr(f, "entity_id", "") if hasattr(f, "entity_id") else ""
            if eid:
                at_risk_ids.add(eid)

        confidence = self._compute_allocation_confidence()
        recs: list[AllocationRecommendation] = []

        for goal in goals:
            gid = goal.get("id", "") if isinstance(goal, dict) else getattr(goal, "id", str(goal))
            gname = goal.get("name", gid) if isinstance(goal, dict) else getattr(goal, "name", str(goal))
            gtype = goal.get("type", "goal") if isinstance(goal, dict) else "goal"

            leverage, signals = self._compute_leverage_for_goal(gid)
            is_at_risk = gid in at_risk_ids
            priority = self._classify_priority(leverage, is_at_risk)

            competing = [
                g2.get("id", "") if isinstance(g2, dict) else getattr(g2, "id", "")
                for g2 in goals
                if (g2.get("id", "") if isinstance(g2, dict) else getattr(g2, "id", "")) != gid
            ][:5]

            rationale_parts = []
            if is_at_risk:
                rationale_parts.append("at-risk trajectory")
            rationale_parts.append(f"leverage={leverage:.2f}")
            rationale_parts.append(f"confidence={confidence:.2f}")

            recs.append(AllocationRecommendation(
                recommendation_id=str(uuid.uuid4())[:8],
                resource_type=ResourceType.TIME.value,
                target_id=gid,
                target_name=gname,
                target_type=gtype,
                priority=priority.value,
                leverage_score=leverage,
                allocation_confidence=confidence,
                rationale="; ".join(rationale_parts),
                competing_targets=competing,
                source_signals=signals,
                generated_at=time.time(),
            ))

        recs.sort(key=lambda r: r.leverage_score, reverse=True)
        return recs

    # ── Public API ────────────────────────────────────────────────

    def recommend(self, resource_type: str | None = None) -> list[AllocationRecommendation]:
        recs = self._build_recommendations()
        if resource_type:
            return [r for r in recs if r.resource_type == resource_type]
        return recs

    def recommend_all(self) -> list[AllocationRecommendation]:
        return self._build_recommendations()

    def top_leverage(self, limit: int = 5) -> list[AllocationRecommendation]:
        recs = self._build_recommendations()
        return recs[:limit]

    def budgets(self) -> list[ResourceBudget]:
        return self._compute_budgets()

    def unallocated_goals(self) -> list[str]:
        goals = self._get_roadmap_goals()
        recs = self._build_recommendations()
        allocated_ids = {r.target_id for r in recs}
        unalloc: list[str] = []
        for g in goals:
            gid = g.get("id", "") if isinstance(g, dict) else getattr(g, "id", "")
            if gid and gid not in allocated_ids:
                unalloc.append(gid)
        orphans = self._get_orphan_goals()
        for o in orphans:
            oid = getattr(o, "id", str(o)) if hasattr(o, "id") else str(o)
            if oid not in allocated_ids and oid not in unalloc:
                unalloc.append(oid)
        return unalloc

    def health(self) -> AllocationHealth:
        budgets = self._compute_budgets()
        overcommitted_count = sum(1 for b in budgets if b.overcommitted)
        goals = self._get_roadmap_goals()
        recs = self._build_recommendations()
        unalloc_ratio = len(self.unallocated_goals()) / max(len(goals), 1)

        if overcommitted_count == 0 and unalloc_ratio == 0.0:
            return AllocationHealth.OPTIMIZED
        if overcommitted_count <= 1 and unalloc_ratio <= 0.2:
            return AllocationHealth.BALANCED
        if overcommitted_count <= 2 and unalloc_ratio <= 0.4:
            return AllocationHealth.CONSTRAINED
        if overcommitted_count >= 3 or unalloc_ratio > 0.6:
            return AllocationHealth.CRITICAL
        return AllocationHealth.OVERCOMMITTED

    def snapshot(self) -> AllocationSnapshot:
        recs = self._build_recommendations()
        budgets = self._compute_budgets()
        h = self.health()

        return AllocationSnapshot(
            recommendations=[r.to_dict() for r in recs],
            resource_budgets=[b.to_dict() for b in budgets],
            top_leverage_targets=[r.to_dict() for r in recs[:5]],
            overcommitted_resources=[
                b.resource_type for b in budgets if b.overcommitted
            ],
            unallocated_goals=self.unallocated_goals(),
            allocation_health=h.value,
            generated_at=time.time(),
        )

    def summary(self) -> dict[str, Any]:
        recs = self._build_recommendations()
        budgets = self._compute_budgets()
        h = self.health()

        return {
            "recommendation_count": len(recs),
            "allocation_health": h.value,
            "overcommitted_resources": [
                b.resource_type for b in budgets if b.overcommitted
            ],
            "top_priority": recs[0].priority if recs else "none",
            "top_leverage": round(recs[0].leverage_score, 4) if recs else 0.0,
            "average_confidence": round(
                sum(r.allocation_confidence for r in recs) / max(len(recs), 1), 4
            ),
            "unallocated_goal_count": len(self.unallocated_goals()),
        }
