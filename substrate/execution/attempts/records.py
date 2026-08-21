"""Typed records for the canonical execution-attempt slice (MVP Wave 2).

These are persisted execution records. They follow the exact serialization
convention of ``substrate.execution.planning.records`` (``asdict`` +
field-filtered ``from_dict`` + ``_new_id``) so the store layer is a faithful
mirror of ``PlanningStore``.

Two record types live here (plus :class:`CompositionAuthorityUnresolved`, an
authority-outcome signal that lives here only because both the scheduler and the
field control plane must name it and the control plane already imports the
scheduler — see its docstring):

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


class CompositionAuthorityUnresolved(RuntimeError):
    """Composition authority for the DECLARED integration Task could not be RESOLVED.

    Strictly distinct from "this packet is not the integration Task" (a normal
    False) and from "authority was legitimately DENIED" (also False, refused by
    the scenario-map gate). This means the question could not be answered at all
    — e.g. the authorization ledger is present but unreadable.

    It lives here, on the records module, because both the scheduler and the
    field control plane must name it and the control plane already imports the
    scheduler (a module-level import the other way would be a cycle).

    The scheduler deliberately does NOT swallow this one: unknown authority must
    never resolve to "run the integration Task as an ordinary worker". In field
    run 20260807T005250Z-p1 exactly that fallback dispatched a real model worker
    for Task C, which failed twice with no commits, while the composition path
    never ran.
    """


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


@dataclass(frozen=True)
class VerifiedExecutionDeclaration:
    """WHAT execution class each Task of ONE run is — built once, then immutable.

    THE SINGLE DECLARATION AUTHORITY. Seven successive review rounds each closed
    a different consumer of "which Task is the integration Task", and the seventh
    showed why that could never converge: AUTHORITY was integrity-checked while
    the DECLARATION identifying what that authority governs was re-read from
    mutable state at every consumer. Move ``integration_task_id`` in
    ``scenario_map.json`` and the declaration moves with it, so every gate keyed
    off it silently skips — including the write-boundary guard — and a worker row
    becomes durable for the real integration Task (reproduced end to end).

    This type removes the re-read. It is created ONCE per run, from
    ``build_from_records`` — which RECOMPUTES the semantic mapping from the
    canonical plan/packet/grant records after ``resolve_canonical_grant`` — and
    is then carried into Attempt creation. The persisted map's own
    ``integration_task_id`` field is never the source: a retargeted field cannot
    move a declaration that was derived from lineage rather than read.

    DECLARATION IS NOT AUTHORIZATION, and the two must never be conflated:

      * DECLARATION (this type) answers "what execution class is this Task
        allowed to be?" — durable for the run's lifetime.
      * AUTHORIZATION (the grant) answers "may that execution happen NOW?" —
        transient, and legitimately DENIED or UNRESOLVED.

    Grant state may stop composition from running; it may NEVER transform the
    integration Task into a worker Task. Every one of the six pointwise defects
    came from letting a transient authority failure decide a durable class.

    ``binding_digest`` covers the full semantic Task-id mapping together with the
    run/candidate/plan/grant binding, so ``digest`` here authenticates both the
    identity of the run and the mapping this declaration asserts.
    """

    run_id: str
    candidate_sha: str
    digest: str
    execution_classes: tuple[tuple[str, str], ...] = ()

    def execution_class_for(self, task_id: str) -> str | None:
        """The DECLARED class of ``task_id``, or None when undeclared.

        None means "ordinary Task" — A/B/D are undeclared and behave exactly as
        before. It never means "unknown"; an unanswerable declaration is a
        refusal raised at construction, never a None returned here.
        """
        if not task_id:
            return None
        for tid, kind in self.execution_classes:
            if tid == task_id:
                return kind
        return None

    def matches_run(self, *, run_id: str, candidate_sha: str) -> bool:
        """Is this declaration for exactly this run AND candidate?"""
        return self.run_id == run_id and self.candidate_sha == candidate_sha


class DeclarationOutcome(str, Enum):
    """The THREE distinguishable answers to "what execution classes does this run declare?".

    Round 8 collapsed two of these into one absence — ``None`` meant BOTH "this
    run positively has no composition Task" AND "the declaration could not be
    determined" — and three builder exits returned the second while the store
    read it as the first. Five bypasses followed (binding truncated/deleted/
    non-dict, scenario map deleted, binding naming a REJECTED plan): the store
    was left neither armed nor sealed, and ``Task C + worker`` persisted
    immutably through the real scheduler.

    THE LAW: **UNKNOWN MUST NEVER MEAN WORKER.** An absence that encodes two
    meanings is what produced eight rounds of pointwise fixes; this enum makes
    the ambiguity unrepresentable.
    """

    DECLARED = "declared"
    NO_COMPOSITION = "no_composition"
    UNANSWERABLE = "unanswerable"


@dataclass(frozen=True)
class DeclarationResult:
    """The tagged outcome of building a run's verified execution declaration.

    Exactly one of three states, never a bare ``None``/``""``/``{}``/side-channel
    error string. ``UNANSWERABLE`` is the DEFAULT for anything unexpected —
    including a builder exception — so a new failure mode cannot silently become
    "no composition".

    ``NO_COMPOSITION`` is a POSITIVE PROOF, not an absence: it is only produced
    when the run's lineage resolved successfully and genuinely contained no
    composition Task. "I could not read the inputs" is never this state.
    """

    outcome: DeclarationOutcome
    declaration: VerifiedExecutionDeclaration | None = None
    reason: str = ""
    # NO_COMPOSITION is a POSITIVE PROOF about a SPECIFIC run, so it carries the
    # run it proves — exactly like DECLARED. An unbound "nothing here" tag is an
    # unseal-everything token: it provably governs nothing yet opens any store
    # (reproduced). Empty for DECLARED (which binds through `declaration`) and
    # for UNANSWERABLE (which never unseals).
    run_id: str = ""
    candidate_sha: str = ""

    def __post_init__(self) -> None:
        if self.outcome is DeclarationOutcome.NO_COMPOSITION and self.declaration is not None:
            raise ValueError(
                "a NO_COMPOSITION result must not carry a declaration payload — "
                "it is a positive proof of ABSENCE, not an assertion about a "
                "specific Task; the declaration field must be None"
            )
        if self.outcome is DeclarationOutcome.DECLARED and self.declaration is None:
            raise ValueError(
                "a DECLARED result must carry a declaration — "
                "DECLARED with no payload is structurally incoherent"
            )

    @property
    def is_declared(self) -> bool:
        return self.outcome is DeclarationOutcome.DECLARED

    @property
    def is_sealed(self) -> bool:
        """Does this outcome REQUIRE the write boundary to stay sealed?"""
        return self.outcome is DeclarationOutcome.UNANSWERABLE

    @classmethod
    def declared(cls, declaration: VerifiedExecutionDeclaration) -> DeclarationResult:
        return cls(DeclarationOutcome.DECLARED, declaration=declaration)

    @classmethod
    def no_composition(
        cls, reason: str, *, run_id: str = "", candidate_sha: str = ""
    ) -> DeclarationResult:
        """Positively proven: THIS run contains no composition Task.

        The run it proves is part of the proof. A NO_COMPOSITION that names no
        run cannot be verified against the store it is arming, and an
        unverifiable unseal is indistinguishable from a forged one.
        """
        return cls(
            DeclarationOutcome.NO_COMPOSITION,
            reason=reason,
            run_id=run_id,
            candidate_sha=candidate_sha,
        )

    @classmethod
    def unanswerable(cls, reason: str) -> DeclarationResult:
        """The declaration cannot be safely determined. The boundary stays SEALED."""
        return cls(DeclarationOutcome.UNANSWERABLE, reason=reason)


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
    # Canonical provider-neutral capability policy evidence requested and
    # enforced for this attempt. This is control-plane/adapter evidence, not a
    # model claim, and is required for deliberate failure-injection qualification.
    capability_policy: dict[str, Any] = field(default_factory=dict)

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
    "AttemptExecutionKind",
    "DeclarationOutcome",
    "DeclarationResult",
    "AttemptTransition",
    "CompositionAuthorityUnresolved",
    "ExecutionAttempt",
    "VerifiedExecutionDeclaration",
    "ExecutionAttemptStatus",
    "ExecutionAuthorizationGrant",
    "ExecutionAuthorizationGrantStatus",
    "ATTEMPT_IMMUTABLE_FIELDS",
    "GRANT_IMMUTABLE_FIELDS",
    "GRANT_TERMINAL",
]
