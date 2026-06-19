"""Outcome Tracking Runtime — measure progress toward goals.

Campaign 8.2. UMH substrate layer. Instance-agnostic.

Consumes GoalRegistry (read-only), GoalHierarchyEngine, RealityGraph,
RuntimeAwarenessRuntime. Produces progress snapshots per goal.

Read-only. No mutation. Deterministic. Zero LLM calls.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────


@dataclass
class OutcomeProgress:
    goal_id: str = ""
    title: str = ""
    goal_type: str = ""
    percent_complete: float = 0.0
    criteria_met: int = 0
    criteria_total: int = 0
    active_work_count: int = 0
    completed_work_count: int = 0
    blocker_count: int = 0
    child_progress: list[dict[str, Any]] = field(default_factory=list)
    health: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "title": self.title,
            "goal_type": self.goal_type,
            "percent_complete": round(self.percent_complete, 4),
            "criteria_met": self.criteria_met,
            "criteria_total": self.criteria_total,
            "active_work_count": self.active_work_count,
            "completed_work_count": self.completed_work_count,
            "blocker_count": self.blocker_count,
            "child_progress": self.child_progress,
            "health": self.health,
        }


@dataclass
class OutcomeSnapshot:
    goals: list[dict[str, Any]] = field(default_factory=list)
    overall_health: str = "unknown"
    total_active: int = 0
    total_completed: int = 0
    total_blocked: int = 0
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "goals": self.goals,
            "overall_health": self.overall_health,
            "total_active": self.total_active,
            "total_completed": self.total_completed,
            "total_blocked": self.total_blocked,
            "generated_at": self.generated_at,
        }


# ── Health thresholds ─────────────────────────────────────────────────────

_HEALTH_THRESHOLDS = {
    "critical": 0.0,
    "degraded": 0.25,
    "watch": 0.50,
    "healthy": 0.75,
}


# ── Runtime ───────────────────────────────────────────────────────────────


class OutcomeTrackingRuntime:
    """Measure progress toward goals. Read-only facade.

    Composes:
      - GoalRegistry (Phase 4) — goal data, success criteria
      - GoalHierarchyEngine (C8.1) — tree traversal
      - RealityGraph (C5) — work packet entities
      - RuntimeAwarenessRuntime (C6.3) — active/blocked work
    """

    def __init__(
        self,
        goal_registry: Any | None = None,
        goal_hierarchy: Any | None = None,
        reality_graph: Any | None = None,
        runtime_awareness: Any | None = None,
    ) -> None:
        self._registry = goal_registry
        self._hierarchy = goal_hierarchy
        self._reality = reality_graph
        self._runtime = runtime_awareness

    def completion(self, goal_id: str) -> float:
        """0-1 completion ratio from success criteria."""
        if self._registry is None:
            return 0.0
        goal = self._registry.get(goal_id)
        if not goal:
            return 0.0
        return goal.completion_ratio()

    def _classify_health(self, progress: OutcomeProgress) -> str:
        """Deterministic health from progress and blockers."""
        if progress.blocker_count > 0:
            return "critical" if progress.blocker_count >= 3 else "degraded"
        pct = progress.percent_complete
        if pct >= _HEALTH_THRESHOLDS["healthy"]:
            return "healthy"
        if pct >= _HEALTH_THRESHOLDS["watch"]:
            return "watch"
        if pct >= _HEALTH_THRESHOLDS["degraded"]:
            return "degraded"
        return "critical"

    def _work_counts(self, goal_id: str) -> tuple[int, int, int]:
        """(active, completed, blocked) work counts for a goal."""
        active = 0
        completed = 0
        blocked = 0

        if self._reality is not None:
            try:
                from substrate.organism.reality_graph import RealityEntityType
                packets = self._reality.find_by_type(RealityEntityType.WORK_PACKET)
                for p in packets:
                    refs = p.properties.get("goal_refs", [])
                    if goal_id in refs or p.properties.get("goal_id") == goal_id:
                        status = p.status.value if hasattr(p.status, "value") else str(p.status)
                        if status == "active":
                            active += 1
                        elif status in ("inactive", "unknown"):
                            completed += 1
            except Exception as exc:
                logger.debug("outcome: reality graph query failed: %s", exc)

        if self._runtime is not None:
            try:
                snap = self._runtime.snapshot()
                for wp in getattr(snap, "blocked_work", []):
                    wp_goal = wp.get("goal_id", "") if isinstance(wp, dict) else ""
                    if wp_goal == goal_id:
                        blocked += 1
            except Exception as exc:
                logger.debug("outcome: runtime awareness query failed: %s", exc)

        return active, completed, blocked

    def progress(self, goal_id: str) -> OutcomeProgress:
        """Single goal progress."""
        if self._registry is None:
            return OutcomeProgress(goal_id=goal_id)

        goal = self._registry.get(goal_id)
        if not goal:
            return OutcomeProgress(goal_id=goal_id)

        criteria_met = sum(1 for c in goal.success_criteria if c.met)
        criteria_total = len(goal.success_criteria)
        pct = goal.completion_ratio()

        active, completed, blocked = self._work_counts(goal_id)

        child_progress: list[dict[str, Any]] = []
        if self._hierarchy is not None:
            try:
                children = self._registry.children_of(goal_id)
                for child in children:
                    cp = self.progress(child.goal_id)
                    child_progress.append(cp.to_dict())
            except Exception as exc:
                logger.debug("outcome: child progress failed: %s", exc)

        prog = OutcomeProgress(
            goal_id=goal_id,
            title=goal.title,
            goal_type=goal.goal_type.value if hasattr(goal.goal_type, "value") else str(goal.goal_type),
            percent_complete=pct,
            criteria_met=criteria_met,
            criteria_total=criteria_total,
            active_work_count=active,
            completed_work_count=completed,
            blocker_count=blocked,
            child_progress=child_progress,
        )
        prog.health = self._classify_health(prog)
        return prog

    def health(self, goal_id: str) -> str:
        """Deterministic health classification for a single goal."""
        return self.progress(goal_id).health

    def goals_at_risk(self) -> list[OutcomeProgress]:
        """Goals with health below 'healthy'."""
        if self._registry is None:
            return []
        results: list[OutcomeProgress] = []
        for goal in self._registry.active_goals():
            prog = self.progress(goal.goal_id)
            if prog.health in ("critical", "degraded", "watch"):
                results.append(prog)
        return results

    def snapshot(self) -> OutcomeSnapshot:
        """All active goals with progress."""
        snap = OutcomeSnapshot(generated_at=time.time())
        if self._registry is None:
            return snap

        active_goals = self._registry.active_goals()
        total_blocked = 0

        for goal in active_goals:
            prog = self.progress(goal.goal_id)
            snap.goals.append(prog.to_dict())
            total_blocked += prog.blocker_count

        snap.total_active = len(active_goals)
        try:
            from substrate.organism.strategic_gap_engine import GoalStatus
            completed = self._registry.goals_by_status(GoalStatus.COMPLETED)
            snap.total_completed = len(completed)
        except Exception:
            snap.total_completed = 0
        snap.total_blocked = total_blocked

        healths = [g.get("health", "unknown") for g in snap.goals]
        if any(h == "critical" for h in healths):
            snap.overall_health = "critical"
        elif any(h == "degraded" for h in healths):
            snap.overall_health = "degraded"
        elif any(h == "watch" for h in healths):
            snap.overall_health = "watch"
        elif healths:
            snap.overall_health = "healthy"

        return snap
