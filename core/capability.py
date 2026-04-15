"""
capability.py — Permission + risk matrix for the unified EOS AI OS.

Every agent carries a CapabilityProfile describing which operations it can
perform. Every step or action is mapped to a required Capability + RiskLevel.
The CapabilityEnforcer answers one question: `may(agent, operation) → bool`.

This module is intentionally pure. No I/O, no LLM calls, no imports from
eos_ai.*. It is safe to import from anywhere in the stack, including the
harness and the action system.

Usage:
    from core.capability import (
        Capability, CapabilityProfile, CapabilityEnforcer,
        OperationKind, DEFAULT_PROFILES,
    )

    enforcer = CapabilityEnforcer()
    allowed, reason = enforcer.may(
        profile=DEFAULT_PROFILES["researcher"],
        kind=OperationKind.READ_GRAPH,
        risk="low",
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


# ---------------------------------------------------------------------------
# Capability levels
# ---------------------------------------------------------------------------


class Capability(str, Enum):
    """Four-level capability lattice. Each level implies all lower levels."""

    READ = "read"  # read graph, memory, summaries
    WRITE = "write"  # write memory, create new files
    EXECUTE = "execute"  # run scripts, commands, edit existing files
    CRITICAL = "critical"  # edit critical hubs, delete files, infra changes

    @property
    def rank(self) -> int:
        return _CAP_RANK[self]


_CAP_RANK = {
    Capability.READ: 0,
    Capability.WRITE: 1,
    Capability.EXECUTE: 2,
    Capability.CRITICAL: 3,
}


def cap_implies(have: Capability, need: Capability) -> bool:
    """A higher-rank capability implies all lower ones."""
    return have.rank >= need.rank


# ---------------------------------------------------------------------------
# Operation kinds — every thing an agent can "do"
# ---------------------------------------------------------------------------


class OperationKind(str, Enum):
    """The cross-product of (what kind of work, which layer).

    Kept small and explicit. Adding a kind = adding a real boundary, not a
    shade of an existing one.
    """

    # read-only
    READ_GRAPH = "read_graph"
    READ_MEMORY = "read_memory"
    READ_SUMMARY = "read_summary"
    # write, no side effects outside EOS data
    WRITE_MEMORY = "write_memory"
    WRITE_LOG = "write_log"
    WRITE_NEW_FILE = "write_new_file"
    # execute — real side effects
    EDIT_FILE = "edit_file"
    RUN_SCRIPT = "run_script"
    RUN_COMMAND = "run_command"
    CALL_LLM = "call_llm"  # LLM call itself is cheap but counts as work
    # critical — irreversible or high-blast
    DELETE_FILE = "delete_file"
    EDIT_CRITICAL_HUB = "edit_critical_hub"
    MUTATE_INFRA = "mutate_infra"


# Minimum capability required to perform an operation.
_REQUIRED_CAP: dict[OperationKind, Capability] = {
    OperationKind.READ_GRAPH: Capability.READ,
    OperationKind.READ_MEMORY: Capability.READ,
    OperationKind.READ_SUMMARY: Capability.READ,
    OperationKind.CALL_LLM: Capability.READ,  # calling an LLM is not a side effect
    OperationKind.WRITE_MEMORY: Capability.WRITE,
    OperationKind.WRITE_LOG: Capability.WRITE,
    OperationKind.WRITE_NEW_FILE: Capability.WRITE,
    OperationKind.EDIT_FILE: Capability.EXECUTE,
    OperationKind.RUN_SCRIPT: Capability.EXECUTE,
    OperationKind.RUN_COMMAND: Capability.EXECUTE,
    OperationKind.DELETE_FILE: Capability.CRITICAL,
    OperationKind.EDIT_CRITICAL_HUB: Capability.CRITICAL,
    OperationKind.MUTATE_INFRA: Capability.CRITICAL,
}


def required_capability(kind: OperationKind) -> Capability:
    """Lookup the minimum capability required for this operation."""
    return _REQUIRED_CAP[kind]


# ---------------------------------------------------------------------------
# Risk tiers — mirrors action_system.RiskLevel but without importing it
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

    max_capability      — highest capability the agent can request
    max_auto_risk       — highest risk tier the agent may run without approval
    allowed_operations  — optional allow-list; empty set means "all allowed
                          at or below max_capability"
    denied_operations   — explicit deny-list; always wins
    require_approval    — risk tier at which approval is required even if the
                          agent's max_auto_risk would otherwise allow it
    """

    name: str
    max_capability: Capability = Capability.READ
    max_auto_risk: RiskTier = RiskTier.LOW
    allowed_operations: set[OperationKind] = field(default_factory=set)
    denied_operations: set[OperationKind] = field(default_factory=set)
    require_approval_above: RiskTier = RiskTier.MEDIUM

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "max_capability": self.max_capability.value,
            "max_auto_risk": self.max_auto_risk.value,
            "allowed_operations": sorted(o.value for o in self.allowed_operations),
            "denied_operations": sorted(o.value for o in self.denied_operations),
            "require_approval_above": self.require_approval_above.value,
        }


