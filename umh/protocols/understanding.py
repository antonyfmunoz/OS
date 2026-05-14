"""UMH Protocol — Understanding Layer (Layer 3).

Covers perception (§9.1), interpretation (§9.2), domain system (§9.5),
and primitive mapping (§6.4).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from .common import (
    Benchmark,
    CapabilityRef,
    Constraint,
    EnvironmentRef,
    EvidenceRef,
    FailureMode,
    PrimitiveType,
    RelationshipType,
    SignalModality,
    Slot,
    TemplateRef,
    WorkflowRef,
)


# ---------------------------------------------------------------------------
# §9.1 — Signal (Perception output)
# ---------------------------------------------------------------------------


class Signal(BaseModel):
    """Raw or structured input from any source. Defined in canonical synthesis §9.1."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    signal_id: str
    modality: SignalModality
    source: str
    content: Any
    context: dict[str, Any] = {}
    timestamp: int
    environment: EnvironmentRef | None = None
    confidence: float
    metadata: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# §9.2 — Interpretation
# ---------------------------------------------------------------------------


class IntentCandidate(BaseModel):
    """A possible intent extracted from a signal. Referenced in §9.2."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    intent_id: str
    description: str
    confidence: float
    domain: str = ""


class Goal(BaseModel):
    """An inferred goal. Referenced in §9.2 and §10.1."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    goal_id: str
    description: str
    priority: float = 0.5
    domain: str = ""


class Entity(BaseModel):
    """An extracted entity from interpretation. Referenced in §9.2."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    entity_id: str
    type: str
    name: str
    attributes: dict[str, Any] = {}


class InterpretedSignal(BaseModel):
    """Structured meaning extracted from a signal. Defined in canonical synthesis §9.2."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    signal_id: str
    intent_candidates: list[IntentCandidate] = []
    extracted_entities: list[Entity] = []
    extracted_constraints: list[Constraint] = []
    inferred_goals: list[Goal] = []
    ambiguity_score: float
    risk_score: float
    confidence: float
    explanation: str


# ---------------------------------------------------------------------------
# §9.5 — Domain System
# ---------------------------------------------------------------------------


class DomainLaw(BaseModel):
    """A law governing a specific domain. Referenced in §9.5."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    law_id: str
    name: str
    description: str
    domain: str


class SlotSpec(BaseModel):
    """Slot specification for a domain. Referenced in §9.5."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    slot_id: str
    name: str
    type: str = "string"
    required: bool = True
    description: str = ""


class EntityType(BaseModel):
    """Entity type common to a domain. Referenced in §9.5."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    type_id: str
    name: str
    description: str = ""


class DomainMap(BaseModel):
    """Domain organization map. Defined in canonical synthesis §9.5."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    domain_id: str
    name: str
    subdomains: list[str] = []
    common_entities: list[EntityType] = []
    common_workflows: list[WorkflowRef] = []
    common_constraints: list[Constraint] = []
    required_slots: list[SlotSpec] = []
    failure_modes: list[FailureMode] = []
    benchmarks: list[Benchmark] = []
    templates: list[TemplateRef] = []
    capabilities: list[CapabilityRef] = []
    domain_laws: list[DomainLaw] = []


# ---------------------------------------------------------------------------
# §6.4 — Primitive Mapping
# ---------------------------------------------------------------------------


class Primitive(BaseModel):
    """A single ontological primitive instance. Referenced in §6.4."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    primitive_id: str
    type: PrimitiveType
    label: str
    description: str = ""
    evidence: str = ""
    confidence: float = 1.0


class Relationship(BaseModel):
    """A typed edge between primitives. Referenced in §6.4."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    relationship_id: str
    type: RelationshipType
    source_id: str
    target_id: str
    description: str = ""
    confidence: float = 1.0


class PrimitiveMapping(BaseModel):
    """Maps a source artifact to ontological primitives. Defined in canonical synthesis §6.4."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    source_id: str
    source_type: str
    primitives: list[Primitive] = []
    relationships: list[Relationship] = []
    constraints: list[Constraint] = []
    confidence: float
    evidence: list[EvidenceRef] = []
