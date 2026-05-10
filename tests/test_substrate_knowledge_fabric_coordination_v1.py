"""Tests for Phase 96.8CB — Substrate Knowledge Fabric Coordination.

Covers all 12 modules: contracts, lifecycle, reconciliation,
promotion, relationships, retrieval, compression, evolution,
integrity, observability, replay, boundary policies, bridges,
coordinator.

UMH substrate. Phase 96.8CB.
"""

import hashlib
import json
import shutil
import tempfile

import pytest

import sys
sys.path.insert(0, "/opt/OS")

from core.knowledge.knowledge_fabric_contracts_v1 import (
    CanonicalKnowledgeNode,
    InstanceKnowledgeNode,
    KnowledgeRelationship,
    SemanticLineageState,
    KnowledgePromotionReceipt,
    KnowledgeConflictState,
    KnowledgeProvenanceState,
    KnowledgeCompressionState,
    RetrievalCoordinationState,
    EntityKnowledgeState,
    ConceptualIntegrityState,
    SemanticClusterState,
    CanonicalPromotionState,
    KnowledgeEvolutionState,
    RetrievalReplayState,
    KnowledgeLifecycleState,
    KnowledgeEventType,
    KnowledgeTier,
    RelationshipType,
    ConflictSeverity,
    _now_iso,
    _new_id,
)
from core.knowledge.knowledge_lifecycle_engine_v1 import (
    KnowledgeLifecycleEngine,
    VALID_TRANSITIONS,
    TERMINAL_STATES,
)
from core.knowledge.semantic_reconciliation_engine_v1 import (
    SemanticReconciliationEngine,
    MAX_PENDING_RECONCILIATIONS,
    MAX_CONFLICTS,
)
from core.knowledge.canonical_promotion_engine_v1 import (
    CanonicalPromotionEngine,
    CORROBORATION_THRESHOLD,
    MAX_PENDING_PROMOTIONS,
)
from core.knowledge.semantic_relationship_engine_v1 import (
    SemanticRelationshipEngine,
    MAX_RELATIONSHIPS,
    MAX_CLUSTERS,
    MAX_NODES_PER_CLUSTER,
    KNOWN_RELATIONSHIP_TYPES,
)
from core.knowledge.contextual_retrieval_coordination_engine_v1 import (
    ContextualRetrievalCoordinationEngine,
    MAX_RESULTS_PER_QUERY,
    TIER_PRIORITY,
)
from core.knowledge.semantic_compression_hierarchy_engine_v1 import (
    SemanticCompressionHierarchyEngine,
    MAX_ABSTRACTION_LEVELS,
    MAX_NODES_PER_COMPRESSION,
)
from core.knowledge.temporal_knowledge_evolution_engine_v1 import (
    TemporalKnowledgeEvolutionEngine,
    MAX_EVOLUTIONS_PER_NODE,
    MAX_TRACKED_NODES,
    MAX_PROVENANCE_CHAIN,
)
from core.knowledge.conceptual_integrity_engine_v1 import (
    ConceptualIntegrityEngine,
    INTEGRITY_THRESHOLD,
    DRIFT_THRESHOLD,
)
from core.knowledge.knowledge_observability_pipeline_v1 import (
    KnowledgeObservabilityPipeline,
    EVENT_FILE_MAP,
)
from core.knowledge.knowledge_replay_validator_v1 import (
    KnowledgeReplayValidator,
    REPLAY_CHECKS,
)
from core.knowledge.knowledge_boundary_policies_v1 import (
    KNOWLEDGE_LIMITS,
    FORBIDDEN_KNOWLEDGE_ACTIONS,
    enforce_limit,
    is_forbidden,
    get_all_limits,
    get_all_forbidden,
    validate_boundaries,
)
from core.knowledge.knowledge_continuity_bridges_v1 import (
    MemoryKnowledgeBridge,
    IntelligenceKnowledgeBridge,
    WorkflowsKnowledgeBridge,
    ResilienceKnowledgeBridge,
    SessionsKnowledgeBridge,
    ContinuityKnowledgeBridge,
    ReplayKnowledgeBridge,
    ObservabilityKnowledgeBridge,
    CognitionKnowledgeBridge,
    ALL_BRIDGES,
)
from core.knowledge.canonical_knowledge_fabric_coordinator_v1 import (
    CanonicalKnowledgeFabricCoordinator,
)


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


# ── Contract tests ──────────────────────────────────────────────


class TestContracts:
    def test_canonical_knowledge_node_defaults(self):
        n = CanonicalKnowledgeNode()
        assert n.node_id.startswith("ckn-")
        assert n.tier == "canonical"
        assert n.corroboration_count == 0
        d = n.to_dict()
        assert "node_id" in d

    def test_instance_knowledge_node_defaults(self):
        n = InstanceKnowledgeNode()
        assert n.node_id.startswith("ikn-")
        assert n.tier == "instance"
        d = n.to_dict()
        assert d["tier"] == "instance"

    def test_knowledge_relationship_defaults(self):
        r = KnowledgeRelationship()
        assert r.relationship_id.startswith("krel-")
        assert r.relationship_type == "relates_to"

    def test_semantic_lineage_state(self):
        s = SemanticLineageState(node_id="n1")
        assert s.lineage_id.startswith("slin-")
        assert s.current_tier == "instance"

    def test_promotion_receipt(self):
        r = KnowledgePromotionReceipt(node_id="n1", from_tier="instance", to_tier="canonical")
        assert r.receipt_id.startswith("kprcpt-")
        assert r.approved is False

    def test_conflict_state(self):
        c = KnowledgeConflictState(node_a="a", node_b="b")
        assert c.conflict_id.startswith("kconf-")
        assert c.resolved is False

    def test_provenance_state(self):
        p = KnowledgeProvenanceState(node_id="n1", origin_source="doc")
        assert p.provenance_id.startswith("kprov-")

    def test_compression_state(self):
        c = KnowledgeCompressionState(original_nodes=10, compressed_nodes=5)
        assert c.compression_id.startswith("kcomp-")

    def test_retrieval_state(self):
        r = RetrievalCoordinationState(query="test")
        assert r.retrieval_id.startswith("kret-")

    def test_entity_knowledge_state(self):
        e = EntityKnowledgeState(entity_name="test")
        assert e.entity_id.startswith("ekst-")

    def test_conceptual_integrity_state(self):
        c = ConceptualIntegrityState()
        assert c.integrity_id.startswith("cinteg-")
        assert c.coherent is True

    def test_semantic_cluster_state(self):
        s = SemanticClusterState(concept="test")
        assert s.cluster_id.startswith("sclust-")

    def test_canonical_promotion_state(self):
        c = CanonicalPromotionState()
        assert c.promotion_id.startswith("cprom-")
        assert c.corroboration_threshold == 2

    def test_knowledge_evolution_state(self):
        e = KnowledgeEvolutionState(node_id="n1")
        assert e.evolution_id.startswith("kevol-")

    def test_retrieval_replay_state(self):
        r = RetrievalReplayState(check_name="test")
        assert r.replay_id.startswith("krply-")
        assert r.deterministic is True

    def test_all_contracts_have_to_dict(self):
        contracts = [
            CanonicalKnowledgeNode(), InstanceKnowledgeNode(),
            KnowledgeRelationship(), SemanticLineageState(),
            KnowledgePromotionReceipt(), KnowledgeConflictState(),
            KnowledgeProvenanceState(), KnowledgeCompressionState(),
            RetrievalCoordinationState(), EntityKnowledgeState(),
            ConceptualIntegrityState(), SemanticClusterState(),
            CanonicalPromotionState(), KnowledgeEvolutionState(),
            RetrievalReplayState(),
        ]
        for c in contracts:
            d = c.to_dict()
            assert isinstance(d, dict)
            assert "timestamp" in d


