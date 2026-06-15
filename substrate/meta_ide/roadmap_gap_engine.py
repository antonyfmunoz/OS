"""Roadmap Gap Engine — detects gaps and recommends engineering work.

Compares current reality (roadmap progress, workspace health) against
desired state and produces prioritized gap analysis with actionable
recommendations that can feed directly into EngineeringPlanner.

Phase 22. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class RoadmapGap:
    """A detected gap between current and desired roadmap state."""

    gap_id: str = field(default_factory=lambda: f"rg-{uuid4().hex[:12]}")
    phase_number: str = ""
    phase_title: str = ""
    gap_type: str = ""
    description: str = ""
    priority_score: float = 0.0
    recommended_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "gap_id": self.gap_id,
            "phase_number": self.phase_number,
            "phase_title": self.phase_title,
            "gap_type": self.gap_type,
            "description": self.description,
            "priority_score": self.priority_score,
            "recommended_action": self.recommended_action,
        }


@dataclass
class GapAnalysis:
    """Complete gap analysis result."""

    analysis_id: str = field(default_factory=lambda: f"ga-{uuid4().hex[:12]}")
    total_phases: int = 0
    completed_phases: int = 0
    blocked_phases: int = 0
    gaps: list[RoadmapGap] = field(default_factory=list)
    completion_percentage: float = 0.0
    analyzed_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "total_phases": self.total_phases,
            "completed_phases": self.completed_phases,
            "blocked_phases": self.blocked_phases,
            "gaps": [g.to_dict() for g in self.gaps],
            "completion_percentage": self.completion_percentage,
            "analyzed_at": self.analyzed_at,
        }


@dataclass
class GapRecommendation:
    """Actionable work recommendation from gap analysis."""

    recommendation_id: str = field(default_factory=lambda: f"gr-{uuid4().hex[:12]}")
    gap_id: str = ""
    title: str = ""
    description: str = ""
    intent_text: str = ""
    estimated_risk: str = "low"
    dependencies: list[str] = field(default_factory=list)
    priority_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "gap_id": self.gap_id,
            "title": self.title,
            "description": self.description,
            "intent_text": self.intent_text,
            "estimated_risk": self.estimated_risk,
            "dependencies": self.dependencies,
            "priority_score": self.priority_score,
        }


_GAP_TYPE_PRIORITY: dict[str, float] = {
    "blocked": 0.9,
    "stale": 0.6,
    "missing_validation": 0.5,
    "not_started": 0.3,
}

_GAP_TYPE_RISK: dict[str, str] = {
    "blocked": "high",
    "stale": "medium",
    "missing_validation": "low",
    "not_started": "medium",
}


class RoadmapGapEngine:
    """Detects roadmap gaps and recommends engineering work.

    Read-only analysis. Does not create work packets or execute anything.
    Recommendations produce intent_text suitable for EngineeringPlanner.
    """

    def __init__(
        self,
        roadmap_intelligence: Any | None = None,
        workspace_engine: Any | None = None,
        reality_engine: Any | None = None,
    ) -> None:
        self._roadmap = roadmap_intelligence
        self._workspace = workspace_engine
        self._reality = reality_engine

    def analyze_gaps(self) -> GapAnalysis:
        """Compare current reality vs roadmap desired state."""
        phases = self._get_all_phases()
        completed = [p for p in phases if p.get("state") == "COMPLETED"]
        blocked = [p for p in phases if p.get("state") == "BLOCKED"]
        planned = [p for p in phases if p.get("state") in ("PLANNED", "IN_PROGRESS", None)]

        total = len(phases)
        pct = (len(completed) / total * 100.0) if total > 0 else 0.0

        gaps: list[RoadmapGap] = []

        for phase in blocked:
            gap = RoadmapGap(
                phase_number=phase.get("phase_number", ""),
                phase_title=phase.get("title", ""),
                gap_type="blocked",
                description=f"Phase {phase.get('phase_number', '?')} is blocked",
                priority_score=_GAP_TYPE_PRIORITY["blocked"],
                recommended_action=f"Unblock phase {phase.get('phase_number', '?')}: {phase.get('title', '')}",
            )
            gaps.append(gap)

        for phase in planned:
            state = phase.get("state", "PLANNED")
            if state == "IN_PROGRESS":
                gap_type = "stale"
                desc = f"Phase {phase.get('phase_number', '?')} is in progress but may be stale"
                action = (
                    f"Continue phase {phase.get('phase_number', '?')}: {phase.get('title', '')}"
                )
            else:
                gap_type = "not_started"
                desc = f"Phase {phase.get('phase_number', '?')} has not been started"
                action = f"Begin phase {phase.get('phase_number', '?')}: {phase.get('title', '')}"

            gap = RoadmapGap(
                phase_number=phase.get("phase_number", ""),
                phase_title=phase.get("title", ""),
                gap_type=gap_type,
                description=desc,
                priority_score=_GAP_TYPE_PRIORITY.get(gap_type, 0.3),
                recommended_action=action,
            )
            gaps.append(gap)

        gaps.sort(key=lambda g: g.priority_score, reverse=True)

        return GapAnalysis(
            total_phases=total,
            completed_phases=len(completed),
            blocked_phases=len(blocked),
            gaps=gaps,
            completion_percentage=round(pct, 1),
        )

    def recommend_work(self, max_items: int = 10) -> list[GapRecommendation]:
        """Generate prioritized work recommendations from gaps."""
        analysis = self.analyze_gaps()
        recommendations: list[GapRecommendation] = []

        for gap in analysis.gaps[:max_items]:
            intent_text = self._gap_to_intent(gap)
            rec = GapRecommendation(
                gap_id=gap.gap_id,
                title=gap.recommended_action,
                description=gap.description,
                intent_text=intent_text,
                estimated_risk=_GAP_TYPE_RISK.get(gap.gap_type, "medium"),
                priority_score=gap.priority_score,
            )
            recommendations.append(rec)

        return recommendations

    # ── Private helpers ─────────────────────────────────────────────────

    def _get_all_phases(self) -> list[dict[str, Any]]:
        if not self._roadmap:
            return []
        try:
            phases: list[dict[str, Any]] = []
            completed = self._roadmap.completed_phases()
            for p in completed:
                phases.append(
                    {
                        "phase_number": getattr(p, "phase_number", ""),
                        "title": getattr(p, "title", ""),
                        "state": "COMPLETED",
                    }
                )
            remaining = self._roadmap.what_remains()
            for p in remaining:
                phases.append(
                    {
                        "phase_number": getattr(p, "phase_number", ""),
                        "title": getattr(p, "title", ""),
                        "state": getattr(p, "state", "PLANNED"),
                    }
                )
            blocked = self._roadmap.what_is_blocked()
            blocked_numbers = {getattr(p, "phase_number", "") for p in blocked}
            for phase in phases:
                if phase["phase_number"] in blocked_numbers:
                    phase["state"] = "BLOCKED"
            return phases
        except Exception:
            return []

    @staticmethod
    def _gap_to_intent(gap: RoadmapGap) -> str:
        action_map: dict[str, str] = {
            "blocked": "Resolve blocking issue for",
            "stale": "Continue work on",
            "missing_validation": "Add validation for",
            "not_started": "Implement",
        }
        verb = action_map.get(gap.gap_type, "Address")
        return (
            f"{verb} {gap.phase_title}" if gap.phase_title else f"{verb} phase {gap.phase_number}"
        )
