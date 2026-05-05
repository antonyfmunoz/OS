"""Phase 85 aggregation — combine scored perspectives into a coherent advisory.

Takes scoring results, evidence assessment, gap analysis, and
disagreement map to produce a single aggregated recommendation.
Deterministic v1.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.council.contracts import ConfidenceLevel, _council_id, normalize_confidence_level
from umh.council.disagreement import DisagreementMap
from umh.council.evidence import EvidenceAssessment
from umh.council.gaps import GapAnalysis
from umh.council.perspective import PerspectiveReport
from umh.council.scoring import ScoringResult


@dataclass
class AggregatedRecommendation:
    recommendation_id: str = ""
    request_id: str = ""
    primary_recommendation: str = ""
    supporting_rationale: str = ""
    dissenting_views: list[str] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    consensus_strength: float = 0.0
    coverage_score: float = 0.0
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "request_id": self.request_id,
            "primary_recommendation": self.primary_recommendation,
            "supporting_rationale": self.supporting_rationale,
            "dissenting_views": self.dissenting_views,
            "conditions": self.conditions,
            "risks": self.risks,
            "next_actions": self.next_actions,
            "confidence": self.confidence.value,
            "consensus_strength": round(self.consensus_strength, 3),
            "coverage_score": round(self.coverage_score, 3),
            "warnings": self.warnings,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AggregatedRecommendation:
        return cls(
            recommendation_id=data.get("recommendation_id", _council_id("arec")),
            request_id=data.get("request_id", ""),
            primary_recommendation=data.get("primary_recommendation", ""),
            supporting_rationale=data.get("supporting_rationale", ""),
            dissenting_views=data.get("dissenting_views", []),
            conditions=data.get("conditions", []),
            risks=data.get("risks", []),
            next_actions=data.get("next_actions", []),
            confidence=normalize_confidence_level(data.get("confidence", "unknown")),
            consensus_strength=float(data.get("consensus_strength", 0.0)),
            coverage_score=float(data.get("coverage_score", 0.0)),
            warnings=data.get("warnings", []),
            metadata=data.get("metadata", {}),
        )


def aggregate_perspectives(
    request_id: str,
    perspectives: list[PerspectiveReport],
    scoring: ScoringResult,
    evidence_assessment: EvidenceAssessment,
    gap_analysis: GapAnalysis,
    disagreement_map: DisagreementMap,
) -> AggregatedRecommendation:
    warnings: list[str] = []

    if not perspectives:
        return AggregatedRecommendation(
            recommendation_id=_council_id("arec"),
            request_id=request_id,
            primary_recommendation="Insufficient perspectives for recommendation",
            confidence=ConfidenceLevel.LOW,
            warnings=["No perspectives provided"],
        )

    top_role_id = scoring.top_role_id
    top_perspective = next((p for p in perspectives if p.role_id == top_role_id), perspectives[0])

    primary_rec = top_perspective.recommendation or top_perspective.position
    rationale = top_perspective.reasoning

    all_risks: list[str] = []
    all_dissents: list[str] = []
    conditions: list[str] = []
    next_actions: list[str] = []

    for p in perspectives:
        all_risks.extend(p.risks_identified)
        all_dissents.extend(p.dissents)

    for d in disagreement_map.disagreements:
        if d.severity.value in ("blocking", "significant"):
            all_dissents.append(f"{d.role_a} vs {d.role_b}: {d.synthesis_hint or 'unresolved'}")

    for gap in gap_analysis.gaps:
        if gap.severity.value in ("critical", "high"):
            conditions.append(f"Gap: {gap.description}")

    if gap_analysis.coverage_score < 1.0:
        conditions.append(
            f"Coverage is {gap_analysis.coverage_score:.0%} — not all roles represented"
        )

    if evidence_assessment.strong_count == 0:
        conditions.append("No strong evidence — recommendation is weakly supported")

    if not disagreement_map.consensus_possible:
        conditions.append("Blocking disagreements exist — consensus not reached")

    next_actions.append("Review recommendation in context of current constraints")
    if gap_analysis.missing_roles:
        next_actions.append(
            f"Consider soliciting perspectives from: {', '.join(gap_analysis.missing_roles)}"
        )

    consensus_strength = _calculate_consensus(scoring, disagreement_map)

    ev_conf = evidence_assessment.overall_confidence
    if ev_conf == ConfidenceLevel.HIGH and consensus_strength > 0.7:
        confidence = ConfidenceLevel.HIGH
    elif ev_conf in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM) and consensus_strength > 0.4:
        confidence = ConfidenceLevel.MEDIUM
    else:
        confidence = ConfidenceLevel.LOW

    warnings.extend(scoring.warnings)
    warnings.extend(gap_analysis.warnings)
    warnings.extend(disagreement_map.warnings)

    return AggregatedRecommendation(
        recommendation_id=_council_id("arec"),
        request_id=request_id,
        primary_recommendation=primary_rec,
        supporting_rationale=rationale,
        dissenting_views=all_dissents[:10],
        conditions=conditions[:10],
        risks=all_risks[:10],
        next_actions=next_actions[:5],
        confidence=confidence,
        consensus_strength=consensus_strength,
        coverage_score=gap_analysis.coverage_score,
        warnings=warnings,
    )


def _calculate_consensus(scoring: ScoringResult, dmap: DisagreementMap) -> float:
    if not scoring.scored_perspectives:
        return 0.0
    if dmap.blocking_count > 0:
        return 0.0
    base = 1.0 - min(1.0, scoring.score_spread * 2)
    penalty = dmap.significant_count * 0.15
    return max(0.0, min(1.0, base - penalty))
