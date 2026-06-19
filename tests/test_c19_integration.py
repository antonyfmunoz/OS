"""Integration tests for Campaign 19 — Execution Fabric & Agent Operations."""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, "/opt/OS")

from substrate.workstation.execution_fabric_runtime import (
    ExecutionFabricRuntime,
    ExecutionFabricSnapshot,
    ExecutionFabricState,
)
from substrate.workstation.agent_workforce_runtime import (
    AgentWorkforceRuntime,
    AgentWorkforceSnapshot,
    WorkforceHealth,
)
from substrate.workstation.session_machine_runtime import (
    MachineSessionBinding,
    SessionMachineRuntime,
    SessionMachineSnapshot,
)


# ── Shared mock fixtures ──────────────────────────────────────────────


@dataclass
class MockComputeNode:
    node_id: str = "node-1"
    node_type: str = "vps"
    health: str = "healthy"
    display_name: str = "VPS"
    active_workers: int = 1
    max_workers: int = 4
    active_executions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id, "node_type": self.node_type,
            "health": self.health, "display_name": self.display_name,
            "active_workers": self.active_workers, "max_workers": self.max_workers,
            "active_executions": self.active_executions,
        }


@dataclass
class MockPlan:
    plan_id: str = "plan-1"
    status: str = "executing"
    target_type: str = "builder"
    session_id: str = "sess-1"

    def to_dict(self) -> dict[str, Any]:
        return {"plan_id": self.plan_id, "status": self.status,
                "target_type": self.target_type, "session_id": self.session_id}


@dataclass
class MockAgentType:
    agent_type_id: str = "builder"
    label: str = "Builder"
    allowed_domains: list[str] = field(default_factory=lambda: ["engineering"])

    def to_dict(self) -> dict[str, Any]:
        return {"agent_type_id": self.agent_type_id, "label": self.label,
                "allowed_domains": self.allowed_domains}


@dataclass
class MockDispatch:
    agent_type: str = "builder"
    work_id: str = "wp-1"
    status: str = "executing"

    def to_dict(self) -> dict[str, Any]:
        return {"agent_type": self.agent_type, "work_id": self.work_id,
                "status": self.status}


@dataclass
class MockDevice:
    device_id: str = "srv1500858"
    display_name: str = "VPS"
    device_type: str = "vps"
    online: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {"device_id": self.device_id, "display_name": self.display_name,
                "device_type": self.device_type, "online": self.online}


@dataclass
class MockSession:
    session_id: str = "sess-1"
    session_type: str = "desktop"
    status: str = "active"
    authority: str = "primary"
    device_id: str = "srv1500858"
    workspace: dict[str, str] = field(default_factory=lambda: {"repo": "OS", "branch": "main"})

    def to_dict(self) -> dict[str, Any]:
        return {"session_id": self.session_id, "session_type": self.session_type,
                "status": self.status, "authority": self.authority,
                "device_id": self.device_id, "workspace": self.workspace}


@dataclass
class MockGovSnapshot:
    state: str = "executing"
    organism_health: str = "active"


def _shared_coord() -> MagicMock:
    coord = MagicMock()
    coord.list_plans_by_status.side_effect = lambda s: [MockPlan()] if s == "executing" else []
    coord.queue_depth.return_value = 1
    coord.pending_approval_count.return_value = 0
    return coord


# ── Snapshot round-trip ───────────────────────────────────────────────


class TestSnapshotRoundTrip:
    def test_fabric_snapshot_all_fields(self) -> None:
        rt = ExecutionFabricRuntime()
        snap = rt.snapshot()
        d = snap.to_dict()
        assert "fabric_state" in d
        assert "compute_nodes" in d
        assert "generated_at" in d
        assert d["generated_at"] > 0

    def test_workforce_snapshot_all_fields(self) -> None:
        rt = AgentWorkforceRuntime()
        snap = rt.snapshot()
        d = snap.to_dict()
        assert "health" in d
        assert "active_dispatches" in d
        assert d["generated_at"] > 0

    def test_session_machine_snapshot_all_fields(self) -> None:
        rt = SessionMachineRuntime()
        snap = rt.snapshot()
        d = snap.to_dict()
        assert "bindings" in d
        assert "primary_session" in d
        assert d["generated_at"] > 0


