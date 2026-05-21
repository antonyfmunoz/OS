"""Tests for Layer 3 Phase 3 Slice A — Capability Catalog + TME Orchestrator.

Proves: dataclass construction, empty-catalog validity (Q18), manifest
vendor_docs_url field, GoogleDriveAdapterV1 carries the URL, orchestrator
skip path, orchestrator write path.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, _ROOT)

from adapters.adapter_engine.adapter_manifest import (
    AdapterManifest,
    AdapterMaturityLevel,
)
from adapters.adapter_engine.adapter_registry_contracts import CapabilityDescriptor
from adapters.adapter_engine.capability_catalog import (
    CapabilityCatalog,
    CatalogEntry,
)
from adapters.adapter_engine.capability_discovery import (
    CapabilityDiscoveryOrchestrator,
)
from adapters.adapter_engine.google_drive_adapter_v1 import GoogleDriveAdapterV1
from adapters.adapter_engine.modality import ModalityType
from adapters.adapter_engine.participant import ParticipantType
from composition.mastery.research.models import SourcePlan


class TestCatalogEntryConstructs:
    def test_defaults(self) -> None:
        entry = CatalogEntry(capability_id="test-cap", action_type="TEST_ACTION")
        assert entry.capability_id == "test-cap"
        assert entry.action_type == "TEST_ACTION"
        assert entry.description == ""
        assert entry.evidence == []
        assert entry.source_urls == []
        assert entry.confidence == 0.0
        assert entry.gotchas == []
        assert entry.requires_auth is None
        assert entry.requires_gui is None


class TestCapabilityCatalogConstructs:
    def test_defaults(self) -> None:
        cat = CapabilityCatalog(adapter_id="test-adapter", adapter_type="test")
        assert cat.adapter_id == "test-adapter"
        assert cat.adapter_type == "test"
        assert cat.vendor_docs_url is None
        assert cat.capabilities == []
        assert cat.gotchas == []
        assert cat.source_plan_notes == []
        assert cat.discovery_timestamp == ""
        assert cat.discovery_version == "slice-a"
        assert cat.maturity_evidence == ""


class TestCatalogEmptyIsValid:
    """Q18 load-bearing test: empty capabilities is the legitimate Slice A state."""

    def test_empty_capabilities_is_valid(self) -> None:
        cat = CapabilityCatalog(
            adapter_id="test-adapter",
            adapter_type="test",
            capabilities=[],
        )
        assert cat.is_empty is True
        d = cat.to_dict()
        assert d["capabilities"] == []
        assert d["adapter_id"] == "test-adapter"

    def test_non_empty_capabilities(self) -> None:
        cat = CapabilityCatalog(
            adapter_id="test-adapter",
            adapter_type="test",
            capabilities=[
                CatalogEntry(capability_id="c1", action_type="ACT1"),
            ],
        )
        assert cat.is_empty is False


class TestCatalogToDictRoundtrip:
    def test_serializable(self) -> None:
        cat = CapabilityCatalog(
            adapter_id="test-adapter",
            adapter_type="test",
            vendor_docs_url="https://example.com/docs",
            capabilities=[
                CatalogEntry(
                    capability_id="c1",
                    action_type="ACT1",
                    description="A capability",
                    evidence=["found in docs"],
                    source_urls=["https://example.com/docs/page"],
                    confidence=0.8,
                    gotchas=["watch out for X"],
                    requires_auth=True,
                    requires_gui=False,
                ),
            ],
            gotchas=["adapter-level gotcha"],
            source_plan_notes=["checked registry"],
            discovery_timestamp="2026-05-21T00:00:00+00:00",
            discovery_version="slice-a",
            maturity_evidence="some evidence",
        )
        d = cat.to_dict()
        raw = json.dumps(d)
        loaded = json.loads(raw)
        assert loaded["adapter_id"] == "test-adapter"
        assert loaded["vendor_docs_url"] == "https://example.com/docs"
        assert len(loaded["capabilities"]) == 1
        assert loaded["capabilities"][0]["capability_id"] == "c1"
        assert loaded["capabilities"][0]["confidence"] == 0.8
        assert loaded["gotchas"] == ["adapter-level gotcha"]


class TestManifestVendorDocsUrlField:
    def test_default_none(self) -> None:
        m = AdapterManifest(
            adapter_id="test",
            adapter_type="test",
            modalities=[ModalityType.API],
            participant_type=ParticipantType.EXTERNAL,
        )
        assert m.vendor_docs_url is None

    def test_set_and_serialize(self) -> None:
        m = AdapterManifest(
            adapter_id="test",
            adapter_type="test",
            modalities=[ModalityType.API],
            participant_type=ParticipantType.EXTERNAL,
            vendor_docs_url="https://example.com/docs",
        )
        assert m.vendor_docs_url == "https://example.com/docs"
        d = m.to_dict()
        assert d["vendor_docs_url"] == "https://example.com/docs"

    def test_none_serializes(self) -> None:
        m = AdapterManifest(
            adapter_id="test",
            adapter_type="test",
            modalities=[ModalityType.API],
            participant_type=ParticipantType.EXTERNAL,
        )
        d = m.to_dict()
        assert d["vendor_docs_url"] is None


class TestGoogleDriveManifestHasVendorDocsUrl:
    def test_manifest_carries_url(self) -> None:
        m = GoogleDriveAdapterV1.MANIFEST
        assert m.vendor_docs_url == "https://developers.google.com/workspace/drive"
        assert m.adapter_id == "google-drive-adapter-v1"


class TestOrchestratorSkipsWhenNoUrl:
    def test_no_vendor_url_produces_skip_note(self, tmp_path: Path) -> None:
        manifest = AdapterManifest(
            adapter_id="no-url-adapter",
            adapter_type="test",
            modalities=[ModalityType.API],
            participant_type=ParticipantType.EXTERNAL,
        )
        orch = CapabilityDiscoveryOrchestrator(catalog_root=tmp_path)
        catalog = orch.discover(manifest)

        assert catalog.adapter_id == "no-url-adapter"
        assert catalog.is_empty is True
        assert any("discovery skipped" in n for n in catalog.source_plan_notes)
        assert catalog.discovery_timestamp != ""

        cat_path = tmp_path / "no-url-adapter" / "catalog.json"
        assert cat_path.exists()
        loaded = json.loads(cat_path.read_text(encoding="utf-8"))
        assert loaded["adapter_id"] == "no-url-adapter"


class TestOrchestratorWritesCatalog:
    def test_with_vendor_url(self, tmp_path: Path) -> None:
        manifest = AdapterManifest(
            adapter_id="test-adapter-v1",
            adapter_type="test_tool",
            modalities=[ModalityType.API],
            participant_type=ParticipantType.EXTERNAL,
            vendor_docs_url="https://example.com/docs",
        )

        mock_plan = SourcePlan(
            tool_slug="test_tool",
            sources=[],
            notes=["checked tool_doc_registry.md", "test note"],
        )

        with patch(
            "adapters.adapter_engine.capability_discovery.discover_sources",
            return_value=mock_plan,
        ) as mock_ds:
            orch = CapabilityDiscoveryOrchestrator(catalog_root=tmp_path)
            catalog = orch.discover(manifest)

            mock_ds.assert_called_once_with(
                tool_slug="test_tool",
                official_url="https://example.com/docs",
            )

        assert catalog.adapter_id == "test-adapter-v1"
        assert catalog.vendor_docs_url == "https://example.com/docs"
        assert catalog.is_empty is True
        assert catalog.discovery_version == "slice-a"
        assert "checked tool_doc_registry.md" in catalog.source_plan_notes
        assert "test note" in catalog.source_plan_notes

        cat_path = tmp_path / "test-adapter-v1" / "catalog.json"
        assert cat_path.exists()
        loaded = json.loads(cat_path.read_text(encoding="utf-8"))
        assert loaded["adapter_id"] == "test-adapter-v1"
        assert loaded["capabilities"] == []
        assert loaded["vendor_docs_url"] == "https://example.com/docs"
