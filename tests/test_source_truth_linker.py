"""Tests for Source Truth Linker — Campaign 5.4."""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from substrate.organism.reality_graph import (
    RealityEntity,
    RealityEntityStatus,
    RealityEntityType,
    RealityGraph,
    RealityRelation,
    RealityRelationType,
)
from substrate.organism.project_registry import ProjectRegistry
from substrate.organism.source_truth_linker import SourceTruthLinker


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def device_registry(tmp_path):
    data = [
        {"id": "vps", "display_name": "srv1500858 (VPS)", "device_type": "vps", "role": "orchestrator", "tailscale_ip": "100.77.233.50"},
        {"id": "beast", "display_name": "desktop-lvguiq9 (PC)", "device_type": "pc", "role": "executor", "gpu": "GTX 1080 Ti"},
    ]
    path = tmp_path / "device_registry.json"
    path.write_text(json.dumps(data))
    return str(path)


@pytest.fixture
def workspace_registry(tmp_path):
    data = [
        {
            "workspace_id": "umh",
            "name": "UMH",
            "workspace_type": "core",
            "repositories": [
                {"repository_id": "umh-os", "name": "OS", "path": "", "branch": "main"}
            ],
            "device_ids": ["vps", "beast"],
        },
        {
            "workspace_id": "creatoros",
            "name": "CreatorOS",
            "workspace_type": "product",
            "repositories": [
                {"repository_id": "creatoros-app", "name": "CreatorOS", "path": "", "branch": "main"}
            ],
            "device_ids": ["beast"],
        },
    ]
    path = tmp_path / "workspace_registry.json"
    path.write_text(json.dumps(data))
    return str(path)


@pytest.fixture
def project_registry_path(tmp_path):
    data = [
        {
            "project_id": "umh",
            "name": "UMH",
            "description": "Universal Meta Harness",
            "projection": "",
            "repositories": ["umh-os"],
            "infrastructure": ["cockpit-api", "os-discord"],
            "capabilities": ["orchestration", "governance"],
            "owner_device_ids": ["vps", "beast"],
            "status": "active",
        },
        {
            "project_id": "creatoros",
            "name": "CreatorOS",
            "description": "Creator workspace",
            "projection": "creatoros",
            "repositories": ["creatoros-app"],
            "infrastructure": [],
            "capabilities": ["desktop-app"],
            "owner_device_ids": ["beast"],
            "status": "active",
        },
    ]
    path = tmp_path / "project_registry.json"
    path.write_text(json.dumps(data))
    return str(path)


@pytest.fixture
def seeded_graph(device_registry, workspace_registry, project_registry_path):
    return RealityGraph.seed_from_registries(
        device_registry_path=device_registry,
        workspace_registry_path=workspace_registry,
        project_registry_path=project_registry_path,
    )


@pytest.fixture
def project_registry(project_registry_path):
    return ProjectRegistry(registry_path=project_registry_path)


@pytest.fixture
def linker(seeded_graph, project_registry):
    return SourceTruthLinker(
        reality_graph=seeded_graph,
        project_registry=project_registry,
    )


@pytest.fixture
def linked_graph(linker):
    linker.link_all()
    return linker


# ── Mock Source Registry ──────────────────────────────────────────────────


class MockSource:
    def __init__(self, source_id, name, source_type, url="", projection=""):
        self.id = source_id
        self.source_id = source_id
        self.name = name
        self.source_type = source_type
        self.url = url
        self.projection = projection


class MockSourceRegistry:
    def __init__(self, sources):
        self._sources_list = sources

    def list_sources(self):
        return self._sources_list


# ── Test: Link Projects to Repos ──────────────────────────────────────────


class TestLinkProjectsToRepos:
    def test_creates_contains_edges_or_already_exist(self, seeded_graph, project_registry):
        linker = SourceTruthLinker(seeded_graph, project_registry=project_registry)
        count = linker._link_projects_to_repos()
        neighbors = seeded_graph.neighbors("proj-umh", RealityRelationType.CONTAINS)
        ids = {n.entity_id for n in neighbors}
        assert "repo-umh-os" in ids

    def test_umh_contains_umh_os(self, linked_graph):
        neighbors = linked_graph._graph.neighbors("proj-umh", RealityRelationType.CONTAINS)
        ids = {n.entity_id for n in neighbors}
        assert "repo-umh-os" in ids

    def test_creatoros_contains_creatoros_app(self, linked_graph):
        neighbors = linked_graph._graph.neighbors("proj-creatoros", RealityRelationType.CONTAINS)
        ids = {n.entity_id for n in neighbors}
        assert "repo-creatoros-app" in ids

    def test_no_registry_returns_zero(self, seeded_graph):
        linker = SourceTruthLinker(seeded_graph, project_registry=None)
        assert linker._link_projects_to_repos() == 0


# ── Test: Link Repos to Workspaces ────────────────────────────────────────


