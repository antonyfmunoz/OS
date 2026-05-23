"""Ontology primitives — the computational physics of UMH.

These are not metadata descriptions. They are enacted constraints
that govern the system the way physics governs reality.

10 primitives, 8 categories, 10 relationship types, 4 temporal modes, 5 causal roles.
"""

from substrate.types import (
    CausalRole,
    OntologicalCategory,
    PrimitiveObservation,
    PrimitiveType,
    RelationshipType,
    TemporalMode,
)

__all__ = [
    "CausalRole",
    "OntologicalCategory",
    "PrimitiveObservation",
    "PrimitiveType",
    "RelationshipType",
    "TemporalMode",
]
