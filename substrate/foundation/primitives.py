"""Layer 0 ontological primitives — the irreducible types of existence in the substrate.

OntologicalCategory and CausalRole are re-exported from substrate.types (canonical).
TemporalMode is also in substrate.types (identical definition).
Modality here is DISTINCT from substrate.types.Modality (signal modality: TEXT/VOICE/IMAGE).
This Modality represents modal logic status (ACTUAL/POSSIBLE/NECESSARY/etc.).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

# Re-export canonical versions from substrate.types
from substrate.types import (  # noqa: F401
    CausalRole,
    OntologicalCategory,
    TemporalMode,
)

# NOTE: substrate.types.Modality is signal modality (TEXT, VOICE, IMAGE, MULTIMODAL).
# This Modality is ontological modal status — intentionally distinct.
from substrate.types import Modality as SignalModality  # noqa: F401


class Modality(str, Enum):
    """Modal status of a proposition or state (ontological, not signal modality)."""

    ACTUAL = "actual"
    POSSIBLE = "possible"
    NECESSARY = "necessary"
    IMPOSSIBLE = "impossible"
    CONTINGENT = "contingent"


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