class TestLinkReposToWorkspaces:
    def test_existing_edges_preserved(self, seeded_graph, project_registry):
        initial_rels = seeded_graph.relation_count
        linker = SourceTruthLinker(seeded_graph, project_registry=project_registry)
        linker._link_repos_to_workspaces()
        assert seeded_graph.relation_count >= initial_rels

    def test_creatoros_workspace_contains_repo(self, linked_graph):
        neighbors = linked_graph._graph.neighbors("ws-creatoros", RealityRelationType.CONTAINS)
        ids = {n.entity_id for n in neighbors}
        assert "repo-creatoros-app" in ids


# ── Test: Link Projects to Projections ────────────────────────────────────


class TestLinkProjectsToProjections:
    def test_creates_projection_entity(self, seeded_graph, project_registry):
        linker = SourceTruthLinker(seeded_graph, project_registry=project_registry)
        linker._link_projects_to_projections()
        proj_entity = seeded_graph.get("projection-creatoros")
        assert proj_entity is not None
        assert proj_entity.entity_type == RealityEntityType.PROJECTION
        assert proj_entity.name == "creatoros"

    def test_creates_owned_by_edge(self, seeded_graph, project_registry):
        linker = SourceTruthLinker(seeded_graph, project_registry=project_registry)
        linker._link_projects_to_projections()
        neighbors = seeded_graph.neighbors("proj-creatoros", RealityRelationType.OWNED_BY)
        ids = {n.entity_id for n in neighbors}
        assert "projection-creatoros" in ids

    def test_skips_project_without_projection(self, seeded_graph, project_registry):
        linker = SourceTruthLinker(seeded_graph, project_registry=project_registry)
        linker._link_projects_to_projections()
        assert seeded_graph.get("projection-") is None

    def test_umh_has_no_projection(self, linked_graph):
        neighbors = linked_graph._graph.neighbors("proj-umh", RealityRelationType.OWNED_BY)
        projection_neighbors = [n for n in neighbors if n.entity_type == RealityEntityType.PROJECTION]
        assert len(projection_neighbors) == 0


# ── Test: Link Projects to Docs ───────────────────────────────────────────


class TestLinkProjectsToDocs:
    def test_creates_document_entity(self, seeded_graph, project_registry):
        source_registry = MockSourceRegistry([
            MockSource("auth-doc", "Auth Architecture", "GWS_DOCUMENT", projection="creatoros"),
        ])
        linker = SourceTruthLinker(seeded_graph, project_registry=project_registry, source_registry=source_registry)
        count = linker._link_projects_to_docs()
        assert count == 1
        doc = seeded_graph.get("doc-auth-doc")
        assert doc is not None
        assert doc.entity_type == RealityEntityType.DOCUMENT
        assert doc.name == "Auth Architecture"

    def test_creates_documents_edge(self, seeded_graph, project_registry):
        source_registry = MockSourceRegistry([
            MockSource("roadmap", "CreatorOS Roadmap", "GWS_DOCUMENT", projection="creatoros"),
        ])
        linker = SourceTruthLinker(seeded_graph, project_registry=project_registry, source_registry=source_registry)
        linker._link_projects_to_docs()
        neighbors = seeded_graph.neighbors("proj-creatoros", RealityRelationType.DOCUMENTS)
        ids = {n.entity_id for n in neighbors}
        assert "doc-roadmap" in ids

    def test_ignores_non_doc_sources(self, seeded_graph, project_registry):
        source_registry = MockSourceRegistry([
            MockSource("repo-1", "Some Repo", "GITHUB_REPO", projection="creatoros"),
        ])
        linker = SourceTruthLinker(seeded_graph, project_registry=project_registry, source_registry=source_registry)
        count = linker._link_projects_to_docs()
        assert count == 0

    def test_no_source_registry_returns_zero(self, seeded_graph, project_registry):
        linker = SourceTruthLinker(seeded_graph, project_registry=project_registry, source_registry=None)
        assert linker._link_projects_to_docs() == 0


# ── Test: Link Services to Devices ────────────────────────────────────────


class TestLinkServicesToDevices:
    def test_links_infra_to_device(self, seeded_graph, project_registry):
        infra = RealityEntity(
            entity_id="infra-cockpit-api",
            entity_type=RealityEntityType.INFRASTRUCTURE,
            name="Cockpit API",
            status=RealityEntityStatus.ACTIVE,
            properties={"host_device_id": "vps"},
            source_system="test",
            last_observed=1.0,
        )
        seeded_graph._add_entity(infra)
        linker = SourceTruthLinker(seeded_graph, project_registry=project_registry)
        count = linker._link_services_to_devices()
        assert count == 1
        neighbors = seeded_graph.neighbors("infra-cockpit-api", RealityRelationType.RUNS_ON)
        ids = {n.entity_id for n in neighbors}
        assert "dev-vps" in ids

    def test_skips_missing_device(self, seeded_graph, project_registry):
        infra = RealityEntity(
            entity_id="infra-external",
            entity_type=RealityEntityType.INFRASTRUCTURE,
            name="External Service",
            status=RealityEntityStatus.ACTIVE,
            properties={"host_device_id": "nonexistent"},
            source_system="test",
            last_observed=1.0,
        )
        seeded_graph._add_entity(infra)
        linker = SourceTruthLinker(seeded_graph, project_registry=project_registry)
        count = linker._link_services_to_devices()
        assert count == 0