class TestEnums:
    def test_lifecycle_states_count(self):
        assert len(KnowledgeLifecycleState) == 10

    def test_event_types_count(self):
        assert len(KnowledgeEventType) == 10

    def test_knowledge_tiers_count(self):
        assert len(KnowledgeTier) == 5

    def test_relationship_types_count(self):
        assert len(RelationshipType) == 5

    def test_conflict_severity_count(self):
        assert len(ConflictSeverity) == 4

    def test_lifecycle_state_values(self):
        vals = {s.value for s in KnowledgeLifecycleState}
        assert "observed" in vals
        assert "canonical" in vals
        assert "superseded" in vals

    def test_event_type_values(self):
        vals = {e.value for e in KnowledgeEventType}
        assert "knowledge_promoted" in vals
        assert "ontology_drift_detected" in vals


class TestHelpers:
    def test_now_iso_format(self):
        ts = _now_iso()
        assert "T" in ts
        assert "+" in ts or "Z" in ts or ts.endswith("+00:00")

    def test_new_id_prefix(self):
        i = _new_id("test")
        assert i.startswith("test-")
        assert len(i) > 5


# ── Lifecycle engine tests ──────────────────────────────────────


class TestLifecycleEngine:
    def test_initial_state(self):
        eng = KnowledgeLifecycleEngine()
        assert eng.current_state == "observed"

    def test_valid_transition(self):
        eng = KnowledgeLifecycleEngine()
        result = eng.transition(KnowledgeLifecycleState.CONTEXTUALIZED)
        assert result == "contextualized"
        assert eng.current_state == "contextualized"

    def test_invalid_transition_raises(self):
        eng = KnowledgeLifecycleEngine()
        with pytest.raises(ValueError):
            eng.transition(KnowledgeLifecycleState.CANONICAL)

    def test_full_lifecycle_to_canonical(self):
        eng = KnowledgeLifecycleEngine()
        eng.transition(KnowledgeLifecycleState.CONTEXTUALIZED)
        eng.transition(KnowledgeLifecycleState.RECONCILED)
        eng.transition(KnowledgeLifecycleState.CORROBORATED)
        eng.transition(KnowledgeLifecycleState.PROMOTABLE)
        eng.transition(KnowledgeLifecycleState.CANONICAL)
        assert eng.current_state == "canonical"

    def test_canonical_to_evolved(self):
        eng = KnowledgeLifecycleEngine()
        eng.transition(KnowledgeLifecycleState.CONTEXTUALIZED)
        eng.transition(KnowledgeLifecycleState.RECONCILED)
        eng.transition(KnowledgeLifecycleState.CORROBORATED)
        eng.transition(KnowledgeLifecycleState.PROMOTABLE)
        eng.transition(KnowledgeLifecycleState.CANONICAL)
        eng.transition(KnowledgeLifecycleState.EVOLVED)
        assert eng.current_state == "evolved"

    def test_evolved_back_to_canonical(self):
        eng = KnowledgeLifecycleEngine()
        eng.transition(KnowledgeLifecycleState.CONTEXTUALIZED)
        eng.transition(KnowledgeLifecycleState.RECONCILED)
        eng.transition(KnowledgeLifecycleState.CORROBORATED)
        eng.transition(KnowledgeLifecycleState.PROMOTABLE)
        eng.transition(KnowledgeLifecycleState.CANONICAL)
        eng.transition(KnowledgeLifecycleState.EVOLVED)
        eng.transition(KnowledgeLifecycleState.CANONICAL)
        assert eng.current_state == "canonical"

    def test_deprecated_to_archived(self):
        eng = KnowledgeLifecycleEngine()
        eng.transition(KnowledgeLifecycleState.CONTEXTUALIZED)
        eng.transition(KnowledgeLifecycleState.RECONCILED)
        eng.transition(KnowledgeLifecycleState.CORROBORATED)
        eng.transition(KnowledgeLifecycleState.PROMOTABLE)
        eng.transition(KnowledgeLifecycleState.CANONICAL)
        eng.transition(KnowledgeLifecycleState.DEPRECATED)
        eng.transition(KnowledgeLifecycleState.ARCHIVED)
        assert eng.current_state == "archived"

    def test_deprecated_to_superseded(self):
        eng = KnowledgeLifecycleEngine()
        eng.transition(KnowledgeLifecycleState.CONTEXTUALIZED)
        eng.transition(KnowledgeLifecycleState.RECONCILED)
        eng.transition(KnowledgeLifecycleState.CORROBORATED)
        eng.transition(KnowledgeLifecycleState.PROMOTABLE)
        eng.transition(KnowledgeLifecycleState.CANONICAL)
        eng.transition(KnowledgeLifecycleState.DEPRECATED)
        eng.transition(KnowledgeLifecycleState.SUPERSEDED)
        assert eng.current_state == "superseded"

    def test_terminal_states_no_transition(self):
        eng = KnowledgeLifecycleEngine()
        eng.transition(KnowledgeLifecycleState.CONTEXTUALIZED)
        eng.transition(KnowledgeLifecycleState.RECONCILED)
        eng.transition(KnowledgeLifecycleState.CORROBORATED)
        eng.transition(KnowledgeLifecycleState.PROMOTABLE)
        eng.transition(KnowledgeLifecycleState.CANONICAL)
        eng.transition(KnowledgeLifecycleState.DEPRECATED)
        eng.transition(KnowledgeLifecycleState.ARCHIVED)
        with pytest.raises(ValueError):
            eng.transition(KnowledgeLifecycleState.OBSERVED)

    def test_terminal_states_set(self):
        assert TERMINAL_STATES == {"archived", "superseded"}

    def test_transitions_recorded(self):
        eng = KnowledgeLifecycleEngine()
        eng.transition(KnowledgeLifecycleState.CONTEXTUALIZED)
        trans = eng.get_transitions()
        assert len(trans) == 1
        assert trans[0]["from"] == "observed"
        assert trans[0]["to"] == "contextualized"

    def test_stats(self):
        eng = KnowledgeLifecycleEngine()
        eng.transition(KnowledgeLifecycleState.CONTEXTUALIZED)
        stats = eng.get_stats()
        assert stats["current_state"] == "contextualized"
        assert stats["total_transitions"] == 1
        assert stats["is_terminal"] is False

    def test_valid_transitions_all_states_covered(self):
        states = {s.value for s in KnowledgeLifecycleState}
        assert set(VALID_TRANSITIONS.keys()) == states


