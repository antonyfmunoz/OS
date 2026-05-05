"""Phase 85 disagreement mapping — surface and classify conflicts between perspectives.

Identifies where perspectives disagree, the nature of the disagreement,
and whether synthesis is possible. Deterministic v1.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.council.contracts import _council_id
from umh.council.perspective import PerspectiveReport


class DisagreementType(str, Enum):
    FACTUAL = "factual"
    PRIORITY = "priority"
    VALUES = "values"
    RISK_ASSESSMENT = "risk_assessment"
    TIMING = "timing"
    SCOPE = "scope"
    METHODOLOGY = "methodology"
    UNKNOWN = "unknown"


class DisagreementSeverity(str, Enum):
    BLOCKING = "blocking"
    SIGNIFICANT = "significant"
    MINOR = "minor"
    COSMETIC = "cosmetic"
    UNKNOWN = "unknown"


def normalize_disagreement_type(value: str) -> DisagreementType:
    v = value.strip().lower().replace(" ", "_").replace("-", "_")
    for m in DisagreementType:
        if m.value == v:
            return m
    return DisagreementType.UNKNOWN


def normalize_disagreement_severity(value: str) -> DisagreementSeverity:
    v = value.strip().lower()
    for m in DisagreementSeverity:
        if m.value == v:
            return m
    return DisagreementSeverity.UNKNOWN


@dataclass
class Disagreement:
    disagreement_id: str = ""
    request_id: str = ""
    role_a: str = ""
    role_b: str = ""
    position_a: str = ""
    position_b: str = ""
    disagreement_type: DisagreementType = DisagreementType.UNKNOWN
    severity: DisagreementSeverity = DisagreementSeverity.UNKNOWN
    synthesis_possible: bool = False
    synthesis_hint: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "disagreement_id": self.disagreement_id,
            "request_id": self.request_id,
            "role_a": self.role_a,
            "role_b": self.role_b,
            "position_a": self.position_a,
            "position_b": self.position_b,
            "disagreement_type": self.disagreement_type.value,
            "severity": self.severity.value,
            "synthesis_possible": self.synthesis_possible,
            "synthesis_hint": self.synthesis_hint,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Disagreement:
        return cls(
            disagreement_id=data.get("disagreement_id", _council_id("disagr")),
            request_id=data.get("request_id", ""),
            role_a=data.get("role_a", ""),
            role_b=data.get("role_b", ""),
            position_a=data.get("position_a", ""),
            position_b=data.get("position_b", ""),
            disagreement_type=normalize_disagreement_type(data.get("disagreement_type", "unknown")),
            severity=normalize_disagreement_severity(data.get("severity", "unknown")),
            synthesis_possible=data.get("synthesis_possible", False),
            synthesis_hint=data.get("synthesis_hint", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class DisagreementMap:
    map_id: str = ""
    request_id: str = ""
    disagreements: list[Disagreement] = field(default_factory=list)
    blocking_count: int = 0
    significant_count: int = 0
    total_count: int = 0
    consensus_possible: bool = True
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "map_id": self.map_id,
            "request_id": self.request_id,
            "disagreements": [d.to_dict() for d in self.disagreements],
            "blocking_count": self.blocking_count,
            "significant_count": self.significant_count,
            "total_count": self.total_count,
            "consensus_possible": self.consensus_possible,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def map_disagreements(
    request_id: str,
    perspectives: list[PerspectiveReport],
) -> DisagreementMap:
    disagreements: list[Disagreement] = []
    warnings: list[str] = []

    if len(perspectives) < 2:
        return DisagreementMap(
            map_id=_council_id("dmap"),
            request_id=request_id,
            warnings=["Fewer than 2 perspectives — no disagreements to map"],
        )

    for p in perspectives:
        for dissent in p.dissents:
            disagreements.append(
                Disagreement(
                    disagreement_id=_council_id("disagr"),
                    request_id=request_id,
                    role_a=p.role_id,
                    role_b="",
                    position_a=p.position,
                    position_b=dissent,
                    disagreement_type=DisagreementType.PRIORITY,
                    severity=DisagreementSeverity.MINOR,
                    synthesis_possible=True,
                    synthesis_hint="Role self-identified this dissent",
                )
            )

    scored = [(p.role_id, p.score, p.position) for p in perspectives if p.position]
    for i in range(len(scored)):
        for j in range(i + 1, len(scored)):
            role_a, score_a, pos_a = scored[i]
            role_b, score_b, pos_b = scored[j]
            if abs(score_a - score_b) > 0.4:
                severity = (
                    DisagreementSeverity.SIGNIFICANT
                    if abs(score_a - score_b) > 0.6
                    else DisagreementSeverity.MINOR
                )
                disagreements.append(
                    Disagreement(
                        disagreement_id=_council_id("disagr"),
                        request_id=request_id,
                        role_a=role_a,
                        role_b=role_b,
                        position_a=pos_a,
                        position_b=pos_b,
                        disagreement_type=DisagreementType.PRIORITY,
                        severity=severity,
                        synthesis_possible=True,
                        synthesis_hint="Score divergence detected",
                    )
                )

    blocking = sum(1 for d in disagreements if d.severity == DisagreementSeverity.BLOCKING)
    significant = sum(1 for d in disagreements if d.severity == DisagreementSeverity.SIGNIFICANT)
    consensus = blocking == 0

    if blocking > 0:
        warnings.append(f"{blocking} blocking disagreement(s) prevent consensus")

    return DisagreementMap(
        map_id=_council_id("dmap"),
        request_id=request_id,
        disagreements=disagreements,
        blocking_count=blocking,
        significant_count=significant,
        total_count=len(disagreements),
        consensus_possible=consensus,
        warnings=warnings,
    )
