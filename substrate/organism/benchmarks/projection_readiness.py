"""Benchmark — Projection Readiness.

Measures whether UMH capabilities are ready to accelerate projection
builds (EOS, LOS, COS). Maps required capabilities against existing
capabilities and computes coverage percentages.

All metrics numerical. No subjective scoring.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Projection capability requirements
# ---------------------------------------------------------------------------

PROJECTION_REQUIREMENTS: dict[str, list[str]] = {
    "EOS": [
        "outreach_automation",
        "lead_tracking",
        "pipeline_management",
        "content_scheduling",
        "analytics_dashboard",
        "client_communication",
        "offer_management",
        "revenue_tracking",
        "task_automation",
        "crm_integration",
    ],
    "LOS": [
        "habit_tracking",
        "goal_setting",
        "progress_visualization",
        "community_features",
        "gamification",
        "streak_tracking",
        "personal_analytics",
        "milestone_system",
        "notification_engine",
        "social_sharing",
    ],
    "COS": [
        "content_creation",
        "publishing_workflow",
        "audience_analytics",
        "monetization",
        "distribution",
        "media_management",
        "template_system",
        "collaboration",
        "scheduling",
        "cross_platform_posting",
    ],
}


@dataclass
class ProjectionCoverage:
    """Coverage analysis for a single projection."""

    projection_name: str = ""
    required_capabilities: list[str] = field(default_factory=list)
    matched_capabilities: list[str] = field(default_factory=list)
    unmatched_capabilities: list[str] = field(default_factory=list)
    existing_coverage_pct: float = 0.0
    net_new_pct: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "projection_name": self.projection_name,
            "required_count": len(self.required_capabilities),
            "matched_count": len(self.matched_capabilities),
            "unmatched_count": len(self.unmatched_capabilities),
            "existing_coverage_pct": self.existing_coverage_pct,
            "net_new_pct": self.net_new_pct,
            "matched": self.matched_capabilities,
            "unmatched": self.unmatched_capabilities,
        }


@dataclass
class ProjectionReadinessResult:
    """Complete projection readiness assessment."""

    projections: list[dict[str, Any]] = field(default_factory=list)
    cross_projection_reuse: float = 0.0
    total_unique_capabilities: int = 0
    shared_capabilities: int = 0
    overall_readiness: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "projections": self.projections,
            "cross_projection_reuse": self.cross_projection_reuse,
            "total_unique_capabilities": self.total_unique_capabilities,
            "shared_capabilities": self.shared_capabilities,
            "overall_readiness": self.overall_readiness,
        }


class ProjectionReadinessBenchmark:
    """Measures projection acceleration from existing capabilities."""

    def __init__(self, existing_capabilities: list[str] | None = None) -> None:
        self._existing = set(existing_capabilities or [])

    def set_existing_capabilities(self, capabilities: list[str]) -> None:
        self._existing = set(capabilities)

    def evaluate(
        self,
        projections: dict[str, list[str]] | None = None,
    ) -> ProjectionReadinessResult:
        """Evaluate readiness for each projection.

        Args:
            projections: Override projection requirements. Defaults to PROJECTION_REQUIREMENTS.

        Returns:
            ProjectionReadinessResult with per-projection coverage and cross-projection reuse.
        """
        proj_reqs = projections or PROJECTION_REQUIREMENTS
        coverages: list[ProjectionCoverage] = []

        for proj_name, requirements in proj_reqs.items():
            matched = [r for r in requirements if self._matches(r)]
            unmatched = [r for r in requirements if not self._matches(r)]
            total = len(requirements)

            coverage = ProjectionCoverage(
                projection_name=proj_name,
                required_capabilities=requirements,
                matched_capabilities=matched,
                unmatched_capabilities=unmatched,
                existing_coverage_pct=round(len(matched) / total, 4) if total > 0 else 0.0,
                net_new_pct=round(len(unmatched) / total, 4) if total > 0 else 1.0,
            )
            coverages.append(coverage)

        # Cross-projection reuse
        all_required: set[str] = set()
        per_projection_sets: list[set[str]] = []
        for proj_name, requirements in proj_reqs.items():
            req_set = set(requirements)
            all_required |= req_set
            per_projection_sets.append(req_set)

        shared = set()
        for cap in all_required:
            count = sum(1 for s in per_projection_sets if cap in s)
            if count >= 2:
                shared.add(cap)

        cross_reuse = round(len(shared) / len(all_required), 4) if all_required else 0.0
        overall = round(sum(c.existing_coverage_pct for c in coverages) / len(coverages), 4) if coverages else 0.0

        return ProjectionReadinessResult(
            projections=[c.to_dict() for c in coverages],
            cross_projection_reuse=cross_reuse,
            total_unique_capabilities=len(all_required),
            shared_capabilities=len(shared),
            overall_readiness=overall,
        )

    def _matches(self, requirement: str) -> bool:
        """Check if a requirement is matched by any existing capability.

        Uses fuzzy matching: exact match, substring, or word overlap.
        """
        req_lower = requirement.lower().replace("_", " ")
        req_words = set(req_lower.split())

        for cap in self._existing:
            cap_lower = cap.lower().replace("_", " ")
            cap_words = set(cap_lower.split())

            # Exact match
            if req_lower == cap_lower:
                return True

            # Substring match
            if req_lower in cap_lower or cap_lower in req_lower:
                return True

            # Word overlap (≥50% of requirement words)
            overlap = req_words & cap_words
            if len(overlap) >= max(1, len(req_words) * 0.5):
                return True

        return False
