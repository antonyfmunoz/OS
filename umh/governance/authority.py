"""Governance authority — safety and permission gating before execution.

Every execution request must pass governance before reaching a capability
backend. Governance checks:
  1. Is the operation allowed for this authority class?
  2. Does it exceed resource constraints?
  3. Are there any hard blocks?

Authority classes (least to most permissive):
  OBSERVE  — read-only, no side effects
  ANALYZE  — compute + read, no mutations
  ACT      — mutations within sandbox
  EXECUTE  — full execution authority

No LLM calls. No domain-specific logic. Pure policy evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Protocol, runtime_checkable


class AuthorityLevel(IntEnum):
    OBSERVE = 1
    ANALYZE = 2
    ACT = 3
    EXECUTE = 4


@dataclass(frozen=True)
class GovernanceDecision:
    """Result of a governance check."""

    allowed: bool
    authority_level: AuthorityLevel
    reason: str
    constraints_applied: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "authority_level": self.authority_level.name,
            "reason": self.reason,
            "constraints_applied": self.constraints_applied,
            "warnings": list(self.warnings),
        }


_OPERATION_AUTHORITY: dict[str, AuthorityLevel] = {
    "answer_query": AuthorityLevel.OBSERVE,
    "run_analysis": AuthorityLevel.ANALYZE,
    "check_status": AuthorityLevel.OBSERVE,
    "execute_action": AuthorityLevel.ACT,
    "create_artifact": AuthorityLevel.ACT,
    "process_input": AuthorityLevel.ANALYZE,
}

_DEFAULT_AUTHORITY = AuthorityLevel.ANALYZE


@runtime_checkable
class GovernancePolicy(Protocol):
    """Extensible governance policy contract."""

    def evaluate(
        self,
        operation: str,
        authority_level: AuthorityLevel,
        constraints: dict[str, Any],
    ) -> GovernanceDecision: ...


class DefaultGovernancePolicy:
    """Default policy — allows everything up to the granted authority level."""

    def __init__(self, max_authority: AuthorityLevel = AuthorityLevel.ACT) -> None:
        self._max = max_authority

    def evaluate(
        self,
        operation: str,
        authority_level: AuthorityLevel,
        constraints: dict[str, Any],
    ) -> GovernanceDecision:
        required = _OPERATION_AUTHORITY.get(operation, _DEFAULT_AUTHORITY)
        granted = min(authority_level, self._max)

        if required > granted:
            return GovernanceDecision(
                allowed=False,
                authority_level=granted,
                reason=f"Operation '{operation}' requires {required.name} "
                f"but granted authority is {granted.name}",
            )

        warnings: list[str] = []
        if required >= AuthorityLevel.ACT:
            warnings.append("Operation has side effects")

        return GovernanceDecision(
            allowed=True,
            authority_level=granted,
            reason=f"Authorized at {granted.name} level",
            constraints_applied=constraints,
            warnings=tuple(warnings),
        )


_POLICY: GovernancePolicy | None = None


def get_governance_policy() -> GovernancePolicy:
    global _POLICY
    if _POLICY is None:
        _POLICY = DefaultGovernancePolicy()
    return _POLICY


def set_governance_policy(policy: GovernancePolicy) -> None:
    global _POLICY
    _POLICY = policy


def reset_governance_policy() -> None:
    global _POLICY
    _POLICY = None


def check_governance(
    operation: str,
    authority_level: AuthorityLevel = AuthorityLevel.ANALYZE,
    constraints: dict[str, Any] | None = None,
) -> GovernanceDecision:
    """Run a governance check for the given operation."""
    policy = get_governance_policy()
    return policy.evaluate(operation, authority_level, constraints or {})
