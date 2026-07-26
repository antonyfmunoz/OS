"""Typed records for the objective-planning loop.

MVP Wave 1. These are persisted planning records — evidence-grounded,
versioned, and navigable in both directions along the linkage contract:

    conversation_id → message_id → intent_id → grounding_snapshot_id
    → current_state_id / desired_state_id / gap_model_id
    → plan_record_id → workpacket_ids → approval_request_ids

The ObjectivePlanRecord is a versioned planning SOURCE consumed by canonical
read surfaces. It is NOT a rival of ``substrate.organism.work_graph.WorkGraph``
(the sole canonical WorkGraph projection): executable plan nodes are
materialized as canonical WorkPackets, which that projection composes untouched.

Desired state must never be represented as current state: the two live in
distinct records with distinct ids, and the compiler enforces non-identity.
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


# ── Intent assessment ────────────────────────────────────────────────────────


class IntentAssessmentState(str, Enum):
    """Assessment of one operator objective — lives on the planning session.

    Deliberately NOT added to ``IntentLoopStage``: the intent-loop read surface,
    panel, and tests switch on that enum's existing values. This assessment is a
    planning-session concern layered on top of the reused IntentSpec.
    """

    SUFFICIENTLY_SPECIFIED = "sufficiently_specified"
    CLARIFICATION_REQUIRED = "clarification_required"
    UNSUPPORTED = "unsupported"
    PROHIBITED = "prohibited"
    FAILED = "failed"


@dataclass
class IntentAssessment:
    """Deterministic assessment of one objective's readiness for planning."""

    intent_id: str
    state: str
    clarification_questions: list[dict[str, str]] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    deterministic: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> IntentAssessment:
        return _from_dict(cls, d)


# ── Grounding ────────────────────────────────────────────────────────────────


@dataclass
class GroundingSnapshot:
    """Bounded, decision-relevant evidence assembled for one objective.

    Failed or timed-out sources land in ``unknown_sources`` — missing evidence
    is a recorded state, never an exception. ``truncated`` marks budget clips.
    """

    grounding_snapshot_id: str = field(default_factory=lambda: _new_id("gs"))
    intent_id: str = ""
    conversation_id: str = ""
    message_id: str = ""
    budget: dict[str, Any] = field(default_factory=dict)
    sources: list[dict[str, Any]] = field(default_factory=list)
    unknown_sources: list[str] = field(default_factory=list)
    truncated: bool = False
    deterministic: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GroundingSnapshot:
        return _from_dict(cls, d)

    def evidence_ref(self, source: str) -> str:
        return f"{self.grounding_snapshot_id}:{source}"


# ── Current / desired / gap (kept separate by construction) ──────────────────


@dataclass
class CurrentStateRecord:
    """What evidence supports as true NOW. Statements carry evidence refs."""

    current_state_id: str = field(default_factory=lambda: _new_id("cur"))
    intent_id: str = ""
    grounding_snapshot_id: str = ""
    statements: list[dict[str, Any]] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CurrentStateRecord:
        return _from_dict(cls, d)


@dataclass
class DesiredStateRecord:
    """What the operator is requesting to BECOME true. Never current state."""

    desired_state_id: str = field(default_factory=lambda: _new_id("des"))
    intent_id: str = ""
    statements: list[dict[str, Any]] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DesiredStateRecord:
        return _from_dict(cls, d)


