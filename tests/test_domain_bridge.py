"""Tests for ontology-domain bridge — business as first domain projection."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")

from substrate.understanding.ontology.primitive_decomposition_v1 import PrimitiveObservation, PrimitiveType
from substrate.understanding.domains.contract import DomainBridge, DomainProjection
from substrate.understanding.domains.business import BusinessBridge
from adapters.data_source_adapters.local_file_source import LocalFileSource
from substrate.understanding.perception.orchestrator import GenericIngestionOrchestrator


BUSINESS_LLM_RESPONSE = json.dumps(
    {
        "observations": [
            {
                "primitive_type": "constraint",
                "label": "Founder must close first 10 sales before hiring a salesperson",
                "description": "Hiring a salesperson for an unproven process trains someone to fail. Founder does all sales until 10 closes.",
                "confidence": 0.92,
                "source_reference": "test.md:lines 1-5",
                "evidence": "Founder closes first. No salesperson hire until process proven.",
                "is_inferred": False,
            },
            {
                "primitive_type": "action",
                "label": "Direct outreach via DM to ICP prospects",
                "description": "Direct message the people who match your ideal customer profile. Don't wait for them to find you.",
                "confidence": 0.88,
                "source_reference": "test.md:lines 6-10",
                "evidence": "DM the people who match your ICP.",
                "is_inferred": False,
            },
            {
                "primitive_type": "goal",
                "label": "Reach $10K monthly revenue through organic conversion",
                "description": "First revenue milestone before scaling. Proves the offer converts organically.",
                "confidence": 0.90,
                "source_reference": "test.md:lines 11-15",
                "evidence": "Reach $10K/month before any paid advertising.",
                "is_inferred": False,
            },
            {
                "primitive_type": "state",
                "label": "Memory palace has 4 navigation layers",
                "description": "The system uses Palace, Wing, Room, Locus for structured codebase navigation.",
                "confidence": 0.95,
                "source_reference": "test.md:lines 20-25",
                "evidence": "Palace — the whole system. Wing — a top-level module.",
                "is_inferred": False,
            },
        ],
        "relationships": [
            {
                "from_index": 0,
                "to_index": 1,
                "relationship_type": "constrains",
                "confidence": 0.90,
                "description": "Hiring constraint governs outreach actions.",
            },
        ],
    }
)


def _mock_call_with_fallback(output: str):
    result = MagicMock()
    result.output = output
    return result


def _make_obs(
    obs_id: str,
    ptype: str,
    label: str,
    description: str,
    confidence: float = 0.90,
) -> PrimitiveObservation:
    return PrimitiveObservation(
        observation_id=obs_id,
        primitive_type=PrimitiveType(ptype),
        label=label,
        description=description,
        confidence=confidence,
        source_reference="test:1",
        evidence="test evidence",
    )


@pytest.fixture
def fixture_file(tmp_path: Path) -> Path:
    p = tmp_path / "business_test.md"
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


class TestBridgeProtocol:
    """test_bridge_protocol_conformance: BusinessBridge implements DomainBridge."""

    def test_implements_protocol(self):
        bridge = BusinessBridge()
        assert isinstance(bridge, DomainBridge)
        assert bridge.domain_id == "business"
        assert len(bridge.describes()) > 0


class TestBridgeNoMatch:
    """test_bridge_returns_none_for_no_match: non-business observations return None."""

    def test_non_business_observation(self):
        bridge = BusinessBridge()
        obs = _make_obs(
            "obs-arch1",
            "state",
            "Memory palace has 4 navigation layers",
            "The system uses Palace, Wing, Room, Locus for structured codebase navigation.",
        )
        result = bridge.bridge(obs)
        assert result is None

    def test_time_type_not_bridgeable(self):
        bridge = BusinessBridge()
        obs = _make_obs(
            "obs-time1",
            "time",
            "Founded in 2024",
            "The company was founded in 2024.",
        )
        result = bridge.bridge(obs)
        assert result is None


class TestStructuralMapping:
    """test_bridge_structural_mapping: known patterns produce expected projections."""

    def test_hiring_constraint_maps_to_hire_salesperson(self):
        bridge = BusinessBridge()
        obs = _make_obs(
            "obs-hire1",
            "constraint",
            "Founder must close first 10 sales before hiring a salesperson",
            "Hiring a salesperson for an unproven process trains someone to fail.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.domain_id == "business"
        assert proj.domain_primitive_type == "hire_salesperson"
        assert proj.ontology_observation_ref == "obs-hire1"
        assert proj.properties["business_domain"] == "hiring"

    def test_outreach_action_maps_to_outreach_before_content(self):
        bridge = BusinessBridge()
        obs = _make_obs(
            "obs-out1",
            "action",
            "Direct outreach via DM to ICP prospects",
            "Direct message the people who match your ideal customer profile.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.domain_primitive_type == "outreach_before_content"
        assert proj.properties["business_domain"] == "sales"

    def test_revenue_goal_maps_to_finance(self):
        bridge = BusinessBridge()
        obs = _make_obs(
            "obs-rev1",
            "goal",
            "Reach $10K monthly revenue through organic conversion",
            "First revenue milestone before scaling.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["business_domain"] == "finance"

    def test_confidence_does_not_exceed_source(self):
        bridge = BusinessBridge()
        obs = _make_obs(
            "obs-conf1",
            "constraint",
            "Never hire before revenue supports it",
            "Revenue must cover the cost of hire.",
            confidence=0.60,
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.confidence <= obs.confidence


class TestProjectionBackReference:
    """test_projection_back_reference_resolves: projection refs point to valid obs."""

    def test_back_reference_matches_observation_id(self, fixture_file: Path, memory_store: Path):
        source = LocalFileSource(fixture_file)
        orchestrator = GenericIngestionOrchestrator(memory_store_path=memory_store)

        with patch(
            "execution.runtime.model_router.call_with_fallback",
            return_value=_mock_call_with_fallback(BUSINESS_LLM_RESPONSE),
        ):
            result = orchestrator.ingest(source)

        assert result.verdict == "COMPLETE_CYCLE"

        obs_ids = {o.observation_id for o in result.decomposition.observations}
        for proj in result.projections:
            assert proj.ontology_observation_ref in obs_ids


class TestPipelinePersistsBothLayers:
    """test_pipeline_persists_both_layers: both obs + projections in memories.jsonl."""

    def test_both_layers_in_memories(self, fixture_file: Path, memory_store: Path):
        source = LocalFileSource(fixture_file)
        orchestrator = GenericIngestionOrchestrator(memory_store_path=memory_store)

        with patch(
            "execution.runtime.model_router.call_with_fallback",
            return_value=_mock_call_with_fallback(BUSINESS_LLM_RESPONSE),
        ):
            result = orchestrator.ingest(source)

        assert result.verdict == "COMPLETE_CYCLE"

        lines = [l for l in (memory_store / "memories.jsonl").read_text().strip().split("\n") if l]

        canonical_count = sum(1 for l in lines if json.loads(l)["memory_type"] == "canonical")
        projection_count = sum(
            1 for l in lines if json.loads(l)["memory_type"] == "domain_projection"
        )

        n_obs = len(result.decomposition.observations)
        n_proj = len(result.projections)

        assert canonical_count == n_obs
        assert projection_count == n_proj
        assert projection_count >= 1
        assert len(lines) == n_obs + n_proj

    def test_projection_entries_have_domain_fields(self, fixture_file: Path, memory_store: Path):
        source = LocalFileSource(fixture_file)
        orchestrator = GenericIngestionOrchestrator(memory_store_path=memory_store)

        with patch(
            "execution.runtime.model_router.call_with_fallback",
            return_value=_mock_call_with_fallback(BUSINESS_LLM_RESPONSE),
        ):
            result = orchestrator.ingest(source)

        lines = [l for l in (memory_store / "memories.jsonl").read_text().strip().split("\n") if l]

        for line in lines:
            entry = json.loads(line)
            if entry["memory_type"] == "domain_projection":
                assert "domain_id" in entry
                assert "domain_primitive_type" in entry
                assert "ontology_observation_ref" in entry
                assert "projection_id" in entry
                assert entry["domain_id"] == "business"
