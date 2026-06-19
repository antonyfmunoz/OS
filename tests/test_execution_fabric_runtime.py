"""Tests for ExecutionFabricRuntime — Campaign 19.0."""
from __future__ import annotations

import sys
import time
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


# ── Mock helpers ──────────────────────────────────────────────────────


@dataclass
class MockComputeNode:
    node_id: str = "node-1"
    node_type: str = "vps"
    health: str = "healthy"
    display_name: str = "VPS"
    active_workers: int = 0
    max_workers: int = 4
    active_executions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "health": self.health,
            "display_name": self.display_name,
            "active_workers": self.active_workers,
            "max_workers": self.max_workers,
            "active_executions": self.active_executions,
        }


@dataclass
class MockGovSnapshot:
    state: str = "idle"
    organism_health: str = "healthy"


@dataclass
class MockPlan:
    plan_id: str = "plan-1"
    status: str = "executing"
    target_type: str = "builder"
    session_id: str = "sess-1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "status": self.status,
            "target_type": self.target_type,
            "session_id": self.session_id,
        }


def _empty_compute() -> MagicMock:
    m = MagicMock()
    m.get_all_nodes.return_value = [
        MockComputeNode(active_workers=0, max_workers=4),
    ]
    return m


def _empty_coord() -> MagicMock:
    m = MagicMock()
    m.list_plans_by_status.return_value = []
    m.queue_depth.return_value = 0
    m.pending_approval_count.return_value = 0
    return m


def _empty_gov() -> MagicMock:
    m = MagicMock()
    m.snapshot.return_value = MockGovSnapshot()
    return m


def _empty_portfolio() -> MagicMock:
    m = MagicMock()
    m.blocked_work.return_value = []
    m.velocity.return_value = {}
    return m


def _empty_sessions() -> MagicMock:
    m = MagicMock()
    m.list_active_sessions.return_value = []
    return m


def _empty_presence() -> MagicMock:
    m = MagicMock()
    m.list_devices.return_value = []
    m.online_devices.return_value = []
    return m


def _make_runtime(**kwargs: Any) -> ExecutionFabricRuntime:
    return ExecutionFabricRuntime(**kwargs)


def _make_empty_runtime(**kwargs: Any) -> ExecutionFabricRuntime:
    """Runtime with all deps mocked to return empty/idle."""
    defaults: dict[str, Any] = {
        "governed_execution": _empty_gov(),
        "execution_coordinator": _empty_coord(),
        "compute_fabric": _empty_compute(),
        "work_portfolio": _empty_portfolio(),
        "session_runtime": _empty_sessions(),
        "presence_runtime": _empty_presence(),
    }
    defaults.update(kwargs)
    return ExecutionFabricRuntime(**defaults)


# ── State derivation ──────────────────────────────────────────────────


class TestStateDrivation:
    def test_idle_when_empty_deps(self) -> None:
        rt = _make_empty_runtime()
        assert rt.state() == ExecutionFabricState.IDLE

    def test_idle_with_empty_nodes(self) -> None:
        compute = MagicMock()
        compute.get_all_nodes.return_value = [
            MockComputeNode(active_workers=0, max_workers=4)
        ]
        coord = MagicMock()
        coord.list_plans_by_status.return_value = []
        coord.queue_depth.return_value = 0
        rt = _make_runtime(compute_fabric=compute, execution_coordinator=coord)
        assert rt.state() == ExecutionFabricState.IDLE

    def test_active_with_executing_plans(self) -> None:
        compute = MagicMock()
        compute.get_all_nodes.return_value = [
            MockComputeNode(active_workers=1, max_workers=4)
        ]
        coord = MagicMock()
        coord.list_plans_by_status.side_effect = lambda s: [MockPlan()] if s == "executing" else []
        coord.queue_depth.return_value = 0
        rt = _make_runtime(compute_fabric=compute, execution_coordinator=coord)
        assert rt.state() == ExecutionFabricState.ACTIVE

    def test_saturated_above_80_percent(self) -> None:
        compute = MagicMock()
        compute.get_all_nodes.return_value = [
            MockComputeNode(active_workers=5, max_workers=6)
        ]
        coord = MagicMock()
        coord.list_plans_by_status.side_effect = lambda s: [MockPlan()] if s == "executing" else []
        coord.queue_depth.return_value = 0
        rt = _make_runtime(compute_fabric=compute, execution_coordinator=coord)
        assert rt.state() == ExecutionFabricState.SATURATED

    def test_blocked_queue_no_capacity(self) -> None:
        compute = MagicMock()
        compute.get_all_nodes.return_value = [
            MockComputeNode(active_workers=4, max_workers=4)
        ]
        coord = MagicMock()
        coord.list_plans_by_status.return_value = []
        coord.queue_depth.return_value = 3
        rt = _make_runtime(compute_fabric=compute, execution_coordinator=coord)
        assert rt.state() == ExecutionFabricState.BLOCKED

    def test_degraded_unreachable_node(self) -> None:
        compute = MagicMock()
        compute.get_all_nodes.return_value = [
            MockComputeNode(health="unreachable")
        ]
        coord = MagicMock()
        coord.list_plans_by_status.return_value = []
        coord.queue_depth.return_value = 0
        rt = _make_runtime(compute_fabric=compute, execution_coordinator=coord)
        assert rt.state() == ExecutionFabricState.DEGRADED


