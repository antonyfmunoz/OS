"""Phase 85B blue team — defensive analysis and resilience assessment.

The blue team ensures the recommended position has recovery paths,
guardrails, fallback plans, and monitoring hooks.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.council.contracts import _council_id
from umh.council.perspective import PerspectiveReport
from umh.council.red_team import RedTeamReport


class DefenseType(str, Enum):
    GUARDRAIL = "guardrail"
    FALLBACK = "fallback"
    MONITORING = "monitoring"
    ROLLBACK = "rollback"
    CIRCUIT_BREAKER = "circuit_breaker"
    UNKNOWN = "unknown"


def normalize_defense_type(value: str) -> DefenseType:
    v = value.strip().lower().replace(" ", "_").replace("-", "_")
    for m in DefenseType:
        if m.value == v:
            return m
    return DefenseType.UNKNOWN


@dataclass
class DefenseRecommendation:
    """A single defensive measure to protect the recommendation."""

    defense_id: str = ""
    defense_type: DefenseType = DefenseType.UNKNOWN
    description: str = ""
    addresses_finding: str = ""
    priority: str = "medium"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "defense_id": self.defense_id,
            "defense_type": self.defense_type.value,
            "description": self.description,
            "addresses_finding": self.addresses_finding,
            "priority": self.priority,
            "metadata": self.metadata,
        }


@dataclass
class BlueTeamReport:
    """Defensive analysis and resilience recommendations."""

    report_id: str = ""
    request_id: str = ""
    defenses: list[DefenseRecommendation] = field(default_factory=list)
    reversibility_score: float = 0.5
    recovery_plan_exists: bool = False
    guardrail_count: int = 0
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "request_id": self.request_id,
            "defenses": [d.to_dict() for d in self.defenses],
            "reversibility_score": round(self.reversibility_score, 3),
            "recovery_plan_exists": self.recovery_plan_exists,
            "guardrail_count": self.guardrail_count,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def run_blue_team_analysis(
    request_id: str,
    perspectives: list[PerspectiveReport],
    red_team: RedTeamReport | None = None,
) -> BlueTeamReport:
    """Run deterministic blue team analysis — defensive resilience assessment.

    For each red team finding, proposes a defense. Also checks that
    perspectives include recovery/monitoring considerations. No LLM calls.
    """
    if not perspectives:
        return BlueTeamReport(
            report_id=_council_id("bt_rep"),
            request_id=request_id,
            warnings=["No perspectives to defend"],
        )

    defenses: list[DefenseRecommendation] = []

    if red_team:
        for finding in red_team.findings:
            if finding.vector.value == "evidence_gap":
                defenses.append(
                    DefenseRecommendation(
                        defense_id=_council_id("bt_d"),
                        defense_type=DefenseType.GUARDRAIL,
                        description=f"Require evidence before acting on {finding.target_role_id} position",
                        addresses_finding=finding.finding_id,
                        priority="high",
                    )
                )
            elif finding.vector.value == "assumption_failure":
                defenses.append(
                    DefenseRecommendation(
                        defense_id=_council_id("bt_d"),
                        defense_type=DefenseType.MONITORING,
                        description=f"Monitor assumption validity: {finding.description[:100]}",
                        addresses_finding=finding.finding_id,
                        priority="high",
                    )
                )
            else:
                defenses.append(
                    DefenseRecommendation(
                        defense_id=_council_id("bt_d"),
                        defense_type=DefenseType.FALLBACK,
                        description=finding.mitigation_hint
                        or f"Address: {finding.description[:80]}",
                        addresses_finding=finding.finding_id,
                        priority="medium",
                    )
                )

    all_risks = []
    for p in perspectives:
        all_risks.extend(p.risks_identified)

    for risk in all_risks[:5]:
        defenses.append(
            DefenseRecommendation(
                defense_id=_council_id("bt_d"),
                defense_type=DefenseType.CIRCUIT_BREAKER,
                description=f"Circuit breaker for risk: {risk[:100]}",
                addresses_finding="",
                priority="medium",
            )
        )

    defenses.append(
        DefenseRecommendation(
            defense_id=_council_id("bt_d"),
            defense_type=DefenseType.ROLLBACK,
            description="Ensure recommendation is reversible — define rollback trigger",
            addresses_finding="",
            priority="high",
        )
    )

    guardrail_count = sum(1 for d in defenses if d.defense_type == DefenseType.GUARDRAIL)

    has_risk_awareness = any(p.risks_identified for p in perspectives)
    reversibility = 0.7 if has_risk_awareness else 0.3
    if red_team and red_team.critical_findings > 0:
        reversibility = max(0.1, reversibility - 0.3)

    return BlueTeamReport(
        report_id=_council_id("bt_rep"),
        request_id=request_id,
        defenses=defenses,
        reversibility_score=reversibility,
        recovery_plan_exists=len(defenses) >= 3,
        guardrail_count=guardrail_count,
    )
