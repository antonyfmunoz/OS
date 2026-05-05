"""
Template promotion contracts for Phase 96.4.

Instance-derived patterns may become reusable templates,
but only through explicit abstraction and founder approval.
Raw instance facts cannot be promoted directly to global canon.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PromotionStatus(str, Enum):
    IDENTIFIED = "identified"
    ABSTRACTED = "abstracted"
    PRIVACY_REVIEWED = "privacy_reviewed"
    APPROVED = "approved"
    PROMOTED = "promoted"
    REJECTED = "rejected"
    REQUIRES_REVIEW = "requires_review"


@dataclass
class TemplatePatternCandidate:
    """A pattern that may become a reusable template."""

    source_instance_id: str
    source_records: list[str] = field(default_factory=list)
    pattern_name: str = ""
    generalized_description: str = ""
    raw_instance_details_removed: bool = False
    privacy_review_status: str = "not_reviewed"
    abstraction_quality: str = "not_assessed"
    reusable_contexts: list[str] = field(default_factory=list)
    approval_required: bool = True
    promotion_status: PromotionStatus = PromotionStatus.REQUIRES_REVIEW

    def is_ready_for_promotion(self) -> bool:
        return (
            self.raw_instance_details_removed
            and self.privacy_review_status == "passed"
            and self.promotion_status == PromotionStatus.APPROVED
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_instance_id": self.source_instance_id,
            "source_records": self.source_records,
            "pattern_name": self.pattern_name,
            "generalized_description": self.generalized_description,
            "raw_instance_details_removed": self.raw_instance_details_removed,
            "privacy_review_status": self.privacy_review_status,
            "abstraction_quality": self.abstraction_quality,
            "reusable_contexts": self.reusable_contexts,
            "approval_required": self.approval_required,
            "promotion_status": self.promotion_status.value,
        }
