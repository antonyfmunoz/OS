"""Phase 85 scoring — weighted perspective scoring and ranking.

Combines role weight, evidence strength, confidence, and score
into a normalized ranking of perspectives. Deterministic v1.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.council.contracts import ConfidenceLevel, EvidenceStrength, _council_id, clamp_score
from umh.council.perspective import PerspectiveReport
from umh.council.roles import CouncilRole


_CONFIDENCE_WEIGHTS: dict[ConfidenceLevel, float] = {
    ConfidenceLevel.VERY_HIGH: 1.0,
    ConfidenceLevel.HIGH: 0.85,
    ConfidenceLevel.MEDIUM: 0.6,
    ConfidenceLevel.LOW: 0.35,
    ConfidenceLevel.UNKNOWN: 0.2,
}

_EVIDENCE_WEIGHTS: dict[EvidenceStrength, float] = {
    EvidenceStrength.STRONG: 1.0,
    EvidenceStrength.MODERATE: 0.7,
    EvidenceStrength.WEAK: 0.4,
    EvidenceStrength.ANECDOTAL: 0.2,
    EvidenceStrength.NONE: 0.0,
    EvidenceStrength.UNKNOWN: 0.1,
}


@dataclass
class ScoredPerspective:
    role_id: str = ""
    raw_score: float = 0.0
    role_weight: float = 1.0
    confidence_factor: float = 0.5
    evidence_factor: float = 0.0
    weighted_score: float = 0.0
    rank: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "role_id": self.role_id,
            "raw_score": round(self.raw_score, 3),
            "role_weight": round(self.role_weight, 3),
            "confidence_factor": round(self.confidence_factor, 3),
            "evidence_factor": round(self.evidence_factor, 3),
            "weighted_score": round(self.weighted_score, 3),
            "rank": self.rank,
            "metadata": self.metadata,
        }


@dataclass
class ScoringResult:
    scoring_id: str = ""
    request_id: str = ""
    scored_perspectives: list[ScoredPerspective] = field(default_factory=list)
    top_role_id: str = ""
    score_spread: float = 0.0
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scoring_id": self.scoring_id,
            "request_id": self.request_id,
            "scored_perspectives": [sp.to_dict() for sp in self.scored_perspectives],
            "top_role_id": self.top_role_id,
            "score_spread": round(self.score_spread, 3),
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def score_perspectives(
    request_id: str,
    perspectives: list[PerspectiveReport],
    roles: list[CouncilRole],
) -> ScoringResult:
    if not perspectives:
        return ScoringResult(
            scoring_id=_council_id("score"),
            request_id=request_id,
            warnings=["No perspectives to score"],
        )

    role_map = {r.role_id: r for r in roles}
    scored: list[ScoredPerspective] = []

    for p in perspectives:
        role = role_map.get(p.role_id)
        role_weight = role.weight if role else 1.0

        conf_factor = _CONFIDENCE_WEIGHTS.get(p.confidence, 0.2)

        ev_scores = [_EVIDENCE_WEIGHTS.get(e.strength, 0.1) for e in p.evidence]
        ev_factor = sum(ev_scores) / len(ev_scores) if ev_scores else 0.0

        weighted = p.score * role_weight * conf_factor * (0.5 + 0.5 * ev_factor)

        scored.append(
            ScoredPerspective(
                role_id=p.role_id,
                raw_score=p.score,
                role_weight=role_weight,
                confidence_factor=conf_factor,
                evidence_factor=ev_factor,
                weighted_score=weighted,
            )
        )

    scored.sort(key=lambda s: s.weighted_score, reverse=True)
    for i, sp in enumerate(scored):
        sp.rank = i + 1

    top_id = scored[0].role_id if scored else ""
    ws = [s.weighted_score for s in scored]
    spread = max(ws) - min(ws) if len(ws) >= 2 else 0.0

    warnings: list[str] = []
    if spread < 0.05 and len(scored) >= 2:
        warnings.append("Very narrow score spread — perspectives are nearly equivalent")

    return ScoringResult(
        scoring_id=_council_id("score"),
        request_id=request_id,
        scored_perspectives=scored,
        top_role_id=top_id,
        score_spread=spread,
        warnings=warnings,
    )
