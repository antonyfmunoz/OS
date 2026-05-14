"""Semantic Relationship Engine v1.

Manages governed semantic relationships between knowledge nodes.
Relationships are typed, weighted, and operator-established.
Never fabricates relationships — all creation is explicit.

UMH substrate subsystem. Phase 96.8CB.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from core.knowledge.knowledge_fabric_contracts_v1 import (
    KnowledgeRelationship,
    RelationshipType,
    SemanticClusterState,
    _new_id,
    _now_iso,
)

MAX_RELATIONSHIPS = 500
MAX_CLUSTERS = 50
MAX_NODES_PER_CLUSTER = 20
KNOWN_RELATIONSHIP_TYPES = {rt.value for rt in RelationshipType}


class SemanticRelationshipEngine:
    """Manages semantic relationships between knowledge nodes."""

    def __init__(self, state_dir: str | Path | None = None) -> None:
        self._relationships: list[KnowledgeRelationship] = []
        self._clusters: list[SemanticClusterState] = []
        self._total_created = 0

    def create_relationship(
        self,
        source_node: str,
        target_node: str,
        relationship_type: str = "relates_to",
        strength: float = 0.5,
        established_by: str = "operator",
    ) -> KnowledgeRelationship | None:
        if relationship_type not in KNOWN_RELATIONSHIP_TYPES:
            return None

        if source_node == target_node:
            return None

        strength = max(0.0, min(1.0, strength))

        rel = KnowledgeRelationship(
            source_node=source_node,
            target_node=target_node,
            relationship_type=relationship_type,
            strength=strength,
            established_by=established_by,
        )

        if len(self._relationships) < MAX_RELATIONSHIPS:
            self._relationships.append(rel)
        self._total_created += 1
        return rel

    def get_relationships(
        self,
        node_id: str,
        direction: str = "both",
    ) -> list[dict[str, Any]]:
        results = []
        for rel in self._relationships:
            if direction in ("both", "outgoing") and rel.source_node == node_id:
                results.append(rel.to_dict())
            elif direction in ("both", "incoming") and rel.target_node == node_id:
                results.append(rel.to_dict())
        return results

    def get_relationships_by_type(
        self,
        relationship_type: str,
    ) -> list[dict[str, Any]]:
        return [
            r.to_dict()
            for r in self._relationships
            if r.relationship_type == relationship_type
        ]

    def cluster_by_concept(
        self,
        concept: str,
        node_ids: list[str],
    ) -> SemanticClusterState | None:
        if len(self._clusters) >= MAX_CLUSTERS:
            return None

        bounded_ids = node_ids[:MAX_NODES_PER_CLUSTER]

        raw = f"{concept}:{'|'.join(sorted(bounded_ids))}"
        coherence_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]

        related_count = 0
        for rel in self._relationships:
            if rel.source_node in bounded_ids and rel.target_node in bounded_ids:
                related_count += 1

        max_possible = len(bounded_ids) * (len(bounded_ids) - 1)
        coherence = related_count / max_possible if max_possible > 0 else 0.0

        cluster = SemanticClusterState(
            concept=concept,
            node_ids=bounded_ids,
            cluster_size=len(bounded_ids),
            coherence=coherence,
        )
        self._clusters.append(cluster)
        return cluster

    def get_clusters(self) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self._clusters]

    def get_stats(self) -> dict[str, object]:
        return {
            "total_relationships": len(self._relationships),
            "total_created": self._total_created,
            "total_clusters": len(self._clusters),
            "relationships_by_type": {
                rt: sum(
                    1 for r in self._relationships
                    if r.relationship_type == rt
                )
                for rt in KNOWN_RELATIONSHIP_TYPES
            },
        }
