"""
core.security — Enterprise security layer for the EOS AI Operating System.

Six composable subsystems, one facade:

    identity        — users, roles, tokens                 identity.py
    rbac            — role → capabilities + approval auth  rbac.py
    approval        — approval queue + request lifecycle   approval.py
    environments    — env selection + isolation contract   environments.py
    audit           — append-only, hash-chained audit log  audit.py
    execution       — restricted execution contexts        execution.py

    SecurityContext — single entry-point that composes all  context.py
                      six into `authorize_action(...)`.

Integration points (see ARCHITECTURE_FINAL.md §6):

    scripts/action_system.ActionSystem.execute(...)
        → SecurityContext.authorize_action(...)
            → identity.authenticate
            → rbac.check
            → approval.require_if_needed
            → audit.record
            → execution.restricted_context

All state lives under /opt/OS/data/security/. Every subsystem is
independent — you can import `audit` without touching identity, or
run `approval` as a CLI without touching RBAC. The facade just makes
"check everything at once" ergonomic.

Usage (high-level):

    from core.security import SecurityContext

    ctx = SecurityContext.default()
    token = ctx.identity.authenticate("operator-1", "alpha-key")
    decision = ctx.authorize_action(
        token=token,
        action_type="edit_file",
        target="eos_ai/memory.py",
        risk="high",
        agent="executor",
    )
    if decision.status == "approved":
        ...                 # proceed
    elif decision.status == "pending":
        approval_id = decision.approval_id
    else:
        raise PermissionError(decision.reason)
"""

from __future__ import annotations

from .identity import (
    AuthError,
    IdentityStore,
    Token,
    User,
)
from .rbac import (
    DEFAULT_ROLES,
    RBACEngine,
    Role,
    RoleName,
)
from .approval import (
    ApprovalAction,
    ApprovalQueue,
    ApprovalRequest,
    ApprovalStatus,
)
from .environments import (
    EnvironmentPolicy,
    SecurityEnv,
    env_for_name,
)
from .audit import (
    AuditEvent,
    AuditLog,
)
from .execution import (
    ExecutionContext,
    RestrictedExecutor,
    restricted_context,
)
from .context import (
    AuthorizationDecision,
    SecurityContext,
)

__all__ = [
    # identity
    "AuthError",
    "IdentityStore",
    "Token",
    "User",
    # rbac
    "DEFAULT_ROLES",
    "RBACEngine",
    "Role",
    "RoleName",
    # approval
    "ApprovalAction",
    "ApprovalQueue",
    "ApprovalRequest",
    "ApprovalStatus",
    # environments
    "EnvironmentPolicy",
    "SecurityEnv",
    "env_for_name",
    # audit
    "AuditEvent",
    "AuditLog",
    # execution
    "ExecutionContext",
    "RestrictedExecutor",
    "restricted_context",
    # facade
    "AuthorizationDecision",
    "SecurityContext",
]
