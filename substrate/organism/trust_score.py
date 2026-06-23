"""Trust Score Engine — composite trust scoring via weakest-link gate.

Composite trust = min(claim_confidence, verification_confidence, reality_confidence).
100% claim + 0% verification = 0% trust. The system cannot believe its own paperwork.

C26E: Reality Correspondence Certification — Phase 2.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────


class TrustDimension(str, Enum):
    CLAIM = "claim"
    VERIFICATION = "verification"
    REALITY = "reality"


class TrustLevel(str, Enum):
    UNTRUSTED = "untrusted"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    FULL = "full"


_TRUST_LEVEL_THRESHOLDS: list[tuple[float, TrustLevel]] = [
    (0.75, TrustLevel.FULL),
    (0.5, TrustLevel.HIGH),
    (0.25, TrustLevel.MEDIUM),
    (0.01, TrustLevel.LOW),
    (0.0, TrustLevel.UNTRUSTED),
]

_PROMOTION_ELIGIBLE = frozenset({TrustLevel.HIGH, TrustLevel.FULL})


# ── Data types ───────────────────────────────────────────────────────────


@dataclass
class DimensionScore:
    """Score for a single trust dimension with evidence."""

    dimension: TrustDimension
    score: float
    evidence: list[str] = field(default_factory=list)
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "score": round(self.score, 4),
            "evidence": self.evidence,
            "source": self.source,
        }


@dataclass
class TrustScore:
    """Composite trust score for a work item."""

    trust_id: str = field(
        default_factory=lambda: f"ts-{uuid4().hex[:12]}"
    )
    work_id: str = ""
    dimensions: list[DimensionScore] = field(default_factory=list)
    composite_trust: float = 0.0
    trust_level: TrustLevel = TrustLevel.UNTRUSTED
    computed_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def can_promote(self) -> bool:
        return self.trust_level in _PROMOTION_ELIGIBLE

    def to_dict(self) -> dict[str, Any]:
        return {
            "trust_id": self.trust_id,
            "work_id": self.work_id,
            "dimensions": [d.to_dict() for d in self.dimensions],
            "composite_trust": round(self.composite_trust, 4),
            "trust_level": self.trust_level.value,
            "can_promote": self.can_promote,
            "computed_at": self.computed_at.isoformat(),
        }


# ── Engine ───────────────────────────────────────────────────────────────


class TrustScoreEngine:
    """Computes composite trust scores. Weakest link determines confidence."""

    def __init__(self) -> None:
        self._scores: dict[str, TrustScore] = {}

    @staticmethod
    def classify(score: float) -> TrustLevel:
        """Classify a numeric score into a TrustLevel."""
        clamped = max(0.0, min(1.0, score))
        for threshold, level in _TRUST_LEVEL_THRESHOLDS:
            if clamped >= threshold:
                return level
        return TrustLevel.UNTRUSTED

    def compute(
        self,
        work_id: str,
        claim_confidence: float,
        verification_confidence: float,
        reality_confidence: float,
        claim_evidence: list[str] | None = None,
        verification_evidence: list[str] | None = None,
        reality_evidence: list[str] | None = None,
        claim_source: str = "",
        verification_source: str = "",
        reality_source: str = "",
    ) -> TrustScore:
        """Compute composite trust for a work item.

        Composite = min(claim, verification, reality). This is the
        mechanical gate — no dimension can compensate for another.
        """
        dimensions = [
            DimensionScore(
                dimension=TrustDimension.CLAIM,
                score=max(0.0, min(1.0, claim_confidence)),
                evidence=claim_evidence or [],
                source=claim_source,
            ),
            DimensionScore(
                dimension=TrustDimension.VERIFICATION,
                score=max(0.0, min(1.0, verification_confidence)),
                evidence=verification_evidence or [],
                source=verification_source,
            ),
            DimensionScore(
                dimension=TrustDimension.REALITY,
                score=max(0.0, min(1.0, reality_confidence)),
                evidence=reality_evidence or [],
                source=reality_source,
            ),
        ]

        composite = min(d.score for d in dimensions)
        trust_level = self.classify(composite)

        trust_score = TrustScore(
            work_id=work_id,
            dimensions=dimensions,
            composite_trust=composite,
            trust_level=trust_level,
        )

        self._scores[work_id] = trust_score

        logger.info(
            "Trust score for %s: composite=%.2f level=%s (claim=%.2f verify=%.2f reality=%.2f)",
            work_id,
            composite,
            trust_level.value,
            claim_confidence,
            verification_confidence,
            reality_confidence,
        )

        return trust_score

    @staticmethod
    def can_promote(trust_score: TrustScore) -> bool:
        """Check if a trust score permits promotion to canonical."""
        return trust_score.can_promote

    def get_score(self, work_id: str) -> TrustScore | None:
        """Retrieve a cached trust score by work ID."""
        return self._scores.get(work_id)

    def summary(self) -> dict[str, Any]:
        """Summary of all cached trust scores, grouped by level."""
        by_level: dict[str, int] = {level.value: 0 for level in TrustLevel}
        for score in self._scores.values():
            by_level[score.trust_level.value] += 1

        return {
            "total": len(self._scores),
            "by_level": by_level,
            "promotion_eligible": sum(
                1 for s in self._scores.values() if s.can_promote
            ),
            "promotion_blocked": sum(
                1 for s in self._scores.values() if not s.can_promote
            ),
        }
