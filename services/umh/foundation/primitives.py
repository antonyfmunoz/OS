"""Layer 0 ontological primitives — the irreducible types of existence in the substrate."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class OntologicalCategory(str, Enum):
    """The fundamental categories of being in the substrate."""

    ENTITY = "entity"
    RELATION = "relation"
    EVENT = "event"
    PROPERTY = "property"
    PROCESS = "process"
    STATE = "state"
    CONSTRAINT = "constraint"
    BOUNDARY = "boundary"


class TemporalMode(str, Enum):
    """How a primitive relates to time."""

    INSTANTANEOUS = "instantaneous"
    DURATIVE = "durative"
    ATEMPORAL = "atemporal"
    PERIODIC = "periodic"


class Modality(str, Enum):
    """Modal status of a proposition or state."""

    ACTUAL = "actual"
    POSSIBLE = "possible"
    NECESSARY = "necessary"
    IMPOSSIBLE = "impossible"
    CONTINGENT = "contingent"


class CausalRole(str, Enum):
    """Role in causal chains."""

    CAUSE = "cause"
    EFFECT = "effect"
    CONDITION = "condition"
    PREVENTION = "prevention"
    MAINTENANCE = "maintenance"


class OntologicalPrimitive(BaseModel):
    """A single irreducible element in the substrate's type system."""

    id: UUID = Field(default_factory=uuid4)
    category: OntologicalCategory
    temporal_mode: TemporalMode = TemporalMode.DURATIVE
    modality: Modality = Modality.ACTUAL
    causal_role: CausalRole | None = None
    label: str = Field(max_length=120)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    def is_temporal(self) -> bool:
        return self.temporal_mode != TemporalMode.ATEMPORAL

    def is_actual(self) -> bool:
        return self.modality == Modality.ACTUAL


class Relation(BaseModel):
    """A typed connection between two primitives."""

    id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    target_id: UUID
    relation_type: str = Field(max_length=80)
    strength: float = Field(default=1.0, ge=0.0, le=1.0)
    bidirectional: bool = False
    temporal_mode: TemporalMode = TemporalMode.DURATIVE
    metadata: dict[str, Any] = Field(default_factory=dict)


class CompositionEdge(BaseModel):
    """Expresses that one primitive is composed of or contains another."""

    parent_id: UUID
    child_id: UUID
    composition_type: str = Field(default="part_of", max_length=60)
    ordering: int | None = None
