"""Tests for GWSSource — Google Workspace ingestion source adapter."""

import hashlib
import os
import sys
from typing import Any
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")

from adapters.data_source_adapters.gws_source import GWSSource
from substrate.understanding.perception.source import RawContent, Source


SAMPLE_DOC_ID = "1aBcDeFgHiJkLmNoPqRsTuVwXyZ"
SAMPLE_DOC_CONTENT = (
    "EntrepreneurOS is a production AI business operating system. "
    "It automates business operations through governed agents, "
    "structured memory, and deterministic execution pipelines."
)
SAMPLE_DOC_META = {
    "id": SAMPLE_DOC_ID,
    "name": "EOS Architecture Overview",
    "mimeType": "application/vnd.google-apps.document",
    "modifiedTime": "2026-05-10T14:30:00.000Z",
    "webViewLink": f"https://docs.google.com/document/d/{SAMPLE_DOC_ID}/edit",
}


def _make_scanner(
    read_return: str = SAMPLE_DOC_CONTENT,
    list_return: list[dict[str, Any]] | None = None,
) -> MagicMock:
    scanner = MagicMock()
    scanner.read_doc.return_value = read_return
    scanner.list_all_docs.return_value = (
        list_return if list_return is not None else [SAMPLE_DOC_META]
    )
    return scanner


class TestGWSSourceImplementsProtocol:
    def test_structural_conformance(self):
        """GWSSource satisfies the Source protocol at the type level."""
        assert isinstance(GWSSource, type)
        assert hasattr(GWSSource, "source_type")
        assert hasattr(GWSSource, "source_id")
        assert callable(getattr(GWSSource, "read", None))
        assert callable(getattr(GWSSource, "metadata", None))
        assert callable(getattr(GWSSource, "exists", None))

    def test_isinstance_check(self):
        """GWSSource instances pass runtime_checkable Source check."""
        scanner = _make_scanner()
        source = GWSSource(SAMPLE_DOC_ID, scanner, SAMPLE_DOC_META)
        assert isinstance(source, Source)

    def test_source_type_is_google_workspace(self):
        scanner = _make_scanner()
        source = GWSSource(SAMPLE_DOC_ID, scanner)
        assert source.source_type == "google_workspace"

    def test_source_id_contains_doc_id(self):
        scanner = _make_scanner()
        source = GWSSource(SAMPLE_DOC_ID, scanner)
        assert source.source_id == f"gws:{SAMPLE_DOC_ID}"


class TestGWSSourceWithMockedScanner:
    def test_read_returns_raw_content(self):
        scanner = _make_scanner()
        source = GWSSource(SAMPLE_DOC_ID, scanner, SAMPLE_DOC_META)
        raw = source.read()

        assert isinstance(raw, RawContent)
        assert raw.content == SAMPLE_DOC_CONTENT
        assert raw.content_type == "text/plain"
        assert raw.size_bytes == len(SAMPLE_DOC_CONTENT.encode("utf-8"))
        expected_sha = hashlib.sha256(SAMPLE_DOC_CONTENT.encode("utf-8")).hexdigest()
        assert raw.sha256 == expected_sha
        scanner.read_doc.assert_called_once_with(SAMPLE_DOC_ID)

    def test_read_caches_content(self):
        scanner = _make_scanner()
        source = GWSSource(SAMPLE_DOC_ID, scanner)
        raw1 = source.read()
        raw2 = source.read()
        assert raw1 is raw2
        scanner.read_doc.assert_called_once()

    def test_read_empty_doc(self):
        scanner = _make_scanner(read_return="")
        source = GWSSource(SAMPLE_DOC_ID, scanner)
        raw = source.read()
        assert raw.content == ""
        assert raw.size_bytes == 0
        assert len(raw.sha256) == 64

    def test_exists_with_meta(self):
        scanner = _make_scanner()
        source = GWSSource(SAMPLE_DOC_ID, scanner, SAMPLE_DOC_META)
        assert source.exists() is True
        scanner.list_all_docs.assert_not_called()

    def test_exists_without_meta_calls_scanner(self):
        scanner = _make_scanner()
        source = GWSSource(SAMPLE_DOC_ID, scanner)
        assert source.exists() is True
        scanner.list_all_docs.assert_called_once_with(limit=500)

    def test_exists_returns_false_when_not_found(self):
        scanner = _make_scanner(list_return=[])
        source = GWSSource(SAMPLE_DOC_ID, scanner)
        assert source.exists() is False

    def test_exists_meta_mismatch_falls_through(self):
        wrong_meta = {"id": "different-doc-id", "name": "Other"}
        scanner = _make_scanner()
        source = GWSSource(SAMPLE_DOC_ID, scanner, wrong_meta)
        assert source.exists() is True
        scanner.list_all_docs.assert_called_once()


class TestGWSSourceMetadataShape:
    def test_metadata_has_standard_keys(self):
        scanner = _make_scanner()
        source = GWSSource(SAMPLE_DOC_ID, scanner, SAMPLE_DOC_META)
        source.read()
        meta = source.metadata()

        assert "path" in meta
        assert "filename" in meta
        assert "extension" in meta
        assert "size_bytes" in meta
        assert "mtime" in meta
        assert "content_type" in meta

    def test_metadata_maps_gws_fields(self):
        scanner = _make_scanner()
        source = GWSSource(SAMPLE_DOC_ID, scanner, SAMPLE_DOC_META)
        source.read()
        meta = source.metadata()

        assert meta["path"] == SAMPLE_DOC_META["webViewLink"]
        assert meta["filename"] == SAMPLE_DOC_META["name"]
        assert meta["extension"] == ".gdoc"
        assert meta["mtime"] == SAMPLE_DOC_META["modifiedTime"]
        assert meta["content_type"] == "text/plain"
        assert meta["doc_id"] == SAMPLE_DOC_ID
        assert meta["source_system"] == "google_workspace"

    def test_metadata_without_meta_uses_defaults(self):
        scanner = _make_scanner()
        source = GWSSource(SAMPLE_DOC_ID, scanner)
        meta = source.metadata()

        assert meta["path"] == f"gws://{SAMPLE_DOC_ID}"
        assert meta["filename"] == SAMPLE_DOC_ID
        assert meta["size_bytes"] == 0

    def test_metadata_size_after_read(self):
        scanner = _make_scanner()
        source = GWSSource(SAMPLE_DOC_ID, scanner, SAMPLE_DOC_META)
        source.read()
        meta = source.metadata()
        assert meta["size_bytes"] == len(SAMPLE_DOC_CONTENT.encode("utf-8"))
