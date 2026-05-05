"""Phase 85 advisory — the final council output. Single coherent advisory record.

Wraps the aggregated recommendation with all analysis artifacts
into a single advisory that can be surfaced to the operator.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.council.aggregation import AggregatedRecommendation
from umh.council.contracts import (
    CouncilStatus,
    ConfidenceLevel,
    _council_id,
    normalize_confidence_level,
    normalize_council_status,
)
from umh.council.disagreement import DisagreementMap
from umh.council.evidence import EvidenceAssessment
from umh.council.gaps import GapAnalysis
from umh.council.scoring import ScoringResult


@dataclass
class CouncilAdvisory:
    advisory_id: str = ""
    request_id: str = ""
    status: CouncilStatus = CouncilStatus.UNKNOWN
    recommendation: AggregatedRecommendation | None = None
    scoring_summary: dict[str, Any] = field(default_factory=dict)
    evidence_summary: dict[str, Any] = field(default_factory=dict)
    gap_summary: dict[str, Any] = field(default_factory=dict)
    disagreement_summary: dict[str, Any] = field(default_factory=dict)
    perspective_count: int = 0
    overall_confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    is_actionable: bool = False
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "advisory_id": self.advisory_id,
            "request_id": self.request_id,
            "status": self.status.value,
            "recommendation": self.recommendation.to_dict() if self.recommendation else None,
            "scoring_summary": self.scoring_summary,
            "evidence_summary": self.evidence_summary,
            "gap_summary": self.gap_summary,
            "disagreement_summary": self.disagreement_summary,
            "perspective_count": self.perspective_count,
            "overall_confidence": self.overall_confidence.value,
            "is_actionable": self.is_actionable,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CouncilAdvisory:
        rec_data = data.get("recommendation")
        rec = AggregatedRecommendation.from_dict(rec_data) if rec_data else None
        return cls(
            advisory_id=data.get("advisory_id", _council_id("adv")),
            request_id=data.get("request_id", ""),
            status=normalize_council_status(data.get("status", "unknown")),
            recommendation=rec,
            scoring_summary=data.get("scoring_summary", {}),
            evidence_summary=data.get("evidence_summary", {}),
            gap_summary=data.get("gap_summary", {}),
            disagreement_summary=data.get("disagreement_summary", {}),
            perspective_count=data.get("perspective_count", 0),
            overall_confidence=normalize_confidence_level(
                data.get("overall_confidence", "unknown")
            ),
            is_actionable=data.get("is_actionable", False),
            warnings=data.get("warnings", []),
            metadata=data.get("metadata", {}),
        )


def build_council_advisory(
    request_id: str,
    recommendation: AggregatedRecommendation,
    scoring: ScoringResult,
    evidence: EvidenceAssessment,
    gaps: GapAnalysis,
    disagreements: DisagreementMap,
    perspective_count: int = 0,
) -> CouncilAdvisory:
    warnings: list[str] = list(recommendation.warnings)

    is_actionable = (
        recommendation.confidence in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM)
        and disagreements.consensus_possible
        and bool(recommendation.primary_recommendation)
    )

    status = CouncilStatus.ADVISORY_ISSUED if is_actionable else CouncilStatus.SYNTHESIZED

    return CouncilAdvisory(
        advisory_id=_council_id("adv"),
        request_id=request_id,
        status=status,
        recommendation=recommendation,
        scoring_summary={
            "top_role": scoring.top_role_id,
            "score_spread": round(scoring.score_spread, 3),
            "perspective_count": len(scoring.scored_perspectives),
        },
        evidence_summary={
            "total_evidence": evidence.total_evidence_count,
            "strong": evidence.strong_count,
            "average_strength": round(evidence.average_strength_score, 3),
            "confidence": evidence.overall_confidence.value,
        },
        gap_summary={
            "coverage_score": round(gaps.coverage_score, 3),
            "gap_count": len(gaps.gaps),
            "missing_roles": gaps.missing_roles,
        },
        disagreement_summary={
            "total": disagreements.total_count,
            "blocking": disagreements.blocking_count,
            "consensus_possible": disagreements.consensus_possible,
        },
        perspective_count=perspective_count,
        overall_confidence=recommendation.confidence,
        is_actionable=is_actionable,
        warnings=warnings,
    )
