"""Domain bridge protocol and projection dataclass.

A DomainBridge maps ontology-level PrimitiveObservations into
domain-typed DomainProjections. Each projection is a separate
memory entry that back-references its source observation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from core.ontology.primitive_decomposition_v1 import PrimitiveObservation


@runtime_checkable
class DomainBridge(Protocol):
    """Protocol for domain bridge implementations."""

    @property
    def domain_id(self) -> str:
        """Unique domain identifier (e.g., 'business')."""
        ...

    def bridge(self, observation: PrimitiveObservation) -> DomainProjection | None:
        """Map an ontology observation to a domain projection.

        Returns None if the observation has no mapping in this domain.
        """
        ...

    def describes(self) -> str:
        """Human-readable description of this bridge."""
        ...


@dataclass
class DomainProjection:
    """A domain-typed projection of an ontology observation.

    Persisted as a separate memory entry alongside the source
    observation. Back-references the observation via
    ontology_observation_ref.
    """

    projection_id: str
    domain_id: str
    domain_primitive_type: str
    label: str
    description: str
    properties: dict[str, Any]
    ontology_observation_ref: str
    confidence: float
    evidence: str
    authority_tier: int = 5

    def to_dict(self) -> dict[str, Any]:
        return {
            "projection_id": self.projection_id,
            "domain_id": self.domain_id,
            "domain_primitive_type": self.domain_primitive_type,
            "label": self.label,
            "description": self.description,
            "properties": self.properties,
            "ontology_observation_ref": self.ontology_observation_ref,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "authority_tier": self.authority_tier,
        }


def make_projection_id() -> str:
    return f"proj-{uuid.uuid4().hex[:12]}"
