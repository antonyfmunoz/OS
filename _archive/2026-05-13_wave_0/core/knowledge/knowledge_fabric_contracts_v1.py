"""Knowledge Fabric Contracts v1.

Data contracts for governed knowledge coordination:
  canonical nodes, instance nodes, semantic relationships,
  lineage, promotion, conflict, provenance, compression,
  retrieval, entity state, conceptual integrity.

The knowledge layer represents governed semantic structure.
It NEVER invents truth or fabricates relationships.

UMH substrate subsystem. Phase 96.8CB.
"""

from __future__ import annotations

import enum
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


class KnowledgeLifecycleState(enum.Enum):
    OBSERVED = "observed"
    CONTEXTUALIZED = "contextualized"
    RECONCILED = "reconciled"
    CORROBORATED = "corroborated"
    PROMOTABLE = "promotable"
    CANONICAL = "canonical"
    EVOLVED = "evolved"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    SUPERSEDED = "superseded"


class KnowledgeEventType(enum.Enum):
    KNOWLEDGE_PROMOTED = "knowledge_promoted"
    SEMANTIC_RELATIONSHIP_CREATED = "semantic_relationship_created"
    SEMANTIC_CONFLICT_DETECTED = "semantic_conflict_detected"
    CORROBORATION_STRENGTHENED = "corroboration_strengthened"
    RETRIEVAL_EXECUTED = "retrieval_executed"
    COMPRESSION_GENERATED = "compression_generated"
    CONCEPTUAL_INTEGRITY_VALIDATED = "conceptual_integrity_validated"
    ONTOLOGY_DRIFT_DETECTED = "ontology_drift_detected"
    SEMANTIC_BOUNDARY_DENIED = "semantic_boundary_denied"
    LINEAGE_TRANSITION_RECORDED = "lineage_transition_recorded"


class KnowledgeTier(enum.Enum):
    CANONICAL = "canonical"
    CORROBORATED = "corroborated"
    INSTANCE = "instance"
    PROVISIONAL = "provisional"
    DEPRECATED = "deprecated"


class RelationshipType(enum.Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    EXTENDS = "extends"
    SUPERSEDES = "supersedes"
    RELATES_TO = "relates_to"


class ConflictSeverity(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CanonicalKnowledgeNode:
    node_id: str = field(default_factory=lambda: _new_id("ckn"))
    concept: str = ""
    content: str = ""
    tier: str = "canonical"
    corroboration_count: int = 0
    promoted_by: str = "operator"
    provenance: list[str] = field(default_factory=list)
    content_hash: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id, "concept": self.concept,
            "content": self.content, "tier": self.tier,
            "corroboration_count": self.corroboration_count,
            "promoted_by": self.promoted_by, "provenance": self.provenance,
            "content_hash": self.content_hash, "timestamp": self.timestamp,
        }


@dataclass
class InstanceKnowledgeNode:
    node_id: str = field(default_factory=lambda: _new_id("ikn"))
    concept: str = ""
    content: str = ""
    tier: str = "instance"
    source: str = ""
    session_id: str = ""
    corroboration_count: int = 0
    content_hash: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id, "concept": self.concept,
            "content": self.content, "tier": self.tier,
            "source": self.source, "session_id": self.session_id,
            "corroboration_count": self.corroboration_count,
            "content_hash": self.content_hash, "timestamp": self.timestamp,
        }


@dataclass
class KnowledgeRelationship:
    relationship_id: str = field(default_factory=lambda: _new_id("krel"))
    source_node: str = ""
    target_node: str = ""
    relationship_type: str = "relates_to"
    strength: float = 0.0
    established_by: str = "operator"
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "relationship_id": self.relationship_id,
            "source_node": self.source_node, "target_node": self.target_node,
            "relationship_type": self.relationship_type,
            "strength": self.strength, "established_by": self.established_by,
            "timestamp": self.timestamp,
        }


@dataclass
class SemanticLineageState:
    lineage_id: str = field(default_factory=lambda: _new_id("slin"))
    node_id: str = ""
    transitions: list[dict[str, str]] = field(default_factory=list)
    current_tier: str = "instance"
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "lineage_id": self.lineage_id, "node_id": self.node_id,
            "transitions": self.transitions, "current_tier": self.current_tier,
            "timestamp": self.timestamp,
        }


@dataclass
class KnowledgePromotionReceipt:
    receipt_id: str = field(default_factory=lambda: _new_id("kprcpt"))
    node_id: str = ""
    from_tier: str = ""
    to_tier: str = ""
    promoted_by: str = "operator"
    corroboration_count: int = 0
    approved: bool = False
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id, "node_id": self.node_id,
            "from_tier": self.from_tier, "to_tier": self.to_tier,
            "promoted_by": self.promoted_by,
            "corroboration_count": self.corroboration_count,
            "approved": self.approved, "timestamp": self.timestamp,
        }


