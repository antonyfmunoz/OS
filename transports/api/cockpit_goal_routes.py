"""Cockpit routes for Goal Systems & Strategic Planning — Campaign 8.6.

Exposes goal registry, hierarchy, outcome tracking, strategic planning,
alignment, and drift detection to the cockpit frontend.
14 endpoints under /goals/ prefix. Read-only except GoalRegistry mutation.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_goal_registry: Any = None
_goal_hierarchy: Any = None
_outcome_tracking: Any = None
_planning_engine: Any = None
_alignment_engine: Any = None
_drift_engine: Any = None


def _get_registry() -> Any:
    global _goal_registry
    if _goal_registry is None:
        from substrate.organism.strategic_gap_engine import GoalRegistry
        _goal_registry = GoalRegistry()
    return _goal_registry


def _get_hierarchy() -> Any:
    global _goal_hierarchy
    if _goal_hierarchy is None:
        from substrate.organism.goal_hierarchy_engine import GoalHierarchyEngine
        _goal_hierarchy = GoalHierarchyEngine(goal_registry=_get_registry())
    return _goal_hierarchy


def _get_outcome_tracking() -> Any:
    global _outcome_tracking
    if _outcome_tracking is None:
        from substrate.organism.outcome_tracking_runtime import OutcomeTrackingRuntime
        _outcome_tracking = OutcomeTrackingRuntime(
            goal_registry=_get_registry(),
            goal_hierarchy=_get_hierarchy(),
        )
    return _outcome_tracking


def _get_planning_engine() -> Any:
    global _planning_engine
    if _planning_engine is None:
        from substrate.organism.strategic_planning_engine import StrategicPlanningEngine
        _planning_engine = StrategicPlanningEngine(
            goal_registry=_get_registry(),
            goal_hierarchy=_get_hierarchy(),
            outcome_tracking=_get_outcome_tracking(),
        )
    return _planning_engine


def _get_alignment_engine() -> Any:
    global _alignment_engine
    if _alignment_engine is None:
        from substrate.organism.goal_alignment_engine import GoalAlignmentEngine
        _alignment_engine = GoalAlignmentEngine(
            goal_registry=_get_registry(),
            goal_hierarchy=_get_hierarchy(),
        )
    return _alignment_engine


def _get_drift_engine() -> Any:
    global _drift_engine
    if _drift_engine is None:
        from substrate.organism.goal_drift_engine import GoalDriftEngine
        _drift_engine = GoalDriftEngine(
            goal_registry=_get_registry(),
            goal_hierarchy=_get_hierarchy(),
            outcome_tracking=_get_outcome_tracking(),
            alignment_engine=_get_alignment_engine(),
            planning_engine=_get_planning_engine(),
        )
    return _drift_engine


def configure(
    goal_registry: Any = None,
    goal_hierarchy: Any = None,
    outcome_tracking: Any = None,
    planning_engine: Any = None,
    alignment_engine: Any = None,
    drift_engine: Any = None,
) -> None:
    """Override lazy singletons for testing."""
    global _goal_registry, _goal_hierarchy, _outcome_tracking
    global _planning_engine, _alignment_engine, _drift_engine
    if goal_registry is not None:
        _goal_registry = goal_registry
    if goal_hierarchy is not None:
        _goal_hierarchy = goal_hierarchy
    if outcome_tracking is not None:
        _outcome_tracking = outcome_tracking
    if planning_engine is not None:
        _planning_engine = planning_engine
    if alignment_engine is not None:
        _alignment_engine = alignment_engine
    if drift_engine is not None:
        _drift_engine = drift_engine


def get_router() -> Any:
    from fastapi import APIRouter

    router = APIRouter(prefix="/goals", tags=["goals"])

    @router.get("/")
    def list_goals() -> dict[str, Any]:
        goals = _get_registry().all_goals()
        return {"goals": [g.to_dict() for g in goals], "total": len(goals)}

    @router.get("/active")
    def active_goals() -> dict[str, Any]:
        goals = _get_registry().active_goals()
        return {"goals": [g.to_dict() for g in goals], "total": len(goals)}

    @router.get("/tree")
    def goal_tree() -> dict[str, Any]:
        return _get_hierarchy().tree()

    @router.get("/hierarchy/summary")
    def hierarchy_summary() -> dict[str, Any]:
        return _get_hierarchy().summary()

    @router.get("/hierarchy/validate")
    def hierarchy_validate() -> dict[str, Any]:
        return _get_hierarchy().validate_hierarchy().to_dict()

    @router.get("/{goal_id}")
    def get_goal(goal_id: str) -> dict[str, Any]:
        goal = _get_registry().get(goal_id)
        if not goal:
            return {"error": "not_found", "goal_id": goal_id}
        return goal.to_dict()

    @router.get("/{goal_id}/trace")
    def trace_goal(goal_id: str) -> dict[str, Any]:
        chain = _get_hierarchy().trace_to_vision(goal_id)
        return {"goal_id": goal_id, "chain": chain, "depth": len(chain)}

    @router.get("/plans/roadmap")
    def roadmap() -> dict[str, Any]:
        return _get_planning_engine().roadmap()

    @router.get("/plans/{goal_id}")
    def get_plan(goal_id: str) -> dict[str, Any]:
        plan = _get_planning_engine().generate_plan(goal_id)
        return plan.to_dict()

    @router.get("/alignment/report")
    def alignment_report() -> dict[str, Any]:
        return _get_alignment_engine().report().to_dict()

    @router.get("/alignment/unlinked")
    def unlinked_work() -> dict[str, Any]:
        items = _get_alignment_engine().unlinked_work()
        return {"unlinked": items, "count": len(items)}

    @router.get("/alignment/trace/{work_id}")
    def trace_work(work_id: str) -> dict[str, Any]:
        chain = _get_alignment_engine().goal_for_work(work_id)
        return {"work_id": work_id, "chain": chain, "depth": len(chain)}

    @router.get("/outcomes/snapshot")
    def outcomes_snapshot() -> dict[str, Any]:
        return _get_outcome_tracking().snapshot().to_dict()

    @router.get("/outcomes/{goal_id}")
    def goal_outcome(goal_id: str) -> dict[str, Any]:
        return _get_outcome_tracking().progress(goal_id).to_dict()

    @router.get("/drift/summary")
    def drift_summary() -> dict[str, Any]:
        return _get_drift_engine().summary().to_dict()

    @router.get("/drift/high")
    def drift_high() -> dict[str, Any]:
        high = _get_drift_engine().high_drift()
        return {"warnings": [w.to_dict() for w in high], "count": len(high)}

    return router
