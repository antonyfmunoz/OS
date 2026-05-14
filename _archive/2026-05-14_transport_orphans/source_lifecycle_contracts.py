"""
Source lifecycle contracts for Phase 96.3.

Ingest-first / review-after lifecycle:
1. Discover → 2. Authorize → 3. Ingest raw → 4. Normalize →
5. Validate coverage → 6. Parity validate → 7. Review →
8. Promote/archive/defer → 9. Update memory

Review gates block promotion, not ingestion.
Raw source records are immutable.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SourceLifecycleStage(str, Enum):
    DISCOVERED = "discovered"
    AUTHORIZED = "authorized"
    INGESTED_RAW = "ingested_raw"
    NORMALIZED_CANONICAL_RECORD = "normalized_canonical_record"
    COVERAGE_VALIDATED = "coverage_validated"
    PARITY_VALIDATED = "parity_validated"
    REVIEWED = "reviewed"
    PROMOTED = "promoted"
    ARCHIVED = "archived"
    DEFERRED = "deferred"
    REQUIRES_FOUNDER_DECISION = "requires_founder_decision"


class SourceReviewType(str, Enum):
    MEMORY_PROMOTION_REVIEW = "memory_promotion_review"
    CANONICALIZATION_REVIEW = "canonicalization_review"
    CONTRADICTION_REVIEW = "contradiction_review"
    STALE_ASSUMPTION_REVIEW = "stale_assumption_review"
    REDUNDANCY_REVIEW = "redundancy_review"
    NEXT_CRAWL_REVIEW = "next_crawl_review"
    SAFETY_REVIEW = "safety_review"


class SourceIngestionRule(str, Enum):
    REVIEW_AFTER_INGESTION = "review_after_ingestion"
    SAFETY_SCOPE_AUTH_BEFORE_INGESTION = "safety_scope_auth_before_ingestion"
    PROMOTION_AFTER_REVIEW_ONLY = "promotion_after_review_only"
    RAW_SOURCE_RECORDS_IMMUTABLE = "raw_source_records_immutable"
    INTERPRETATION_SEPARATE_FROM_RAW = "interpretation_separate_from_raw"
    NO_MEMORY_PROMOTION_WITHOUT_REVIEW = "no_memory_promotion_without_review"


_STAGES_BEFORE_REVIEW = {
    SourceLifecycleStage.DISCOVERED,
    SourceLifecycleStage.AUTHORIZED,
    SourceLifecycleStage.INGESTED_RAW,
    SourceLifecycleStage.NORMALIZED_CANONICAL_RECORD,
    SourceLifecycleStage.COVERAGE_VALIDATED,
    SourceLifecycleStage.PARITY_VALIDATED,
}

_STAGES_REQUIRING_REVIEW = {
    SourceLifecycleStage.PROMOTED,
}

_PRE_INGESTION_GATES = {
    SourceLifecycleStage.DISCOVERED,
    SourceLifecycleStage.AUTHORIZED,
}


def can_ingest_without_review(stage: SourceLifecycleStage) -> bool:
    """Raw ingestion does not require review. Review gates block promotion."""
    return stage in _STAGES_BEFORE_REVIEW


def requires_review_before_promotion(stage: SourceLifecycleStage) -> bool:
    """Promotion requires explicit review."""
    return stage in _STAGES_REQUIRING_REVIEW or stage == SourceLifecycleStage.REVIEWED


def requires_safety_auth_before_ingestion() -> bool:
    """Safety, scope, and auth checks must happen before ingestion."""
    return True


def is_raw_record_immutable() -> bool:
    """Raw source records must not be modified after ingestion."""
    return True


def is_interpretation_separate_from_raw() -> bool:
    """Summaries and interpretations are separate from raw records."""
    return True


@dataclass
class SourceLifecycleRecord:
    """Tracks a source through the ingest-first lifecycle."""

    source_id: str
    current_stage: SourceLifecycleStage = SourceLifecycleStage.DISCOVERED
    authorized: bool = False
    scope_verified: bool = False
    safety_verified: bool = False
    raw_ingested: bool = False
    normalized: bool = False
    coverage_validated: bool = False
    parity_validated: bool = False
    reviewed: bool = False
    promoted: bool = False
    review_types_completed: list[SourceReviewType] = field(default_factory=list)
    notes: str = ""

    def can_proceed_to_ingestion(self) -> bool:
        return self.authorized and self.scope_verified and self.safety_verified

    def can_proceed_to_promotion(self) -> bool:
        return self.reviewed and not self.promoted

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "current_stage": self.current_stage.value,
            "authorized": self.authorized,
            "scope_verified": self.scope_verified,
            "safety_verified": self.safety_verified,
            "raw_ingested": self.raw_ingested,
            "normalized": self.normalized,
            "coverage_validated": self.coverage_validated,
            "parity_validated": self.parity_validated,
            "reviewed": self.reviewed,
            "promoted": self.promoted,
            "review_types_completed": [r.value for r in self.review_types_completed],
            "notes": self.notes,
        }