@dataclass
class KnowledgeConflictState:
    conflict_id: str = field(default_factory=lambda: _new_id("kconf"))
    node_a: str = ""
    node_b: str = ""
    conflict_type: str = "contradiction"
    severity: str = "medium"
    resolved: bool = False
    resolution: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "node_a": self.node_a, "node_b": self.node_b,
            "conflict_type": self.conflict_type, "severity": self.severity,
            "resolved": self.resolved, "resolution": self.resolution,
            "timestamp": self.timestamp,
        }


@dataclass
class KnowledgeProvenanceState:
    provenance_id: str = field(default_factory=lambda: _new_id("kprov"))
    node_id: str = ""
    origin_source: str = ""
    origin_session: str = ""
    origin_document: str = ""
    chain: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provenance_id": self.provenance_id, "node_id": self.node_id,
            "origin_source": self.origin_source,
            "origin_session": self.origin_session,
            "origin_document": self.origin_document,
            "chain": self.chain, "timestamp": self.timestamp,
        }


@dataclass
class KnowledgeCompressionState:
    compression_id: str = field(default_factory=lambda: _new_id("kcomp"))
    original_nodes: int = 0
    compressed_nodes: int = 0
    abstraction_level: int = 0
    compression_hash: str = ""
    preserved_concepts: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "compression_id": self.compression_id,
            "original_nodes": self.original_nodes,
            "compressed_nodes": self.compressed_nodes,
            "abstraction_level": self.abstraction_level,
            "compression_hash": self.compression_hash,
            "preserved_concepts": self.preserved_concepts,
            "timestamp": self.timestamp,
        }


@dataclass
class RetrievalCoordinationState:
    retrieval_id: str = field(default_factory=lambda: _new_id("kret"))
    query: str = ""
    results: list[str] = field(default_factory=list)
    retrieval_tier: str = "canonical"
    result_count: int = 0
    retrieval_hash: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "retrieval_id": self.retrieval_id, "query": self.query,
            "results": self.results, "retrieval_tier": self.retrieval_tier,
            "result_count": self.result_count,
            "retrieval_hash": self.retrieval_hash,
            "timestamp": self.timestamp,
        }


@dataclass
class EntityKnowledgeState:
    entity_id: str = field(default_factory=lambda: _new_id("ekst"))
    entity_name: str = ""
    related_nodes: list[str] = field(default_factory=list)
    canonical_count: int = 0
    instance_count: int = 0
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id, "entity_name": self.entity_name,
            "related_nodes": self.related_nodes,
            "canonical_count": self.canonical_count,
            "instance_count": self.instance_count,
            "timestamp": self.timestamp,
        }


@dataclass
class ConceptualIntegrityState:
    integrity_id: str = field(default_factory=lambda: _new_id("cinteg"))
    total_nodes: int = 0
    canonical_count: int = 0
    instance_count: int = 0
    conflict_count: int = 0
    integrity_score: float = 1.0
    coherent: bool = True
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "integrity_id": self.integrity_id,
            "total_nodes": self.total_nodes,
            "canonical_count": self.canonical_count,
            "instance_count": self.instance_count,
            "conflict_count": self.conflict_count,
            "integrity_score": self.integrity_score,
            "coherent": self.coherent, "timestamp": self.timestamp,
        }


@dataclass
class SemanticClusterState:
    cluster_id: str = field(default_factory=lambda: _new_id("sclust"))
    concept: str = ""
    node_ids: list[str] = field(default_factory=list)
    cluster_size: int = 0
    coherence: float = 0.0
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cluster_id": self.cluster_id, "concept": self.concept,
            "node_ids": self.node_ids, "cluster_size": self.cluster_size,
            "coherence": self.coherence, "timestamp": self.timestamp,
        }


@dataclass
class CanonicalPromotionState:
    promotion_id: str = field(default_factory=lambda: _new_id("cprom"))
    pending_promotions: int = 0
    total_promoted: int = 0
    total_denied: int = 0
    corroboration_threshold: int = 2
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "promotion_id": self.promotion_id,
            "pending_promotions": self.pending_promotions,
            "total_promoted": self.total_promoted,
            "total_denied": self.total_denied,
            "corroboration_threshold": self.corroboration_threshold,
            "timestamp": self.timestamp,
        }


@dataclass
class KnowledgeEvolutionState:
    evolution_id: str = field(default_factory=lambda: _new_id("kevol"))
    node_id: str = ""
    revision_count: int = 0
    last_evolution: str = ""
    evolution_type: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evolution_id": self.evolution_id, "node_id": self.node_id,
            "revision_count": self.revision_count,
            "last_evolution": self.last_evolution,
            "evolution_type": self.evolution_type,
            "timestamp": self.timestamp,
        }


@dataclass
class RetrievalReplayState:
    replay_id: str = field(default_factory=lambda: _new_id("krply"))
    check_name: str = ""
    input_hash: str = ""
    output_hash: str = ""
    deterministic: bool = True
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "replay_id": self.replay_id, "check_name": self.check_name,
            "input_hash": self.input_hash, "output_hash": self.output_hash,
            "deterministic": self.deterministic, "timestamp": self.timestamp,
        }
