"""Deliberation Council — 7-role multi-perspective advisory system.

Before high-risk decisions, the system convenes a council of specialized
perspectives. Each role evaluates the proposal independently, then a
synthesis judge produces a unified recommendation.

Deterministic-first: each role applies structured rules and heuristics.
LLM calls are optional escalation for complex deliberations.

Roles:
  1. Strategist       — long-term alignment with north star goals
  2. Skeptic          — adversarial challenge, finds flaws
  3. Completeness     — checks all 13 slots are filled
  4. Risk/Governance  — evaluates risk class, authority requirements
  5. Domain Expert    — domain-specific knowledge and constraints
  6. Engineer         — implementation feasibility and technical debt
  7. Synthesis Judge  — weighs all perspectives, produces final verdict
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from substrate.reality_model.simulation import SimulationReality

logger = logging.getLogger(__name__)


class CouncilRole(str, Enum):
    STRATEGIST = "strategist"
    SKEPTIC = "skeptic"
    COMPLETENESS = "completeness"
    RISK_GOVERNANCE = "risk_governance"
    DOMAIN_EXPERT = "domain_expert"
    ENGINEER = "engineer"
    SYNTHESIS_JUDGE = "synthesis_judge"


class Verdict(str, Enum):
    APPROVE = "approve"
    APPROVE_WITH_CONDITIONS = "approve_with_conditions"
    DEFER = "defer"
    REJECT = "reject"


@dataclass
class RoleOpinion:
    role: CouncilRole
    verdict: Verdict
    confidence: float = 0.5
    rationale: str = ""
    concerns: list[str] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role.value,
            "verdict": self.verdict.value,
            "confidence": round(self.confidence, 3),
            "rationale": self.rationale,
            "concerns": self.concerns,
            "conditions": self.conditions,
        }


@dataclass
class CouncilDeliberation:
    proposal: str
    opinions: list[RoleOpinion] = field(default_factory=list)
    synthesis: RoleOpinion | None = None
    final_verdict: Verdict = Verdict.DEFER
    overall_confidence: float = 0.0
    duration_ms: float = 0.0
    dissenting_roles: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal": self.proposal[:300],
            "opinions": [o.to_dict() for o in self.opinions],
            "synthesis": self.synthesis.to_dict() if self.synthesis else None,
            "final_verdict": self.final_verdict.value,
            "overall_confidence": round(self.overall_confidence, 3),
            "duration_ms": round(self.duration_ms, 1),
            "dissenting_roles": self.dissenting_roles,
        }


_RISK_KEYWORDS = frozenset([
    "delete", "drop", "truncate", "remove", "destroy", "kill",
    "production", "deploy", "migrate", "force", "override",
    "financial", "payment", "billing", "credential", "secret",
    "external", "public", "publish", "broadcast",
])

_STRATEGIC_KEYWORDS = frozenset([
    "revenue", "customer", "growth", "brand", "market",
    "acquisition", "retention", "conversion", "profit",
    "competitive", "moat", "scale",
])

_TECHNICAL_DEBT_SIGNALS = frozenset([
    "hack", "workaround", "temporary", "todo", "fixme",
    "quick fix", "shortcut", "skip", "bypass", "ignore",
])


class DeliberationCouncil:
    """Convenes 7 advisory roles to evaluate high-risk proposals."""

    def __init__(
        self,
        completeness_engine: Any | None = None,
        simulation: SimulationReality | None = None,
    ) -> None:
        self._completeness = completeness_engine
        self._simulation = simulation or SimulationReality()

    def deliberate(
        self,
        proposal: str,
        context: dict[str, Any] | None = None,
    ) -> CouncilDeliberation:
        """Run a full council deliberation on a proposal."""
        t0 = time.monotonic()
        ctx = context or {}

        delib = CouncilDeliberation(proposal=proposal)

        delib.opinions = [
            self._strategist(proposal, ctx),
            self._skeptic(proposal, ctx),
            self._completeness_auditor(proposal, ctx),
            self._risk_governance(proposal, ctx),
            self._domain_expert(proposal, ctx),
            self._engineer(proposal, ctx),
        ]

        delib.synthesis = self._synthesize(delib.opinions, proposal)
        delib.final_verdict = delib.synthesis.verdict
        delib.overall_confidence = delib.synthesis.confidence
        delib.dissenting_roles = [
            o.role.value for o in delib.opinions
            if o.verdict != delib.final_verdict
        ]
        delib.duration_ms = (time.monotonic() - t0) * 1000

        return delib

    def _strategist(self, proposal: str, ctx: dict[str, Any]) -> RoleOpinion:
        """Does this align with north star goals?"""
        lower = proposal.lower()
        strategic_hits = [kw for kw in _STRATEGIC_KEYWORDS if kw in lower]

        if strategic_hits:
            return RoleOpinion(
                role=CouncilRole.STRATEGIST,
                verdict=Verdict.APPROVE,
                confidence=0.7,
                rationale=f"Strategically aligned: {', '.join(strategic_hits)}",
            )

        if any(kw in lower for kw in ["test", "experiment", "prototype"]):
            return RoleOpinion(
                role=CouncilRole.STRATEGIST,
                verdict=Verdict.APPROVE_WITH_CONDITIONS,
                confidence=0.6,
                rationale="Experimental — approve with time-box",
                conditions=["Time-box to 2 hours", "Define success criteria upfront"],
            )

        return RoleOpinion(
            role=CouncilRole.STRATEGIST,
            verdict=Verdict.APPROVE,
            confidence=0.5,
            rationale="No strategic flags — neutral",
        )

    def _skeptic(self, proposal: str, ctx: dict[str, Any]) -> RoleOpinion:
        """Challenge assumptions and find flaws."""
        lower = proposal.lower()
        concerns: list[str] = []

        if len(proposal.split()) < 10:
            concerns.append("Proposal is vague — insufficient detail to evaluate")

        if "all" in lower or "every" in lower or "always" in lower:
            concerns.append("Absolute language detected — likely over-scoped")

        if any(kw in lower for kw in _TECHNICAL_DEBT_SIGNALS):
            concerns.append("Technical debt signals detected — shortcut being proposed")

        if "and" in lower and lower.count("and") > 2:
            concerns.append("Multiple objectives bundled — should be decomposed")

        if concerns:
            return RoleOpinion(
                role=CouncilRole.SKEPTIC,
                verdict=Verdict.APPROVE_WITH_CONDITIONS if len(concerns) < 3 else Verdict.REJECT,
                confidence=0.7,
                rationale=f"Found {len(concerns)} concern(s)",
                concerns=concerns,
                conditions=["Address concerns before proceeding"] if len(concerns) < 3 else [],
            )

        return RoleOpinion(
            role=CouncilRole.SKEPTIC,
            verdict=Verdict.APPROVE,
            confidence=0.6,
            rationale="No obvious flaws — approve with normal caution",
        )

    def _completeness_auditor(self, proposal: str, ctx: dict[str, Any]) -> RoleOpinion:
        """Check all 13 completeness slots."""
        if self._completeness is None:
            try:
                from substrate.governance.validation.completeness_engine import CompletenessEngine
                self._completeness = CompletenessEngine()
            except Exception:
                return RoleOpinion(
                    role=CouncilRole.COMPLETENESS,
                    verdict=Verdict.DEFER,
                    confidence=0.3,
                    rationale="Completeness engine unavailable",
                )

        result = self._completeness.evaluate_text(proposal)

        if result.complete:
            return RoleOpinion(
                role=CouncilRole.COMPLETENESS,
                verdict=Verdict.APPROVE,
                confidence=0.9,
                rationale=f"All 13 slots filled (score={result.score:.2f})",
            )

        if result.score >= 0.7:
            return RoleOpinion(
                role=CouncilRole.COMPLETENESS,
                verdict=Verdict.APPROVE_WITH_CONDITIONS,
                confidence=0.6,
                rationale=f"Score {result.score:.2f} — missing: {', '.join(result.missing)}",
                conditions=[f"Fill {slot} slot" for slot in result.missing],
            )

        return RoleOpinion(
            role=CouncilRole.COMPLETENESS,
            verdict=Verdict.REJECT,
            confidence=0.8,
            rationale=f"Score {result.score:.2f} — too many gaps: {', '.join(result.missing)}",
            concerns=[f"Missing: {slot}" for slot in result.missing],
        )

    def _risk_governance(self, proposal: str, ctx: dict[str, Any]) -> RoleOpinion:
        """Evaluate risk and governance requirements."""
        lower = proposal.lower()
        risk_hits = [kw for kw in _RISK_KEYWORDS if kw in lower]

        if not risk_hits:
            return RoleOpinion(
                role=CouncilRole.RISK_GOVERNANCE,
                verdict=Verdict.APPROVE,
                confidence=0.8,
                rationale="No risk keywords detected — low risk",
            )

        high_risk = [kw for kw in risk_hits if kw in {"production", "financial", "payment", "credential", "secret", "destroy", "force"}]

        if high_risk:
            return RoleOpinion(
                role=CouncilRole.RISK_GOVERNANCE,
                verdict=Verdict.APPROVE_WITH_CONDITIONS,
                confidence=0.7,
                rationale=f"High-risk indicators: {', '.join(high_risk)}",
                conditions=[
                    "Requires founder approval",
                    "Must have rollback plan",
                    "Execute in sandbox first",
                ],
                concerns=[f"Risk factor: {kw}" for kw in high_risk],
            )

        return RoleOpinion(
            role=CouncilRole.RISK_GOVERNANCE,
            verdict=Verdict.APPROVE_WITH_CONDITIONS,
            confidence=0.6,
            rationale=f"Medium-risk indicators: {', '.join(risk_hits)}",
            conditions=["Standard governance gate applies"],
        )

    def _domain_expert(self, proposal: str, ctx: dict[str, Any]) -> RoleOpinion:
        """Domain-specific evaluation with simulation for risky proposals."""
        lower = proposal.lower()
        concerns: list[str] = []
        conditions: list[str] = []

        if any(kw in lower for kw in ["api", "endpoint", "request", "response"]):
            conditions.extend(["Verify rate limit headroom", "Confirm authentication is current"])

        if any(kw in lower for kw in ["database", "query", "migration", "schema"]):
            conditions.extend(["Backup exists", "Test on staging first"])

        sim_result = self._simulation.simulate(proposal)
        if not sim_result.safe_to_execute:
            concerns.extend(sim_result.diff.risk_factors)
            conditions.append("Run in sandbox before production")

        if concerns or conditions:
            return RoleOpinion(
                role=CouncilRole.DOMAIN_EXPERT,
                verdict=Verdict.APPROVE_WITH_CONDITIONS,
                confidence=max(0.5, sim_result.overall_confidence),
                rationale=f"Simulation: {sim_result.diff.predicted_outcome} (confidence={sim_result.overall_confidence:.2f})",
                concerns=concerns,
                conditions=conditions,
            )

        return RoleOpinion(
            role=CouncilRole.DOMAIN_EXPERT,
            verdict=Verdict.APPROVE,
            confidence=max(0.5, sim_result.overall_confidence),
            rationale=f"Simulation safe: {sim_result.diff.predicted_outcome}",
        )

    def _engineer(self, proposal: str, ctx: dict[str, Any]) -> RoleOpinion:
        """Implementation feasibility and technical debt assessment."""
        lower = proposal.lower()
        concerns: list[str] = []

        debt_signals = [kw for kw in _TECHNICAL_DEBT_SIGNALS if kw in lower]
        if debt_signals:
            concerns.append(f"Technical debt signals: {', '.join(debt_signals)}")

        word_count = len(proposal.split())
        if word_count > 200:
            concerns.append("Proposal is very long — may be over-scoped for single execution")

        if "and" in lower and "or" in lower:
            concerns.append("Conditional branching in proposal — break into separate tasks")

        if concerns:
            return RoleOpinion(
                role=CouncilRole.ENGINEER,
                verdict=Verdict.APPROVE_WITH_CONDITIONS,
                confidence=0.6,
                rationale=f"Feasible with {len(concerns)} concern(s)",
                concerns=concerns,
                conditions=["Decompose into smaller tasks" if word_count > 200 else "Address debt signals"],
            )

        return RoleOpinion(
            role=CouncilRole.ENGINEER,
            verdict=Verdict.APPROVE,
            confidence=0.7,
            rationale="Technically feasible — no implementation concerns",
        )

    def _synthesize(self, opinions: list[RoleOpinion], proposal: str) -> RoleOpinion:
        """Synthesis judge: weigh all perspectives and produce final verdict."""
        approve_count = sum(1 for o in opinions if o.verdict == Verdict.APPROVE)
        conditional_count = sum(1 for o in opinions if o.verdict == Verdict.APPROVE_WITH_CONDITIONS)
        reject_count = sum(1 for o in opinions if o.verdict == Verdict.REJECT)
        defer_count = sum(1 for o in opinions if o.verdict == Verdict.DEFER)

        all_concerns = []
        all_conditions = []
        for o in opinions:
            all_concerns.extend(o.concerns)
            all_conditions.extend(o.conditions)

        avg_confidence = sum(o.confidence for o in opinions) / len(opinions) if opinions else 0.5

        if reject_count >= 2:
            return RoleOpinion(
                role=CouncilRole.SYNTHESIS_JUDGE,
                verdict=Verdict.REJECT,
                confidence=avg_confidence,
                rationale=f"Council rejected: {reject_count} roles voted reject",
                concerns=all_concerns[:10],
            )

        if reject_count == 1 and conditional_count >= 2:
            return RoleOpinion(
                role=CouncilRole.SYNTHESIS_JUDGE,
                verdict=Verdict.APPROVE_WITH_CONDITIONS,
                confidence=avg_confidence * 0.8,
                rationale="One rejection, multiple conditions — proceed carefully",
                concerns=all_concerns[:10],
                conditions=list(set(all_conditions))[:10],
            )

        if approve_count >= 4 and reject_count == 0:
            if all_conditions:
                return RoleOpinion(
                    role=CouncilRole.SYNTHESIS_JUDGE,
                    verdict=Verdict.APPROVE_WITH_CONDITIONS,
                    confidence=avg_confidence,
                    rationale=f"Strong approval ({approve_count} approve) with conditions",
                    conditions=list(set(all_conditions))[:5],
                )
            return RoleOpinion(
                role=CouncilRole.SYNTHESIS_JUDGE,
                verdict=Verdict.APPROVE,
                confidence=avg_confidence,
                rationale=f"Council approved: {approve_count} roles approve",
            )

        return RoleOpinion(
            role=CouncilRole.SYNTHESIS_JUDGE,
            verdict=Verdict.APPROVE_WITH_CONDITIONS,
            confidence=avg_confidence,
            rationale=f"Mixed council: {approve_count} approve, {conditional_count} conditional, {reject_count} reject",
            concerns=all_concerns[:10],
            conditions=list(set(all_conditions))[:10],
        )
