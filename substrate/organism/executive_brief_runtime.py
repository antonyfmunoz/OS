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

        if self.recommendations:
            lines.append("Recommended Actions:")
            for item in self.recommendations:
                lines.append(f"  > {item}")

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
    ) -> None:
        self._strategic_context = strategic_context
        self._priority_engine = priority_engine
        self._risk_engine = risk_engine
        self._recommendation_engine = recommendation_engine
        self._drift_engine = drift_engine

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
