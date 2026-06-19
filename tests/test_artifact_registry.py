"""Tests for Campaign 6.0 — Artifact Registry."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")

import pytest

from substrate.organism.artifact_registry import (
    ArtifactEntry,
    ArtifactRegistry,
    ArtifactStatus,
    ArtifactType,
)
from substrate.organism.reality_graph import (
    RealityEntityType,
    RealityGraph,
    RealityRelationType,
)


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_store(tmp_path):
    return str(tmp_path / "artifacts.jsonl")


@pytest.fixture
def registry(tmp_store):
    return ArtifactRegistry(store_path=tmp_store)


def _make_entry(
    name: str = "test-artifact",
    artifact_type: str = ArtifactType.PROOF_PACKAGE.value,
    entity_refs: list[str] | None = None,
    status: str = ArtifactStatus.ACTIVE.value,
) -> ArtifactEntry:
    return ArtifactEntry(
        artifact_id="",
        artifact_type=artifact_type,
        name=name,
        source_path=f"/data/{name}.json",
        source_system="test",
        entity_refs=entity_refs or [],
        created_at=time.time(),
        last_verified=time.time(),
        status=status,
    )


# ── Type Tests ────────────────────────────────────────────────────────────


class TestArtifactTypes:
    def test_artifact_type_values(self):
        assert ArtifactType.PROOF_PACKAGE.value == "proof_package"
        assert ArtifactType.DECISION_RECORD.value == "decision_record"
        assert ArtifactType.TEMPLATE.value == "template"
        assert ArtifactType.DEPLOYMENT_MANIFEST.value == "deployment_manifest"

    def test_artifact_status_values(self):
        assert ArtifactStatus.ACTIVE.value == "active"
        assert ArtifactStatus.SUPERSEDED.value == "superseded"
        assert ArtifactStatus.ARCHIVED.value == "archived"
        assert ArtifactStatus.DRAFT.value == "draft"

    def test_artifact_type_is_str_enum(self):
        assert isinstance(ArtifactType.PROOF_PACKAGE, str)
        assert ArtifactType.PROOF_PACKAGE == "proof_package"

    def test_artifact_status_is_str_enum(self):
        assert isinstance(ArtifactStatus.ACTIVE, str)
        assert ArtifactStatus.ACTIVE == "active"


# ── Entry Tests ───────────────────────────────────────────────────────────


class TestArtifactEntry:
    def test_to_dict(self):
        entry = _make_entry(name="proof-1", entity_refs=["proj-umh"])
        d = entry.to_dict()
        assert d["name"] == "proof-1"
        assert d["entity_refs"] == ["proj-umh"]
        assert d["artifact_type"] == ArtifactType.PROOF_PACKAGE.value

    def test_from_dict_roundtrip(self):
        entry = _make_entry(name="roundtrip", entity_refs=["proj-umh", "repo-os"])
        d = entry.to_dict()
        restored = ArtifactEntry.from_dict(d)
        assert restored.name == entry.name
        assert restored.artifact_type == entry.artifact_type
        assert restored.entity_refs == entry.entity_refs
        assert restored.source_path == entry.source_path

    def test_from_dict_defaults(self):
        entry = ArtifactEntry.from_dict({"artifact_id": "x", "name": "minimal"})
        assert entry.artifact_id == "x"
        assert entry.name == "minimal"
        assert entry.status == "active"
        assert entry.entity_refs == []

    def test_default_factory_isolation(self):
        e1 = _make_entry(name="a")
        e2 = _make_entry(name="b")
        e1.entity_refs.append("proj-x")
        assert "proj-x" not in e2.entity_refs


# ── Registry CRUD Tests ──────────────────────────────────────────────────


class TestRegistryCRUD:
    def test_register_assigns_id(self, registry):
        entry = _make_entry(name="auto-id")
        result = registry.register(entry)
        assert result.artifact_id
        assert result.artifact_id.startswith("art-")

    def test_register_preserves_explicit_id(self, registry):
        entry = _make_entry(name="explicit")
        entry.artifact_id = "art-custom-123"
        result = registry.register(entry)
        assert result.artifact_id == "art-custom-123"

    def test_register_deduplicates(self, registry):
        entry1 = _make_entry(name="dedup")
        entry1.artifact_id = "art-same"
        entry2 = _make_entry(name="dedup-updated")
        entry2.artifact_id = "art-same"
        registry.register(entry1)
        registry.register(entry2)
        assert registry.count() == 1
        assert registry.get("art-same").name == "dedup-updated"

    def test_get_returns_none_for_missing(self, registry):
        assert registry.get("nonexistent") is None

    def test_get_returns_entry(self, registry):
        entry = _make_entry(name="findme")
        registered = registry.register(entry)
        found = registry.get(registered.artifact_id)
        assert found is not None
        assert found.name == "findme"

    def test_count(self, registry):
        assert registry.count() == 0
        registry.register(_make_entry(name="a"))
        registry.register(_make_entry(name="b"))
        assert registry.count() == 2


# ── Find/Filter Tests ────────────────────────────────────────────────────


class TestRegistryFilters:
    def test_find_by_type(self, registry):
        registry.register(_make_entry(name="p1", artifact_type=ArtifactType.PROOF_PACKAGE.value))
        registry.register(_make_entry(name="d1", artifact_type=ArtifactType.DECISION_RECORD.value))
        registry.register(_make_entry(name="p2", artifact_type=ArtifactType.PROOF_PACKAGE.value))
        proofs = registry.find_by_type(ArtifactType.PROOF_PACKAGE.value)
        assert len(proofs) == 2
        assert all(a.artifact_type == ArtifactType.PROOF_PACKAGE.value for a in proofs)

    def test_find_by_entity(self, registry):
        registry.register(_make_entry(name="related", entity_refs=["proj-umh", "repo-os"]))
        registry.register(_make_entry(name="unrelated", entity_refs=["proj-other"]))
        found = registry.find_by_entity("proj-umh")
        assert len(found) == 1
        assert found[0].name == "related"

    def test_find_by_entity_empty(self, registry):
        registry.register(_make_entry(name="nope", entity_refs=[]))
        assert registry.find_by_entity("proj-umh") == []

    def test_find_by_source(self, registry):
        entry = _make_entry(name="sourced")
        entry.source_path = "/data/specific.json"
        registry.register(entry)
        found = registry.find_by_source("/data/specific.json")
        assert len(found) == 1
        assert found[0].name == "sourced"

    def test_find_by_source_no_match(self, registry):
        assert registry.find_by_source("/nonexistent") == []

    def test_list_artifacts_all(self, registry):
        registry.register(_make_entry(name="a"))
        registry.register(_make_entry(name="b"))
        assert len(registry.list_artifacts()) == 2

    def test_list_artifacts_filter_type(self, registry):
        registry.register(_make_entry(name="p", artifact_type=ArtifactType.PROOF_PACKAGE.value))
        registry.register(_make_entry(name="d", artifact_type=ArtifactType.DECISION_RECORD.value))
        filtered = registry.list_artifacts(artifact_type=ArtifactType.DECISION_RECORD.value)
        assert len(filtered) == 1
        assert filtered[0].name == "d"

    def test_list_artifacts_filter_status(self, registry):
        registry.register(_make_entry(name="active", status=ArtifactStatus.ACTIVE.value))
        registry.register(_make_entry(name="archived", status=ArtifactStatus.ARCHIVED.value))
        filtered = registry.list_artifacts(status=ArtifactStatus.ARCHIVED.value)
        assert len(filtered) == 1
        assert filtered[0].name == "archived"

    def test_list_artifacts_filter_both(self, registry):
        registry.register(_make_entry(name="match", artifact_type=ArtifactType.TEMPLATE.value, status=ArtifactStatus.DRAFT.value))
        registry.register(_make_entry(name="type-only", artifact_type=ArtifactType.TEMPLATE.value, status=ArtifactStatus.ACTIVE.value))
        registry.register(_make_entry(name="status-only", artifact_type=ArtifactType.PROOF_PACKAGE.value, status=ArtifactStatus.DRAFT.value))
        filtered = registry.list_artifacts(artifact_type=ArtifactType.TEMPLATE.value, status=ArtifactStatus.DRAFT.value)
        assert len(filtered) == 1
        assert filtered[0].name == "match"


# ── Summary Tests ─────────────────────────────────────────────────────────


class TestRegistrySummary:
    def test_summary_empty(self, registry):
        s = registry.summary()
        assert s["total"] == 0
        assert s["by_type"] == {}
        assert s["by_status"] == {}

    def test_summary_counts(self, registry):
        registry.register(_make_entry(name="a", artifact_type=ArtifactType.PROOF_PACKAGE.value))
        registry.register(_make_entry(name="b", artifact_type=ArtifactType.PROOF_PACKAGE.value))
        registry.register(_make_entry(name="c", artifact_type=ArtifactType.DECISION_RECORD.value, status=ArtifactStatus.ARCHIVED.value))
        s = registry.summary()
        assert s["total"] == 3
        assert s["by_type"]["proof_package"] == 2
        assert s["by_type"]["decision_record"] == 1
        assert s["by_status"]["active"] == 2
        assert s["by_status"]["archived"] == 1


# ── Persistence Tests ─────────────────────────────────────────────────────


class TestPersistence:
    def test_jsonl_roundtrip(self, tmp_store):
        reg1 = ArtifactRegistry(store_path=tmp_store)
        reg1.register(_make_entry(name="persist-1", entity_refs=["proj-umh"]))
        reg1.register(_make_entry(name="persist-2"))

        reg2 = ArtifactRegistry(store_path=tmp_store)
        assert reg2.count() == 2
        found = reg2.find_by_entity("proj-umh")
        assert len(found) == 1
        assert found[0].name == "persist-1"

    def test_compact_deduplicates(self, tmp_store):
        reg = ArtifactRegistry(store_path=tmp_store)
        entry = _make_entry(name="compact-me")
        entry.artifact_id = "art-compact"
        reg.register(entry)
        entry.name = "compact-me-updated"
        reg.register(entry)

        reg._compact()
        with open(tmp_store, "r") as f:
            lines = [l for l in f if l.strip()]
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["name"] == "compact-me-updated"

    def test_load_skips_malformed_lines(self, tmp_store):
        with open(tmp_store, "w") as f:
            f.write("not json\n")
            f.write(json.dumps({"artifact_id": "art-good", "name": "good"}) + "\n")
        reg = ArtifactRegistry(store_path=tmp_store)
        assert reg.count() == 1
        assert reg.get("art-good").name == "good"

    def test_missing_store_starts_empty(self, tmp_path):
        reg = ArtifactRegistry(store_path=str(tmp_path / "nonexistent.jsonl"))
        assert reg.count() == 0


# ── RealityGraph Integration Tests ───────────────────────────────────────


class TestRealityGraphIngestion:
    def test_ingest_creates_artifact_entities(self, registry):
        registry.register(_make_entry(name="proof-1", entity_refs=["proj-umh"]))
        registry.register(_make_entry(name="decision-1", artifact_type=ArtifactType.DECISION_RECORD.value))

        graph = RealityGraph()
        count = graph.ingest_from_artifact_registry(registry)
        assert count == 2

        artifacts = graph.find_by_type(RealityEntityType.ARTIFACT)
        assert len(artifacts) == 2

    def test_ingest_creates_documents_relations(self, registry):
        registry.register(_make_entry(name="linked", entity_refs=["proj-umh", "repo-os"]))
        graph = RealityGraph()
        graph.ingest_from_artifact_registry(registry)

        all_relations = graph.all_relations()
        doc_relations = [r for r in all_relations if r.relation_type == RealityRelationType.DOCUMENTS]
        assert len(doc_relations) == 2

    def test_ingest_no_artifacts(self, registry):
        graph = RealityGraph()
        count = graph.ingest_from_artifact_registry(registry)
        assert count == 0

    def test_ingest_sets_properties(self, registry):
        entry = _make_entry(name="with-props", artifact_type=ArtifactType.TEMPLATE.value)
        entry.source_system = "cadence"
        registered = registry.register(entry)

        graph = RealityGraph()
        graph.ingest_from_artifact_registry(registry)

        art_entities = graph.find_by_type(RealityEntityType.ARTIFACT)
        assert len(art_entities) == 1
        props = art_entities[0].properties
        assert props["artifact_type"] == ArtifactType.TEMPLATE.value
        assert props["source_system"] == "cadence"

    def test_ingest_status_mapping(self, registry):
        registry.register(_make_entry(name="active", status=ArtifactStatus.ACTIVE.value))
        registry.register(_make_entry(name="archived", status=ArtifactStatus.ARCHIVED.value))

        graph = RealityGraph()
        graph.ingest_from_artifact_registry(registry)

        entities = {e.name: e for e in graph.find_by_type(RealityEntityType.ARTIFACT)}
        assert entities["active"].status.value == "active"
        assert entities["archived"].status.value == "inactive"


# ── ID Generation Tests ──────────────────────────────────────────────────


class TestIdGeneration:
    def test_auto_generated_id_is_deterministic(self, registry):
        e1 = _make_entry(name="same")
        e2 = _make_entry(name="same")
        id1 = ArtifactRegistry._generate_id(e1)
        id2 = ArtifactRegistry._generate_id(e2)
        assert id1 == id2

    def test_different_entries_get_different_ids(self, registry):
        e1 = _make_entry(name="a")
        e2 = _make_entry(name="b")
        assert ArtifactRegistry._generate_id(e1) != ArtifactRegistry._generate_id(e2)

    def test_auto_id_starts_with_art(self, registry):
        entry = _make_entry(name="prefix-check")
        aid = ArtifactRegistry._generate_id(entry)
        assert aid.startswith("art-")
