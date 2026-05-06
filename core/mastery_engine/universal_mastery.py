"""Universal Mastery / Competence Layer.

Tool Mastery Engine (TME) is the first implementation slice of a larger
Universal Mastery / Competence Layer. UMH must not execute merely
because it has access to a tool, model, environment, data source,
human, or adapter.

Before execution, UMH must possess or acquire sufficient scoped,
versioned, testable mastery of the action, domain, tool/system, adapter
boundary, environment, data, model/worker, human approval path,
governance constraints, success criteria, and proof requirements.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MasteryCategory(str, Enum):
    TOOL = "tool"
    ACTION = "action"
    DOMAIN = "domain"
    ENVIRONMENT = "environment"
    DATA = "data"
    MODEL = "model"
    ADAPTER_BOUNDARY = "adapter_boundary"
    HUMAN_APPROVAL = "human_approval"
    GOVERNANCE = "governance"
    CONTEXT = "context"
    PHYSICAL_WORLD = "physical_world"


class MasteryStatus(str, Enum):
    MISSING = "missing"
    PARTIAL = "partial"
    PROVISIONAL = "provisional"
    CURRENT = "current"
    STALE = "stale"
    BLOCKED = "blocked"
    VERIFIED = "verified"


@dataclass
class UniversalMasteryDecision:
    action_id: str = ""
    required_categories: list[str] = field(default_factory=list)
    satisfied_categories: list[str] = field(default_factory=list)
    missing_categories: list[str] = field(default_factory=list)
    stale_categories: list[str] = field(default_factory=list)
    proof_required: bool = False
    can_execute: bool = False
    blockers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "required_categories": self.required_categories,
            "satisfied_categories": self.satisfied_categories,
            "missing_categories": self.missing_categories,
            "stale_categories": self.stale_categories,
            "proof_required": self.proof_required,
            "can_execute": self.can_execute,
            "blockers": self.blockers,
            "notes": self.notes,
        }


def build_universal_mastery_decision(
    action_id: str,
    required_categories: list[str] | None = None,
    satisfied_categories: list[str] | None = None,
    missing_categories: list[str] | None = None,
    stale_categories: list[str] | None = None,
    proof_required: bool = False,
) -> UniversalMasteryDecision:
    req = required_categories or []
    sat = satisfied_categories or []
    mis = missing_categories or []
    stale = stale_categories or []

    blockers: list[str] = []
    if mis:
        blockers.append(f"MISSING_MASTERY: {', '.join(mis)}")
    if stale:
        blockers.append(f"STALE_MASTERY: {', '.join(stale)}")

    can_execute = len(mis) == 0 and len(stale) == 0

    return UniversalMasteryDecision(
        action_id=action_id,
        required_categories=req,
        satisfied_categories=sat,
        missing_categories=mis,
        stale_categories=stale,
        proof_required=proof_required,
        can_execute=can_execute,
        blockers=blockers,
    )


def mastery_category_required_for_execution(category: MasteryCategory) -> bool:
    return True


def mastery_decision_blocks_execution(decision: UniversalMasteryDecision) -> bool:
    return not decision.can_execute


def summarize_universal_mastery_decision(
    decision: UniversalMasteryDecision,
) -> dict[str, Any]:
    return {
        "action_id": decision.action_id,
        "can_execute": decision.can_execute,
        "required_count": len(decision.required_categories),
        "satisfied_count": len(decision.satisfied_categories),
        "missing_count": len(decision.missing_categories),
        "stale_count": len(decision.stale_categories),
        "blocker_count": len(decision.blockers),
    }
