"""Temporal Knowledge Evolution Engine v1.

Tracks how knowledge evolves over time through revisions.
Evolution is governed — no spontaneous mutation.
All changes record lineage and provenance.

UMH substrate subsystem. Phase 96.8CB.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from core.knowledge.knowledge_fabric_contracts_v1 import (
    KnowledgeEvolutionState,
    KnowledgeProvenanceState,
    _new_id,
    _now_iso,
)

MAX_EVOLUTIONS_PER_NODE = 50
MAX_TRACKED_NODES = 200
MAX_PROVENANCE_CHAIN = 20


class TemporalKnowledgeEvolutionEngine:
    """Tracks knowledge evolution over time."""

    def __init__(self, state_dir: str | Path | None = None) -> None:
        self._evolutions: dict[str, list[KnowledgeEvolutionState]] = {}
        self._provenance: dict[str, KnowledgeProvenanceState] = {}
        self._total_evolutions = 0

    def evolve(
        self,
        node_id: str,
        evolution_type: str,
        evolved_by: str = "operator",
    ) -> dict[str, Any]:
        if evolved_by != "operator":
            raise ValueError(
                f"Only operator can evolve knowledge. Got: {evolved_by}"
            )

        if node_id not in self._evolutions:
            if len(self._evolutions) >= MAX_TRACKED_NODES:
                return {"error": "max_tracked_nodes_reached"}
            self._evolutions[node_id] = []

        history = self._evolutions[node_id]
        revision_count = len(history) + 1

        if revision_count > MAX_EVOLUTIONS_PER_NODE:
            return {"error": "max_evolutions_per_node_reached"}

        state = KnowledgeEvolutionState(
            node_id=node_id,
            revision_count=revision_count,
            last_evolution=_now_iso(),
            evolution_type=evolution_type,
        )
        history.append(state)
        self._total_evolutions += 1

        return state.to_dict()

    def record_provenance(
        self,
        node_id: str,
        origin_source: str,
        origin_session: str = "",
        origin_document: str = "",
        chain: list[str] | None = None,
    ) -> dict[str, Any]:
        bounded_chain = (chain or [])[:MAX_PROVENANCE_CHAIN]

        provenance = KnowledgeProvenanceState(
            node_id=node_id,
            origin_source=origin_source,
            origin_session=origin_session,
            origin_document=origin_document,
            chain=bounded_chain,
        )
        self._provenance[node_id] = provenance
        return provenance.to_dict()

    def get_evolution_history(
        self,
        node_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        history = self._evolutions.get(node_id, [])
        return [e.to_dict() for e in history[-limit:]]

    def get_provenance(self, node_id: str) -> dict[str, Any] | None:
        prov = self._provenance.get(node_id)
        return prov.to_dict() if prov else None

    def get_stats(self) -> dict[str, object]:
        return {
            "total_evolutions": self._total_evolutions,
            "tracked_nodes": len(self._evolutions),
            "provenance_records": len(self._provenance),
        }
