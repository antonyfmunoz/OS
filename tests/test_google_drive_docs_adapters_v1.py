"""Tests for Google Drive and Docs Adapters v1.

Phase 96.8AB — adapter maturity validation.
"""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import pytest

from adapters.adapter_engine.google_drive_adapter_v1 import (
    DRIVE_ADAPTER_GOVERNANCE,
    FORBIDDEN_DRIVE_ACTIONS,
    DriveAdapterStatus,
    DriveCapabilityType,
    DriveMetadataResult,
    DriveOpenProof,
    GoogleDriveAdapterV1,
)
from adapters.adapter_engine.google_docs_adapter_v1 import (
    DOCS_ADAPTER_GOVERNANCE,
    FORBIDDEN_DOCS_ACTIONS,
    DocsAdapterStatus,
    DocsCapabilityType,
    ExtractionPath,
    ExtractionResult,
    GoogleDocsAdapterV1,
    NormalizedExtraction,
    normalize_text,
)


SAFE_CONFIG = {
    "safe_drive_url": "https://drive.google.com/drive/my-drive",
    "safe_doc_url_or_id": "https://docs.google.com/document/d/test123/edit",
    "safe_doc_title": "Test Doc",
    "cu_enabled": True,
    "api_enabled": True,
    "preview_char_limit": 100,
    "extraction_timeout_seconds": 30,
}


class TestGoogleDriveAdapterV1:
    def test_init(self) -> None:
        adapter = GoogleDriveAdapterV1(SAFE_CONFIG)
        assert adapter.adapter_id == "google-drive-adapter-v1"
        assert adapter.status == DriveAdapterStatus.IDLE
        assert DriveCapabilityType.GOOGLE_DRIVE_SAFE_OPEN in adapter.capabilities

    def test_safe_url_validation_passes(self) -> None:
        adapter = GoogleDriveAdapterV1(SAFE_CONFIG)
        errors = adapter.validate_url("https://drive.google.com/drive/my-drive")
        assert errors == []

    def test_arbitrary_url_blocked(self) -> None:
        adapter = GoogleDriveAdapterV1(SAFE_CONFIG)
        errors = adapter.validate_url("https://drive.google.com/drive/other-folder")
        assert "url_not_safe_target" in errors

    def test_empty_url_blocked(self) -> None:
        adapter = GoogleDriveAdapterV1(SAFE_CONFIG)
        errors = adapter.validate_url("")
        assert "url_empty" in errors

    def test_non_drive_url_blocked(self) -> None:
        adapter = GoogleDriveAdapterV1(SAFE_CONFIG)
        errors = adapter.validate_url("https://example.com/not-drive")
        assert "url_not_google_drive" in errors

    def test_open_safe_drive_success(self) -> None:
        adapter = GoogleDriveAdapterV1(SAFE_CONFIG)
        proof = adapter.open_safe_drive(trace_id="T1")
        assert proof.chrome_detected is True
        assert proof.drive_page_loaded is True
        assert proof.governance_state == "governed"
        assert proof.trace_id == "T1"
        assert adapter.status == DriveAdapterStatus.OPEN

    def test_open_with_bad_config(self) -> None:
        adapter = GoogleDriveAdapterV1({"safe_drive_url": ""})
        proof = adapter.open_safe_drive()
        assert proof.governance_state == "blocked"
        assert adapter.status == DriveAdapterStatus.ERROR

    def test_read_metadata(self) -> None:
        adapter = GoogleDriveAdapterV1(SAFE_CONFIG)
        result = adapter.read_metadata("file123", "Test Doc", trace_id="T1")
        assert result.file_id == "file123"
        assert result.content_hash != ""
        assert adapter.status == DriveAdapterStatus.METADATA_READ

    def test_governance_constraints(self) -> None:
        assert "no_mutation" in DRIVE_ADAPTER_GOVERNANCE
        assert "no_broad_drive_search" in DRIVE_ADAPTER_GOVERNANCE
        assert "no_arbitrary_url_access" in DRIVE_ADAPTER_GOVERNANCE

    def test_forbidden_actions(self) -> None:
        assert "broad_drive_search" in FORBIDDEN_DRIVE_ACTIONS
        assert "file_mutation" in FORBIDDEN_DRIVE_ACTIONS
        assert "credential_capture" in FORBIDDEN_DRIVE_ACTIONS

    def test_to_dict(self) -> None:
        adapter = GoogleDriveAdapterV1(SAFE_CONFIG)
        d = adapter.to_dict()
        assert d["adapter_id"] == "google-drive-adapter-v1"
        assert d["version"] == "v1"
        assert "GOOGLE_DRIVE_SAFE_OPEN" in d["capabilities"]


