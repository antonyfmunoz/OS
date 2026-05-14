"""Contextual Retrieval Coordination Engine v1.

Coordinates knowledge retrieval with tier-aware filtering.
Canonical knowledge retrieved first, then corroborated, then instance.
Results are bounded, hashed, and deterministic.

UMH substrate subsystem. Phase 96.8CB.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from core.knowledge.knowledge_fabric_contracts_v1 import (
    RetrievalCoordinationState,
    KnowledgeTier,
    _now_iso,
)

MAX_RESULTS_PER_QUERY = 50
TIER_PRIORITY = ["canonical", "corroborated", "instance", "provisional"]


class ContextualRetrievalCoordinationEngine:
    """Coordinates tier-aware knowledge retrieval."""

    def __init__(self, state_dir: str | Path | None = None) -> None:
        self._nodes: dict[str, dict[str, Any]] = {}
        self._retrievals: list[RetrievalCoordinationState] = []
        self._total_retrievals = 0

    def register_node(
        self,
        node_id: str,
        concept: str,
        content: str,
        tier: str = "instance",
    ) -> None:
        self._nodes[node_id] = {
            "node_id": node_id,
            "concept": concept,
            "content": content,
            "tier": tier,
        }

    def retrieve(
        self,
        query: str,
        retrieval_tier: str = "canonical",
        max_results: int = 10,
    ) -> dict[str, Any]:
        max_results = min(max_results, MAX_RESULTS_PER_QUERY)

        tier_idx = TIER_PRIORITY.index(retrieval_tier) if retrieval_tier in TIER_PRIORITY else 0
        allowed_tiers = TIER_PRIORITY[: tier_idx + 1]

        query_lower = query.lower()
        matches: list[tuple[int, str]] = []

        for node_id, node in self._nodes.items():
            if node["tier"] not in allowed_tiers:
                continue
            if query_lower in node["concept"].lower() or query_lower in node["content"].lower():
                tier_rank = TIER_PRIORITY.index(node["tier"])
                matches.append((tier_rank, node_id))

        matches.sort(key=lambda x: x[0])
        result_ids = [m[1] for m in matches[:max_results]]

        raw = f"{query}:{'|'.join(sorted(result_ids))}"
        retrieval_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]

        state = RetrievalCoordinationState(
            query=query,
            results=result_ids,
            retrieval_tier=retrieval_tier,
            result_count=len(result_ids),
            retrieval_hash=retrieval_hash,
        )
        self._retrievals.append(state)
        self._total_retrievals += 1

        return state.to_dict()

    def get_recent_retrievals(self, limit: int = 10) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._retrievals[-limit:]]

    def get_stats(self) -> dict[str, object]:
        return {
            "total_retrievals": self._total_retrievals,
            "registered_nodes": len(self._nodes),
            "nodes_by_tier": {
                tier: sum(
                    1 for n in self._nodes.values() if n["tier"] == tier
                )
                for tier in TIER_PRIORITY
            },
        }
