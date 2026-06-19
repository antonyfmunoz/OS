"""Tests for Campaign 6.5 — Context Resolution V2 (Operational Reality)."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any

sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")

import pytest

from substrate.organism.context_resolution import (
    ContextResolutionEngine,
    ResolvedContext,
)
from substrate.organism.reality_graph import RealityGraph
from substrate.organism.project_registry import ProjectRegistry


# ── Mock Runtimes ────────────────────────────────────────────────────────


@dataclass
class MockFileEntry:
    path: str
    category: str
    entity_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "category": self.category, "entity_refs": self.entity_refs}


class MockRepositoryRuntime:
    def __init__(self, files: list[MockFileEntry] | None = None):
        self._files = files or []

    def find_files_for_entity(self, entity_id: str) -> list[MockFileEntry]:
        return [f for f in self._files if entity_id in f.entity_refs]

    def snapshot(self) -> dict[str, Any]:
        return {"important_files": [f.to_dict() for f in self._files]}


@dataclass
class MockDocEntry:
    doc_id: str
    name: str
    decision_count: int = 0
    constraint_count: int = 0
    entity_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "name": self.name,
            "decision_count": self.decision_count,
            "constraint_count": self.constraint_count,
            "entity_refs": self.entity_refs,
        }


class MockDocumentationRuntime:
    def __init__(self, docs: list[MockDocEntry] | None = None):
        self._docs = docs or []

    def find_docs_for_entity(self, entity_id: str) -> list[MockDocEntry]:
        return [d for d in self._docs if entity_id in d.entity_refs]


@dataclass
class MockWorkPacket:
    packet_id: str
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {"packet_id": self.packet_id, "status": self.status}


class MockRuntimeAwareness:
    def __init__(self, active: list[dict] | None = None):
        self._active = active or []

    def active_work(self) -> list[dict]:
        return self._active


@dataclass
class MockKnowledgeEntry:
    knowledge_id: str
    knowledge_type: str
    summary: str
    entity_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "knowledge_id": self.knowledge_id,
            "knowledge_type": self.knowledge_type,
            "summary": self.summary,
            "entity_refs": self.entity_refs,
        }


class MockKnowledgeRuntime:
    def __init__(self, entries: list[MockKnowledgeEntry] | None = None):
        self._entries = entries or []

    def find_for_entity(self, entity_id: str) -> list[MockKnowledgeEntry]:
        return [e for e in self._entries if entity_id in e.entity_refs]


# ── Fixture: seeded graph ────────────────────────────────────────────────


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
def seeded_graph(device_registry, workspace_registry, project_registry_path):
    return RealityGraph.seed_from_registries(
        device_registry_path=device_registry,
        workspace_registry_path=workspace_registry,
        project_registry_path=project_registry_path,
    )


@pytest.fixture
def project_reg(project_registry_path):
    return ProjectRegistry(registry_path=project_registry_path)


@pytest.fixture
def rich_runtimes():
    repo = MockRepositoryRuntime([
        MockFileEntry("src/auth/clerk.ts", "source_code", ["proj-creatoros"]),
        MockFileEntry("src/auth/middleware.ts", "source_code", ["proj-creatoros"]),
        MockFileEntry("package.json", "configuration", ["proj-creatoros"]),
    ])
    docs = MockDocumentationRuntime([
        MockDocEntry("doc-auth", "Auth Architecture", decision_count=2, constraint_count=1, entity_refs=["proj-creatoros"]),
        MockDocEntry("doc-clerk", "Clerk Integration Guide", decision_count=1, constraint_count=0, entity_refs=["proj-creatoros"]),
    ])
    runtime = MockRuntimeAwareness([
        {"packet_id": "wp-clerk-setup", "status": "executing", "description": "Clerk integration"},
    ])
    knowledge = MockKnowledgeRuntime([
        MockKnowledgeEntry("kn-1", "decision", "Use Clerk for identity", ["proj-creatoros"]),
        MockKnowledgeEntry("kn-2", "constraint", "Multi-tenant isolation", ["proj-creatoros"]),
        MockKnowledgeEntry("kn-3", "convention", "Deterministic-first", ["proj-creatoros"]),
    ])
    return repo, docs, runtime, knowledge


# ── ResolvedContext new fields ───────────────────────────────────────────


class TestResolvedContextNewFields:
    def test_defaults_empty(self):
        ctx = ResolvedContext()
        assert ctx.files == []
        assert ctx.decisions == []
        assert ctx.active_work == []
        assert ctx.approvals == []
        assert ctx.constraints == []
        assert ctx.knowledge == []

    def test_to_dict_includes_new_fields(self):
        ctx = ResolvedContext(
            files=[{"path": "x.py"}],
            decisions=[{"summary": "Use Clerk"}],
            active_work=[{"id": "wp-1"}],
            approvals=[{"id": "ap-1"}],
            constraints=[{"summary": "Multi-tenant"}],
            knowledge=[{"id": "kn-1"}],
        )
        d = ctx.to_dict()
        assert len(d["files"]) == 1
        assert len(d["decisions"]) == 1
        assert len(d["active_work"]) == 1
        assert len(d["approvals"]) == 1
        assert len(d["constraints"]) == 1
        assert len(d["knowledge"]) == 1

    def test_backward_compat_is_resolved(self):
        ctx = ResolvedContext(project_id="proj-x")
        assert ctx.is_resolved

    def test_backward_compat_not_resolved(self):
        ctx = ResolvedContext()
        assert not ctx.is_resolved

    def test_default_factory_isolation(self):
        c1 = ResolvedContext()
        c2 = ResolvedContext()
        c1.files.append({"path": "a.py"})
        assert c2.files == []


# ── Enrichment from repo runtime ────────────────────────────────────────


class TestRepoEnrichment:
    def test_populates_files(self, seeded_graph, project_reg, rich_runtimes):
        repo, docs, runtime, knowledge = rich_runtimes
        engine = ContextResolutionEngine(
            reality_graph=seeded_graph,
            project_registry=project_reg,
            repository_runtime=repo,
        )
        ctx = engine.resolve("CreatorOS")
        assert len(ctx.files) == 3
        assert any("clerk" in f.get("path", "") for f in ctx.files)

    def test_no_repo_runtime_no_error(self, seeded_graph):
        engine = ContextResolutionEngine(reality_graph=seeded_graph)
        ctx = engine.resolve("CreatorOS")
        assert ctx.files == []

    def test_repo_runtime_chain_entry(self, seeded_graph, rich_runtimes):
        repo, _, _, _ = rich_runtimes
        engine = ContextResolutionEngine(
            reality_graph=seeded_graph,
            repository_runtime=repo,
        )
        ctx = engine.resolve("CreatorOS")
        steps = [s["step"] for s in ctx.resolution_chain if isinstance(s, dict) and "step" in s]
        assert "repo_runtime_enrichment" in steps

    def test_files_are_dicts(self, seeded_graph, rich_runtimes):
        repo, _, _, _ = rich_runtimes
        engine = ContextResolutionEngine(
            reality_graph=seeded_graph,
            repository_runtime=repo,
        )
        ctx = engine.resolve("CreatorOS")
        assert all(isinstance(f, dict) for f in ctx.files)


# ── Enrichment from documentation runtime ───────────────────────────────


class TestDocEnrichment:
    def test_populates_documents(self, seeded_graph, rich_runtimes):
        _, docs, _, _ = rich_runtimes
        engine = ContextResolutionEngine(
            reality_graph=seeded_graph,
            documentation_runtime=docs,
        )
        ctx = engine.resolve("CreatorOS")
        assert len(ctx.documents) >= 2

    def test_extracts_decisions_from_docs(self, seeded_graph, rich_runtimes):
        _, docs, _, _ = rich_runtimes
        engine = ContextResolutionEngine(
            reality_graph=seeded_graph,
            documentation_runtime=docs,
        )
        ctx = engine.resolve("CreatorOS")
        assert len(ctx.decisions) >= 1

    def test_extracts_constraints_from_docs(self, seeded_graph, rich_runtimes):
        _, docs, _, _ = rich_runtimes
        engine = ContextResolutionEngine(
            reality_graph=seeded_graph,
            documentation_runtime=docs,
        )
        ctx = engine.resolve("CreatorOS")
        assert len(ctx.constraints) >= 1

    def test_no_doc_runtime_no_error(self, seeded_graph):
        engine = ContextResolutionEngine(reality_graph=seeded_graph)
        ctx = engine.resolve("CreatorOS")
        assert ctx.documents == []


# ── Enrichment from runtime awareness ───────────────────────────────────


class TestRuntimeAwarenessEnrichment:
    def test_populates_active_work(self, seeded_graph, rich_runtimes):
        _, _, runtime, _ = rich_runtimes
        engine = ContextResolutionEngine(
            reality_graph=seeded_graph,
            runtime_awareness=runtime,
        )
        ctx = engine.resolve("CreatorOS")
        assert len(ctx.active_work) == 1
        assert ctx.active_work[0]["status"] == "executing"

    def test_no_runtime_awareness_no_error(self, seeded_graph):
        engine = ContextResolutionEngine(reality_graph=seeded_graph)
        ctx = engine.resolve("CreatorOS")
        assert ctx.active_work == []

    def test_runtime_chain_entry(self, seeded_graph, rich_runtimes):
        _, _, runtime, _ = rich_runtimes
        engine = ContextResolutionEngine(
            reality_graph=seeded_graph,
            runtime_awareness=runtime,
        )
        ctx = engine.resolve("CreatorOS")
        steps = [s["step"] for s in ctx.resolution_chain if isinstance(s, dict) and "step" in s]
        assert "runtime_awareness_enrichment" in steps


# ── Enrichment from knowledge runtime ───────────────────────────────────


class TestKnowledgeEnrichment:
    def test_populates_knowledge(self, seeded_graph, rich_runtimes):
        _, _, _, knowledge = rich_runtimes
        engine = ContextResolutionEngine(
            reality_graph=seeded_graph,
            knowledge_runtime=knowledge,
        )
        ctx = engine.resolve("CreatorOS")
        assert len(ctx.knowledge) == 3

    def test_decisions_from_knowledge(self, seeded_graph, rich_runtimes):
        _, _, _, knowledge = rich_runtimes
        engine = ContextResolutionEngine(
            reality_graph=seeded_graph,
            knowledge_runtime=knowledge,
        )
        ctx = engine.resolve("CreatorOS")
        decision_summaries = [d.get("summary", "") for d in ctx.decisions]
        assert any("Clerk" in s for s in decision_summaries)

    def test_constraints_from_knowledge(self, seeded_graph, rich_runtimes):
        _, _, _, knowledge = rich_runtimes
        engine = ContextResolutionEngine(
            reality_graph=seeded_graph,
            knowledge_runtime=knowledge,
        )
        ctx = engine.resolve("CreatorOS")
        constraint_summaries = [c.get("summary", "") for c in ctx.constraints]
        assert any("tenant" in s.lower() for s in constraint_summaries)

    def test_no_knowledge_runtime_no_error(self, seeded_graph):
        engine = ContextResolutionEngine(reality_graph=seeded_graph)
        ctx = engine.resolve("CreatorOS")
        assert ctx.knowledge == []

    def test_knowledge_chain_entry(self, seeded_graph, rich_runtimes):
        _, _, _, knowledge = rich_runtimes
        engine = ContextResolutionEngine(
            reality_graph=seeded_graph,
            knowledge_runtime=knowledge,
        )
        ctx = engine.resolve("CreatorOS")
        steps = [s["step"] for s in ctx.resolution_chain if isinstance(s, dict) and "step" in s]
        assert "knowledge_runtime_enrichment" in steps


# ── Confidence scoring with new fields ──────────────────────────────────


class TestConfidenceV2:
    def test_files_boost_confidence(self, seeded_graph, rich_runtimes):
        repo, _, _, _ = rich_runtimes
        engine_with = ContextResolutionEngine(
            reality_graph=seeded_graph,
            repository_runtime=repo,
        )
        engine_without = ContextResolutionEngine(reality_graph=seeded_graph)
        ctx_with = engine_with.resolve("CreatorOS")
        ctx_without = engine_without.resolve("CreatorOS")
        assert ctx_with.confidence > ctx_without.confidence

    def test_docs_boost_confidence(self, seeded_graph, rich_runtimes):
        _, docs, _, _ = rich_runtimes
        engine_with = ContextResolutionEngine(
            reality_graph=seeded_graph,
            documentation_runtime=docs,
        )
        engine_without = ContextResolutionEngine(reality_graph=seeded_graph)
        ctx_with = engine_with.resolve("CreatorOS")
        ctx_without = engine_without.resolve("CreatorOS")
        assert ctx_with.confidence > ctx_without.confidence

    def test_knowledge_boosts_confidence(self, seeded_graph, rich_runtimes):
        _, _, _, knowledge = rich_runtimes
        engine_with = ContextResolutionEngine(
            reality_graph=seeded_graph,
            knowledge_runtime=knowledge,
        )
        engine_without = ContextResolutionEngine(reality_graph=seeded_graph)
        ctx_with = engine_with.resolve("CreatorOS")
        ctx_without = engine_without.resolve("CreatorOS")
        assert ctx_with.confidence > ctx_without.confidence

    def test_all_runtimes_max_confidence(self, seeded_graph, rich_runtimes):
        repo, docs, runtime, knowledge = rich_runtimes
        engine = ContextResolutionEngine(
            reality_graph=seeded_graph,
            repository_runtime=repo,
            documentation_runtime=docs,
            runtime_awareness=runtime,
            knowledge_runtime=knowledge,
        )
        ctx = engine.resolve("CreatorOS")
        assert ctx.confidence >= 0.9

    def test_topology_only_lower_confidence(self, seeded_graph):
        engine = ContextResolutionEngine(reality_graph=seeded_graph)
        ctx = engine.resolve("CreatorOS")
        assert ctx.confidence < 0.9


# ── Backward compatibility ──────────────────────────────────────────────


class TestBackwardCompat:
    def test_no_runtimes_resolves_like_v1(self, seeded_graph):
        engine = ContextResolutionEngine(reality_graph=seeded_graph)
        ctx = engine.resolve("CreatorOS")
        assert ctx.project_id == "creatoros"
        assert ctx.repository_id == "creatoros-app"
        assert ctx.is_resolved

    def test_empty_new_fields_by_default(self, seeded_graph):
        engine = ContextResolutionEngine(reality_graph=seeded_graph)
        ctx = engine.resolve("CreatorOS")
        assert ctx.files == []
        assert ctx.decisions == []
        assert ctx.active_work == []
        assert ctx.approvals == []
        assert ctx.constraints == []
        assert ctx.knowledge == []

    def test_to_dict_backward_compat(self, seeded_graph):
        engine = ContextResolutionEngine(reality_graph=seeded_graph)
        ctx = engine.resolve("CreatorOS")
        d = ctx.to_dict()
        assert "project_id" in d
        assert "files" in d
        assert "decisions" in d


# ── Full chain tests ────────────────────────────────────────────────────


class TestFullChain:
    def test_all_runtimes_populated(self, seeded_graph, rich_runtimes):
        repo, docs, runtime, knowledge = rich_runtimes
        engine = ContextResolutionEngine(
            reality_graph=seeded_graph,
            repository_runtime=repo,
            documentation_runtime=docs,
            runtime_awareness=runtime,
            knowledge_runtime=knowledge,
        )
        ctx = engine.resolve("CreatorOS")
        assert ctx.project_id == "creatoros"
        assert len(ctx.files) == 3
        assert len(ctx.documents) >= 2
        assert len(ctx.decisions) >= 1
        assert len(ctx.active_work) >= 1
        assert len(ctx.constraints) >= 1
        assert len(ctx.knowledge) >= 1

    def test_resolution_chain_includes_all_steps(self, seeded_graph, rich_runtimes):
        repo, docs, runtime, knowledge = rich_runtimes
        engine = ContextResolutionEngine(
            reality_graph=seeded_graph,
            repository_runtime=repo,
            documentation_runtime=docs,
            runtime_awareness=runtime,
            knowledge_runtime=knowledge,
        )
        ctx = engine.resolve("CreatorOS")
        steps = [s["step"] for s in ctx.resolution_chain if isinstance(s, dict) and "step" in s]
        assert "repo_runtime_enrichment" in steps
        assert "doc_runtime_enrichment" in steps
        assert "runtime_awareness_enrichment" in steps
        assert "knowledge_runtime_enrichment" in steps


# ── Golden Test: "Use Clerk for CreatorOS" ──────────────────────────────


class TestGoldenTest:
    """The Campaign 6 acceptance test.

    Input: "Use Clerk for CreatorOS"
    Expected: project + repo + files + docs + decisions + active work +
              constraints + knowledge resolved with >= 0.95 confidence.
    """

    def test_golden_resolution(self, seeded_graph, project_reg, rich_runtimes):
        repo, docs, runtime, knowledge = rich_runtimes
        engine = ContextResolutionEngine(
            reality_graph=seeded_graph,
            project_registry=project_reg,
            repository_runtime=repo,
            documentation_runtime=docs,
            runtime_awareness=runtime,
            knowledge_runtime=knowledge,
        )
        ctx = engine.resolve("Use Clerk for CreatorOS")

        assert ctx.project_id == "creatoros"
        assert ctx.repository_id == "creatoros-app"

        assert len(ctx.files) >= 1
        assert any("clerk" in f.get("path", "").lower() for f in ctx.files)

        assert len(ctx.documents) >= 1

        assert len(ctx.decisions) >= 1
        assert any("Clerk" in d.get("summary", "") for d in ctx.decisions)

        assert len(ctx.active_work) >= 1

        assert len(ctx.constraints) >= 1

        assert len(ctx.knowledge) >= 1

        assert ctx.confidence >= 0.95

    def test_golden_unresolved_clerk(self, seeded_graph, project_reg, rich_runtimes):
        """Clerk itself is not a graph entity — it appears as unresolved reference."""
        repo, docs, runtime, knowledge = rich_runtimes
        engine = ContextResolutionEngine(
            reality_graph=seeded_graph,
            project_registry=project_reg,
            repository_runtime=repo,
            documentation_runtime=docs,
            runtime_awareness=runtime,
            knowledge_runtime=knowledge,
        )
        ctx = engine.resolve("Use Clerk for CreatorOS")
        assert "Clerk" in ctx.unresolved_references

    def test_golden_is_deterministic(self, seeded_graph, project_reg, rich_runtimes):
        """Same input → same output, zero LLM calls."""
        repo, docs, runtime, knowledge = rich_runtimes
        engine = ContextResolutionEngine(
            reality_graph=seeded_graph,
            project_registry=project_reg,
            repository_runtime=repo,
            documentation_runtime=docs,
            runtime_awareness=runtime,
            knowledge_runtime=knowledge,
        )
        ctx1 = engine.resolve("Use Clerk for CreatorOS")
        ctx2 = engine.resolve("Use Clerk for CreatorOS")
        assert ctx1.project_id == ctx2.project_id
        assert ctx1.confidence == ctx2.confidence
        assert len(ctx1.files) == len(ctx2.files)
        assert len(ctx1.knowledge) == len(ctx2.knowledge)


# ── Edge cases ──────────────────────────────────────────────────────────


class TestEdgeCasesV2:
    def test_runtime_with_no_project(self, seeded_graph, rich_runtimes):
        repo, docs, runtime, knowledge = rich_runtimes
        engine = ContextResolutionEngine(
            reality_graph=seeded_graph,
            repository_runtime=repo,
            documentation_runtime=docs,
            runtime_awareness=runtime,
            knowledge_runtime=knowledge,
        )
        ctx = engine.resolve("some unknown query")
        assert ctx.files == []
        assert ctx.knowledge == []

    def test_broken_repo_runtime(self, seeded_graph):
        class BrokenRuntime:
            def find_files_for_entity(self, _: str) -> list:
                raise RuntimeError("broken")
        engine = ContextResolutionEngine(
            reality_graph=seeded_graph,
            repository_runtime=BrokenRuntime(),
        )
        ctx = engine.resolve("CreatorOS")
        assert ctx.files == []
        assert ctx.project_id == "creatoros"

    def test_broken_knowledge_runtime(self, seeded_graph):
        class BrokenKnowledge:
            def find_for_entity(self, _: str) -> list:
                raise RuntimeError("broken")
        engine = ContextResolutionEngine(
            reality_graph=seeded_graph,
            knowledge_runtime=BrokenKnowledge(),
        )
        ctx = engine.resolve("CreatorOS")
        assert ctx.knowledge == []
        assert ctx.project_id == "creatoros"

    def test_runtime_that_returns_empty(self, seeded_graph):
        engine = ContextResolutionEngine(
            reality_graph=seeded_graph,
            repository_runtime=MockRepositoryRuntime([]),
            documentation_runtime=MockDocumentationRuntime([]),
            runtime_awareness=MockRuntimeAwareness([]),
            knowledge_runtime=MockKnowledgeRuntime([]),
        )
        ctx = engine.resolve("CreatorOS")
        assert ctx.project_id == "creatoros"
        assert ctx.files == []
        assert ctx.knowledge == []