@dataclass
class GapAssessmentSnapshot:
    """Planning-time gap assessment — an EVIDENCE-class snapshot, NOT the
    strategic-gap authority.

    The canonical strategic gap is ``substrate.organism.strategic_gap_engine.
    Gap`` (goal-linked, current/required state). This snapshot records the
    transformations/discoveries one planning pass derived between current and
    desired state, plus assumptions, contradictions, unknowns, and owner-only
    decisions — all explicit, none folded into prose. ``goal_refs`` links to
    canonical Gap/Goal records where they exist; the snapshot never claims
    strategic-gap authority (Convergence Law representation class: evidence).
    """

    gap_model_id: str = field(default_factory=lambda: _new_id("gap"))
    current_state_id: str = ""
    desired_state_id: str = ""
    goal_refs: list[str] = field(default_factory=list)
    # The EXECUTABLE gap set — exactly the gaps that materialize as Tasks.
    gaps: list[dict[str, Any]] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    contradictions: list[dict[str, Any]] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    owner_decisions: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    # Which producer owns ``gaps`` for this Plan version (DecompositionMode).
    # Recorded so the selection is auditable rather than inferred after the
    # fact from what happens to be present.
    decomposition_mode: str = ""
    # Evidence-derived gaps that did NOT win executable authority under
    # DECLARED_EXCLUSIVE. They are PRESERVED here as non-executable planning
    # evidence — never silently deleted, never materialized as sibling Tasks —
    # so the information remains inspectable and available to later planning.
    derived_evidence_gaps: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GapAssessmentSnapshot:
        return _from_dict(cls, d)


# ── Planning session (conversation → plan resolver + idempotency) ────────────


class PlanningStageMarker(str, Enum):
    """Recovery marker for the planning unit of work (§22.2).

    Objective resolution + Plan creation + Task materialization form ONE
    recoverable logical operation. The marker lives ONLY on PlanningSession
    (and the plan record it points to) — it is never a new lifecycle on the
    canonical Goal, which keeps its own GoalStatus vocabulary (§23.3).
    Retries resume from the last committed stage and reuse the persisted
    objective_id; partial failure can never duplicate Objectives/Plans/Tasks.
    """

    RESOLVING_OBJECTIVE = "resolving_objective"
    OBJECTIVE_RESOLVED = "objective_resolved"
    PLAN_COMPILED = "plan_compiled"
    TASKS_MATERIALIZED = "tasks_materialized"
    DECISION_EVALUATED = "decision_evaluated"
    COMMITTED = "committed"
    FAILED = "failed"


@dataclass
class PlanningSession:
    """One conversation's planning thread — the conversation→plan resolver.

    Idempotency primary key: ``(conversation_id, client_message_id)`` — the
    planning_operation_key (§23.2) that governs retries. The content
    fingerprint is the fallback when the client omits its message id.
    ``objective_id`` is persisted BEFORE planning continues past objective
    resolution; every retry reuses that exact id.
    """

    session_id: str = field(default_factory=lambda: _new_id("ps"))
    conversation_id: str = ""
    message_id: str = ""
    client_message_id: str = ""
    message_fingerprint: str = ""
    tenant_id: str = ""
    principal_id: str = ""
    membership_id: str = ""
    objective_id: str = ""
    intent_id: str = ""
    objective_text: str = ""
    assessment: dict[str, Any] = field(default_factory=dict)
    stage: str = "assessed"  # assessed | awaiting_clarification | compiled | closed
    # §22.2 unit-of-work recovery marker (PlanningStageMarker values).
    operation_stage: str = ""
    operation_error: str = ""
    clarification_history: list[dict[str, str]] = field(default_factory=list)
    active_plan_record_id: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PlanningSession:
        return _from_dict(cls, d)


# ── The versioned plan record ────────────────────────────────────────────────


class ObjectivePlanStatus(str, Enum):
    DRAFT = "draft"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"


_NODE_KINDS = ("packet", "decision_gate", "verification", "milestone")


@dataclass
class ObjectivePlanNode:
    """One node of a plan. Only ``packet`` nodes materialize WorkPackets."""

    node_id: str = field(default_factory=lambda: _new_id("node"))
    kind: str = "packet"
    title: str = ""
    lane: str = ""
    workpacket_id: str = ""
    status: str = "active"  # active | removed | superseded
    depends_on: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    gap_id: str = ""
    # Cross-projection planning (§23.6): "" | "substrate" | "projection:<id>".
    # Projection-target nodes materialize with a NARROWED WorkScope.
    target: str = ""
    # The node's OBJECTIVE-DERIVED writable-path authority, worktree-relative.
    # This is the planning-time owner of mutation scope: the compiler seeds it
    # onto the materialized WorkPacket's WorkRequirements
    # (``declare_writable_paths`` → ``scope_declared=True``), and verification
    # reads that persisted contract alone. Empty list + ``scope_declared`` means
    # "nothing may change" (the verifier lane); a packet node that declares NO
    # scope fails materialization closed — an undeclared scope is never
    # whole-repository permission (field run 20260725T230726Z: a Task persisted
    # with scope_declared=False made every legitimate diff unverifiable).
    writable_path_scope: list[str] = field(default_factory=list)
    scope_declared: bool = False
    # The declaring lane's semantic identity (e.g. implementation vs the
    # independent-verification lane), carried for read surfaces and verifier
    # diagnostics. NEVER used to derive authority — the persisted
    # writable_path_scope is the only mutation authority.
    semantic_label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ObjectivePlanNode:
        return _from_dict(cls, d)


