"""Tests for decomposer depth upgrade — semantic extraction quality."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")

from understanding.ontology.primitive_decomposition_v1 import (
    PrimitiveType,
    RelationshipType,
)
from understanding.perception.orchestrator import (
    GenericIngestionOrchestrator,
    InterpretationResult,
    Signal,
)
from understanding.perception.source import RawContent


VALID_LLM_RESPONSE = json.dumps(
    {
        "observations": [
            {
                "primitive_type": "state",
                "label": "Memory palace has 4 navigation layers",
                "description": "The system uses a 4-layer hierarchy: Palace, Wing, Room, Locus for structured codebase navigation.",
                "confidence": 0.95,
                "source_reference": "test.md:lines 1-5",
                "evidence": "Palace — the whole system. Wing — a top-level module.",
                "is_inferred": False,
            },
            {
                "primitive_type": "constraint",
                "label": "AI must translate questions to concerns before navigating",
                "description": "Agents cannot directly access files; they must first map questions to domain concerns, then navigate rooms.",
                "confidence": 0.90,
                "source_reference": "test.md:lines 10-15",
                "evidence": "Translate the user's question into a concern.",
                "is_inferred": False,
            },
            {
                "primitive_type": "action",
                "label": "Navigate by concern then room then purpose then loci",
                "description": "The retrieval sequence is: identify concern, open room, verify purpose, read core loci table.",
                "confidence": 0.90,
                "source_reference": "test.md:lines 12-18",
                "evidence": "1. Translate the question. 2. Open the room. 3. Read purpose. 4. Core loci.",
                "is_inferred": False,
            },
            {
                "primitive_type": "resource",
                "label": "Locus rank formula uses inbound, outbound, criticality, entry status",
                "description": "Files are promoted based on a composite score: inbound*2 + outbound + critical*10 + entry*3.",
                "confidence": 0.95,
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
                "description": "The retrieval constraint governs navigation actions.",
            },
            {
                "from_index": 0,
                "to_index": 2,
                "relationship_type": "enables",
                "confidence": 0.85,
                "description": "The 4-layer structure enables the navigation pattern.",
            },
        ],
    }
)


def _make_signal() -> Signal:
    return Signal(
        signal_id="SIG-test123",
        source_path="/opt/OS/test.md",
        source_type="text/markdown",
        content_sha256="abc123" * 10 + "abcd",
        content_length={"chars": 500, "words": 80, "lines": 20},
        timestamp_utc="2026-05-12T00:00:00+00:00",
        perceive_duration_ms=1.0,
    )


def _make_interp(signal: Signal) -> InterpretationResult:
    return InterpretationResult(
        signal_id=signal.signal_id,
        inferred_document_type="structured_operational_document",
        inferred_domains=["architecture", "knowledge"],
        confidence=0.85,
        structural_features={"heading_count": 5},
        intent_candidates=["reference_document"],
        interpret_duration_ms=1.0,
    )


def _make_raw() -> RawContent:
    return RawContent(
        content="# Test\n\nThis is test content with must and never keywords.\n\n## Section\n\nMore content.",
        content_type="text/markdown",
        size_bytes=80,
        sha256="abc123" * 10 + "abcd",
    )


def _mock_call_with_fallback(output: str):
    result = MagicMock()
    result.output = output
    return result


class TestExtractionSchemaShape:
    """test_extraction_schema_shape: output conforms to Phase 1 contract."""

    def test_llm_output_produces_typed_observations(self):
        orchestrator = GenericIngestionOrchestrator(
            memory_store_path=Path("/tmp/test_store"),
        )
        signal = _make_signal()
        raw = _make_raw()

        with patch(
            "runtime.model_router.call_with_fallback",
            return_value=_mock_call_with_fallback(VALID_LLM_RESPONSE),
        ):
            result = orchestrator._decompose_llm(signal, _make_interp(signal), raw, "decomp-test1")

        assert result is not None
        assert len(result.observations) == 4

        for obs in result.observations:
            assert obs.observation_id.startswith("obs-")
            assert obs.primitive_type in PrimitiveType
            assert len(obs.label) <= 80
            assert len(obs.description) <= 300
            assert obs.label != obs.description
            assert 0.0 <= obs.confidence <= 1.0
            assert obs.source_reference != ""
            assert obs.evidence != ""
            assert isinstance(obs.is_inferred, bool)

    def test_label_is_semantic_not_raw_text(self):
        orchestrator = GenericIngestionOrchestrator(
            memory_store_path=Path("/tmp/test_store"),
        )
        signal = _make_signal()
        raw = _make_raw()

        with patch(
            "runtime.model_router.call_with_fallback",
            return_value=_mock_call_with_fallback(VALID_LLM_RESPONSE),
        ):
            result = orchestrator._decompose_llm(signal, _make_interp(signal), raw, "decomp-test2")

        assert result is not None
        for obs in result.observations:
            assert not obs.label.startswith("#")
            assert "**" not in obs.label
            assert "```" not in obs.label


class TestIdentityStability:
    """test_identity_stability: same input twice produces same structure."""

    def test_same_input_produces_consistent_type_coverage(self):
        orchestrator = GenericIngestionOrchestrator(
            memory_store_path=Path("/tmp/test_store"),
        )
        signal = _make_signal()
        raw = _make_raw()

        results = []
        for _ in range(2):
            with patch(
                "runtime.model_router.call_with_fallback",
                return_value=_mock_call_with_fallback(VALID_LLM_RESPONSE),
            ):
                r = orchestrator._decompose_llm(signal, _make_interp(signal), raw, "decomp-stable")
                assert r is not None
                results.append(r)

        types_a = {o.primitive_type.value for o in results[0].observations}
        types_b = {o.primitive_type.value for o in results[1].observations}
        assert types_a == types_b

        assert len(results[0].observations) == len(results[1].observations)


class TestRelationshipsAreTyped:
    """test_relationships_are_typed: each has target + type, not raw text."""

    def test_relationships_reference_valid_observations(self):
        orchestrator = GenericIngestionOrchestrator(
            memory_store_path=Path("/tmp/test_store"),
        )
        signal = _make_signal()
        raw = _make_raw()

        with patch(
            "runtime.model_router.call_with_fallback",
            return_value=_mock_call_with_fallback(VALID_LLM_RESPONSE),
        ):
            result = orchestrator._decompose_llm(signal, _make_interp(signal), raw, "decomp-rel")

        assert result is not None
        assert len(result.relationships) >= 1

        obs_ids = {o.observation_id for o in result.observations}
        for rel in result.relationships:
            assert rel.from_observation_id in obs_ids
            assert rel.to_observation_id in obs_ids
            assert rel.relationship_type in RelationshipType
            assert 0.0 <= rel.confidence <= 1.0
            assert len(rel.description) > 0

    def test_relationships_are_semantically_varied(self):
        orchestrator = GenericIngestionOrchestrator(
            memory_store_path=Path("/tmp/test_store"),
        )
        signal = _make_signal()
        raw = _make_raw()

        with patch(
            "runtime.model_router.call_with_fallback",
            return_value=_mock_call_with_fallback(VALID_LLM_RESPONSE),
        ):
            result = orchestrator._decompose_llm(signal, _make_interp(signal), raw, "decomp-relvar")

        assert result is not None
        rel_types = {r.relationship_type.value for r in result.relationships}
        assert len(rel_types) >= 2, f"Expected 2+ relationship types, got: {rel_types}"


class TestHeuristicFallback:
    """Verify heuristic fallback still works when LLM fails."""

    def test_fallback_produces_valid_result(self):
        orchestrator = GenericIngestionOrchestrator(
            memory_store_path=Path("/tmp/test_store"),
        )
        signal = _make_signal()
        raw = _make_raw()
        interp = _make_interp(signal)

        result = orchestrator._decompose_heuristic(signal, interp, raw, "decomp-fallback")

        assert len(result.observations) >= 1
        for obs in result.observations:
            assert obs.primitive_type in PrimitiveType
            assert obs.observation_id.startswith("obs-")

    def test_decompose_falls_back_on_llm_failure(self):
        orchestrator = GenericIngestionOrchestrator(
            memory_store_path=Path("/tmp/test_store"),
        )
        signal = _make_signal()
        raw = _make_raw()
        interp = _make_interp(signal)

        with patch(
            "runtime.model_router.call_with_fallback",
            side_effect=Exception("API down"),
        ):
            result = orchestrator._decompose(signal, interp, raw)

        assert len(result.observations) >= 1
        assert hasattr(result, "_duration_ms")
        assert hasattr(result, "_signal_id")


class TestValidationRejectsGarbage:
    """Verify parser rejects invalid LLM output."""

    def test_rejects_non_json(self):
        orchestrator = GenericIngestionOrchestrator(
            memory_store_path=Path("/tmp/test_store"),
        )
        signal = _make_signal()
        result = orchestrator._parse_extraction_output(
            "This is not JSON", signal, "abc123", "decomp-bad"
        )
        assert result is None

    def test_rejects_invalid_primitive_type(self):
        bad = json.dumps(
            {
                "observations": [
                    {
                        "primitive_type": "INVALID_TYPE",
                        "label": "test",
                        "description": "desc",
                        "confidence": 0.9,
                        "source_reference": "x",
                        "evidence": "e",
                    },
                    {
                        "primitive_type": "ALSO_INVALID",
                        "label": "test2",
                        "description": "desc2",
                        "confidence": 0.9,
                        "source_reference": "x",
                        "evidence": "e",
                    },
                ],
                "relationships": [],
            }
        )
        orchestrator = GenericIngestionOrchestrator(
            memory_store_path=Path("/tmp/test_store"),
        )
        result = orchestrator._parse_extraction_output(bad, _make_signal(), "abc", "decomp-bad2")
        assert result is None

    def test_rejects_label_equals_description(self):
        bad = json.dumps(
            {
                "observations": [
                    {
                        "primitive_type": "state",
                        "label": "same text",
                        "description": "same text",
                        "confidence": 0.9,
                        "source_reference": "x",
                        "evidence": "e",
                    },
                    {
                        "primitive_type": "state",
                        "label": "same text 2",
                        "description": "same text 2",
                        "confidence": 0.9,
                        "source_reference": "x",
                        "evidence": "e",
                    },
                ],
                "relationships": [],
            }
        )
        orchestrator = GenericIngestionOrchestrator(
            memory_store_path=Path("/tmp/test_store"),
        )
        result = orchestrator._parse_extraction_output(bad, _make_signal(), "abc", "decomp-bad3")
        assert result is None

    def test_handles_markdown_code_fence(self):
        fenced = "```json\n" + VALID_LLM_RESPONSE + "\n```"
        orchestrator = GenericIngestionOrchestrator(
            memory_store_path=Path("/tmp/test_store"),
        )
        result = orchestrator._parse_extraction_output(
            fenced, _make_signal(), "abc123", "decomp-fence"
        )
        assert result is not None
        assert len(result.observations) == 4
