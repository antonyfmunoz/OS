"""Phase 85 gap detection — identify missing perspectives and blind spots.

Compares the deliberation request requirements against the perspectives
actually provided to find coverage gaps. Deterministic v1.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.council.contracts import DeliberationDomain, _council_id
from umh.council.perspective import PerspectiveReport
from umh.council.request import DeliberationRequest
from umh.council.roles import CouncilRole


class GapSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    UNKNOWN = "unknown"


def normalize_gap_severity(value: str) -> GapSeverity:
    v = value.strip().lower()
    for m in GapSeverity:
        if m.value == v:
            return m
    return GapSeverity.UNKNOWN


@dataclass
class CoverageGap:
    gap_id: str = ""
    description: str = ""
    severity: GapSeverity = GapSeverity.UNKNOWN
    missing_role_id: str = ""
    missing_domain: str = ""
    recommendation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "gap_id": self.gap_id,
            "description": self.description,
            "severity": self.severity.value,
            "missing_role_id": self.missing_role_id,
            "missing_domain": self.missing_domain,
            "recommendation": self.recommendation,
            "metadata": self.metadata,
        }


@dataclass
class GapAnalysis:
    analysis_id: str = ""
    request_id: str = ""
    gaps: list[CoverageGap] = field(default_factory=list)
    covered_roles: list[str] = field(default_factory=list)
    missing_roles: list[str] = field(default_factory=list)
    coverage_score: float = 0.0
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "request_id": self.request_id,
            "gaps": [g.to_dict() for g in self.gaps],
            "covered_roles": self.covered_roles,
            "missing_roles": self.missing_roles,
            "coverage_score": round(self.coverage_score, 3),
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def detect_gaps(
    request: DeliberationRequest,
    roles: list[CouncilRole],
    perspectives: list[PerspectiveReport],
) -> GapAnalysis:
    covered_role_ids = {p.role_id for p in perspectives}
    all_role_ids = {r.role_id for r in roles}
    missing_role_ids = all_role_ids - covered_role_ids

    gaps: list[CoverageGap] = []
    warnings: list[str] = []

    for role in roles:
        if role.role_id in missing_role_ids:
            gaps.append(
                CoverageGap(
                    gap_id=_council_id("gap"),
                    description=f"No perspective from {role.name} ({role.role_type.value})",
                    severity=GapSeverity.HIGH if role.weight >= 1.0 else GapSeverity.MEDIUM,
                    missing_role_id=role.role_id,
                    missing_domain=role.domain.value,
                    recommendation=f"Solicit perspective from {role.role_type.value}",
                )
            )

    for p in perspectives:
        if not p.evidence:
            gaps.append(
                CoverageGap(
                    gap_id=_council_id("gap"),
                    description=f"Perspective from {p.role_id} has no evidence",
                    severity=GapSeverity.MEDIUM,
                    missing_role_id="",
                    recommendation="Add evidence to support the position",
                )
            )

    if not perspectives:
        warnings.append("No perspectives provided — deliberation cannot proceed")
        gaps.append(
            CoverageGap(
                gap_id=_council_id("gap"),
                description="No perspectives at all",
                severity=GapSeverity.CRITICAL,
                recommendation="Convene council roles before deliberation",
            )
        )

    coverage = len(covered_role_ids) / len(all_role_ids) if all_role_ids else 0.0

    return GapAnalysis(
        analysis_id=_council_id("gapan"),
        request_id=request.request_id,
        gaps=gaps,
        covered_roles=sorted(covered_role_ids),
        missing_roles=sorted(missing_role_ids),
        coverage_score=coverage,
        warnings=warnings,
    )