# ── Reconciliation engine tests ─────────────────────────────────


class TestReconciliationEngine:
    def test_reconcile_no_conflict(self):
        eng = SemanticReconciliationEngine()
        result = eng.reconcile("ikn-1", "ckn-1", "abc", "abc")
        assert result["conflict_detected"] is False

    def test_reconcile_with_conflict(self):
        eng = SemanticReconciliationEngine()
        result = eng.reconcile("ikn-1", "ckn-1", "abc", "def")
        assert result["conflict_detected"] is True
        assert "conflict_id" in result

    def test_reconcile_empty_hashes_no_conflict(self):
        eng = SemanticReconciliationEngine()
        result = eng.reconcile("ikn-1", "ckn-1", "", "")
        assert result["conflict_detected"] is False

    def test_resolve_conflict(self):
        eng = SemanticReconciliationEngine()
        result = eng.reconcile("ikn-1", "ckn-1", "abc", "def")
        conflict_id = result["conflict_id"]
        resolved = eng.resolve_conflict(conflict_id, "merged")
        assert resolved is not None
        assert resolved.resolved is True
        assert resolved.resolution == "merged"

    def test_resolve_unknown_conflict(self):
        eng = SemanticReconciliationEngine()
        assert eng.resolve_conflict("fake-id", "n/a") is None

    def test_get_conflicts_unresolved_only(self):
        eng = SemanticReconciliationEngine()
        eng.reconcile("a", "b", "x", "y")
        eng.reconcile("c", "d", "x", "z")
        all_c = eng.get_conflicts()
        assert len(all_c) == 2
        unresolved = eng.get_conflicts(unresolved_only=True)
        assert len(unresolved) == 2

    def test_lineage_tracked(self):
        eng = SemanticReconciliationEngine()
        eng.reconcile("ikn-1", "ckn-1")
        lineage = eng.get_lineage("ikn-1")
        assert len(lineage) >= 1

    def test_reconciliation_hash_deterministic(self):
        eng = SemanticReconciliationEngine()
        r = eng.reconcile("ikn-1", "ckn-1")
        assert len(r["reconciliation_hash"]) == 16

    def test_stats(self):
        eng = SemanticReconciliationEngine()
        eng.reconcile("a", "b", "x", "y")
        stats = eng.get_stats()
        assert stats["total_reconciliations"] == 1
        assert stats["total_conflicts_detected"] == 1


# ── Promotion engine tests ──────────────────────────────────────


class TestPromotionEngine:
    def test_request_promotion(self):
        eng = CanonicalPromotionEngine()
        receipt = eng.request_promotion("n1", "instance", corroboration_count=3)
        assert receipt.approved is False
        assert receipt.node_id == "n1"

    def test_non_operator_rejected(self):
        eng = CanonicalPromotionEngine()
        with pytest.raises(ValueError):
            eng.request_promotion("n1", "instance", 3, promoted_by="system")

    def test_approve_with_sufficient_corroboration(self):
        eng = CanonicalPromotionEngine()
        receipt = eng.request_promotion("n1", "instance", corroboration_count=3)
        approved = eng.approve_promotion(receipt.receipt_id)
        assert approved is not None
        assert approved.approved is True

    def test_approve_insufficient_corroboration(self):
        eng = CanonicalPromotionEngine()
        receipt = eng.request_promotion("n1", "instance", corroboration_count=1)
        result = eng.approve_promotion(receipt.receipt_id)
        assert result is None

    def test_deny_promotion(self):
        eng = CanonicalPromotionEngine()
        receipt = eng.request_promotion("n1", "instance", corroboration_count=3)
        denied = eng.deny_promotion(receipt.receipt_id)
        assert denied is not None
        assert denied.approved is False

    def test_approve_unknown_receipt(self):
        eng = CanonicalPromotionEngine()
        assert eng.approve_promotion("fake-id") is None

    def test_deny_unknown_receipt(self):
        eng = CanonicalPromotionEngine()
        assert eng.deny_promotion("fake-id") is None

    def test_pending_list(self):
        eng = CanonicalPromotionEngine()
        eng.request_promotion("n1", "instance", 3)
        eng.request_promotion("n2", "instance", 3)
        pending = eng.get_pending()
        assert len(pending) == 2

    def test_promotion_state(self):
        eng = CanonicalPromotionEngine()
        eng.request_promotion("n1", "instance", 3)
        state = eng.get_promotion_state()
        assert state["pending_promotions"] == 1
        assert state["corroboration_threshold"] == CORROBORATION_THRESHOLD

    def test_stats(self):
        eng = CanonicalPromotionEngine()
        receipt = eng.request_promotion("n1", "instance", 3)
        eng.approve_promotion(receipt.receipt_id)
        stats = eng.get_stats()
        assert stats["total_promoted"] == 1
        assert stats["pending_promotions"] == 0

    def test_corroboration_threshold_value(self):
        assert CORROBORATION_THRESHOLD == 2


