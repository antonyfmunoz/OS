"""Primitive Decomposition v1 for the UMH substrate layer.

Decomposes observations into the substrate's primitive ontology.
Every observation is expressed as a set of typed primitives with
explicit relationships, confidence scores, and uncertainty markers.

UMH substrate subsystem. Phase 96.8W.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PrimitiveType(str, Enum):
    STATE = "state"
    CHANGE = "change"
    CONSTRAINT = "constraint"
    RESOURCE = "resource"
    SIGNAL = "signal"
    ACTION = "action"
    OUTCOME = "outcome"
    FEEDBACK = "feedback"
    GOAL = "goal"
    TIME = "time"


REQUIRED_PRIMITIVE_TYPES = frozenset(PrimitiveType)


class RelationshipType(str, Enum):
    CAUSES = "causes"
    CONSTRAINS = "constrains"
    ENABLES = "enables"
    REQUIRES = "requires"
    PRECEDES = "precedes"
    FOLLOWS = "follows"
    PRODUCES = "produces"
    CONSUMES = "consumes"
    MEASURES = "measures"
    CONFLICTS_WITH = "conflicts_with"


@dataclass
class PrimitiveObservation:
    """A single observed primitive."""

    observation_id: str
    primitive_type: PrimitiveType
    label: str
    description: str
    confidence: float
    source_reference: str = ""
    evidence: str = ""
    is_inferred: bool = False
    authority_tier: int = 5

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "primitive_type": self.primitive_type.value,
            "label": self.label,
            "description": self.description,
            "confidence": self.confidence,
            "source_reference": self.source_reference,
            "evidence": self.evidence,
            "is_inferred": self.is_inferred,
            "authority_tier": self.authority_tier,
        }


@dataclass
class PrimitiveRelationship:
    """A directed relationship between two primitives."""

    from_observation_id: str
    to_observation_id: str
    relationship_type: RelationshipType
    confidence: float
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_observation_id": self.from_observation_id,
            "to_observation_id": self.to_observation_id,
            "relationship_type": self.relationship_type.value,
            "confidence": self.confidence,
            "description": self.description,
        }


@dataclass
class DecompositionResult:
    """Complete primitive decomposition of an observation."""

    decomposition_id: str
    source_content_hash: str
    observations: list[PrimitiveObservation] = field(default_factory=list)
    relationships: list[PrimitiveRelationship] = field(default_factory=list)
    decomposition_confidence: float = 0.0
    unsupported_assumptions: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    explicit_unknowns: list[str] = field(default_factory=list)
    primitive_type_coverage: dict[str, int] = field(default_factory=dict)

    def compute_coverage(self) -> dict[str, int]:
        coverage: dict[str, int] = {}
        for obs in self.observations:
            ptype = obs.primitive_type.value
            coverage[ptype] = coverage.get(ptype, 0) + 1
        self.primitive_type_coverage = coverage
        return coverage

    def to_dict(self) -> dict[str, Any]:
        return {
            "decomposition_id": self.decomposition_id,
            "source_content_hash": self.source_content_hash,
            "observations": [o.to_dict() for o in self.observations],
            "relationships": [r.to_dict() for r in self.relationships],
            "decomposition_confidence": self.decomposition_confidence,
            "unsupported_assumptions": self.unsupported_assumptions,
            "missing_information": self.missing_information,
            "explicit_unknowns": self.explicit_unknowns,
            "primitive_type_coverage": self.primitive_type_coverage,
        }
