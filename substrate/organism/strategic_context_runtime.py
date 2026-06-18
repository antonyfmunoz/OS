"""Strategic Context Runtime — unified executive synthesis facade.

Campaign 7.0. UMH substrate layer.

This is the executive synthesis layer ABOVE the existing strategic engines.
It consumes their outputs and produces cross-cutting strategic meaning.
It does NOT reimplement gap detection, drift detection, risk detection,
or recommendation generation — those belong to the engines below.

Composes:
  - StrategicGapEngine (Phase 4) — gap analysis, recommendations
  - StrategicTickLoop (Phase 5) — change detection, drift, candidates
  - ProjectionEngine (Phase 6) — trends, risks, opportunities
  - OperatorContextEngine (Phase 31) — health, attention
  - NextActionEngine — evidence-based action recommendations
  - RuntimeAwarenessRuntime (C6.3) — active/blocked work
  - KnowledgeAwarenessRuntime (C6.4) — decisions, constraints
  - RealityGraph (C5) — entity topology

Read-only. No execution. No mutation. No autonomous action.
Deterministic. Zero LLM calls.
"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────


class StrategicHealth(str, Enum):
    HEALTHY = "healthy"
    WATCH = "watch"
    DEGRADED = "degraded"
    CRITICAL = "critical"


@dataclass
class StrategicContext:
    active_projects: list[str] = field(default_factory=list)
    active_work: list[dict[str, Any]] = field(default_factory=list)
    blocked_work: list[dict[str, Any]] = field(default_factory=list)
    pending_approvals: list[dict[str, Any]] = field(default_factory=list)
    critical_constraints: list[dict[str, Any]] = field(default_factory=list)
    strategic_priorities: list[dict[str, Any]] = field(default_factory=list)
    risks: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    drift_warnings: list[dict[str, Any]] = field(default_factory=list)
    goal_summary: dict[str, Any] = field(default_factory=dict)
    goal_alignment: dict[str, Any] = field(default_factory=dict)
    decision_health: dict[str, Any] = field(default_factory=dict)
    memory_health: dict[str, Any] = field(default_factory=dict)
    health: str = StrategicHealth.HEALTHY.value
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_projects": self.active_projects,
            "active_work": self.active_work,
            "blocked_work": self.blocked_work,
            "pending_approvals": self.pending_approvals,
            "critical_constraints": self.critical_constraints,
            "strategic_priorities": self.strategic_priorities,
            "risks": self.risks,
            "recommendations": self.recommendations,
            "drift_warnings": self.drift_warnings,
            "goal_summary": self.goal_summary,
            "goal_alignment": self.goal_alignment,
            "decision_health": self.decision_health,
            "memory_health": self.memory_health,
            "health": self.health,
            "generated_at": self.generated_at,
        }


# ── Runtime ───────────────────────────────────────────────────────────


class StrategicContextRuntime:
    """Unified executive synthesis facade.

    Composes 5 existing strategic engines + 3 awareness runtimes into
    a single strategic view. Does NOT reimplement any engine logic —
    delegates and synthesizes.
    """

    def __init__(
        self,
        gap_engine: Any | None = None,
        tick_loop: Any | None = None,
        projection_engine: Any | None = None,
        operator_context: Any | None = None,
        next_action_engine: Any | None = None,
        runtime_awareness: Any | None = None,
        knowledge_awareness: Any | None = None,
        reality_graph: Any | None = None,
        goal_alignment_engine: Any | None = None,
        decision_registry: Any | None = None,
        memory_engine: Any | None = None,
    ) -> None:
        self._gap_engine = gap_engine
        self._tick_loop = tick_loop
        self._projection_engine = projection_engine
        self._operator_context = operator_context
        self._next_action_engine = next_action_engine
        self._runtime_awareness = runtime_awareness
        self._knowledge_awareness = knowledge_awareness
        self._reality_graph = reality_graph
        self._goal_alignment_engine = goal_alignment_engine
        self._decision_registry = decision_registry
        self._memory_engine = memory_engine

    def context(self) -> StrategicContext:
        """Synthesize strategic context from all composed engines."""
        ctx = StrategicContext(generated_at=time.time())

        self._fill_from_reality_graph(ctx)
        self._fill_from_runtime_awareness(ctx)
        self._fill_from_knowledge_awareness(ctx)
        self._fill_from_gap_engine(ctx)
        self._fill_from_tick_loop(ctx)
        self._fill_from_projection_engine(ctx)
        self._fill_from_operator_context(ctx)
        self._fill_from_next_action_engine(ctx)
        self._fill_from_goal_system(ctx)
        self._fill_from_decision_system(ctx)

        ctx.health = self._classify_health(ctx).value
        return ctx

    def health(self) -> StrategicHealth:
        """Deterministic health classification from current state."""
        ctx = self.context()
        return StrategicHealth(ctx.health)

    def summary(self) -> dict[str, Any]:
        """Compact summary for API."""
        ctx = self.context()
        return {
            "health": ctx.health,
            "active_project_count": len(ctx.active_projects),
            "active_work_count": len(ctx.active_work),
            "blocked_count": len(ctx.blocked_work),
            "approval_count": len(ctx.pending_approvals),
            "risk_count": len(ctx.risks),
            "drift_count": len(ctx.drift_warnings),
            "recommendation_count": len(ctx.recommendations),
            "generated_at": ctx.generated_at,
        }

    def snapshot(self) -> dict[str, Any]:
        """Full serialized context for cockpit."""
        return self.context().to_dict()

    # ── Fill methods (delegate to composed engines) ───────────────

    def _fill_from_reality_graph(self, ctx: StrategicContext) -> None:
        if self._reality_graph is None:
            return
        try:
            from substrate.organism.reality_graph import RealityEntityType
            projects = self._reality_graph.find_by_type(RealityEntityType.PROJECT)
            ctx.active_projects = [
                p.name for p in projects
                if p.status in ("active", "ACTIVE")
            ]
        except Exception as exc:
            logger.debug("strategic_context: reality_graph fill failed: %s", exc)

    def _fill_from_runtime_awareness(self, ctx: StrategicContext) -> None:
        if self._runtime_awareness is None:
            return
        try:
            active = self._runtime_awareness.active_work()
            ctx.active_work = active if isinstance(active, list) else []

            blocked = self._runtime_awareness.blocked_work()
            ctx.blocked_work = blocked if isinstance(blocked, list) else []
        except Exception as exc:
            logger.debug("strategic_context: runtime_awareness fill failed: %s", exc)

    def _fill_from_knowledge_awareness(self, ctx: StrategicContext) -> None:
        if self._knowledge_awareness is None:
            return
        try:
            constraints = self._knowledge_awareness.find_constraints()
            ctx.critical_constraints = [
                c.to_dict() if hasattr(c, "to_dict") else c
                for c in constraints
            ]
        except Exception as exc:
            logger.debug("strategic_context: knowledge_awareness fill failed: %s", exc)

    def _fill_from_gap_engine(self, ctx: StrategicContext) -> None:
        if self._gap_engine is None:
            return
        try:
            analysis = self._gap_engine.analyze()
            gaps = analysis.get("gaps", [])
            ctx.strategic_priorities = gaps[:10]

            recs = analysis.get("recommendations", [])
            ctx.recommendations.extend(recs[:10])
        except Exception as exc:
            logger.debug("strategic_context: gap_engine fill failed: %s", exc)

    def _fill_from_tick_loop(self, ctx: StrategicContext) -> None:
        if self._tick_loop is None:
            return
        try:
            state = self._tick_loop.get_strategic_state()

            drift = state.get("drift_warnings", [])
            ctx.drift_warnings = drift

            candidates = state.get("candidate_queue", {}).get("items", [])
            for c in candidates[:5]:
                ctx.recommendations.append({
                    "source": "tick_candidate",
                    "title": c.get("title", ""),
                    "priority_score": c.get("priority_score", 0),
                })
        except Exception as exc:
            logger.debug("strategic_context: tick_loop fill failed: %s", exc)

    def _fill_from_projection_engine(self, ctx: StrategicContext) -> None:
        if self._projection_engine is None:
            return
        try:
            state = self._projection_engine.get_projection_state()
            risks = state.get("risks", [])
            ctx.risks = [
                r.to_dict() if hasattr(r, "to_dict") else r
                for r in risks
            ]
        except Exception as exc:
            logger.debug("strategic_context: projection_engine fill failed: %s", exc)

    def _fill_from_operator_context(self, ctx: StrategicContext) -> None:
        if self._operator_context is None:
            return
        try:
            approvals = self._operator_context.pending_approvals()
            items = approvals.get("items", approvals.get("approvals", []))
            ctx.pending_approvals = items if isinstance(items, list) else []
        except Exception as exc:
            logger.debug("strategic_context: operator_context fill failed: %s", exc)

    def _fill_from_next_action_engine(self, ctx: StrategicContext) -> None:
        if self._next_action_engine is None:
            return
        try:
            actions = self._next_action_engine.actions
            for act in actions[:5]:
                ctx.recommendations.append(
                    act.to_dict() if hasattr(act, "to_dict") else act
                )
        except Exception as exc:
            logger.debug("strategic_context: next_action_engine fill failed: %s", exc)

    def _fill_from_goal_system(self, ctx: StrategicContext) -> None:
        if self._goal_alignment_engine is None:
            return
        try:
            report = self._goal_alignment_engine.report()
            report_dict = report.to_dict() if hasattr(report, "to_dict") else report
            ctx.goal_alignment = {
                "score": report_dict.get("alignment_score", 0.0),
                "unlinked_count": report_dict.get("unlinked_work_count", 0),
            }
        except Exception as exc:
            logger.debug("strategic_context: goal_alignment fill failed: %s", exc)

        if self._gap_engine is not None:
            try:
                registry = getattr(self._gap_engine, "registry", None)
                if registry is not None:
                    from substrate.organism.strategic_gap_engine import GoalStatus
                    active = registry.goals_by_status(GoalStatus.ACTIVE)
                    ctx.goal_summary = {
                        "active_count": len(active),
                        "total_count": len(registry.all_goals()),
                    }
            except Exception as exc:
                logger.debug("strategic_context: goal_summary fill failed: %s", exc)

    # ── Health classification ─────────────────────────────────────

    def _classify_health(self, ctx: StrategicContext) -> StrategicHealth:
        """Deterministic health classification.

        CRITICAL: critical gaps OR critical drift OR blocked high-priority work
        DEGRADED: high-severity gaps OR alert-level drift OR >3 pending approvals
        WATCH: medium gaps OR warning-level drift OR stale constraints
        HEALTHY: otherwise
        """
        has_critical_gaps = any(
            g.get("severity") == "critical" or g.get("priority_score", 0) > 0.9
            for g in ctx.strategic_priorities
        )
        has_critical_drift = any(
            d.get("severity") == "critical"
            for d in ctx.drift_warnings
        )
        has_blocked_high = len(ctx.blocked_work) > 0 and any(
            w.get("priority", "").lower() in ("critical", "high")
            or w.get("priority_score", 0) > 0.7
            for w in ctx.blocked_work
        )

        if has_critical_gaps or has_critical_drift or has_blocked_high:
            return StrategicHealth.CRITICAL

        has_high_gaps = any(
            g.get("severity") == "high" or g.get("priority_score", 0) > 0.7
            for g in ctx.strategic_priorities
        )
        has_alert_drift = any(
            d.get("severity") == "alert"
            for d in ctx.drift_warnings
        )
        many_approvals = len(ctx.pending_approvals) > 3

        if has_high_gaps or has_alert_drift or many_approvals:
            return StrategicHealth.DEGRADED

        has_medium_gaps = any(
            g.get("severity") == "medium" or g.get("priority_score", 0) > 0.4
            for g in ctx.strategic_priorities
        )
        has_warning_drift = any(
            d.get("severity") == "warning"
            for d in ctx.drift_warnings
        )

        if has_medium_gaps or has_warning_drift:
            return StrategicHealth.WATCH

        return StrategicHealth.HEALTHY

    def _fill_from_decision_system(self, ctx: StrategicContext) -> None:
        if self._decision_registry:
            try:
                s = self._decision_registry.summary()
                ctx.decision_health = {
                    "total": s.get("total", 0),
                    "by_status": s.get("by_status", {}),
                }
            except Exception:
                logger.debug("Failed to fill decision health", exc_info=True)
        if self._memory_engine:
            try:
                s = self._memory_engine.summary()
                ctx.memory_health = {
                    "snapshot_count": s.get("snapshot_count", 0),
                    "pattern_count": s.get("pattern_count", 0),
                }
            except Exception:
                logger.debug("Failed to fill memory health", exc_info=True)
