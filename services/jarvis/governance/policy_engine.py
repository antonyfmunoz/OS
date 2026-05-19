"""Policy engine — evaluates risk class + context to produce governance verdicts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from services.jarvis.governance.authority import AuthorityLevel
from services.jarvis.governance.risk_classes import RiskClass
from services.jarvis.protocols.governance import (
    GovernanceCondition,
    GovernanceDecision,
    GovernanceRequest,
    GovernanceVerdict,
    RiskLevel,
)


@dataclass(frozen=True)
class PolicyVerdict:
    """Result of policy evaluation before converting to protocol GovernanceVerdict."""

    risk_class: RiskClass
    authority_required: AuthorityLevel
    decision: GovernanceDecision
    rationale: str
    conditions: list[GovernanceCondition] = field(default_factory=list)


# path overrides keyed by (risk_class, context_key) → authority level
_PATH_OVERRIDES: dict[tuple[RiskClass, str], AuthorityLevel] = {}


class PolicyEngine:
    """Stateless policy evaluator.

    Maps (RiskClass, context) → GovernanceVerdict using the default
    policy table with optional path overrides and safe-root expansion.
    """

    def __init__(
        self,
        safe_roots: list[str] | None = None,
        allowed_shell_prefixes: list[str] | None = None,
        overrides: dict[tuple[RiskClass, str], AuthorityLevel] | None = None,
    ) -> None:
        self._safe_roots: list[str] = safe_roots or []
        self._allowed_shell_prefixes: list[str] = allowed_shell_prefixes or []
        self._overrides = dict(_PATH_OVERRIDES)
        if overrides:
            self._overrides.update(overrides)

    @property
    def safe_roots(self) -> list[str]:
        return list(self._safe_roots)

    @property
    def allowed_shell_prefixes(self) -> list[str]:
        return list(self._allowed_shell_prefixes)

    def evaluate(
        self,
        risk_class: RiskClass,
        request: GovernanceRequest,
        context: dict[str, Any] | None = None,
    ) -> GovernanceVerdict:
        """Evaluate a governance request against the default policy."""
        ctx = context or {}
        verdict = self._apply_policy(risk_class, request, ctx)
        return self._to_protocol_verdict(request, verdict)

    def _apply_policy(
        self,
        risk_class: RiskClass,
        request: GovernanceRequest,
        context: dict[str, Any],
    ) -> PolicyVerdict:
        authority = _DEFAULT_POLICY[risk_class]

        if risk_class == RiskClass.READ_ONLY:
            return PolicyVerdict(
                risk_class=risk_class,
                authority_required=AuthorityLevel.AUTONOMOUS,
                decision=GovernanceDecision.APPROVE,
                rationale="read-only operations are always allowed",
            )

        if risk_class == RiskClass.SAFE_WRITE:
            target_path = context.get("target_path", "")
            if self._is_safe_rooted(target_path):
                return PolicyVerdict(
                    risk_class=risk_class,
                    authority_required=AuthorityLevel.AUTONOMOUS,
                    decision=GovernanceDecision.APPROVE,
                    rationale=f"write inside safe root: {target_path}",
                )
            return PolicyVerdict(
                risk_class=risk_class,
                authority_required=AuthorityLevel.APPROVE,
                decision=GovernanceDecision.DEFER,
                rationale=f"write outside safe roots requires approval: {target_path}",
            )

        if risk_class == RiskClass.REVERSIBLE_WRITE:
            target_path = context.get("target_path", "")
            if self._is_safe_rooted(target_path) and context.get("explicitly_safe", False):
                return PolicyVerdict(
                    risk_class=risk_class,
                    authority_required=AuthorityLevel.NOTIFY,
                    decision=GovernanceDecision.APPROVE,
                    rationale=f"reversible write in safe root with explicit flag: {target_path}",
                )
            return PolicyVerdict(
                risk_class=risk_class,
                authority_required=AuthorityLevel.APPROVE,
                decision=GovernanceDecision.DEFER,
                rationale="reversible write requires approval",
            )

        if risk_class in (
            RiskClass.IRREVERSIBLE_WRITE,
            RiskClass.EXTERNAL_COMMUNICATION,
            RiskClass.FINANCIAL,
        ):
            return PolicyVerdict(
                risk_class=risk_class,
                authority_required=AuthorityLevel.DENY,
                decision=GovernanceDecision.DENY,
                rationale=f"{risk_class.value} blocked by default policy",
            )

        if risk_class in (RiskClass.SECURITY_SENSITIVE, RiskClass.PHYSICAL_WORLD):
            return PolicyVerdict(
                risk_class=risk_class,
                authority_required=AuthorityLevel.ESCALATE,
                decision=GovernanceDecision.ESCALATE,
                rationale=f"{risk_class.value} requires escalation",
            )

        return PolicyVerdict(
            risk_class=risk_class,
            authority_required=authority,
            decision=GovernanceDecision.DENY,
            rationale="unhandled risk class — deny by default",
        )

    def _is_safe_rooted(self, path: str) -> bool:
        if not path:
            return False
        from pathlib import PurePosixPath

        resolved = str(PurePosixPath(path))
        return any(resolved.startswith(root) for root in self._safe_roots)

    def _to_protocol_verdict(
        self,
        request: GovernanceRequest,
        verdict: PolicyVerdict,
    ) -> GovernanceVerdict:
        return GovernanceVerdict(
            request_id=request.id,
            decision=verdict.decision,
            risk_level=verdict.risk_class.to_risk_level(),
            rationale=verdict.rationale,
            conditions=verdict.conditions,
            decided_by="policy_engine",
        )


_DEFAULT_POLICY: dict[RiskClass, AuthorityLevel] = {
    RiskClass.READ_ONLY: AuthorityLevel.AUTONOMOUS,
    RiskClass.SAFE_WRITE: AuthorityLevel.NOTIFY,
    RiskClass.REVERSIBLE_WRITE: AuthorityLevel.APPROVE,
    RiskClass.IRREVERSIBLE_WRITE: AuthorityLevel.DENY,
    RiskClass.EXTERNAL_COMMUNICATION: AuthorityLevel.DENY,
    RiskClass.FINANCIAL: AuthorityLevel.DENY,
    RiskClass.SECURITY_SENSITIVE: AuthorityLevel.ESCALATE,
    RiskClass.PHYSICAL_WORLD: AuthorityLevel.ESCALATE,
}
