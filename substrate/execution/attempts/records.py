"""Typed records for the canonical execution-attempt slice (MVP Wave 2).

These are persisted execution records. They follow the exact serialization
convention of ``substrate.execution.planning.records`` (``asdict`` +
field-filtered ``from_dict`` + ``_new_id``) so the store layer is a faithful
mirror of ``PlanningStore``.

Two record types live here:

- :class:`ExecutionAttempt` — the ONE canonical concrete execution lifecycle
  object. One Task (WorkPacket) has zero, one, or many attempts. An attempt
  never becomes a Task; a retry creates a new attempt linked to the prior one;
  historical attempts are immutable except through valid lifecycle transitions.

- :class:`ExecutionAuthorizationGrant` — the persisted BOUNDED EFFECT of an
  APPROVED ``execution_authorization`` Decision (Amendment v1 clause 1). It is
  NOT a Decision: ``substrate.types.ApprovalRequest`` owns pending/approved/
  rejected decision state. The grant only exists once its Decision was approved,
  and its states are ACTIVATING/ACTIVE/EXPIRED/REVOKED/INVALIDATED/
  FAILED_ACTIVATION — there is deliberately NO ``requested``/``denied`` state.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _from_dict(cls: type, d: dict[str, Any]) -> Any:
    return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── ExecutionAttempt ─────────────────────────────────────────────────────────


class AttemptExecutionKind(str, Enum):
    """WHO executes an attempt — the persisted composition authority.

    An attempt is either performed by a model WORKER in a dispatched sandbox, or
    it is a CONTROL-PLANE COMPOSITION: a deterministic git-plumbing fan-in that
    the control plane performs itself, with no worker, no dispatch and no
    instruction package.

    This exists because nothing else on the record could carry that fact. The
    semantic label ("integration_task_id") lives on the ObjectivePlanNode and in
    the run's scenario map — it is NEVER copied onto the WorkPacket, so
    ``lifecycle.py`` (which receives only the attempt) cannot see it. And the
    absence of a worker cannot stand in for it: in real field data EVERY attempt
    carries ``worker_identity == 'cc-cli@vps-host'`` (run 20260805T182714Z-p1,
    all five attempts including the failed ones), so "empty worker" discriminates
    nothing and would be an inference over a field that never varies.

    Assigned once at attempt creation from the VALIDATED scenario map, then
    immutable (see ``ATTEMPT_IMMUTABLE_FIELDS``): ``transition_cas`` raises on any
    attempt to write it through ``updates``, so no caller can promote an ordinary
    worker attempt into the composition lifecycle after the fact.
    """

    WORKER = "worker"
    CONTROL_PLANE_COMPOSITION = "control_plane_composition"


class ExecutionAttemptStatus(str, Enum):
    """The one canonical execution-attempt lifecycle (directive §IV)."""

    CREATED = "created"
    READY = "ready"
    LEASED = "leased"
    DISPATCHED = "dispatched"
    RUNNING = "running"
    VERIFYING = "verifying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"


@dataclass
class AttemptTransition:
    """One immutable entry in an attempt's append-only lifecycle history."""

    from_status: str = ""
    to_status: str = ""
    # "scheduler" | "worker:<identity>" | "verifier:<identity>" |
    # "operator:<id>" | "system:expiry"
    actor: str = ""
    reason: str = ""
    # EventSpine event_id emitted for this transition (correlation anchor).
    event_id: str = ""
    at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AttemptTransition:
        return _from_dict(cls, d)


