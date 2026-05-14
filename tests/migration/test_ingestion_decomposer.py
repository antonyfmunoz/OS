"""Migration pin: decomposer depth upgrade — LLM semantic extraction.

Pins recent commit: decomposer-depth-upgrade. The offline test uses
a mock; the live test (marked @llm @external) calls cc_sdk against
a known input and asserts structured output.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")

from runtime.ingestion.local_file_source import LocalFileSource
from runtime.ingestion.orchestrator import GenericIngestionOrchestrator

from .conftest import FIXTURE_PATH, MOCK_LLM_RESPONSE

pytestmark = pytest.mark.migration


class TestDecomposerWithMock:
    def test_produces_observations_from_mock(self, temp_memory_store: Path):
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

        assert result.decomposition is not None
        obs = result.decomposition.observations
        assert len(obs) == 3

        types_found = {o.primitive_type.value for o in obs}
        assert "state" in types_found
        assert "constraint" in types_found
        assert "action" in types_found

    def test_observations_have_required_fields(self, temp_memory_store: Path):
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

        for obs in result.decomposition.observations:
            assert obs.observation_id, "observation_id must not be empty"
            assert obs.label, "label must not be empty"
            assert obs.description, "description must not be empty"
            assert obs.confidence > 0
            assert obs.evidence, "evidence must not be empty"

    def test_relationships_extracted(self, temp_memory_store: Path):
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

        assert result.decomposition is not None
        assert len(result.decomposition.relationships) >= 1


@pytest.mark.llm
@pytest.mark.external
class TestDecomposerLive:
    def test_live_llm_produces_structured_output(self, temp_memory_store: Path):
        source = LocalFileSource(FIXTURE_PATH)
        orchestrator = GenericIngestionOrchestrator(
            memory_store_path=temp_memory_store,
        )

        result = orchestrator.ingest(source)

        assert result.verdict == "COMPLETE_CYCLE", (
            f"Expected COMPLETE_CYCLE, got {result.verdict}: {result.error_trace}"
        )
        assert result.decomposition is not None
        assert len(result.decomposition.observations) >= 3

        for obs in result.decomposition.observations:
            assert obs.primitive_type.value in (
                "state", "change", "constraint", "resource",
                "time", "signal", "feedback", "goal", "action", "outcome",
            )
