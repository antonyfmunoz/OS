"""Tests for Campaign 6.3 — Runtime Awareness Runtime."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Any

sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")

import pytest

from substrate.organism.runtime_awareness_runtime import (
    RuntimeAwarenessRuntime,
    RuntimeAwarenessSnapshot,
)


# ── Mock Subsystems ───────────────────────────────────────────────────────


@dataclass
class MockWorktree:
    path: str
    branch: str

    def to_dict(self):
        return {"path": self.path, "branch": self.branch}


@dataclass
class MockProcess:
    pid: int
    command: str

    def to_dict(self):
        return {"pid": self.pid, "command": self.command}


@dataclass
class MockContainer:
    name: str
    status: str

    def to_dict(self):
        return {"name": self.name, "status": self.status}


@dataclass
class MockExecution:
    execution_id: str
    status: str

    def to_dict(self):
        return {"execution_id": self.execution_id, "status": self.status}


@dataclass
class MockSnapshot:
    worktrees: list[Any] = field(default_factory=list)
    repositories: list[Any] = field(default_factory=list)
    processes: list[Any] = field(default_factory=list)
    containers: list[Any] = field(default_factory=list)
    executions: list[Any] = field(default_factory=list)


class MockStateRegistry:
    def __init__(self, snapshot: MockSnapshot | None = None):
        self._snap = snapshot

    def latest_snapshot(self):
        return self._snap


@dataclass
class MockWorkPacket:
    packet_id: str
    status: str

    def to_dict(self):
        return {"packet_id": self.packet_id, "status": self.status}


class MockExecutionCoordinator:
    def __init__(self, packets: list[MockWorkPacket] | None = None):
        self._packets = packets or []

    def list_packets(self):
        return self._packets


@dataclass
class MockBlockedNode:
    node_id: str
    status: str = "blocked"
    blocker: str = "dependency"

    def to_dict(self):
        return {"node_id": self.node_id, "status": self.status, "blocker": self.blocker}


class MockWorkGraph:
    def __init__(self, blocked: list[MockBlockedNode] | None = None):
        self._blocked = blocked or []

    def find_blocked(self):
        return self._blocked


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def populated_state():
    return MockStateRegistry(MockSnapshot(
        worktrees=[MockWorktree("/opt/OS/.claude/worktrees/test", "feature/test")],
        repositories=[{"repo": "os", "branch": "main"}],
        processes=[MockProcess(1234, "python3 services/discord_bot.py")],
        containers=[
            MockContainer("os-discord", "running"),
            MockContainer("os-webhook", "exited"),
        ],
        executions=[
            MockExecution("exec-1", "running"),
            MockExecution("exec-2", "completed"),
        ],
    ))


@pytest.fixture
def populated_execution():
    return MockExecutionCoordinator([
        MockWorkPacket("wp-1", "executing"),
        MockWorkPacket("wp-2", "completed"),
        MockWorkPacket("wp-3", "in_progress"),
    ])


@pytest.fixture
def populated_work_graph():
    return MockWorkGraph([
        MockBlockedNode("node-1", blocker="missing_info"),
        MockBlockedNode("node-2", blocker="dependency"),
    ])


# ── RuntimeAwarenessSnapshot Tests ───────────────────────────────────────


class TestSnapshot:
    def test_to_dict(self):
        snap = RuntimeAwarenessSnapshot(
            worktrees=[{"path": "/test"}],
            processes=[{"pid": 1}],
            detected_at=1000.0,
        )
        d = snap.to_dict()
        assert d["worktrees"] == [{"path": "/test"}]
        assert d["detected_at"] == 1000.0

    def test_defaults(self):
        snap = RuntimeAwarenessSnapshot()
        assert snap.worktrees == []
        assert snap.processes == []
        assert snap.active_work_packets == []


# ── Empty Runtime Tests ──────────────────────────────────────────────────


class TestEmptyRuntime:
    def test_snapshot_empty(self):
        rt = RuntimeAwarenessRuntime()
        snap = rt.snapshot()
        assert snap.worktrees == []
        assert snap.processes == []
        assert snap.containers == []
        assert snap.active_work_packets == []
        assert snap.blocked_work == []

    def test_active_work_empty(self):
        rt = RuntimeAwarenessRuntime()
        assert rt.active_work() == []

    def test_blocked_work_empty(self):
        rt = RuntimeAwarenessRuntime()
        assert rt.blocked_work() == []

    def test_health_empty(self):
        rt = RuntimeAwarenessRuntime()
        health = rt.environment_health()
        assert health["process_count"] == 0
        assert health["container_count"] == 0


# ── State Registry Tests ─────────────────────────────────────────────────


class TestStateRegistry:
    def test_collects_worktrees(self, populated_state):
        rt = RuntimeAwarenessRuntime(runtime_state_registry=populated_state)
        snap = rt.snapshot()
        assert len(snap.worktrees) == 1
        assert snap.worktrees[0]["branch"] == "feature/test"

    def test_collects_processes(self, populated_state):
        rt = RuntimeAwarenessRuntime(runtime_state_registry=populated_state)
        snap = rt.snapshot()
        assert len(snap.processes) == 1
        assert snap.processes[0]["pid"] == 1234

    def test_collects_containers(self, populated_state):
        rt = RuntimeAwarenessRuntime(runtime_state_registry=populated_state)
        snap = rt.snapshot()
        assert len(snap.containers) == 2

    def test_collects_repositories(self, populated_state):
        rt = RuntimeAwarenessRuntime(runtime_state_registry=populated_state)
        snap = rt.snapshot()
        assert len(snap.repositories) == 1

    def test_filters_active_executions(self, populated_state):
        rt = RuntimeAwarenessRuntime(runtime_state_registry=populated_state)
        snap = rt.snapshot()
        assert len(snap.active_executions) == 1
        assert snap.active_executions[0]["status"] == "running"

    def test_no_snapshot_returns_empty(self):
        rt = RuntimeAwarenessRuntime(runtime_state_registry=MockStateRegistry(None))
        snap = rt.snapshot()
        assert snap.worktrees == []


# ── Execution Coordinator Tests ──────────────────────────────────────────


class TestExecutionCoordinator:
    def test_collects_active_packets(self, populated_execution):
        rt = RuntimeAwarenessRuntime(execution_coordinator=populated_execution)
        active = rt.active_work()
        assert len(active) == 2
        statuses = {a["status"] for a in active}
        assert "executing" in statuses
        assert "in_progress" in statuses

    def test_excludes_completed(self, populated_execution):
        rt = RuntimeAwarenessRuntime(execution_coordinator=populated_execution)
        active = rt.active_work()
        assert all(a["status"] != "completed" for a in active)


# ── Work Graph Tests ─────────────────────────────────────────────────────


class TestWorkGraph:
    def test_collects_blocked(self, populated_work_graph):
        rt = RuntimeAwarenessRuntime(work_graph=populated_work_graph)
        blocked = rt.blocked_work()
        assert len(blocked) == 2
        assert blocked[0]["blocker"] == "missing_info"

    def test_no_blocked(self):
        rt = RuntimeAwarenessRuntime(work_graph=MockWorkGraph([]))
        assert rt.blocked_work() == []


# ── Environment Health Tests ─────────────────────────────────────────────


class TestEnvironmentHealth:
    def test_health_with_data(self, populated_state, populated_execution, populated_work_graph):
        rt = RuntimeAwarenessRuntime(
            runtime_state_registry=populated_state,
            execution_coordinator=populated_execution,
            work_graph=populated_work_graph,
        )
        health = rt.environment_health()
        assert health["process_count"] == 1
        assert health["container_count"] == 2
        assert health["healthy_containers"] == 1
        assert health["unhealthy_containers"] == 1
        assert health["active_executions"] == 1
        assert health["blocked_count"] == 2


# ── Full Integration Tests ───────────────────────────────────────────────


class TestFullIntegration:
    def test_all_sources_combined(self, populated_state, populated_execution, populated_work_graph):
        rt = RuntimeAwarenessRuntime(
            runtime_state_registry=populated_state,
            execution_coordinator=populated_execution,
            work_graph=populated_work_graph,
        )
        snap = rt.snapshot()
        assert snap.detected_at > 0
        assert len(snap.worktrees) == 1
        assert len(snap.containers) == 2
        assert len(snap.active_work_packets) == 2
        assert len(snap.blocked_work) == 2

    def test_to_dict_safe_handles_dicts(self):
        assert RuntimeAwarenessRuntime._to_dict_safe({"a": 1}) == {"a": 1}

    def test_to_dict_safe_handles_to_dict(self):
        class HasToDict:
            def to_dict(self):
                return {"x": 1}
        assert RuntimeAwarenessRuntime._to_dict_safe(HasToDict()) == {"x": 1}

    def test_to_dict_safe_handles_unknown(self):
        result = RuntimeAwarenessRuntime._to_dict_safe("hello")
        assert "repr" in result
