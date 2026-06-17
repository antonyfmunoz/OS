"""Tests for Campaign 6.2 — Documentation Awareness Runtime."""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")

import pytest

from substrate.organism.documentation_awareness_runtime import (
    DocumentationAwarenessRuntime,
    DocumentationSnapshot,
    DocumentEntry,
    DocumentStatus,
)


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def runtime():
    return DocumentationAwarenessRuntime()


@pytest.fixture
def doc_content():
    return """# Architecture Overview

## Decision: Use Clerk for Auth

We decided to use Clerk as the identity provider.

## Constraint: Multi-tenant

The system must support multiple tenants.

## Constraint: Offline mode

Electron app must work offline.

## Components

### Gateway
### SubstrateContext
"""


# ── DocumentStatus Tests ─────────────────────────────────────────────────


class TestDocumentStatus:
    def test_enum_values(self):
        assert DocumentStatus.CURRENT.value == "current"
        assert DocumentStatus.STALE.value == "stale"
        assert DocumentStatus.UNVERIFIED.value == "unverified"
        assert DocumentStatus.MISSING.value == "missing"

    def test_is_str_enum(self):
        assert isinstance(DocumentStatus.CURRENT, str)
        assert DocumentStatus.CURRENT == "current"


# ── DocumentEntry Tests ──────────────────────────────────────────────────


class TestDocumentEntry:
    def test_to_dict(self):
        entry = DocumentEntry(
            doc_id="doc-1",
            name="Architecture",
            source_id="src-1",
            path_or_url="/docs/arch.md",
            topics=["Gateway", "Auth"],
            entity_refs=["proj-umh"],
            decision_count=1,
            constraint_count=2,
        )
        d = entry.to_dict()
        assert d["doc_id"] == "doc-1"
        assert d["topics"] == ["Gateway", "Auth"]
        assert d["decision_count"] == 1
        assert d["constraint_count"] == 2

    def test_defaults(self):
        entry = DocumentEntry(doc_id="x", name="x", source_id="", path_or_url="")
        assert entry.topics == []
        assert entry.entity_refs == []
        assert entry.status == "unverified"

    def test_default_factory_isolation(self):
        e1 = DocumentEntry(doc_id="a", name="a", source_id="", path_or_url="")
        e2 = DocumentEntry(doc_id="b", name="b", source_id="", path_or_url="")
        e1.topics.append("x")
        assert "x" not in e2.topics


# ── DocumentationSnapshot Tests ──────────────────────────────────────────


class TestDocumentationSnapshot:
    def test_to_dict(self):
        snap = DocumentationSnapshot(
            total_docs=3,
            by_status={"current": 2, "stale": 1},
            by_source_type={"local_filesystem": 3},
            stale_docs=[DocumentEntry(doc_id="old", name="old", source_id="", path_or_url="")],
            detected_at=1000.0,
        )
        d = snap.to_dict()
        assert d["total_docs"] == 3
        assert len(d["stale_docs"]) == 1

    def test_defaults(self):
        snap = DocumentationSnapshot(total_docs=0)
        assert snap.by_status == {}
        assert snap.stale_docs == []


# ── Indexing Tests ────────────────────────────────────────────────────────


class TestIndexing:
    def test_index_extracts_topics(self, runtime, doc_content):
        entry = runtime.index_document(
            doc_id="doc-1", name="arch", content=doc_content,
        )
        assert len(entry.topics) > 0
        topic_lower = [t.lower() for t in entry.topics]
        assert "architecture overview" in topic_lower

    def test_index_counts_decisions(self, runtime, doc_content):
        entry = runtime.index_document(
            doc_id="doc-1", name="arch", content=doc_content,
        )
        assert entry.decision_count >= 1

    def test_index_counts_constraints(self, runtime, doc_content):
        entry = runtime.index_document(
            doc_id="doc-1", name="arch", content=doc_content,
        )
        assert entry.constraint_count >= 2

    def test_index_empty_content(self, runtime):
        entry = runtime.index_document(doc_id="doc-e", name="empty", content="")
        assert entry.topics == []
        assert entry.decision_count == 0
        assert entry.constraint_count == 0

    def test_index_stores_in_registry(self, runtime, doc_content):
        runtime.index_document(doc_id="doc-1", name="arch", content=doc_content)
        assert runtime.get_document("doc-1") is not None
        assert runtime.get_document("doc-1").name == "arch"

    def test_index_overwrites_on_same_id(self, runtime):
        runtime.index_document(doc_id="doc-1", name="v1", content="# V1")
        runtime.index_document(doc_id="doc-1", name="v2", content="# V2")
        assert runtime.get_document("doc-1").name == "v2"


# ── Status Detection Tests ───────────────────────────────────────────────


class TestStatusDetection:
    def test_current_doc(self, runtime):
        entry = runtime.index_document(
            doc_id="doc-c", name="current", content="# Current",
            last_modified=time.time(),
        )
        assert entry.status == "current"

    def test_stale_doc(self, runtime):
        old_time = time.time() - (60 * 86400)
        entry = runtime.index_document(
            doc_id="doc-s", name="stale", content="# Stale",
            last_modified=old_time,
        )
        assert entry.status == "stale"

    def test_unverified_doc(self, runtime):
        entry = runtime.index_document(
            doc_id="doc-u", name="unverified", content="# Unknown",
            last_modified=0.0,
        )
        assert entry.status == "unverified"

    def test_custom_staleness_threshold(self):
        rt = DocumentationAwarenessRuntime(staleness_days=7)
        old_time = time.time() - (10 * 86400)
        entry = rt.index_document(
            doc_id="doc-1", name="week-old", content="# Old",
            last_modified=old_time,
        )
        assert entry.status == "stale"


