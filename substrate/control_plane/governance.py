"""GovernanceEngine — classifies signals by risk and decides execution authority.

Merges the production authority_engine.py risk classification with
UMH governance protocol's GovernanceVerdict model.
"""

from __future__ import annotations

import re
from typing import Protocol, runtime_checkable

from substrate.types import (
    ExecutionContext,
    ExecutionPlan,
    GovernanceDecision,
    GovernanceVerdict,
    RiskClass,
    SignalEnvelope,
)


@runtime_checkable
class GovernanceEngine(Protocol):
    """Protocol for governance engines."""

    async def classify(
        self, signal: SignalEnvelope, context: ExecutionContext
    ) -> GovernanceVerdict: ...

    async def check_execution(self, plan: ExecutionPlan, verdict: GovernanceVerdict) -> bool: ...


AUTONOMY_THRESHOLDS: dict[RiskClass, int] = {
    RiskClass.CRITICAL: 999,
    RiskClass.HIGH: 3,
    RiskClass.MEDIUM: 1,
    RiskClass.LOW: 0,
}

_CRITICAL_PATTERNS = re.compile(
    r"\b("
    r"send\s+(?:email|message|dm)"
    r"|execute\s+payment"
    r"|delete\s+records?"
    r"|bulk\s+update"
    r"|mass\s+outreach"
    r"|publish"
    r"|robotic\s+arm"
    r"|activate\s+(?:arm|motor|actuator)"
    r"|iot\s+command"
    r"|vehicle\s+control"
    r")\b",
    re.IGNORECASE,
)
_HIGH_PATTERNS = re.compile(
    r"\b(create\s+outreach|post\s+content|book\s+call|update\s+crm)\b",
    re.IGNORECASE,
)
_MEDIUM_PATTERNS = re.compile(
    r"\b(draft\s+(?:message|content)|create\s+(?:task|document))\b",
    re.IGNORECASE,
)


class ConcreteGovernanceEngine:
    """Deterministic-first governance with risk classification."""

    async def classify(
        self, signal: SignalEnvelope, context: ExecutionContext
    ) -> GovernanceVerdict:
        """Classify a signal's risk and decide whether to approve execution."""
        risk_class = self._classify_risk(signal.content)
        autonomy = context.identity.autonomy_level
        threshold = AUTONOMY_THRESHOLDS[risk_class]

        if autonomy >= threshold:
            decision = GovernanceDecision.APPROVE
            rationale = f"Autonomy level {autonomy} >= threshold {threshold} for {risk_class.value}"
        else:
            decision = GovernanceDecision.DENY
            rationale = f"Autonomy level {autonomy} < threshold {threshold} for {risk_class.value}"

        return GovernanceVerdict(
            signal_id=signal.id,
            risk_class=risk_class,
            decision=decision,
            rationale=rationale,
        )

    async def check_execution(self, plan: ExecutionPlan, verdict: GovernanceVerdict) -> bool:
        """Check whether an execution plan is permitted by the verdict."""
        return verdict.is_executable()

    def _classify_risk(self, content: str) -> RiskClass:
        """Classify risk based on content patterns. Deterministic spine."""
        if _CRITICAL_PATTERNS.search(content):
            return RiskClass.CRITICAL
        if _HIGH_PATTERNS.search(content):
            return RiskClass.HIGH
        if _MEDIUM_PATTERNS.search(content):
            return RiskClass.MEDIUM
        return RiskClass.LOW
