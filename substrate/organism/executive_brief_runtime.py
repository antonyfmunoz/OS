"""Executive Brief Runtime — structured operator briefing synthesis.

Campaign 7.5. UMH substrate layer.

Composes C7.0-C7.4 (StrategicContextRuntime, PriorityEngine, RiskEngine,
RecommendationEngine, DriftDetectionEngine) into a structured briefing.

The "morning brief" for the operator. Template-based, deterministic.
No LLM. No execution. No mutation.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────


@dataclass
class ExecutiveBrief:
    situation: str = ""
    progress: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    priorities: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    drift_warnings: list[str] = field(default_factory=list)
    active_goals: list[str] = field(default_factory=list)
    goal_health: str = "unknown"
    goal_drift: list[str] = field(default_factory=list)
    critical_decisions: list[str] = field(default_factory=list)
    at_risk_decisions: list[str] = field(default_factory=list)
    invalid_assumptions: list[str] = field(default_factory=list)
    top_capabilities: list[str] = field(default_factory=list)
    critical_capability_gaps: list[str] = field(default_factory=list)
    capability_health: str = "unknown"
    learning_health: str = "unknown"
    learning_velocity: float = 0.0
    learning_drift_count: int = 0
    prediction_health: str = "unknown"
    top_forecasts: list[str] = field(default_factory=list)
    critical_future_risks: list[str] = field(default_factory=list)
    allocation_health: str = "unknown"
    top_allocations: list[str] = field(default_factory=list)
    overcommitment_index: float = 0.0
    executive_health: str = "unknown"
    executive_drift_count: int = 0
    governance_health: str = "unknown"
    organism_coherence_score: float = 0.0
    governance_conflict_count: int = 0
    execution_state: str = "idle"
    execution_readiness_count: int = 0
    execution_blocked_count: int = 0
    health: str = "healthy"
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "situation": self.situation,
            "progress": self.progress,
            "blockers": self.blockers,
            "risks": self.risks,
            "priorities": self.priorities,
            "recommendations": self.recommendations,
            "drift_warnings": self.drift_warnings,
            "active_goals": self.active_goals,
            "goal_health": self.goal_health,
            "goal_drift": self.goal_drift,
            "critical_decisions": self.critical_decisions,
            "at_risk_decisions": self.at_risk_decisions,
            "invalid_assumptions": self.invalid_assumptions,
            "top_capabilities": self.top_capabilities,
            "critical_capability_gaps": self.critical_capability_gaps,
            "capability_health": self.capability_health,
            "learning_health": self.learning_health,
            "learning_velocity": self.learning_velocity,
            "learning_drift_count": self.learning_drift_count,
            "prediction_health": self.prediction_health,
            "top_forecasts": self.top_forecasts,
            "critical_future_risks": self.critical_future_risks,
            "allocation_health": self.allocation_health,
            "top_allocations": self.top_allocations,
            "overcommitment_index": self.overcommitment_index,
            "executive_health": self.executive_health,
            "executive_drift_count": self.executive_drift_count,
            "governance_health": self.governance_health,
            "organism_coherence_score": self.organism_coherence_score,
            "governance_conflict_count": self.governance_conflict_count,
            "execution_state": self.execution_state,
            "execution_readiness_count": self.execution_readiness_count,
            "execution_blocked_count": self.execution_blocked_count,
            "health": self.health,
            "generated_at": self.generated_at,
        }

    def to_text(self) -> str:
        """Human-readable formatted briefing."""
        lines: list[str] = []
        lines.append(f"Health: {self.health.upper()}")
        lines.append("")

        if self.situation:
            lines.append(f"Situation: {self.situation}")
            lines.append("")

        if self.progress:
            lines.append("Progress:")
            for item in self.progress:
                lines.append(f"  - {item}")
            lines.append("")

        if self.blockers:
            lines.append("Blockers:")
            for item in self.blockers:
                lines.append(f"  - {item}")
            lines.append("")

        if self.risks:
            lines.append("Risks:")
            for item in self.risks:
                lines.append(f"  - {item}")
            lines.append("")

        if self.priorities:
            lines.append("Priorities:")
            for i, item in enumerate(self.priorities, 1):
                lines.append(f"  {i}. {item}")
            lines.append("")

        if self.drift_warnings:
            lines.append("Drift:")
            for item in self.drift_warnings:
                lines.append(f"  - {item}")
            lines.append("")

        if self.active_goals:
            lines.append(f"Goals ({self.goal_health}):")
            for item in self.active_goals:
                lines.append(f"  - {item}")
            lines.append("")

        if self.goal_drift:
            lines.append("Goal Drift:")
            for item in self.goal_drift:
                lines.append(f"  - {item}")
            lines.append("")

        if self.critical_decisions:
            lines.append("Critical Decisions:")
            for item in self.critical_decisions:
                lines.append(f"  - {item}")
            lines.append("")

        if self.at_risk_decisions:
            lines.append("At-Risk Decisions:")
            for item in self.at_risk_decisions:
                lines.append(f"  ! {item}")
            lines.append("")

        if self.invalid_assumptions:
            lines.append("Invalid Assumptions:")
            for item in self.invalid_assumptions:
                lines.append(f"  X {item}")
            lines.append("")

        if self.top_capabilities:
            lines.append(f"Capabilities ({self.capability_health}):")
            for item in self.top_capabilities:
                lines.append(f"  - {item}")
            lines.append("")

        if self.critical_capability_gaps:
            lines.append("Capability Gaps:")
            for item in self.critical_capability_gaps:
                lines.append(f"  ! {item}")
            lines.append("")

        if self.recommendations:
            lines.append("Recommended Actions:")
            for item in self.recommendations:
                lines.append(f"  > {item}")
            lines.append("")

        if self.executive_health != "unknown":
            lines.append(f"Executive: {self.executive_health.upper()} "
                         f"(allocation: {self.allocation_health}, "
                         f"overcommit: {self.overcommitment_index:.0%}, "
                         f"drifts: {self.executive_drift_count})")
            lines.append("")

        if self.top_allocations:
            lines.append("Top Allocations:")
            for item in self.top_allocations:
                lines.append(f"  $ {item}")

        if self.governance_health != "unknown":
            lines.append("")
            lines.append(f"Governance: {self.governance_health.upper()} "
                         f"(coherence: {self.organism_coherence_score:.0%}, "
                         f"conflicts: {self.governance_conflict_count})")

        return "\n".join(lines).strip()


# ── Runtime ───────────────────────────────────────────────────────────


class ExecutiveBriefRuntime:
    """Generates structured operator briefings from C7 engines.

    Composes:
      - StrategicContextRuntime (C7.0) for situation + health
      - PriorityEngine (C7.1) for ordered priorities
      - RiskEngine (C7.2) for top risks
      - RecommendationEngine (C7.3) for suggested actions
      - DriftDetectionEngine (C7.4) for drift warnings
    """

    def __init__(
        self,
        strategic_context: Any | None = None,
        priority_engine: Any | None = None,
        risk_engine: Any | None = None,
        recommendation_engine: Any | None = None,
        drift_engine: Any | None = None,
        goal_drift_engine: Any | None = None,
        outcome_tracking: Any | None = None,
        decision_registry: Any | None = None,
        validity_engine: Any | None = None,
        assumption_tracking: Any | None = None,
        capability_runtime: Any | None = None,
        capability_portfolio: Any | None = None,
    ) -> None:
        self._strategic_context = strategic_context
        self._priority_engine = priority_engine
        self._risk_engine = risk_engine
        self._recommendation_engine = recommendation_engine
        self._drift_engine = drift_engine
        self._goal_drift_engine = goal_drift_engine
        self._outcome_tracking = outcome_tracking
        self._decision_registry = decision_registry
        self._validity_engine = validity_engine
        self._assumption_tracking = assumption_tracking
        self._capability_runtime = capability_runtime
        self._capability_portfolio = capability_portfolio

    def generate(self) -> ExecutiveBrief:
        """Generate a deterministic executive brief."""
        brief = ExecutiveBrief(generated_at=time.time())

        self._fill_situation(brief)
        self._fill_progress(brief)
        self._fill_blockers(brief)
        self._fill_risks(brief)
        self._fill_priorities(brief)
        self._fill_recommendations(brief)
        self._fill_drift(brief)
        self._fill_goal_health(brief)
        self._fill_goal_drift(brief)
        self._fill_decisions(brief)
        self._fill_capabilities(brief)
        self._fill_learning(brief)
        self._fill_prediction(brief)
        self._fill_executive(brief)
        self._fill_governance(brief)
        self._fill_execution_loop(brief)

        return brief

    def summary(self) -> dict[str, Any]:
        """Compact summary."""
        brief = self.generate()
        return {
            "health": brief.health,
            "situation": brief.situation,
            "priority_count": len(brief.priorities),
            "risk_count": len(brief.risks),
            "blocker_count": len(brief.blockers),
            "drift_count": len(brief.drift_warnings),
            "recommendation_count": len(brief.recommendations),
            "generated_at": brief.generated_at,
        }

    def snapshot(self) -> dict[str, Any]:
        """Full serialized brief."""
        return self.generate().to_dict()

    # ── Fill methods ──────────────────────────────────────────────

    def _fill_situation(self, brief: ExecutiveBrief) -> None:
        if self._strategic_context is None:
            brief.situation = "No strategic context available"
            return
        try:
            ctx = self._strategic_context.context()
            health = ctx.health if hasattr(ctx, "health") else "unknown"
            brief.health = health

            project_count = len(ctx.active_projects) if hasattr(ctx, "active_projects") else 0
            work_count = len(ctx.active_work) if hasattr(ctx, "active_work") else 0
            blocked_count = len(ctx.blocked_work) if hasattr(ctx, "blocked_work") else 0

            parts: list[str] = []
            parts.append(f"{project_count} active project(s)")
            parts.append(f"{work_count} work item(s) in progress")
            if blocked_count > 0:
                parts.append(f"{blocked_count} blocked")
            parts.append(f"Health: {health}")

            brief.situation = ". ".join(parts)
        except Exception as exc:
            logger.debug("executive_brief: situation fill failed: %s", exc)
            brief.situation = "Strategic context unavailable"

    def _fill_progress(self, brief: ExecutiveBrief) -> None:
        if self._strategic_context is None:
            return
        try:
            ctx = self._strategic_context.context()
            for work in (ctx.active_work if hasattr(ctx, "active_work") else [])[:5]:
                title = work.get("title", work.get("packet_id", "work"))
                status = work.get("status", "active")
                brief.progress.append(f"{title} ({status})")
        except Exception as exc:
            logger.debug("executive_brief: progress fill failed: %s", exc)

    def _fill_blockers(self, brief: ExecutiveBrief) -> None:
        if self._strategic_context is None:
            return
        try:
            ctx = self._strategic_context.context()
            for work in (ctx.blocked_work if hasattr(ctx, "blocked_work") else [])[:5]:
                title = work.get("title", work.get("packet_id", "blocked"))
                reason = work.get("reason", work.get("blocker_detail", "unknown"))
                brief.blockers.append(f"{title}: {reason}")
        except Exception as exc:
            logger.debug("executive_brief: blockers fill failed: %s", exc)

    def _fill_risks(self, brief: ExecutiveBrief) -> None:
        if self._risk_engine is None:
            return
        try:
            risks = self._risk_engine.high_risks()
            for r in risks[:3]:
                title = r.title if hasattr(r, "title") else str(r)
                severity = r.severity if hasattr(r, "severity") else "unknown"
                brief.risks.append(f"[{severity.upper()}] {title}")
        except Exception as exc:
            logger.debug("executive_brief: risks fill failed: %s", exc)

    def _fill_priorities(self, brief: ExecutiveBrief) -> None:
        if self._priority_engine is None:
            return
        try:
            priorities = self._priority_engine.top(limit=5)
            for p in priorities:
                title = p.title if hasattr(p, "title") else str(p)
                score = p.score if hasattr(p, "score") else 0.0
                brief.priorities.append(f"{title} (score: {score:.2f})")
        except Exception as exc:
            logger.debug("executive_brief: priorities fill failed: %s", exc)

    def _fill_recommendations(self, brief: ExecutiveBrief) -> None:
        if self._recommendation_engine is None:
            return
        try:
            recs = self._recommendation_engine.top(limit=3)
            for r in recs:
                action = r.action if hasattr(r, "action") else str(r)
                reason = r.reason if hasattr(r, "reason") else ""
                if reason:
                    brief.recommendations.append(f"{action} — {reason}")
                else:
                    brief.recommendations.append(action)
        except Exception as exc:
            logger.debug("executive_brief: recommendations fill failed: %s", exc)

    def _fill_drift(self, brief: ExecutiveBrief) -> None:
        if self._drift_engine is None:
            return
        try:
            drift = self._drift_engine.high_drift()
            for d in drift[:5]:
                title = d.title if hasattr(d, "title") else str(d)
                dtype = d.drift_type if hasattr(d, "drift_type") else "unknown"
                brief.drift_warnings.append(f"[{dtype}] {title}")
        except Exception as exc:
            logger.debug("executive_brief: drift fill failed: %s", exc)

    def _fill_goal_health(self, brief: ExecutiveBrief) -> None:
        if self._outcome_tracking is None:
            return
        try:
            snapshot = self._outcome_tracking.snapshot()
            snap_dict = snapshot.to_dict() if hasattr(snapshot, "to_dict") else snapshot
            brief.goal_health = snap_dict.get("overall_health", "unknown")
            for g in snap_dict.get("goals", [])[:5]:
                title = g.get("title", g.get("goal_id", "goal"))
                brief.active_goals.append(title)
        except Exception as exc:
            logger.debug("executive_brief: goal_health fill failed: %s", exc)

    def _fill_goal_drift(self, brief: ExecutiveBrief) -> None:
        if self._goal_drift_engine is None:
            return
        try:
            warnings = self._goal_drift_engine.high_drift()
            for w in warnings[:5]:
                title = w.goal_title if hasattr(w, "goal_title") else str(w)
                dtype = w.drift_type if hasattr(w, "drift_type") else "unknown"
                brief.goal_drift.append(f"[{dtype}] {title}")
        except Exception as exc:
            logger.debug("executive_brief: goal_drift fill failed: %s", exc)

    def _fill_decisions(self, brief: ExecutiveBrief) -> None:
        if self._decision_registry:
            try:
                from substrate.organism.decision_registry import DecisionStatus
                active = self._decision_registry.list_decisions(
                    status=DecisionStatus.ACTIVE
                )
                for d in active[:5]:
                    brief.critical_decisions.append(d.title)
            except Exception as exc:
                logger.debug("executive_brief: decisions fill failed: %s", exc)

        if self._validity_engine:
            try:
                at_risk = self._validity_engine.at_risk()
                for v in at_risk[:5]:
                    label = v.decision_title if hasattr(v, "decision_title") else v.decision_id
                    brief.at_risk_decisions.append(label)
            except Exception as exc:
                logger.debug("executive_brief: at_risk fill failed: %s", exc)

        if self._assumption_tracking:
            try:
                invalid = self._assumption_tracking.invalidated()
                for a in invalid[:5]:
                    brief.invalid_assumptions.append(a.statement)
            except Exception as exc:
                logger.debug("executive_brief: invalid_assumptions fill failed: %s", exc)

    def _fill_capabilities(self, brief: ExecutiveBrief) -> None:
        if self._capability_portfolio is None:
            return
        try:
            snap = self._capability_portfolio.snapshot()
            brief.capability_health = (
                snap.health.value if hasattr(snap.health, "value") else str(snap.health)
            )
            for cap in getattr(snap, "top_capabilities", [])[:5]:
                name = cap.get("name", "")
                maturity = cap.get("maturity", "")
                brief.top_capabilities.append(f"{name} ({maturity})")
            for gap in getattr(snap, "critical_gaps", [])[:5]:
                rec = gap.get("recommendation", str(gap))
                brief.critical_capability_gaps.append(rec)
        except Exception as exc:
            logger.debug("executive_brief: capabilities fill failed: %s", exc)

    def _fill_learning(self, brief: ExecutiveBrief) -> None:
        try:
            from substrate.organism.learning_portfolio_runtime import LearningPortfolioRuntime
            lpr = LearningPortfolioRuntime()
            h = lpr.health()
            brief.learning_health = h.value if hasattr(h, "value") else str(h)
            brief.learning_velocity = lpr.lesson_velocity()
            brief.learning_drift_count = len(lpr.drift_warnings())
        except Exception as exc:
            logger.debug("executive_brief: learning fill failed: %s", exc)

    def _fill_prediction(self, brief: ExecutiveBrief) -> None:
        try:
            from substrate.organism.prediction_portfolio_runtime import PredictionPortfolioRuntime
            ppr = PredictionPortfolioRuntime()
            h = ppr.health()
            brief.prediction_health = h.value if hasattr(h, "value") else str(h)
            top = ppr.highest_risk_forecasts(limit=3)
            for f in top:
                eid = getattr(f, "entity_id", "") if hasattr(f, "entity_id") else f.get("entity_id", "")
                status = getattr(f, "status", "") if hasattr(f, "status") else f.get("status", "")
                brief.top_forecasts.append(f"{eid} ({status})")
            snap = ppr.snapshot()
            for risk in getattr(snap, "critical_risks", [])[:3]:
                if isinstance(risk, dict):
                    brief.critical_future_risks.append(risk.get("risk", str(risk)))
                else:
                    brief.critical_future_risks.append(str(risk))
        except Exception as exc:
            logger.debug("executive_brief: prediction fill failed: %s", exc)

    def _fill_executive(self, brief: ExecutiveBrief) -> None:
        try:
            from substrate.organism.executive_portfolio_runtime import ExecutivePortfolioRuntime
            epr = ExecutivePortfolioRuntime()
            h = epr.health()
            brief.executive_health = h.value if hasattr(h, "value") else str(h)
            brief.allocation_health = epr._get_allocation_health()
            brief.overcommitment_index = epr.overcommitment_index()
            brief.executive_drift_count = len(epr.drift_warnings())
            top = epr.top_recommendations(limit=3)
            for r in top:
                name = r.get("target_name", "") if isinstance(r, dict) else getattr(r, "target_name", "")
                priority = r.get("priority", "") if isinstance(r, dict) else getattr(r, "priority", "")
                brief.top_allocations.append(f"{name} ({priority})")
        except Exception as exc:
            logger.debug("executive_brief: executive fill failed: %s", exc)

    def _fill_governance(self, brief: ExecutiveBrief) -> None:
        try:
            from substrate.organism.organism_portfolio_runtime import OrganismPortfolioRuntime
            opr = OrganismPortfolioRuntime()
            h = opr.health()
            brief.governance_health = h.value if hasattr(h, "value") else str(h)
            brief.organism_coherence_score = opr.coherence_score()
            from substrate.organism.governance_runtime import GovernanceRuntime
            gr = GovernanceRuntime()
            brief.governance_conflict_count = len(gr.active_conflicts())
        except Exception as exc:
            logger.debug("executive_brief: governance fill failed: %s", exc)

    def _fill_execution_loop(self, brief: ExecutiveBrief) -> None:
        try:
            from substrate.organism.governed_execution_runtime import (
                GovernedExecutionRuntime,
            )

            ger = GovernedExecutionRuntime()
            assessment = ger.assessment()
            brief.execution_state = assessment.state
            brief.execution_readiness_count = assessment.ready_count
            brief.execution_blocked_count = assessment.blocked_count
        except Exception as exc:
            logger.debug("executive_brief: execution_loop fill failed: %s", exc)