# ── Entity Reference Tests ───────────────────────────────────────────────


class TestEntityRefs:
    def test_no_graph_no_refs(self, runtime):
        entry = runtime.index_document(
            doc_id="doc-1", name="arch", content="Gateway and SubstrateContext",
        )
        assert entry.entity_refs == []

    def test_with_graph_finds_refs(self, doc_content):
        class MockEntity:
            def __init__(self, eid, name):
                self.entity_id = eid
                self.name = name

        class MockGraph:
            def all_entities(self):
                return [
                    MockEntity("proj-umh", "Gateway"),
                    MockEntity("proj-other", "NonExistent"),
                ]

        rt = DocumentationAwarenessRuntime(reality_graph=MockGraph())
        entry = rt.index_document(
            doc_id="doc-1", name="arch", content=doc_content,
        )
        assert "proj-umh" in entry.entity_refs
        assert "proj-other" not in entry.entity_refs

    def test_short_names_ignored(self):
        class MockEntity:
            def __init__(self, eid, name):
                self.entity_id = eid
                self.name = name

        class MockGraph:
            def all_entities(self):
                return [MockEntity("x", "ab")]

        rt = DocumentationAwarenessRuntime(reality_graph=MockGraph())
        entry = rt.index_document(doc_id="doc-1", name="test", content="ab is here")
        assert entry.entity_refs == []


# ── Query Tests ───────────────────────────────────────────────────────────


class TestQueries:
    def test_find_docs_for_entity(self, runtime):
        runtime.index_document(
            doc_id="doc-1", name="related", content="",
        )
        runtime._documents["doc-1"].entity_refs = ["proj-umh"]
        runtime.index_document(
            doc_id="doc-2", name="unrelated", content="",
        )
        found = runtime.find_docs_for_entity("proj-umh")
        assert len(found) == 1
        assert found[0].name == "related"

    def test_find_stale_docs(self, runtime):
        runtime.index_document(
            doc_id="doc-old", name="old", content="",
            last_modified=time.time() - (60 * 86400),
        )
        runtime.index_document(
            doc_id="doc-new", name="new", content="",
            last_modified=time.time(),
        )
        stale = runtime.find_stale_docs()
        assert len(stale) == 1
        assert stale[0].name == "old"

    def test_find_stale_docs_custom_age(self, runtime):
        runtime.index_document(
            doc_id="doc-1", name="week-old", content="",
            last_modified=time.time() - (10 * 86400),
        )
        assert len(runtime.find_stale_docs(max_age_days=7)) == 1
        assert len(runtime.find_stale_docs(max_age_days=14)) == 0

    def test_list_documents_all(self, runtime):
        runtime.index_document(doc_id="doc-1", name="a", content="")
        runtime.index_document(doc_id="doc-2", name="b", content="")
        assert len(runtime.list_documents()) == 2

    def test_list_documents_filter_status(self, runtime):
        runtime.index_document(doc_id="doc-1", name="current", content="", last_modified=time.time())
        runtime.index_document(doc_id="doc-2", name="unverified", content="")
        current = runtime.list_documents(status="current")
        assert len(current) == 1
        assert current[0].name == "current"

    def test_list_documents_filter_source_type(self, runtime):
        runtime.index_document(doc_id="doc-1", name="a", content="", source_type="google_docs")
        runtime.index_document(doc_id="doc-2", name="b", content="", source_type="local_filesystem")
        gdocs = runtime.list_documents(source_type="google_docs")
        assert len(gdocs) == 1
        assert gdocs[0].name == "a"

    def test_get_document(self, runtime):
        runtime.index_document(doc_id="doc-1", name="findme", content="")
        assert runtime.get_document("doc-1").name == "findme"
        assert runtime.get_document("nonexistent") is None


# ── Scan Tests ────────────────────────────────────────────────────────────


class TestScan:
    def test_scan_empty(self, runtime):
        snap = runtime.scan_documentation()
        assert snap.total_docs == 0

    def test_scan_after_indexing(self, runtime):
        runtime.index_document(doc_id="doc-1", name="a", content="# A")
        runtime.index_document(doc_id="doc-2", name="b", content="# B")
        snap = runtime.scan_documentation()
        assert snap.total_docs == 2
        assert snap.detected_at > 0

    def test_scan_counts_status(self, runtime):
        runtime.index_document(doc_id="doc-1", name="current", content="", last_modified=time.time())
        runtime.index_document(doc_id="doc-2", name="unverified", content="")
        snap = runtime.scan_documentation()
        assert snap.by_status.get("current", 0) == 1
        assert snap.by_status.get("unverified", 0) == 1


# ── Local File Tests ─────────────────────────────────────────────────────


class TestLocalFiles:
    def test_read_local_content(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Test Content\n\n## Decision: Use Clerk")
        content = DocumentationAwarenessRuntime._read_local_content(str(f))
        assert "Test Content" in content

    def test_read_nonexistent(self):
        content = DocumentationAwarenessRuntime._read_local_content("/nonexistent")
        assert content == ""

    def test_file_mtime(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("test")
        mtime = DocumentationAwarenessRuntime._file_mtime(str(f))
        assert mtime > 0

    def test_file_mtime_missing(self):
        assert DocumentationAwarenessRuntime._file_mtime("/nonexistent") == 0.0
