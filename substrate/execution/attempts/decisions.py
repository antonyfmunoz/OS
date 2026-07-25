"""Execution-authorization authority — the bounded EFFECT of a HUD Decision.

Mirrors ``substrate.execution.planning.decisions`` but for the
``execution_authorization`` decision kind. Invariants (Amendment v1):

- ``substrate.types.ApprovalRequest`` is the sole Decision identity/lifecycle
  authority. A rejected execution request never becomes a grant record — it
  lives only in ApprovalRequest history. Approving one creates exactly one
  ``ExecutionAuthorizationGrant`` (clause 1).
- Approval kicks off the ACTIVATION UNIT OF WORK (clause 2): resolve the exact
  latest accepted plan version → resolve the authorized WorkPacket set →
  create/reuse ONE grant in ACTIVATING → close the ``execution_authorization``
  gate on those Tasks → transition PLANNED Tasks to APPROVED through canonical
  WorkPacket authority → emit one canonical event chain → mark the grant ACTIVE
  only after every required Task transition commits. Partial failure →
  FAILED_ACTIVATION, never ACTIVE. Retry resumes idempotently.
- No auto-approval path exists: the only callers are the HUD route and
  UnifiedApprovalRuntime.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Callable

from substrate.execution.attempts.events import emit_execution_event
from substrate.execution.attempts.records import (
    ExecutionAuthorizationGrant,
    ExecutionAuthorizationGrantStatus,
)
from substrate.execution.attempts.store import AttemptStoreConflict, ExecutionAttemptStore

logger = logging.getLogger(__name__)

EXECUTION_AUTH_DECISION_KIND = "execution_authorization"
EXECUTION_AUTH_EFFECT = "execute_bounded_task_set"

AUTHORIZATION_REQUEST_MUTATION = "execution_authorization_request"
AUTHORIZATION_DECISION_MUTATION = "execution_authorization_decision"
AUTHORIZATION_REVOKE_MUTATION = "execution_authorization_revoke"
ATTEMPT_TRANSITION_MUTATION = "execution_attempt_transition"  # reused for packet gate close

_GRANT = ExecutionAuthorizationGrantStatus


class ExecutionDecisionConflict(RuntimeError):
    """A conflicting execution decision already resolved this decision_ref."""


def execution_decision_ref(plan: Any) -> str:
    """4-part decision_ref bound to the exact plan version by construction."""
    from substrate.types import build_decision_ref

    return build_decision_ref(
        "objective_plan",
        getattr(plan, "plan_record_id", ""),
        EXECUTION_AUTH_DECISION_KIND,
        f"v{getattr(plan, 'graph_version', 0)}",
    )


def _scope_hash(plan_record_id: str, plan_version: int, task_frontier: list[str]) -> str:
    payload = json.dumps(
        {"plan": plan_record_id, "v": plan_version, "tasks": sorted(task_frontier)},
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


def _native_runner():
    from substrate.execution.intent.loop import _substrate_native_governed_mutation

    return _substrate_native_governed_mutation


def is_authorization_valid(
    grant: ExecutionAuthorizationGrant,
    latest_plan_lookup: Callable[[str], Any] | None = None,
    *,
    now: float | None = None,
) -> tuple[bool, str]:
    """A grant is valid iff ACTIVE, within its time window, and still bound to
    the latest accepted plan version. Any failure → (False, reason)."""
    now = time.time() if now is None else now
    if grant.status != _GRANT.ACTIVE.value:
        return False, f"grant status {grant.status!r} is not active"
    if grant.not_before and now < grant.not_before:
        return False, "grant not yet active (not_before)"
    if grant.expires_at and now >= grant.expires_at:
        return False, "grant expired"
    if latest_plan_lookup is not None:
        latest = latest_plan_lookup(grant.objective_id)
        if latest is None:
            return False, "objective has no plan"
        if getattr(latest, "plan_record_id", "") != grant.plan_record_id:
            return False, "grant plan version invalidated by a newer plan"
        if getattr(latest, "status", "") != "approved":
            return False, f"plan status {getattr(latest, 'status', '')!r} not approved"
    return True, "valid"


def build_execution_approval_request(grant: ExecutionAuthorizationGrant) -> Any:
    """Project one requested authorization into the canonical Decision object.

    The ApprovalRequest carries the full bounded package the HUD renders. Its
    ``expires_at`` is LIVE in Wave 2 (activated here, inert in Wave 1)."""
    from datetime import datetime, timezone

    from substrate.types import ApprovalOrigin, ApprovalRequest, RiskClass

    expires = (
        datetime.fromtimestamp(grant.expires_at, timezone.utc) if grant.expires_at else None
    )
    return ApprovalRequest(
        approval_id=grant.decision_ref,  # stable — never minted per poll
        source_origin=ApprovalOrigin.OTHER,
        source_id=grant.plan_record_id,
        source_channel="execution_authorization",
        title=f"Authorize execution of plan v{grant.plan_version}",
        description=(
            f"Execute {len(grant.task_frontier)} authorized Task(s) under bounded "
            f"authorization (risk ceiling {grant.risk_ceiling})."
        ),
        operation="execution_authorization",
        requested_action="approve or reject bounded execution authorization",
        risk_class=RiskClass.HIGH,
        decision_ref=grant.decision_ref,
        decision_kind=EXECUTION_AUTH_DECISION_KIND,
        subject_type="objective_plan",
        subject_id=grant.plan_record_id,
        subject_version=f"v{grant.plan_version}",
        tenant_id=grant.tenant_id,
        principal_id=grant.principal_id,
        membership_id=grant.membership_id,
        scope_ref=f"tenant:{grant.tenant_id}/plan:{grant.plan_record_id}",
        authorization_effect=EXECUTION_AUTH_EFFECT,
        expires_at=expires,
    )


def request_execution_authorization(
    store: ExecutionAttemptStore,
    *,
    plan: Any,
    task_frontier: list[str],
    tenant_id: str,
    principal_id: str = "",
    membership_id: str = "",
    conversation_id: str = "",
    correlation_id: str = "",
    role_ids: list[str] | None = None,
    environment_classes: list[str] | None = None,
    allowed_tools: list[str] | None = None,
    credential_scope_refs: list[str] | None = None,
    verification_obligations: list[str] | None = None,
    rollback_obligations: list[str] | None = None,
    max_attempts_per_task: int = 2,
    risk_ceiling: str = "high",
    ttl_seconds: float = 3600.0,
    cost_limit_usd: float = 0.0,
    cost_enforceable: bool = False,
    requested_by: str = "operator",
    now: float | None = None,
    mutation_runner: Callable[..., Any] | None = None,
    event_emit: Callable[[str, dict[str, Any]], None] | None = None,
) -> tuple[ExecutionAuthorizationGrant, Any]:
    """Create (or reuse) the requested authorization grant + its ApprovalRequest.

    Fail closed: the plan must be APPROVED. Idempotent: an existing grant for the
    same decision_ref (in any state) is returned with a freshly built
    ApprovalRequest — a request never creates a second grant, and never conveys
    execution authority on its own (the grant stays ACTIVATING until an approved
    Decision drives activation).
    """
    now = time.time() if now is None else now
    if getattr(plan, "status", "") != "approved":
        raise ExecutionDecisionConflict(
            f"plan {getattr(plan, 'plan_record_id', '')} is "
            f"{getattr(plan, 'status', '')!r} — cannot request execution authorization "
            f"(plan must be accepted first)"
        )

    decision_ref = execution_decision_ref(plan)
    existing = store.get_grant(decision_ref)
    if existing is not None:
        return existing, build_execution_approval_request(existing)

    plan_version = int(getattr(plan, "graph_version", 0) or 0)
    grant = ExecutionAuthorizationGrant(
        decision_ref=decision_ref,
        plan_record_id=getattr(plan, "plan_record_id", ""),
        plan_version=plan_version,
        objective_id=getattr(plan, "objective_id", ""),
        tenant_id=tenant_id,
        principal_id=principal_id,
        membership_id=membership_id,
        conversation_id=conversation_id,
        correlation_id=correlation_id or conversation_id,
        status=_GRANT.ACTIVATING.value,
        task_frontier=list(task_frontier),
        max_attempts_per_task=max_attempts_per_task,
        risk_ceiling=risk_ceiling,
        role_ids=list(role_ids or []),
        environment_classes=list(environment_classes or ["git_worktree"]),
        allowed_tools=list(allowed_tools or []),
        credential_scope_refs=list(credential_scope_refs or []),
        not_before=now,
        expires_at=now + ttl_seconds,
        cost_limit_usd=cost_limit_usd,
        cost_enforceable=cost_enforceable,
        verification_obligations=list(verification_obligations or []),
        rollback_obligations=list(rollback_obligations or []),
        authorized_scope_hash=_scope_hash(
            getattr(plan, "plan_record_id", ""), plan_version, list(task_frontier)
        ),
    )
    grant.decision_log.append(
        {"event": "requested", "by": requested_by, "at": now, "tasks": list(task_frontier)}
    )

    runner = mutation_runner or _native_runner()

    def _apply() -> tuple[str, bool]:
        store.create_grant_idempotent(grant)
        return (f"execution authorization requested: {decision_ref}", True)

    response = runner(
        mutation_name=AUTHORIZATION_REQUEST_MUTATION,
        intent=f"request execution authorization for plan {grant.plan_record_id}",
        execute_fn=_apply,
        source="execution_attempts_decisions",
        metadata={
            "decision_ref": decision_ref,
            "plan_record_id": grant.plan_record_id,
            "tenant_id": tenant_id,
            "task_count": len(task_frontier),
        },
    )
    if not bool(getattr(response, "success", False)):
        raise RuntimeError(
            f"execution authorization request rejected by governance: "
            f"{getattr(response, 'output', '')}"
        )

    emit_execution_event(
        "execution.authorization_requested",
        {
            "decision_ref": decision_ref,
            "plan_record_id": grant.plan_record_id,
            "tenant_id": tenant_id,
            "task_frontier": list(task_frontier),
        },
        correlation_id=grant.correlation_id,
    )
    if event_emit is not None:
        try:
            event_emit("execution.authorization_requested", {"decision_ref": decision_ref})
        except Exception as exc:  # observability only
            logger.debug("authorization request event emit failed: %s", exc)
    return grant, build_execution_approval_request(grant)


def apply_execution_decision(
    store: ExecutionAttemptStore,
    decision_ref: str,
    decision: str,  # "approve" | "reject" | "revoke"
    *,
    decided_by: str = "operator",
    reason: str = "",
    latest_plan_lookup: Callable[[str], Any] | None = None,
    activate_fn: Callable[[ExecutionAuthorizationGrant], ExecutionAuthorizationGrant] | None = None,
    now: float | None = None,
    mutation_runner: Callable[..., Any] | None = None,
) -> ExecutionAuthorizationGrant:
    """Apply one HUD execution-authorization decision under governed mutation.

    approve → runs the activation unit of work (grant → ACTIVE). reject → the
    grant is discarded (never persisted as a live grant; if a requested grant
    exists it moves to a terminal non-active state). revoke → ACTIVE grant →
    REVOKED (cascade handled by the scheduler). Idempotent: repeating the SAME
    decision is a no-op; a conflicting decision raises ExecutionDecisionConflict.
    """
    now = time.time() if now is None else now
    decision = (decision or "").strip().lower()
    if decision not in ("approve", "reject", "revoke"):
        raise ValueError(f"unknown execution decision {decision!r} (approve|reject|revoke)")

    grant = store.get_grant(decision_ref)
    if grant is None:
        raise ExecutionDecisionConflict(f"no execution authorization grant for {decision_ref}")

    # Idempotency + conflict handling.
    if decision == "approve" and grant.status == _GRANT.ACTIVE.value:
        return grant  # already activated — no-op
    if decision == "revoke" and grant.status == _GRANT.REVOKED.value:
        return grant
    if decision == "reject" and grant.status in (
        _GRANT.INVALIDATED.value,
        _GRANT.FAILED_ACTIVATION.value,
    ):
        return grant
    if grant.status in (_GRANT.EXPIRED.value, _GRANT.INVALIDATED.value) and decision == "approve":
        raise ExecutionDecisionConflict(
            f"grant {decision_ref} is {grant.status!r} — cannot approve a stale authorization"
        )

    runner = mutation_runner or _native_runner()

    if decision == "approve":
        # Re-validate at grant time: plan still latest + approved, not expired.
        if grant.expires_at and now >= grant.expires_at:
            _terminalize(store, grant, _GRANT.EXPIRED.value, "expired before approval", now, runner)
            raise ExecutionDecisionConflict(f"grant {decision_ref} expired before approval")
        if latest_plan_lookup is not None:
            latest = latest_plan_lookup(grant.objective_id)
            if latest is None or getattr(latest, "plan_record_id", "") != grant.plan_record_id:
                _terminalize(
                    store, grant, _GRANT.INVALIDATED.value, "plan revised", now, runner
                )
                raise ExecutionDecisionConflict(
                    f"grant {decision_ref} invalidated — a newer plan version supersedes it"
                )
            if getattr(latest, "status", "") != "approved":
                raise ExecutionDecisionConflict(
                    f"grant {decision_ref}: plan not approved ({getattr(latest, 'status', '')})"
                )
        # Activation unit of work → ACTIVE (or FAILED_ACTIVATION on partial failure).
        if activate_fn is not None:
            grant = activate_fn(grant)
        else:
            grant = _mark_active(store, grant, now, runner, decided_by)
        emit_execution_event(
            "execution.authorization_granted",
            {"decision_ref": decision_ref, "plan_record_id": grant.plan_record_id},
            correlation_id=grant.correlation_id,
        )
        return grant

    if decision == "reject":
        grant = _terminalize(
            store, grant, _GRANT.FAILED_ACTIVATION.value, reason or "rejected", now, runner,
            log_event="rejected",
        )
        emit_execution_event(
            "execution.authorization_rejected",
            {"decision_ref": decision_ref, "reason": reason},
            correlation_id=grant.correlation_id,
        )
        return grant

    # revoke
    grant = _terminalize(
        store, grant, _GRANT.REVOKED.value, reason or "revoked", now, runner, log_event="revoked"
    )
    emit_execution_event(
        "execution.authorization_revoked",
        {"decision_ref": decision_ref, "reason": reason},
        correlation_id=grant.correlation_id,
    )
    return grant


def _mark_active(
    store: ExecutionAttemptStore,
    grant: ExecutionAuthorizationGrant,
    now: float,
    runner: Callable[..., Any],
    decided_by: str,
) -> ExecutionAuthorizationGrant:
    """Minimal activation: flip ACTIVATING → ACTIVE under governed mutation.

    The Task-gate-close + PLANNED→APPROVED steps of the activation unit of work
    are supplied by an ``activate_fn`` (wired in C2 route/scheduler integration);
    here the grant simply commits to ACTIVE. Kept as a single CAS write so a
    crash between request and approval resumes idempotently."""
    def _apply() -> tuple[str, bool]:
        grant.status = _GRANT.ACTIVE.value
        grant.decision_log.append({"event": "activated", "by": decided_by, "at": now})
        store.update_grant_cas(
            grant,
            expected_record_version=grant.record_version,
            expected_statuses=(_GRANT.ACTIVATING.value,),
        )
        return (f"execution authorization active: {grant.decision_ref}", True)

    response = runner(
        mutation_name=AUTHORIZATION_DECISION_MUTATION,
        intent=f"activate execution authorization {grant.decision_ref}",
        execute_fn=_apply,
        source="execution_attempts_decisions",
        metadata={"decision_ref": grant.decision_ref, "decision": "approve"},
    )
    if not bool(getattr(response, "success", False)):
        # Fail-closed: a rejected activation leaves the grant NOT active.
        raise RuntimeError(
            f"execution authorization decision rejected by governance: "
            f"{getattr(response, 'output', '')}"
        )
    return grant


def _terminalize(
    store: ExecutionAttemptStore,
    grant: ExecutionAuthorizationGrant,
    to_status: str,
    reason: str,
    now: float,
    runner: Callable[..., Any],
    log_event: str = "terminalized",
) -> ExecutionAuthorizationGrant:
    mutation = (
        AUTHORIZATION_REVOKE_MUTATION
        if to_status == _GRANT.REVOKED.value
        else AUTHORIZATION_DECISION_MUTATION
    )

    def _apply() -> tuple[str, bool]:
        grant.status = to_status
        grant.decision_log.append({"event": log_event, "reason": reason, "at": now})
        store.update_grant_cas(grant, expected_record_version=grant.record_version)
        return (f"grant {grant.decision_ref} → {to_status}", True)

    response = runner(
        mutation_name=mutation,
        intent=f"{log_event} execution authorization {grant.decision_ref}",
        execute_fn=_apply,
        source="execution_attempts_decisions",
        metadata={"decision_ref": grant.decision_ref, "to_status": to_status},
    )
    if not bool(getattr(response, "success", False)):
        raise RuntimeError(
            f"grant terminalization rejected by governance: {getattr(response, 'output', '')}"
        )
    return grant


def sweep_expired_authorizations(
    store: ExecutionAttemptStore,
    *,
    now: float | None = None,
    mutation_runner: Callable[..., Any] | None = None,
) -> int:
    """Expire ACTIVATING/ACTIVE grants past their window. Returns the count."""
    now = time.time() if now is None else now
    runner = mutation_runner or _native_runner()
    expired = 0
    for grant in store.active_grants() + [
        g
        for g in _all_grants(store)
        if g.status == _GRANT.ACTIVATING.value
    ]:
        if grant.expires_at and now >= grant.expires_at:
            try:
                _terminalize(
                    store, grant, _GRANT.EXPIRED.value, "time window elapsed", now, runner
                )
                emit_execution_event(
                    "execution.authorization_expired",
                    {"decision_ref": grant.decision_ref},
                    correlation_id=grant.correlation_id,
                )
                expired += 1
            except (AttemptStoreConflict, RuntimeError) as exc:
                logger.debug("expiry sweep skipped %s: %s", grant.decision_ref, exc)
    return expired


def _all_grants(store: ExecutionAttemptStore) -> list[ExecutionAuthorizationGrant]:
    rows = store._read_lines(store._grants_path)  # noqa: SLF001 - internal sweep read
    return [ExecutionAuthorizationGrant.from_dict(r) for r in rows]


class ExecutionAuthorizationDecisionSource:
    """UnifiedApprovalRuntime source adapter (source_type=execution_authorization).

    Structurally identical to ObjectivePlanDecisionSource: surfaces requested
    grants as pending HUD decisions with STABLE ids (the decision_ref), risk
    HIGH, and the full bounded package in ``context.details``; approve/reject
    route to ``apply_execution_decision``. approve() additionally requests one
    bounded scheduler pass (wired by the caller via ``on_grant_activated``).
    """

    def __init__(
        self,
        store: ExecutionAttemptStore | None = None,
        *,
        latest_plan_lookup: Callable[[str], Any] | None = None,
        activate_fn: Callable[[ExecutionAuthorizationGrant], ExecutionAuthorizationGrant] | None = None,
        on_grant_activated: Callable[[ExecutionAuthorizationGrant], None] | None = None,
        mutation_runner: Callable[..., Any] | None = None,
    ) -> None:
        self._store = store or ExecutionAttemptStore()
        self._latest_plan_lookup = latest_plan_lookup
        # Default the activation to the FULL unit-of-work (grant → ACTIVE AND each
        # task_frontier packet PLANNED → APPROVED), not the bare grant-flip.
        # apply_execution_decision falls back to `_mark_active` when activate_fn is
        # None, and `_mark_active` ONLY flips the grant to ACTIVE — it does NOT
        # close the task gate. With no activate_fn wired, the HUD approve left the
        # grant ACTIVE but its tasks PLANNED, so the runner refused to dispatch
        # ("waiting on tasks that are not APPROVED yet") and no worker ran (field
        # run 20260725T185849Z-p1). Wire activate_authorized_tasks by default so
        # approval runs the whole clause-2 unit of work; a caller may still inject
        # its own activate_fn for tests.
        if activate_fn is None:
            def _default_activate_fn(
                grant: ExecutionAuthorizationGrant,
            ) -> ExecutionAuthorizationGrant:
                from substrate.execution.attempts.activation import activate_authorized_tasks
                from substrate.organism.universal_work_queue import UniversalWorkQueue

                return activate_authorized_tasks(
                    self._store,
                    grant,
                    UniversalWorkQueue(),
                    mutation_runner=self._mutation_runner,
                )

            activate_fn = _default_activate_fn
        self._activate_fn = activate_fn
        self._on_grant_activated = on_grant_activated
        self._mutation_runner = mutation_runner

    def pending_decisions(self) -> list[Any]:
        from substrate.workstation.unified_approval_runtime import (
            ApprovalSourceType,
            UnifiedApproval,
        )

        out: list[Any] = []
        for grant in _all_grants(self._store):
            if grant.status != _GRANT.ACTIVATING.value:
                continue
            out.append(
                UnifiedApproval(
                    approval_id=grant.decision_ref,
                    source_type=ApprovalSourceType.EXECUTION_AUTH,
                    title=f"Authorize execution of plan v{grant.plan_version}",
                    description=(
                        f"Execute {len(grant.task_frontier)} authorized Task(s) "
                        f"(risk ceiling {grant.risk_ceiling})."
                    ),
                    risk_class="high",  # HUD top-slice guarantee
                    waiting_since=grant.updated_at or grant.created_at,
                    work_id=grant.decision_ref,
                    context={
                        "decision_ref": grant.decision_ref,
                        "authorization_effect": EXECUTION_AUTH_EFFECT,
                        "details": {
                            "plan_record_id": grant.plan_record_id,
                            "plan_version": grant.plan_version,
                            "task_frontier": list(grant.task_frontier),
                            "role_ids": list(grant.role_ids),
                            "environment_classes": list(grant.environment_classes),
                            "allowed_tools": list(grant.allowed_tools),
                            "risk_ceiling": grant.risk_ceiling,
                            "expires_at": grant.expires_at,
                            "cost_limit_usd": grant.cost_limit_usd,
                            "cost_enforceable": grant.cost_enforceable,
                            "verification_obligations": list(grant.verification_obligations),
                            "rollback_obligations": list(grant.rollback_obligations),
                        },
                    },
                )
            )
        return out

    def approve(self, decision_ref: str, decided_by: str = "operator") -> bool:
        grant = apply_execution_decision(
            self._store,
            decision_ref,
            "approve",
            decided_by=decided_by,
            latest_plan_lookup=self._latest_plan_lookup,
            activate_fn=self._activate_fn,
            mutation_runner=self._mutation_runner,
        )
        if grant.status == _GRANT.ACTIVE.value and self._on_grant_activated is not None:
            try:
                self._on_grant_activated(grant)
            except Exception as exc:  # a scheduler kick failure must not unwind the grant
                logger.debug("post-activation scheduler kick failed: %s", exc)
        return grant.status == _GRANT.ACTIVE.value

    def reject(self, decision_ref: str, reason: str = "", decided_by: str = "operator") -> bool:
        grant = apply_execution_decision(
            self._store,
            decision_ref,
            "reject",
            decided_by=decided_by,
            reason=reason,
            mutation_runner=self._mutation_runner,
        )
        return grant.status == _GRANT.FAILED_ACTIVATION.value


__all__ = [
    "EXECUTION_AUTH_DECISION_KIND",
    "EXECUTION_AUTH_EFFECT",
    "ExecutionDecisionConflict",
    "execution_decision_ref",
    "is_authorization_valid",
    "build_execution_approval_request",
    "request_execution_authorization",
    "apply_execution_decision",
    "sweep_expired_authorizations",
    "ExecutionAuthorizationDecisionSource",
]
