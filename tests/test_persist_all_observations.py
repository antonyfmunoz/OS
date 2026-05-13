"""Tests for persist-all-observations — every observation becomes a memory entry."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")

from runtime.ingestion.local_file_source import LocalFileSource
from runtime.ingestion.orchestrator import GenericIngestionOrchestrator


MULTI_OBS_LLM_RESPONSE = json.dumps(
    {
        "observations": [
            {
                "primitive_type": "state",
                "label": "System uses 4-layer navigation hierarchy",
                "description": "Palace, Wing, Room, Locus form structured navigation layers.",
                "confidence": 0.95,
                "source_reference": "test.md:lines 1-5",
                "evidence": "Palace — the whole system. Wing — a top-level module.",
                "is_inferred": False,
            },
            {
                "primitive_type": "constraint",
                "label": "AI must translate questions to concerns first",
                "description": "Agents map questions to concerns before navigating rooms.",
                "confidence": 0.90,
                "source_reference": "test.md:lines 10-15",
                "evidence": "Translate the user's question into a concern.",
                "is_inferred": False,
            },
            {
                "primitive_type": "action",
                "label": "Navigate by concern then room then purpose then loci",
                "description": "The retrieval sequence is: concern, room, purpose, core loci.",
                "confidence": 0.88,
                "source_reference": "test.md:lines 12-18",
                "evidence": "1. Translate. 2. Open room. 3. Read purpose. 4. Core loci.",
                "is_inferred": False,
            },
            {
                "primitive_type": "resource",
                "label": "Locus rank formula uses composite scoring",
                "description": "Rank = inbound*2 + outbound + critical*10 + entry*3.",
                "confidence": 0.92,
                "source_reference": "test.md:line 20",
                "evidence": "Rank is inbound*2 + outbound + critical*10 + entry*3.",
                "is_inferred": False,
            },
        ],
        "relationships": [
            {
                "from_index": 1,
                "to_index": 2,
                "relationship_type": "constrains",
                "confidence": 0.90,
                "description": "Constraint governs navigation actions.",
            },
            {
                "from_index": 0,
                "to_index": 2,
                "relationship_type": "enables",
                "confidence": 0.85,
                "description": "4-layer structure enables navigation pattern.",
            },
        ],
    }
)


def _mock_call_with_fallback(output: str):
    result = MagicMock()
    result.output = output
    return result


@pytest.fixture
def fixture_file(tmp_path: Path) -> Path:
    p = tmp_path / "test_doc.md"
    p.write_text(
        "# Navigation System\n\n"
        "Palace — the whole system. Wing — a top-level module.\n\n"
        "## Retrieval Rules\n\n"
        "Translate the user's question into a concern.\n"
        "1. Translate. 2. Open room. 3. Read purpose. 4. Core loci.\n\n"
        "## Ranking\n\n"
        "Rank is inbound*2 + outbound + critical*10 + entry*3.\n"
    )
    return p


@pytest.fixture
def memory_store(tmp_path: Path) -> Path:
    store = tmp_path / "store"
    store.mkdir()
    (store / "memories.jsonl").write_text("")
    (store / "promotion_receipts.jsonl").write_text("")
    (store / "index.json").write_text(json.dumps({"entries": {}}))
    (store / "promotion_summary.json").write_text(json.dumps({"promoted_canonical": []}))
    return store


class TestPersistAllObservations:
    """All decomposed observations become discrete memory entries."""

    def test_n_observations_produce_n_memory_entries(self, fixture_file: Path, memory_store: Path):
        source = LocalFileSource(fixture_file)
        orchestrator = GenericIngestionOrchestrator(memory_store_path=memory_store)

        with patch(
            "runtime.model_router.call_with_fallback",
            return_value=_mock_call_with_fallback(MULTI_OBS_LLM_RESPONSE),
        ):
            result = orchestrator.ingest(source)

        assert result.verdict == "COMPLETE_CYCLE"
        assert result.memory_write is not None
        assert result.memory_write.entries_written == 4
        assert len(result.memory_write.memory_ids_written) == 4

        lines = [l for l in (memory_store / "memories.jsonl").read_text().strip().split("\n") if l]
        assert len(lines) == 4

        types_written = {json.loads(l)["primitive_type"] for l in lines}
        assert types_written == {"state", "constraint", "action", "resource"}

    def test_each_entry_tagged_with_source_and_decomposition_id(
        self, fixture_file: Path, memory_store: Path
    ):
        source = LocalFileSource(fixture_file)
        orchestrator = GenericIngestionOrchestrator(memory_store_path=memory_store)

        with patch(
            "runtime.model_router.call_with_fallback",
            return_value=_mock_call_with_fallback(MULTI_OBS_LLM_RESPONSE),
        ):
            result = orchestrator.ingest(source)

        lines = [l for l in (memory_store / "memories.jsonl").read_text().strip().split("\n") if l]
        decomp_id = result.decomposition.decomposition_id

        for line in lines:
            entry = json.loads(line)
            assert entry["source_document_id"].startswith("local-")
            assert entry["source_decomposition_id"] == decomp_id
            assert len(entry["source_content_hash"]) == 64

    def test_n_receipts_match_n_entries(self, fixture_file: Path, memory_store: Path):
        source = LocalFileSource(fixture_file)
        orchestrator = GenericIngestionOrchestrator(memory_store_path=memory_store)

        with patch(
            "runtime.model_router.call_with_fallback",
            return_value=_mock_call_with_fallback(MULTI_OBS_LLM_RESPONSE),
        ):
            result = orchestrator.ingest(source)

        assert len(result.promotion_receipts) == 4
        for receipt in result.promotion_receipts:
            assert receipt.decision == "promoted"
            assert receipt.receipt_id.startswith("receipt-")

        receipt_lines = [
            l
            for l in (memory_store / "promotion_receipts.jsonl").read_text().strip().split("\n")
            if l
        ]
        assert len(receipt_lines) == 4

    def test_heuristic_fallback_also_persists_all(self, fixture_file: Path, memory_store: Path):
        source = LocalFileSource(fixture_file)
        orchestrator = GenericIngestionOrchestrator(memory_store_path=memory_store)

        with patch(
            "runtime.model_router.call_with_fallback",
            side_effect=Exception("API down"),
        ):
            result = orchestrator.ingest(source)

        assert result.verdict == "COMPLETE_CYCLE"
        assert result.memory_write is not None
        n = result.memory_write.entries_written
        assert n >= 1

        lines = [l for l in (memory_store / "memories.jsonl").read_text().strip().split("\n") if l]
        assert len(lines) == n
        assert len(result.memory_write.memory_ids_written) == n

    def test_query_back_finds_at_least_one_new_entry(self, fixture_file: Path, memory_store: Path):
        source = LocalFileSource(fixture_file)
        orchestrator = GenericIngestionOrchestrator(memory_store_path=memory_store)

        with patch(
            "runtime.model_router.call_with_fallback",
            return_value=_mock_call_with_fallback(MULTI_OBS_LLM_RESPONSE),
        ):
            result = orchestrator.ingest(source)

        assert result.query_proof is not None
        assert result.query_proof.new_entry_appears_in_results

    def test_index_json_has_all_entries(self, fixture_file: Path, memory_store: Path):
        source = LocalFileSource(fixture_file)
        orchestrator = GenericIngestionOrchestrator(memory_store_path=memory_store)

        with patch(
            "runtime.model_router.call_with_fallback",
            return_value=_mock_call_with_fallback(MULTI_OBS_LLM_RESPONSE),
        ):
            result = orchestrator.ingest(source)

        index = json.loads((memory_store / "index.json").read_text())
        written_ids = set(result.memory_write.memory_ids_written)
        index_ids = set(index["entries"].keys())
        assert written_ids.issubset(index_ids)
        assert len(written_ids) == 4
