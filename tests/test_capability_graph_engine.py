"""Campaign 10.0 — Capability Graph Engine tests.

Tests dependency/composition edges, graph traversal, cycle detection,
orphan/bottleneck analysis, persistence, graceful degradation.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.organism.capability_graph_engine import (
    CapabilityEdge,
    CapabilityGraphEngine,
    CapabilityRelationType,
)


# ── Lightweight mocks ────────────────────────────────────────────────


class _MockCap:
    def __init__(self, capability_id: str = "", name: str = "") -> None:
        self.capability_id = capability_id
        self.name = name


class _MockCapabilityRuntime:
    def __init__(self, caps: list | None = None) -> None:
        self._caps = {c.capability_id: c for c in (caps or [])}

    def list_capabilities(self) -> list:
        return list(self._caps.values())

    def get(self, capability_id: str):
        return self._caps.get(capability_id)


def _make_engine(**kwargs) -> CapabilityGraphEngine:
    d = tempfile.mkdtemp()
    kwargs.setdefault("data_dir", d)
    return CapabilityGraphEngine(**kwargs)


# ── CapabilityEdge tests ─────────────────────────────────────────────


class TestCapabilityEdge:
    def test_defaults(self) -> None:
        e = CapabilityEdge()
        assert e.edge_id.startswith("cedge-")
        assert e.relation == CapabilityRelationType.DEPENDS_ON
        assert e.strength == 1.0

    def test_to_dict_keys(self) -> None:
        e = CapabilityEdge(source_id="a", target_id="b")
        d = e.to_dict()
        expected = {"edge_id", "source_id", "target_id", "relation", "strength", "evidence_ids", "created_at"}
        assert set(d.keys()) == expected

    def test_round_trip(self) -> None:
        e = CapabilityEdge(source_id="a", target_id="b", relation=CapabilityRelationType.COMPOSES)
        d = e.to_dict()
        e2 = CapabilityEdge.from_dict(d)
        assert e2.source_id == "a"
        assert e2.target_id == "b"
        assert e2.relation == CapabilityRelationType.COMPOSES


class TestCapabilityRelationType:
    def test_values(self) -> None:
        assert CapabilityRelationType.DEPENDS_ON.value == "depends_on"
        assert CapabilityRelationType.COMPOSES.value == "composes"
        assert CapabilityRelationType.ENABLES.value == "enables"
        assert CapabilityRelationType.CONFLICTS_WITH.value == "conflicts_with"


# ── Graph operations ─────────────────────────────────────────────────


class TestAddEdge:
    def test_basic_add(self) -> None:
        eng = _make_engine()
        e = eng.add_edge("cap-a", "cap-b")
        assert e.source_id == "cap-a"
        assert e.target_id == "cap-b"
        assert e.relation == CapabilityRelationType.DEPENDS_ON

    def test_dedup(self) -> None:
        eng = _make_engine()
        e1 = eng.add_edge("cap-a", "cap-b")
        e2 = eng.add_edge("cap-a", "cap-b")
        assert e1.edge_id == e2.edge_id

    def test_different_relations_not_deduped(self) -> None:
        eng = _make_engine()
        e1 = eng.add_edge("cap-a", "cap-b", CapabilityRelationType.DEPENDS_ON)
        e2 = eng.add_edge("cap-a", "cap-b", CapabilityRelationType.ENABLES)
        assert e1.edge_id != e2.edge_id

    def test_strength_clamped(self) -> None:
        eng = _make_engine()
        e = eng.add_edge("a", "b", strength=1.5)
        assert e.strength == 1.0
        e2 = eng.add_edge("c", "d", strength=-0.5)
        assert e2.strength == 0.0


class TestRemoveEdge:
    def test_remove_existing(self) -> None:
        eng = _make_engine()
        e = eng.add_edge("a", "b")
        assert eng.remove_edge(e.edge_id) is True
        assert eng.get_edge(e.edge_id) is None

    def test_remove_nonexistent(self) -> None:
        eng = _make_engine()
        assert eng.remove_edge("nonexistent") is False


class TestDependencies:
    def test_dependencies(self) -> None:
        eng = _make_engine()
        eng.add_edge("cap-a", "cap-b", CapabilityRelationType.DEPENDS_ON)
        eng.add_edge("cap-a", "cap-c", CapabilityRelationType.DEPENDS_ON)
        deps = eng.dependencies("cap-a")
        assert set(deps) == {"cap-b", "cap-c"}

    def test_dependents(self) -> None:
        eng = _make_engine()
        eng.add_edge("cap-a", "cap-x", CapabilityRelationType.DEPENDS_ON)
        eng.add_edge("cap-b", "cap-x", CapabilityRelationType.DEPENDS_ON)
        assert set(eng.dependents("cap-x")) == {"cap-a", "cap-b"}


class TestCompositionTree:
    def test_simple_tree(self) -> None:
        rt = _MockCapabilityRuntime([_MockCap("a", "A"), _MockCap("b", "B")])
        eng = _make_engine(capability_runtime=rt)
        eng.add_edge("a", "b", CapabilityRelationType.COMPOSES)
        tree = eng.composition_tree("a")
        assert tree["capability_id"] == "a"
        assert tree["name"] == "A"
        assert len(tree["children"]) == 1
        assert tree["children"][0]["capability_id"] == "b"

    def test_handles_cycle(self) -> None:
        eng = _make_engine()
        eng.add_edge("a", "b", CapabilityRelationType.COMPOSES)
        eng.add_edge("b", "a", CapabilityRelationType.COMPOSES)
        tree = eng.composition_tree("a")
        assert tree["capability_id"] == "a"


class TestCriticalPath:
    def test_direct_path(self) -> None:
        eng = _make_engine()
        eng.add_edge("a", "b")
        eng.add_edge("b", "c")
        path = eng.critical_path("a", "c")
        assert path == ["a", "b", "c"]

    def test_no_path(self) -> None:
        eng = _make_engine()
        eng.add_edge("a", "b")
        assert eng.critical_path("a", "x") == []

    def test_same_node(self) -> None:
        eng = _make_engine()
        assert eng.critical_path("a", "a") == ["a"]


# ── Analysis ─────────────────────────────────────────────────────────


class TestCycleDetection:
    def test_no_cycles(self) -> None:
        eng = _make_engine()
        eng.add_edge("a", "b")
        eng.add_edge("b", "c")
        assert eng.detect_cycles() == []

    def test_simple_cycle(self) -> None:
        eng = _make_engine()
        eng.add_edge("a", "b")
        eng.add_edge("b", "a")
        cycles = eng.detect_cycles()
        assert len(cycles) >= 1


class TestOrphans:
    def test_orphan_detection(self) -> None:
        rt = _MockCapabilityRuntime([
            _MockCap("a", "A"), _MockCap("b", "B"), _MockCap("c", "C"),
        ])
        eng = _make_engine(capability_runtime=rt)
        eng.add_edge("a", "b")
        orphans = eng.orphans()
        assert "c" in orphans
        assert "a" not in orphans

    def test_no_runtime(self) -> None:
        eng = _make_engine()
        assert eng.orphans() == []


class TestBottlenecks:
    def test_bottleneck_ranking(self) -> None:
        eng = _make_engine()
        eng.add_edge("a", "x")
        eng.add_edge("b", "x")
        eng.add_edge("c", "x")
        eng.add_edge("d", "y")
        bottlenecks = eng.bottlenecks(2)
        assert len(bottlenecks) == 2
        assert bottlenecks[0]["capability_id"] == "x"
        assert bottlenecks[0]["dependent_count"] == 3


class TestSummary:
    def test_summary_keys(self) -> None:
        eng = _make_engine()
        s = eng.summary()
        expected = {"total_edges", "total_nodes", "by_relation", "cycles", "bottlenecks"}
        assert set(s.keys()) == expected


# ── Persistence ──────────────────────────────────────────────────────


class TestPersistence:
    def test_reload(self) -> None:
        d = tempfile.mkdtemp()
        eng = CapabilityGraphEngine(data_dir=d)
        eng.add_edge("a", "b", CapabilityRelationType.COMPOSES)
        eng.add_edge("b", "c")

        eng2 = CapabilityGraphEngine(data_dir=d)
        assert len(eng2.edges_for("a")) >= 1
        assert len(eng2.edges_for("b")) >= 1