# ── State derivation chain ───────────────────────────────────────────


class TestStateDerivationChain:
    def test_fabric_reflects_governed_and_compute(self) -> None:
        gov = MagicMock()
        gov.snapshot.return_value = MockGovSnapshot()
        compute = MagicMock()
        compute.get_all_nodes.return_value = [MockComputeNode()]
        coord = _shared_coord()
        rt = ExecutionFabricRuntime(
            governed_execution=gov,
            compute_fabric=compute,
            execution_coordinator=coord,
        )
        snap = rt.snapshot()
        assert snap.execution_state == "executing"
        assert snap.fabric_state == "active"


# ── Session binding accuracy ─────────────────────────────────────────


class TestSessionBindingAccuracy:
    def test_device_session_workspace_map(self) -> None:
        presence = MagicMock()
        presence.list_devices.return_value = [MockDevice()]
        sessions = MagicMock()
        sessions.list_all_sessions.return_value = [MockSession()]
        sessions.pending_handoffs.return_value = []
        rt = SessionMachineRuntime(presence_runtime=presence, session_runtime=sessions)
        snap = rt.snapshot()
        assert snap.total_devices == 1
        assert snap.active_sessions == 1
        assert len(snap.bindings) == 1
        binding = snap.bindings[0]
        assert binding["device_id"] == "srv1500858"
        assert len(binding["sessions"]) == 1


# ── Workforce capacity ───────────────────────────────────────────────


class TestWorkforceCapacity:
    def test_detects_idle(self) -> None:
        registry = MagicMock()
        registry.list_agents.return_value = [MockAgentType()]
        fleet = MagicMock()
        fleet.active_dispatches.return_value = []
        delegation = MagicMock()
        delegation.pending_delegations.return_value = []
        rt = AgentWorkforceRuntime(
            agent_registry=registry,
            agent_fleet=fleet,
            delegation_readiness=delegation,
        )
        assert rt.health() == WorkforceHealth.IDLE

    def test_detects_overloaded(self) -> None:
        registry = MagicMock()
        registry.list_agents.return_value = [MockAgentType()]
        fleet = MagicMock()
        fleet.active_dispatches.return_value = [
            MockDispatch(work_id="1"), MockDispatch(work_id="2"),
        ]
        delegation = MagicMock()
        delegation.pending_delegations.return_value = []
        rt = AgentWorkforceRuntime(
            agent_registry=registry,
            agent_fleet=fleet,
            delegation_readiness=delegation,
        )
        assert rt.health() == WorkforceHealth.OVERLOADED


# ── Cross-runtime consistency ─────────────────────────────────────────


class TestCrossRuntimeConsistency:
    def test_fabric_and_workforce_share_coord_queue(self) -> None:
        coord = _shared_coord()
        fabric = ExecutionFabricRuntime(execution_coordinator=coord)
        workforce = AgentWorkforceRuntime(execution_coordinator=coord)
        assert fabric.snapshot().queue_depth == workforce.snapshot().queue_depth


# ── Blocked work propagation ─────────────────────────────────────────


class TestBlockedWorkPropagation:
    def test_portfolio_blocked_appears_in_fabric(self) -> None:
        portfolio = MagicMock()
        portfolio.blocked_work.return_value = [
            {"work_id": "wp-99", "blocker_type": "missing_capability"},
        ]
        portfolio.velocity.return_value = {}
        rt = ExecutionFabricRuntime(work_portfolio=portfolio)
        blocked = rt.blocked()
        assert len(blocked) == 1
        assert blocked[0]["work_id"] == "wp-99"


# ── Graceful degradation ─────────────────────────────────────────────


