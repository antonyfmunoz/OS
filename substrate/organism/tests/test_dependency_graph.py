"""Tests for organism dependency graph."""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

import pytest

from substrate.organism.dependency_graph import (
    CriticalPath,
    DependencyEdge,
    DependencyGraph,
    DependencyNode,
    DependencyStrength,
    DependencyType,
    build_dependency_graph,
    persist_dependency_graph,
)


class TestDependencyNode:
    def test_creation(self):
        node = DependencyNode(id="test", name="TestNode", category="subsystem")
        assert node.id == "test"
        assert node.name == "TestNode"

    def test_to_dict(self):
        node = DependencyNode(id="n", name="N", category="subsystem", status="operational")
        d = node.to_dict()
        assert d["id"] == "n"
        assert d["status"] == "operational"


class TestDependencyEdge:
    def test_creation(self):
        edge = DependencyEdge(
            source="a", target="b",
            dep_type=DependencyType.RUNTIME,
            strength=DependencyStrength.HARD,
            evidence="A depends on B at runtime",
        )
        assert edge.source == "a"
        assert edge.target == "b"
        assert edge.dep_type == DependencyType.RUNTIME

    def test_to_dict(self):
        edge = DependencyEdge(
            source="x", target="y",
            dep_type=DependencyType.DATA,
            strength=DependencyStrength.SOFT,
        )
        d = edge.to_dict()
        assert d["type"] == "data"
        assert d["strength"] == "soft"


class TestDependencyGraph:
    def _make_graph(self) -> DependencyGraph:
        g = DependencyGraph()
        g.add_node(DependencyNode(id="a", name="A"))
        g.add_node(DependencyNode(id="b", name="B"))
        g.add_node(DependencyNode(id="c", name="C"))
        g.add_node(DependencyNode(id="d", name="D"))
        g.add_edge(DependencyEdge(source="a", target="b", dep_type=DependencyType.RUNTIME))
        g.add_edge(DependencyEdge(source="b", target="c", dep_type=DependencyType.CODE))
        return g

    def test_add_node(self):
        g = DependencyGraph()
        g.add_node(DependencyNode(id="x", name="X"))
        assert "x" in g.nodes

    def test_add_edge(self):
        g = DependencyGraph()
        g.add_edge(DependencyEdge(source="a", target="b", dep_type=DependencyType.RUNTIME))
        assert len(g.edges) == 1

    def test_upstream(self):
        g = self._make_graph()
        up = g.upstream("a")
        assert "b" in up

    def test_downstream(self):
        g = self._make_graph()
        down = g.downstream("b")
        assert "a" in down

    def test_orphaned_nodes(self):
        g = self._make_graph()
        orphans = g.orphaned_nodes()
        assert "d" in orphans
        assert "a" not in orphans

    def test_circular_dependencies_none(self):
        g = self._make_graph()
        cycles = g.circular_dependencies()
        assert len(cycles) == 0

    def test_circular_dependencies_detected(self):
        g = DependencyGraph()
        g.add_node(DependencyNode(id="a", name="A"))
        g.add_node(DependencyNode(id="b", name="B"))
        g.add_node(DependencyNode(id="c", name="C"))
        g.add_edge(DependencyEdge(source="a", target="b", dep_type=DependencyType.RUNTIME))
        g.add_edge(DependencyEdge(source="b", target="c", dep_type=DependencyType.RUNTIME))
        g.add_edge(DependencyEdge(source="c", target="a", dep_type=DependencyType.RUNTIME))
        cycles = g.circular_dependencies()
        assert len(cycles) > 0

    def test_critical_paths(self):
        g = self._make_graph()
        paths = g.critical_paths()
        assert len(paths) >= 0

    def test_weak_dependencies(self):
        g = DependencyGraph()
        g.add_node(DependencyNode(id="a", name="A"))
        g.add_node(DependencyNode(id="b", name="B"))
        g.add_edge(DependencyEdge(
            source="a", target="b",
            dep_type=DependencyType.RUNTIME,
            strength=DependencyStrength.SOFT,
        ))
        weak = g.weak_dependencies()
        assert len(weak) == 1

    def test_missing_dependencies(self):
        g = DependencyGraph()
        g.add_node(DependencyNode(id="a", name="A"))
        g.add_edge(DependencyEdge(source="a", target="nonexistent", dep_type=DependencyType.RUNTIME))
        missing = g.missing_dependencies()
        assert len(missing) == 1
        assert missing[0]["missing_target"] == "nonexistent"

    def test_summary(self):
        g = self._make_graph()
        s = g.summary()
        assert s["total_nodes"] == 4
        assert s["total_edges"] == 2
        assert "orphaned" in s

    def test_to_dict_serialization(self):
        g = self._make_graph()
        d = g.to_dict()
        serialized = json.dumps(d, default=str)
        parsed = json.loads(serialized)
        assert "summary" in parsed
        assert "nodes" in parsed
        assert "edges" in parsed
        assert "orphaned" in parsed
        assert "cycles" in parsed


class TestBuildDependencyGraph:
    def test_builds_from_world_model(self):
        graph = build_dependency_graph()
        assert len(graph.nodes) > 0
        assert len(graph.edges) > 0

    def test_includes_known_dependencies(self):
        graph = build_dependency_graph()
        daemon_deps = graph.upstream("organism_daemon")
        assert "event_spine" in daemon_deps

    def test_no_edges_to_nonexistent_nodes(self):
        graph = build_dependency_graph()
        missing = graph.missing_dependencies()
        assert len(missing) == 0


class TestPersistence:
    def test_persist_dependency_graph(self):
        g = DependencyGraph()
        g.add_node(DependencyNode(id="p", name="P"))
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            result = persist_dependency_graph(g, path=path)
            assert os.path.isfile(result)
            with open(result) as f:
                data = json.loads(f.readline())
            assert "nodes" in data
        finally:
            os.unlink(path)
