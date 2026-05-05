"""Phase 85B red team — structured attack analysis of deliberation positions.

The red team assumes the role of adversary and attempts to find weaknesses,
failure modes, and exploitation paths in the council's recommended position.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.council.contracts import _council_id
from umh.council.perspective import PerspectiveReport


class AttackVector(str, Enum):
    ASSUMPTION_FAILURE = "assumption_failure"
    EVIDENCE_GAP = "evidence_gap"
    DEPENDENCY_FAILURE = "dependency_failure"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    TIMING_RISK = "timing_risk"
    SCOPE_CREEP = "scope_creep"
    ADVERSARY_ACTION = "adversary_action"
    UNKNOWN = "unknown"


def normalize_attack_vector(value: str) -> AttackVector:
    v = value.strip().lower().replace(" ", "_").replace("-", "_")
    for m in AttackVector:
        if m.value == v:
            return m
    return AttackVector.UNKNOWN


@dataclass
class RedTeamFinding:
    """A single vulnerability found by the red team."""

    finding_id: str = ""
    vector: AttackVector = AttackVector.UNKNOWN
    description: str = ""
    target_role_id: str = ""
    exploitability: str = "medium"
    impact: str = "medium"
    mitigation_hint: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "vector": self.vector.value,
            "description": self.description,
            "target_role_id": self.target_role_id,
            "exploitability": self.exploitability,
            "impact": self.impact,
            "mitigation_hint": self.mitigation_hint,
            "metadata": self.metadata,
        }


@dataclass
class RedTeamReport:
    """Aggregated red team analysis of all perspectives."""

    report_id: str = ""
    request_id: str = ""
    findings: list[RedTeamFinding] = field(default_factory=list)
    critical_findings: int = 0
    high_findings: int = 0
    overall_risk_level: str = "low"
    recommendation_safe: bool = True
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "request_id": self.request_id,
            "findings": [f.to_dict() for f in self.findings],
            "critical_findings": self.critical_findings,
            "high_findings": self.high_findings,
            "overall_risk_level": self.overall_risk_level,
            "recommendation_safe": self.recommendation_safe,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def run_red_team_analysis(
    request_id: str,
    perspectives: list[PerspectiveReport],
) -> RedTeamReport:
    """Run deterministic red team analysis on perspectives.

    Checks for untested assumptions, evidence gaps, missing risks,
    and structural vulnerabilities. No LLM calls.
    """
    if not perspectives:
        return RedTeamReport(
            report_id=_council_id("rt_rep"),
            request_id=request_id,
            warnings=["No perspectives to attack"],
        )

    findings: list[RedTeamFinding] = []

    for p in perspectives:
        if not p.evidence:
            findings.append(
                RedTeamFinding(
                    finding_id=_council_id("rt_f"),
                    vector=AttackVector.EVIDENCE_GAP,
                    description=f"{p.role_id} makes claims with no evidence",
                    target_role_id=p.role_id,
                    exploitability="high",
                    impact="high",
                    mitigation_hint="Require evidence before accepting position",
                )
            )

        for asm in p.assumptions:
            if asm.confidence < 0.5:
                findings.append(
                    RedTeamFinding(
                        finding_id=_council_id("rt_f"),
                        vector=AttackVector.ASSUMPTION_FAILURE,
                        description=f"{p.role_id} assumes '{asm.statement[:80]}' with low confidence ({asm.confidence:.2f})",
                        target_role_id=p.role_id,
                        exploitability="medium",
                        impact="high" if asm.risk_if_wrong else "medium",
                        mitigation_hint=asm.risk_if_wrong
                        or "Validate assumption before proceeding",
                    )
                )

        if not p.risks_identified and p.score > 0.5:
            findings.append(
                RedTeamFinding(
                    finding_id=_council_id("rt_f"),
                    vector=AttackVector.SCOPE_CREEP,
                    description=f"{p.role_id} recommends action (score {p.score:.2f}) without identifying any risks",
                    target_role_id=p.role_id,
                    exploitability="medium",
                    impact="medium",
                    mitigation_hint="Require risk identification for high-score recommendations",
                )
            )

    all_risks = []
    for p in perspectives:
        all_risks.extend(p.risks_identified)
    if not all_risks and len(perspectives) >= 3:
        findings.append(
            RedTeamFinding(
                finding_id=_council_id("rt_f"),
                vector=AttackVector.ADVERSARY_ACTION,
                description="No perspective identified any risk — blind optimism detected",
                target_role_id="all",
                exploitability="high",
                impact="high",
                mitigation_hint="Require at least one risk per deliberation",
            )
        )

    critical = sum(1 for f in findings if f.impact == "critical")
    high = sum(1 for f in findings if f.impact == "high")

    if critical > 0:
        risk_level = "critical"
    elif high >= 3:
        risk_level = "high"
    elif high >= 1:
        risk_level = "medium"
    else:
        risk_level = "low"

    safe = critical == 0 and high < 3

    return RedTeamReport(
        report_id=_council_id("rt_rep"),
        request_id=request_id,
        findings=findings,
        critical_findings=critical,
        high_findings=high,
        overall_risk_level=risk_level,
        recommendation_safe=safe,
    )
