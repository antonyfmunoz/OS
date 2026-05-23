"""Substrate Candidate Generation v1 — generates ingestion candidates from decomposition.

Classifies each primitive observation as canonical (universal truth)
or instance (time-bound, context-specific fact).

Deterministic. Replay-safe. IDs derived from content hashes.

UMH substrate subsystem.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from substrate.understanding.ontology.primitive_decomposition_v1 import (
    DecompositionResult,
    PrimitiveObservation,
    PrimitiveType,
)


class MemoryType(str, Enum):
    CANONICAL = "canonical"
    INSTANCE = "instance"


class GovernanceState(str, Enum):
    CANDIDATE = "candidate"
    PROMOTED = "promoted"
    REJECTED = "rejected"


@dataclass
class IngestionCandidate:
    """A single memory candidate derived from a primitive observation."""

    candidate_id: str
    source_observation_id: str
    source_decomposition_id: str
    source_document_id: str
    source_content_hash: str
    memory_type: MemoryType
    primitive_type: str
    label: str
    content: str
    confidence: float
    classification_reason: str
    governance_state: GovernanceState = GovernanceState.CANDIDATE
    provenance: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "source_observation_id": self.source_observation_id,
            "source_decomposition_id": self.source_decomposition_id,
            "source_document_id": self.source_document_id,
            "source_content_hash": self.source_content_hash,
            "memory_type": self.memory_type.value,
            "primitive_type": self.primitive_type,
            "label": self.label,
            "content": self.content,
            "confidence": self.confidence,
            "classification_reason": self.classification_reason,
            "governance_state": self.governance_state.value,
            "provenance": self.provenance,
            "timestamp": self.timestamp,
        }


@dataclass
class CandidateSet:
    """Complete set of ingestion candidates from a decomposition."""

    set_id: str
    source_decomposition_id: str
    source_document_id: str
    canonical_candidates: list[IngestionCandidate] = field(default_factory=list)
    instance_candidates: list[IngestionCandidate] = field(default_factory=list)
    total_observations: int = 0
    classified_count: int = 0
    skipped_count: int = 0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "set_id": self.set_id,
            "source_decomposition_id": self.source_decomposition_id,
            "source_document_id": self.source_document_id,
            "canonical_candidates": [c.to_dict() for c in self.canonical_candidates],
            "instance_candidates": [c.to_dict() for c in self.instance_candidates],
            "total_observations": self.total_observations,
            "classified_count": self.classified_count,
            "skipped_count": self.skipped_count,
            "timestamp": self.timestamp,
        }


def _deterministic_id(namespace: str, content: str) -> str:
    h = hashlib.sha256(f"{namespace}:{content}".encode("utf-8")).hexdigest()[:16]
    return f"{namespace}-{h}"


# Canonical: universal truths, frameworks, principles, recurring structures
# Instance: specific events, time-bound facts, contextual details
CANONICAL_TYPES = frozenset(
    {
        PrimitiveType.GOAL,
        PrimitiveType.CONSTRAINT,
        PrimitiveType.RESOURCE,
    }
)

INSTANCE_TYPES = frozenset(
    {
        PrimitiveType.ACTION,
        PrimitiveType.OUTCOME,
        PrimitiveType.SIGNAL,
        PrimitiveType.TIME,
        PrimitiveType.FEEDBACK,
    }
)

CONTEXT_DEPENDENT_TYPES = frozenset(
    {
        PrimitiveType.STATE,
        PrimitiveType.CHANGE,
    }
)


def _classify_memory_type(obs: PrimitiveObservation) -> tuple[MemoryType, str]:
    """Classify an observation as canonical or instance."""
    ptype = obs.primitive_type

    if ptype in CANONICAL_TYPES:
        return MemoryType.CANONICAL, f"{ptype.value} is structurally canonical"

    if ptype in INSTANCE_TYPES:
        return MemoryType.INSTANCE, f"{ptype.value} is contextually instance-bound"

    # Context-dependent: classify by confidence and content patterns
    desc = obs.description.lower()
    universal_markers = ["always", "never", "every", "must", "principle", "framework", "system"]
    instance_markers = ["today", "yesterday", "just", "recently", "once", "at 22", "this"]

    canonical_score = sum(1 for m in universal_markers if m in desc)
    instance_score = sum(1 for m in instance_markers if m in desc)

    if canonical_score > instance_score:
        return MemoryType.CANONICAL, f"{ptype.value} has universal language markers"
    return MemoryType.INSTANCE, f"{ptype.value} has contextual/temporal markers"


def generate_candidates(
    decomposition: DecompositionResult,
    document_id: str,
    min_confidence: float = 0.4,
) -> CandidateSet:
    """Generate canonical and instance candidates from a decomposition result."""
    set_id = _deterministic_id("candset", f"{decomposition.decomposition_id}:{document_id}")

    candidate_set = CandidateSet(
        set_id=set_id,
        source_decomposition_id=decomposition.decomposition_id,
        source_document_id=document_id,
        total_observations=len(decomposition.observations),
    )

    for obs in decomposition.observations:
        if obs.confidence < min_confidence:
            candidate_set.skipped_count += 1
            continue

        memory_type, reason = _classify_memory_type(obs)
        candidate_id = _deterministic_id("cand", f"{set_id}:{obs.observation_id}")

        candidate = IngestionCandidate(
            candidate_id=candidate_id,
            source_observation_id=obs.observation_id,
            source_decomposition_id=decomposition.decomposition_id,
            source_document_id=document_id,
            source_content_hash=decomposition.source_content_hash,
            memory_type=memory_type,
            primitive_type=obs.primitive_type.value,
            label=obs.label,
            content=obs.description,
            confidence=obs.confidence,
            classification_reason=reason,
            provenance={
                "source_reference": obs.source_reference,
                "evidence": obs.evidence[:200],
                "is_inferred": obs.is_inferred,
            },
        )

        if memory_type == MemoryType.CANONICAL:
            candidate_set.canonical_candidates.append(candidate)
        else:
            candidate_set.instance_candidates.append(candidate)

        candidate_set.classified_count += 1

    return candidate_set
