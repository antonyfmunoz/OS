"""Phase 85B minority report — preserve dissenting perspectives that the majority overrules.

Ensures that contrarian positions, low-score-but-high-evidence perspectives,
and adversarial challenges are recorded and not erased by aggregation.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.council.contracts import ConfidenceLevel, _council_id
from umh.council.perspective import PerspectiveReport
from umh.council.scoring import ScoringResult


class MinorityReasonType(str, Enum):
    LOW_SCORE_HIGH_EVIDENCE = "low_score_high_evidence"
    ADVERSARIAL_PERSPECTIVE = "adversarial_perspective"
    EXPLICIT_DISSENT = "explicit_dissent"
    CONTRARIAN_POSITION = "contrarian_position"
    OUTLIER_SCORE = "outlier_score"
    UNKNOWN = "unknown"


def normalize_minority_reason(value: str) -> MinorityReasonType:
    v = value.strip().lower().replace(" ", "_").replace("-", "_")
    for m in MinorityReasonType:
        if m.value == v:
            return m
    return MinorityReasonType.UNKNOWN


@dataclass
class MinorityEntry:
    """A single preserved minority position."""

    entry_id: str = ""
    role_id: str = ""
    position: str = ""
    reasoning: str = ""
    evidence_count: int = 0
    score: float = 0.0
    confidence: str = ""
    reason_type: MinorityReasonType = MinorityReasonType.UNKNOWN
    why_preserved: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "role_id": self.role_id,
            "position": self.position,
            "reasoning": self.reasoning,
            "evidence_count": self.evidence_count,
            "score": round(self.score, 3),
            "confidence": self.confidence,
            "reason_type": self.reason_type.value,
            "why_preserved": self.why_preserved,
            "metadata": self.metadata,
        }


@dataclass
class MinorityReport:
    """Collection of preserved minority positions from a deliberation."""

    report_id: str = ""
    request_id: str = ""
    entries: list[MinorityEntry] = field(default_factory=list)
    total_perspectives: int = 0
    minority_count: int = 0
    dissent_preserved: bool = False
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "request_id": self.request_id,
            "entries": [e.to_dict() for e in self.entries],
            "total_perspectives": self.total_perspectives,
            "minority_count": self.minority_count,
            "dissent_preserved": self.dissent_preserved,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def build_minority_report(
    request_id: str,
    perspectives: list[PerspectiveReport],
    scoring: ScoringResult,
) -> MinorityReport:
    """Identify and preserve minority positions that aggregation would suppress."""
    if not perspectives:
        return MinorityReport(
            report_id=_council_id("minrep"),
            request_id=request_id,
            warnings=["No perspectives to analyze"],
        )

    score_map = {sp.role_id: sp.weighted_score for sp in scoring.scored_perspectives}

    scores = list(score_map.values())
    if len(scores) >= 2:
        mean_score = sum(scores) / len(scores)
    else:
        mean_score = scores[0] if scores else 0.0

    entries: list[MinorityEntry] = []

    for p in perspectives:
        weighted = score_map.get(p.role_id, p.score)
        reasons: list[tuple[MinorityReasonType, str]] = []

        if weighted < mean_score * 0.7 and len(p.evidence) >= 2:
            reasons.append(
                (
                    MinorityReasonType.LOW_SCORE_HIGH_EVIDENCE,
                    f"Scored {weighted:.3f} (below mean {mean_score:.3f}) but provided {len(p.evidence)} evidence items",
                )
            )

        if p.metadata.get("adversarial", False):
            reasons.append(
                (
                    MinorityReasonType.ADVERSARIAL_PERSPECTIVE,
                    "Adversarial thinker — contrarian view must be preserved",
                )
            )

        if p.dissents:
            reasons.append(
                (
                    MinorityReasonType.EXPLICIT_DISSENT,
                    f"Explicitly dissented: {p.dissents[0][:100]}",
                )
            )

        is_archetype = p.role_id.startswith("archetype:")
        if is_archetype and p.metadata.get("archetype") in ("contrarian", "skeptic"):
            reasons.append(
                (
                    MinorityReasonType.CONTRARIAN_POSITION,
                    f"Contrarian/skeptic archetype: perspective exists to challenge consensus",
                )
            )

        if len(scores) >= 3 and weighted > 0:
            if abs(weighted - mean_score) > mean_score * 0.5:
                reasons.append(
                    (
                        MinorityReasonType.OUTLIER_SCORE,
                        f"Score {weighted:.3f} is an outlier from mean {mean_score:.3f}",
                    )
                )

        for reason_type, why in reasons:
            entries.append(
                MinorityEntry(
                    entry_id=_council_id("mine"),
                    role_id=p.role_id,
                    position=p.position,
                    reasoning=p.reasoning,
                    evidence_count=len(p.evidence),
                    score=weighted,
                    confidence=p.confidence.value
                    if hasattr(p.confidence, "value")
                    else str(p.confidence),
                    reason_type=reason_type,
                    why_preserved=why,
                    metadata=p.metadata,
                )
            )

    unique_roles = {e.role_id for e in entries}

    return MinorityReport(
        report_id=_council_id("minrep"),
        request_id=request_id,
        entries=entries,
        total_perspectives=len(perspectives),
        minority_count=len(unique_roles),
        dissent_preserved=len(entries) > 0,
    )