@dataclass
class ExecutionAttempt:
    """The ONE canonical concrete execution object.

    Identity fields are immutable once created; only binding/result fields are
    updated, and only through ``ExecutionAttemptStore.transition_cas`` (the
    single CAS-protected write path).
    """

    # ── Identity (directive-mandated; immutable) ──────────────────────────
    attempt_id: str = field(default_factory=lambda: _new_id("ea"))
    task_id: str = ""  # canonical WorkPacket.packet_id (wp-*)
    objective_id: str = ""  # goal-*
    plan_record_id: str = ""  # opr-*
    plan_version: int = 0  # exact ObjectivePlanRecord.graph_version bound
    # decision_ref of the execution_authorization Decision whose grant admits
    # this attempt (objective_plan:opr-x:execution_authorization:vN).
    execution_authorization_ref: str = ""
    attempt_number: int = 1
    tenant_id: str = ""
    principal_id: str = ""
    membership_id: str = ""
    # conversation_id → … → plan_record_id → task_id → attempt_id chain anchor.
    correlation_id: str = ""
    # WHO executes this attempt. Immutable after creation; a legacy record with
    # no such key deserializes to WORKER, so existing behavior is unchanged.
    execution_kind: str = AttemptExecutionKind.WORKER.value

    # ── Lifecycle ─────────────────────────────────────────────────────────
    status: str = ExecutionAttemptStatus.CREATED.value
    transitions: list[dict[str, Any]] = field(default_factory=list)  # AttemptTransition dicts
    # Retry linkage — a retry is ALWAYS a new attempt, never a re-transition.
    previous_attempt_id: str = ""
    blocked_reason: str = ""

    # ── Bindings (filled as the pipeline advances; each write is CAS) ──────
    readiness_assessment_id: str = ""
    assignment_id: str = ""  # durable FleetAssignment
    lease_id: str = ""  # ExecutionEnvironmentLease
    instruction_package_hash: str = ""  # ModelExecutionPackage.package_hash (sealed per attempt)
    worker_identity: str = ""  # e.g. "cc_cli_worktree@node:<compute_node_id>"
    verifier_role_id: str = ""
    verifier_identity: str = ""

    # ── Result ────────────────────────────────────────────────────────────
    proof_id: str = ""  # AttemptProof id (required before SUCCEEDED — clause 6)
    result_summary: str = ""
    error: str = ""
    files_changed: list[str] = field(default_factory=list)
    commits: list[str] = field(default_factory=list)

    # ── Budget / cost truth (Amendment v1 clause 8) ───────────────────────
    # cost_usd is recorded ONLY when a trustworthy provider usage figure is
    # available; otherwise it stays null and cost_status stays "unknown". Wave 2
    # NEVER claims USD enforcement — boundedness comes from time/turn/attempt.
    cost_usd: float | None = None
    cost_status: str = "unknown"  # "unknown" | "recorded"
    budget_enforcement: str = "time_turn_attempt"
    max_turns: int = 0
    timeout_seconds: int = 0

    # ── Concurrency ───────────────────────────────────────────────────────
    record_version: int = 0  # CAS counter, bumped by every store rewrite
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ExecutionAttempt:
        return _from_dict(cls, d)

    def is_terminal(self) -> bool:
        return self.status in _ATTEMPT_TERMINAL

    def transition_objects(self) -> list[AttemptTransition]:
        return [AttemptTransition.from_dict(t) for t in self.transitions]


_ATTEMPT_TERMINAL: frozenset[str] = frozenset(
    {
        ExecutionAttemptStatus.SUCCEEDED.value,
        ExecutionAttemptStatus.FAILED.value,
        ExecutionAttemptStatus.CANCELLED.value,
        ExecutionAttemptStatus.ROLLED_BACK.value,
    }
)

# Identity fields may NEVER be mutated after creation (enforced by the store).
ATTEMPT_IMMUTABLE_FIELDS: frozenset[str] = frozenset(
    {
        "attempt_id",
        "task_id",
        "objective_id",
        "plan_record_id",
        "plan_version",
        "execution_authorization_ref",
        "attempt_number",
        "tenant_id",
        "principal_id",
        "membership_id",
        "correlation_id",
        "previous_attempt_id",
        "created_at",
        # Composition authority. Immutable so a caller cannot flip an ordinary
        # worker attempt into the composition lifecycle (which skips DISPATCHED /
        # RUNNING) through a binding update.
        "execution_kind",
    }
)


# ── ExecutionAuthorizationGrant ──────────────────────────────────────────────


class ExecutionAuthorizationGrantStatus(str, Enum):
    """Grant states (Amendment v1 clause 1).

    A grant is the bounded EFFECT of an APPROVED ``execution_authorization``
    Decision — never the decision itself. Hence NO ``requested``/``denied``
    state exists here: pending/rejected decision state lives only in the
    canonical ApprovalRequest history.
    """

    ACTIVATING = "activating"  # approval committed; applying Task activation unit-of-work
    ACTIVE = "active"  # every required Task transition committed — admission may proceed
    EXPIRED = "expired"  # past expires_at
    REVOKED = "revoked"  # operator/system revoked
    INVALIDATED = "invalidated"  # plan revised to a newer accepted version
    FAILED_ACTIVATION = "failed_activation"  # partial failure — never became ACTIVE


