"""GovernanceEngine — classifies signals by risk and decides execution authority.

Merges the production authority_engine.py risk classification with
UMH governance protocol's GovernanceVerdict model.
"""

from __future__ import annotations

import re
from typing import Any, Protocol, runtime_checkable

from substrate.types import (
    ExecutionContext,
    ExecutionPlan,
    GovernanceDecision,
    GovernanceVerdict,
    PermissionTier,
    RiskClass,
    SignalEnvelope,
    required_tier_for_action,
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
    """Deterministic-first governance with risk classification and permission tiers."""

    async def classify(
        self, signal: SignalEnvelope, context: ExecutionContext
    ) -> GovernanceVerdict:
        """Classify a signal's risk and decide whether to approve execution."""
        risk_class = self._classify_risk(signal.content)

        tier_check = self._check_permission_tier(signal.content, context)
        if tier_check is not None:
            return GovernanceVerdict(
                signal_id=signal.id,
                risk_class=risk_class,
                decision=GovernanceDecision.DENY,
                rationale=tier_check,
            )

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

    def check_tier(self, action_type: str, identity_tier: str) -> dict[str, Any]:
        """Check if an action is permitted by the caller's permission tier.

        Returns dict with 'permitted' bool and 'reason' str.
        """
        try:
            caller_tier = PermissionTier(identity_tier)
        except ValueError:
            caller_tier = PermissionTier.EXECUTE

        required = required_tier_for_action(action_type)
        permitted = caller_tier.permits(required)
        return {
            "permitted": permitted,
            "caller_tier": caller_tier.value,
            "required_tier": required.value,
            "reason": (
                f"tier {caller_tier.value} permits {required.value}"
                if permitted
                else f"tier {caller_tier.value} insufficient — {required.value} required"
            ),
        }

    def _check_permission_tier(self, content: str, context: ExecutionContext) -> str | None:
        """Return denial rationale if the identity's tier blocks the action, else None."""
        tier_str = getattr(context.identity, "permission_tier", "execute")
        try:
            caller_tier = PermissionTier(tier_str)
        except ValueError:
            caller_tier = PermissionTier.EXECUTE

        inferred_action = self._infer_action_type(content)
        if inferred_action is None:
            return None

        required = required_tier_for_action(inferred_action)
        if caller_tier.permits(required):
            return None
        return (
            f"Permission tier {caller_tier.value} cannot perform "
            f"{inferred_action} (requires {required.value})"
        )

    def _infer_action_type(self, content: str) -> str | None:
        """Best-effort deterministic inference of action type from content."""
        c = content.lower()
        if _CRITICAL_PATTERNS.search(c):
            if "payment" in c:
                return "execute_payment"
            if "delete" in c:
                return "delete_records"
            return "send_message"
        if _HIGH_PATTERNS.search(c):
            if "outreach" in c:
                return "create_outreach"
            if "book" in c:
                return "book_call"
            return "post_content"
        if _MEDIUM_PATTERNS.search(c):
            if "draft" in c:
                return "draft_message"
            return "create_task"
        return None

    def _classify_risk(self, content: str) -> RiskClass:
        """Classify risk based on content patterns. Deterministic spine."""
        if _CRITICAL_PATTERNS.search(content):
            return RiskClass.CRITICAL
        if _HIGH_PATTERNS.search(content):
            return RiskClass.HIGH
        if _MEDIUM_PATTERNS.search(content):
            return RiskClass.MEDIUM
        return RiskClass.LOW