class TestGracefulDegradation:
    def test_all_three_degrade_on_empty_deps(self) -> None:
        empty_gov = MagicMock()
        empty_gov.snapshot.return_value = MagicMock(state="idle", organism_health="unknown")
        empty_coord = MagicMock()
        empty_coord.list_plans_by_status.return_value = []
        empty_coord.queue_depth.return_value = 0
        empty_coord.pending_approval_count.return_value = 0
        empty_compute = MagicMock()
        empty_compute.get_all_nodes.return_value = [
            MockComputeNode(active_workers=0, max_workers=4),
        ]
        empty_portfolio = MagicMock()
        empty_portfolio.blocked_work.return_value = []
        empty_portfolio.velocity.return_value = {}
        empty_sessions = MagicMock()
        empty_sessions.list_active_sessions.return_value = []
        empty_sessions.list_all_sessions.return_value = []
        empty_sessions.pending_handoffs.return_value = []
        empty_presence = MagicMock()
        empty_presence.list_devices.return_value = []
        empty_presence.online_devices.return_value = []
        empty_registry = MagicMock()
        empty_registry.list_agents.return_value = []
        empty_fleet = MagicMock()
        empty_fleet.active_dispatches.return_value = []
        empty_delegation = MagicMock()
        empty_delegation.pending_delegations.return_value = []
        empty_delegation.snapshot.return_value = MagicMock(assessments=[], avg_success_probability=0.0)
        empty_workspace = MagicMock()
        empty_workspace.detect_active_workspace.return_value = None
        empty_continuity = MagicMock()
        empty_continuity.recent_handoffs.return_value = []

        f = ExecutionFabricRuntime(
            governed_execution=empty_gov, execution_coordinator=empty_coord,
            compute_fabric=empty_compute, work_portfolio=empty_portfolio,
            session_runtime=empty_sessions, presence_runtime=empty_presence,
        ).snapshot()
        w = AgentWorkforceRuntime(
            agent_registry=empty_registry, agent_fleet=empty_fleet,
            delegation_readiness=empty_delegation, execution_coordinator=empty_coord,
        ).snapshot()
        s = SessionMachineRuntime(
            session_runtime=empty_sessions, presence_runtime=empty_presence,
            workspace_awareness=empty_workspace, continuity_runtime=empty_continuity,
        ).snapshot()
        assert f.fabric_state == "idle"
        assert w.health == "idle"
        assert s.total_devices == 0

    def test_all_three_degrade_on_exceptions(self) -> None:
        bad = MagicMock()
        bad.snapshot.side_effect = RuntimeError("fail")
        bad.get_all_nodes.side_effect = RuntimeError("fail")
        bad.list_agents.side_effect = RuntimeError("fail")
        bad.list_devices.side_effect = RuntimeError("fail")
        bad.list_all_sessions.side_effect = RuntimeError("fail")

        f = ExecutionFabricRuntime(compute_fabric=bad).snapshot()
        w = AgentWorkforceRuntime(agent_registry=bad).snapshot()
        s = SessionMachineRuntime(presence_runtime=bad).snapshot()
        assert f.compute_nodes == []
        assert w.total_agent_types == 0
        assert s.total_devices == 0


# ── Full composition ─────────────────────────────────────────────────


class TestFullComposition:
    def test_all_three_independent(self) -> None:
        f = ExecutionFabricRuntime()
        w = AgentWorkforceRuntime()
        s = SessionMachineRuntime()
        fs = f.snapshot()
        ws = w.snapshot()
        ss = s.snapshot()
        assert isinstance(fs, ExecutionFabricSnapshot)
        assert isinstance(ws, AgentWorkforceSnapshot)
        assert isinstance(ss, SessionMachineSnapshot)

    def test_no_cross_dependency_between_c19_runtimes(self) -> None:
        f = ExecutionFabricRuntime()
        w = AgentWorkforceRuntime()
        s = SessionMachineRuntime()
        assert not hasattr(f, "_agent_workforce")
        assert not hasattr(w, "_session_machine")
        assert not hasattr(s, "_execution_fabric")


# ── Type coherence ────────────────────────────────────────────────────


class TestTypeCoherence:
    def test_all_nine_types_registered(self) -> None:
        from substrate.canonical_types import lookup
        types = [
            "ExecutionFabricState", "ExecutionFabricSnapshot", "ExecutionFabricRuntime",
            "WorkforceHealth", "AgentWorkforceSnapshot", "AgentWorkforceRuntime",
            "MachineSessionBinding", "SessionMachineSnapshot", "SessionMachineRuntime",
        ]
        for t in types:
            assert lookup(t) is not None, f"{t} not registered in canonical_types.py"