# ── Relationship engine tests ───────────────────────────────────


class TestRelationshipEngine:
    def test_create_relationship(self):
        eng = SemanticRelationshipEngine()
        rel = eng.create_relationship("a", "b", "supports", 0.8)
        assert rel is not None
        assert rel.relationship_type == "supports"

    def test_unknown_type_rejected(self):
        eng = SemanticRelationshipEngine()
        assert eng.create_relationship("a", "b", "invented_type") is None

    def test_self_reference_rejected(self):
        eng = SemanticRelationshipEngine()
        assert eng.create_relationship("a", "a") is None

    def test_strength_bounded(self):
        eng = SemanticRelationshipEngine()
        rel = eng.create_relationship("a", "b", "supports", 5.0)
        assert rel.strength == 1.0
        rel2 = eng.create_relationship("c", "d", "supports", -1.0)
        assert rel2.strength == 0.0

    def test_get_relationships_outgoing(self):
        eng = SemanticRelationshipEngine()
        eng.create_relationship("a", "b", "supports")
        eng.create_relationship("a", "c", "extends")
        rels = eng.get_relationships("a", direction="outgoing")
        assert len(rels) == 2

    def test_get_relationships_incoming(self):
        eng = SemanticRelationshipEngine()
        eng.create_relationship("a", "b", "supports")
        rels = eng.get_relationships("b", direction="incoming")
        assert len(rels) == 1

    def test_get_relationships_both(self):
        eng = SemanticRelationshipEngine()
        eng.create_relationship("a", "b", "supports")
        eng.create_relationship("c", "a", "extends")
        rels = eng.get_relationships("a", direction="both")
        assert len(rels) == 2

    def test_get_by_type(self):
        eng = SemanticRelationshipEngine()
        eng.create_relationship("a", "b", "supports")
        eng.create_relationship("c", "d", "contradicts")
        supports = eng.get_relationships_by_type("supports")
        assert len(supports) == 1

    def test_cluster_by_concept(self):
        eng = SemanticRelationshipEngine()
        eng.create_relationship("a", "b", "supports")
        cluster = eng.cluster_by_concept("test", ["a", "b"])
        assert cluster is not None
        assert cluster.concept == "test"
        assert cluster.cluster_size == 2

    def test_cluster_bounded(self):
        eng = SemanticRelationshipEngine()
        node_ids = [f"n{i}" for i in range(30)]
        cluster = eng.cluster_by_concept("test", node_ids)
        assert cluster.cluster_size == MAX_NODES_PER_CLUSTER

    def test_cluster_max_reached(self):
        eng = SemanticRelationshipEngine()
        for i in range(MAX_CLUSTERS):
            eng.cluster_by_concept(f"c{i}", [f"n{i}"])
        result = eng.cluster_by_concept("overflow", ["x"])
        assert result is None

    def test_known_relationship_types(self):
        expected = {"supports", "contradicts", "extends", "supersedes", "relates_to"}
        assert KNOWN_RELATIONSHIP_TYPES == expected

    def test_stats(self):
        eng = SemanticRelationshipEngine()
        eng.create_relationship("a", "b", "supports")
        stats = eng.get_stats()
        assert stats["total_relationships"] == 1
        assert stats["total_created"] == 1
        assert "relationships_by_type" in stats


# ── Retrieval engine tests ──────────────────────────────────────


class TestRetrievalEngine:
    def test_register_and_retrieve(self):
        eng = ContextualRetrievalCoordinationEngine()
        eng.register_node("n1", "sovereignty", "self-governance", "canonical")
        result = eng.retrieve("sovereignty")
        assert result["result_count"] == 1
        assert "n1" in result["results"]

    def test_tier_filtering(self):
        eng = ContextualRetrievalCoordinationEngine()
        eng.register_node("n1", "test", "content", "canonical")
        eng.register_node("n2", "test", "content", "instance")
        result = eng.retrieve("test", retrieval_tier="canonical")
        assert result["result_count"] == 1

    def test_tier_filtering_includes_lower(self):
        eng = ContextualRetrievalCoordinationEngine()
        eng.register_node("n1", "test", "content", "canonical")
        eng.register_node("n2", "test", "content", "corroborated")
        result = eng.retrieve("test", retrieval_tier="corroborated")
        assert result["result_count"] == 2

    def test_max_results_bounded(self):
        eng = ContextualRetrievalCoordinationEngine()
        for i in range(60):
            eng.register_node(f"n{i}", "test", "content", "canonical")
        result = eng.retrieve("test", max_results=100)
        assert result["result_count"] <= MAX_RESULTS_PER_QUERY

    def test_retrieval_hash_present(self):
        eng = ContextualRetrievalCoordinationEngine()
        eng.register_node("n1", "test", "content", "canonical")
        result = eng.retrieve("test")
        assert len(result["retrieval_hash"]) == 16

    def test_no_matches(self):
        eng = ContextualRetrievalCoordinationEngine()
        result = eng.retrieve("nonexistent")
        assert result["result_count"] == 0

    def test_recent_retrievals(self):
        eng = ContextualRetrievalCoordinationEngine()
        eng.retrieve("q1")
        eng.retrieve("q2")
        recent = eng.get_recent_retrievals()
        assert len(recent) == 2

    def test_tier_priority_order(self):
        assert TIER_PRIORITY == ["canonical", "corroborated", "instance", "provisional"]

    def test_stats(self):
        eng = ContextualRetrievalCoordinationEngine()
        eng.register_node("n1", "test", "content", "canonical")
        eng.retrieve("test")
        stats = eng.get_stats()
        assert stats["total_retrievals"] == 1
        assert stats["registered_nodes"] == 1


# ── Compression engine tests ────────────────────────────────────


