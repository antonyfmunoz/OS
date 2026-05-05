"""Phase 85 council contracts — shared enums, types, and base structures.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CouncilStatus(str, Enum):
    DRAFT = "draft"
    CONVENED = "convened"
    DELIBERATING = "deliberating"
    SYNTHESIZED = "synthesized"
    ADVISORY_ISSUED = "advisory_issued"
    REJECTED = "rejected"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


class DeliberationDomain(str, Enum):
    BUSINESS = "business"
    SOFTWARE = "software"
    HUMAN = "human"
    CONTENT = "content"
    UMH_INTERNAL = "umh_internal"
    CROSS_DOMAIN = "cross_domain"
    UNKNOWN = "unknown"


class UrgencyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"
    UNKNOWN = "unknown"


class EvidenceStrength(str, Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    ANECDOTAL = "anecdotal"
    NONE = "none"
    UNKNOWN = "unknown"


class AssumptionStatus(str, Enum):
    STATED = "stated"
    VALIDATED = "validated"
    CHALLENGED = "challenged"
    INVALIDATED = "invalidated"
    UNKNOWN = "unknown"


def normalize_council_status(value: str) -> CouncilStatus:
    v = value.strip().lower()
    for m in CouncilStatus:
        if m.value == v:
            return m
    return CouncilStatus.UNKNOWN


def normalize_deliberation_domain(value: str) -> DeliberationDomain:
    v = value.strip().lower().replace(" ", "_").replace("-", "_")
    for m in DeliberationDomain:
        if m.value == v:
            return m
    return DeliberationDomain.UNKNOWN


def normalize_urgency_level(value: str) -> UrgencyLevel:
    v = value.strip().lower()
    for m in UrgencyLevel:
        if m.value == v:
            return m
    return UrgencyLevel.UNKNOWN


def normalize_confidence_level(value: str) -> ConfidenceLevel:
    v = value.strip().lower().replace(" ", "_").replace("-", "_")
    for m in ConfidenceLevel:
        if m.value == v:
            return m
    return ConfidenceLevel.UNKNOWN


def normalize_evidence_strength(value: str) -> EvidenceStrength:
    v = value.strip().lower()
    for m in EvidenceStrength:
        if m.value == v:
            return m
    return EvidenceStrength.UNKNOWN


def normalize_assumption_status(value: str) -> AssumptionStatus:
    v = value.strip().lower()
    for m in AssumptionStatus:
        if m.value == v:
            return m
    return AssumptionStatus.UNKNOWN


def _council_id(prefix: str = "council") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def clamp_score(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    if not isinstance(value, (int, float)):
        return lo
    return max(lo, min(hi, float(value)))


@dataclass
class EvidenceItem:
    evidence_id: str = ""
    claim: str = ""
    strength: EvidenceStrength = EvidenceStrength.UNKNOWN
    source: str = ""
    domain: DeliberationDomain = DeliberationDomain.UNKNOWN
    confidence: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "claim": self.claim,
            "strength": self.strength.value,
            "source": self.source,
            "domain": self.domain.value,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidenceItem:
        return cls(
            evidence_id=data.get("evidence_id", _council_id("ev")),
            claim=data.get("claim", ""),
            strength=normalize_evidence_strength(data.get("strength", "unknown")),
            source=data.get("source", ""),
            domain=normalize_deliberation_domain(data.get("domain", "unknown")),
            confidence=clamp_score(data.get("confidence", 0.5)),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Assumption:
    assumption_id: str = ""
    statement: str = ""
    status: AssumptionStatus = AssumptionStatus.STATED
    basis: str = ""
    risk_if_wrong: str = ""
    confidence: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "assumption_id": self.assumption_id,
            "statement": self.statement,
            "status": self.status.value,
            "basis": self.basis,
            "risk_if_wrong": self.risk_if_wrong,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Assumption:
        return cls(
            assumption_id=data.get("assumption_id", _council_id("asm")),
            statement=data.get("statement", ""),
            status=normalize_assumption_status(data.get("status", "stated")),
            basis=data.get("basis", ""),
            risk_if_wrong=data.get("risk_if_wrong", ""),
            confidence=clamp_score(data.get("confidence", 0.5)),
            metadata=data.get("metadata", {}),
        )
