"""Canonical ingestion pipeline — substrate.execution.ingestion.

Re-exports the GenericIngestionOrchestrator and its stage contracts
from the implementation at substrate.understanding.perception.orchestrator.

Usage:
    from substrate.execution.ingestion import IngestionPipeline, Source
    pipeline = IngestionPipeline()
    result = pipeline.ingest(source)
"""

from substrate.understanding.perception.orchestrator import (
    GenericIngestionOrchestrator as IngestionPipeline,
    IngestionResult,
    InterpretationResult,
    MemoryWrite,
    QueryProof,
    Signal,
    WorldUpdate,
)
from substrate.understanding.perception.source import RawContent, Source
from substrate.understanding.ontology.primitive_decomposition_v1 import (
    DecompositionResult,
    PrimitiveObservation,
    PrimitiveType,
    RelationshipType,
)
from substrate.understanding.domains.contract import DomainBridge, DomainProjection

__all__ = [
    "IngestionPipeline",
    "IngestionResult",
    "InterpretationResult",
    "MemoryWrite",
    "QueryProof",
    "Signal",
    "WorldUpdate",
    "RawContent",
    "Source",
    "DecompositionResult",
    "PrimitiveObservation",
    "PrimitiveType",
    "RelationshipType",
    "DomainBridge",
    "DomainProjection",
]