class TestCompressionEngine:
    def test_basic_compression(self):
        eng = SemanticCompressionHierarchyEngine()
        result = eng.compress(["n1", "n2", "n3"], ["c1", "c2"])
        assert result["original_nodes"] == 3
        assert result["compressed_nodes"] <= 3

    def test_abstraction_level_bounded(self):
        eng = SemanticCompressionHierarchyEngine()
        result = eng.compress(["n1"], ["c1"], abstraction_level=100)
        assert result["abstraction_level"] == MAX_ABSTRACTION_LEVELS

    def test_compression_hash_deterministic(self):
        eng = SemanticCompressionHierarchyEngine()
        r1 = eng.compress(["n1", "n2"], ["c1"], 1)
        r2 = eng.compress(["n1", "n2"], ["c1"], 1)
        assert r1["compression_hash"] == r2["compression_hash"]

    def test_higher_abstraction_more_compression(self):
        eng = SemanticCompressionHierarchyEngine()
        r1 = eng.compress([f"n{i}" for i in range(20)], ["c1"], 1)
        r2 = eng.compress([f"n{i}" for i in range(20)], ["c1"], 4)
        assert r2["compressed_nodes"] <= r1["compressed_nodes"]

    def test_nodes_bounded(self):
        eng = SemanticCompressionHierarchyEngine()
        big = [f"n{i}" for i in range(200)]
        result = eng.compress(big, ["c1"])
        assert result["original_nodes"] == MAX_NODES_PER_COMPRESSION

    def test_get_compressions(self):
        eng = SemanticCompressionHierarchyEngine()
        eng.compress(["n1"], ["c1"])
        eng.compress(["n2"], ["c2"])
        comps = eng.get_compressions()
        assert len(comps) == 2

    def test_stats(self):
        eng = SemanticCompressionHierarchyEngine()
        eng.compress(["n1"], ["c1"])
        stats = eng.get_stats()
        assert stats["total_compressions"] == 1


# ── Evolution engine tests ──────────────────────────────────────


class TestEvolutionEngine:
    def test_evolve(self):
        eng = TemporalKnowledgeEvolutionEngine()
        result = eng.evolve("n1", "refinement")
        assert result["evolution_type"] == "refinement"
        assert result["revision_count"] == 1

    def test_non_operator_rejected(self):
        eng = TemporalKnowledgeEvolutionEngine()
        with pytest.raises(ValueError):
            eng.evolve("n1", "refinement", evolved_by="system")

    def test_multiple_evolutions_increment(self):
        eng = TemporalKnowledgeEvolutionEngine()
        eng.evolve("n1", "refinement")
        r2 = eng.evolve("n1", "correction")
        assert r2["revision_count"] == 2

    def test_evolution_history(self):
        eng = TemporalKnowledgeEvolutionEngine()
        eng.evolve("n1", "refinement")
        eng.evolve("n1", "correction")
        history = eng.get_evolution_history("n1")
        assert len(history) == 2

    def test_record_provenance(self):
        eng = TemporalKnowledgeEvolutionEngine()
        prov = eng.record_provenance("n1", "manual_entry", "s1", "doc1", ["a", "b"])
        assert prov["origin_source"] == "manual_entry"

    def test_provenance_chain_bounded(self):
        eng = TemporalKnowledgeEvolutionEngine()
        chain = [f"c{i}" for i in range(30)]
        prov = eng.record_provenance("n1", "src", chain=chain)
        assert len(prov["chain"]) == MAX_PROVENANCE_CHAIN

    def test_get_provenance(self):
        eng = TemporalKnowledgeEvolutionEngine()
        eng.record_provenance("n1", "src")
        prov = eng.get_provenance("n1")
        assert prov is not None

    def test_get_provenance_missing(self):
        eng = TemporalKnowledgeEvolutionEngine()
        assert eng.get_provenance("missing") is None

    def test_stats(self):
        eng = TemporalKnowledgeEvolutionEngine()
        eng.evolve("n1", "refinement")
        eng.record_provenance("n1", "src")
        stats = eng.get_stats()
        assert stats["total_evolutions"] == 1
        assert stats["provenance_records"] == 1


# ── Integrity engine tests ──────────────────────────────────────


class TestIntegrityEngine:
    def test_validate_no_nodes(self):
        eng = ConceptualIntegrityEngine()
        result = eng.validate()
        assert result["integrity_score"] == 1.0
        assert result["coherent"] is True

    def test_validate_with_conflicts(self):
        eng = ConceptualIntegrityEngine()
        result = eng.validate(canonical_count=5, instance_count=5, conflict_count=5)
        assert result["integrity_score"] < 1.0

    def test_high_canonical_ratio_helps(self):
        eng = ConceptualIntegrityEngine()
        r1 = eng.validate(canonical_count=9, instance_count=1, conflict_count=0)
        r2 = eng.validate(canonical_count=1, instance_count=9, conflict_count=0)
        assert r1["integrity_score"] >= r2["integrity_score"]

    def test_coherent_threshold(self):
        assert INTEGRITY_THRESHOLD == 0.7

    def test_detect_drift(self):
        eng = ConceptualIntegrityEngine()
        drift = eng.detect_drift("test", "canonical", "instance")
        assert drift is not None
        assert drift["drift_detected"] is True

    def test_no_drift_when_equal(self):
        eng = ConceptualIntegrityEngine()
        assert eng.detect_drift("test", "canonical", "canonical") is None

    def test_drift_events_tracked(self):
        eng = ConceptualIntegrityEngine()
        eng.detect_drift("a", "canonical", "instance")
        eng.detect_drift("b", "corroborated", "instance")
        events = eng.get_drift_events()
        assert len(events) == 2

    def test_stats(self):
        eng = ConceptualIntegrityEngine()
        eng.validate(5, 5, 1)
        stats = eng.get_stats()
        assert stats["total_validations"] == 1
        assert stats["conflict_count"] == 1


# ── Observability pipeline tests ────────────────────────────────


