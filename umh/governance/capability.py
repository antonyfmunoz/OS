"""UMH Capability System — permission + risk matrix for agent operations.

Every agent carries a CapabilityProfile describing which operations it can
perform. Every step or action is mapped to a required CapabilityLevel +
RiskTier. The CapabilityEnforcer answers one question:
    may(profile, operation, risk) → Decision

This module is intentionally pure. No I/O, no LLM calls, no external
imports. It is safe to import from anywhere in the stack.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable


# ---------------------------------------------------------------------------
# Capability levels — four-level lattice
# ---------------------------------------------------------------------------


class CapabilityLevel(str, Enum):
    """Four-level capability lattice. Each level implies all lower levels."""

    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        return _CAP_RANK[self]


_CAP_RANK = {
    CapabilityLevel.READ: 0,
    CapabilityLevel.WRITE: 1,
    CapabilityLevel.EXECUTE: 2,
    CapabilityLevel.CRITICAL: 3,
}


def cap_implies(have: CapabilityLevel, need: CapabilityLevel) -> bool:
    """A higher-rank capability implies all lower ones."""
    return have.rank >= need.rank


# ---------------------------------------------------------------------------
# Operation kinds — every thing an agent can "do"
# ---------------------------------------------------------------------------


class OperationKind(str, Enum):
    """Cross-product of (what kind of work, which layer).

    Kept small and explicit. Adding a kind = adding a real boundary.
    """

    READ_DATA = "read_data"
    READ_MEMORY = "read_memory"
    READ_SUMMARY = "read_summary"
    WRITE_MEMORY = "write_memory"
    WRITE_LOG = "write_log"
    WRITE_NEW_FILE = "write_new_file"
    EDIT_FILE = "edit_file"
    RUN_SCRIPT = "run_script"
    RUN_COMMAND = "run_command"
    CALL_LLM = "call_llm"
    DELETE_FILE = "delete_file"
    EDIT_CRITICAL = "edit_critical"
    MUTATE_INFRA = "mutate_infra"
    READ_GRAPH = "read_graph"


_REQUIRED_CAP: dict[OperationKind, CapabilityLevel] = {
    OperationKind.READ_DATA: CapabilityLevel.READ,
    OperationKind.READ_MEMORY: CapabilityLevel.READ,
    OperationKind.READ_SUMMARY: CapabilityLevel.READ,
    OperationKind.READ_GRAPH: CapabilityLevel.READ,
    OperationKind.CALL_LLM: CapabilityLevel.READ,
    OperationKind.WRITE_MEMORY: CapabilityLevel.WRITE,
    OperationKind.WRITE_LOG: CapabilityLevel.WRITE,
    OperationKind.WRITE_NEW_FILE: CapabilityLevel.WRITE,
    OperationKind.EDIT_FILE: CapabilityLevel.EXECUTE,
    OperationKind.RUN_SCRIPT: CapabilityLevel.EXECUTE,
    OperationKind.RUN_COMMAND: CapabilityLevel.EXECUTE,
    OperationKind.DELETE_FILE: CapabilityLevel.CRITICAL,
    OperationKind.EDIT_CRITICAL: CapabilityLevel.CRITICAL,
    OperationKind.MUTATE_INFRA: CapabilityLevel.CRITICAL,
}


def required_capability(kind: OperationKind) -> CapabilityLevel:
    """Lookup the minimum capability required for this operation."""
    return _REQUIRED_CAP[kind]


# ---------------------------------------------------------------------------
# Risk tiers
# ---------------------------------------------------------------------------


class RiskTier(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        return _RISK_RANK[self]


_RISK_RANK = {
    RiskTier.NONE: 0,
    RiskTier.LOW: 1,
    RiskTier.MEDIUM: 2,
    RiskTier.HIGH: 3,
    RiskTier.CRITICAL: 4,
}


def coerce_risk(value: str | RiskTier | None) -> RiskTier:
    """Accept str or RiskTier, return RiskTier. Unknown → NONE."""
    if value is None:
        return RiskTier.NONE
    if isinstance(value, RiskTier):
        return value
    try:
        return RiskTier(value.lower())
    except (ValueError, AttributeError):
        return RiskTier.NONE


# ---------------------------------------------------------------------------
# Capability profile — what one agent is allowed to do
# ---------------------------------------------------------------------------


@dataclass
class CapabilityProfile:
    """An agent's explicit capability declaration.

    max_capability       — highest capability the agent can request
    max_auto_risk        — highest risk tier runnable without approval
    allowed_operations   — optional allow-list; empty = all allowed
                           at or below max_capability
    denied_operations    — explicit deny-list; always wins
    require_approval_above — risk tier at which approval is required
    """

    name: str
    max_capability: CapabilityLevel = CapabilityLevel.READ
    max_auto_risk: RiskTier = RiskTier.LOW
    allowed_operations: set[OperationKind] = field(default_factory=set)
    denied_operations: set[OperationKind] = field(default_factory=set)
    require_approval_above: RiskTier = RiskTier.MEDIUM

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "max_capability": self.max_capability.value,
            "max_auto_risk": self.max_auto_risk.value,
            "allowed_operations": sorted(o.value for o in self.allowed_operations),
            "denied_operations": sorted(o.value for o in self.denied_operations),
            "require_approval_above": self.require_approval_above.value,
        }


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------


@dataclass
class CapabilityDecision:
    """Result of a capability enforcement check."""

    allowed: bool
    reason: str
    needs_approval: bool = False
    required_capability: CapabilityLevel | None = None
    effective_risk: RiskTier = RiskTier.NONE


# ---------------------------------------------------------------------------
# Enforcer
# ---------------------------------------------------------------------------


class CapabilityEnforcer:
    """Pure policy object. may() is the single answer-everything method.

    Never mutates anything and never blocks. Returns a CapabilityDecision;
    the harness or action system acts on it.
    """

    def may(
        self,
        profile: CapabilityProfile,
        kind: OperationKind,
        risk: str | RiskTier | None = None,
    ) -> CapabilityDecision:
        if kind in profile.denied_operations:
            return CapabilityDecision(
                allowed=False,
                reason=f"{profile.name} explicitly denies {kind.value}",
                required_capability=required_capability(kind),
            )

        if profile.allowed_operations and kind not in profile.allowed_operations:
            return CapabilityDecision(
                allowed=False,
                reason=f"{profile.name} allow-list does not include {kind.value}",
                required_capability=required_capability(kind),
            )

        need = required_capability(kind)
        if not cap_implies(profile.max_capability, need):
            return CapabilityDecision(
                allowed=False,
                reason=(
                    f"{profile.name} has max_capability={profile.max_capability.value} "
                    f"but {kind.value} requires {need.value}"
                ),
                required_capability=need,
            )

        r = coerce_risk(risk)
        decision = CapabilityDecision(
            allowed=True,
            reason=f"{profile.name} may {kind.value} at risk={r.value}",
            required_capability=need,
            effective_risk=r,
        )
        if (
            r.rank > profile.max_auto_risk.rank
            or r.rank > profile.require_approval_above.rank
        ):
            decision.needs_approval = True
            decision.reason += " (approval required)"
        return decision

    def enforce(
        self,
        profile: CapabilityProfile,
        kind: OperationKind,
        risk: str | RiskTier | None = None,
    ) -> CapabilityDecision:
        """Raise PermissionError if denied, else return the CapabilityDecision."""
        d = self.may(profile, kind, risk)
        if not d.allowed:
            raise PermissionError(d.reason)
        return d


# ---------------------------------------------------------------------------
# Profile registry — configurable, not hardcoded
# ---------------------------------------------------------------------------


class ProfileRegistry:
    """Registry of agent capability profiles.

    Provides default profiles for common agent archetypes.
    Instances can register additional profiles or override defaults.
    """

    def __init__(self) -> None:
        self._profiles: dict[str, CapabilityProfile] = {}

    def register(self, profile: CapabilityProfile) -> None:
        self._profiles[profile.name] = profile

    def get(self, name: str) -> CapabilityProfile:
        p = self._profiles.get(name)
        if p is None:
            raise KeyError(
                f"no capability profile for agent {name!r} — "
                f"register one via ProfileRegistry.register()"
            )
        return p

    def list_profiles(self) -> list[str]:
        return sorted(self._profiles.keys())

    @property
    def size(self) -> int:
        return len(self._profiles)


def _make_profile(
    name: str,
    cap: CapabilityLevel,
    risk: RiskTier,
    *,
    allow: Iterable[OperationKind] = (),
    deny: Iterable[OperationKind] = (),
    approval_above: RiskTier = RiskTier.MEDIUM,
) -> CapabilityProfile:
    return CapabilityProfile(
        name=name,
        max_capability=cap,
        max_auto_risk=risk,
        allowed_operations=set(allow),
        denied_operations=set(deny),
        require_approval_above=approval_above,
    )


def default_registry() -> ProfileRegistry:
    """Create a registry with archetype profiles.

    These are generic agent archetypes, not instance-specific agents.
    Override or extend for your deployment.
    """
    reg = ProfileRegistry()

    reg.register(
        _make_profile(
            "reader",
            CapabilityLevel.READ,
            RiskTier.LOW,
            allow={
                OperationKind.READ_DATA,
                OperationKind.READ_MEMORY,
                OperationKind.READ_SUMMARY,
                OperationKind.CALL_LLM,
            },
        )
    )

    reg.register(
        _make_profile(
            "writer",
            CapabilityLevel.WRITE,
            RiskTier.LOW,
            allow={
                OperationKind.READ_DATA,
                OperationKind.READ_MEMORY,
                OperationKind.READ_SUMMARY,
                OperationKind.CALL_LLM,
                OperationKind.WRITE_MEMORY,
                OperationKind.WRITE_LOG,
                OperationKind.WRITE_NEW_FILE,
            },
        )
    )

    reg.register(
        _make_profile(
            "executor",
            CapabilityLevel.EXECUTE,
            RiskTier.MEDIUM,
            allow={
                OperationKind.READ_DATA,
                OperationKind.READ_MEMORY,
                OperationKind.READ_SUMMARY,
                OperationKind.CALL_LLM,
                OperationKind.WRITE_MEMORY,
                OperationKind.WRITE_LOG,
                OperationKind.WRITE_NEW_FILE,
                OperationKind.EDIT_FILE,
                OperationKind.RUN_SCRIPT,
                OperationKind.RUN_COMMAND,
            },
            deny={
                OperationKind.EDIT_CRITICAL,
                OperationKind.DELETE_FILE,
                OperationKind.MUTATE_INFRA,
            },
            approval_above=RiskTier.MEDIUM,
        )
    )

    reg.register(
        _make_profile(
            "observer",
            CapabilityLevel.READ,
            RiskTier.LOW,
            allow={
                OperationKind.READ_DATA,
                OperationKind.READ_MEMORY,
                OperationKind.READ_SUMMARY,
                OperationKind.WRITE_LOG,
            },
        )
    )

    reg.register(
        _make_profile(
            "advisor",
            CapabilityLevel.READ,
            RiskTier.MEDIUM,
            allow={
                OperationKind.READ_DATA,
                OperationKind.READ_MEMORY,
                OperationKind.READ_SUMMARY,
                OperationKind.CALL_LLM,
            },
            deny={
                OperationKind.WRITE_MEMORY,
                OperationKind.WRITE_LOG,
                OperationKind.WRITE_NEW_FILE,
                OperationKind.EDIT_FILE,
                OperationKind.RUN_SCRIPT,
                OperationKind.RUN_COMMAND,
                OperationKind.DELETE_FILE,
                OperationKind.EDIT_CRITICAL,
                OperationKind.MUTATE_INFRA,
            },
        )
    )

    return reg


def operation_for_action_type(
    action_type: str,
    *,
    is_critical: bool = False,
) -> OperationKind:
    """Translate an action type string into an OperationKind.

    Bridge function for action systems that use string-based action types.
    """
    at = action_type.lower()
    if at in ("query_graph", "read_graph", "graph_search"):
        return OperationKind.READ_GRAPH
    if at in ("query", "read", "read_data"):
        return OperationKind.READ_DATA
    if at in ("write_file", "create_file"):
        return OperationKind.WRITE_NEW_FILE
    if at == "edit_file":
        return OperationKind.EDIT_CRITICAL if is_critical else OperationKind.EDIT_FILE
    if at == "delete_file":
        return OperationKind.DELETE_FILE
    if at == "run_script":
        return OperationKind.RUN_SCRIPT
    if at == "run_command":
        return OperationKind.RUN_COMMAND
    return OperationKind.EDIT_FILE


__all__ = [
    "CapabilityDecision",
    "CapabilityEnforcer",
    "CapabilityLevel",
    "CapabilityProfile",
    "OperationKind",
    "ProfileRegistry",
    "RiskTier",
    "cap_implies",
    "coerce_risk",
    "default_registry",
    "operation_for_action_type",
    "required_capability",
]
