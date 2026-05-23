"""Tests for the generic ingestion orchestrator."""

import json
import os
import sys
import shutil
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")

from adapters.data_source_adapters.local_file_source import LocalFileSource
from substrate.understanding.perception.orchestrator import GenericIngestionOrchestrator

FIXTURE_PATH = Path("/opt/OS/tests/fixtures/ingestion_fixture.md")


@pytest.fixture
def temp_memory_store(tmp_path: Path):
    """Create a temporary canonical memory store with seed data."""
    store = tmp_path / "canonical_memory_store"
    store.mkdir()
    (store / "memories.jsonl").write_text(
        json.dumps(
            {
                "memory_id": "mem-seed-001",
                "candidate_id": "cand-seed-001",
                "memory_type": "canonical",
                "primitive_type": "resource",
                "label": "Seed entry for testing",
                "content": "This is a seed memory entry.",
                "confidence": 0.8,
                "source_document_id": "test-seed",
                "source_content_hash": "abc123",
                "source_decomposition_id": "decomp-seed",
                "promotion_receipt_id": "receipt-seed",
                "provenance": {
                    "source_reference": "test",
                    "evidence": "seed",
                    "is_inferred": False,
                },
                "lineage": {
                    "candidate_id": "cand-seed-001",
                    "decomposition_id": "decomp-seed",
                    "document_id": "test-seed",
                    "content_hash": "abc123",
                    "classification_reason": "seed",
                },
                "timestamp": "2026-05-12T00:00:00+00:00",
            }
        )
        + "\n"
    )
    (store / "promotion_receipts.jsonl").write_text(
        json.dumps(
            {
                "receipt_id": "receipt-seed",
                "candidate_id": "cand-seed-001",
                "decision": "promoted",
                "reason": "Seed",
                "confidence": 0.8,
                "promoter": "test",
                "timestamp": "2026-05-12T00:00:00+00:00",
                "rollback_reference": "candidate:cand-seed-001",
            }
        )
        + "\n"
    )
    (store / "index.json").write_text(
        json.dumps(
            {
                "entries": {
                    "mem-seed-001": {
                        "memory_type": "canonical",
                        "primitive_type": "resource",
                        "label": "Seed entry for testing",
                        "source_document_id": "test-seed",
                        "timestamp": "2026-05-12T00:00:00+00:00",
                    }
                }
            }
        )
    )
    (store / "promotion_summary.json").write_text(
        json.dumps(
            {
                "promoted_canonical": [
                    {
                        "memory_id": "mem-seed-001",
                        "receipt_id": "receipt-seed",
                        "label": "Seed entry for testing",
                        "type": "resource",
                    }
                ]
            }
        )
    )
    return store


class TestLocalFileSource:
    def test_reads_correctly(self):
        source = LocalFileSource(FIXTURE_PATH)
        assert source.exists()
        raw = source.read()

        assert raw.content_type == "text/markdown"
        assert raw.size_bytes > 0
        assert len(raw.sha256) == 64
        assert "XQVR7-ZEPHYR-CANARY-9F3K" in raw.content

        meta = source.metadata()
        assert meta["path"] == str(FIXTURE_PATH.resolve())
        assert meta["extension"] == ".md"
        assert meta["size_bytes"] > 0
        assert source.source_type == "local_file"
        assert source.source_id == raw.sha256


class TestGenericIngestionOrchestrator:
    def test_completes_full_cycle(self, temp_memory_store: Path):
        source = LocalFileSource(FIXTURE_PATH)
        orchestrator = GenericIngestionOrchestrator(
            memory_store_path=temp_memory_store,
        )
        result = orchestrator.ingest(source)

        assert result.verdict == "COMPLETE_CYCLE", (
            f"Expected COMPLETE_CYCLE, got {result.verdict}: {result.error_trace}"
        )
        assert result.cycle_duration_ms > 0

        assert result.signal is not None
        assert result.signal.signal_id.startswith("SIG-")
        assert result.signal.content_sha256 == source.read().sha256

        assert result.interpretation is not None
        assert result.interpretation.inferred_document_type == "structured_operational_document"
        assert len(result.interpretation.inferred_domains) > 0

        assert result.decomposition is not None
        assert len(result.decomposition.observations) >= 3

        assert result.world_update is not None
        assert len(result.world_update.entities_added) == len(result.decomposition.observations)

        assert result.memory_write is not None
        assert result.memory_write.new_canonical_memory_entry_id.startswith("mem-")
        assert result.memory_write.memories_jsonl_before == 1
        n_obs = len(result.decomposition.observations)
        assert result.memory_write.memories_jsonl_after == 1 + n_obs
        assert result.memory_write.entries_written == n_obs
        assert len(result.memory_write.memory_ids_written) == n_obs

        assert result.promotion_receipt is not None
        assert result.promotion_receipt.decision == "promoted"
        assert len(result.promotion_receipts) == n_obs

        assert result.query_proof is not None

    def test_query_back_retrieves_persisted_entry(self, temp_memory_store: Path):
        source = LocalFileSource(FIXTURE_PATH)
        orchestrator = GenericIngestionOrchestrator(
            memory_store_path=temp_memory_store,
        )
        result = orchestrator.ingest(source)

        assert result.verdict == "COMPLETE_CYCLE"
        assert result.query_proof is not None
        assert result.query_proof.new_entry_appears_in_results
        assert result.query_proof.new_entry_rank == 1