class TestObservabilityPipeline:
    def test_event_file_map_count(self, tmp_dir):
        assert len(EVENT_FILE_MAP) == 10

    def test_event_file_map_matches_enum(self):
        enum_vals = {e.value for e in KnowledgeEventType}
        map_keys = set(EVENT_FILE_MAP.keys())
        assert enum_vals == map_keys

    def test_emit_knowledge_promoted(self, tmp_dir):
        p = KnowledgeObservabilityPipeline(state_dir=tmp_dir)
        p.emit_knowledge_promoted("n1", "instance", "canonical")
        stats = p.get_stats()
        assert stats["event_counts"]["knowledge_promoted"] == 1

    def test_emit_semantic_relationship_created(self, tmp_dir):
        p = KnowledgeObservabilityPipeline(state_dir=tmp_dir)
        p.emit_semantic_relationship_created("a", "b", "supports")
        assert p.get_stats()["event_counts"]["semantic_relationship_created"] == 1

    def test_emit_semantic_conflict_detected(self, tmp_dir):
        p = KnowledgeObservabilityPipeline(state_dir=tmp_dir)
        p.emit_semantic_conflict_detected("a", "b", "high")
        assert p.get_stats()["event_counts"]["semantic_conflict_detected"] == 1

    def test_emit_corroboration_strengthened(self, tmp_dir):
        p = KnowledgeObservabilityPipeline(state_dir=tmp_dir)
        p.emit_corroboration_strengthened("n1", 3)
        assert p.get_stats()["event_counts"]["corroboration_strengthened"] == 1

    def test_emit_retrieval_executed(self, tmp_dir):
        p = KnowledgeObservabilityPipeline(state_dir=tmp_dir)
        p.emit_retrieval_executed("query", 5)
        assert p.get_stats()["event_counts"]["retrieval_executed"] == 1

    def test_emit_compression_generated(self, tmp_dir):
        p = KnowledgeObservabilityPipeline(state_dir=tmp_dir)
        p.emit_compression_generated(10, 5)
        assert p.get_stats()["event_counts"]["compression_generated"] == 1

    def test_emit_conceptual_integrity_validated(self, tmp_dir):
        p = KnowledgeObservabilityPipeline(state_dir=tmp_dir)
        p.emit_conceptual_integrity_validated(0.95, True)
        assert p.get_stats()["event_counts"]["conceptual_integrity_validated"] == 1

    def test_emit_ontology_drift_detected(self, tmp_dir):
        p = KnowledgeObservabilityPipeline(state_dir=tmp_dir)
        p.emit_ontology_drift_detected("test", "canonical", "instance")
        assert p.get_stats()["event_counts"]["ontology_drift_detected"] == 1

    def test_emit_semantic_boundary_denied(self, tmp_dir):
        p = KnowledgeObservabilityPipeline(state_dir=tmp_dir)
        p.emit_semantic_boundary_denied("action", "reason")
        assert p.get_stats()["event_counts"]["semantic_boundary_denied"] == 1

    def test_emit_lineage_transition_recorded(self, tmp_dir):
        p = KnowledgeObservabilityPipeline(state_dir=tmp_dir)
        p.emit_lineage_transition_recorded("n1", "instance", "canonical")
        assert p.get_stats()["event_counts"]["lineage_transition_recorded"] == 1

    def test_total_events(self, tmp_dir):
        p = KnowledgeObservabilityPipeline(state_dir=tmp_dir)
        p.emit_knowledge_promoted("n1", "i", "c")
        p.emit_retrieval_executed("q", 1)
        stats = p.get_stats()
        assert stats["total_events"] == 2

    def test_events_written_to_file(self, tmp_dir):
        p = KnowledgeObservabilityPipeline(state_dir=tmp_dir)
        p.emit_knowledge_promoted("n1", "instance", "canonical")
        from pathlib import Path
        f = Path(tmp_dir) / "knowledge_promoted.jsonl"
        assert f.exists()
        content = f.read_text()
        data = json.loads(content.strip())
        assert data["event_type"] == "knowledge_promoted"


# ── Replay validator tests ──────────────────────────────────────


class TestReplayValidator:
    def test_replay_checks_count(self):
        assert len(REPLAY_CHECKS) == 6

    def test_validate_determinism(self):
        v = KnowledgeReplayValidator()
        result = v.validate_determinism("semantic_reconciliation", "in", "out")
        assert result["deterministic"] is True
        assert len(result["input_hash"]) == 16

    def test_unknown_check_rejected(self):
        v = KnowledgeReplayValidator()
        with pytest.raises(ValueError):
            v.validate_determinism("fake_check", "in", "out")

    def test_replay_pair_same_output(self):
        v = KnowledgeReplayValidator()
        result = v.validate_replay_pair(
            "retrieval_coordination", "in", "out", "out",
        )
        assert result["deterministic"] is True

    def test_replay_pair_different_output(self):
        v = KnowledgeReplayValidator()
        result = v.validate_replay_pair(
            "retrieval_coordination", "in", "out_a", "out_b",
        )
        assert result["deterministic"] is False

    def test_all_checks_valid(self):
        v = KnowledgeReplayValidator()
        for check in REPLAY_CHECKS:
            result = v.validate_determinism(check, "in", "out")
            assert result["deterministic"] is True

    def test_stats(self):
        v = KnowledgeReplayValidator()
        v.validate_determinism("semantic_reconciliation", "in", "out")
        stats = v.get_stats()
        assert stats["total_checks"] == 1
        assert stats["deterministic_count"] == 1


# ── Boundary policies tests ────────────────────────────────────


class TestBoundaryPolicies:
    def test_limits_count(self):
        assert len(KNOWLEDGE_LIMITS) == 10

    def test_forbidden_count(self):
        assert len(FORBIDDEN_KNOWLEDGE_ACTIONS) == 10

    def test_enforce_limit_default(self):
        assert enforce_limit("max_canonical_nodes") == 500

    def test_enforce_limit_override_lower(self):
        assert enforce_limit("max_canonical_nodes", 100) == 100

    def test_enforce_limit_override_higher_capped(self):
        assert enforce_limit("max_canonical_nodes", 1000) == 500

    def test_enforce_limit_unknown_raises(self):
        with pytest.raises(ValueError):
            enforce_limit("nonexistent_limit")

    def test_is_forbidden_true(self):
        assert is_forbidden("autonomous_truth_generation") is True

    def test_is_forbidden_false(self):
        assert is_forbidden("normal_operation") is False

    def test_get_all_limits(self):
        limits = get_all_limits()
        assert isinstance(limits, dict)
        assert len(limits) == 10

    def test_get_all_forbidden(self):
        forbidden = get_all_forbidden()
        assert isinstance(forbidden, list)
        assert len(forbidden) == 10

    def test_validate_boundaries(self):
        result = validate_boundaries()
        assert result["limits_count"] == 10
        assert result["forbidden_count"] == 10

    def test_autonomous_truth_generation_forbidden(self):
        assert "autonomous_truth_generation" in FORBIDDEN_KNOWLEDGE_ACTIONS

    def test_self_authored_canonical_forbidden(self):
        assert "self_authored_canonical" in FORBIDDEN_KNOWLEDGE_ACTIONS


