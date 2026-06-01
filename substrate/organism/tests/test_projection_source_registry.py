"""Tests for ProjectionSourceRegistry (Phase 14.0)."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from substrate.organism.projection_source_registry import (
    ProjectionName,
    ProjectionSource,
    ProjectionSourceRegistry,
    ProjectionSourceType,
    ReadStatus,
    SourceCanonicality,
    create_initial_registry,
)


class TestProjectionSourceType:
    def test_all_values_present(self):
        expected = {
            "google_docs", "google_drive", "github_repository",
            "device_filesystem", "local_filesystem", "audit_artifact",
            "production_truth_artifact", "runtime_state", "unknown",
        }
        actual = {e.value for e in ProjectionSourceType}
        assert actual == expected

    def test_string_enum(self):
        assert ProjectionSourceType.GOOGLE_DOCS == "google_docs"
        assert isinstance(ProjectionSourceType.GOOGLE_DOCS, str)


class TestProjectionName:
    def test_all_values_present(self):
        expected = {"UMH", "Shared", "Unknown"}
        actual = {e.value for e in ProjectionName}
        assert actual == expected

    def test_string_enum(self):
        assert ProjectionName.UMH == "UMH"


class TestSourceCanonicality:
    def test_all_values_present(self):
        expected = {
            "production_truth", "candidate_canonical", "partial",
            "stale", "historical", "duplicate", "divergent", "unknown",
        }
        actual = {e.value for e in SourceCanonicality}
        assert actual == expected

    def test_no_source_auto_canonical(self):
        src = ProjectionSource()
        assert src.canonicality == SourceCanonicality.UNKNOWN.value


class TestReadStatus:
    def test_all_values_present(self):
        expected = {
            "unread", "metadata_only", "inspected",
            "fully_read", "permission_denied", "unavailable",
        }
        actual = {e.value for e in ReadStatus}
        assert actual == expected


class TestProjectionSource:
    def test_default_values(self):
        src = ProjectionSource()
        assert src.source_id.startswith("psrc-")
        assert src.projection == ProjectionName.UNKNOWN.value
        assert src.source_type == ProjectionSourceType.UNKNOWN.value
        assert src.canonicality == SourceCanonicality.UNKNOWN.value
        assert src.read_status == ReadStatus.UNREAD.value
        assert src.last_seen_at > 0

    def test_to_dict(self):
        src = ProjectionSource(
            source_id="test-1",
            projection="EOS",
            name="test_source",
        )
        d = src.to_dict()
        assert d["source_id"] == "test-1"
        assert d["projection"] == "EOS"
        assert d["name"] == "test_source"
        assert "contains" in d
        assert "evidence" in d

    def test_from_dict(self):
        d = {
            "source_id": "test-2",
            "projection": "UMH",
            "source_type": "local_filesystem",
            "name": "umh_source",
        }
        src = ProjectionSource.from_dict(d)
        assert src.source_id == "test-2"
        assert src.projection == "UMH"
        assert src.name == "umh_source"

    def test_from_dict_ignores_unknown_keys(self):
        d = {
            "source_id": "test-3",
            "unknown_key": "should be ignored",
        }
        src = ProjectionSource.from_dict(d)
        assert src.source_id == "test-3"
        assert not hasattr(src, "unknown_key")

    def test_roundtrip_serialization(self):
        src = ProjectionSource(
            source_id="rt-1",
            projection="TestProjection",
            source_type=ProjectionSourceType.DEVICE_FILESYSTEM.value,
            name="beast_test",
            device="Test Device",
            contains=["frontend", "backend"],
            canonicality=SourceCanonicality.CANDIDATE_CANONICAL.value,
        )
        d = src.to_dict()
        restored = ProjectionSource.from_dict(d)
        assert restored.source_id == src.source_id
        assert restored.projection == src.projection
        assert restored.contains == src.contains


class TestProjectionSourceRegistry:
    def test_empty_registry(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            reg = ProjectionSourceRegistry(path=path)
            assert reg.count() == 0
        finally:
            os.unlink(path)

    def test_register_and_count(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            reg = ProjectionSourceRegistry(path=path)
            src = ProjectionSource(name="test", projection="EOS", source_type="local_filesystem")
            reg.register(src)
            assert reg.count() == 1
        finally:
            os.unlink(path)

    def test_register_deduplicates(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            reg = ProjectionSourceRegistry(path=path)
            src1 = ProjectionSource(name="test", projection="EOS", source_type="local_filesystem")
            src2 = ProjectionSource(name="test", projection="EOS", source_type="local_filesystem")
            reg.register(src1)
            reg.register(src2)
            assert reg.count() == 1
        finally:
            os.unlink(path)

    def test_list_sources_by_projection(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            reg = ProjectionSourceRegistry(path=path)
            reg.register(ProjectionSource(name="a", projection="EOS", source_type="local_filesystem"))
            reg.register(ProjectionSource(name="b", projection="UMH", source_type="local_filesystem"))
            eos_sources = reg.list_sources(projection="EOS")
            assert len(eos_sources) == 1
            assert eos_sources[0].projection == "EOS"
        finally:
            os.unlink(path)

    def test_update_read_status(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            reg = ProjectionSourceRegistry(path=path)
            src = ProjectionSource(source_id="upd-1", name="test", projection="EOS", source_type="local_filesystem")
            reg.register(src)
            assert reg.update_read_status("upd-1", ReadStatus.INSPECTED.value)
            assert reg.get("upd-1").read_status == ReadStatus.INSPECTED.value
        finally:
            os.unlink(path)

    def test_update_canonicality(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            reg = ProjectionSourceRegistry(path=path)
            src = ProjectionSource(source_id="can-1", name="test", projection="EOS", source_type="local_filesystem")
            reg.register(src)
            assert reg.update_canonicality("can-1", SourceCanonicality.PRODUCTION_TRUTH.value)
            assert reg.get("can-1").canonicality == SourceCanonicality.PRODUCTION_TRUTH.value
        finally:
            os.unlink(path)

    def test_sources_requiring_permission(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            reg = ProjectionSourceRegistry(path=path)
            reg.register(ProjectionSource(name="a", projection="EOS", source_type="google_docs", permission_required=True))
            reg.register(ProjectionSource(name="b", projection="UMH", source_type="local_filesystem", permission_required=False))
            perm = reg.sources_requiring_permission()
            assert len(perm) == 1
            assert perm[0].permission_required is True
        finally:
            os.unlink(path)

    def test_uninspected_sources(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            reg = ProjectionSourceRegistry(path=path)
            reg.register(ProjectionSource(name="a", projection="EOS", source_type="google_docs", read_status=ReadStatus.UNREAD.value))
            reg.register(ProjectionSource(name="b", projection="UMH", source_type="local_filesystem", read_status=ReadStatus.INSPECTED.value))
            uninspected = reg.uninspected_sources()
            assert len(uninspected) == 1
        finally:
            os.unlink(path)

    def test_persistence_reload(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            reg1 = ProjectionSourceRegistry(path=path)
            reg1.register(ProjectionSource(source_id="persist-1", name="test", projection="EOS", source_type="local_filesystem"))
            reg2 = ProjectionSourceRegistry(path=path)
            assert reg2.count() == 1
            assert reg2.get("persist-1") is not None
        finally:
            os.unlink(path)

    def test_summary(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            reg = ProjectionSourceRegistry(path=path)
            reg.register(ProjectionSource(name="a", projection="EOS", source_type="local_filesystem", permission_required=True))
            reg.register(ProjectionSource(name="b", projection="UMH", source_type="github_repository"))
            s = reg.summary()
            assert s["total"] == 2
            assert "EOS" in s["by_projection"]
            assert "UMH" in s["by_projection"]
        finally:
            os.unlink(path)


def _make_test_sources() -> list[ProjectionSource]:
    """Test-only source data for registry creation tests."""
    return [
        ProjectionSource(
            source_id="psrc-docs",
            projection="Shared",
            source_type=ProjectionSourceType.GOOGLE_DOCS.value,
            name="docs_source",
            permission_required=True,
            read_status=ReadStatus.UNREAD.value,
            canonicality=SourceCanonicality.CANDIDATE_CANONICAL.value,
        ),
        ProjectionSource(
            source_id="psrc-github",
            projection="Shared",
            source_type=ProjectionSourceType.GITHUB_REPOSITORY.value,
            name="github_source",
            permission_required=True,
            read_status=ReadStatus.UNREAD.value,
            canonicality=SourceCanonicality.CANDIDATE_CANONICAL.value,
        ),
        ProjectionSource(
            source_id="psrc-device",
            projection="Shared",
            source_type=ProjectionSourceType.DEVICE_FILESYSTEM.value,
            name="device_source",
            permission_required=True,
            read_status=ReadStatus.UNREAD.value,
            canonicality=SourceCanonicality.CANDIDATE_CANONICAL.value,
        ),
        ProjectionSource(
            source_id="psrc-local-umh",
            projection="UMH",
            source_type=ProjectionSourceType.LOCAL_FILESYSTEM.value,
            name="umh_source",
            permission_required=False,
            read_status=ReadStatus.INSPECTED.value,
            canonicality=SourceCanonicality.PRODUCTION_TRUTH.value,
        ),
        ProjectionSource(
            source_id="psrc-partial",
            projection="TestProj",
            source_type=ProjectionSourceType.LOCAL_FILESYSTEM.value,
            name="partial_backend",
            permission_required=False,
            read_status=ReadStatus.INSPECTED.value,
            canonicality=SourceCanonicality.PARTIAL.value,
        ),
    ]


class TestCreateInitialRegistry:
    def test_creates_sources(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            reg = create_initial_registry(path=path, sources=_make_test_sources())
            assert reg.count() == 5
        finally:
            os.unlink(path)

    def test_no_source_auto_canonical(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            reg = create_initial_registry(path=path, sources=_make_test_sources())
            for src in reg.list_sources():
                if src.canonicality == SourceCanonicality.PRODUCTION_TRUTH.value:
                    assert src.projection == "UMH"
                elif src.canonicality == SourceCanonicality.PARTIAL.value:
                    assert src.projection == "TestProj"
                else:
                    assert src.canonicality == SourceCanonicality.CANDIDATE_CANONICAL.value
        finally:
            os.unlink(path)

    def test_three_require_permission(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            reg = create_initial_registry(path=path, sources=_make_test_sources())
            assert len(reg.sources_requiring_permission()) == 3
        finally:
            os.unlink(path)

    def test_partial_source_classified(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            reg = create_initial_registry(path=path, sources=_make_test_sources())
            partial = reg.get("psrc-partial")
            assert partial is not None
            assert partial.canonicality == SourceCanonicality.PARTIAL.value
        finally:
            os.unlink(path)

    def test_device_source_permission_gated(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            reg = create_initial_registry(path=path, sources=_make_test_sources())
            device = reg.get("psrc-device")
            assert device is not None
            assert device.permission_required is True
            assert device.read_status == ReadStatus.UNREAD.value
        finally:
            os.unlink(path)

    def test_docs_source_permission_gated(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            reg = create_initial_registry(path=path, sources=_make_test_sources())
            docs = reg.get("psrc-docs")
            assert docs is not None
            assert docs.permission_required is True
        finally:
            os.unlink(path)

    def test_github_source_permission_gated(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            reg = create_initial_registry(path=path, sources=_make_test_sources())
            gh = reg.get("psrc-github")
            assert gh is not None
            assert gh.permission_required is True
        finally:
            os.unlink(path)

    def test_empty_registry_when_no_sources(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            reg = create_initial_registry(path=path)
            assert reg.count() == 0
        finally:
            os.unlink(path)
