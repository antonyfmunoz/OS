"""Tests for OrchestratorAwarenessRuntime — Campaign 4.0.

Covers: context assembly across 6 domains, domain isolation queries,
awareness scoring, graceful degradation, snapshot round-trip,
read-only guarantee, and dual capability layer distinction.
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock

import pytest

from substrate.organism.orchestrator_awareness_runtime import (
    AwarenessDomain,
    DomainAwareness,
    OrchestratorAwarenessRuntime,
    OrchestratorAwarenessSnapshot,
    OrchestratorContext,
)


# ── Fixtures ──────────────────────────────────────────────────────────────


def _mock_intent() -> MagicMock:
    m = MagicMock()
    m.active_by_scope.return_value = [
        {"intent_id": "i-1", "text": "Build feature", "scope": "engineering"}
    ]
    m.context_for_session.return_value = {"session": "s-1"}
    m.summary.return_value = {"total": 3, "active": 1}
    return m


def _mock_snapshot() -> MagicMock:
    m = MagicMock()
    m.snapshot.return_value = {"device": "vps-01", "session_id": "sess-abc"}
    m.situation.return_value = {"status": "active", "focus": "development"}
    m.changes.return_value = {"recent": ["file1.py"]}
    m.decisions.return_value = {"pending": 0}
    return m


def _mock_attention() -> MagicMock:
    m = MagicMock()
    m.top.return_value = [
        {"category": "approval", "urgency": 0.9},
        {"category": "drift", "urgency": 0.5},
    ]
    m.compute.return_value = {"score": 0.8}
    return m


def _mock_cap_map() -> MagicMock:
    m = MagicMock()
    m.snapshot.return_value = {
        "active_panel": "orchestrator",
        "capability_surface": "primary",
        "total_routes": 52,
    }
    m.mvp_gaps.return_value = [{"name": "voice", "status": "missing"}]
    return m


def _mock_cmd_center() -> MagicMock:
    m = MagicMock()
    m.snapshot.return_value = {"recommendations": [{"action": "deploy"}]}
    m.recommendations.return_value = [{"action": "deploy", "priority": 1}]
    return m


def _mock_exec_surface() -> MagicMock:
    m = MagicMock()
    m.snapshot.return_value = {"pending_approvals": [{"id": "a-1"}], "active_streams": 2}
    m.active_streams.return_value = [{"id": "s-1"}]
    m.pending_approvals.return_value = [{"id": "a-1"}]
    return m


def _mock_capability_runtime() -> MagicMock:
    m = MagicMock()
    m.summary.return_value = {"total": 12, "mature": 4}
    m.list_capabilities.return_value = [MagicMock(capability_id="ec-1")]
    m.capabilities_from_intent.return_value = []
    m.lineage.return_value = {"depth": 3}
    return m


def _mock_capability_router() -> MagicMock:
    m = MagicMock()
    m.capabilities = lambda: ["code_generation", "testing", "deployment"]
    return m


def _mock_ops_runtime() -> MagicMock:
    m = MagicMock()
    m.summary.return_value = {"total": 8, "active": 5}
    m.list_operationalizations.return_value = []
    return m


def _mock_infra_runtime() -> MagicMock:
    m = MagicMock()
    m.summary.return_value = {"total": 6, "healthy": 4}
    m.health_check.return_value = {"overall": "degraded"}
    m.list_entities.return_value = [
        MagicMock(to_dict=lambda: {"infra_type": "device", "name": "vps"}),
        MagicMock(to_dict=lambda: {"infra_type": "service", "name": "discord"}),
    ]
    return m


def _mock_compounding() -> MagicMock:
    m = MagicMock()
    m.summary.return_value = {"promoted": [{"id": "w-1"}], "candidates": 3}
    return m


def _mock_continuity() -> MagicMock:
    m = MagicMock()
    m.status.return_value = {"state": "active", "last_snapshot": "2026-06-16"}
    m.get_snapshot.return_value = {"data": "snapshot-data"}
    return m


def _mock_templates() -> MagicMock:
    m = MagicMock()
    m.summary.return_value = {"total": 15, "approved": 10}
    m.pending_approvals.return_value = []
    return m


def _mock_fleet() -> MagicMock:
    m = MagicMock()
    m.fleet_status.return_value = {"active_agents": 2, "total": 5}
    m.active_dispatches.return_value = [
        MagicMock(to_dict=lambda: {"dispatch_id": "d-1", "agent": "builder"}),
    ]
    m.fleet_health.return_value = {"healthy": True}
    return m


def _mock_fabric() -> MagicMock:
    m = MagicMock()
    m.nodes.return_value = [
        MagicMock(to_dict=lambda: {"node_id": "n-1", "role": "vps"}),
    ]
    m.health.return_value = {"overall": "healthy"}
    m.active_executions.return_value = [
        MagicMock(to_dict=lambda: {"exec_id": "e-1"}),
    ]
    return m


def _mock_governed() -> MagicMock:
    m = MagicMock()
    m.active.return_value = [
        MagicMock(to_dict=lambda: {"work_id": "w-1", "status": "running"}),
    ]
    m.blocked.return_value = []
    m.queue.return_value = []
    return m


def _mock_graph() -> MagicMock:
    m = MagicMock()
    m.list_nodes.return_value = [{"node_id": "gn-1"}]
    m.audit_completeness.return_value = {"complete": 10, "incomplete": 2}
    return m


def _mock_meta_ide() -> MagicMock:
    m = MagicMock()
    m.workspace_snapshot.return_value = {"repos": [{"name": "OS", "path": "/opt/OS"}]}
    m.ide_status.return_value = {
        "active_repo": "OS",
        "active_directory": "/opt/OS/substrate",
        "active_files": ["types.py", "gateway.py"],
    }
    m.active_development.return_value = [
        MagicMock(to_dict=lambda: {"stream_id": "ds-1"}),
    ]
    return m


def _mock_build_loop() -> MagicMock:
    m = MagicMock()
    m.status.return_value = {"active_requests": 1, "active_loops": [{"id": "bl-1"}]}
    m.active_requests.return_value = [MagicMock(to_dict=lambda: {"id": "br-1"})]
    return m


def _mock_proj_integration() -> MagicMock:
    m = MagicMock()
    m.snapshot.return_value = {
        "active_projection": "entrepreneuros",
        "active_project": "initiate-arena",
        "codebases": [{"name": "OS"}],
    }
    return m


def _mock_proj_port() -> MagicMock:
    m = MagicMock()
    m.list_registrations.return_value = [
        MagicMock(to_dict=lambda: {"projection_id": "eos", "name": "EntrepreneurOS"}),
    ]
    return m


def _mock_source_reg() -> MagicMock:
    m = MagicMock()
    m.summary.return_value = {
        "total": 20,
        "documents": [{"id": "d-1"}],
        "skills": [{"id": "s-1"}],
        "adapters": [{"id": "a-1"}],
    }
    return m


def _mock_reconciliation() -> MagicMock:
    m = MagicMock()
    m.list_divergences.return_value = [
        MagicMock(to_dict=lambda: {"divergence_id": "div-1", "type": "schema_drift"}),
    ]
    return m


def _build_full_runtime() -> OrchestratorAwarenessRuntime:
    return OrchestratorAwarenessRuntime(
        intent_runtime=_mock_intent(),
        snapshot_runtime=_mock_snapshot(),
        attention_engine=_mock_attention(),
        capability_map=_mock_cap_map(),
        command_center=_mock_cmd_center(),
        execution_surface=_mock_exec_surface(),
        capability_runtime=_mock_capability_runtime(),
        capability_router=_mock_capability_router(),
        operationalization_runtime=_mock_ops_runtime(),
        infrastructure_runtime=_mock_infra_runtime(),
        compounding_engine=_mock_compounding(),
        continuity_runtime=_mock_continuity(),
        template_registry=_mock_templates(),
        agent_fleet=_mock_fleet(),
        compute_fabric=_mock_fabric(),
        governed_work=_mock_governed(),
        execution_graph=_mock_graph(),
        meta_ide=_mock_meta_ide(),
        build_loop=_mock_build_loop(),
        projection_integration=_mock_proj_integration(),
        projection_port=_mock_proj_port(),
        source_registry=_mock_source_reg(),
        reconciliation_engine=_mock_reconciliation(),
    )


# ── Context Assembly ──────────────────────────────────────────────────────


class TestContextAssembly:
    def test_full_context_has_generated_at(self) -> None:
        rt = _build_full_runtime()
        ctx = rt.context()
        assert ctx.generated_at > 0

    def test_operator_state_populated(self) -> None:
        rt = _build_full_runtime()
        ctx = rt.context()
        assert ctx.operator_state["situation"] == {"status": "active", "focus": "development"}

    def test_active_device_from_snapshot(self) -> None:
        rt = _build_full_runtime()
        ctx = rt.context()
        assert ctx.active_device == "vps-01"

    def test_active_session_from_snapshot(self) -> None:
        rt = _build_full_runtime()
        ctx = rt.context()
        assert ctx.active_session == "sess-abc"

    def test_active_intents_populated(self) -> None:
        rt = _build_full_runtime()
        ctx = rt.context()
        assert len(ctx.active_intents) == 1
        assert ctx.active_intents[0]["intent_id"] == "i-1"

    def test_active_agents_from_fleet(self) -> None:
        rt = _build_full_runtime()
        ctx = rt.context()
        assert len(ctx.active_agents) == 1
        assert ctx.active_agents[0]["dispatch_id"] == "d-1"

    def test_active_compute_nodes(self) -> None:
        rt = _build_full_runtime()
        ctx = rt.context()
        assert len(ctx.active_compute_nodes) == 1
        assert ctx.active_compute_nodes[0]["node_id"] == "n-1"

    def test_active_executions_merged(self) -> None:
        rt = _build_full_runtime()
        ctx = rt.context()
        assert len(ctx.active_executions) == 2

    def test_active_projection_from_integration(self) -> None:
        rt = _build_full_runtime()
        ctx = rt.context()
        assert ctx.active_projection == "entrepreneuros"

    def test_active_repo_from_ide(self) -> None:
        rt = _build_full_runtime()
        ctx = rt.context()
        assert ctx.active_repo == "OS"

    def test_active_files_from_ide(self) -> None:
        rt = _build_full_runtime()
        ctx = rt.context()
        assert "types.py" in ctx.active_files

    def test_projections_from_port(self) -> None:
        rt = _build_full_runtime()
        ctx = rt.context()
        assert len(ctx.projections) == 1
        assert ctx.projections[0]["projection_id"] == "eos"


# ── Dual Capability Layer ─────────────────────────────────────────────────


class TestDualCapabilityLayer:
    def test_capabilities_has_emergent_and_execution(self) -> None:
        rt = _build_full_runtime()
        ctx = rt.context()
        assert "emergent" in ctx.capabilities
        assert "execution" in ctx.capabilities

    def test_emergent_capabilities_from_organism(self) -> None:
        rt = _build_full_runtime()
        ctx = rt.context()
        assert ctx.capabilities["emergent"]["total"] == 12

    def test_execution_capabilities_from_router(self) -> None:
        rt = _build_full_runtime()
        ctx = rt.context()
        exec_caps = ctx.capabilities["execution"]
        assert "execution_capabilities" in exec_caps

    def test_no_capability_router_graceful(self) -> None:
        rt = OrchestratorAwarenessRuntime(capability_runtime=_mock_capability_runtime())
        ctx = rt.context()
        assert ctx.capabilities["execution"] == {}

    def test_no_capability_runtime_graceful(self) -> None:
        rt = OrchestratorAwarenessRuntime(capability_router=_mock_capability_router())
        ctx = rt.context()
        assert ctx.capabilities["emergent"] == {}


# ── Domain Isolation ──────────────────────────────────────────────────────


class TestDomainIsolation:
    def test_operator_awareness_independent(self) -> None:
        rt = OrchestratorAwarenessRuntime(
            snapshot_runtime=_mock_snapshot(),
            attention_engine=_mock_attention(),
        )
        result = rt.operator_awareness()
        assert result["subsystems_available"] == 2
        assert "situation" in result

    def test_cockpit_awareness_independent(self) -> None:
        rt = OrchestratorAwarenessRuntime(capability_map=_mock_cap_map())
        result = rt.cockpit_awareness()
        assert result["subsystems_available"] == 1
        assert result["capability_map"]["total_routes"] == 52

    def test_organism_awareness_independent(self) -> None:
        rt = OrchestratorAwarenessRuntime(
            capability_runtime=_mock_capability_runtime(),
            infrastructure_runtime=_mock_infra_runtime(),
        )
        result = rt.organism_awareness()
        assert result["subsystems_available"] == 2

    def test_execution_awareness_independent(self) -> None:
        rt = OrchestratorAwarenessRuntime(agent_fleet=_mock_fleet())
        result = rt.execution_awareness()
        assert result["subsystems_available"] == 1
        assert result["fleet_status"]["active_agents"] == 2

    def test_development_awareness_independent(self) -> None:
        rt = OrchestratorAwarenessRuntime(meta_ide=_mock_meta_ide())
        result = rt.development_awareness()
        assert result["subsystems_available"] == 1
        assert result["workspace"]["repos"][0]["name"] == "OS"

    def test_source_truth_awareness_independent(self) -> None:
        rt = OrchestratorAwarenessRuntime(projection_port=_mock_proj_port())
        result = rt.source_truth_awareness()
        assert result["subsystems_available"] == 1
        assert len(result["projection_registrations"]) == 1


# ── Awareness Scoring ─────────────────────────────────────────────────────


class TestAwarenessScoring:
    def test_full_score_is_1(self) -> None:
        rt = _build_full_runtime()
        assert rt.awareness_score() == 1.0

    def test_empty_score_is_0(self) -> None:
        rt = OrchestratorAwarenessRuntime()
        assert rt.awareness_score() == 0.0

    def test_partial_score_correct(self) -> None:
        rt = OrchestratorAwarenessRuntime(
            intent_runtime=_mock_intent(),
            snapshot_runtime=_mock_snapshot(),
            attention_engine=_mock_attention(),
        )
        score = rt.awareness_score()
        assert score == round(3 / 23, 3)

    def test_score_matches_active_over_total(self) -> None:
        rt = OrchestratorAwarenessRuntime(
            agent_fleet=_mock_fleet(),
            compute_fabric=_mock_fabric(),
        )
        assert rt.awareness_score() == round(2 / 23, 3)


# ── Domain Health ─────────────────────────────────────────────────────────


class TestDomainHealth:
    def test_six_domains_returned(self) -> None:
        rt = _build_full_runtime()
        health = rt.domain_health()
        assert len(health) == 6

    def test_all_available_when_full(self) -> None:
        rt = _build_full_runtime()
        health = rt.domain_health()
        assert all(d.available for d in health)

    def test_operator_domain_count(self) -> None:
        rt = _build_full_runtime()
        health = rt.domain_health()
        op = [d for d in health if d.domain == AwarenessDomain.OPERATOR][0]
        assert op.subsystem_count == 3
        assert op.active_subsystems == 3

    def test_organism_domain_count(self) -> None:
        rt = _build_full_runtime()
        health = rt.domain_health()
        org = [d for d in health if d.domain == AwarenessDomain.ORGANISM][0]
        assert org.subsystem_count == 7
        assert org.active_subsystems == 7

    def test_empty_runtime_no_domains_available(self) -> None:
        rt = OrchestratorAwarenessRuntime()
        health = rt.domain_health()
        assert not any(d.available for d in health)

    def test_domain_health_to_dict(self) -> None:
        rt = _build_full_runtime()
        health = rt.domain_health()
        d = health[0].to_dict()
        assert "domain" in d
        assert "available" in d
        assert "subsystem_count" in d


# ── Graceful Degradation ─────────────────────────────────────────────────


class TestGracefulDegradation:
    def test_no_intent_runtime(self) -> None:
        rt = OrchestratorAwarenessRuntime(snapshot_runtime=_mock_snapshot())
        ctx = rt.context()
        assert ctx.active_intents == []

    def test_no_snapshot_runtime(self) -> None:
        rt = OrchestratorAwarenessRuntime(intent_runtime=_mock_intent())
        ctx = rt.context()
        assert ctx.active_device == ""

    def test_no_fleet(self) -> None:
        rt = OrchestratorAwarenessRuntime()
        ctx = rt.context()
        assert ctx.active_agents == []

    def test_no_fabric(self) -> None:
        rt = OrchestratorAwarenessRuntime()
        ctx = rt.context()
        assert ctx.active_compute_nodes == []

    def test_no_meta_ide(self) -> None:
        rt = OrchestratorAwarenessRuntime()
        ctx = rt.context()
        assert ctx.repositories == []
        assert ctx.active_files == []

    def test_no_proj_port(self) -> None:
        rt = OrchestratorAwarenessRuntime()
        ctx = rt.context()
        assert ctx.projections == []

    def test_no_source_registry(self) -> None:
        rt = OrchestratorAwarenessRuntime()
        ctx = rt.context()
        assert ctx.documents == []
        assert ctx.skills == []

    def test_no_infra_runtime(self) -> None:
        rt = OrchestratorAwarenessRuntime()
        ctx = rt.context()
        assert ctx.infrastructure == {}

    def test_no_compounding(self) -> None:
        rt = OrchestratorAwarenessRuntime()
        ctx = rt.context()
        assert ctx.workflows == []

    def test_subsystem_raises_exception(self) -> None:
        bad = MagicMock()
        bad.snapshot.side_effect = RuntimeError("boom")
        bad.situation.side_effect = RuntimeError("boom")
        bad.changes.side_effect = RuntimeError("boom")
        bad.decisions.side_effect = RuntimeError("boom")
        rt = OrchestratorAwarenessRuntime(snapshot_runtime=bad)
        ctx = rt.context()
        assert ctx.operator_state["situation"] == {}


# ── Snapshot ──────────────────────────────────────────────────────────────


class TestSnapshot:
    def test_snapshot_full_round_trip(self) -> None:
        rt = _build_full_runtime()
        snap = rt.snapshot()
        assert isinstance(snap, OrchestratorAwarenessSnapshot)
        assert snap.awareness_score == 1.0
        assert snap.total_subsystems == 23

    def test_snapshot_to_dict(self) -> None:
        rt = _build_full_runtime()
        snap = rt.snapshot()
        d = snap.to_dict()
        assert "context" in d
        assert "domain_health" in d
        assert d["total_subsystems"] == 23

    def test_snapshot_context_is_populated(self) -> None:
        rt = _build_full_runtime()
        snap = rt.snapshot()
        assert snap.context.active_device == "vps-01"

    def test_snapshot_empty_runtime(self) -> None:
        rt = OrchestratorAwarenessRuntime()
        snap = rt.snapshot()
        assert snap.awareness_score == 0.0
        assert snap.active_subsystems == 0


# ── Context Serialization ─────────────────────────────────────────────────


class TestContextSerialization:
    def test_context_to_dict(self) -> None:
        rt = _build_full_runtime()
        ctx = rt.context()
        d = ctx.to_dict()
        assert "operator_state" in d
        assert "active_device" in d
        assert "capabilities" in d
        assert "generated_at" in d

    def test_context_to_dict_has_all_fields(self) -> None:
        rt = _build_full_runtime()
        ctx = rt.context()
        d = ctx.to_dict()
        expected_keys = {
            "operator_state", "active_device", "active_session", "active_intents",
            "active_projection", "active_project", "active_repo", "active_directory",
            "active_files", "active_panel", "active_capability_surface",
            "active_agents", "active_compute_nodes", "active_executions",
            "active_loops", "pending_approvals", "projections", "capabilities",
            "workflows", "templates", "skills", "adapters", "operationalizations",
            "infrastructure", "documents", "codebases", "repositories", "devices",
            "recommendations", "coherence_summary", "continuity_state", "generated_at",
        }
        assert expected_keys == set(d.keys())


# ── No Mutation ───────────────────────────────────────────────────────────


class TestNoMutation:
    def test_context_does_not_write(self) -> None:
        intent = _mock_intent()
        rt = OrchestratorAwarenessRuntime(intent_runtime=intent)
        rt.context()
        intent.capture.assert_not_called()

    def test_snapshot_does_not_write(self) -> None:
        fleet = _mock_fleet()
        rt = OrchestratorAwarenessRuntime(agent_fleet=fleet)
        rt.snapshot()
        fleet.dispatch.assert_not_called() if hasattr(fleet, "dispatch") else None

    def test_domain_queries_read_only(self) -> None:
        governed = _mock_governed()
        rt = OrchestratorAwarenessRuntime(governed_work=governed)
        rt.execution_awareness()
        governed.approve_work.assert_not_called() if hasattr(governed, "approve_work") else None

    def test_multiple_calls_independent(self) -> None:
        rt = _build_full_runtime()
        ctx1 = rt.context()
        ctx2 = rt.context()
        assert ctx1.generated_at <= ctx2.generated_at
        assert ctx1.active_device == ctx2.active_device


# ── Empty State ───────────────────────────────────────────────────────────


class TestEmptyState:
    def test_empty_context_valid(self) -> None:
        rt = OrchestratorAwarenessRuntime()
        ctx = rt.context()
        assert ctx.generated_at > 0
        assert ctx.active_device == ""
        assert ctx.active_agents == []
        assert ctx.projections == []

    def test_empty_snapshot_valid(self) -> None:
        rt = OrchestratorAwarenessRuntime()
        snap = rt.snapshot()
        assert snap.total_subsystems == 23
        assert snap.active_subsystems == 0
        assert snap.awareness_score == 0.0


# ── Organism Fields ───────────────────────────────────────────────────────


class TestOrganismFields:
    def test_documents_from_source_registry(self) -> None:
        rt = OrchestratorAwarenessRuntime(source_registry=_mock_source_reg())
        ctx = rt.context()
        assert len(ctx.documents) == 1

    def test_skills_from_source_registry(self) -> None:
        rt = OrchestratorAwarenessRuntime(source_registry=_mock_source_reg())
        ctx = rt.context()
        assert len(ctx.skills) == 1

    def test_devices_from_infrastructure(self) -> None:
        rt = OrchestratorAwarenessRuntime(infrastructure_runtime=_mock_infra_runtime())
        ctx = rt.context()
        assert len(ctx.devices) == 1
        assert ctx.devices[0]["infra_type"] == "device"

    def test_codebases_from_projection_integration(self) -> None:
        rt = OrchestratorAwarenessRuntime(projection_integration=_mock_proj_integration())
        ctx = rt.context()
        assert len(ctx.codebases) == 1