class DecompositionMode(str, Enum):
    """WHO owns the executable decomposition of one Plan version.

    Exactly one mode wins per ObjectivePlanRecord version, chosen at a single
    deterministic selection point in the canonical compiler. Two producers may
    never both claim executable Task authority for the same Plan version: a
    caller-DECLARED lane set and generic evidence-DERIVED gaps compiling as
    siblings is what produced an 11-Task graph where the protocol requires
    four (field run 20260726T193442Z, layer 11).

    - ``DECLARED_EXCLUSIVE`` — the caller declared lanes; that set is the
      COMPLETE executable decomposition. Evidence-derived gaps are preserved as
      non-executable planning evidence (``GapAssessmentSnapshot.gaps`` retains
      them via ``derived_evidence_gaps``) and materialize ZERO sibling Tasks.
    - ``DERIVED`` — no declaration; the evidence/gap compiler owns it.
    - ``UMBRELLA_FALLBACK`` — neither produced anything actionable, so the
      objective itself is the single transformation.
    """

    DECLARED_EXCLUSIVE = "declared_exclusive"
    DERIVED = "derived"
    UMBRELLA_FALLBACK = "umbrella_fallback"


@dataclass
class ObjectiveLane:
    """One caller-declared lane of a decomposed objective.

    A lane is the planning-time declaration that an objective is realized by
    SEVERAL cooperating Tasks rather than one umbrella Task — each with its own
    least-privilege mutation authority and its own place in the dependency
    graph. It is the typed form of the authority the caller already supplies
    via ``writable_path_scope``: substrate never infers lanes from titles, ids,
    packet-id shapes, or a worker's diff (all explicitly prohibited) — the
    runtime that OWNS the target workspace declares them, exactly as it already
    declares that workspace's writable paths.

    ``lane_key`` is the caller's stable handle for this lane; ``depends_on``
    names other lanes by their ``lane_key``. The compiler resolves those keys
    to canonical gap keys and then to real node ids — a caller never supplies a
    node id or a packet id, so a lane declaration can never mint identity.

    ``writable_path_scope`` is this lane's own authority. An EMPTY list is
    meaningful and legal: it declares a zero-write lane (the independent
    verifier), which materializes a Task whose every diff is out of scope.
    ``None`` is NOT permitted here — a lane that declares no authority is a
    caller error, and the compiler fails closed rather than materializing a
    Task no diff can satisfy.
    """

    lane_key: str = ""
    title: str = ""
    writable_path_scope: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    # Optional semantic identity for this lane (e.g. an implementation lane vs
    # the independent-verification lane). Carried onto the node for read
    # surfaces and the verifier contract; never used to DERIVE authority.
    semantic_label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ObjectiveLane:
        return _from_dict(cls, d)