# ---------------------------------------------------------------------------
# Enforcer
# ---------------------------------------------------------------------------


@dataclass
class Decision:
    allowed: bool
    reason: str
    needs_approval: bool = False
    required_capability: Capability | None = None
    effective_risk: RiskTier = RiskTier.NONE


class CapabilityEnforcer:
    """Pure policy object. `may(...)` is the single answer-everything method.

    The enforcer never mutates anything and never blocks. Its only job is
    to return a Decision; the harness or action system acts on it.
    """

    def may(
        self,
        profile: CapabilityProfile,
        kind: OperationKind,
        risk: str | RiskTier | None = None,
    ) -> Decision:
        # 1. Explicit deny always wins.
        if kind in profile.denied_operations:
            return Decision(
                allowed=False,
                reason=f"{profile.name} explicitly denies {kind.value}",
                required_capability=required_capability(kind),
            )

        # 2. If allow-list is non-empty, the operation must appear in it.
        if profile.allowed_operations and kind not in profile.allowed_operations:
            return Decision(
                allowed=False,
                reason=f"{profile.name} allow-list does not include {kind.value}",
                required_capability=required_capability(kind),
            )

        # 3. Capability level must be sufficient.
        need = required_capability(kind)
        if not cap_implies(profile.max_capability, need):
            return Decision(
                allowed=False,
                reason=(
                    f"{profile.name} has max_capability={profile.max_capability.value} "
                    f"but {kind.value} requires {need.value}"
                ),
                required_capability=need,
            )

        # 4. Risk gate.
        r = coerce_risk(risk)
        effective = Decision(
            allowed=True,
            reason=f"{profile.name} may {kind.value} at risk={r.value}",
            required_capability=need,
            effective_risk=r,
        )
        # require_approval_above is inclusive of the boundary tier itself;
        # max_auto_risk is inclusive of the tier itself.
        if (
            r.rank > profile.max_auto_risk.rank
            or r.rank > profile.require_approval_above.rank
        ):
            effective.needs_approval = True
            effective.reason += " (approval required)"
        return effective

    def enforce(
        self,
        profile: CapabilityProfile,
        kind: OperationKind,
        risk: str | RiskTier | None = None,
    ) -> Decision:
        """Raise PermissionError if denied, else return the Decision."""
        d = self.may(profile, kind, risk)
        if not d.allowed:
            raise PermissionError(d.reason)
        return d


# ---------------------------------------------------------------------------
# Default profiles — matches the WorkflowEngine agent roster
# ---------------------------------------------------------------------------


