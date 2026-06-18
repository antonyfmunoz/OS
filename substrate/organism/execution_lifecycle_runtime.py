"""Execution Lifecycle Runtime — Campaign 16.2.

Retrospective layer composing outcome, learning, pattern, and evolution
runtimes into a unified lifecycle arc: what happened, what was learned,
what compounded.

Read-only. Deterministic. No LLM calls.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Enums ───────────────────────────────────────────────────────────


class LifecycleStage(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    LEARNING = "learning"
    COMPOUNDED = "compounded"


# ── Dataclasses ─────────────────────────────────────────────────────


@dataclass
class LifecycleArc:
    goal_id: str = ""
    stage: str = LifecycleStage.NOT_STARTED.value
    completion_pct: float = 0.0
    lessons_extracted: int = 0
    patterns_detected: int = 0
    capabilities_evolved: int = 0
    outcome_health: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "stage": self.stage,
            "completion_pct": self.completion_pct,
            "lessons_extracted": self.lessons_extracted,
            "patterns_detected": self.patterns_detected,
            "capabilities_evolved": self.capabilities_evolved,
            "outcome_health": self.outcome_health,
        }


@dataclass
class ExecutionLifecycleSnapshot:
    arcs: list[dict[str, Any]] = field(default_factory=list)
    total_lessons: int = 0
    total_patterns: int = 0
    advancing_capabilities: int = 0
    declining_capabilities: int = 0
    overall_stage: str = LifecycleStage.NOT_STARTED.value
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "arcs": self.arcs,
            "total_lessons": self.total_lessons,
            "total_patterns": self.total_patterns,
            "advancing_capabilities": self.advancing_capabilities,
            "declining_capabilities": self.declining_capabilities,
            "overall_stage": self.overall_stage,
            "generated_at": self.generated_at,
        }


# ── Runtime ─────────────────────────────────────────────────────────


class ExecutionLifecycleRuntime:
    """Execution lifecycle — outcome to lesson to compounding arc.

    Composes 4 subsystems:
    - OutcomeTrackingRuntime: goal completion tracking
    - LearningExtractionRuntime: lesson extraction from outcomes
    - OutcomePatternEngine: recurring pattern detection
    - CapabilityEvolutionEngine: capability growth/decline tracking

    Read-only retrospective. No mutation.
    """

    def __init__(
        self,
        outcome_tracking: Any | None = None,
        learning_extraction: Any | None = None,
        outcome_patterns: Any | None = None,
        capability_evolution: Any | None = None,
    ) -> None:
        self._outcome_tracking_dep = outcome_tracking
        self._learning_extraction_dep = learning_extraction
        self._outcome_patterns_dep = outcome_patterns
        self._capability_evolution_dep = capability_evolution

    # ── Lazy subsystem access ───────────────────────────────────────

    @property
    def _outcome_tracking(self) -> Any | None:
        if self._outcome_tracking_dep is not None:
            return self._outcome_tracking_dep
        try:
            from substrate.organism.outcome_tracking_runtime import (
                OutcomeTrackingRuntime,
            )

            self._outcome_tracking_dep = OutcomeTrackingRuntime()
        except Exception as exc:
            logger.debug("execution_lifecycle: outcome_tracking init failed: %s", exc)
        return self._outcome_tracking_dep

    @property
    def _learning_extraction(self) -> Any | None:
        if self._learning_extraction_dep is not None:
            return self._learning_extraction_dep
        try:
            from substrate.organism.learning_extraction_runtime import (
                LearningExtractionRuntime,
            )

            self._learning_extraction_dep = LearningExtractionRuntime()
        except Exception as exc:
            logger.debug(
                "execution_lifecycle: learning_extraction init failed: %s", exc
            )
        return self._learning_extraction_dep

    @property
    def _outcome_patterns(self) -> Any | None:
        if self._outcome_patterns_dep is not None:
            return self._outcome_patterns_dep
        try:
            from substrate.organism.outcome_pattern_engine import (
                OutcomePatternEngine,
            )

            self._outcome_patterns_dep = OutcomePatternEngine()
        except Exception as exc:
            logger.debug("execution_lifecycle: outcome_patterns init failed: %s", exc)
        return self._outcome_patterns_dep

    @property
    def _capability_evolution(self) -> Any | None:
        if self._capability_evolution_dep is not None:
            return self._capability_evolution_dep
        try:
            from substrate.organism.capability_evolution_engine import (
                CapabilityEvolutionEngine,
            )

            self._capability_evolution_dep = CapabilityEvolutionEngine()
        except Exception as exc:
            logger.debug(
                "execution_lifecycle: capability_evolution init failed: %s", exc
            )
        return self._capability_evolution_dep

    # ── Goal enumeration ────────────────────────────────────────────

    def _get_tracked_goal_ids(self) -> list[str]:
        try:
            if self._outcome_tracking is not None:
                snap = self._outcome_tracking.snapshot()
                if hasattr(snap, "to_dict"):
                    d = snap.to_dict()
                    goals = d.get("goals", d.get("tracked_goals", []))
                    return [
                        g.get("goal_id", g) if isinstance(g, dict) else str(g)
                        for g in goals
                    ]
                if hasattr(snap, "goals"):
                    return [
                        getattr(g, "goal_id", str(g))
                        for g in snap.goals
                    ]
        except Exception as exc:
            logger.debug("execution_lifecycle: goal enumeration failed: %s", exc)
        return []

    def _get_completion(self, goal_id: str) -> float:
        try:
            if self._outcome_tracking is not None:
                return self._outcome_tracking.completion(goal_id)
        except Exception as exc:
            logger.debug("execution_lifecycle: completion(%s) failed: %s", goal_id, exc)
        return 0.0

    def _get_outcome_health(self, goal_id: str) -> str:
        try:
            if self._outcome_tracking is not None:
                h = self._outcome_tracking.health(goal_id)
                return h if isinstance(h, str) else getattr(h, "value", str(h))
        except Exception as exc:
            logger.debug(
                "execution_lifecycle: outcome_health(%s) failed: %s", goal_id, exc
            )
        return "unknown"

    def _get_lessons_for_goal(self, goal_id: str) -> int:
        try:
            if self._learning_extraction is not None:
                lessons = self._learning_extraction.recent_lessons(limit=100)
                return sum(
                    1
                    for le in lessons
                    if _lesson_matches_goal(le, goal_id)
                )
        except Exception as exc:
            logger.debug(
                "execution_lifecycle: lessons_for_goal(%s) failed: %s", goal_id, exc
            )
        return 0

    def _get_patterns_for_goal(self, goal_id: str) -> int:
        try:
            if self._outcome_patterns is not None:
                patterns = self._outcome_patterns.patterns_for_goal(goal_id)
                return len(patterns)
        except Exception as exc:
            logger.debug(
                "execution_lifecycle: patterns_for_goal(%s) failed: %s", goal_id, exc
            )
        return 0

    def _get_capabilities_evolved_for_goal(self, goal_id: str) -> int:
        try:
            if self._capability_evolution is not None:
                adv = self._capability_evolution.advancing()
                return len(adv)
        except Exception as exc:
            logger.debug(
                "execution_lifecycle: capabilities_evolved(%s) failed: %s",
                goal_id,
                exc,
            )
        return 0

    # ── Stage classification ────────────────────────────────────────

    def _classify_stage(
        self,
        completion: float,
        health: str,
        lessons: int,
        capabilities_evolved: int,
    ) -> LifecycleStage:
        if completion <= 0.0:
            return LifecycleStage.NOT_STARTED

        if health in ("failed", "at_risk") and completion < 1.0:
            return LifecycleStage.FAILED

        if completion < 1.0:
            return LifecycleStage.IN_PROGRESS

        if capabilities_evolved > 0:
            return LifecycleStage.COMPOUNDED

        if lessons > 0:
            return LifecycleStage.LEARNING

        return LifecycleStage.COMPLETED

    # ── Public API ──────────────────────────────────────────────────

    def arc(self, goal_id: str) -> LifecycleArc:
        completion = self._get_completion(goal_id)
        health = self._get_outcome_health(goal_id)
        lessons = self._get_lessons_for_goal(goal_id)
        patterns = self._get_patterns_for_goal(goal_id)
        cap_evolved = self._get_capabilities_evolved_for_goal(goal_id)

        stage = self._classify_stage(completion, health, lessons, cap_evolved)

        return LifecycleArc(
            goal_id=goal_id,
            stage=stage.value,
            completion_pct=completion,
            lessons_extracted=lessons,
            patterns_detected=patterns,
            capabilities_evolved=cap_evolved,
            outcome_health=health,
        )

    def all_arcs(self) -> list[LifecycleArc]:
        goal_ids = self._get_tracked_goal_ids()
        return [self.arc(gid) for gid in goal_ids]

    def overall_stage(self) -> LifecycleStage:
        arcs = self.all_arcs()
        if not arcs:
            return LifecycleStage.NOT_STARTED

        stages = [a.stage for a in arcs]

        if all(s == LifecycleStage.COMPOUNDED.value for s in stages):
            return LifecycleStage.COMPOUNDED

        if any(s == LifecycleStage.COMPOUNDED.value for s in stages):
            return LifecycleStage.LEARNING

        if any(s == LifecycleStage.LEARNING.value for s in stages):
            return LifecycleStage.LEARNING

        if any(s == LifecycleStage.FAILED.value for s in stages):
            return LifecycleStage.FAILED

        if any(s == LifecycleStage.IN_PROGRESS.value for s in stages):
            return LifecycleStage.IN_PROGRESS

        if any(s == LifecycleStage.COMPLETED.value for s in stages):
            return LifecycleStage.COMPLETED

        return LifecycleStage.NOT_STARTED

    def recent_lessons(self, limit: int = 10) -> list[dict[str, Any]]:
        try:
            if self._learning_extraction is not None:
                lessons = self._learning_extraction.recent_lessons(limit=limit)
                return [
                    le.to_dict() if hasattr(le, "to_dict") else {"lesson": str(le)}
                    for le in lessons
                ]
        except Exception as exc:
            logger.debug("execution_lifecycle: recent_lessons failed: %s", exc)
        return []

    def recent_patterns(self, limit: int = 10) -> list[dict[str, Any]]:
        try:
            if self._outcome_patterns is not None:
                patterns = self._outcome_patterns.top_patterns(limit=limit)
                return [
                    p.to_dict() if hasattr(p, "to_dict") else {"pattern": str(p)}
                    for p in patterns
                ]
        except Exception as exc:
            logger.debug("execution_lifecycle: recent_patterns failed: %s", exc)
        return []

    def capability_momentum(self) -> dict[str, Any]:
        advancing = 0
        declining = 0
        stalled = 0
        try:
            if self._capability_evolution is not None:
                advancing = len(self._capability_evolution.advancing())
                declining = len(self._capability_evolution.declining())
                stalled = len(self._capability_evolution.stalled())
        except Exception as exc:
            logger.debug("execution_lifecycle: capability_momentum failed: %s", exc)

        total = advancing + declining + stalled
        return {
            "advancing": advancing,
            "declining": declining,
            "stalled": stalled,
            "total": total,
            "momentum_score": advancing / total if total > 0 else 0.0,
        }

    def health(self) -> str:
        stage = self.overall_stage()
        if stage == LifecycleStage.COMPOUNDED:
            return "thriving"
        if stage == LifecycleStage.LEARNING:
            return "growing"
        if stage in (LifecycleStage.COMPLETED, LifecycleStage.IN_PROGRESS):
            return "active"
        if stage == LifecycleStage.FAILED:
            return "degraded"
        return "dormant"

    def snapshot(self) -> ExecutionLifecycleSnapshot:
        arcs = self.all_arcs()
        momentum = self.capability_momentum()
        lessons = self.recent_lessons(limit=50)
        patterns = self.recent_patterns(limit=50)

        return ExecutionLifecycleSnapshot(
            arcs=[a.to_dict() for a in arcs],
            total_lessons=len(lessons),
            total_patterns=len(patterns),
            advancing_capabilities=momentum["advancing"],
            declining_capabilities=momentum["declining"],
            overall_stage=self.overall_stage().value,
        )

    def summary(self) -> dict[str, Any]:
        stage = self.overall_stage()
        momentum = self.capability_momentum()
        arcs = self.all_arcs()
        return {
            "overall_stage": stage.value,
            "health": self.health(),
            "arc_count": len(arcs),
            "advancing_capabilities": momentum["advancing"],
            "declining_capabilities": momentum["declining"],
            "momentum_score": momentum["momentum_score"],
        }


# ── Helpers ─────────────────────────────────────────────────────────


def _lesson_matches_goal(lesson: Any, goal_id: str) -> bool:
    if hasattr(lesson, "goal_id"):
        return getattr(lesson, "goal_id", "") == goal_id
    if hasattr(lesson, "source_id"):
        return getattr(lesson, "source_id", "") == goal_id
    if isinstance(lesson, dict):
        return lesson.get("goal_id", lesson.get("source_id", "")) == goal_id
    return False
