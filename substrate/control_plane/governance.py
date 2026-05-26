"""GovernanceEngine — the single governance entry point for UMH.

Five governance layers, one API surface:
  1. Signal-level: classify() — risk + autonomy check from SignalEnvelope content
  2. Business-action: evaluate_action() — delegates to AuthorityEngine
  3. Capability-level: evaluate_capability() — delegates to PolicyEngine
  4. Output quality: evaluate_quality() — delegates to QualityTransformationGate
  5. Tier check: check_tier() — permission tier validation

All external callers should go through ConcreteGovernanceEngine.
Internal engines (AuthorityEngine, PolicyEngine, QualityGate) handle
their own concerns but are accessed through this facade.
"""

from __future__ import annotations

import re
from typing import Any, Protocol, runtime_checkable

from substrate.types import (
    ExecutionContext,
    ExecutionPlan,
    GovernanceDecision,
    GovernanceVerdict,
    GovernanceRequest,
    PipelineGovernanceVerdict,
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
    RiskClass.FORBIDDEN: 999,
    RiskClass.CRITICAL: 999,
    RiskClass.HIGH: 3,
    RiskClass.MEDIUM: 1,
    RiskClass.LOW: 0,
    RiskClass.NEGLIGIBLE: 0,
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

    def evaluate_action(
        self,
        action_type: str,
        workflow_id: str | None = None,
        caller_permission_tier: str = "execute",
    ) -> dict[str, Any]:
        """Business-action governance — delegates to AuthorityEngine.

        Use for explicit action types (send_dm, execute_payment, etc.).
        Returns the same dict shape as AuthorityEngine.check_can_execute().
        """
        from substrate.governance.policy.authority_engine import AuthorityEngine
        from substrate.state.context.context import load_context_from_env

        ctx = load_context_from_env()
        ae = AuthorityEngine(ctx)
        return ae.check_can_execute(action_type, workflow_id, caller_permission_tier)

    def evaluate_capability(
        self,
        risk_category: str,
        request: GovernanceRequest,
        context: dict[str, Any] | None = None,
    ) -> PipelineGovernanceVerdict:
        """Capability-level governance — delegates to PolicyEngine.

        Use for side-effect classification (READ_ONLY, FINANCIAL, etc.).
        """
        from substrate.governance.policy_engine import PolicyEngine
        from substrate.governance.risk_classes import ActionRiskCategory

        try:
            category = ActionRiskCategory(risk_category)
        except ValueError:
            category = ActionRiskCategory.READ_ONLY

        pe = PolicyEngine(safe_roots=["/opt/OS"])
        return pe.evaluate(category, request, context)

    def queue_for_approval(
        self,
        action_type: str,
        request: dict[str, Any],
        workflow_id: str | None = None,
    ) -> str:
        """Queue an action for human approval via AuthorityEngine.

        Returns the approval_id string.
        """
        from substrate.governance.policy.authority_engine import AuthorityEngine
        from substrate.state.context.context import load_context_from_env

        ctx = load_context_from_env()
        ae = AuthorityEngine(ctx)
        return ae.queue_for_approval(request)

    def get_pending_approvals(self) -> list[dict[str, Any]]:
        """List all pending approval requests."""
        from substrate.governance.policy.authority_engine import AuthorityEngine
        from substrate.state.context.context import load_context_from_env

        ctx = load_context_from_env()
        ae = AuthorityEngine(ctx)
        return ae.get_pending()

    def evaluate_quality(
        self,
        output: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Output quality governance — delegates to QualityTransformationGate.

        Scores output against the 4-value lens (reality, intelligence,
        personalization, execution). Returns score dict with passed bool.
        """
        try:
            from substrate.governance.quality.quality_gate import QualityTransformationGate

            gate = QualityTransformationGate()
            result = gate.transform(output, context or {})
            return {
                "score": result.quality_score,
                "passed": result.quality_score >= 0.75,
                "values": result.value_scores,
            }
        except Exception:
            return {"score": 0.5, "passed": True, "values": {}}

    def _classify_risk(self, content: str) -> RiskClass:
        """Classify risk based on content patterns. Deterministic spine."""
        if _CRITICAL_PATTERNS.search(content):
            return RiskClass.CRITICAL
        if _HIGH_PATTERNS.search(content):
            return RiskClass.HIGH
        if _MEDIUM_PATTERNS.search(content):
            return RiskClass.MEDIUM
        return RiskClass.LOW