def _profile(
    name: str,
    cap: Capability,
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


DEFAULT_PROFILES: dict[str, CapabilityProfile] = {
    # Researcher: read everything, call LLMs, never mutate.
    "researcher": _profile(
        "researcher",
        Capability.READ,
        RiskTier.LOW,
        allow={
            OperationKind.READ_GRAPH,
            OperationKind.READ_MEMORY,
            OperationKind.READ_SUMMARY,
            OperationKind.CALL_LLM,
        },
    ),
    # Writer: READ + LLM + write memory (for remembered outputs).
    "writer": _profile(
        "writer",
        Capability.WRITE,
        RiskTier.LOW,
        allow={
            OperationKind.READ_GRAPH,
            OperationKind.READ_MEMORY,
            OperationKind.READ_SUMMARY,
            OperationKind.CALL_LLM,
            OperationKind.WRITE_MEMORY,
            OperationKind.WRITE_LOG,
            OperationKind.WRITE_NEW_FILE,
        },
    ),
    # Executor: can run scripts, edit files, but critical hubs need approval.
    "executor": _profile(
        "executor",
        Capability.EXECUTE,
        RiskTier.MEDIUM,
        allow={
            OperationKind.READ_GRAPH,
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
            OperationKind.EDIT_CRITICAL_HUB,
            OperationKind.DELETE_FILE,
            OperationKind.MUTATE_INFRA,
        },
        approval_above=RiskTier.MEDIUM,
    ),
    # Generalist: mid-range. READ + LLM + WRITE_MEMORY only.
    "generalist": _profile(
        "generalist",
        Capability.WRITE,
        RiskTier.LOW,
        allow={
            OperationKind.READ_GRAPH,
            OperationKind.READ_MEMORY,
            OperationKind.READ_SUMMARY,
            OperationKind.CALL_LLM,
            OperationKind.WRITE_MEMORY,
            OperationKind.WRITE_LOG,
        },
    ),
    # CEO: reads everything, decides, strategic LLM, no mutation.
    "ceo": _profile(
        "ceo",
        Capability.READ,
        RiskTier.MEDIUM,
        allow={
            OperationKind.READ_GRAPH,
            OperationKind.READ_MEMORY,
            OperationKind.READ_SUMMARY,
            OperationKind.CALL_LLM,
        },
    ),
    # System agents — persistent agents need mid-range capability.
    "observer": _profile(
        "observer",
        Capability.READ,
        RiskTier.LOW,
        allow={
            OperationKind.READ_GRAPH,
            OperationKind.READ_MEMORY,
            OperationKind.READ_SUMMARY,
            OperationKind.WRITE_LOG,
        },
    ),
    "healer": _profile(
        "healer",
        Capability.EXECUTE,
        RiskTier.MEDIUM,
        allow={
            OperationKind.READ_GRAPH,
            OperationKind.READ_MEMORY,
            OperationKind.READ_SUMMARY,
            OperationKind.CALL_LLM,
            OperationKind.WRITE_MEMORY,
            OperationKind.WRITE_LOG,
            OperationKind.EDIT_FILE,
            OperationKind.RUN_SCRIPT,
        },
        deny={
            OperationKind.EDIT_CRITICAL_HUB,
            OperationKind.DELETE_FILE,
            OperationKind.MUTATE_INFRA,
        },
    ),
    "librarian": _profile(
        "librarian",
        Capability.WRITE,
        RiskTier.LOW,
        allow={
            OperationKind.READ_GRAPH,
            OperationKind.READ_MEMORY,
            OperationKind.READ_SUMMARY,
            OperationKind.WRITE_MEMORY,
            OperationKind.WRITE_LOG,
            OperationKind.WRITE_NEW_FILE,
        },
    ),
    # Advisor: READ-only + LLM. Never executes, never writes, never mutates.
    "advisor": _profile(
        "advisor",
        Capability.READ,
        RiskTier.MEDIUM,
        allow={
            OperationKind.READ_GRAPH,
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
            OperationKind.EDIT_CRITICAL_HUB,
            OperationKind.MUTATE_INFRA,
        },
    ),
}


def get_profile(name: str) -> CapabilityProfile:
    """Lookup with a clear error. Never auto-creates profiles."""
    p = DEFAULT_PROFILES.get(name)
    if p is None:
        raise KeyError(
            f"no capability profile for agent {name!r} — "
            f"register one in core.capability.DEFAULT_PROFILES"
        )
    return p


# ---------------------------------------------------------------------------
# Action-type bridge — maps scripts.action_system.ActionType → OperationKind
# ---------------------------------------------------------------------------


def operation_for_action_type(
    action_type: str, *, is_critical_hub: bool = False
) -> OperationKind:
    """Translate an ActionSystem action_type string into an OperationKind.

    This lives here (not in action_system) so action_system can stay free of
    capability imports — the harness is the bridge.
    """
    at = action_type.lower()
    if at == "query_graph":
        return OperationKind.READ_GRAPH
    if at == "write_file":
        return OperationKind.WRITE_NEW_FILE
    if at == "edit_file":
        return (
            OperationKind.EDIT_CRITICAL_HUB
            if is_critical_hub
            else OperationKind.EDIT_FILE
        )
    if at == "delete_file":
        return OperationKind.DELETE_FILE
    if at == "run_script":
        return OperationKind.RUN_SCRIPT
    if at == "run_command":
        return OperationKind.RUN_COMMAND
    # Unknown → treat as EDIT_FILE (middle of the road) so the enforcer denies
    # it unless the agent has EXECUTE. Never default to READ for unknowns.
    return OperationKind.EDIT_FILE


__all__ = [
    "Capability",
    "CapabilityEnforcer",
    "CapabilityProfile",
    "DEFAULT_PROFILES",
    "Decision",
    "OperationKind",
    "RiskTier",
    "cap_implies",
    "coerce_risk",
    "get_profile",
    "operation_for_action_type",
    "required_capability",
]
