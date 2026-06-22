"""Audit — Empire Readiness.

Campaign 23B — Category P Audit.
Tier 3: organism audit (inspects system state, generates a report — no task execution).

Measures whether existing UMH capabilities are ready to accelerate future
empire projections (Game of Lyfe, music, fiction, acquisitions) and, optionally,
the current projections (EOS/LOS/COS). Uses the same fuzzy capability matching
as the projection-readiness benchmark. All metrics deterministic. No LLM calls.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any

from substrate.organism.benchmarks.projection_readiness import PROJECTION_REQUIREMENTS

logger = logging.getLogger(__name__)


FUTURE_PROJECTIONS: dict[str, list[str]] = {
    "game_of_lyfe": [
        "gamification_engine",
        "achievement_system",
        "leaderboard",
        "progression_tracking",
        "challenge_creation",
        "reward_distribution",
        "social_features",
        "analytics_dashboard",
    ],
    "music": [
        "audio_processing",
        "distribution_pipeline",
        "royalty_tracking",
        "collaboration_tools",
        "catalog_management",
        "streaming_integration",
    ],
    "fiction": [
        "content_management",
        "publishing_workflow",
        "audience_analytics",
        "distribution_channels",
        "revision_tracking",
        "feedback_collection",
    ],
    "acquisitions": [
        "due_diligence_framework",
        "valuation_models",
        "integration_planning",
        "portfolio_management",
        "risk_assessment",
        "deal_pipeline",
    ],
}


@dataclass
class ProjectionScore:
    """Capability coverage for a single projection."""

    projection_name: str = ""
    required_capabilities: list[str] = field(default_factory=list)
    matched_capabilities: list[str] = field(default_factory=list)
    missing_capabilities: list[str] = field(default_factory=list)
    coverage_pct: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EmpireReadinessReport:
    """Result of an empire-readiness audit."""

    projection_scores: dict[str, float] = field(default_factory=dict)
    projection_details: list[ProjectionScore] = field(default_factory=list)
    cross_projection_reuse: float = 0.0
    overall_readiness: float = 0.0
    future_projection_count: int = 0
    total_missing_capabilities: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EmpireReadinessAudit:
    """Audits readiness to launch future empire projections."""

    def __init__(self, include_existing: bool = True) -> None:
        self._include_existing = include_existing

    def run(
        self,
        existing_capabilities: list[str] | None = None,
        projections: dict[str, list[str]] | None = None,
    ) -> EmpireReadinessReport:
        """Run the empire-readiness audit.

        Evaluates :data:`FUTURE_PROJECTIONS` (plus the current
        ``PROJECTION_REQUIREMENTS`` when ``include_existing`` is set) against the
        existing capability set using fuzzy matching.
        """
        existing = set(existing_capabilities or [])

        proj_reqs: dict[str, list[str]] = {}
        proj_reqs.update(FUTURE_PROJECTIONS)
        if self._include_existing:
            proj_reqs.update(PROJECTION_REQUIREMENTS)
        if projections is not None:
            proj_reqs.update(projections)

        if not proj_reqs:
            return EmpireReadinessReport()

        scores: list[ProjectionScore] = []
        for name, requirements in proj_reqs.items():
            matched = [r for r in requirements if self._matches(r, existing)]
            missing = [r for r in requirements if r not in matched]
            total = len(requirements)
            coverage = round(len(matched) / total, 4) if total > 0 else 0.0
            scores.append(
                ProjectionScore(
                    projection_name=name,
                    required_capabilities=list(requirements),
                    matched_capabilities=matched,
                    missing_capabilities=missing,
                    coverage_pct=coverage,
                )
            )

        projection_scores = {s.projection_name: s.coverage_pct for s in scores}
        overall = round(sum(s.coverage_pct for s in scores) / len(scores), 4) if scores else 0.0

        cross_reuse = self._cross_projection_reuse(proj_reqs)

        # Aggregate unique missing capabilities, preserving first-seen order.
        missing_seen: dict[str, None] = {}
        for s in scores:
            for cap in s.missing_capabilities:
                missing_seen.setdefault(cap, None)

        return EmpireReadinessReport(
            projection_scores=projection_scores,
            projection_details=scores,
            cross_projection_reuse=cross_reuse,
            overall_readiness=overall,
            future_projection_count=len(FUTURE_PROJECTIONS),
            total_missing_capabilities=list(missing_seen.keys()),
        )

    # ------------------------------------------------------------------
    # Matching (mirrors projection_readiness benchmark)
    # ------------------------------------------------------------------

    @staticmethod
    def _matches(requirement: str, existing: set[str]) -> bool:
        req_lower = requirement.lower().replace("_", " ")
        req_words = set(req_lower.split())

        for cap in existing:
            cap_lower = cap.lower().replace("_", " ")
            cap_words = set(cap_lower.split())

            if req_lower == cap_lower:
                return True
            if req_lower in cap_lower or cap_lower in req_lower:
                return True
            overlap = req_words & cap_words
            if len(overlap) >= max(1, len(req_words) * 0.5):
                return True

        return False

    @staticmethod
    def _cross_projection_reuse(proj_reqs: dict[str, list[str]]) -> float:
        all_required: set[str] = set()
        per_projection_sets: list[set[str]] = []
        for requirements in proj_reqs.values():
            req_set = set(requirements)
            all_required |= req_set
            per_projection_sets.append(req_set)

        if not all_required:
            return 0.0

        shared = 0
        for cap in all_required:
            count = sum(1 for s in per_projection_sets if cap in s)
            if count >= 2:
                shared += 1

        return round(shared / len(all_required), 4)
