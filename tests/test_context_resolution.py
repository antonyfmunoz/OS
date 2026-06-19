"""Tests for Context Resolution Engine — Campaign 5.5."""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from substrate.organism.context_resolution import (
    ContextResolutionEngine,
    ResolvedContext,
    ResolutionStrategy,
    _extract_candidate_names,
)
from substrate.organism.reality_graph import (
    RealityGraph,
    RealityEntityType,
)
from substrate.organism.project_registry import ProjectRegistry


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def device_registry(tmp_path):
    data = [
        {"id": "vps", "display_name": "srv1500858 (VPS)", "device_type": "vps", "role": "orchestrator", "tailscale_ip": "100.77.233.50", "compute": True, "always_online": True},
        {"id": "beast", "display_name": "desktop-lvguiq9 (PC)", "device_type": "pc", "role": "executor", "gpu": "GTX 1080 Ti", "compute": True},
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
            "repositories": [{"repository_id": "umh-os", "name": "OS", "path": "", "branch": "main"}],
            "device_ids": ["vps", "beast"],
        },
        {
            "workspace_id": "creatoros",
            "name": "CreatorOS",
            "workspace_type": "product",
            "repositories": [{"repository_id": "creatoros-app", "name": "CreatorOS", "path": "", "branch": "main"}],
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
            "capabilities": ["orchestration"],
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
def graph(device_registry, workspace_registry, project_registry_path):
    return RealityGraph.seed_from_registries(
        device_registry_path=device_registry,
        workspace_registry_path=workspace_registry,
        project_registry_path=project_registry_path,
    )


@pytest.fixture
def project_reg(project_registry_path):
    return ProjectRegistry(registry_path=project_registry_path)


@pytest.fixture
def engine(graph, project_reg):
    return ContextResolutionEngine(
        reality_graph=graph,
        project_registry=project_reg,
    )


# ── Candidate Extraction Tests ────────────────────────────────────────────


class TestCandidateExtraction:
    def test_extracts_capitalized_words(self):
        candidates = _extract_candidate_names("Use Clerk for CreatorOS")
        assert "Clerk" in candidates
        assert "CreatorOS" in candidates

    def test_extracts_quoted_names(self):
        candidates = _extract_candidate_names('Deploy "my-service" to VPS')
        assert "my-service" in candidates

    def test_filters_stop_words(self):
        candidates = _extract_candidate_names("the system is running")
        lower_candidates = [c.lower() for c in candidates]
        assert "the" not in lower_candidates
        assert "system" in lower_candidates
        assert "running" in lower_candidates

    def test_empty_input(self):
        candidates = _extract_candidate_names("")
        assert len(candidates) == 0

    def test_deduplication(self):
        candidates = _extract_candidate_names("UMH UMH umh")
        lower = [c.lower() for c in candidates]
        assert lower.count("umh") == 1


# ── Resolution Tests ──────────────────────────────────────────────────────


class TestResolveCreatorOS:
    """The golden test: 'Use Clerk for CreatorOS'."""

    def test_resolves_project(self, engine):
        ctx = engine.resolve("Use Clerk for CreatorOS")
        assert ctx.project_id == "creatoros"
        assert ctx.project_name == "CreatorOS"

    def test_resolves_repo_via_graph_walk(self, engine):
        ctx = engine.resolve("Use Clerk for CreatorOS")
        assert ctx.repository_id == "creatoros-app"

    def test_resolves_device_via_graph_walk(self, engine):
        ctx = engine.resolve("Use Clerk for CreatorOS")
        assert ctx.device_id == "beast"

    def test_resolves_projection(self, engine):
        ctx = engine.resolve("Use Clerk for CreatorOS")
        assert ctx.projection == "creatoros"

    def test_clerk_is_unresolved(self, engine):
        ctx = engine.resolve("Use Clerk for CreatorOS")
        assert "Clerk" in ctx.unresolved_references

    def test_has_resolution_chain(self, engine):
        ctx = engine.resolve("Use Clerk for CreatorOS")
        assert len(ctx.resolution_chain) >= 1
        steps = [s["step"] for s in ctx.resolution_chain]
        assert "project_registry_match" in steps

    def test_confidence_above_zero(self, engine):
        ctx = engine.resolve("Use Clerk for CreatorOS")
        assert ctx.confidence > 0.5

    def test_is_resolved(self, engine):
        ctx = engine.resolve("Use Clerk for CreatorOS")
        assert ctx.is_resolved


class TestResolveUMH:
    def test_resolves_umh_project(self, engine):
        ctx = engine.resolve("Deploy UMH cockpit")
        assert ctx.project_id == "umh"
        assert ctx.project_name == "UMH"

    def test_resolves_umh_repo(self, engine):
        ctx = engine.resolve("Deploy UMH cockpit")
        assert ctx.repository_id == "umh-os"

    def test_resolves_umh_device(self, engine):
        ctx = engine.resolve("Deploy UMH cockpit")
        assert ctx.device_id in ("vps", "beast")


class TestResolveByRepoName:
    def test_resolves_workspace_from_repo(self, engine):
        ctx = engine.resolve("Check the OS repository")
        assert ctx.repository_name == "OS" or ctx.workspace_id


class TestNoResolution:
    def test_unknown_input(self, engine):
        ctx = engine.resolve("random gibberish xyz")
        assert ctx.confidence < 0.3

    def test_empty_input(self, engine):
        ctx = engine.resolve("")
        assert not ctx.is_resolved
        assert ctx.confidence == 0.0


# ── ResolvedContext Tests ─────────────────────────────────────────────────


class TestResolvedContext:
    def test_to_dict(self):
        ctx = ResolvedContext(
            project_id="umh",
            project_name="UMH",
            confidence=0.85,
        )
        d = ctx.to_dict()
        assert d["project_id"] == "umh"
        assert d["confidence"] == 0.85
        assert d["strategy"] == "exact_match"

    def test_is_resolved_true(self):
        ctx = ResolvedContext(project_id="umh")
        assert ctx.is_resolved

    def test_is_resolved_false(self):
        ctx = ResolvedContext()
        assert not ctx.is_resolved

    def test_default_values(self):
        ctx = ResolvedContext()
        assert ctx.project_id == ""
        assert ctx.confidence == 0.0
        assert ctx.unresolved_references == []
        assert ctx.resolution_chain == []


# ── Entity Reference Tests ────────────────────────────────────────────────


class TestResolveEntityReference:
    def test_find_by_name(self, engine):
        results = engine.resolve_entity_reference("CreatorOS")
        assert len(results) > 0
        names = {r["name"] for r in results}
        assert "CreatorOS" in names

    def test_no_match(self, engine):
        results = engine.resolve_entity_reference("NonExistentXYZ")
        assert len(results) == 0

    def test_no_graph(self):
        engine = ContextResolutionEngine()
        results = engine.resolve_entity_reference("anything")
        assert results == []


# ── Populate Context Tests ────────────────────────────────────────────────


class TestPopulateOrchestratorContext:
    def test_populates_fields(self, engine):
        resolved = engine.resolve("Use Clerk for CreatorOS")

        class MockCtx:
            active_project = ""
            active_repo = ""
            active_projection = ""
            active_device = ""
            preferred_execution_device = ""

        ctx = MockCtx()
        engine.populate_orchestrator_context(ctx, resolved)
        assert ctx.active_project == "CreatorOS"
        assert ctx.active_repo in ("creatoros-app", "CreatorOS")
        assert ctx.active_projection == "creatoros"
        assert ctx.preferred_execution_device == "beast"

    def test_does_not_overwrite_empty(self, engine):
        resolved = ResolvedContext()

        class MockCtx:
            active_project = "existing"
            active_repo = ""
            active_projection = ""
            active_device = ""
            preferred_execution_device = ""

        ctx = MockCtx()
        engine.populate_orchestrator_context(ctx, resolved)
        assert ctx.active_project == "existing"


# ── Graph Walk Tests ──────────────────────────────────────────────────────


class TestGraphWalkEnrichment:
    def test_project_to_repo_walk(self, engine):
        ctx = engine.resolve("CreatorOS")
        assert ctx.repository_id == "creatoros-app"
        chain_steps = [s["step"] for s in ctx.resolution_chain]
        assert "graph_walk_project_to_repo" in chain_steps

    def test_project_to_device_walk(self, engine):
        ctx = engine.resolve("CreatorOS")
        assert ctx.device_id == "beast"
        chain_steps = [s["step"] for s in ctx.resolution_chain]
        assert "graph_walk_project_to_device" in chain_steps


# ── Edge Cases ────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_no_graph_no_registry(self):
        engine = ContextResolutionEngine()
        ctx = engine.resolve("CreatorOS")
        assert not ctx.is_resolved
        assert "CreatorOS" in ctx.unresolved_references

    def test_graph_only_no_registry(self, graph):
        engine = ContextResolutionEngine(reality_graph=graph)
        ctx = engine.resolve("CreatorOS")
        assert ctx.is_resolved

    def test_registry_only_no_graph(self, project_reg):
        engine = ContextResolutionEngine(project_registry=project_reg)
        ctx = engine.resolve("CreatorOS")
        assert ctx.project_id == "creatoros"
        assert ctx.repository_id == ""  # no graph to walk

    def test_multiple_entities_in_input(self, engine):
        ctx = engine.resolve("Deploy CreatorOS to VPS")
        assert ctx.project_id == "creatoros"

    def test_resolution_chain_audit_trail(self, engine):
        ctx = engine.resolve("CreatorOS build")
        assert len(ctx.resolution_chain) >= 1
        for step in ctx.resolution_chain:
            assert "step" in step
