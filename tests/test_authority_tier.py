"""Tests for authority tier propagation through the ingestion pipeline."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")

from understanding.ontology.primitive_decomposition_v1 import PrimitiveObservation, PrimitiveType
from runtime.domain_bridge.business import BusinessBridge
from runtime.ingestion.authority_tier import (
    T1_CANONICAL,
    T2_ACTIVE,
    T5_DEFAULT,
    T8_SCRATCH,
    T9_OLD_CHATS,
    get_authority_tier,
    tier_name,
    validate_tier,
)
from runtime.ingestion.gws_source import GWSSource
from runtime.ingestion.local_file_source import LocalFileSource
from runtime.ingestion.orchestrator import GenericIngestionOrchestrator


TIERED_LLM_RESPONSE = json.dumps(
    {
        "observations": [
            {
                "primitive_type": "constraint",
                "label": "Founder must close first 10 sales before hiring a salesperson",
                "description": "Hiring a salesperson for an unproven process trains someone to fail.",
                "confidence": 0.92,
                "source_reference": "test.md:lines 1-5",
                "evidence": "Founder closes first. No salesperson hire until process proven.",
                "is_inferred": False,
            },
            {
                "primitive_type": "action",
                "label": "Direct outreach via DM to ICP prospects",
                "description": "Direct message the people who match your ideal customer profile.",
                "confidence": 0.88,
                "source_reference": "test.md:lines 6-10",
                "evidence": "DM the people who match your ICP.",
                "is_inferred": False,
            },
            {
                "primitive_type": "goal",
                "label": "Reach $10K monthly revenue through organic conversion",
                "description": "First revenue milestone before scaling.",
                "confidence": 0.90,
                "source_reference": "test.md:lines 11-15",
                "evidence": "Reach $10K/month before any paid advertising.",
                "is_inferred": False,
            },
        ],
        "relationships": [],
    }
)


def _mock_call_with_fallback(output: str):
    result = MagicMock()
    result.output = output
    return result


@pytest.fixture
def fixture_file(tmp_path: Path) -> Path:
    p = tmp_path / "tier_test.md"
    p.write_text(
        "# Sales Playbook\n\n"
        "Founder closes first. No salesperson hire until process proven.\n\n"
        "## Outreach\n\n"
        "DM the people who match your ICP.\n"
        "Direct outreach closes faster than content.\n\n"
        "## Revenue\n\n"
        "Reach $10K/month before any paid advertising.\n"
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


class TestSourceDeclaresTier:
    """test_source_declares_tier: LocalFileSource + GWSSource have authority_tier."""

    def test_local_file_source_default_tier(self, fixture_file: Path):
        source = LocalFileSource(fixture_file)
        assert source.authority_tier == T5_DEFAULT

    def test_local_file_source_custom_tier(self, fixture_file: Path):
        source = LocalFileSource(fixture_file, authority_tier=T2_ACTIVE)
        assert source.authority_tier == T2_ACTIVE

    def test_gws_source_default_tier(self):
        scanner = MagicMock()
        source = GWSSource("doc-123", scanner)
        assert source.authority_tier == T5_DEFAULT

    def test_gws_source_custom_tier(self):
        scanner = MagicMock()
        source = GWSSource("doc-123", scanner, authority_tier=T1_CANONICAL)
        assert source.authority_tier == T1_CANONICAL


class TestTierValidation:
    """test_tier_validation_rejects_invalid: tiers <1 or >9 raise."""

    def test_tier_zero_rejected(self, fixture_file: Path):
        with pytest.raises(ValueError, match="authority_tier must be 1-9"):
            LocalFileSource(fixture_file, authority_tier=0)

    def test_tier_ten_rejected(self, fixture_file: Path):
        with pytest.raises(ValueError, match="authority_tier must be 1-9"):
            LocalFileSource(fixture_file, authority_tier=10)

    def test_negative_tier_rejected(self, fixture_file: Path):
        with pytest.raises(ValueError, match="authority_tier must be 1-9"):
            LocalFileSource(fixture_file, authority_tier=-1)

    def test_valid_tiers_accepted(self, fixture_file: Path):
        for tier in range(1, 10):
            source = LocalFileSource(fixture_file, authority_tier=tier)
            assert source.authority_tier == tier

    def test_validate_tier_function(self):
        assert validate_tier(1) == 1
        assert validate_tier(9) == 9
        with pytest.raises(ValueError):
            validate_tier(0)

    def test_tier_name_function(self):
        assert tier_name(1) == "canonical"
        assert tier_name(5) == "default"
        assert tier_name(9) == "old_chats"


class TestTierFlowsToObservation:
    """test_tier_flows_to_observation: observation from tiered source carries the tier."""

    def test_tier_propagates_through_pipeline(self, fixture_file: Path, memory_store: Path):
        source = LocalFileSource(fixture_file, authority_tier=T2_ACTIVE)
        orchestrator = GenericIngestionOrchestrator(memory_store_path=memory_store)

        with patch(
            "runtime.model_router.call_with_fallback",
            return_value=_mock_call_with_fallback(TIERED_LLM_RESPONSE),
        ):
            result = orchestrator.ingest(source)

        assert result.verdict == "COMPLETE_CYCLE"
        assert result.signal.authority_tier == T2_ACTIVE
        assert result.interpretation.authority_tier == T2_ACTIVE

        for obs in result.decomposition.observations:
            assert obs.authority_tier == T2_ACTIVE

    def test_default_tier_propagates(self, fixture_file: Path, memory_store: Path):
        source = LocalFileSource(fixture_file)
        orchestrator = GenericIngestionOrchestrator(memory_store_path=memory_store)

        with patch(
            "runtime.model_router.call_with_fallback",
            return_value=_mock_call_with_fallback(TIERED_LLM_RESPONSE),
        ):
            result = orchestrator.ingest(source)

        assert result.verdict == "COMPLETE_CYCLE"
        for obs in result.decomposition.observations:
            assert obs.authority_tier == T5_DEFAULT


class TestTierFlowsToProjection:
    """test_tier_flows_to_projection: projection inherits from source observation."""

    def test_projection_inherits_tier(self, fixture_file: Path, memory_store: Path):
        source = LocalFileSource(fixture_file, authority_tier=T2_ACTIVE)
        orchestrator = GenericIngestionOrchestrator(memory_store_path=memory_store)

        with patch(
            "runtime.model_router.call_with_fallback",
            return_value=_mock_call_with_fallback(TIERED_LLM_RESPONSE),
        ):
            result = orchestrator.ingest(source)

        assert result.verdict == "COMPLETE_CYCLE"
        assert len(result.projections) >= 1

        for proj in result.projections:
            assert proj.authority_tier == T2_ACTIVE

    def test_bridge_carries_tier_from_observation(self):
        bridge = BusinessBridge()
        obs = PrimitiveObservation(
            observation_id="obs-test1",
            primitive_type=PrimitiveType("constraint"),
            label="Founder must close first 10 sales before hiring a salesperson",
            description="Hiring a salesperson for an unproven process trains someone to fail.",
            confidence=0.90,
            source_reference="test:1",
            evidence="test evidence",
            authority_tier=T1_CANONICAL,
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.authority_tier == T1_CANONICAL


class TestTierPersistsInMemoryEntry:
    """test_tier_persists_in_memory_entry: memories.jsonl row includes authority_tier."""

    def test_memory_entries_have_tier(self, fixture_file: Path, memory_store: Path):
        source = LocalFileSource(fixture_file, authority_tier=T8_SCRATCH)
        orchestrator = GenericIngestionOrchestrator(memory_store_path=memory_store)

        with patch(
            "runtime.model_router.call_with_fallback",
            return_value=_mock_call_with_fallback(TIERED_LLM_RESPONSE),
        ):
            result = orchestrator.ingest(source)

        assert result.verdict == "COMPLETE_CYCLE"

        lines = [l for l in (memory_store / "memories.jsonl").read_text().strip().split("\n") if l]
        assert len(lines) >= 1

        for line in lines:
            entry = json.loads(line)
            assert "authority_tier" in entry
            assert entry["authority_tier"] == T8_SCRATCH


class TestLegacyEntriesDefaultToT5:
    """test_legacy_entries_default_to_t5: entry without authority_tier reads as T5_DEFAULT."""

    def test_get_authority_tier_missing_field(self):
        legacy_entry = {"memory_id": "mem-legacy", "label": "old entry"}
        assert get_authority_tier(legacy_entry) == T5_DEFAULT

    def test_get_authority_tier_present_field(self):
        entry = {"memory_id": "mem-new", "authority_tier": 2}
        assert get_authority_tier(entry) == 2

    def test_query_back_defaults_legacy_entries(self, fixture_file: Path, memory_store: Path):
        legacy_entry = {
            "memory_id": "mem-legacy-001",
            "candidate_id": "cand-legacy",
            "memory_type": "canonical",
            "primitive_type": "state",
            "label": "Legacy entry without tier",
            "content": "This entry predates authority tier feature.",
            "confidence": 0.80,
            "source_document_id": "doc-old",
            "source_content_hash": "abc123",
            "source_decomposition_id": "decomp-old",
            "promotion_receipt_id": "receipt-old",
            "provenance": {"source_reference": "old", "evidence": "old", "is_inferred": False},
            "lineage": {},
            "timestamp": "2026-05-01T00:00:00+00:00",
        }
        (memory_store / "memories.jsonl").write_text(json.dumps(legacy_entry) + "\n")

        source = LocalFileSource(fixture_file, authority_tier=T2_ACTIVE)
        orchestrator = GenericIngestionOrchestrator(memory_store_path=memory_store)

        with patch(
            "runtime.model_router.call_with_fallback",
            return_value=_mock_call_with_fallback(TIERED_LLM_RESPONSE),
        ):
            result = orchestrator.ingest(source)

        assert result.verdict == "COMPLETE_CYCLE"

        for entry in result.query_proof.retrieved_entries:
            assert "authority_tier" in entry
            if entry["memory_id"] == "mem-legacy-001":
                assert entry["authority_tier"] == T5_DEFAULT
