"""RealityTemplate metamodel types — the L2 ontology of provable patterns.

Implements the chain compiled in ``docs/REALITY_TEMPLATE_GRAPH.md``::

    Primitive → Invariant → Variable → RealityTemplate → TemplateInstance
        → TemplateGraph / TemplateEdge → CapabilityRevision → (better) RealityTemplate

A RealityTemplate is ``f(invariants, variables, context)`` — a named, versioned,
provable pattern. It is compiled ONCE from a pattern that executed with proof,
then instantiated many times. All tenant/projection specificity enters through
declared variables; template bodies stay instance-free (Instance Context Law at
the template layer).

The six essentialism rules from the ontology doc become code-level enforcement
here where feasible:
  1. One canonical home — this module is that home for the metamodel types.
  2. No speculative templates — a template proven beyond CANDIDATE requires a
     source instance (RealityTemplate ``_essentialism_rules`` validator).
  3. N≥2 before extraction — ``extraction_enabled`` requires ``instance_count`` ≥ 2.
  4. Instance values never in template bodies — declared invariants/variables and
     the proof requirement are scanned for known instance-literal patterns.
  5. Proof gates edges — a TemplateEdge's producer must carry proof; a
     TemplateGraph rejects an edge whose producer instance is unproven.
  6. Revision is append-only — CapabilityRevision versions are immutable and cite
     the instance proofs that motivated them; the registry enforces monotonic,
     non-overwriting revision history.

This is a substrate L2 metamodel module. It MUST NOT import from ``projections/``,
``transports/``, ``services/``, or ``substrate/state/business/``. It defines the
RULES OF templated worlds, never the CONTENTS of one world.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─── Instance-literal detection (essentialism rule 4) ────────────────────────
# Template BODIES (invariants, variable NAMES, proof requirement text) must never
# hardcode a tenant / node / brand / product literal. Those bind through variable
# VALUES at instantiation, never into the template definition. This is the
# template-layer projection of the Instance Context Law.
#
# Which concrete strings ARE instance identity (a founder name, a device
# hostname, a brand) is itself INSTANCE CONTEXT — so this substrate module holds
# NO such literal. The denylist is injected at runtime from BIS/config via
# ``configure_instance_denylist()``; it defaults to empty. The registry loader
# seeds it from the instance profile; tests seed it explicitly. A boundary that
# also treats '_' as a separator catches underscore-joined leaks (e.g.
# '<founder>_column'), which a plain ``\b`` would miss ('_' is a word char).

_instance_denylist: tuple[str, ...] = ()
_instance_literal_re: re.Pattern[str] | None = None


def configure_instance_denylist(tokens: tuple[str, ...] | list[str]) -> None:
    """Set the instance-identity tokens that may not appear in a template body.

    Called at runtime with values loaded from the instance profile (BIS/env/
    config) — never hardcoded here. Passing an empty sequence disables scanning
    (the substrate default: identity-agnostic).
    """
    global _instance_denylist, _instance_literal_re
    _instance_denylist = tuple(t for t in tokens if t)
    if _instance_denylist:
        _instance_literal_re = re.compile(
            "|".join(rf"(?<![a-z0-9]){re.escape(tok)}(?![a-z0-9])" for tok in _instance_denylist),
            re.IGNORECASE,
        )
    else:
        _instance_literal_re = None


def _scan_instance_literal(text: str, where: str) -> None:
    """Raise ``ValueError`` if ``text`` embeds a configured instance literal.

    Used by template-body validators. Instance values are legitimate only as
    variable BINDINGS on a :class:`TemplateInstance`, never inside a template
    definition body. No-op until a denylist is configured for the running
    instance (the substrate module ships identity-free).
    """
    if _instance_literal_re is None:
        return
    match = _instance_literal_re.search(text or "")
    if match:
        raise ValueError(
            f"instance literal {match.group(0)!r} found in {where}; instance "
            "values bind through variables at instantiation, never in a "
            "template body (essentialism rule 4)"
        )


# ─── Status ──────────────────────────────────────────────────────────────────


class RealityTemplateStatus(str, Enum):
    """Lifecycle of a provable pattern.

    Distinct from ``substrate.organism.template_registry.TemplateStatus`` (the
    runtime executable-action-pattern store with RAW/APPROVED/PROMOTED). This is
    the METAMODEL maturity of a RealityTemplate.
    """

    # A pattern named but not yet proven with a real executed instance. Allowed
    # to exist with zero instances — the ONLY status for which that is legal.
    CANDIDATE = "CANDIDATE"
    # Exactly one real instance executed with proof. A RECORD, not an abstraction.
    PROVEN_1_INSTANCE = "PROVEN_1_INSTANCE"
    # Two or more real instances — extraction into an abstraction is now allowed.
    PROVEN_N_INSTANCES = "PROVEN_N_INSTANCES"

    @property
    def is_proven(self) -> bool:
        return self in (
            RealityTemplateStatus.PROVEN_1_INSTANCE,
            RealityTemplateStatus.PROVEN_N_INSTANCES,
        )


# ─── Invariant / Variable ────────────────────────────────────────────────────


class TemplateInvariant(BaseModel):
    """What must NOT change across instances — the contract making proof
    transferable. An invariant without a testable assertion is a wish."""

    statement: str = Field(min_length=1, description="Testable 'must hold' assertion.")
    # Optional pointer to the test / gate that pins this invariant to reality.
    verified_by: str | None = Field(
        default=None,
        description="Test id, gate name, or proof pointer that enforces this.",
    )

    @field_validator("statement")
    @classmethod
    def _no_instance_literal(cls, v: str) -> str:
        _scan_instance_literal(v, "invariant statement")
        return v


class TemplateVariable(BaseModel):
    """A declared, typed slot for instantiation.

    ALL tenant/projection specificity enters HERE — this is the Instance Context
    Law at the template layer. The variable NAME and TYPE are part of the
    template body (instance-free); the variable VALUE is supplied per instance.
    """

    name: str = Field(min_length=1, description="Slot name, e.g. 'tenant_id'.")
    var_type: str = Field(
        default="str",
        description="Declared type of the binding value (informational).",
    )
    description: str = ""
    required: bool = True

    @field_validator("name")
    @classmethod
    def _name_is_instance_free(cls, v: str) -> str:
        # A variable NAME is a slot label ('tenant_id'), never a bound value.
        _scan_instance_literal(v, "variable name")
        return v


# ─── ProofRequirement (template layer) ───────────────────────────────────────


class TemplateProofRequirement(BaseModel):
    """What a template demands before an instance may be marked complete.

    Named distinctly from ``substrate.organism.domain_registry.ProofRequirement``
    (the per-WorkPacket execution-policy dataclass) — this is the template-layer
    proof CONTRACT: envelope ids, server-truth reads, row verification, gate
    output. No proof, no completion; without proof an instance cannot feed edges.
    """

    description: str = Field(min_length=1)
    # The concrete artifacts an instance must produce to satisfy the requirement.
    required_artifacts: list[str] = Field(default_factory=list)

    @field_validator("description")
    @classmethod
    def _no_instance_literal(cls, v: str) -> str:
        _scan_instance_literal(v, "proof requirement description")
        return v


# ─── RealityTemplate ─────────────────────────────────────────────────────────


class RealityTemplate(BaseModel):
    """A named, versioned, provable pattern: primitives composed under invariants
    with declared variables. ``f(invariants, variables, context)``.

    Enforced at construction:
      - a template MUST declare invariants, variables, and a proof requirement;
      - a PROVEN status REQUIRES a ``source_instance`` (no speculative proof);
      - ``extraction_enabled`` (code-level abstraction marker) REQUIRES
        ``instance_count`` ≥ 2 (the N≥2 rule);
      - status and ``instance_count`` are consistent (CANDIDATE ⇒ may be 0;
        PROVEN_1_INSTANCE ⇒ ≥1; PROVEN_N_INSTANCES ⇒ ≥2);
      - no instance literal leaks into any body field.
    """

    id: str = Field(
        min_length=1, description="Stable template id, e.g. 'RT-GOVERNED-PROPOSAL-LOOP'."
    )
    version: int = Field(default=1, ge=1)
    status: RealityTemplateStatus = RealityTemplateStatus.CANDIDATE
    description: str = ""

    # The pattern body — all instance-free.
    primitives: list[str] = Field(
        default_factory=list,
        description="Substrate primitives composed (Signal/Operation/Approval/Proof/...).",
    )
    invariants: list[TemplateInvariant] = Field(default_factory=list)
    variables: list[TemplateVariable] = Field(default_factory=list)
    proof_requirement: TemplateProofRequirement | None = None

    # Provenance — a projection/instance REFERENCE (e.g. 'eos/<tenant>'), a
    # pointer, never the person's identity. Present only for PROVEN templates.
    source_instance: str | None = None
    proof_pointer: str | None = Field(
        default=None,
        description="PR / audit doc that proves the source instance.",
    )
    instance_count: int = Field(default=0, ge=0)

    # Code-level abstraction marker. May only be true once N≥2 real instances
    # exist — mirrors the projection-read-surface 'do not extract at N=1' rule.
    extraction_enabled: bool = False

    next_instances: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)

    @field_validator("description")
    @classmethod
    def _description_instance_free(cls, v: str) -> str:
        _scan_instance_literal(v, "template description")
        return v

    @field_validator("primitives")
    @classmethod
    def _primitives_instance_free(cls, v: list[str]) -> list[str]:
        for p in v:
            _scan_instance_literal(p, "template primitive")
        return v

    @model_validator(mode="after")
    def _essentialism_rules(self) -> RealityTemplate:
        # Rule: a template must declare invariants + variables + a proof requirement.
        if not self.invariants:
            raise ValueError(f"{self.id}: template must declare at least one invariant")
        if not self.variables:
            raise ValueError(f"{self.id}: template must declare at least one variable")
        if self.proof_requirement is None:
            raise ValueError(f"{self.id}: template must declare a proof requirement")

        # Rule 2: no speculative proof — a proven template needs a source instance.
        if self.status.is_proven and not self.source_instance:
            raise ValueError(
                f"{self.id}: status {self.status.value} requires a source_instance "
                "(no speculative templates — proof comes from a real executed instance)"
            )

        # Status ↔ instance_count coherence.
        if self.status is RealityTemplateStatus.PROVEN_1_INSTANCE and self.instance_count < 1:
            raise ValueError(f"{self.id}: PROVEN_1_INSTANCE requires instance_count >= 1")
        if self.status is RealityTemplateStatus.PROVEN_N_INSTANCES and self.instance_count < 2:
            raise ValueError(f"{self.id}: PROVEN_N_INSTANCES requires instance_count >= 2")

        # Rule 3: N≥2 before extraction.
        if self.extraction_enabled and self.instance_count < 2:
            raise ValueError(
                f"{self.id}: extraction_enabled requires instance_count >= 2 "
                "(code-level abstraction demands a second real instance — the N>=2 rule)"
            )
        return self


# ─── TemplateInstance ────────────────────────────────────────────────────────


class TemplateInstance(BaseModel):
    """One binding of a RealityTemplate's variables for one tenant+projection,
    with its own proof record. No proof → not complete → cannot feed edges."""

    id: UUID = Field(default_factory=uuid4)
    template_id: str = Field(min_length=1)
    # The projection/tenant reference this instance binds for, e.g. 'eos/<tenant>'.
    instance_ref: str = Field(min_length=1)
    # Variable bindings: this is the ONLY place instance values legitimately live.
    bindings: dict[str, Any] = Field(default_factory=dict)

    # Proof record — presence gates edge participation.
    proof_pointer: str | None = None
    proof_satisfied: bool = False
    created_at: datetime = Field(default_factory=_now)

    @property
    def is_proven(self) -> bool:
        return self.proof_satisfied and bool(self.proof_pointer)


# ─── TemplateEdge / TemplateGraph ────────────────────────────────────────────


class TemplateEdge(BaseModel):
    """A typed connection ``(producer.proof_field) → (consumer.variable)``.

    Edges carry proof, never raw trust. The producer instance must be proven for
    the edge to be traversable — an unproven producer starves its consumers
    (fail-closed propagation), enforced by :class:`TemplateGraph`.
    """

    producer_instance_id: UUID
    producer_proof_field: str = Field(min_length=1)
    consumer_instance_id: UUID
    consumer_variable: str = Field(min_length=1)

    @model_validator(mode="after")
    def _no_self_edge(self) -> TemplateEdge:
        if self.producer_instance_id == self.consumer_instance_id:
            raise ValueError("a TemplateEdge may not connect an instance to itself (DAG rule)")
        return self


class TemplateGraph(BaseModel):
    """A DAG of TemplateInstances; workflows ARE TemplateGraphs.

    Cycles are forbidden (revision loops go through CapabilityRevision, not
    back-edges). Proof gates edges: adding an edge whose producer is unproven is
    rejected. Both invariants are enforced by :meth:`validate`, which the
    registry calls before accepting a graph.
    """

    id: str = Field(default_factory=lambda: f"tg-{uuid4().hex[:8]}")
    instances: list[TemplateInstance] = Field(default_factory=list)
    edges: list[TemplateEdge] = Field(default_factory=list)

    def _instance_index(self) -> dict[UUID, TemplateInstance]:
        return {inst.id: inst for inst in self.instances}

    def validate_graph(self) -> None:
        """Enforce the DAG + proof-gates-edges invariants. Raises ``ValueError``
        on the first violation."""
        index = self._instance_index()

        # Every edge endpoint must be a known instance.
        for edge in self.edges:
            if edge.producer_instance_id not in index:
                raise ValueError(f"edge producer {edge.producer_instance_id} not in graph")
            if edge.consumer_instance_id not in index:
                raise ValueError(f"edge consumer {edge.consumer_instance_id} not in graph")
            # Rule 5: proof gates edges — producer must be proven.
            producer = index[edge.producer_instance_id]
            if not producer.is_proven:
                raise ValueError(
                    f"edge from unproven producer {producer.instance_ref!r} is forbidden "
                    "(proof gates edges — fail-closed propagation)"
                )

        # DAG check — no cycles.
        self._assert_acyclic()

    def _assert_acyclic(self) -> None:
        # Kahn's algorithm; if not all nodes are emitted, a cycle exists.
        adjacency: dict[UUID, list[UUID]] = {inst.id: [] for inst in self.instances}
        indegree: dict[UUID, int] = {inst.id: 0 for inst in self.instances}
        for edge in self.edges:
            adjacency[edge.producer_instance_id].append(edge.consumer_instance_id)
            indegree[edge.consumer_instance_id] += 1

        queue = [node for node, deg in indegree.items() if deg == 0]
        emitted = 0
        while queue:
            node = queue.pop()
            emitted += 1
            for nxt in adjacency[node]:
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    queue.append(nxt)

        if emitted != len(self.instances):
            raise ValueError(
                "TemplateGraph contains a cycle — workflows are DAGs; revision "
                "loops go through CapabilityRevision, not back-edges"
            )


# ─── CapabilityRevision ──────────────────────────────────────────────────────


class CapabilityRevision(BaseModel):
    """The learning edge: an executed instance's proof + defects motivate a new,
    higher template version. Templates improve ONLY through executed instances.

    Revisions are append-only and immutable (``frozen``). Each cites the instance
    proof(s) that motivated it and records the version transition. The #197/#198
    defects becoming standard template invariants is the canonical example.
    """

    model_config = {"frozen": True}

    template_id: str = Field(min_length=1)
    from_version: int = Field(ge=1)
    to_version: int = Field(ge=2)
    # What changed and why — a sharpened invariant, an added variable, a gotcha.
    change_summary: str = Field(min_length=1)
    # Proof pointers of the instance(s) that motivated the revision.
    motivating_proofs: list[str] = Field(default_factory=list, min_length=1)
    created_at: datetime = Field(default_factory=_now)

    @model_validator(mode="after")
    def _forward_only(self) -> CapabilityRevision:
        if self.to_version <= self.from_version:
            raise ValueError(
                f"revision must advance version ({self.from_version} -> "
                f"{self.to_version}); revisions are forward-only and append-only"
            )
        return self


__all__ = [
    "RealityTemplateStatus",
    "TemplateInvariant",
    "TemplateVariable",
    "TemplateProofRequirement",
    "RealityTemplate",
    "TemplateInstance",
    "TemplateEdge",
    "TemplateGraph",
    "CapabilityRevision",
    "configure_instance_denylist",
]