# ── Test: Trace from Entity ───────────────────────────────────────────────


class TestTraceFromEntity:
    def test_trace_from_repo_reaches_device(self, linked_graph):
        trace = linked_graph.trace_from_entity("repo-creatoros-app")
        all_ids = set()
        for entities in trace.values():
            for e in entities:
                all_ids.add(e["entity_id"])
        assert "dev-beast" in all_ids

    def test_trace_from_project_reaches_repo(self, linked_graph):
        trace = linked_graph.trace_from_entity("proj-umh")
        contains = trace.get("contains", [])
        ids = {e["entity_id"] for e in contains}
        assert "repo-umh-os" in ids

    def test_trace_nonexistent_returns_empty(self, linked_graph):
        trace = linked_graph.trace_from_entity("nonexistent-xyz")
        assert trace == {}

    def test_trace_groups_by_relation_type(self, linked_graph):
        trace = linked_graph.trace_from_entity("proj-creatoros")
        assert isinstance(trace, dict)
        for key in trace:
            assert isinstance(trace[key], list)

    def test_trace_from_device_reaches_workspace(self, linked_graph):
        trace = linked_graph.trace_from_entity("dev-beast")
        all_ids = set()
        for entities in trace.values():
            for e in entities:
                all_ids.add(e["entity_id"])
        assert "ws-creatoros" in all_ids


# ── Test: Link Summary ───────────────────────────────────────────────────


class TestLinkSummary:
    def test_summary_structure(self, linked_graph):
        summary = linked_graph.link_summary()
        assert "edge_counts_by_type" in summary
        assert "total_edges" in summary
        assert "total_entities" in summary
        assert "linked_entities" in summary
        assert "unlinked_entities" in summary

    def test_summary_has_contains_edges(self, linked_graph):
        summary = linked_graph.link_summary()
        assert summary["edge_counts_by_type"].get("contains", 0) > 0

    def test_summary_counts_match(self, linked_graph):
        summary = linked_graph.link_summary()
        assert summary["total_edges"] == linked_graph._graph.relation_count
        assert summary["total_entities"] == linked_graph._graph.entity_count

    def test_linked_plus_unlinked_equals_total(self, linked_graph):
        summary = linked_graph.link_summary()
        assert summary["linked_entities"] + len(summary["unlinked_entities"]) == summary["total_entities"]


# ── Test: Edge Cases ──────────────────────────────────────────────────────


class TestEdgeCases:
    def test_no_registries(self):
        graph = RealityGraph()
        linker = SourceTruthLinker(graph)
        count = linker.link_all()
        assert count == 0

    def test_empty_graph(self):
        graph = RealityGraph()
        linker = SourceTruthLinker(graph, project_registry=None, source_registry=None)
        summary = linker.link_summary()
        assert summary["total_entities"] == 0
        assert summary["total_edges"] == 0

    def test_graph_with_entities_no_linkable(self):
        graph = RealityGraph()
        graph._add_entity(RealityEntity(
            entity_id="dev-test",
            entity_type=RealityEntityType.DEVICE,
            name="Test Device",
            last_observed=1.0,
        ))
        linker = SourceTruthLinker(graph)
        count = linker.link_all()
        assert count == 0


# ── Test: Idempotency ─────────────────────────────────────────────────────


class TestIdempotency:
    def test_link_all_twice_no_duplicate_edges(self, seeded_graph, project_registry):
        linker = SourceTruthLinker(seeded_graph, project_registry=project_registry)
        count1 = linker.link_all()
        rel_count_after_first = seeded_graph.relation_count
        count2 = linker.link_all()
        assert count2 == 0
        assert seeded_graph.relation_count == rel_count_after_first

    def test_link_projects_to_repos_twice_idempotent(self, seeded_graph, project_registry):
        linker = SourceTruthLinker(seeded_graph, project_registry=project_registry)
        c1 = linker._link_projects_to_repos()
        c2 = linker._link_projects_to_repos()
        assert c2 == 0

    def test_link_projections_twice_idempotent(self, seeded_graph, project_registry):
        linker = SourceTruthLinker(seeded_graph, project_registry=project_registry)
        c1 = linker._link_projects_to_projections()
        entity_count = seeded_graph.entity_count
        c2 = linker._link_projects_to_projections()
        assert c2 == 0
        assert seeded_graph.entity_count == entity_count
