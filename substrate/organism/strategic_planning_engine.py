"""Strategic Planning Engine — generate plans linking current reality to goals.

Campaign 8.3. UMH substrate layer. Instance-agnostic.

This is the most important runtime in Campaign 8. It generates
deterministic strategic plans by composing goal hierarchy, outcome
tracking, priority/risk/recommendation engines, and the reality graph.

Read-only. No mutation. No execution authority. Deterministic. Zero LLM.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────


class PlanningStatus(str, Enum):
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    BLOCKED = "blocked"
    NOT_STARTED = "not_started"


@dataclass
class StrategicMilestone:
    milestone_id: str = field(default_factory=lambda: f"ms-{uuid4().hex[:8]}")
    title: str = ""
    goal_id: str = ""
    status: str = PlanningStatus.NOT_STARTED.value
    dependencies: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    percent_complete: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "milestone_id": self.milestone_id,
            "title": self.title,
            "goal_id": self.goal_id,
            "status": self.status,
            "dependencies": self.dependencies,
            "evidence": self.evidence,
            "percent_complete": round(self.percent_complete, 4),
        }


@dataclass
class StrategicPlan:
    plan_id: str = field(default_factory=lambda: f"plan-{uuid4().hex[:8]}")
    goal_id: str = ""
    goal_title: str = ""
    goal_type: str = ""
    status: str = PlanningStatus.NOT_STARTED.value
    current_state: dict[str, Any] = field(default_factory=dict)
    desired_state: dict[str, Any] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)
    milestones: list[dict[str, Any]] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    child_plans: list[dict[str, Any]] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "goal_id": self.goal_id,
            "goal_title": self.goal_title,
            "goal_type": self.goal_type,
            "status": self.status,
            "current_state": self.current_state,
            "desired_state": self.desired_state,
            "blockers": self.blockers,
            "milestones": self.milestones,
            "recommended_actions": self.recommended_actions,
            "risk_factors": self.risk_factors,
            "child_plans": self.child_plans,
            "generated_at": self.generated_at,
        }


# ── Engine ────────────────────────────────────────────────────────────────


class StrategicPlanningEngine:
    """Generate deterministic strategic plans.

    Read-only. Composes:
      - GoalRegistry (Phase 4) — goal data
      - GoalHierarchyEngine (C8.1) — tree structure
      - OutcomeTrackingRuntime (C8.2) — progress measurement
      - PriorityEngine (C7.1) — priority scoring
      - RiskEngine (C7.2) — risk assessment
      - RecommendationEngine (C7.3) — action recommendations
      - RealityGraph (C5) — entity topology
    """

    def __init__(
        self,
        goal_registry: Any | None = None,
        goal_hierarchy: Any | None = None,
        outcome_tracking: Any | None = None,
        priority_engine: Any | None = None,
        risk_engine: Any | None = None,
        recommendation_engine: Any | None = None,
        reality_graph: Any | None = None,
    ) -> None:
        self._registry = goal_registry
        self._hierarchy = goal_hierarchy
        self._outcomes = outcome_tracking
        self._priority = priority_engine
        self._risk = risk_engine
        self._recommendation = recommendation_engine
        self._reality = reality_graph

    def _goal_type_value(self, goal: Any) -> str:
        gt = goal.goal_type
        return gt.value if hasattr(gt, "value") else str(gt)

    def _current_state(self, goal_id: str) -> dict[str, Any]:
        """Derive current state from outcome tracking and reality graph."""
        state: dict[str, Any] = {}

        if self._outcomes is not None:
            try:
                prog = self._outcomes.progress(goal_id)
                state["percent_complete"] = prog.percent_complete
                state["criteria_met"] = prog.criteria_met
                state["criteria_total"] = prog.criteria_total
                state["active_work"] = prog.active_work_count
                state["blocked_work"] = prog.blocker_count
                state["health"] = prog.health
            except Exception as exc:
                logger.debug("planning: outcome query failed: %s", exc)

        if self._reality is not None:
            try:
                from substrate.organism.reality_graph import RealityEntityType
                projects = self._reality.find_by_type(RealityEntityType.PROJECT)
                state["active_projects"] = len([
                    p for p in projects
                    if p.status.value == "active"
                    or (hasattr(p.status, "value") and p.status.value == "active")
                ])
            except Exception as exc:
                logger.debug("planning: reality graph query failed: %s", exc)

        return state

    def _desired_state(self, goal: Any) -> dict[str, Any]:
        """Derive desired state from goal definition."""
        state: dict[str, Any] = {
            "percent_complete": 1.0,
            "all_criteria_met": True,
        }
        if goal.target_date:
            state["target_date"] = goal.target_date
        if goal.success_criteria:
            state["criteria"] = [
                {"description": c.description, "target": c.target_value}
                for c in goal.success_criteria
            ]
        return state

    def _blockers_for(self, goal_id: str) -> list[str]:
        """Derive blockers from outcome tracking and dependencies."""
        blockers: list[str] = []

        if self._registry is not None:
            goal = self._registry.get(goal_id)
            if goal and goal.dependencies:
                for dep_id in goal.dependencies:
                    dep = self._registry.get(dep_id)
                    if dep and dep.status.value not in ("completed",):
                        blockers.append(f"Depends on incomplete: {dep.title}")

        if self._outcomes is not None:
            try:
                prog = self._outcomes.progress(goal_id)
                if prog.blocker_count > 0:
                    blockers.append(f"{prog.blocker_count} blocked work items")
            except Exception:
                pass

        return blockers

    def _risks_for(self, goal_id: str) -> list[str]:
        """Derive risks from risk engine."""
        risks: list[str] = []
        if self._risk is not None:
            try:
                risk_data = self._risk.risks()
                for r in risk_data:
                    refs = r.entity_refs if hasattr(r, "entity_refs") else []
                    if goal_id in refs:
                        title = r.title if hasattr(r, "title") else str(r)
                        risks.append(title)
            except Exception as exc:
                logger.debug("planning: risk query failed: %s", exc)
        return risks

    def _recommendations_for(self, goal_id: str) -> list[str]:
        """Derive recommendations from recommendation engine."""
        recs: list[str] = []
        if self._recommendation is not None:
            try:
                rec_data = self._recommendation.recommendations()
                for r in rec_data:
                    refs = r.entity_refs if hasattr(r, "entity_refs") else []
                    if goal_id in refs:
                        action = r.action if hasattr(r, "action") else str(r)
                        recs.append(action)
            except Exception as exc:
                logger.debug("planning: recommendation query failed: %s", exc)
        return recs

    def _classify_status(
        self, progress_pct: float, blocker_count: int, has_work: bool
    ) -> PlanningStatus:
        """Deterministic status classification."""
        if blocker_count > 0:
            return PlanningStatus.BLOCKED
        if not has_work and progress_pct == 0.0:
            return PlanningStatus.NOT_STARTED
        if progress_pct < 0.5:
            return PlanningStatus.AT_RISK
        return PlanningStatus.ON_TRACK

    def milestones(self, goal_id: str) -> list[StrategicMilestone]:
        """Derive milestones from child goals."""
        if self._registry is None:
            return []

        children = self._registry.children_of(goal_id)
        milestones: list[StrategicMilestone] = []

        for child in children:
            pct = child.completion_ratio()
            if pct >= 1.0:
                status = PlanningStatus.ON_TRACK.value
            elif pct > 0:
                status = PlanningStatus.AT_RISK.value
            else:
                status = PlanningStatus.NOT_STARTED.value

            ms = StrategicMilestone(
                title=child.title,
                goal_id=child.goal_id,
                status=status,
                dependencies=child.dependencies,
                percent_complete=pct,
            )
            milestones.append(ms)

        return milestones

    def generate_plan(self, goal_id: str) -> StrategicPlan:
        """Generate a strategic plan for a single goal."""
        if self._registry is None:
            return StrategicPlan(goal_id=goal_id)

        goal = self._registry.get(goal_id)
        if not goal:
            return StrategicPlan(goal_id=goal_id)

        current = self._current_state(goal_id)
        desired = self._desired_state(goal)
        blockers = self._blockers_for(goal_id)
        risks = self._risks_for(goal_id)
        recs = self._recommendations_for(goal_id)
        ms = self.milestones(goal_id)

        pct = current.get("percent_complete", 0.0)
        has_work = current.get("active_work", 0) > 0
        status = self._classify_status(pct, len(blockers), has_work)

        child_plans: list[dict[str, Any]] = []
        children = self._registry.children_of(goal_id)
        for child in children:
            cp = self.generate_plan(child.goal_id)
            child_plans.append({
                "goal_id": cp.goal_id,
                "goal_title": cp.goal_title,
                "status": cp.status,
            })

        return StrategicPlan(
            goal_id=goal_id,
            goal_title=goal.title,
            goal_type=self._goal_type_value(goal),
            status=status.value,
            current_state=current,
            desired_state=desired,
            blockers=blockers,
            milestones=[m.to_dict() for m in ms],
            recommended_actions=recs,
            risk_factors=risks,
            child_plans=child_plans,
            generated_at=time.time(),
        )

    def status(self, goal_id: str) -> PlanningStatus:
        """Deterministic planning status for a goal."""
        plan = self.generate_plan(goal_id)
        return PlanningStatus(plan.status)

    def roadmap(self) -> dict[str, Any]:
        """All active goals with plans, ordered by priority."""
        if self._registry is None:
            return {"plans": [], "generated_at": time.time()}

        active = self._registry.active_goals()
        plans: list[dict[str, Any]] = []

        for goal in active:
            plan = self.generate_plan(goal.goal_id)
            plans.append(plan.to_dict())

        plans.sort(key=lambda p: {
            PlanningStatus.BLOCKED.value: 0,
            PlanningStatus.AT_RISK.value: 1,
            PlanningStatus.ON_TRACK.value: 2,
            PlanningStatus.NOT_STARTED.value: 3,
        }.get(p.get("status", ""), 4))

        return {
            "plans": plans,
            "total": len(plans),
            "blocked": sum(1 for p in plans if p["status"] == PlanningStatus.BLOCKED.value),
            "at_risk": sum(1 for p in plans if p["status"] == PlanningStatus.AT_RISK.value),
            "on_track": sum(1 for p in plans if p["status"] == PlanningStatus.ON_TRACK.value),
            "not_started": sum(1 for p in plans if p["status"] == PlanningStatus.NOT_STARTED.value),
            "generated_at": time.time(),
        }

    def snapshot(self) -> dict[str, Any]:
        """Full planning state."""
        return self.roadmap()
