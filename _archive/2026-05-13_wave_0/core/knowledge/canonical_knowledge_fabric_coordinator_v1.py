"""Canonical Knowledge Fabric Coordinator v1.

Coordinates governed knowledge operations:
  reconciliation, promotion, relationships, retrieval,
  compression, evolution, integrity, observability.

The knowledge layer represents governed semantic structure.
It NEVER invents truth or fabricates relationships.
All canonical promotion requires operator approval.

UMH substrate subsystem. Phase 96.8CB.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.knowledge.knowledge_fabric_contracts_v1 import (
    KnowledgeLifecycleState,
    CanonicalKnowledgeNode,
    InstanceKnowledgeNode,
    _now_iso,
)
from core.knowledge.knowledge_lifecycle_engine_v1 import KnowledgeLifecycleEngine
from core.knowledge.semantic_reconciliation_engine_v1 import (
    SemanticReconciliationEngine,
)
from core.knowledge.canonical_promotion_engine_v1 import CanonicalPromotionEngine
from core.knowledge.semantic_relationship_engine_v1 import (
    SemanticRelationshipEngine,
)
from core.knowledge.contextual_retrieval_coordination_engine_v1 import (
    ContextualRetrievalCoordinationEngine,
)
from core.knowledge.semantic_compression_hierarchy_engine_v1 import (
    SemanticCompressionHierarchyEngine,
)
from core.knowledge.temporal_knowledge_evolution_engine_v1 import (
    TemporalKnowledgeEvolutionEngine,
)
from core.knowledge.conceptual_integrity_engine_v1 import ConceptualIntegrityEngine
from core.knowledge.knowledge_observability_pipeline_v1 import (
    KnowledgeObservabilityPipeline,
)


class CanonicalKnowledgeFabricCoordinator:
    """Coordinates all knowledge fabric operations.

    Cannot fabricate truth. Cannot auto-promote.
    Cannot create relationships without explicit invocation.
    All canonical promotion requires operator approval.
    """

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/knowledge",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)

        self._lifecycle = KnowledgeLifecycleEngine(state_dir=self._state_dir)
        self._reconciliation = SemanticReconciliationEngine(
            state_dir=self._state_dir,
        )
        self._promotion = CanonicalPromotionEngine(state_dir=self._state_dir)
        self._relationships = SemanticRelationshipEngine(
            state_dir=self._state_dir,
        )
        self._retrieval = ContextualRetrievalCoordinationEngine(
            state_dir=self._state_dir,
        )
        self._compression = SemanticCompressionHierarchyEngine(
            state_dir=self._state_dir,
        )
        self._evolution = TemporalKnowledgeEvolutionEngine(
            state_dir=self._state_dir,
        )
        self._integrity = ConceptualIntegrityEngine(state_dir=self._state_dir)
        self._observability = KnowledgeObservabilityPipeline(
            state_dir=self._state_dir / "observability",
        )

        self._canonical_nodes: dict[str, CanonicalKnowledgeNode] = {}
        self._instance_nodes: dict[str, InstanceKnowledgeNode] = {}

    def register_instance(
        self,
        concept: str,
        content: str,
        source: str = "",
        session_id: str = "",
    ) -> dict[str, Any]:
        node = InstanceKnowledgeNode(
            concept=concept,
            content=content,
            source=source,
            session_id=session_id,
        )
        self._instance_nodes[node.node_id] = node
        self._retrieval.register_node(
            node.node_id, concept, content, tier="instance",
        )

        if self._lifecycle.current_state == "observed":
            self._lifecycle.transition(KnowledgeLifecycleState.CONTEXTUALIZED)

        return node.to_dict()

    def register_canonical(
        self,
        concept: str,
        content: str,
        promoted_by: str = "operator",
        provenance: list[str] | None = None,
    ) -> dict[str, Any]:
        if promoted_by != "operator":
            raise ValueError("Only operator can register canonical knowledge")

        node = CanonicalKnowledgeNode(
            concept=concept,
            content=content,
            promoted_by=promoted_by,
            provenance=provenance or [],
        )
        self._canonical_nodes[node.node_id] = node
        self._retrieval.register_node(
            node.node_id, concept, content, tier="canonical",
        )

        self._observability.emit_knowledge_promoted(
            node_id=node.node_id, from_tier="none", to_tier="canonical",
        )

        return node.to_dict()

    def reconcile(
        self,
        instance_node_id: str,
        canonical_node_id: str,
    ) -> dict[str, Any]:
        instance = self._instance_nodes.get(instance_node_id)
        canonical = self._canonical_nodes.get(canonical_node_id)

        i_hash = instance.content_hash if instance else ""
        c_hash = canonical.content_hash if canonical else ""

        result = self._reconciliation.reconcile(
            instance_node_id, canonical_node_id, i_hash, c_hash,
        )

        if result.get("conflict_detected"):
            self._observability.emit_semantic_conflict_detected(
                node_a=instance_node_id,
                node_b=canonical_node_id,
                severity="medium",
            )

        self._observability.emit_lineage_transition_recorded(
            node_id=instance_node_id,
            from_tier="instance",
            to_tier="reconciled" if not result.get("conflict_detected") else "instance",
        )

        return result

    def request_promotion(
        self,
        node_id: str,
        corroboration_count: int = 0,
    ) -> dict[str, Any]:
        node = self._instance_nodes.get(node_id)
        from_tier = "instance"
        if node:
            from_tier = node.tier

        receipt = self._promotion.request_promotion(
            node_id=node_id,
            from_tier=from_tier,
            corroboration_count=corroboration_count,
            promoted_by="operator",
        )
        return receipt.to_dict()

    def approve_promotion(self, receipt_id: str) -> dict[str, Any] | None:
        receipt = self._promotion.approve_promotion(receipt_id)
        if receipt is None:
            return None

        self._observability.emit_knowledge_promoted(
            node_id=receipt.node_id,
            from_tier=receipt.from_tier,
            to_tier="canonical",
        )

        instance = self._instance_nodes.get(receipt.node_id)
        if instance:
            canonical = CanonicalKnowledgeNode(
                concept=instance.concept,
                content=instance.content,
                corroboration_count=receipt.corroboration_count,
                promoted_by="operator",
                provenance=[instance.source],
            )
            self._canonical_nodes[canonical.node_id] = canonical
            self._retrieval.register_node(
                canonical.node_id, instance.concept,
                instance.content, tier="canonical",
            )

        return receipt.to_dict()

    def deny_promotion(self, receipt_id: str) -> dict[str, Any] | None:
        receipt = self._promotion.deny_promotion(receipt_id)
        return receipt.to_dict() if receipt else None

    def create_relationship(
        self,
        source_node: str,
        target_node: str,
        relationship_type: str = "relates_to",
        strength: float = 0.5,
    ) -> dict[str, Any] | None:
        rel = self._relationships.create_relationship(
            source_node=source_node,
            target_node=target_node,
            relationship_type=relationship_type,
            strength=strength,
            established_by="operator",
        )
        if rel is None:
            self._observability.emit_semantic_boundary_denied(
                action="create_relationship",
                reason=f"invalid type or self-reference: {relationship_type}",
            )
            return None

        self._observability.emit_semantic_relationship_created(
            source=source_node,
            target=target_node,
            relationship_type=relationship_type,
        )
        return rel.to_dict()

    def retrieve(
        self,
        query: str,
        tier: str = "canonical",
        max_results: int = 10,
    ) -> dict[str, Any]:
        result = self._retrieval.retrieve(query, tier, max_results)
        self._observability.emit_retrieval_executed(
            query=query, result_count=result["result_count"],
        )
        return result

    def compress(
        self,
        node_ids: list[str],
        concepts: list[str],
        abstraction_level: int = 1,
    ) -> dict[str, Any]:
        result = self._compression.compress(node_ids, concepts, abstraction_level)
        self._observability.emit_compression_generated(
            original=result["original_nodes"],
            compressed=result["compressed_nodes"],
        )
        return result

    def evolve(
        self,
        node_id: str,
        evolution_type: str,
    ) -> dict[str, Any]:
        return self._evolution.evolve(node_id, evolution_type, evolved_by="operator")

    def record_provenance(
        self,
        node_id: str,
        origin_source: str,
        origin_session: str = "",
        origin_document: str = "",
        chain: list[str] | None = None,
    ) -> dict[str, Any]:
        return self._evolution.record_provenance(
            node_id, origin_source, origin_session, origin_document, chain,
        )

    def validate_integrity(self) -> dict[str, Any]:
        conflicts = self._reconciliation.get_conflicts(unresolved_only=True)
        result = self._integrity.validate(
            canonical_count=len(self._canonical_nodes),
            instance_count=len(self._instance_nodes),
            conflict_count=len(conflicts),
        )
        self._observability.emit_conceptual_integrity_validated(
            integrity_score=result["integrity_score"],
            coherent=result["coherent"],
        )
        return result

    def detect_drift(
        self,
        concept: str,
        expected_tier: str,
        actual_tier: str,
    ) -> dict[str, Any] | None:
        drift = self._integrity.detect_drift(concept, expected_tier, actual_tier)
        if drift:
            self._observability.emit_ontology_drift_detected(
                concept=concept,
                expected_tier=expected_tier,
                actual_tier=actual_tier,
            )
        return drift

    def cluster_by_concept(
        self,
        concept: str,
        node_ids: list[str],
    ) -> dict[str, Any] | None:
        cluster = self._relationships.cluster_by_concept(concept, node_ids)
        return cluster.to_dict() if cluster else None

    def get_relationships(
        self,
        node_id: str,
        direction: str = "both",
    ) -> list[dict[str, Any]]:
        return self._relationships.get_relationships(node_id, direction)

    def get_conflicts(self, unresolved_only: bool = False) -> list[dict[str, Any]]:
        return self._reconciliation.get_conflicts(unresolved_only)

    def resolve_conflict(
        self,
        conflict_id: str,
        resolution: str,
    ) -> dict[str, Any] | None:
        result = self._reconciliation.resolve_conflict(conflict_id, resolution)
        return result.to_dict() if result else None

    def get_evolution_history(
        self,
        node_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        return self._evolution.get_evolution_history(node_id, limit)

    def get_provenance(self, node_id: str) -> dict[str, Any] | None:
        return self._evolution.get_provenance(node_id)

    def get_pending_promotions(self) -> list[dict[str, Any]]:
        return self._promotion.get_pending()

    def get_promotion_state(self) -> dict[str, Any]:
        return self._promotion.get_promotion_state()

    def get_health(self) -> dict[str, Any]:
        return {
            "lifecycle_state": self._lifecycle.current_state,
            "canonical_nodes": len(self._canonical_nodes),
            "instance_nodes": len(self._instance_nodes),
            "integrity": self._integrity.get_stats(),
            "promotion": self._promotion.get_stats(),
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "lifecycle": self._lifecycle.get_stats(),
            "reconciliation": self._reconciliation.get_stats(),
            "promotion": self._promotion.get_stats(),
            "relationships": self._relationships.get_stats(),
            "retrieval": self._retrieval.get_stats(),
            "compression": self._compression.get_stats(),
            "evolution": self._evolution.get_stats(),
            "integrity": self._integrity.get_stats(),
            "observability": self._observability.get_stats(),
        }
