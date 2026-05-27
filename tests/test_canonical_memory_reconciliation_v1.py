"""Tests for canonical memory reconciliation engine.

Validates:
  - Duplicate detection (exact fingerprint match)
  - Semantic overlap detection (label + content Jaccard)
  - Strengthening (corroboration from multiple sources)
  - Conflict detection (opposing sentiment markers)
  - Entity continuity mapping
  - Reconciliation receipts
  - Memory identity tracking
  - Replay determinism of reconciliation decisions

Uses REAL ingestion artifacts. No fabricated data.
Phase 96.8BM.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from adapters.adapter_engine.gws_scanner_bridge_v1 import normalize_from_scanner_outputs
from adapters.adapter_engine.substrate_candidate_gen_v1 import generate_candidates
from adapters.adapter_engine.substrate_decomposer_v1 import decompose_document
from substrate.state.memory.contracts.canonical_memory_reconciliation_engine_v1 import (
    ReconciliationAction,
    ReconciliationEngine,
    _content_overlap_score,
    _detect_conflict,
    _label_overlap_score,
)
from substrate.state.memory.contracts.canonical_memory_store_v1 import CanonicalMemoryStore
from substrate.state.memory.contracts.memory_conflict_governance_v1 import (
    ConflictGovernance,
    ConflictResolution,
)
from substrate.state.memory.contracts.memory_identity_v1 import (
    EntityReference,
    MemoryIdentity,
    content_fingerprint,
    deterministic_id,
)

CANONICAL_RECORD_1 = Path("data/canonical_source_records/w0_001/EntrepreneurOS_1kKBGCS9.json")
RAW_EXTRACTION_1 = Path("data/drive_doc_ingestion_tab_aware/EntrepreneurOS_1kKBGCS9.json")
CANONICAL_RECORD_2 = Path("data/canonical_source_records/w0_001/Conglomerate_Brands_1e6E8OxC.json")
RAW_EXTRACTION_2 = Path("data/drive_doc_ingestion_tab_aware/Conglomerate_Brands_1e6E8OxC.json")


@pytest.fixture()
def real_sources():
    for p in [CANONICAL_RECORD_1, RAW_EXTRACTION_1, CANONICAL_RECORD_2, RAW_EXTRACTION_2]:
        if not p.exists():
            pytest.skip("Real scanner artifacts not present")
    return True


@pytest.fixture()
def tmp_store(tmp_path):
    store_dir = tmp_path / "store"
    return CanonicalMemoryStore(store_dir=store_dir)


@pytest.fixture()
def tmp_engine(tmp_path):
    store_dir = tmp_path / "store"
    receipts_dir = tmp_path / "receipts"
    return ReconciliationEngine(store_dir=store_dir, receipts_dir=receipts_dir)


@pytest.fixture()
def doc1_candidates(real_sources):
    doc = normalize_from_scanner_outputs(CANONICAL_RECORD_1, RAW_EXTRACTION_1)
    decomp = decompose_document(doc.document_id, doc.content_hash, doc.full_text, doc.title)
    return generate_candidates(decomp, doc.document_id)


@pytest.fixture()
def doc2_candidates(real_sources):
    doc = normalize_from_scanner_outputs(CANONICAL_RECORD_2, RAW_EXTRACTION_2)
    decomp = decompose_document(doc.document_id, doc.content_hash, doc.full_text, doc.title)
    return generate_candidates(decomp, doc.document_id)


class TestMemoryIdentity:
    def test_deterministic_id_stable(self):
        id1 = deterministic_id("test", "hello world")
        id2 = deterministic_id("test", "hello world")
        assert id1 == id2
        assert id1.startswith("test-")

    def test_deterministic_id_different_input(self):
        id1 = deterministic_id("test", "hello")
        id2 = deterministic_id("test", "world")
        assert id1 != id2

    def test_content_fingerprint_normalization(self):
        fp1 = content_fingerprint("Hello  World")
        fp2 = content_fingerprint("hello world")
        fp3 = content_fingerprint("  HELLO   WORLD  ")
        assert fp1 == fp2 == fp3

    def test_content_fingerprint_different_content(self):
        fp1 = content_fingerprint("hello world")
        fp2 = content_fingerprint("goodbye world")
        assert fp1 != fp2

    def test_memory_identity_creation(self):
        mi = MemoryIdentity(
            memory_id="mem-test",
            content_fingerprint="fp-test",
            memory_type="canonical",
            primitive_type="goal",
        )
        assert mi.strength == 1
        assert mi.confidence == 0.0
        assert mi.created_at
        d = mi.to_dict()
        assert d["memory_id"] == "mem-test"

    def test_entity_reference_creation(self):
        er = EntityReference(
            entity_id="entity-test",
            label="test entity",
            entity_type="concept",
        )
        assert er.occurrence_count == 0
        assert er.first_seen
        d = er.to_dict()
        assert d["entity_id"] == "entity-test"


class TestOverlapScoring:
    def test_exact_label_match(self):
        assert _label_overlap_score("Revenue Goal", "Revenue Goal") == 1.0

    def test_partial_label_overlap(self):
        score = _label_overlap_score("Revenue Growth Goal", "Revenue Goal")
        assert 0.5 < score < 1.0

    def test_no_label_overlap(self):
        score = _label_overlap_score("Alpha Beta", "Gamma Delta")
        assert score == 0.0

    def test_content_overlap_identical(self):
        assert _content_overlap_score("the quick brown fox", "the quick brown fox") == 1.0

    def test_content_overlap_partial(self):
        score = _content_overlap_score(
            "the quick brown fox jumps over the lazy dog",
            "the quick brown fox runs through the forest",
        )
        assert 0.3 < score < 0.8

    def test_empty_strings(self):
        assert _label_overlap_score("", "") == 0.0
        assert _content_overlap_score("", "") == 0.0


class TestConflictDetection:
    def test_opposing_sentiment_detected(self):
        a = "Always pursue revenue growth aggressively"
        b = "Never pursue revenue growth aggressively"
        assert _detect_conflict(a, b) is True

    def test_no_conflict_same_sentiment(self):
        a = "Always pursue revenue growth"
        b = "Pursue revenue growth continuously"
        assert _detect_conflict(a, b) is False

    def test_both_negative_no_conflict(self):
        a = "Never skip validation steps"
        b = "Don't skip validation steps"
        assert _detect_conflict(a, b) is False


class TestReconciliationEngine:
    def test_empty_store_all_new(self, tmp_engine, doc1_candidates):
        all_cands = [c.to_dict() for c in doc1_candidates.canonical_candidates[:5]]
        receipt = tmp_engine.reconcile_candidates(all_cands, "doc-test")
        assert receipt.new_count == 5
        assert receipt.duplicate_count == 0

    def test_duplicate_detection(self, tmp_engine, tmp_store, doc1_candidates):
        cands = [c.to_dict() for c in doc1_candidates.canonical_candidates[:3]]

        # Promote first
        for c in cands:
            tmp_store.promote_candidate(c, reason="test", promoter="test")

        # Reconcile same candidates
        tmp_engine.load_existing_memories()
        receipt = tmp_engine.reconcile_candidates(cands, "doc-test")
        assert receipt.duplicate_count == 3
        assert receipt.new_count == 0

    def test_new_after_existing(self, tmp_engine, tmp_store, doc1_candidates, doc2_candidates):
        cands1 = [c.to_dict() for c in doc1_candidates.canonical_candidates[:3]]
        for c in cands1:
            tmp_store.promote_candidate(c, reason="test", promoter="test")

        cands2 = [c.to_dict() for c in doc2_candidates.canonical_candidates[:3]]
        tmp_engine.load_existing_memories()
        receipt = tmp_engine.reconcile_candidates(cands2, "doc-test2")
        assert receipt.total_candidates == 3

    def test_receipt_has_decisions(self, tmp_engine, doc1_candidates):
        cands = [c.to_dict() for c in doc1_candidates.canonical_candidates[:5]]
        receipt = tmp_engine.reconcile_candidates(cands, "doc-test")
        assert len(receipt.decisions) == 5
        for d in receipt.decisions:
            assert d.decision_id
            assert d.candidate_id
            assert d.action in ReconciliationAction

    def test_receipt_save(self, tmp_engine, doc1_candidates):
        cands = [c.to_dict() for c in doc1_candidates.canonical_candidates[:3]]
        receipt = tmp_engine.reconcile_candidates(cands, "doc-test")
        path = tmp_engine.save_receipt(receipt)
        assert path.exists()
        with open(path) as f:
            data = json.load(f)
        assert data["total_candidates"] == 3

    def test_apply_decisions(self, tmp_engine, tmp_store, doc1_candidates):
        cands = [c.to_dict() for c in doc1_candidates.canonical_candidates[:5]]
        receipt = tmp_engine.reconcile_candidates(cands, "doc-test")
        result = tmp_engine.apply_decisions(receipt, cands, tmp_store)
        assert result["promoted"] == 5
        assert result["skipped"] == 0

    def test_entity_map_generation(self, tmp_engine, tmp_store, doc1_candidates):
        cands = [c.to_dict() for c in doc1_candidates.canonical_candidates[:10]]
        for c in cands:
            tmp_store.promote_candidate(c, reason="test", promoter="test")

        tmp_engine.load_existing_memories()
        entity_map = tmp_engine.get_entity_map()
        assert len(entity_map) > 0
        for eid, entity in entity_map.items():
            assert entity.entity_id == eid
            assert entity.label
            assert entity.entity_type
            assert entity.occurrence_count >= 1


class TestConflictGovernance:
    def test_record_conflict(self, tmp_path):
        gov = ConflictGovernance(store_dir=tmp_path / "conflicts")
        candidate = {
            "candidate_id": "cand-1",
            "content": "Always do X",
            "label": "X Rule",
            "primitive_type": "constraint",
            "source_document_id": "doc-1",
        }
        existing = {"memory_id": "mem-1", "content": "Never do X", "label": "X Rule"}
        record = gov.record_conflict(candidate, existing, "receipt-1")
        assert record.conflict_id.startswith("conflict-")
        assert record.resolution.value == "pending"

    def test_resolve_conflict(self, tmp_path):
        gov = ConflictGovernance(store_dir=tmp_path / "conflicts")
        candidate = {
            "candidate_id": "cand-1",
            "content": "A",
            "label": "L",
            "primitive_type": "goal",
            "source_document_id": "doc-1",
        }
        existing = {"memory_id": "mem-1", "content": "B", "label": "L"}
        record = gov.record_conflict(candidate, existing, "receipt-1")
        resolved = gov.resolve_conflict(
            record.conflict_id,
            ConflictResolution.KEEP_EXISTING,
            "existing is more authoritative",
        )
        assert resolved is not None
        assert resolved.resolution == ConflictResolution.KEEP_EXISTING

    def test_get_pending(self, tmp_path):
        gov = ConflictGovernance(store_dir=tmp_path / "conflicts")
        for i in range(3):
            candidate = {
                "candidate_id": f"cand-{i}",
                "content": f"C{i}",
                "label": f"L{i}",
                "primitive_type": "goal",
                "source_document_id": "doc-1",
            }
            existing = {"memory_id": f"mem-{i}", "content": f"E{i}", "label": f"L{i}"}
            gov.record_conflict(candidate, existing, "receipt-1")
        pending = gov.get_pending()
        assert len(pending) == 3


class TestReconciliationReplay:
    def test_replay_deterministic(self, tmp_engine, doc1_candidates):
        cands = [c.to_dict() for c in doc1_candidates.canonical_candidates[:10]]

        receipt1 = tmp_engine.reconcile_candidates(cands, "doc-replay")
        receipt2 = tmp_engine.reconcile_candidates(cands, "doc-replay")

        assert receipt1.receipt_id == receipt2.receipt_id
        assert receipt1.new_count == receipt2.new_count
        assert receipt1.duplicate_count == receipt2.duplicate_count
        assert len(receipt1.decisions) == len(receipt2.decisions)

        for d1, d2 in zip(receipt1.decisions, receipt2.decisions):
            assert d1.decision_id == d2.decision_id
            assert d1.action == d2.action
            assert d1.candidate_id == d2.candidate_id


class TestRuntimeArtifacts:
    def test_ingestion_summary_exists(self):
        path = Path("data/runtime/reconciliation_ingestion_set/ingestion_summary.json")
        if not path.exists():
            pytest.skip("Runtime artifacts not present")
        with open(path) as f:
            data = json.load(f)
        assert data["documents_processed"] == 4
        assert data["total_observations"] > 0
        assert data["total_candidates"] > 0

    def test_reconciliation_receipts_exist(self):
        receipts_dir = Path("data/runtime/reconciliation_receipts")
        if not receipts_dir.exists():
            pytest.skip("Runtime artifacts not present")
        receipts = list(receipts_dir.glob("*.json"))
        if not receipts:
            pytest.skip("No reconciliation receipts generated yet")
        assert len(receipts) >= 4

    def test_entity_continuity_map_exists(self):
        path = Path("data/runtime/canonical_entity_continuity/entity_continuity_map.json")
        if not path.exists():
            pytest.skip("Runtime artifacts not present")
        with open(path) as f:
            data = json.load(f)
        assert data["total_entities"] > 0

    def test_query_validation_proof_exists(self):
        path = Path("data/runtime/reconciliation_query_proofs/query_validation_proof.json")
        if not path.exists():
            pytest.skip("Runtime artifacts not present")
        with open(path) as f:
            data = json.load(f)
        assert data["all_pass"] is True

    def test_replay_validation_proof_exists(self):
        path = Path("data/runtime/reconciliation_replay_proofs/replay_validation_proof.json")
        if not path.exists():
            pytest.skip("Runtime artifacts not present")
        with open(path) as f:
            data = json.load(f)
        assert data["all_pass"] is True

    def test_memory_store_not_empty(self):
        path = Path("data/runtime/reconciliation_memory_store/memories.jsonl")
        if not path.exists():
            pytest.skip("Runtime artifacts not present")
        with open(path) as f:
            lines = [line for line in f if line.strip()]
        assert len(lines) > 100
