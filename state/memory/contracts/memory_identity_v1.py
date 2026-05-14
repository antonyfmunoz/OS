"""Memory Identity v1 — deterministic identity model for canonical memories.

Supports lineage chains, supersession, reconciliation references,
and canonical/instance isolation.

UMH substrate subsystem. Phase 96.8BM.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def deterministic_id(namespace: str, content: str) -> str:
    h = hashlib.sha256(f"{namespace}:{content}".encode("utf-8")).hexdigest()[:16]
    return f"{namespace}-{h}"


def content_fingerprint(text: str) -> str:
    normalized = " ".join(text.lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]


@dataclass
class MemoryIdentity:
    """Identity envelope for a canonical or instance memory."""

    memory_id: str
    content_fingerprint: str
    memory_type: str  # canonical | instance
    primitive_type: str
    source_document_ids: list[str] = field(default_factory=list)
    source_content_hashes: list[str] = field(default_factory=list)
    supersedes: list[str] = field(default_factory=list)
    superseded_by: str | None = None
    reconciliation_ids: list[str] = field(default_factory=list)
    confidence: float = 0.0
    strength: int = 1  # how many sources corroborate
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "content_fingerprint": self.content_fingerprint,
            "memory_type": self.memory_type,
            "primitive_type": self.primitive_type,
            "source_document_ids": self.source_document_ids,
            "source_content_hashes": self.source_content_hashes,
            "supersedes": self.supersedes,
            "superseded_by": self.superseded_by,
            "reconciliation_ids": self.reconciliation_ids,
            "confidence": self.confidence,
            "strength": self.strength,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class EntityReference:
    """A recurring entity or concept tracked across documents."""

    entity_id: str
    label: str
    entity_type: str  # person | organization | concept | workflow | goal | constraint
    memory_ids: list[str] = field(default_factory=list)
    source_document_ids: list[str] = field(default_factory=list)
    occurrence_count: int = 0
    first_seen: str = ""
    last_seen: str = ""

    def __post_init__(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        if not self.first_seen:
            self.first_seen = now
        if not self.last_seen:
            self.last_seen = now

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "label": self.label,
            "entity_type": self.entity_type,
            "memory_ids": self.memory_ids,
            "source_document_ids": self.source_document_ids,
            "occurrence_count": self.occurrence_count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }
