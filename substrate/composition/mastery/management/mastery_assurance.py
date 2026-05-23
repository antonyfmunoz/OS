"""Mastery Assurance Gate for the Tool Mastery Engine.

No worker may execute with an external tool unless TME has assured
a complete, fresh, up-to-date mastery pack for that tool, or the
founder explicitly waives the requirement.

TME is a UMH substrate subsystem. EOS is one platform consumer.

This module provides pure helper functions that evaluate mastery
readiness and produce a blocking/allowing decision. It does not
perform I/O — callers supply pack metadata and text content.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Any


class MasteryAssuranceStatus(str, Enum):
    ASSURED = "assured"
    MISSING_PACK = "missing_pack"
    STALE_PACK = "stale_pack"
    INCOMPLETE_PACK = "incomplete_pack"
    QUALITY_BELOW_THRESHOLD = "quality_below_threshold"
    RESEARCH_REQUIRED = "research_required"
    UPDATE_REQUIRED = "update_required"
    BLOCKED = "blocked"
    WAIVED_BY_FOUNDER = "waived_by_founder"


class RecommendedFlow(str, Enum):
    CREATE_FLOW = "create_flow"
    RE_RESEARCH_FLOW = "re_research_flow"
    INCREMENTAL_UPDATE_FLOW = "incremental_update_flow"
    ABSORPTION_FLOW = "absorption_flow"
    PROCEED = "proceed"


STALENESS_THRESHOLDS: dict[str, int] = {
    "fast": 14,
    "medium": 45,
    "stable": 90,
    "slow": 120,
}

QUALITY_TIER_MINIMUMS: dict[str, int] = {
    "critical": 20_000,
    "core": 15_000,
    "standard": 8_000,
    "light": 5_000,
}

_COMPLETENESS_SECTIONS = [
    "authentication",
    "rate limits",
    "error codes",
    "sdk idioms",
    "anti-patterns",
    "design intent",
    "gotchas",
]

_ALIAS_MAP: dict[str, str] = {
    "postgres": "neon_postgres",
    "postgresql": "neon_postgres",
    "pg": "neon_postgres",
    "neon": "neon_postgres",
    "google sheets": "google_sheets",
    "gsheets": "google_sheets",
    "gcp": "google_cloud",
    "google cloud": "google_cloud",
    "meta": "instagram",
    "facebook": "instagram",
    "drizzle": "drizzle_orm",
}


@dataclass
class MasteryAssuranceDecision:
    tool_name: str
    normalized_tool_name: str
    required_packs: list[str] = field(default_factory=list)
    found_packs: list[str] = field(default_factory=list)
    missing_packs: list[str] = field(default_factory=list)
    stale_packs: list[str] = field(default_factory=list)
    incomplete_packs: list[str] = field(default_factory=list)
    freshness_status: str = ""
    quality_status: str = ""
    status: MasteryAssuranceStatus = MasteryAssuranceStatus.BLOCKED
    action_required: str = ""
    can_execute: bool = False
    block_reason: str = ""
    recommended_flow: RecommendedFlow = RecommendedFlow.CREATE_FLOW
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "normalized_tool_name": self.normalized_tool_name,
            "required_packs": self.required_packs,
            "found_packs": self.found_packs,
            "missing_packs": self.missing_packs,
            "stale_packs": self.stale_packs,
            "incomplete_packs": self.incomplete_packs,
            "freshness_status": self.freshness_status,
            "quality_status": self.quality_status,
            "status": self.status.value,
            "action_required": self.action_required,
            "can_execute": self.can_execute,
            "block_reason": self.block_reason,
            "recommended_flow": self.recommended_flow.value,
            "notes": self.notes,
        }


def normalize_tool_name(tool_name: str) -> str:
    lower = tool_name.strip().lower()
    if lower in _ALIAS_MAP:
        return _ALIAS_MAP[lower]
    return re.sub(r"[^a-z0-9]+", "_", lower).strip("_")


def determine_staleness_threshold(speed_category: str) -> int:
    return STALENESS_THRESHOLDS.get(speed_category, STALENESS_THRESHOLDS["medium"])


def evaluate_pack_freshness(
    last_researched: str | None,
    speed_category: str = "medium",
    current_date: date | None = None,
) -> str:
    """Return 'fresh', 'near_stale', 'stale', or 'missing_date'."""
    if not last_researched:
        return "missing_date"
    today = current_date or date.today()
    try:
        lr_date = date.fromisoformat(last_researched)
    except ValueError:
        return "missing_date"
    threshold = determine_staleness_threshold(speed_category)
    age = (today - lr_date).days
    if age > threshold:
        return "stale"
    if age > int(threshold * 0.8):
        return "near_stale"
    return "fresh"


def evaluate_pack_quality(pack_text: str, tier: str = "standard") -> str:
    """Return 'pass' or 'below_threshold'."""
    minimum = QUALITY_TIER_MINIMUMS.get(tier, QUALITY_TIER_MINIMUMS["standard"])
    if len(pack_text) >= minimum:
        return "pass"
    return "below_threshold"


def evaluate_pack_completeness(pack_text: str) -> str:
    """Return 'complete' or 'incomplete'."""
    lower = pack_text.lower()
    for section in _COMPLETENESS_SECTIONS:
        if section not in lower:
            return "incomplete"
    return "complete"


def determine_required_tme_flow(
    pack_exists: bool,
    freshness: str,
    completeness: str,
    quality: str,
) -> RecommendedFlow:
    if not pack_exists:
        return RecommendedFlow.CREATE_FLOW
    if freshness == "stale" or freshness == "missing_date":
        return RecommendedFlow.RE_RESEARCH_FLOW
    if completeness == "incomplete" or quality == "below_threshold":
        return RecommendedFlow.INCREMENTAL_UPDATE_FLOW
    return RecommendedFlow.PROCEED


def ensure_mastery_before_execution(
    tool_name: str,
    pack_exists: bool,
    pack_text: str = "",
    last_researched: str | None = None,
    speed_category: str = "medium",
    tier: str = "standard",
    founder_waiver: bool = False,
    current_date: date | None = None,
) -> MasteryAssuranceDecision:
    """Evaluate mastery and produce a blocking/allowing decision."""
    normalized = normalize_tool_name(tool_name)

    decision = MasteryAssuranceDecision(
        tool_name=tool_name,
        normalized_tool_name=normalized,
        required_packs=[normalized],
    )

    if founder_waiver:
        decision.status = MasteryAssuranceStatus.WAIVED_BY_FOUNDER
        decision.can_execute = True
        decision.recommended_flow = RecommendedFlow.PROCEED
        decision.notes.append("founder explicitly waived mastery requirement")
        decision.found_packs = [normalized] if pack_exists else []
        decision.missing_packs = [] if pack_exists else [normalized]
        return decision

    if not pack_exists:
        decision.status = MasteryAssuranceStatus.MISSING_PACK
        decision.can_execute = False
        decision.block_reason = f"no mastery pack for {normalized}"
        decision.missing_packs = [normalized]
        decision.recommended_flow = RecommendedFlow.CREATE_FLOW
        decision.action_required = "create mastery pack"
        return decision

    decision.found_packs = [normalized]

    freshness = evaluate_pack_freshness(last_researched, speed_category, current_date)
    decision.freshness_status = freshness

    quality = evaluate_pack_quality(pack_text, tier)
    decision.quality_status = quality

    completeness = evaluate_pack_completeness(pack_text)

    flow = determine_required_tme_flow(True, freshness, completeness, quality)
    decision.recommended_flow = flow

    if freshness in ("stale", "missing_date"):
        decision.status = MasteryAssuranceStatus.STALE_PACK
        decision.can_execute = False
        decision.block_reason = f"mastery pack for {normalized} is stale"
        decision.stale_packs = [normalized]
        decision.action_required = "re-research mastery pack"
        return decision

    if completeness == "incomplete":
        decision.status = MasteryAssuranceStatus.INCOMPLETE_PACK
        decision.can_execute = False
        decision.block_reason = f"mastery pack for {normalized} is incomplete"
        decision.incomplete_packs = [normalized]
        decision.action_required = "update mastery pack"
        return decision

    if quality == "below_threshold":
        decision.status = MasteryAssuranceStatus.QUALITY_BELOW_THRESHOLD
        decision.can_execute = False
        decision.block_reason = f"mastery pack for {normalized} below {tier} quality tier"
        decision.action_required = "expand mastery pack content"
        return decision

    decision.status = MasteryAssuranceStatus.ASSURED
    decision.can_execute = True
    decision.recommended_flow = RecommendedFlow.PROCEED
    return decision


def mastery_assurance_blocks_execution(decision: MasteryAssuranceDecision) -> bool:
    return not decision.can_execute
