"""Migration pin: LocalFileSource ingestion path.

Pins recent commits: ingestion-orchestrator-1, persist-all-observations,
authority-tier-on-source. Exercises the full pipeline: file → signal →
interpretation → decomposition → observations → memory entries written.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")

from governance.policy.authority_tier import T5_DEFAULT, get_authority_tier
from runtime.ingestion.local_file_source import LocalFileSource
from runtime.ingestion.orchestrator import GenericIngestionOrchestrator

from .conftest import FIXTURE_PATH, MOCK_LLM_RESPONSE

pytestmark = pytest.mark.migration


class TestLocalFileSource:
    def test_fixture_file_exists(self):
        assert FIXTURE_PATH.exists(), f"Fixture not found: {FIXTURE_PATH}"

    def test_source_reads_content(self):
        source = LocalFileSource(FIXTURE_PATH)
        raw = source.read()
        assert raw.content_type == "text/markdown"
        assert raw.size_bytes > 0
        assert len(raw.sha256) == 64

    def test_source_type_is_local_file(self):
        source = LocalFileSource(FIXTURE_PATH)
        assert source.source_type == "local_file"

    def test_source_id_is_sha256(self):
        source = LocalFileSource(FIXTURE_PATH)
        raw = source.read()
        assert source.source_id == raw.sha256

    def test_metadata_includes_path(self):
        source = LocalFileSource(FIXTURE_PATH)
        meta = source.metadata()
        assert "path" in meta
        assert str(FIXTURE_PATH.resolve()) == meta["path"]

    def test_authority_tier_default(self):
        source = LocalFileSource(FIXTURE_PATH)
        assert source.authority_tier == T5_DEFAULT

    def test_canary_in_content(self):
        source = LocalFileSource(FIXTURE_PATH)
        raw = source.read()
        assert "XQVR7-ZEPHYR-CANARY-9F3K" in raw.content


class TestIngestionFullCycle:
    def test_complete_cycle_with_mock_llm(self, temp_memory_store: Path):
        source = LocalFileSource(FIXTURE_PATH)
        orchestrator = GenericIngestionOrchestrator(
            memory_store_path=temp_memory_store,
        )

        mock_result = MagicMock()
        mock_result.output = MOCK_LLM_RESPONSE

        with patch(
            "runtime.model_router.call_with_fallback",
            return_value=mock_result,
        ):
            result = orchestrator.ingest(source)

        assert result.verdict == "COMPLETE_CYCLE", (
            f"Expected COMPLETE_CYCLE, got {result.verdict}: {result.error_trace}"
        )

        assert result.signal is not None
        assert result.signal.signal_id.startswith("SIG-")

        assert result.interpretation is not None
        assert len(result.interpretation.inferred_domains) > 0

        assert result.decomposition is not None
        n_obs = len(result.decomposition.observations)
        assert n_obs == 3

        assert result.memory_write is not None
        assert result.memory_write.entries_written == n_obs
        assert len(result.memory_write.memory_ids_written) == n_obs

    def test_authority_tier_propagates(self, temp_memory_store: Path):
        source = LocalFileSource(FIXTURE_PATH)
        orchestrator = GenericIngestionOrchestrator(
            memory_store_path=temp_memory_store,
        )

        mock_result = MagicMock()
        mock_result.output = MOCK_LLM_RESPONSE

        with patch(
            "runtime.model_router.call_with_fallback",
            return_value=mock_result,
        ):
            result = orchestrator.ingest(source)

        assert result.signal is not None
        assert result.signal.authority_tier == T5_DEFAULT

        assert result.interpretation is not None
        assert result.interpretation.authority_tier == T5_DEFAULT

    def test_query_back_finds_entry(self, temp_memory_store: Path):
        source = LocalFileSource(FIXTURE_PATH)
        orchestrator = GenericIngestionOrchestrator(
            memory_store_path=temp_memory_store,
        )

        mock_result = MagicMock()
        mock_result.output = MOCK_LLM_RESPONSE

        with patch(
            "runtime.model_router.call_with_fallback",
            return_value=mock_result,
        ):
            result = orchestrator.ingest(source)

        assert result.query_proof is not None
        assert result.query_proof.new_entry_appears_in_results
