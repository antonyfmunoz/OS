"""Tests for GWS-to-canonical-substrate ingestion pipeline.

Validates the end-to-end path:
  scanner output → bridge → decomposition → candidates → memory → query → replay

Uses REAL scanner artifacts. No example/fabricated data.
Phase 96.8BL.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

import pytest

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from core.adapters.gws_scanner_bridge_v1 import (
    NormalizedDocument,
    normalize_from_scanner_outputs,
)
from core.adapters.substrate_candidate_gen_v1 import (
    CandidateSet,
    MemoryType,
    generate_candidates,
)
from core.adapters.substrate_decomposer_v1 import (
    DecompositionResult,
    decompose_document,
)
from core.memory.canonical_memory_store_v1 import CanonicalMemoryStore
from understanding.ontology.primitive_decomposition_v1 import PrimitiveType

CANONICAL_RECORD = Path(
    "data/canonical_source_records/w0_001/Antony_Munoz_Email_Sequence_1aZiPZ0i.json"
)
RAW_EXTRACTION = Path(
    "data/drive_doc_ingestion_tab_aware/Antony_Munoz_Email_Sequence_1aZiPZ0i.json"
)
EXPECTED_DOC_ID = "doc-1aZiPZ0ijSvLQsL6"
EXPECTED_CONTENT_HASH = "0c320243f7199d2f05cb42d6a08b8e395fa04319769741afc0f590f92f1953e9"


@pytest.fixture()
def real_source_files():
    if not CANONICAL_RECORD.exists() or not RAW_EXTRACTION.exists():
        pytest.skip("Real scanner artifacts not present")
    return CANONICAL_RECORD, RAW_EXTRACTION


@pytest.fixture()
def normalized_doc(real_source_files):
    canonical_path, raw_path = real_source_files
    return normalize_from_scanner_outputs(canonical_path, raw_path)


@pytest.fixture()
def decomposition(normalized_doc):
    return decompose_document(
        document_id=normalized_doc.document_id,
        content_hash=normalized_doc.content_hash,
        full_text=normalized_doc.full_text,
        title=normalized_doc.title,
    )


@pytest.fixture()
def candidates(decomposition, normalized_doc):
    return generate_candidates(decomposition, normalized_doc.document_id)


@pytest.fixture()
def memory_store(tmp_path):
    return CanonicalMemoryStore(store_dir=tmp_path / "memory_store")


class TestBridge:
    def test_reads_real_scanner_artifact(self, normalized_doc):
        assert isinstance(normalized_doc, NormalizedDocument)
        assert normalized_doc.document_id == EXPECTED_DOC_ID
        assert normalized_doc.full_text
        assert normalized_doc.total_words > 0

    def test_deterministic_ids(self, normalized_doc):
        assert normalized_doc.document_id.startswith("doc-")
        assert normalized_doc.content_hash == EXPECTED_CONTENT_HASH

    def test_provenance_preserved(self, normalized_doc):
        assert normalized_doc.file_id
        assert normalized_doc.extraction_method
        assert normalized_doc.metadata.get("bridge_version") == "gws_scanner_bridge_v1"

    def test_tabs_extracted(self, normalized_doc):
        assert len(normalized_doc.tabs) >= 1
        for tab in normalized_doc.tabs:
            assert tab.text
            assert tab.word_count > 0


class TestDecomposition:
    def test_accepts_real_content(self, decomposition):
        assert isinstance(decomposition, DecompositionResult)
        assert len(decomposition.observations) > 0

    def test_deterministic_decomposition_id(self, decomposition):
        assert decomposition.decomposition_id.startswith("decomp-")

    def test_primitive_types_covered(self, decomposition):
        decomposition.compute_coverage()
        types_found = set(decomposition.primitive_type_coverage.keys())
        assert len(types_found) >= 5

    def test_observations_have_confidence(self, decomposition):
        for obs in decomposition.observations:
            assert 0.0 < obs.confidence <= 1.0

    def test_relationships_generated(self, decomposition):
        assert len(decomposition.relationships) > 0


class TestCandidateGeneration:
    def test_candidate_split_works(self, candidates):
        assert isinstance(candidates, CandidateSet)
        assert len(candidates.canonical_candidates) > 0
        assert len(candidates.instance_candidates) > 0

    def test_all_observations_classified(self, candidates):
        total = len(candidates.canonical_candidates) + len(candidates.instance_candidates)
        assert total == candidates.classified_count

    def test_candidates_have_provenance(self, candidates):
        for c in candidates.canonical_candidates + candidates.instance_candidates:
            assert c.source_document_id == EXPECTED_DOC_ID
            assert c.source_content_hash == EXPECTED_CONTENT_HASH
            assert c.classification_reason


class TestMemoryStore:
    def test_append_works(self, candidates, memory_store):
        c = candidates.canonical_candidates[0]
        entry, receipt = memory_store.promote_candidate(
            c.to_dict(), reason="test promotion", promoter="test"
        )
        assert entry.memory_id.startswith("mem-")
        assert receipt.receipt_id.startswith("receipt-")

    def test_query_returns_provenance(self, candidates, memory_store):
        c = candidates.canonical_candidates[0]
        entry, _ = memory_store.promote_candidate(c.to_dict(), reason="test", promoter="test")
        result = memory_store.query_by_id(entry.memory_id)
        assert result is not None
        assert result["source_document_id"] == EXPECTED_DOC_ID
        assert result["provenance"]

    def test_query_by_document(self, candidates, memory_store):
        for c in candidates.canonical_candidates[:2]:
            memory_store.promote_candidate(c.to_dict(), reason="test", promoter="test")
        results = memory_store.query_by_document(EXPECTED_DOC_ID)
        assert len(results) == 2

    def test_query_by_type(self, candidates, memory_store):
        c_can = candidates.canonical_candidates[0]
        c_inst = candidates.instance_candidates[0]
        memory_store.promote_candidate(c_can.to_dict(), reason="test", promoter="test")
        memory_store.promote_candidate(c_inst.to_dict(), reason="test", promoter="test")
        canonical = memory_store.query_by_type("canonical")
        instance = memory_store.query_by_type("instance")
        assert len(canonical) >= 1
        assert len(instance) >= 1


class TestReplay:
    def test_replay_deterministic(self, real_source_files):
        canonical_path, raw_path = real_source_files

        doc1 = normalize_from_scanner_outputs(canonical_path, raw_path)
        decomp1 = decompose_document(
            doc1.document_id, doc1.content_hash, doc1.full_text, doc1.title
        )
        cands1 = generate_candidates(decomp1, doc1.document_id)

        doc2 = normalize_from_scanner_outputs(canonical_path, raw_path)
        decomp2 = decompose_document(
            doc2.document_id, doc2.content_hash, doc2.full_text, doc2.title
        )
        cands2 = generate_candidates(decomp2, doc2.document_id)

        assert doc1.content_hash == doc2.content_hash
        assert decomp1.decomposition_id == decomp2.decomposition_id
        assert len(decomp1.observations) == len(decomp2.observations)
        assert len(decomp1.relationships) == len(decomp2.relationships)
        assert cands1.set_id == cands2.set_id
        assert len(cands1.canonical_candidates) == len(cands2.canonical_candidates)
        assert len(cands1.instance_candidates) == len(cands2.instance_candidates)


class TestNoFabricatedProof:
    def test_artifacts_are_not_example_data(self):
        """Verify runtime artifacts were generated, not hand-written."""
        memories_path = Path("data/runtime/canonical_memory_store/memories.jsonl")
        if not memories_path.exists():
            pytest.skip("Runtime artifacts not present")
        with open(memories_path) as f:
            lines = [json.loads(line) for line in f if line.strip()]
        for entry in lines:
            assert entry["source_document_id"] == EXPECTED_DOC_ID
            assert entry["source_content_hash"] == EXPECTED_CONTENT_HASH
            assert entry["promotion_receipt_id"].startswith("receipt-")
            assert entry["lineage"]["document_id"] == EXPECTED_DOC_ID
