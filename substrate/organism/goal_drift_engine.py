"""Goal Drift Engine — detect movement away from objectives.

Campaign 8.5. UMH substrate layer. Instance-agnostic.

Detects four drift types:
  - Activity Drift: lots of work, no progress
  - Alignment Drift: work not connected to goals
  - Outcome Drift: goals with no active execution
  - Planning Drift: plan not advancing

Read-only. No mutation. Deterministic. Zero LLM calls.
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


class GoalDriftType(str, Enum):
    ACTIVITY_DRIFT = "activity_drift"
    ALIGNMENT_DRIFT = "alignment_drift"
    OUTCOME_DRIFT = "outcome_drift"
    PLANNING_DRIFT = "planning_drift"


@dataclass
class GoalDriftWarning:
    drift_id: str = field(default_factory=lambda: f"gd-{uuid4().hex[:8]}")
    goal_id: str = ""
    goal_title: str = ""
    drift_type: str = GoalDriftType.ACTIVITY_DRIFT.value
    severity: str = "medium"
    description: str = ""
    evidence: list[str] = field(default_factory=list)
    detected_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "drift_id": self.drift_id,
            "goal_id": self.goal_id,
            "goal_title": self.goal_title,
            "drift_type": self.drift_type,
            "severity": self.severity,
            "description": self.description,
            "evidence": self.evidence,
            "detected_at": self.detected_at,
        }


@dataclass
class GoalDriftSnapshot:
    warnings: list[dict[str, Any]] = field(default_factory=list)
    high_drift_count: int = 0
    drift_by_type: dict[str, int] = field(default_factory=dict)
    overall_drift_health: str = "healthy"
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "warnings": self.warnings,
            "warning_count": len(self.warnings),
            "high_drift_count": self.high_drift_count,
            "drift_by_type": self.drift_by_type,
            "overall_drift_health": self.overall_drift_health,
            "generated_at": self.generated_at,
        }


# ── Engine ────────────────────────────────────────────────────────────────


class GoalDriftEngine:
    """Detect goal drift. Read-only.

    Composes:
      - GoalRegistry (Phase 4) — goal data
      - GoalHierarchyEngine (C8.1) — tree structure
      - OutcomeTrackingRuntime (C8.2) — progress measurement
      - GoalAlignmentEngine (C8.4) — alignment scoring
      - StrategicPlanningEngine (C8.3) — plan status
    """

    def __init__(
        self,
        goal_registry: Any | None = None,
        goal_hierarchy: Any | None = None,
        outcome_tracking: Any | None = None,
        alignment_engine: Any | None = None,
        planning_engine: Any | None = None,
    ) -> None:
        self._registry = goal_registry
        self._hierarchy = goal_hierarchy
        self._outcomes = outcome_tracking
        self._alignment = alignment_engine
        self._planning = planning_engine

    def _detect_activity_drift(self) -> list[GoalDriftWarning]:
        """Lots of work, no progress."""
        warnings: list[GoalDriftWarning] = []
        if self._registry is None or self._outcomes is None:
            return warnings

        for goal in self._registry.active_goals():
            try:
                prog = self._outcomes.progress(goal.goal_id)
                if prog.active_work_count >= 3 and prog.percent_complete < 0.1:
                    severity = "high" if prog.active_work_count >= 5 else "medium"
                    warnings.append(GoalDriftWarning(
                        goal_id=goal.goal_id,
                        goal_title=goal.title,
                        drift_type=GoalDriftType.ACTIVITY_DRIFT.value,
                        severity=severity,
                        description=f"{prog.active_work_count} active work items but only {prog.percent_complete:.0%} progress",
                        evidence=[
                            f"active_work_count={prog.active_work_count}",
                            f"percent_complete={prog.percent_complete:.4f}",
                        ],
                    ))
            except Exception as exc:
                logger.debug("drift: activity check failed for %s: %s", goal.goal_id, exc)

        return warnings

    def _detect_alignment_drift(self) -> list[GoalDriftWarning]:
        """Work not connected to goals."""
        warnings: list[GoalDriftWarning] = []
        if self._alignment is None:
            return warnings

        try:
            score = self._alignment.alignment_score()
            if score < 0.5:
                severity = "critical" if score < 0.25 else "high"
                unlinked = self._alignment.unlinked_work()
                warnings.append(GoalDriftWarning(
                    goal_id="system",
                    goal_title="System-wide alignment",
                    drift_type=GoalDriftType.ALIGNMENT_DRIFT.value,
                    severity=severity,
                    description=f"Only {score:.0%} of work is linked to goals ({len(unlinked)} unlinked items)",
                    evidence=[
                        f"alignment_score={score:.4f}",
                        f"unlinked_count={len(unlinked)}",
                    ],
                ))
        except Exception as exc:
            logger.debug("drift: alignment check failed: %s", exc)

        return warnings

    def _detect_outcome_drift(self) -> list[GoalDriftWarning]:
        """Goals with no active execution."""
        warnings: list[GoalDriftWarning] = []
        if self._registry is None or self._outcomes is None:
            return warnings

        for goal in self._registry.active_goals():
            try:
                prog = self._outcomes.progress(goal.goal_id)
                if prog.active_work_count == 0 and prog.percent_complete < 1.0:
                    severity = "high" if prog.percent_complete < 0.25 else "medium"
                    warnings.append(GoalDriftWarning(
                        goal_id=goal.goal_id,
                        goal_title=goal.title,
                        drift_type=GoalDriftType.OUTCOME_DRIFT.value,
                        severity=severity,
                        description=f"Active goal with {prog.percent_complete:.0%} progress but no active work",
                        evidence=[
                            f"percent_complete={prog.percent_complete:.4f}",
                            f"active_work_count=0",
                        ],
                    ))
            except Exception as exc:
                logger.debug("drift: outcome check failed for %s: %s", goal.goal_id, exc)

        return warnings

    def _detect_planning_drift(self) -> list[GoalDriftWarning]:
        """Plan not advancing."""
        warnings: list[GoalDriftWarning] = []
        if self._registry is None or self._planning is None:
            return warnings

        for goal in self._registry.active_goals():
            try:
                from substrate.organism.strategic_planning_engine import PlanningStatus
                status = self._planning.status(goal.goal_id)
                if status == PlanningStatus.BLOCKED:
                    warnings.append(GoalDriftWarning(
                        goal_id=goal.goal_id,
                        goal_title=goal.title,
                        drift_type=GoalDriftType.PLANNING_DRIFT.value,
                        severity="high",
                        description=f"Plan for '{goal.title}' is BLOCKED",
                        evidence=[f"planning_status={status.value}"],
                    ))
                elif status == PlanningStatus.NOT_STARTED:
                    warnings.append(GoalDriftWarning(
                        goal_id=goal.goal_id,
                        goal_title=goal.title,
                        drift_type=GoalDriftType.PLANNING_DRIFT.value,
                        severity="medium",
                        description=f"Active goal '{goal.title}' has no plan progress",
                        evidence=[f"planning_status={status.value}"],
                    ))
            except Exception as exc:
                logger.debug("drift: planning check failed for %s: %s", goal.goal_id, exc)

        return warnings

    def detect(self) -> list[GoalDriftWarning]:
        """All drift warnings across all types."""
        warnings: list[GoalDriftWarning] = []
        warnings.extend(self._detect_activity_drift())
        warnings.extend(self._detect_alignment_drift())
        warnings.extend(self._detect_outcome_drift())
        warnings.extend(self._detect_planning_drift())
        return warnings

    def high_drift(self) -> list[GoalDriftWarning]:
        """Critical and high severity only."""
        return [w for w in self.detect() if w.severity in ("critical", "high")]

    def drift_for_goal(self, goal_id: str) -> list[GoalDriftWarning]:
        """Drift warnings for a single goal."""
        return [w for w in self.detect() if w.goal_id == goal_id]

    def summary(self) -> GoalDriftSnapshot:
        """Aggregated drift snapshot."""
        warnings = self.detect()
        by_type: dict[str, int] = {}
        high_count = 0

        for w in warnings:
            by_type[w.drift_type] = by_type.get(w.drift_type, 0) + 1
            if w.severity in ("critical", "high"):
                high_count += 1

        if any(w.severity == "critical" for w in warnings):
            health = "critical"
        elif high_count > 0:
            health = "degraded"
        elif warnings:
            health = "watch"
        else:
            health = "healthy"

        return GoalDriftSnapshot(
            warnings=[w.to_dict() for w in warnings],
            high_drift_count=high_count,
            drift_by_type=by_type,
            overall_drift_health=health,
            generated_at=time.time(),
        )