@dataclass
class ExecutionAuthorizationGrant:
    """Persisted bounded effect of an APPROVED execution_authorization Decision.

    The Decision object is ``substrate.types.ApprovalRequest`` (adapted, 4-part
    ``decision_ref``). This record is its bounded, versioned execution effect —
    like ``ObjectivePlanRecord`` is the subject of a ``plan_acceptance`` Decision.
    """

    grant_id: str = field(default_factory=lambda: _new_id("exgrant"))
    # 4-part decision_ref of the approved execution_authorization Decision
    # (objective_plan:opr-x:execution_authorization:vN) — bound to exact version.
    decision_ref: str = ""
    plan_record_id: str = ""
    plan_version: int = 0
    objective_id: str = ""
    tenant_id: str = ""
    principal_id: str = ""
    membership_id: str = ""
    conversation_id: str = ""
    correlation_id: str = ""

    status: str = ExecutionAuthorizationGrantStatus.ACTIVATING.value

    # ── The BOUNDS (directive "execution authorization") ──────────────────
    task_frontier: list[str] = field(default_factory=list)  # exact packet_ids authorized
    max_attempts_per_task: int = 2
    risk_ceiling: str = "high"  # RiskClass value
    role_ids: list[str] = field(default_factory=list)  # RoleContract ids permitted to execute
    environment_classes: list[str] = field(default_factory=list)  # e.g. ["git_worktree"]
    allowed_tools: list[str] = field(default_factory=list)
    credential_scope_refs: list[str] = field(default_factory=list)  # names/refs ONLY, never values
    not_before: float = 0.0
    expires_at: float = 0.0  # time window — expiry is LIVE in Wave 2
    # Monetary ceiling is DECLARED but not USD-enforceable in Wave 2 (clause 8):
    # a non-zero value with cost_enforceable False BLOCKS readiness.
    cost_limit_usd: float = 0.0
    cost_enforceable: bool = False
    verification_obligations: list[str] = field(default_factory=list)
    rollback_obligations: list[str] = field(default_factory=list)

    # Hash over the immutable authorized scope — the governed spine validates
    # every Wave 2 action is a subset of this (Amendment v1 clause 5).
    authorized_scope_hash: str = ""

    # Task-activation unit-of-work bookkeeping (clause 2): the packet ids whose
    # execution_authorization gate this grant closed and transitioned to APPROVED.
    activated_task_ids: list[str] = field(default_factory=list)

    # grant/revoke/expire/invalidate/activation-progress entries (append-only).
    decision_log: list[dict[str, Any]] = field(default_factory=list)

    record_version: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ExecutionAuthorizationGrant:
        return _from_dict(cls, d)

    def is_active(self) -> bool:
        return self.status == ExecutionAuthorizationGrantStatus.ACTIVE.value


GRANT_TERMINAL: frozenset[str] = frozenset(
    {
        ExecutionAuthorizationGrantStatus.EXPIRED.value,
        ExecutionAuthorizationGrantStatus.REVOKED.value,
        ExecutionAuthorizationGrantStatus.INVALIDATED.value,
        ExecutionAuthorizationGrantStatus.FAILED_ACTIVATION.value,
    }
)

GRANT_IMMUTABLE_FIELDS: frozenset[str] = frozenset(
    {
        "grant_id",
        "decision_ref",
        "plan_record_id",
        "plan_version",
        "objective_id",
        "tenant_id",
        "principal_id",
        "membership_id",
        "conversation_id",
        "correlation_id",
        "authorized_scope_hash",
        "created_at",
    }
)


__all__ = [
    "AttemptTransition",
    "ExecutionAttempt",
    "ExecutionAttemptStatus",
    "ExecutionAuthorizationGrant",
    "ExecutionAuthorizationGrantStatus",
    "ATTEMPT_IMMUTABLE_FIELDS",
    "GRANT_IMMUTABLE_FIELDS",
    "GRANT_TERMINAL",
]
