"""Transformation State Ledger for the UMH substrate layer.

Formalizes persistent state for every meaningful transformation.
Every stage in the pipeline from raw source to canonical memory
must produce a StateLedgerRecord with input/output hashes,
lineage references, and governance metadata.

Core principle: no transformation without saved state.

UMH substrate subsystem. Phase 96.8V.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class TransformationStage(str, Enum):
    RAW_SOURCE = "raw_source"
    EXTRACTION = "extraction"
    NORMALIZATION = "normalization"
    INTERPRETATION = "interpretation"
    PRIMITIVE_DECOMPOSITION = "primitive_decomposition"
    INGESTION_CANDIDATE = "ingestion_candidate"
    MEMORY_CANDIDATE = "memory_candidate"
    GOVERNANCE_REVIEW = "governance_review"
    CANONICAL_MEMORY = "canonical_memory"
    WORLD_MODEL_MUTATION = "world_model_mutation"


GOVERNANCE_REQUIRED_STAGES = frozenset(
    {
        TransformationStage.CANONICAL_MEMORY,
        TransformationStage.WORLD_MODEL_MUTATION,
    }
)

MUTATION_BLOCKED_STAGES = frozenset(
    {
        TransformationStage.RAW_SOURCE,
        TransformationStage.EXTRACTION,
        TransformationStage.NORMALIZATION,
        TransformationStage.INTERPRETATION,
        TransformationStage.PRIMITIVE_DECOMPOSITION,
        TransformationStage.INGESTION_CANDIDATE,
        TransformationStage.MEMORY_CANDIDATE,
    }
)

VALID_TRANSITIONS: dict[TransformationStage, frozenset[TransformationStage]] = {
    TransformationStage.RAW_SOURCE: frozenset({TransformationStage.EXTRACTION}),
    TransformationStage.EXTRACTION: frozenset({TransformationStage.NORMALIZATION}),
    TransformationStage.NORMALIZATION: frozenset(
        {
            TransformationStage.INTERPRETATION,
            TransformationStage.INGESTION_CANDIDATE,
        }
    ),
    TransformationStage.INTERPRETATION: frozenset({TransformationStage.PRIMITIVE_DECOMPOSITION}),
    TransformationStage.PRIMITIVE_DECOMPOSITION: frozenset(
        {TransformationStage.INGESTION_CANDIDATE}
    ),
    TransformationStage.INGESTION_CANDIDATE: frozenset({TransformationStage.MEMORY_CANDIDATE}),
    TransformationStage.MEMORY_CANDIDATE: frozenset({TransformationStage.GOVERNANCE_REVIEW}),
    TransformationStage.GOVERNANCE_REVIEW: frozenset({TransformationStage.CANONICAL_MEMORY}),
    TransformationStage.CANONICAL_MEMORY: frozenset({TransformationStage.WORLD_MODEL_MUTATION}),
    TransformationStage.WORLD_MODEL_MUTATION: frozenset(),
}


@dataclass
class StateArtifactReference:
    """Pointer to a specific artifact (proof, candidate, memory, etc.)."""

    artifact_id: str
    artifact_type: str
    artifact_path: str = ""
    content_hash: str = ""


@dataclass
class TransformationEdge:
    """Directed edge between two transformation states."""

    from_state_id: str
    to_state_id: str
    from_stage: TransformationStage
    to_stage: TransformationStage
    edge_type: str = "transformation"
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class StateLedgerRecord:
    """Immutable record of a single transformation step."""

    state_id: str
    trace_id: str
    parent_state_id: str
    stage: TransformationStage
    input_artifact_ref: StateArtifactReference
    output_artifact_ref: StateArtifactReference
    transformer_name: str
    transformer_version: str
    runtime_id: str
    adapter_id: str
    policy_envelope: dict[str, Any]
    confidence: str
    input_hash: str
    output_hash: str
    timestamp: str = ""
    allowed_next_actions: list[str] = field(default_factory=list)
    blocked_next_actions: list[str] = field(default_factory=list)
    rollback_reference: str = ""
    governance_reference: str = ""
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "trace_id": self.trace_id,
            "parent_state_id": self.parent_state_id,
            "stage": self.stage.value
            if isinstance(self.stage, TransformationStage)
            else self.stage,
            "input_artifact_ref": {
                "artifact_id": self.input_artifact_ref.artifact_id,
                "artifact_type": self.input_artifact_ref.artifact_type,
                "artifact_path": self.input_artifact_ref.artifact_path,
                "content_hash": self.input_artifact_ref.content_hash,
            },
            "output_artifact_ref": {
                "artifact_id": self.output_artifact_ref.artifact_id,
                "artifact_type": self.output_artifact_ref.artifact_type,
                "artifact_path": self.output_artifact_ref.artifact_path,
                "content_hash": self.output_artifact_ref.content_hash,
            },
            "transformer_name": self.transformer_name,
            "transformer_version": self.transformer_version,
            "runtime_id": self.runtime_id,
            "adapter_id": self.adapter_id,
            "policy_envelope": self.policy_envelope,
            "confidence": self.confidence,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "timestamp": self.timestamp,
            "allowed_next_actions": self.allowed_next_actions,
            "blocked_next_actions": self.blocked_next_actions,
            "rollback_reference": self.rollback_reference,
            "governance_reference": self.governance_reference,
            "notes": self.notes,
        }


class TransformationStateLedger:
    """In-memory ledger that stores and validates transformation state records.

    Persists records to JSON files in a configured directory.
    Supports lineage reconstruction and trace replay.
    """

    def __init__(self, ledger_dir: Path) -> None:
        self.ledger_dir = ledger_dir
        self.ledger_dir.mkdir(parents=True, exist_ok=True)
        self._records: dict[str, StateLedgerRecord] = {}
        self._traces: dict[str, list[str]] = {}

    def validate_record(self, record: StateLedgerRecord) -> list[str]:
        """Validate a state record. Returns list of errors (empty = valid)."""
        errors: list[str] = []

        if not record.state_id:
            errors.append("state_id required")
        if not record.trace_id:
            errors.append("trace_id required")
        if not record.input_hash:
            errors.append("input_hash required")
        if not record.output_hash:
            errors.append("output_hash required")
        if not record.stage:
            errors.append("stage required")
        if not record.allowed_next_actions and not record.blocked_next_actions:
            errors.append("allowed_next_actions or blocked_next_actions required")

        if record.stage in GOVERNANCE_REQUIRED_STAGES:
            if not record.governance_reference:
                errors.append(f"governance_reference required for {record.stage.value}")

        if record.parent_state_id and record.parent_state_id in self._records:
            parent = self._records[record.parent_state_id]
            valid_next = VALID_TRANSITIONS.get(parent.stage, frozenset())
            if record.stage not in valid_next:
                errors.append(f"invalid transition: {parent.stage.value} -> {record.stage.value}")

        for field_name in ["password", "api_key", "secret_key", "bearer", "token_value"]:
            record_str = json.dumps(record.to_dict()).lower()
            if field_name in record_str:
                errors.append(f"secret field detected: {field_name}")

        return errors

    def append(self, record: StateLedgerRecord) -> list[str]:
        """Validate and append a record. Returns errors if invalid."""
        errors = self.validate_record(record)
        if errors:
            return errors

        self._records[record.state_id] = record
        if record.trace_id not in self._traces:
            self._traces[record.trace_id] = []
        self._traces[record.trace_id].append(record.state_id)

        path = self.ledger_dir / f"{record.state_id}.json"
        with open(path, "w") as f:
            json.dump(record.to_dict(), f, indent=2)

        return []

    def get_record(self, state_id: str) -> StateLedgerRecord | None:
        return self._records.get(state_id)

    def get_trace(self, trace_id: str) -> list[StateLedgerRecord]:
        """Reconstruct all states in a trace, ordered by insertion."""
        state_ids = self._traces.get(trace_id, [])
        return [self._records[sid] for sid in state_ids if sid in self._records]

    def reconstruct_lineage(self, state_id: str) -> list[StateLedgerRecord]:
        """Walk parent_state_id chain back to root."""
        chain: list[StateLedgerRecord] = []
        current_id = state_id
        visited: set[str] = set()
        while current_id and current_id in self._records and current_id not in visited:
            visited.add(current_id)
            record = self._records[current_id]
            chain.append(record)
            current_id = record.parent_state_id
        chain.reverse()
        return chain

    def get_rollback_chain(self, state_id: str) -> list[dict[str, str]]:
        """Get rollback references for a state and its ancestors."""
        lineage = self.reconstruct_lineage(state_id)
        return [
            {"state_id": r.state_id, "rollback_reference": r.rollback_reference}
            for r in lineage
            if r.rollback_reference
        ]

    @property
    def record_count(self) -> int:
        return len(self._records)

    @property
    def trace_count(self) -> int:
        return len(self._traces)


def compute_hash(content: str) -> str:
    """Deterministic SHA-256 hash."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def make_state_id() -> str:
    return f"STATE-{uuid.uuid4().hex[:8]}"


def make_trace_id(prefix: str = "TRACE") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"