# ── Snapshot ──────────────────────────────────────────────────────────


class TestSnapshot:
    def test_snapshot_returns_all_fields(self) -> None:
        rt = _make_empty_runtime()
        snap = rt.snapshot()
        assert isinstance(snap, ExecutionFabricSnapshot)
        assert snap.fabric_state == "idle"
        assert snap.generated_at > 0

    def test_snapshot_to_dict_keys(self) -> None:
        rt = _make_empty_runtime()
        d = rt.snapshot().to_dict()
        expected = {
            "fabric_state", "execution_state", "organism_health",
            "active_plans", "queue_depth", "awaiting_approval_count",
            "compute_nodes", "active_sessions", "online_devices",
            "blocked_work", "work_velocity", "generated_at",
        }
        assert set(d.keys()) == expected

    def test_snapshot_with_data(self) -> None:
        gov = MagicMock()
        gov.snapshot.return_value = MockGovSnapshot(state="executing", organism_health="active")
        compute = MagicMock()
        compute.get_all_nodes.return_value = [MockComputeNode()]
        coord = MagicMock()
        coord.list_plans_by_status.side_effect = lambda s: [MockPlan()] if s == "executing" else []
        coord.queue_depth.return_value = 2
        coord.pending_approval_count.return_value = 1
        rt = _make_runtime(
            governed_execution=gov,
            compute_fabric=compute,
            execution_coordinator=coord,
        )
        snap = rt.snapshot()
        assert snap.execution_state == "executing"
        assert snap.organism_health == "active"
        assert len(snap.active_plans) == 1
        assert snap.queue_depth == 2
        assert snap.awaiting_approval_count == 1
        assert len(snap.compute_nodes) == 1


# ── Public API ────────────────────────────────────────────────────────


class TestPublicAPI:
    def test_active_executions_empty(self) -> None:
        rt = _make_empty_runtime()
        assert rt.active_executions() == []

    def test_blocked_empty(self) -> None:
        rt = _make_empty_runtime()
        assert rt.blocked() == []

    def test_capacity_idle(self) -> None:
        rt = _make_empty_runtime()
        cap = rt.capacity()
        assert cap["total_capacity"] > 0
        assert cap["used_capacity"] == 0
        assert cap["available_capacity"] == cap["total_capacity"]
        assert cap["utilization"] == 0.0

    def test_capacity_with_nodes(self) -> None:
        compute = MagicMock()
        compute.get_all_nodes.return_value = [
            MockComputeNode(active_workers=1, max_workers=4),
            MockComputeNode(node_id="n2", active_workers=2, max_workers=4),
        ]
        rt = _make_runtime(compute_fabric=compute)
        cap = rt.capacity()
        assert cap["total_capacity"] == 8
        assert cap["used_capacity"] == 3
        assert cap["available_capacity"] == 5
        assert cap["node_count"] == 2

    def test_session_bindings_empty(self) -> None:
        rt = _make_empty_runtime()
        assert rt.session_bindings() == []

    def test_summary_keys(self) -> None:
        rt = _make_empty_runtime()
        s = rt.summary()
        assert s["ok"] is True
        assert "fabric_state" in s
        assert "active_plan_count" in s
        assert "generated_at" in s


# ── Graceful degradation ─────────────────────────────────────────────


class TestGracefulDegradation:
    def test_empty_deps_produce_idle_snapshot(self) -> None:
        rt = _make_empty_runtime()
        snap = rt.snapshot()
        assert snap.active_plans == []
        assert snap.active_sessions == []
        assert snap.online_devices == []
        assert snap.blocked_work == []
        assert snap.fabric_state == "idle"

    def test_exception_in_dep_returns_defaults(self) -> None:
        compute = MagicMock()
        compute.get_all_nodes.side_effect = RuntimeError("boom")
        rt = _make_runtime(compute_fabric=compute)
        snap = rt.snapshot()
        assert snap.compute_nodes == []

    def test_dep_returning_unexpected_type(self) -> None:
        portfolio = MagicMock()
        portfolio.blocked_work.return_value = "not-a-list"
        portfolio.velocity.return_value = 42
        rt = _make_runtime(work_portfolio=portfolio)
        snap = rt.snapshot()
        assert snap.blocked_work == []
        assert snap.work_velocity == {}


# ── Type registration ─────────────────────────────────────────────────


class TestTypeRegistration:
    def test_types_registered_in_canonical(self) -> None:
        from substrate.canonical_types import lookup
        assert lookup("ExecutionFabricState") is not None
        assert lookup("ExecutionFabricSnapshot") is not None
        assert lookup("ExecutionFabricRuntime") is not None

    def test_enum_values(self) -> None:
        assert ExecutionFabricState.IDLE.value == "idle"
        assert ExecutionFabricState.DEGRADED.value == "degraded"