@dataclass
class ObjectivePlanRecord:
    """One immutable VERSION of an objective's plan.

    ``objective_id`` is stable across versions; each revision appends a new
    record with ``graph_version + 1`` and ``supersedes_plan_record_id`` set,
    and the prior version's status flips to SUPERSEDED (record preserved).

    This record carries the full linkage contract as first-class fields.
    Approval-record ids live ONLY here (``approval_request_ids``) — never
    stuffed into a WorkPacket linkage field of a different type.
    """

    plan_record_id: str = field(default_factory=lambda: _new_id("opr"))
    # REFERENCES the canonical Objective — a GoalRegistry Goal(OBJECTIVE) id
    # (``goal-<hex>``). This record never mints a rival objective identity;
    # an empty value means the plan is not yet bound and may not be compiled.
    objective_id: str = ""
    graph_version: int = 1
    supersedes_plan_record_id: str = ""
    status: str = ObjectivePlanStatus.DRAFT.value
    # Linkage contract (forward navigation)
    conversation_id: str = ""
    message_id: str = ""
    client_message_id: str = ""
    intent_id: str = ""
    grounding_snapshot_id: str = ""
    current_state_id: str = ""
    desired_state_id: str = ""
    gap_model_id: str = ""
    workpacket_ids: list[str] = field(default_factory=list)
    approval_request_ids: list[str] = field(default_factory=list)
    # Graph body
    objective_text: str = ""
    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, str]] = field(default_factory=list)
    lanes: list[str] = field(default_factory=list)
    decision_log: list[dict[str, Any]] = field(default_factory=list)
    # Wave 1 §4/§6/§7/§8/§10 — first-class typed context (never hidden in
    # evidence blobs): scope, fractal decomposition record, archetype policy,
    # development profile, and the latest readiness assessment.
    work_scope: dict[str, Any] = field(default_factory=dict)
    planning_scale: str = ""
    decomposition: dict[str, Any] = field(default_factory=dict)
    archetype_resolution: dict[str, Any] = field(default_factory=dict)
    development_profile: dict[str, Any] = field(default_factory=dict)
    readiness_assessment: dict[str, Any] = field(default_factory=dict)
    deterministic: bool = True
    enhancement_used: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ObjectivePlanRecord:
        return _from_dict(cls, d)

    def node_objects(self) -> list[ObjectivePlanNode]:
        return [ObjectivePlanNode.from_dict(n) for n in self.nodes]

    def node_by_id(self, node_id: str) -> ObjectivePlanNode | None:
        for n in self.nodes:
            if n.get("node_id") == node_id:
                return ObjectivePlanNode.from_dict(n)
        return None

    def linkage(self) -> dict[str, Any]:
        """The flat linkage-contract dict surfaced to the Cockpit."""
        return {
            "plan_record_id": self.plan_record_id,
            "objective_id": self.objective_id,
            "graph_version": self.graph_version,
            "conversation_id": self.conversation_id,
            "message_id": self.message_id,
            "intent_id": self.intent_id,
            "grounding_snapshot_id": self.grounding_snapshot_id,
            "current_state_id": self.current_state_id,
            "desired_state_id": self.desired_state_id,
            "gap_model_id": self.gap_model_id,
            "workpacket_ids": list(self.workpacket_ids),
            "approval_request_ids": list(self.approval_request_ids),
        }


# ── Revision edits ───────────────────────────────────────────────────────────

_EDIT_OPS = ("remove_node", "add_node", "add_edge", "remove_edge", "retitle", "move_lane")


@dataclass
class RevisionEditSet:
    """A validated set of edits one revision message applies to a plan."""

    edits: list[dict[str, Any]] = field(default_factory=list)
    parsed_by: str = "deterministic"  # deterministic | llm
    unmatched_phrases: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> RevisionEditSet:
        return _from_dict(cls, d)

    def validate_ops(self) -> list[str]:
        """Return a list of op-validation errors (empty when clean)."""
        errors: list[str] = []
        for e in self.edits:
            op = e.get("op", "")
            if op not in _EDIT_OPS:
                errors.append(f"unknown edit op: {op!r}")
        return errors


NODE_KINDS = _NODE_KINDS
EDIT_OPS = _EDIT_OPS

__all__ = [
    "EDIT_OPS",
    "NODE_KINDS",
    "CurrentStateRecord",
    "DesiredStateRecord",
    "GapAssessmentSnapshot",
    "GroundingSnapshot",
    "IntentAssessment",
    "IntentAssessmentState",
    "ObjectivePlanNode",
    "ObjectivePlanRecord",
    "ObjectivePlanStatus",
    "PlanningSession",
    "PlanningStageMarker",
    "RevisionEditSet",
]
