"""Tests for EnvironmentGraph — operational topology."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

from substrate.organism.environment_graph import (
    EnvironmentGraph,
    TopologyDiff,
    TopologyNode,
    TopologySnapshot,
)
from substrate.organism.runtime_graph import (
    AvailabilityStatus,
    CostProfile,
    RuntimeCapability,
    RuntimeClass,
    RuntimeGraph,
)


def _make_graph() -> RuntimeGraph:
    g = RuntimeGraph()
    g.register(
        "cc_sdk",
        RuntimeClass.AI_CLI,
        frozenset({RuntimeCapability.REASON}),
        cost=CostProfile(is_subscription=True),
    )
    g.update_status("cc_sdk", AvailabilityStatus.AVAILABLE)
    g.register(
        "docker:os-discord",
        RuntimeClass.CONTAINER,
        frozenset({RuntimeCapability.SHELL}),
    )
    g.update_status("docker:os-discord", AvailabilityStatus.AVAILABLE)
    return g


def test_capture_creates_snapshot():
    env = EnvironmentGraph()
    graph = _make_graph()
    snap = env.capture(graph=graph)

    assert snap.node_count == 2
    assert snap.available_count == 2
    assert snap.timestamp > 0
    ids = snap.node_ids()
    assert "cc_sdk" in ids
    assert "docker:os-discord" in ids


def test_capture_includes_workcells():
    env = EnvironmentGraph()
    workcells = [
        {
            "workcell_id": "advisor",
            "role": "coordinator",
            "alive": True,
            "generation": 3,
            "messages_processed": 10,
            "inbox_depth": 0,
        }
    ]
    snap = env.capture(workcells=workcells)
    assert snap.node_count == 1
    node = snap.nodes[0]
    assert node.node_id == "workcell:advisor"
    assert node.node_type == "workcell"


def test_diff_detects_added_nodes():
    env = EnvironmentGraph()
    g1 = RuntimeGraph()
    g1.register("cc_sdk", RuntimeClass.AI_CLI, frozenset())
    g1.update_status("cc_sdk", AvailabilityStatus.AVAILABLE)
    env.capture(graph=g1)

    g1.register("docker:new", RuntimeClass.CONTAINER, frozenset())
    g1.update_status("docker:new", AvailabilityStatus.AVAILABLE)
    env.capture(graph=g1)

    diff = env.diff()
    assert diff.has_changes
    assert "docker:new" in diff.added


def test_diff_detects_removed_nodes():
    env = EnvironmentGraph()
    g = RuntimeGraph()
    g.register("r1", RuntimeClass.PROCESS, frozenset())
    g.register("r2", RuntimeClass.PROCESS, frozenset())
    env.capture(graph=g)

    g.unregister("r2")
    env.capture(graph=g)

    diff = env.diff()
    assert "r2" in diff.removed


def test_diff_detects_status_changes():
    env = EnvironmentGraph()
    g = RuntimeGraph()
    g.register("r1", RuntimeClass.PROCESS, frozenset())
    g.update_status("r1", AvailabilityStatus.AVAILABLE)
    env.capture(graph=g)

    g.update_status("r1", AvailabilityStatus.UNAVAILABLE)
    env.capture(graph=g)

    diff = env.diff()
    assert len(diff.status_changes) == 1
    assert diff.status_changes[0]["old_status"] == "available"
    assert diff.status_changes[0]["new_status"] == "unavailable"


def test_no_diff_when_unchanged():
    env = EnvironmentGraph()
    g = RuntimeGraph()
    g.register("r1", RuntimeClass.PROCESS, frozenset())
    g.update_status("r1", AvailabilityStatus.AVAILABLE)
    env.capture(graph=g)
    env.capture(graph=g)

    diff = env.diff()
    assert not diff.has_changes


def test_to_dict_structure():
    env = EnvironmentGraph()
    g = _make_graph()
    env.capture(graph=g)

    d = env.to_dict()
    assert d["snapshot_count"] == 1
    assert d["latest"] is not None
    assert d["latest"]["total_nodes"] == 2


def test_latest_returns_none_when_empty():
    env = EnvironmentGraph()
    assert env.latest() is None


def test_recent_snapshots():
    env = EnvironmentGraph()
    g = _make_graph()
    for _ in range(5):
        env.capture(graph=g)

    recent = env.recent_snapshots(limit=3)
    assert len(recent) == 3
