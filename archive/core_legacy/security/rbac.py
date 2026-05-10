"""
rbac.py — Role-based access control on top of core.capability.

Design decision
---------------
`core.capability` already has `CapabilityProfile` + `CapabilityEnforcer`
for *agents*. RBAC here is for *users* (humans or external callers).
Rather than duplicate the enum machinery, we map each RoleName to:

    1. an allowed set of OperationKinds (same enum as capability.py)
    2. a max auto-risk tier
    3. an approval-authority level (highest risk they can sign off on)

The existing agent-capability profiles still exist and still run inside
the agent harness. This module exists to answer the question:

    "Is this authenticated user allowed to request/approve this action?"

Not the same as:

    "Is this agent's runtime allowed to call this tool?"

Both checks happen — user RBAC gates request intent, agent capability
gates tool dispatch.

Roles
-----
    admin       — full authority, can approve CRITICAL, max auto-risk CRITICAL
    operator    — runs day-to-day, approves up to HIGH, max auto-risk MEDIUM
    viewer      — read-only, no approval authority
    agent       — execution role for autonomous agents; approves nothing,
                  auto-risk LOW. (Separate from the agent-harness capability
                  profiles — those are per-agent; this is the baseline any
                  agent gets when authenticated as an OS principal.)

The role layer is deliberately simple. If you need fine-grained policies,
extend `allowed_operations` on a Role and re-register it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

from core.capability import (
    Capability,
    OperationKind,
    RiskTier,
    cap_implies,
    coerce_risk,
    required_capability,
)


class RoleName(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"
    AGENT = "agent"


@dataclass
class Role:
    """A named bundle of permissions.

    Fields
    ------
    name                  — one of RoleName
    max_capability        — highest capability level operations in this role can use
    max_auto_risk         — highest risk tier that runs without approval
    approval_authority    — highest risk tier this role can approve on
                            behalf of others (None = cannot approve)
    allowed_operations    — optional allow-list of OperationKinds; empty
                            means "all operations at or below max_capability"
    denied_operations     — explicit deny-list; always wins
    """

    name: RoleName
    max_capability: Capability
    max_auto_risk: RiskTier
    approval_authority: RiskTier | None
    allowed_operations: set[OperationKind] = field(default_factory=set)
    denied_operations: set[OperationKind] = field(default_factory=set)

    def as_dict(self) -> dict:
        return {
            "name": self.name.value,
            "max_capability": self.max_capability.value,
            "max_auto_risk": self.max_auto_risk.value,
            "approval_authority": (
                self.approval_authority.value if self.approval_authority else None
            ),
            "allowed_operations": sorted(o.value for o in self.allowed_operations),
            "denied_operations": sorted(o.value for o in self.denied_operations),
        }


# ─── Default roles ──────────────────────────────────────────────────────────


def _role(
    name: RoleName,
    cap: Capability,
    auto_risk: RiskTier,
    authority: RiskTier | None,
    *,
    allow: Iterable[OperationKind] = (),
    deny: Iterable[OperationKind] = (),
) -> Role:
    return Role(
        name=name,
        max_capability=cap,
        max_auto_risk=auto_risk,
        approval_authority=authority,
        allowed_operations=set(allow),
        denied_operations=set(deny),
    )


_ALL_OPS = set(OperationKind)
_READ_OPS = {
    OperationKind.READ_GRAPH,
    OperationKind.READ_MEMORY,
    OperationKind.READ_SUMMARY,
    OperationKind.CALL_LLM,
}
_WRITE_OPS = _READ_OPS | {
    OperationKind.WRITE_MEMORY,
    OperationKind.WRITE_LOG,
    OperationKind.WRITE_NEW_FILE,
}
_OPERATOR_OPS = _WRITE_OPS | {
    OperationKind.EDIT_FILE,
    OperationKind.RUN_SCRIPT,
    OperationKind.RUN_COMMAND,
}


DEFAULT_ROLES: dict[RoleName, Role] = {
    RoleName.ADMIN: _role(
        RoleName.ADMIN,
        Capability.CRITICAL,
        RiskTier.CRITICAL,
        RiskTier.CRITICAL,
        allow=_ALL_OPS,
    ),
    RoleName.OPERATOR: _role(
        RoleName.OPERATOR,
        Capability.EXECUTE,
        RiskTier.MEDIUM,
        RiskTier.HIGH,
        allow=_OPERATOR_OPS,
        deny={
            OperationKind.DELETE_FILE,
            OperationKind.EDIT_CRITICAL_HUB,
            OperationKind.MUTATE_INFRA,
        },
    ),
    RoleName.VIEWER: _role(
        RoleName.VIEWER,
        Capability.READ,
        RiskTier.NONE,
        None,  # cannot approve anything
        allow=_READ_OPS,
    ),
    RoleName.AGENT: _role(
        RoleName.AGENT,
        Capability.EXECUTE,
        RiskTier.LOW,
        None,  # agents cannot self-approve
        allow=_OPERATOR_OPS,
        deny={
            OperationKind.DELETE_FILE,
            OperationKind.EDIT_CRITICAL_HUB,
            OperationKind.MUTATE_INFRA,
        },
    ),
}


# ─── Engine ─────────────────────────────────────────────────────────────────


@dataclass
class RBACCheck:
    """Outcome of an RBAC check — mirrors core.capability.Decision."""

    allowed: bool
    reason: str
    needs_approval: bool = False
    role: RoleName | None = None
    required_capability: Capability | None = None


class RBACEngine:
    """Policy object for role → operation lookups.

    The engine holds a dict of roles by name and answers two questions:
        check(role, op, risk)      — can this role request this operation?
        can_approve(role, risk)    — can this role approve this risk tier?

    Roles can be registered or overridden via `register(role)`.
    """

    def __init__(self, roles: dict[RoleName, Role] | None = None) -> None:
        self._roles: dict[RoleName, Role] = dict(roles or DEFAULT_ROLES)

    def register(self, role: Role) -> None:
        self._roles[role.name] = role

    def get(self, name: str | RoleName) -> Role:
        key = name if isinstance(name, RoleName) else RoleName(name)
        if key not in self._roles:
            raise KeyError(f"unknown role: {name}")
        return self._roles[key]

    def list_roles(self) -> list[Role]:
        return sorted(self._roles.values(), key=lambda r: r.name.value)

    def check(
        self,
        role_name: str | RoleName,
        op: OperationKind,
        risk: str | RiskTier | None = None,
    ) -> RBACCheck:
        """Evaluate whether `role_name` may request `op` at `risk`.

        Returns RBACCheck. Never raises; callers decide what to do.
        """
        try:
            role = self.get(role_name)
        except KeyError:
            return RBACCheck(
                allowed=False,
                reason=f"unknown role: {role_name}",
            )

        if op in role.denied_operations:
            return RBACCheck(
                allowed=False,
                reason=f"role {role.name.value} explicitly denies {op.value}",
                role=role.name,
                required_capability=required_capability(op),
            )

        if role.allowed_operations and op not in role.allowed_operations:
            return RBACCheck(
                allowed=False,
                reason=f"role {role.name.value} not permitted for {op.value}",
                role=role.name,
                required_capability=required_capability(op),
            )

        need = required_capability(op)
        if not cap_implies(role.max_capability, need):
            return RBACCheck(
                allowed=False,
                reason=(
                    f"role {role.name.value} has max_capability="
                    f"{role.max_capability.value} but {op.value} requires "
                    f"{need.value}"
                ),
                role=role.name,
                required_capability=need,
            )

        r = coerce_risk(risk)
        needs_approval = r.rank > role.max_auto_risk.rank
        return RBACCheck(
            allowed=True,
            reason=(
                f"role {role.name.value} may {op.value} at risk={r.value}"
                + (" (approval required)" if needs_approval else "")
            ),
            needs_approval=needs_approval,
            role=role.name,
            required_capability=need,
        )

    def can_approve(
        self,
        role_name: str | RoleName,
        risk: str | RiskTier | None,
    ) -> bool:
        """True if this role's approval authority covers `risk`."""
        try:
            role = self.get(role_name)
        except KeyError:
            return False
        if role.approval_authority is None:
            return False
        r = coerce_risk(risk)
        return role.approval_authority.rank >= r.rank


__all__ = [
    "DEFAULT_ROLES",
    "RBACCheck",
    "RBACEngine",
    "Role",
    "RoleName",
]
