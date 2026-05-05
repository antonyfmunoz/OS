"""Phase 85B consensus analysis — distinguish real consensus from false agreement.

Detects false consensus risk, unanimity bias, and confidence without evidence.
Supplements Phase 85 aggregation with explicit consensus quality checks.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.council.contracts import ConfidenceLevel, _council_id
from umh.council.perspective import PerspectiveReport
from umh.council.scoring import ScoringResult


class ConsensusQuality(str, Enum):
    GENUINE = "genuine"
    WEAK = "weak"
    FALSE = "false"
    UNTESTED = "untested"
    UNKNOWN = "unknown"


def normalize_consensus_quality(value: str) -> ConsensusQuality:
    v = value.strip().lower()
    for m in ConsensusQuality:
        if m.value == v:
            return m
    return ConsensusQuality.UNKNOWN


@dataclass
class ConsensusAnalysis:
    """Structured assessment of whether consensus is genuine or false."""

    analysis_id: str = ""
    request_id: str = ""
    quality: ConsensusQuality = ConsensusQuality.UNKNOWN
    consensus_score: float = 0.0
    evidence_backed_agreement: int = 0
    opinion_only_agreement: int = 0
    adversarial_challenges_present: bool = False
    false_consensus_indicators: list[str] = field(default_factory=list)
    genuine_consensus_indicators: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "request_id": self.request_id,
            "quality": self.quality.value,
            "consensus_score": round(self.consensus_score, 3),
            "evidence_backed_agreement": self.evidence_backed_agreement,
            "opinion_only_agreement": self.opinion_only_agreement,
            "adversarial_challenges_present": self.adversarial_challenges_present,
            "false_consensus_indicators": self.false_consensus_indicators,
            "genuine_consensus_indicators": self.genuine_consensus_indicators,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def analyze_consensus(
    request_id: str,
    perspectives: list[PerspectiveReport],
    scoring: ScoringResult,
) -> ConsensusAnalysis:
    """Determine whether apparent consensus is genuine, false, or untested."""
    if len(perspectives) < 2:
        return ConsensusAnalysis(
            analysis_id=_council_id("cons"),
            request_id=request_id,
            quality=ConsensusQuality.UNTESTED,
            warnings=["Fewer than 2 perspectives — consensus cannot be assessed"],
        )

    false_indicators: list[str] = []
    genuine_indicators: list[str] = []

    scores = [sp.weighted_score for sp in scoring.scored_perspectives]
    spread = max(scores) - min(scores) if scores else 0.0

    evidence_backed = sum(1 for p in perspectives if p.evidence)
    opinion_only = len(perspectives) - evidence_backed
    adversarial_present = any(p.metadata.get("adversarial", False) for p in perspectives)
    has_dissents = any(p.dissents for p in perspectives)
    has_varied_confidence = len({p.confidence for p in perspectives}) > 1

    if spread < 0.1 and len(perspectives) >= 3:
        false_indicators.append("Score spread < 0.1 across 3+ perspectives")
    if not adversarial_present and len(perspectives) >= 3:
        false_indicators.append("No adversarial thinker challenged the consensus")
    if opinion_only > evidence_backed:
        false_indicators.append("More opinion-only perspectives than evidence-backed")
    if not has_dissents and len(perspectives) >= 3:
        false_indicators.append("No dissents recorded by any perspective")
    if not has_varied_confidence and len(perspectives) >= 3:
        false_indicators.append(
            "All perspectives have identical confidence — suspicious uniformity"
        )

    if evidence_backed >= len(perspectives) * 0.7:
        genuine_indicators.append("70%+ perspectives backed by evidence")
    if adversarial_present:
        genuine_indicators.append("Adversarial thinker present and did not block")
    if has_dissents:
        genuine_indicators.append("Dissents were recorded — consensus is not silent")
    if has_varied_confidence:
        genuine_indicators.append("Varied confidence levels — independent assessment")
    if spread > 0.2 and spread < 0.5:
        genuine_indicators.append("Moderate score spread — disagreement exists but not blocking")

    false_count = len(false_indicators)
    genuine_count = len(genuine_indicators)

    if false_count >= 3:
        quality = ConsensusQuality.FALSE
    elif false_count == 0 and genuine_count >= 3:
        quality = ConsensusQuality.GENUINE
    elif not adversarial_present:
        quality = ConsensusQuality.UNTESTED
    else:
        quality = ConsensusQuality.WEAK

    consensus_score = 0.5
    if quality == ConsensusQuality.GENUINE:
        consensus_score = min(1.0, 0.7 + genuine_count * 0.06)
    elif quality == ConsensusQuality.FALSE:
        consensus_score = max(0.0, 0.3 - false_count * 0.05)
    elif quality == ConsensusQuality.UNTESTED:
        consensus_score = 0.3

    return ConsensusAnalysis(
        analysis_id=_council_id("cons"),
        request_id=request_id,
        quality=quality,
        consensus_score=consensus_score,
        evidence_backed_agreement=evidence_backed,
        opinion_only_agreement=opinion_only,
        adversarial_challenges_present=adversarial_present,
        false_consensus_indicators=false_indicators,
        genuine_consensus_indicators=genuine_indicators,
    )
