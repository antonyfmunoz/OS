"""Phase 85B adversarial deliberation protocol — structured opposition and stress-testing.

Ensures the council doesn't converge on comfortable answers by requiring
adversarial analysis on every non-trivial deliberation.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.council.contracts import ConfidenceLevel, _council_id
from umh.council.perspective import PerspectiveReport


class AdversarialMode(str, Enum):
    FULL = "full"
    LIGHT = "light"
    NONE = "none"
    UNKNOWN = "unknown"


def normalize_adversarial_mode(value: str) -> AdversarialMode:
    v = value.strip().lower()
    for m in AdversarialMode:
        if m.value == v:
            return m
    return AdversarialMode.UNKNOWN


@dataclass
class AdversarialChallenge:
    """A single structured challenge to the majority position."""

    challenge_id: str = ""
    target_position: str = ""
    challenge_type: str = ""
    challenge_statement: str = ""
    evidence_against: str = ""
    what_would_change_mind: str = ""
    severity: str = "medium"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "challenge_id": self.challenge_id,
            "target_position": self.target_position,
            "challenge_type": self.challenge_type,
            "challenge_statement": self.challenge_statement,
            "evidence_against": self.evidence_against,
            "what_would_change_mind": self.what_would_change_mind,
            "severity": self.severity,
            "metadata": self.metadata,
        }


@dataclass
class AdversarialAssessment:
    """Result of running adversarial analysis on a set of perspectives."""

    assessment_id: str = ""
    request_id: str = ""
    mode: AdversarialMode = AdversarialMode.FULL
    challenges: list[AdversarialChallenge] = field(default_factory=list)
    false_consensus_risk: float = 0.0
    groupthink_indicators: list[str] = field(default_factory=list)
    residual_uncertainty: list[str] = field(default_factory=list)
    what_would_change_recommendation: list[str] = field(default_factory=list)
    guardrails: list[str] = field(default_factory=list)
    non_actions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "request_id": self.request_id,
            "mode": self.mode.value,
            "challenges": [c.to_dict() for c in self.challenges],
            "false_consensus_risk": round(self.false_consensus_risk, 3),
            "groupthink_indicators": self.groupthink_indicators,
            "residual_uncertainty": self.residual_uncertainty,
            "what_would_change_recommendation": self.what_would_change_recommendation,
            "guardrails": self.guardrails,
            "non_actions": self.non_actions,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def run_adversarial_assessment(
    request_id: str,
    perspectives: list[PerspectiveReport],
    *,
    mode: AdversarialMode = AdversarialMode.FULL,
) -> AdversarialAssessment:
    """Analyze perspectives for false consensus, groupthink, and untested assumptions.

    Deterministic v1 — uses structural analysis, not LLM reasoning.
    """
    if not perspectives:
        return AdversarialAssessment(
            assessment_id=_council_id("adv_assess"),
            request_id=request_id,
            mode=mode,
            warnings=["No perspectives to challenge"],
        )

    challenges: list[AdversarialChallenge] = []
    groupthink: list[str] = []
    residual: list[str] = []
    change_triggers: list[str] = []
    guardrails: list[str] = []
    non_actions: list[str] = []

    positions = [p.position for p in perspectives if p.position]
    scores = [p.score for p in perspectives]
    confidences = [p.confidence for p in perspectives]

    score_spread = max(scores) - min(scores) if len(scores) >= 2 else 0.0
    all_agree = score_spread < 0.15 and len(perspectives) >= 3

    if all_agree:
        groupthink.append("All perspectives score within 0.15 — possible groupthink")

    all_same_confidence = len(set(confidences)) == 1 and len(perspectives) >= 3
    if all_same_confidence:
        groupthink.append("All perspectives report identical confidence level")

    no_dissents = all(len(p.dissents) == 0 for p in perspectives)
    if no_dissents and len(perspectives) >= 3:
        groupthink.append("No perspective reported any dissent")

    adversarial_count = sum(1 for p in perspectives if p.metadata.get("adversarial", False))
    if adversarial_count == 0 and len(perspectives) >= 3:
        groupthink.append("No adversarial thinker present in deliberation")

    false_consensus_risk = _calculate_false_consensus_risk(perspectives, score_spread, groupthink)

    for p in perspectives:
        if p.assumptions:
            for asm in p.assumptions:
                residual.append(f"{p.role_id}: assumes {asm.statement}")
        if not p.evidence:
            residual.append(f"{p.role_id}: provided no evidence — position is ungrounded")

    if all_agree and positions:
        challenges.append(
            AdversarialChallenge(
                challenge_id=_council_id("chal"),
                target_position=positions[0][:200],
                challenge_type="false_consensus",
                challenge_statement="All perspectives converged — no genuine opposition was tested",
                evidence_against="Convergence itself is not evidence of correctness",
                what_would_change_mind="One well-evidenced contrary perspective with score > 0.7",
                severity="high",
            )
        )

    weak_evidence_count = sum(1 for p in perspectives if not p.evidence)
    if weak_evidence_count > len(perspectives) / 2:
        challenges.append(
            AdversarialChallenge(
                challenge_id=_council_id("chal"),
                target_position="Majority position",
                challenge_type="evidence_deficit",
                challenge_statement=f"{weak_evidence_count}/{len(perspectives)} perspectives lack evidence",
                evidence_against="Recommendations without evidence are opinions",
                what_would_change_mind="Strong evidence supporting the recommendation",
                severity="high",
            )
        )

    if mode == AdversarialMode.FULL:
        for p in perspectives:
            if p.score > 0.7 and not p.evidence:
                challenges.append(
                    AdversarialChallenge(
                        challenge_id=_council_id("chal"),
                        target_position=p.position[:200],
                        challenge_type="high_confidence_no_evidence",
                        challenge_statement=f"{p.role_id} scores {p.score:.2f} with no evidence",
                        evidence_against="High confidence requires supporting evidence",
                        what_would_change_mind="Evidence supporting the position",
                        severity="medium",
                    )
                )

    if false_consensus_risk > 0.5:
        change_triggers.append("Introducing a well-evidenced contrarian perspective")
    if weak_evidence_count > 0:
        change_triggers.append("Providing strong evidence for or against the recommendation")
    change_triggers.append("New information or changed constraints")

    guardrails.append("Do not treat consensus as proof of correctness")
    guardrails.append("Revisit if assumptions are invalidated")
    if false_consensus_risk > 0.3:
        guardrails.append("Seek explicit contrarian review before acting")

    non_actions.append("Do not proceed if blocking disagreements exist")
    if weak_evidence_count > len(perspectives) / 2:
        non_actions.append("Do not commit irreversible resources without evidence")

    return AdversarialAssessment(
        assessment_id=_council_id("adv_assess"),
        request_id=request_id,
        mode=mode,
        challenges=challenges,
        false_consensus_risk=false_consensus_risk,
        groupthink_indicators=groupthink,
        residual_uncertainty=residual,
        what_would_change_recommendation=change_triggers,
        guardrails=guardrails,
        non_actions=non_actions,
    )


def _calculate_false_consensus_risk(
    perspectives: list[PerspectiveReport],
    score_spread: float,
    groupthink_indicators: list[str],
) -> float:
    """0.0 = no false consensus risk, 1.0 = extremely high risk."""
    if len(perspectives) < 2:
        return 0.0

    risk = 0.0

    if score_spread < 0.1:
        risk += 0.3
    elif score_spread < 0.2:
        risk += 0.15

    risk += min(0.4, len(groupthink_indicators) * 0.1)

    adversarial_count = sum(1 for p in perspectives if p.metadata.get("adversarial", False))
    if adversarial_count == 0:
        risk += 0.2

    evidence_count = sum(1 for p in perspectives if p.evidence)
    if evidence_count == 0:
        risk += 0.2
    elif evidence_count < len(perspectives) / 2:
        risk += 0.1

    return min(1.0, risk)
