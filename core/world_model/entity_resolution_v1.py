"""Entity Resolution v1 for the UMH substrate layer.

Defines candidate entities, relationships, and resolution
confidence for the world-model candidate system. All entities
are candidates — never canonical truth — until governance
promotes them.

UMH substrate subsystem. Phase 96.8X.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CandidateRelationshipType(str, Enum):
    CAUSAL = "causal"
    TEMPORAL = "temporal"
    CONSTRAINT = "constraint"
    DEPENDENCY = "dependency"
    ASSOCIATION = "association"
    HIERARCHY = "hierarchy"
    CONFLICT = "conflict"
    ENABLES = "enables"
    PRODUCES = "produces"
    CONSUMES = "consumes"


class ResolutionConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SPECULATIVE = "speculative"


@dataclass
class EntityAlias:
    """An alternative reference to the same entity."""

    alias: str
    source: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "alias": self.alias,
            "source": self.source,
            "confidence": self.confidence,
        }


@dataclass
class EntityReference:
    """A reference to an entity from an external source."""

    reference_id: str
    reference_type: str
    source_trace_id: str = ""
    source_interpretation_id: str = ""
    source_observation_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference_id": self.reference_id,
            "reference_type": self.reference_type,
            "source_trace_id": self.source_trace_id,
            "source_interpretation_id": self.source_interpretation_id,
            "source_observation_id": self.source_observation_id,
        }


@dataclass
class RelationshipReference:
    """A reference linking a relationship to its evidence."""

    reference_id: str
    relationship_type: str
    source_observation_ids: list[str] = field(default_factory=list)
    source_interpretation_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference_id": self.reference_id,
            "relationship_type": self.relationship_type,
            "source_observation_ids": self.source_observation_ids,
            "source_interpretation_id": self.source_interpretation_id,
        }


@dataclass
class CandidateEntity:
    """A candidate entity in the world model — NOT canonical truth."""

    entity_id: str
    entity_type: str
    label: str
    confidence: float
    source_observation_ids: list[str] = field(default_factory=list)
    source_interpretation_ids: list[str] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    aliases: list[EntityAlias] = field(default_factory=list)
    references: list[EntityReference] = field(default_factory=list)
    resolution_confidence: ResolutionConfidence = ResolutionConfidence.MEDIUM
    uncertainty_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "label": self.label,
            "confidence": self.confidence,
            "source_observation_ids": self.source_observation_ids,
            "source_interpretation_ids": self.source_interpretation_ids,
            "source_trace_ids": self.source_trace_ids,
            "aliases": [a.to_dict() for a in self.aliases],
            "references": [r.to_dict() for r in self.references],
            "resolution_confidence": self.resolution_confidence.value,
            "uncertainty_notes": self.uncertainty_notes,
        }


@dataclass
class CandidateRelationship:
    """A candidate relationship between entities — NOT canonical truth."""

    relationship_id: str
    from_entity_id: str
    to_entity_id: str
    relationship_type: str
    confidence: float
    evidence_observation_ids: list[str] = field(default_factory=list)
    references: list[RelationshipReference] = field(default_factory=list)
    is_causal: bool = False
    is_temporal: bool = False
    is_constraint: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "relationship_id": self.relationship_id,
            "from_entity_id": self.from_entity_id,
            "to_entity_id": self.to_entity_id,
            "relationship_type": self.relationship_type,
            "confidence": self.confidence,
            "evidence_observation_ids": self.evidence_observation_ids,
            "references": [r.to_dict() for r in self.references],
            "is_causal": self.is_causal,
            "is_temporal": self.is_temporal,
            "is_constraint": self.is_constraint,
        }
