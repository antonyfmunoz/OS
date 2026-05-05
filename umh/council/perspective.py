"""Phase 85 perspective reports — typed output from each council role.

Each specialist produces a PerspectiveReport with evidence,
assumptions, recommendations, and dissents. Advisory only.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.council.contracts import (
    Assumption,
    ConfidenceLevel,
    EvidenceItem,
    _council_id,
    clamp_score,
    normalize_confidence_level,
)


@dataclass
class PerspectiveReport:
    report_id: str = ""
    request_id: str = ""
    role_id: str = ""
    position: str = ""
    reasoning: str = ""
    recommendation: str = ""
    evidence: list[EvidenceItem] = field(default_factory=list)
    assumptions: list[Assumption] = field(default_factory=list)
    risks_identified: list[str] = field(default_factory=list)
    opportunities_identified: list[str] = field(default_factory=list)
    dissents: list[str] = field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    score: float = 0.5
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "request_id": self.request_id,
            "role_id": self.role_id,
            "position": self.position,
            "reasoning": self.reasoning,
            "recommendation": self.recommendation,
            "evidence": [e.to_dict() for e in self.evidence],
            "assumptions": [a.to_dict() for a in self.assumptions],
            "risks_identified": self.risks_identified,
            "opportunities_identified": self.opportunities_identified,
            "dissents": self.dissents,
            "confidence": self.confidence.value,
            "score": self.score,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PerspectiveReport:
        return cls(
            report_id=data.get("report_id", _council_id("prpt")),
            request_id=data.get("request_id", ""),
            role_id=data.get("role_id", ""),
            position=data.get("position", ""),
            reasoning=data.get("reasoning", ""),
            recommendation=data.get("recommendation", ""),
            evidence=[EvidenceItem.from_dict(e) for e in data.get("evidence", [])],
            assumptions=[Assumption.from_dict(a) for a in data.get("assumptions", [])],
            risks_identified=data.get("risks_identified", []),
            opportunities_identified=data.get("opportunities_identified", []),
            dissents=data.get("dissents", []),
            confidence=normalize_confidence_level(data.get("confidence", "unknown")),
            score=clamp_score(data.get("score", 0.5)),
            warnings=data.get("warnings", []),
            metadata=data.get("metadata", {}),
        )


def create_perspective_report(
    request_id: str,
    role_id: str,
    *,
    position: str = "",
    reasoning: str = "",
    recommendation: str = "",
    evidence: list[EvidenceItem] | None = None,
    assumptions: list[Assumption] | None = None,
    risks_identified: list[str] | None = None,
    opportunities_identified: list[str] | None = None,
    dissents: list[str] | None = None,
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
    score: float = 0.5,
    metadata: dict[str, Any] | None = None,
) -> PerspectiveReport:
    warnings: list[str] = []
    if not position:
        warnings.append("No position stated")
    if not evidence:
        warnings.append("No evidence provided")
    return PerspectiveReport(
        report_id=_council_id("prpt"),
        request_id=request_id,
        role_id=role_id,
        position=position,
        reasoning=reasoning,
        recommendation=recommendation,
        evidence=evidence or [],
        assumptions=assumptions or [],
        risks_identified=risks_identified or [],
        opportunities_identified=opportunities_identified or [],
        dissents=dissents or [],
        confidence=confidence,
        score=clamp_score(score),
        warnings=warnings,
        metadata=metadata or {},
    )


def validate_perspective_report(report: PerspectiveReport) -> list[str]:
    issues: list[str] = []
    if not report.report_id:
        issues.append("Missing report_id")
    if not report.request_id:
        issues.append("Missing request_id")
    if not report.role_id:
        issues.append("Missing role_id")
    if not report.position:
        issues.append("Missing position")
    if not report.evidence:
        issues.append("No evidence — perspective is unsupported")
    if not report.recommendation:
        issues.append("Missing recommendation")
    return issues
