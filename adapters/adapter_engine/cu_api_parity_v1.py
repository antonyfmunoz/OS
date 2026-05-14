"""CU / API Parity Validator v1 for the UMH substrate layer.

Validates that Computer Use extraction and API extraction produce
equivalent results for the same configured safe document.
Generates parity confidence scores and captures discrepancies.

Never treats CU/OCR as identical to API without confidence downgrade.

UMH substrate subsystem. Phase 96.8AB.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .google_docs_adapter_v1 import (
    ExtractionResult,
    NormalizedExtraction,
)


class ParityConfidence(str, Enum):
    EXACT = "exact"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NO_PARITY = "no_parity"


class ParityStatus(str, Enum):
    NOT_CHECKED = "not_checked"
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"
    DEGRADED = "degraded"


PARITY_FORBIDDEN_ACTIONS = frozenset(
    {
        "arbitrary_doc_comparison",
        "drive_wide_scan",
        "silent_fallback",
        "mutation",
        "ocr_as_identical_without_downgrade",
    }
)


@dataclass
class ParityCheck:
    """A single parity check between CU and API for one field."""

    field_name: str
    cu_value: str
    api_value: str
    match: bool = False
    discrepancy: str = ""

    def __post_init__(self) -> None:
        self.match = self.cu_value == self.api_value
        if not self.match:
            self.discrepancy = (
                f"{self.field_name}: cu='{self.cu_value[:100]}' api='{self.api_value[:100]}'"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_name": self.field_name,
            "cu_value_preview": self.cu_value[:100],
            "api_value_preview": self.api_value[:100],
            "match": self.match,
            "discrepancy": self.discrepancy,
        }


@dataclass
class ExtractionComparison:
    """Side-by-side comparison of CU and API extractions."""

    comparison_id: str
    doc_url_or_id: str
    doc_title: str
    cu_extraction_id: str
    api_extraction_id: str
    checks: list[ParityCheck] = field(default_factory=list)
    timestamp: str = ""
    trace_id: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.comparison_id:
            self.comparison_id = f"PARITY-CMP-{uuid.uuid4().hex[:8]}"

    @property
    def total_checks(self) -> int:
        return len(self.checks)

    @property
    def passing_checks(self) -> int:
        return sum(1 for c in self.checks if c.match)

    @property
    def failing_checks(self) -> int:
        return self.total_checks - self.passing_checks

    @property
    def match_ratio(self) -> float:
        if self.total_checks == 0:
            return 0.0
        return self.passing_checks / self.total_checks

    def to_dict(self) -> dict[str, Any]:
        return {
            "comparison_id": self.comparison_id,
            "doc_url_or_id": self.doc_url_or_id,
            "doc_title": self.doc_title,
            "cu_extraction_id": self.cu_extraction_id,
            "api_extraction_id": self.api_extraction_id,
            "total_checks": self.total_checks,
            "passing_checks": self.passing_checks,
            "failing_checks": self.failing_checks,
            "match_ratio": self.match_ratio,
            "checks": [c.to_dict() for c in self.checks],
            "timestamp": self.timestamp,
            "trace_id": self.trace_id,
        }


@dataclass
class ParityResult:
    """Final parity assessment."""

    result_id: str
    comparison_id: str
    confidence: ParityConfidence
    status: ParityStatus
    normalized_hash_match: bool = False
    preview_match: bool = False
    char_count_delta: int = 0
    word_count_delta: int = 0
    discrepancies: list[str] = field(default_factory=list)
    governance_state: str = "governed"
    timestamp: str = ""
    trace_id: str = ""
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.result_id:
            self.result_id = f"PARITY-{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "comparison_id": self.comparison_id,
            "confidence": self.confidence.value,
            "status": self.status.value,
            "normalized_hash_match": self.normalized_hash_match,
            "preview_match": self.preview_match,
            "char_count_delta": self.char_count_delta,
            "word_count_delta": self.word_count_delta,
            "discrepancies": self.discrepancies,
            "governance_state": self.governance_state,
            "timestamp": self.timestamp,
            "trace_id": self.trace_id,
            "notes": self.notes,
        }


def compare_extractions(
    cu_extraction: ExtractionResult,
    api_extraction: ExtractionResult,
    cu_normalized: NormalizedExtraction,
    api_normalized: NormalizedExtraction,
    trace_id: str = "",
) -> ExtractionComparison:
    """Build a field-by-field comparison between CU and API extractions."""
    checks = [
        ParityCheck("doc_title", cu_extraction.doc_title, api_extraction.doc_title),
        ParityCheck("char_count", str(cu_extraction.char_count), str(api_extraction.char_count)),
        ParityCheck("word_count", str(cu_extraction.word_count), str(api_extraction.word_count)),
        ParityCheck(
            "preview",
            cu_extraction.preview[:200],
            api_extraction.preview[:200],
        ),
        ParityCheck(
            "normalized_hash", cu_normalized.normalized_hash, api_normalized.normalized_hash
        ),
        ParityCheck(
            "normalized_char_count",
            str(cu_normalized.char_count),
            str(api_normalized.char_count),
        ),
    ]

    return ExtractionComparison(
        comparison_id="",
        doc_url_or_id=cu_extraction.doc_url_or_id,
        doc_title=cu_extraction.doc_title,
        cu_extraction_id=cu_extraction.extraction_id,
        api_extraction_id=api_extraction.extraction_id,
        checks=checks,
        trace_id=trace_id,
    )


def assess_parity(
    comparison: ExtractionComparison,
    cu_normalized: NormalizedExtraction,
    api_normalized: NormalizedExtraction,
    trace_id: str = "",
) -> ParityResult:
    """Produce a confidence-scored parity result from a comparison."""
    hash_match = cu_normalized.normalized_hash == api_normalized.normalized_hash
    char_delta = abs(cu_normalized.char_count - api_normalized.char_count)
    word_delta = abs(cu_normalized.word_count - api_normalized.word_count)

    preview_match = comparison.checks[3].match if len(comparison.checks) > 3 else False

    discrepancies = [c.discrepancy for c in comparison.checks if not c.match]

    ratio = comparison.match_ratio
    if ratio == 1.0 and hash_match:
        confidence = ParityConfidence.EXACT
        status = ParityStatus.PASSED
    elif ratio >= 0.8 and hash_match:
        confidence = ParityConfidence.HIGH
        status = ParityStatus.PASSED
    elif ratio >= 0.6:
        confidence = ParityConfidence.MEDIUM
        status = ParityStatus.PARTIAL
    elif ratio >= 0.3:
        confidence = ParityConfidence.LOW
        status = ParityStatus.DEGRADED
    else:
        confidence = ParityConfidence.NO_PARITY
        status = ParityStatus.FAILED

    return ParityResult(
        result_id="",
        comparison_id=comparison.comparison_id,
        confidence=confidence,
        status=status,
        normalized_hash_match=hash_match,
        preview_match=preview_match,
        char_count_delta=char_delta,
        word_count_delta=word_delta,
        discrepancies=discrepancies,
        trace_id=trace_id or comparison.trace_id,
    )