class TestGoogleDocsAdapterV1:
    def test_init_both_paths(self) -> None:
        adapter = GoogleDocsAdapterV1(SAFE_CONFIG)
        assert adapter.adapter_id == "google-docs-adapter-v1"
        caps = adapter.capabilities
        assert DocsCapabilityType.GOOGLE_DOCS_CU_EXTRACT in caps
        assert DocsCapabilityType.GOOGLE_DOCS_API_EXTRACT in caps

    def test_init_api_only(self) -> None:
        config = {**SAFE_CONFIG, "cu_enabled": False}
        adapter = GoogleDocsAdapterV1(config)
        caps = adapter.capabilities
        assert DocsCapabilityType.GOOGLE_DOCS_CU_EXTRACT not in caps
        assert DocsCapabilityType.GOOGLE_DOCS_API_EXTRACT in caps

    def test_safe_doc_validation(self) -> None:
        adapter = GoogleDocsAdapterV1(SAFE_CONFIG)
        errors = adapter.validate_doc_target(SAFE_CONFIG["safe_doc_url_or_id"])
        assert errors == []

    def test_arbitrary_doc_blocked(self) -> None:
        adapter = GoogleDocsAdapterV1(SAFE_CONFIG)
        errors = adapter.validate_doc_target("https://docs.google.com/document/d/other/edit")
        assert "doc_not_safe_target" in errors

    def test_open_safe_doc(self) -> None:
        adapter = GoogleDocsAdapterV1(SAFE_CONFIG)
        proof = adapter.open_safe_doc(trace_id="T1")
        assert proof.chrome_detected is True
        assert proof.doc_page_loaded is True
        assert proof.governance_state == "governed"

    def test_api_extraction(self) -> None:
        adapter = GoogleDocsAdapterV1(SAFE_CONFIG)
        result = adapter.extract(ExtractionPath.API, "Hello world content", trace_id="T1")
        assert result.char_count == len("Hello world content")
        assert result.word_count == 3
        assert result.content_hash != ""

    def test_cu_extraction(self) -> None:
        adapter = GoogleDocsAdapterV1(SAFE_CONFIG)
        result = adapter.extract(ExtractionPath.CU, "CU extracted text", trace_id="T1")
        assert result.extraction_path == "computer_use"
        assert result.char_count > 0

    def test_cu_extraction_blocked_when_disabled(self) -> None:
        config = {**SAFE_CONFIG, "cu_enabled": False}
        adapter = GoogleDocsAdapterV1(config)
        result = adapter.extract(ExtractionPath.CU, "text")
        assert result.governance_state == "blocked"
        assert "cu_extraction_not_enabled" in result.notes

    def test_api_extraction_blocked_when_disabled(self) -> None:
        config = {**SAFE_CONFIG, "api_enabled": False}
        adapter = GoogleDocsAdapterV1(config)
        result = adapter.extract(ExtractionPath.API, "text")
        assert result.governance_state == "blocked"

    def test_normalization(self) -> None:
        adapter = GoogleDocsAdapterV1(SAFE_CONFIG)
        extraction = adapter.extract(ExtractionPath.API, "  Hello   world  \n  test  ")
        normalized = adapter.normalize(extraction)
        assert normalized.normalized_content == "Hello world\ntest"
        assert normalized.normalized_hash != ""

    def test_preview_bounded(self) -> None:
        adapter = GoogleDocsAdapterV1(SAFE_CONFIG)
        long_text = "x" * 1000
        result = adapter.extract(ExtractionPath.API, long_text)
        assert len(result.preview) == 100  # preview_char_limit

    def test_normalize_text_deterministic(self) -> None:
        input1 = "  Hello   world  \n\n  test  line  "
        input2 = "  Hello   world  \n\n  test  line  "
        assert normalize_text(input1) == normalize_text(input2)

    def test_mutation_blocked(self) -> None:
        assert "document_mutation" in FORBIDDEN_DOCS_ACTIONS
        assert "no_document_edit" in DOCS_ADAPTER_GOVERNANCE

    def test_broad_search_blocked(self) -> None:
        assert "broad_drive_search" in FORBIDDEN_DOCS_ACTIONS


class TestExtractionResult:
    def test_content_hash_deterministic(self) -> None:
        r1 = ExtractionResult(
            extraction_id="e1",
            adapter_id="a1",
            doc_url_or_id="d1",
            doc_title="t1",
            extraction_path="api",
            raw_content="test content",
        )
        r2 = ExtractionResult(
            extraction_id="e2",
            adapter_id="a1",
            doc_url_or_id="d1",
            doc_title="t1",
            extraction_path="api",
            raw_content="test content",
        )
        r1.compute_content_hash()
        r2.compute_content_hash()
        assert r1.content_hash == r2.content_hash

    def test_different_content_different_hash(self) -> None:
        r1 = ExtractionResult(
            extraction_id="",
            adapter_id="a1",
            doc_url_or_id="d1",
            doc_title="t1",
            extraction_path="api",
            raw_content="content A",
        )
        r2 = ExtractionResult(
            extraction_id="",
            adapter_id="a1",
            doc_url_or_id="d1",
            doc_title="t1",
            extraction_path="api",
            raw_content="content B",
        )
        r1.compute_content_hash()
        r2.compute_content_hash()
        assert r1.content_hash != r2.content_hash


class TestNormalizedExtraction:
    def test_auto_hash_on_init(self) -> None:
        n = NormalizedExtraction(
            normalization_id="",
            source_extraction_id="e1",
            extraction_path="api",
            normalized_content="hello world",
        )
        assert n.normalized_hash != ""
        assert n.char_count == 11
        assert n.word_count == 2
