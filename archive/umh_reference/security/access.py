"""Access policy — access control decisions for UMH resources.

Provides a default open policy (AllowAll) for standalone operation
and an injectable AccessPolicy protocol for production deployments.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AccessDecision:
    """Result of an access control check."""

    allowed: bool
    reason: str
    principal: str
    resource: str
    action: str


class AllowAllPolicy:
    """Default open policy — allows all access. For standalone/dev use."""

    def check_access(
        self,
        principal: str,
        resource: str,
        action: str,
    ) -> tuple[bool, str]:
        return True, f"{principal} permitted {action} on {resource}"


class DenyAllPolicy:
    """Locked-down policy — denies all access. For testing."""

    def check_access(
        self,
        principal: str,
        resource: str,
        action: str,
    ) -> tuple[bool, str]:
        return False, f"Access denied: {principal} cannot {action} on {resource}"


_POLICY: Any = None


def get_access_policy() -> Any:
    """Get the configured access policy."""
    global _POLICY
    if _POLICY is None:
        _POLICY = AllowAllPolicy()
    return _POLICY


def set_access_policy(policy: Any) -> None:
    """Override the access policy."""
    global _POLICY
    _POLICY = policy


def reset_access_policy() -> None:
    """Clear the access policy singleton (for testing)."""
    global _POLICY
    _POLICY = None


def check_access(principal: str, resource: str, action: str) -> AccessDecision:
    """Run an access control check."""
    policy = get_access_policy()
    allowed, reason = policy.check_access(principal, resource, action)
    return AccessDecision(
        allowed=allowed,
        reason=reason,
        principal=principal,
        resource=resource,
        action=action,
    )
