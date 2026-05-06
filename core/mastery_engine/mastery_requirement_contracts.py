"""Mastery requirement contracts for the Universal Mastery Layer.

Each mastery requirement defines scoped, versioned, testable, proof-
backed competence that UMH must possess before execution.

Mastery is scoped — not "master Google Workspace" but "master Google
Docs tab-aware extraction for W0-001 under read-only OAuth/API
constraints with includeTabsContent=true, child tab recursion, source
provenance, and coverage validation."

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .universal_mastery import MasteryCategory, MasteryStatus


@dataclass
class MasteryRequirement:
    mastery_id: str = ""
    category: MasteryCategory = MasteryCategory.TOOL
    target: str = ""
    capability_scope: str = ""
    risk_level: str = "low"
    required_freshness: str = "medium"
    required_tests: list[str] = field(default_factory=list)
    required_proof: list[str] = field(default_factory=list)
    current_status: MasteryStatus = MasteryStatus.MISSING
    gaps: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mastery_id": self.mastery_id,
            "category": self.category.value,
            "target": self.target,
            "capability_scope": self.capability_scope,
            "risk_level": self.risk_level,
            "required_freshness": self.required_freshness,
            "required_tests": self.required_tests,
            "required_proof": self.required_proof,
            "current_status": self.current_status.value,
            "gaps": self.gaps,
            "notes": self.notes,
        }


def build_mastery_requirement(
    mastery_id: str,
    category: MasteryCategory = MasteryCategory.TOOL,
    target: str = "",
    capability_scope: str = "",
    risk_level: str = "low",
    required_freshness: str = "medium",
    required_tests: list[str] | None = None,
    required_proof: list[str] | None = None,
    current_status: MasteryStatus = MasteryStatus.MISSING,
    gaps: list[str] | None = None,
) -> MasteryRequirement:
    return MasteryRequirement(
        mastery_id=mastery_id,
        category=category,
        target=target,
        capability_scope=capability_scope,
        risk_level=risk_level,
        required_freshness=required_freshness,
        required_tests=required_tests or [],
        required_proof=required_proof or [],
        current_status=current_status,
        gaps=gaps or [],
    )


def mastery_requirement_is_satisfied(requirement: MasteryRequirement) -> bool:
    return requirement.current_status in (
        MasteryStatus.CURRENT,
        MasteryStatus.VERIFIED,
    )


def mastery_requirement_is_stale(requirement: MasteryRequirement) -> bool:
    return requirement.current_status == MasteryStatus.STALE


def mastery_requirement_blocks_execution(requirement: MasteryRequirement) -> bool:
    if requirement.current_status in (MasteryStatus.MISSING, MasteryStatus.BLOCKED):
        return True
    if requirement.current_status == MasteryStatus.STALE and requirement.risk_level in (
        "high",
        "critical",
    ):
        return True
    if requirement.required_proof and requirement.current_status != MasteryStatus.VERIFIED:
        return True
    return False


def summarize_mastery_requirement(requirement: MasteryRequirement) -> dict[str, Any]:
    return {
        "mastery_id": requirement.mastery_id,
        "category": requirement.category.value,
        "target": requirement.target,
        "status": requirement.current_status.value,
        "satisfied": mastery_requirement_is_satisfied(requirement),
        "stale": mastery_requirement_is_stale(requirement),
        "blocks_execution": mastery_requirement_blocks_execution(requirement),
        "gap_count": len(requirement.gaps),
    }
