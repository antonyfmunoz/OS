"""Tests for Layer 3 Phase 3 Slice B — LLM capability extraction.

Proves: JSON parse, capability_id validation, evidence truncation,
empty artifact handling, LLM failure containment, full orchestrator
flow, research agent failure, confidence formula, integration extraction.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, _ROOT)

from adapters.adapter_engine.adapter_manifest import AdapterManifest
from adapters.adapter_engine.capability_catalog import CatalogEntry
from adapters.adapter_engine.capability_discovery import (
    CapabilityDiscoveryOrchestrator,
)
from adapters.adapter_engine.modality import ModalityType
from adapters.adapter_engine.participant import ParticipantType


def _make_manifest(
    adapter_id: str = "test-adapter-v1",
    adapter_type: str = "test_tool",
    vendor_docs_url: str | None = "https://example.com/docs",
) -> AdapterManifest:
    return AdapterManifest(
        adapter_id=adapter_id,
        adapter_type=adapter_type,
        modalities=[ModalityType.API],
        participant_type=ParticipantType.EXTERNAL,
        vendor_docs_url=vendor_docs_url,
    )


_VALID_TWO_CAP_JSON = json.dumps(
    {
        "capabilities": [
            {
                "capability_id": "test_tool-list-items",
                "action_type": "LIST_ITEMS",
                "description": "List all items in the workspace.",
                "evidence": ["Use the items.list endpoint to retrieve items."],
                "gotchas": ["Rate limited to 100 requests/min."],
            },
            {
                "capability_id": "test_tool-get-item",
                "action_type": "GET_ITEM",
                "description": "Retrieve a single item by ID.",
                "evidence": [
                    "GET /items/{id} returns the item.",
                    "Requires read scope.",
                ],
                "gotchas": [],
            },
        ]
    }
)


class TestValidJsonParse:
    def test_two_capabilities_parsed(self) -> None:
        manifest = _make_manifest()
        orch = CapabilityDiscoveryOrchestrator()
        entries, drops = orch._parse_extraction(_VALID_TWO_CAP_JSON, manifest)

        assert entries is not None
        assert len(entries) == 2
        assert entries[0].capability_id == "test_tool-list-items"
        assert entries[0].action_type == "LIST_ITEMS"
        assert entries[0].description == "List all items in the workspace."
        assert len(entries[0].evidence) == 1
        assert entries[0].requires_auth is True
        assert entries[0].requires_gui is False
        assert entries[1].capability_id == "test_tool-get-item"
        assert len(entries[1].evidence) == 2
        assert len(drops) == 0


class TestInvalidCapabilityIdRejected:
    def test_mixed_valid_invalid(self) -> None:
        raw = json.dumps(
            {
                "capabilities": [
                    {
                        "capability_id": "test_tool-list-items",
                        "action_type": "LIST_ITEMS",
                        "description": "Valid entry.",
                        "evidence": ["evidence"],
                        "gotchas": [],
                    },
                    {
                        "capability_id": "has spaces invalid",
                        "action_type": "BAD",
                        "description": "Invalid entry.",
                        "evidence": [],
                        "gotchas": [],
                    },
                ]
            }
        )
        manifest = _make_manifest()
        orch = CapabilityDiscoveryOrchestrator()
        entries, drops = orch._parse_extraction(raw, manifest)

        assert entries is not None
        assert len(entries) == 1
        assert entries[0].capability_id == "test_tool-list-items"
        assert len(drops) == 1
        assert "invalid capability_id" in drops[0]


class TestEvidenceTruncation:
    def test_long_evidence_truncated_to_500(self) -> None:
        long_evidence = "x" * 600
        raw = json.dumps(
            {
                "capabilities": [
                    {
                        "capability_id": "test_tool-do-thing",
                        "action_type": "DO_THING",
                        "description": "Does a thing.",
                        "evidence": [long_evidence],
                        "gotchas": [],
                    },
                ]
            }
        )
        manifest = _make_manifest()
        orch = CapabilityDiscoveryOrchestrator()
        entries, _ = orch._parse_extraction(raw, manifest)

        assert entries is not None
        assert len(entries) == 1
        assert len(entries[0].evidence[0]) == 500


class TestEmptyArtifactHandling:
    def test_empty_patterns_still_calls_llm(self) -> None:
        manifest = _make_manifest()
        orch = CapabilityDiscoveryOrchestrator()

        mock_result = MagicMock()
        mock_result.output = _VALID_TWO_CAP_JSON

        with patch(
            "substrate.execution.runtime.model_router.call_with_fallback",
            return_value=mock_result,
        ):
            caps, drops = orch._extract_capabilities(
                manifest,
                {"extracted_patterns": {"usage": [], "api": [], "workflows": []}},
                "",
            )

        assert len(caps) == 2
        assert caps[0].capability_id == "test_tool-list-items"


class TestLlmFailureReturnsEmpty:
    def test_exception_produces_empty_with_drop(self) -> None:
        manifest = _make_manifest()
        orch = CapabilityDiscoveryOrchestrator()

        with patch(
            "substrate.execution.runtime.model_router.call_with_fallback",
            side_effect=Exception("LLM unavailable"),
        ):
            caps, drops = orch._extract_capabilities(manifest, {}, "")

        assert caps == []
        assert any("all extraction attempts failed" in d for d in drops)


class TestFullOrchestratorMocked:
    def test_discover_with_mocked_research_and_llm(self, tmp_path: Path) -> None:
        manifest = _make_manifest()

        artifact_dir = tmp_path / "research"
        artifact_dir.mkdir()
        artifact_path = artifact_dir / "artifact.json"
        artifact_path.write_text(
            json.dumps(
                {
                    "tool_slug": "test_tool",
                    "extracted_patterns": {"usage": [], "api": [], "workflows": []},
                }
            )
        )
        raw_dir = artifact_dir / "raw"
        raw_dir.mkdir()
        (raw_dir / "page1.txt").write_text("some raw content")

        mock_research_result = MagicMock()
        mock_research_result.status = MagicMock()
        mock_research_result.status.value = "ok"
        mock_research_result.artifact_path = str(artifact_path)
        mock_research_result.run_dir = str(artifact_dir)

        from substrate.composition.mastery.research.models import ResearchStatus

        mock_research_result.status = ResearchStatus.OK

        mock_llm_result = MagicMock()
        mock_llm_result.output = _VALID_TWO_CAP_JSON

        mock_plan = MagicMock()
        mock_plan.notes = ["checked registry"]

        with (
            patch(
                "adapters.adapter_engine.capability_discovery.discover_sources",
                return_value=mock_plan,
            ),
            patch(
                "composition.mastery.research.agent.run",
                return_value=mock_research_result,
            ),
            patch(
                "substrate.execution.runtime.model_router.call_with_fallback",
                return_value=mock_llm_result,
            ),
        ):
            orch = CapabilityDiscoveryOrchestrator(catalog_root=tmp_path / "catalogs")
            catalog = orch.discover(manifest)

        assert catalog.adapter_id == "test-adapter-v1"
        assert catalog.discovery_version == "slice-b"
        assert len(catalog.capabilities) == 2
        assert catalog.capabilities[0].capability_id == "test_tool-list-items"

        cat_path = tmp_path / "catalogs" / "test-adapter-v1" / "catalog.json"
        assert cat_path.exists()
        loaded = json.loads(cat_path.read_text())
        assert len(loaded["capabilities"]) == 2
        assert loaded["discovery_version"] == "slice-b"


class TestResearchAgentFailure:
    def test_exception_still_writes_catalog(self, tmp_path: Path) -> None:
        manifest = _make_manifest()

        mock_plan = MagicMock()
        mock_plan.notes = ["checked registry"]

        with (
            patch(
                "adapters.adapter_engine.capability_discovery.discover_sources",
                return_value=mock_plan,
            ),
            patch.object(
                CapabilityDiscoveryOrchestrator,
                "_run_research",
                side_effect=RuntimeError("research broke"),
            ),
        ):
            orch = CapabilityDiscoveryOrchestrator(catalog_root=tmp_path / "catalogs")
            catalog = orch.discover(manifest)

        assert catalog.adapter_id == "test-adapter-v1"
        assert catalog.capabilities == []
        assert any("extraction error: RuntimeError" in n for n in catalog.source_plan_notes)

        cat_path = tmp_path / "catalogs" / "test-adapter-v1" / "catalog.json"
        assert cat_path.exists()


class TestConfidenceFormula:
    def test_evidence_count_to_confidence(self) -> None:
        manifest = _make_manifest()
        orch = CapabilityDiscoveryOrchestrator()

        cases = [
            (0, 0.1),
            (1, 0.3),
            (3, 0.7),
            (5, 1.0),
            (10, 1.0),
        ]
        for ev_count, expected_conf in cases:
            item = {
                "capability_id": "test_tool-do-thing",
                "action_type": "DO_THING",
                "description": "Does a thing.",
                "evidence": [f"evidence {i}" for i in range(ev_count)],
                "gotchas": [],
            }
            entry, reason = orch._validate_entry(item, manifest)
            assert entry is not None, f"Failed for ev_count={ev_count}"
            assert entry.confidence == pytest.approx(expected_conf), (
                f"ev_count={ev_count}: got {entry.confidence}"
            )


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "capability_discovery" / "googledrive"


def _load_fixture() -> tuple[dict, str]:
    artifact = json.loads((FIXTURE_DIR / "artifact.json").read_text(encoding="utf-8"))
    raw = (FIXTURE_DIR / "raw_excerpt.txt").read_text(encoding="utf-8")
    return artifact, raw


@pytest.mark.integration
class TestIntegrationGoogleDriveExtraction:
    def test_real_llm_extraction(self) -> None:
        if not FIXTURE_DIR.exists():
            pytest.skip("fixture not yet generated (awaiting operator approval)")

        artifact_data, raw_excerpt = _load_fixture()
        manifest = AdapterManifest(
            adapter_id="google-drive-adapter-v1",
            adapter_type="google_drive",
            modalities=[ModalityType.API],
            participant_type=ParticipantType.EXTERNAL,
            vendor_docs_url="https://developers.google.com/workspace/drive",
        )

        orch = CapabilityDiscoveryOrchestrator()
        caps, drops = orch._extract_capabilities(manifest, artifact_data, raw_excerpt)

        assert len(caps) >= 3, f"Expected >=3 capabilities, got {len(caps)}"

        import re

        cap_id_re = re.compile(r"^[a-z][a-z0-9_-]+$")
        for c in caps:
            assert cap_id_re.match(c.capability_id), f"Bad cap_id: {c.capability_id}"
            assert 0.0 < c.confidence <= 1.0
            assert len(c.evidence) > 0

        action_types = {c.action_type for c in caps}
        has_basic = any(kw in at for at in action_types for kw in ("LIST", "GET", "CREATE"))
        assert has_basic, f"No basic CRUD action found in {action_types}"
