"""
context.py — SecurityContext facade.

Single entry point that composes identity + RBAC + approval +
environment-policy + audit into one call:

    AuthorizationDecision = ctx.authorize_action(
        token=...,
        action_type="edit_file",
        target="eos_ai/memory.py",
        operation=OperationKind.EDIT_FILE,
        risk="high",
        agent="executor",
    )

The caller (ActionSystem) inspects `decision.status`:

    "approved" → proceed immediately
    "pending"  → an approval request exists; caller waits or returns
    "denied"   → raise / log / abort

Every call — regardless of outcome — writes an AuditEvent.

Wiring decisions
----------------
- The context does NOT instantiate an ActionSystem or a CoreEnvironment
  on its own. It takes whatever is passed. That keeps imports clean
  and avoids a circular dep (security → action_system → security).
- `SecurityContext.default()` builds a prod-mode context with default
  stores. Tests can instantiate with specific paths.
- The facade deliberately holds references to each subsystem as public
  attributes so callers can reach past the facade when they need to
  (`ctx.identity.create_user(...)`, `ctx.queue.list_pending()`, etc).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from core.capability import OperationKind, RiskTier, coerce_risk

from .approval import (
    ApprovalError,
    ApprovalQueue,
    ApprovalRequest,
    ApprovalStatus,
)
from .audit import AuditEvent, AuditLog
from .environments import SecurityEnv, env_for_name, wrap_environment
from .execution import ExecutionContext
from .identity import AuthError, IdentityStore, Token
from .rbac import RBACEngine, RoleName

DecisionStatus = Literal["approved", "pending", "denied"]


@dataclass
class AuthorizationDecision:
    """Outcome of SecurityContext.authorize_action.

    Fields
    ------
    status            — "approved" | "pending" | "denied"
    reason            — human-readable explanation
    token             — the verified token (or None if auth failed)
    role              — the user's role
    operation         — the OperationKind evaluated
    risk              — the RiskTier evaluated
    environment       — which SecurityEnv the call ran against
    needs_approval    — whether RBAC or env policy flagged the action
    approval_id       — set when status == "pending"
    audit_event_id    — the audit row this decision produced
    """

    status: DecisionStatus
    reason: str
    token: Token | None = None
    role: str = ""
    operation: str = ""
    risk: str = ""
    environment: str = ""
    needs_approval: bool = False
    approval_id: str = ""
    audit_event_id: str = ""
    approval_chain: list[dict] = field(default_factory=list)

    @property
    def is_approved(self) -> bool:
        return self.status == "approved"

    @property
    def is_pending(self) -> bool:
        return self.status == "pending"

    @property
    def is_denied(self) -> bool:
        return self.status == "denied"

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "reason": self.reason,
            "role": self.role,
            "operation": self.operation,
            "risk": self.risk,
            "environment": self.environment,
            "needs_approval": self.needs_approval,
            "approval_id": self.approval_id,
            "audit_event_id": self.audit_event_id,
            "approval_chain": list(self.approval_chain),
        }


# ─── Facade ─────────────────────────────────────────────────────────────────


class SecurityContext:
    """Composes the six security subsystems into one object.

    Typical use from ActionSystem:

        from core.security import SecurityContext
        from core.capability import OperationKind

        sec = SecurityContext.default()
        decision = sec.authorize_action(
            token=user_token,
            action_type="edit_file",
            target="eos_ai/memory.py",
            operation=OperationKind.EDIT_FILE,
            risk="high",
            agent="executor",
            reason="optimizer proposal #42",
        )

        if decision.is_approved:
            ...
        elif decision.is_pending:
            req = sec.queue.wait_for_decision(decision.approval_id, timeout=300)
            if req and req.status == ApprovalStatus.APPROVED:
                ...
        else:
            raise PermissionError(decision.reason)
    """

    def __init__(
        self,
        *,
        identity: IdentityStore,
        rbac: RBACEngine,
        queue: ApprovalQueue,
        audit: AuditLog,
        env: SecurityEnv,
    ) -> None:
        self.identity = identity
        self.rbac = rbac
        self.queue = queue
        self.audit = audit
        self.env = env

    # ─── Constructors ──────────────────────────────────────────────────────

    @classmethod
    def default(
        cls,
        *,
        environment: str = "prod",
        sandbox_name: str | None = None,
    ) -> "SecurityContext":
        """Build a SecurityContext against the standard data layout."""
        return cls(
            identity=IdentityStore(),
            rbac=RBACEngine(),
            queue=ApprovalQueue(),
            audit=AuditLog(),
            env=env_for_name(environment, sandbox_name=sandbox_name),
        )

    @classmethod
    def for_env(cls, env: SecurityEnv) -> "SecurityContext":
        """Build a context rooted at a specific SecurityEnv (useful for
        sandbox runs where logs go into the sandbox tree)."""
        log_dir = Path(str(env.env.log_dir))
        state_dir = Path(str(env.env.state_dir))
        return cls(
            identity=IdentityStore(
                users_path=state_dir / "users.jsonl",
                secret_path=state_dir / "secret.key",
                revocations_path=state_dir / "revocations.jsonl",
            ),
            rbac=RBACEngine(),
            queue=ApprovalQueue(approvals_dir=state_dir / "approvals"),
            audit=AuditLog(path=log_dir / "security_audit.jsonl"),
            env=env,
        )

    # ─── Token lookup ──────────────────────────────────────────────────────

    def verify_token(self, token: str | Token | None) -> Token | None:
        if token is None:
            return None
        if isinstance(token, Token):
            return token if not token.is_expired else None
        try:
            return self.identity.verify(token)
        except AuthError:
            return None

    # ─── Core authorization path ───────────────────────────────────────────

    def authorize_action(
        self,
        *,
        token: str | Token | None,
        action_type: str,
        target: str,
        operation: OperationKind,
        risk: str | RiskTier,
        agent: str = "",
        reason: str = "",
        metadata: dict | None = None,
        approval_ttl_seconds: int | None = 3600,
        wait_for_approval: float = 0.0,
    ) -> AuthorizationDecision:
        """Run the full authorization pipeline.

        Steps
        -----
        1. Verify the token (or fail with "denied" + audit row).
        2. Ask RBAC whether this role may perform this op at this risk.
        3. Ask the environment policy whether this risk needs approval.
        4. If approval needed → create a request, optionally wait.
        5. Write the audit row (chained) and return the decision.

        `wait_for_approval` > 0 blocks up to that many seconds waiting
        for a human decision on the pending request. Default 0 =
        return a pending decision immediately.
        """
        risk_tier = coerce_risk(risk)
        risk_str = risk_tier.value
        op_str = operation.value
        env_label = self.env.label

        # 1) Authenticate
        verified = self.verify_token(token)
        if verified is None:
            return self._deny_and_audit(
                reason="authentication failed or token expired",
                action=action_type,
                target=target,
                operation=op_str,
                risk=risk_str,
                agent=agent,
                metadata=metadata,
            )

        # 2) RBAC
        rbac_check = self.rbac.check(verified.role, operation, risk=risk_tier)
        if not rbac_check.allowed:
            return self._deny_and_audit(
                reason=rbac_check.reason,
                action=action_type,
                target=target,
                operation=op_str,
                risk=risk_str,
                agent=agent,
                user=verified.user_id,
                role=verified.role,
                token=verified,
                metadata=metadata,
            )

        # 3) Env policy — hard block overrides approvals
        if self.env.blocks(risk_tier):
            return self._deny_and_audit(
                reason=(
                    f"environment {env_label} blocks risk={risk_str} "
                    f"(allow_critical=False)"
                ),
                action=action_type,
                target=target,
                operation=op_str,
                risk=risk_str,
                agent=agent,
                user=verified.user_id,
                role=verified.role,
                token=verified,
                metadata=metadata,
            )

        needs_approval = rbac_check.needs_approval or self.env.needs_approval(risk_tier)

        # 4) Approval path
        if needs_approval:
            req = self.queue.create_request(
                requester=verified.user_id,
                requester_role=verified.role,
                action_type=action_type,
                target=target,
                operation=op_str,
                risk=risk_str,
                reason=reason,
                agent=agent,
                environment=env_label,
                ttl_seconds=approval_ttl_seconds,
                metadata=metadata or {},
            )

            if wait_for_approval > 0:
                decided = self.queue.wait_for_decision(
                    req.request_id,
                    timeout=wait_for_approval,
                )
                if decided and decided.status == ApprovalStatus.APPROVED:
                    return self._approve_and_audit(
                        verified,
                        action=action_type,
                        target=target,
                        operation=op_str,
                        risk=risk_str,
                        agent=agent,
                        reason=f"approved via request {req.request_id}",
                        approval_chain=[_chain_entry(req, decided)],
                        metadata=metadata,
                    )
                if decided and decided.status in (
                    ApprovalStatus.REJECTED,
                    ApprovalStatus.EXPIRED,
                    ApprovalStatus.CANCELLED,
                ):
                    return self._deny_and_audit(
                        reason=(
                            f"approval request {req.request_id} "
                            f"{decided.status.value}: {decided.decision_reason}"
                        ),
                        action=action_type,
                        target=target,
                        operation=op_str,
                        risk=risk_str,
                        agent=agent,
                        user=verified.user_id,
                        role=verified.role,
                        token=verified,
                        approval_chain=[_chain_entry(req, decided)],
                        metadata=metadata,
                    )
                # Timeout without decision → return pending
            return self._pending_and_audit(
                verified,
                action=action_type,
                target=target,
                operation=op_str,
                risk=risk_str,
                agent=agent,
                request=req,
                metadata=metadata,
            )

        # 5) Auto-approved
        return self._approve_and_audit(
            verified,
            action=action_type,
            target=target,
            operation=op_str,
            risk=risk_str,
            agent=agent,
            reason=rbac_check.reason,
            metadata=metadata,
        )

    # ─── Approval actions (operator-facing) ────────────────────────────────

    def approve(
        self,
        *,
        approver_token: str | Token,
        request_id: str,
        reason: str = "",
    ) -> ApprovalRequest:
        """Approve a pending request. Operator calls this.

        The approver's role must have authority over the request's risk.
        Writes an audit row on success.
        """
        token = self.verify_token(approver_token)
        if token is None:
            raise AuthError("invalid approver token")

        req = self.queue.get(request_id)
        if req is None:
            raise ApprovalError(f"no such request: {request_id}")

        can = self.rbac.can_approve(token.role, req.risk)
        if not can:
            self.audit.record(
                user=token.user_id,
                role=token.role,
                action="approve_denied",
                target=req.target,
                operation=req.operation,
                risk=req.risk,
                environment=self.env.label,
                outcome="denied",
                reason=f"role {token.role} lacks approval authority for {req.risk}",
                metadata={"request_id": request_id},
            )
            raise ApprovalError(f"role {token.role} cannot approve risk={req.risk}")

        decided = self.queue.approve(
            request_id,
            approver=token.user_id,
            approver_role=token.role,
            can_approve_risk=True,
            reason=reason,
        )
        self.audit.record(
            user=token.user_id,
            role=token.role,
            action="approve",
            target=req.target,
            operation=req.operation,
            risk=req.risk,
            environment=self.env.label,
            outcome="allowed",
            reason=reason,
            approval_chain=[_chain_entry(req, decided)],
        )
        return decided

    def reject(
        self,
        *,
        approver_token: str | Token,
        request_id: str,
        reason: str = "",
    ) -> ApprovalRequest:
        """Reject a pending request. Any authenticated user may reject."""
        token = self.verify_token(approver_token)
        if token is None:
            raise AuthError("invalid approver token")
        req = self.queue.get(request_id)
        if req is None:
            raise ApprovalError(f"no such request: {request_id}")
        decided = self.queue.reject(
            request_id,
            approver=token.user_id,
            approver_role=token.role,
            reason=reason,
        )
        self.audit.record(
            user=token.user_id,
            role=token.role,
            action="reject",
            target=req.target,
            operation=req.operation,
            risk=req.risk,
            environment=self.env.label,
            outcome="denied",
            reason=reason,
            approval_chain=[_chain_entry(req, decided)],
        )
        return decided

    # ─── Execution context helper ──────────────────────────────────────────

    def build_execution_context(
        self,
        *,
        name: str = "scoped",
        extra_allowed_paths: list[str] | None = None,
        timeout_seconds: int | None = None,
    ) -> ExecutionContext:
        """Build an ExecutionContext pre-wired to the current env.

        The context allows reads/writes under the env's workspace and
        data_dir, and denies writes to the forbidden production paths
        when running inside an isolated env.
        """
        allowed = [str(self.env.env.workspace), str(self.env.env.data_dir)]
        if extra_allowed_paths:
            allowed.extend(extra_allowed_paths)
        denied: list[str] = []
        if self.env.is_isolated:
            from core.environment import FORBIDDEN_WRITE_PREFIXES

            denied = list(FORBIDDEN_WRITE_PREFIXES)
        return ExecutionContext(
            name=name,
            allowed_paths=allowed,
            denied_paths=denied,
            timeout_seconds=timeout_seconds or 30,
        )

    # ─── Private audit helpers ─────────────────────────────────────────────

    def _deny_and_audit(
        self,
        *,
        reason: str,
        action: str,
        target: str,
        operation: str,
        risk: str,
        agent: str,
        user: str = "",
        role: str = "",
        token: Token | None = None,
        approval_chain: list[dict] | None = None,
        metadata: dict | None = None,
    ) -> AuthorizationDecision:
        ev = self.audit.record(
            user=user,
            agent=agent,
            role=role,
            action=action,
            target=target,
            operation=operation,
            risk=risk,
            environment=self.env.label,
            outcome="denied",
            reason=reason,
            approval_chain=approval_chain or [],
            metadata=metadata or {},
        )
        return AuthorizationDecision(
            status="denied",
            reason=reason,
            token=token,
            role=role,
            operation=operation,
            risk=risk,
            environment=self.env.label,
            audit_event_id=ev.event_id,
            approval_chain=approval_chain or [],
        )

    def _approve_and_audit(
        self,
        token: Token,
        *,
        action: str,
        target: str,
        operation: str,
        risk: str,
        agent: str,
        reason: str,
        approval_chain: list[dict] | None = None,
        metadata: dict | None = None,
    ) -> AuthorizationDecision:
        ev = self.audit.record(
            user=token.user_id,
            agent=agent,
            role=token.role,
            action=action,
            target=target,
            operation=operation,
            risk=risk,
            environment=self.env.label,
            outcome="allowed",
            reason=reason,
            approval_chain=approval_chain or [],
            metadata=metadata or {},
        )
        return AuthorizationDecision(
            status="approved",
            reason=reason,
            token=token,
            role=token.role,
            operation=operation,
            risk=risk,
            environment=self.env.label,
            needs_approval=bool(approval_chain),
            audit_event_id=ev.event_id,
            approval_chain=approval_chain or [],
        )

    def _pending_and_audit(
        self,
        token: Token,
        *,
        action: str,
        target: str,
        operation: str,
        risk: str,
        agent: str,
        request: ApprovalRequest,
        metadata: dict | None = None,
    ) -> AuthorizationDecision:
        ev = self.audit.record(
            user=token.user_id,
            agent=agent,
            role=token.role,
            action=action,
            target=target,
            operation=operation,
            risk=risk,
            environment=self.env.label,
            outcome="pending",
            reason=f"approval required — request {request.request_id}",
            approval_chain=[_chain_entry(request)],
            metadata=metadata or {},
        )
        return AuthorizationDecision(
            status="pending",
            reason=f"approval required — request {request.request_id}",
            token=token,
            role=token.role,
            operation=operation,
            risk=risk,
            environment=self.env.label,
            needs_approval=True,
            approval_id=request.request_id,
            audit_event_id=ev.event_id,
            approval_chain=[_chain_entry(request)],
        )


def _chain_entry(
    request: ApprovalRequest, decided: ApprovalRequest | None = None
) -> dict:
    """One entry in an audit approval_chain."""
    source = decided or request
    return {
        "request_id": request.request_id,
        "requester": request.requester,
        "requester_role": request.requester_role,
        "status": source.status.value,
        "approver": source.approver,
        "decided_at": source.decision_at,
        "decision_reason": source.decision_reason,
    }


__all__ = [
    "AuthorizationDecision",
    "DecisionStatus",
    "SecurityContext",
]
