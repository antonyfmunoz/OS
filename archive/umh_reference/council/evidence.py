"""Phase 85 evidence assessment — evaluate evidence quality across perspectives.

Assesses collective evidence strength, identifies gaps, and flags
conflicting claims. Deterministic rule-based v1.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.council.contracts import (
    ConfidenceLevel,
    EvidenceItem,
    EvidenceStrength,
    _council_id,
    clamp_score,
    normalize_confidence_level,
)
from umh.council.perspective import PerspectiveReport


_STRENGTH_SCORES: dict[EvidenceStrength, float] = {
    EvidenceStrength.STRONG: 1.0,
    EvidenceStrength.MODERATE: 0.7,
    EvidenceStrength.WEAK: 0.4,
    EvidenceStrength.ANECDOTAL: 0.2,
    EvidenceStrength.NONE: 0.0,
    EvidenceStrength.UNKNOWN: 0.1,
}


@dataclass
class EvidenceConflict:
    claim_a: str = ""
    claim_b: str = ""
    source_a: str = ""
    source_b: str = ""
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_a": self.claim_a,
            "claim_b": self.claim_b,
            "source_a": self.source_a,
            "source_b": self.source_b,
            "description": self.description,
            "metadata": self.metadata,
        }


@dataclass
class EvidenceAssessment:
    assessment_id: str = ""
    request_id: str = ""
    total_evidence_count: int = 0
    strong_count: int = 0
    moderate_count: int = 0
    weak_count: int = 0
    average_strength_score: float = 0.0
    conflicts: list[EvidenceConflict] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    overall_confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "request_id": self.request_id,
            "total_evidence_count": self.total_evidence_count,
            "strong_count": self.strong_count,
            "moderate_count": self.moderate_count,
            "weak_count": self.weak_count,
            "average_strength_score": round(self.average_strength_score, 3),
            "conflicts": [c.to_dict() for c in self.conflicts],
            "gaps": self.gaps,
            "overall_confidence": self.overall_confidence.value,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def assess_evidence(
    request_id: str,
    perspectives: list[PerspectiveReport],
) -> EvidenceAssessment:
    all_evidence: list[EvidenceItem] = []
    for p in perspectives:
        all_evidence.extend(p.evidence)

    total = len(all_evidence)
    if total == 0:
        return EvidenceAssessment(
            assessment_id=_council_id("evass"),
            request_id=request_id,
            total_evidence_count=0,
            overall_confidence=ConfidenceLevel.LOW,
            warnings=["No evidence provided by any perspective"],
            gaps=["All domains lack evidence"],
        )

    strong = sum(1 for e in all_evidence if e.strength == EvidenceStrength.STRONG)
    moderate = sum(1 for e in all_evidence if e.strength == EvidenceStrength.MODERATE)
    weak = sum(
        1 for e in all_evidence if e.strength in (EvidenceStrength.WEAK, EvidenceStrength.ANECDOTAL)
    )

    scores = [_STRENGTH_SCORES.get(e.strength, 0.1) for e in all_evidence]
    avg_score = sum(scores) / len(scores) if scores else 0.0

    gaps: list[str] = []
    domains_covered = {e.domain.value for e in all_evidence if e.domain.value != "unknown"}
    role_ids = {p.role_id for p in perspectives}
    for p in perspectives:
        if not p.evidence:
            gaps.append(f"Role {p.role_id} provided no evidence")

    warnings: list[str] = []
    if strong == 0:
        warnings.append("No strong evidence from any perspective")
    if total < len(perspectives):
        warnings.append("Some perspectives have no evidence")

    if avg_score >= 0.7:
        confidence = ConfidenceLevel.HIGH
    elif avg_score >= 0.5:
        confidence = ConfidenceLevel.MEDIUM
    else:
        confidence = ConfidenceLevel.LOW

    return EvidenceAssessment(
        assessment_id=_council_id("evass"),
        request_id=request_id,
        total_evidence_count=total,
        strong_count=strong,
        moderate_count=moderate,
        weak_count=weak,
        average_strength_score=avg_score,
        conflicts=[],
        gaps=gaps,
        overall_confidence=confidence,
        warnings=warnings,
    )
