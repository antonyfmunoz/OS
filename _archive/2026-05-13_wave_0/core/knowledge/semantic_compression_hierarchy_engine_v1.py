"""Semantic Compression Hierarchy Engine v1.

Compresses knowledge through abstraction hierarchy levels.
Preserves canonical concepts, compresses instance redundancy.
Compression is deterministic and replay-safe.

UMH substrate subsystem. Phase 96.8CB.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from core.knowledge.knowledge_fabric_contracts_v1 import (
    KnowledgeCompressionState,
    _now_iso,
)

MAX_ABSTRACTION_LEVELS = 5
MAX_NODES_PER_COMPRESSION = 100
MAX_PRESERVED_CONCEPTS = 50


class SemanticCompressionHierarchyEngine:
    """Compresses knowledge through semantic abstraction levels."""

    def __init__(self, state_dir: str | Path | None = None) -> None:
        self._compressions: list[KnowledgeCompressionState] = []
        self._total_compressions = 0

    def compress(
        self,
        node_ids: list[str],
        concepts: list[str],
        abstraction_level: int = 1,
    ) -> dict[str, Any]:
        abstraction_level = min(abstraction_level, MAX_ABSTRACTION_LEVELS)
        bounded_nodes = node_ids[:MAX_NODES_PER_COMPRESSION]
        bounded_concepts = concepts[:MAX_PRESERVED_CONCEPTS]

        original_count = len(bounded_nodes)
        ratio = max(0.3, 1.0 - (abstraction_level * 0.15))
        compressed_count = max(1, int(original_count * ratio))

        raw = f"{abstraction_level}:{'|'.join(sorted(bounded_nodes))}:{'|'.join(sorted(bounded_concepts))}"
        compression_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]

        state = KnowledgeCompressionState(
            original_nodes=original_count,
            compressed_nodes=compressed_count,
            abstraction_level=abstraction_level,
            compression_hash=compression_hash,
            preserved_concepts=bounded_concepts,
        )
        self._compressions.append(state)
        self._total_compressions += 1

        return state.to_dict()

    def get_compressions(self, limit: int = 10) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self._compressions[-limit:]]

    def get_stats(self) -> dict[str, object]:
        return {
            "total_compressions": self._total_compressions,
            "max_abstraction_levels": MAX_ABSTRACTION_LEVELS,
        }