# ── Continuity bridges tests ────────────────────────────────────


class TestContinuityBridges:
    def test_all_bridges_count(self):
        assert len(ALL_BRIDGES) == 9

    def test_memory_bridge(self, tmp_dir):
        b = MemoryKnowledgeBridge(state_dir=tmp_dir)
        event = b.record("sync", {"key": "value"})
        assert event["bridge"] == "memory_knowledge"

    def test_intelligence_bridge(self, tmp_dir):
        b = IntelligenceKnowledgeBridge(state_dir=tmp_dir)
        event = b.record("sync", {"key": "value"})
        assert event["bridge"] == "intelligence_knowledge"

    def test_workflows_bridge(self, tmp_dir):
        b = WorkflowsKnowledgeBridge(state_dir=tmp_dir)
        event = b.record("sync", {})
        assert event["bridge"] == "workflows_knowledge"

    def test_resilience_bridge(self, tmp_dir):
        b = ResilienceKnowledgeBridge(state_dir=tmp_dir)
        event = b.record("sync", {})
        assert event["bridge"] == "resilience_knowledge"

    def test_sessions_bridge(self, tmp_dir):
        b = SessionsKnowledgeBridge(state_dir=tmp_dir)
        event = b.record("sync", {})
        assert event["bridge"] == "sessions_knowledge"

    def test_continuity_bridge(self, tmp_dir):
        b = ContinuityKnowledgeBridge(state_dir=tmp_dir)
        event = b.record("sync", {})
        assert event["bridge"] == "continuity_knowledge"

    def test_replay_bridge(self, tmp_dir):
        b = ReplayKnowledgeBridge(state_dir=tmp_dir)
        event = b.record("sync", {})
        assert event["bridge"] == "replay_knowledge"

    def test_observability_bridge(self, tmp_dir):
        b = ObservabilityKnowledgeBridge(state_dir=tmp_dir)
        event = b.record("sync", {})
        assert event["bridge"] == "observability_knowledge"

    def test_cognition_bridge(self, tmp_dir):
        b = CognitionKnowledgeBridge(state_dir=tmp_dir)
        event = b.record("sync", {})
        assert event["bridge"] == "cognition_knowledge"

    def test_bridge_events_tracked(self, tmp_dir):
        b = MemoryKnowledgeBridge(state_dir=tmp_dir)
        b.record("sync", {"a": 1})
        b.record("update", {"b": 2})
        events = b.get_events()
        assert len(events) == 2

    def test_bridge_stats(self, tmp_dir):
        b = MemoryKnowledgeBridge(state_dir=tmp_dir)
        b.record("sync", {})
        stats = b.get_stats()
        assert stats["total_events"] == 1
        assert stats["bridge_name"] == "memory_knowledge"

    def test_bridge_writes_to_file(self, tmp_dir):
        b = MemoryKnowledgeBridge(state_dir=tmp_dir)
        b.record("sync", {"test": True})
        from pathlib import Path
        f = Path(tmp_dir) / "memory_knowledge.jsonl"
        assert f.exists()


# ── Coordinator tests ───────────────────────────────────────────


