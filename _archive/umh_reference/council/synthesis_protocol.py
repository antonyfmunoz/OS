"""Phase 85B synthesis protocol — produce a single coherent advisory without erasing dissent.

Combines the Phase 85 aggregation output with Phase 85B adversarial assessment,
minority report, red/blue team reports, and consensus analysis into an
EnhancedCouncilAdvisory that preserves all dissent and uncertainty.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.council.adversarial import AdversarialAssessment
from umh.council.advisory import CouncilAdvisory
from umh.council.blue_team import BlueTeamReport
from umh.council.consensus import ConsensusAnalysis, ConsensusQuality
from umh.council.contracts import ConfidenceLevel, CouncilStatus, _council_id
from umh.council.minority_report import MinorityReport
from umh.council.red_team import RedTeamReport


@dataclass
class EnhancedCouncilAdvisory:
    """Phase 85B enhanced advisory — wraps Phase 85 advisory with adversarial and minority data."""

    enhanced_id: str = ""
    base_advisory: CouncilAdvisory | None = None
    adversarial: AdversarialAssessment | None = None
    minority: MinorityReport | None = None
    red_team: RedTeamReport | None = None
    blue_team: BlueTeamReport | None = None
    consensus: ConsensusAnalysis | None = None
    guardrails: list[str] = field(default_factory=list)
    non_actions: list[str] = field(default_factory=list)
    residual_uncertainty: list[str] = field(default_factory=list)
    what_would_change: list[str] = field(default_factory=list)
    dissent_preserved: bool = False
    false_consensus_risk: float = 0.0
    overall_safe: bool = True
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "enhanced_id": self.enhanced_id,
            "base_advisory": self.base_advisory.to_dict() if self.base_advisory else None,
            "adversarial": self.adversarial.to_dict() if self.adversarial else None,
            "minority": self.minority.to_dict() if self.minority else None,
            "red_team": self.red_team.to_dict() if self.red_team else None,
            "blue_team": self.blue_team.to_dict() if self.blue_team else None,
            "consensus": self.consensus.to_dict() if self.consensus else None,
            "guardrails": self.guardrails,
            "non_actions": self.non_actions,
            "residual_uncertainty": self.residual_uncertainty,
            "what_would_change": self.what_would_change,
            "dissent_preserved": self.dissent_preserved,
            "false_consensus_risk": round(self.false_consensus_risk, 3),
            "overall_safe": self.overall_safe,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def synthesize_enhanced_advisory(
    base_advisory: CouncilAdvisory,
    adversarial: AdversarialAssessment,
    minority: MinorityReport,
    red_team: RedTeamReport,
    blue_team: BlueTeamReport,
    consensus: ConsensusAnalysis,
) -> EnhancedCouncilAdvisory:
    """Combine all analysis layers into a single enhanced advisory.

    Does NOT erase dissent. Preserves minority positions. Reports
    false consensus risk. Lists guardrails, non-actions, residual
    uncertainty, and what would change the recommendation.
    """
    guardrails = list(adversarial.guardrails)
    non_actions = list(adversarial.non_actions)
    residual = list(adversarial.residual_uncertainty)
    what_would_change = list(adversarial.what_would_change_recommendation)

    warnings: list[str] = list(base_advisory.warnings)

    if adversarial.false_consensus_risk > 0.5:
        warnings.append(f"High false consensus risk: {adversarial.false_consensus_risk:.2f}")

    if red_team.critical_findings > 0:
        warnings.append(f"Red team found {red_team.critical_findings} critical vulnerability(ies)")

    if not red_team.recommendation_safe:
        warnings.append("Red team assessment: recommendation is NOT safe to proceed")
        non_actions.append("Do not proceed without addressing red team critical findings")

    if consensus.quality == ConsensusQuality.FALSE:
        warnings.append("Consensus quality is FALSE — agreement is not genuine")
        guardrails.append("Re-deliberate with additional adversarial perspectives")
    elif consensus.quality == ConsensusQuality.UNTESTED:
        warnings.append("Consensus quality is UNTESTED — no adversarial challenge applied")

    if minority.dissent_preserved:
        warnings.append(
            f"Minority report preserves {minority.minority_count} dissenting position(s)"
        )

    overall_safe = (
        red_team.recommendation_safe
        and consensus.quality != ConsensusQuality.FALSE
        and adversarial.false_consensus_risk < 0.7
    )

    return EnhancedCouncilAdvisory(
        enhanced_id=_council_id("eadv"),
        base_advisory=base_advisory,
        adversarial=adversarial,
        minority=minority,
        red_team=red_team,
        blue_team=blue_team,
        consensus=consensus,
        guardrails=guardrails,
        non_actions=non_actions,
        residual_uncertainty=residual,
        what_would_change=what_would_change,
        dissent_preserved=minority.dissent_preserved,
        false_consensus_risk=adversarial.false_consensus_risk,
        overall_safe=overall_safe,
        warnings=warnings,
    )
