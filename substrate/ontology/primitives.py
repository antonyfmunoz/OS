"""Ontology primitives — the foundational classification system for UMH.

PrimitiveType, OntologicalCategory, and PrimitiveObservation are defined
in substrate.types (the single type authority). This module re-exports
them and adds ontology-specific utilities.
"""

from __future__ import annotations

from substrate.types import (
    OntologicalCategory,
    PrimitiveObservation,
    PrimitiveType,
)

__all__ = ["PrimitiveType", "OntologicalCategory", "PrimitiveObservation"]