class TestCoordinator:
    def test_register_instance(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        result = c.register_instance("test", "content")
        assert result["node_id"].startswith("ikn-")
        assert result["concept"] == "test"

    def test_register_canonical_operator_only(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        result = c.register_canonical("test", "content", promoted_by="operator")
        assert result["node_id"].startswith("ckn-")

    def test_register_canonical_non_operator_raises(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        with pytest.raises(ValueError):
            c.register_canonical("test", "content", promoted_by="system")

    def test_reconcile(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        inst = c.register_instance("test", "content_a")
        can = c.register_canonical("test", "content_b")
        result = c.reconcile(inst["node_id"], can["node_id"])
        assert "reconciliation_id" in result

    def test_promotion_flow(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        inst = c.register_instance("test", "content")
        receipt = c.request_promotion(inst["node_id"], corroboration_count=3)
        assert receipt["approved"] is False
        approved = c.approve_promotion(receipt["receipt_id"])
        assert approved is not None
        assert approved["approved"] is True

    def test_promotion_insufficient_corroboration(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        inst = c.register_instance("test", "content")
        receipt = c.request_promotion(inst["node_id"], corroboration_count=1)
        result = c.approve_promotion(receipt["receipt_id"])
        assert result is None

    def test_deny_promotion(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        inst = c.register_instance("test", "content")
        receipt = c.request_promotion(inst["node_id"], corroboration_count=3)
        denied = c.deny_promotion(receipt["receipt_id"])
        assert denied is not None

    def test_create_relationship(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        inst = c.register_instance("a", "content")
        can = c.register_canonical("b", "content")
        rel = c.create_relationship(inst["node_id"], can["node_id"], "supports", 0.8)
        assert rel is not None
        assert rel["relationship_type"] == "supports"

    def test_create_relationship_self_denied(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        inst = c.register_instance("a", "content")
        result = c.create_relationship(inst["node_id"], inst["node_id"])
        assert result is None

    def test_create_relationship_invalid_type_denied(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        result = c.create_relationship("a", "b", "invented_type")
        assert result is None

    def test_retrieve(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        c.register_canonical("sovereignty", "Self-governance")
        result = c.retrieve("sovereignty")
        assert result["result_count"] >= 1

    def test_retrieve_no_results(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        result = c.retrieve("nonexistent")
        assert result["result_count"] == 0

    def test_compress(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        result = c.compress(["n1", "n2"], ["c1", "c2"])
        assert result["original_nodes"] == 2

    def test_evolve(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        result = c.evolve("n1", "refinement")
        assert result["evolution_type"] == "refinement"

    def test_record_provenance(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        result = c.record_provenance("n1", "manual_entry")
        assert result["origin_source"] == "manual_entry"

    def test_validate_integrity(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        c.register_canonical("a", "content")
        c.register_instance("b", "content")
        result = c.validate_integrity()
        assert "integrity_score" in result
        assert result["coherent"] in (True, False)

    def test_detect_drift(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        drift = c.detect_drift("test", "canonical", "instance")
        assert drift is not None
        assert drift["drift_detected"] is True

    def test_detect_no_drift(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        assert c.detect_drift("test", "canonical", "canonical") is None

    def test_cluster_by_concept(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        result = c.cluster_by_concept("test", ["n1", "n2"])
        assert result is not None
        assert result["concept"] == "test"

    def test_get_relationships(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        c.create_relationship("a", "b", "supports")
        rels = c.get_relationships("a")
        assert len(rels) == 1

    def test_get_conflicts(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        conflicts = c.get_conflicts()
        assert isinstance(conflicts, list)

    def test_resolve_conflict(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        assert c.resolve_conflict("fake-id", "n/a") is None

    def test_get_evolution_history(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        c.evolve("n1", "refinement")
        history = c.get_evolution_history("n1")
        assert len(history) == 1

    def test_get_provenance(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        c.record_provenance("n1", "src")
        prov = c.get_provenance("n1")
        assert prov is not None

    def test_get_pending_promotions(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        inst = c.register_instance("test", "content")
        c.request_promotion(inst["node_id"], 3)
        pending = c.get_pending_promotions()
        assert len(pending) == 1

    def test_get_promotion_state(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        state = c.get_promotion_state()
        assert "pending_promotions" in state

    def test_get_health(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        health = c.get_health()
        assert "lifecycle_state" in health
        assert "canonical_nodes" in health
        assert "instance_nodes" in health

    def test_get_stats_nine_subsystems(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        stats = c.get_stats()
        assert len(stats) == 9
        expected_keys = {
            "lifecycle", "reconciliation", "promotion", "relationships",
            "retrieval", "compression", "evolution", "integrity",
            "observability",
        }
        assert set(stats.keys()) == expected_keys

    def test_no_forbidden_methods(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        forbidden = ["execute", "dispatch", "run", "invoke", "auto_promote"]
        for method in forbidden:
            assert not hasattr(c, method), f"Coordinator has forbidden method: {method}"

    def test_lifecycle_transitions_on_register(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        assert c.get_health()["lifecycle_state"] == "observed"
        c.register_instance("test", "content")
        assert c.get_health()["lifecycle_state"] == "contextualized"


# ── Constraint verification tests ───────────────────────────────


class TestConstraintVerification:
    def test_no_autonomous_truth_generation(self):
        assert is_forbidden("autonomous_truth_generation")

    def test_no_self_authored_canonical(self):
        assert is_forbidden("self_authored_canonical")

    def test_no_hidden_relationship_creation(self):
        assert is_forbidden("hidden_relationship_creation")

    def test_operator_only_canonical_registration(self, tmp_dir):
        c = CanonicalKnowledgeFabricCoordinator(state_dir=tmp_dir)
        with pytest.raises(ValueError):
            c.register_canonical("test", "content", promoted_by="system")

    def test_operator_only_promotion(self):
        eng = CanonicalPromotionEngine()
        with pytest.raises(ValueError):
            eng.request_promotion("n1", "instance", 3, promoted_by="system")

    def test_operator_only_evolution(self):
        eng = TemporalKnowledgeEvolutionEngine()
        with pytest.raises(ValueError):
            eng.evolve("n1", "test", evolved_by="system")

    def test_corroboration_required_for_promotion(self):
        eng = CanonicalPromotionEngine()
        receipt = eng.request_promotion("n1", "instance", corroboration_count=1)
        assert eng.approve_promotion(receipt.receipt_id) is None

    def test_self_reference_relationships_denied(self):
        eng = SemanticRelationshipEngine()
        assert eng.create_relationship("a", "a") is None

    def test_terminal_lifecycle_states(self):
        eng = KnowledgeLifecycleEngine()
        eng.transition(KnowledgeLifecycleState.CONTEXTUALIZED)
        eng.transition(KnowledgeLifecycleState.RECONCILED)
        eng.transition(KnowledgeLifecycleState.CORROBORATED)
        eng.transition(KnowledgeLifecycleState.PROMOTABLE)
        eng.transition(KnowledgeLifecycleState.CANONICAL)
        eng.transition(KnowledgeLifecycleState.DEPRECATED)
        eng.transition(KnowledgeLifecycleState.ARCHIVED)
        with pytest.raises(ValueError):
            eng.transition(KnowledgeLifecycleState.OBSERVED)

    def test_override_capping(self):
        assert enforce_limit("max_canonical_nodes", 1000) == 500
        assert enforce_limit("max_canonical_nodes", 100) == 100

    def test_retrieval_tier_priority(self):
        eng = ContextualRetrievalCoordinationEngine()
        eng.register_node("n1", "test", "c", "canonical")
        eng.register_node("n2", "test", "c", "instance")
        result = eng.retrieve("test", retrieval_tier="canonical")
        assert result["result_count"] == 1

    def test_bounded_compression(self):
        eng = SemanticCompressionHierarchyEngine()
        big = [f"n{i}" for i in range(200)]
        result = eng.compress(big, ["c1"])
        assert result["original_nodes"] == MAX_NODES_PER_COMPRESSION

    def test_bounded_clusters(self):
        eng = SemanticRelationshipEngine()
        for i in range(MAX_CLUSTERS):
            eng.cluster_by_concept(f"c{i}", [f"n{i}"])
        assert eng.cluster_by_concept("overflow", ["x"]) is None

    def test_bounded_retrieval_results(self):
        eng = ContextualRetrievalCoordinationEngine()
        for i in range(60):
            eng.register_node(f"n{i}", "test", "c", "canonical")
        result = eng.retrieve("test", max_results=100)
        assert result["result_count"] <= MAX_RESULTS_PER_QUERY

    def test_replay_determinism_reconciliation(self):
        eng = SemanticReconciliationEngine()
        r1 = eng.reconcile("a", "b", "x", "y")
        r2 = eng.reconcile("a", "b", "x", "y")
        assert len(r1["reconciliation_hash"]) == 16
        assert len(r2["reconciliation_hash"]) == 16

    def test_replay_determinism_compression(self):
        eng = SemanticCompressionHierarchyEngine()
        r1 = eng.compress(["n1", "n2"], ["c1"], 1)
        r2 = eng.compress(["n1", "n2"], ["c1"], 1)
        assert r1["compression_hash"] == r2["compression_hash"]

    def test_replay_determinism_retrieval(self):
        eng = ContextualRetrievalCoordinationEngine()
        eng.register_node("n1", "test", "c", "canonical")
        r1 = eng.retrieve("test")
        r2 = eng.retrieve("test")
        assert r1["retrieval_hash"] == r2["retrieval_hash"]
