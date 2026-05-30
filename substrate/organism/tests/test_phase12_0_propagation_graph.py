"""Phase 12.0 — Universal Propagation Graph / Correspondence Layer tests.

Covers: PropagationNode, PropagationEdge, PropagationGraph, ChangeEvent,
PropagationPlan, PropagationWave, PropagationAction, PropagationResult,
ImpactAnalyzer, PropagationPlanner, PropagationExecutor, GraphBuilder,
correspondence proof, UniversalWorkQueue integration, API route shapes,
cockpit data shapes, and safety invariants.

Phase 12.0. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import os
import tempfile
import time

import pytest

from substrate.organism.propagation_graph import (
    PropagationGraph,
    PropagationNode,
    PropagationEdge,
    PropagationNodeType,
    PropagationEdgeType,
    PropagationMode,
    EdgeStrength,
)
from substrate.organism.change_event import (
    ChangeEvent,
    ChangeType,
    PropagationAction,
    PropagationActionStatus,
    PropagationWave,
    PropagationPlan,
    PropagationResult,
    persist_change_events,
    load_change_events,
    persist_propagation_plans,
    persist_propagation_results,
)
from substrate.organism.impact_analyzer import (
    ImpactAnalyzer,
    ImpactAnalysis,
    ImpactedNode,
)
from substrate.organism.propagation_planner import PropagationPlanner
from substrate.organism.propagation_executor import PropagationExecutor, ExecutionMode


# ── PropagationNode serialization ──────────────────────────────────────────

class TestPropagationNodeSerialization:
    def test_to_dict_round_trip(self):
        node = PropagationNode(
            node_id="pgn-test-001",
            node_type=PropagationNodeType.WORK_PACKET,
            title="Test Packet",
            description="A test work packet",
            source_type="work_packet",
            source_id="wp-001",
            domain="self_build",
            status="classified",
        )
        d = node.to_dict()
        restored = PropagationNode.from_dict(d)
        assert restored.node_id == "pgn-test-001"
        assert restored.node_type == PropagationNodeType.WORK_PACKET
        assert restored.title == "Test Packet"
        assert restored.domain == "self_build"

    def test_from_dict_invalid_type_defaults(self):
        d = {"node_id": "pgn-x", "node_type": "invalid_type_xyz"}
        node = PropagationNode.from_dict(d)
        assert node.node_type == PropagationNodeType.WORK_PACKET

    def test_all_node_types_serialize(self):
        for nt in PropagationNodeType:
            node = PropagationNode(node_type=nt, title=nt.value)
            d = node.to_dict()
            assert d["node_type"] == nt.value
            restored = PropagationNode.from_dict(d)
            assert restored.node_type == nt

    def test_metadata_and_evidence_preserved(self):
        node = PropagationNode(
            metadata={"key": "value", "nested": {"a": 1}},
            evidence=[{"type": "test", "detail": "check"}],
        )
        d = node.to_dict()
        restored = PropagationNode.from_dict(d)
        assert restored.metadata["key"] == "value"
        assert restored.evidence[0]["type"] == "test"


# ── PropagationEdge serialization ──────────────────────────────────────────

class TestPropagationEdgeSerialization:
    def test_to_dict_round_trip(self):
        edge = PropagationEdge(
            edge_id="pge-test-001",
            from_node_id="pgn-a",
            to_node_id="pgn-b",
            edge_type=PropagationEdgeType.DEPENDS_ON,
            propagation_mode=PropagationMode.RECOMPUTE,
            strength=EdgeStrength.HARD,
            reason="test dependency",
            validation_required=True,
        )
        d = edge.to_dict()
        restored = PropagationEdge.from_dict(d)
        assert restored.edge_id == "pge-test-001"
        assert restored.edge_type == PropagationEdgeType.DEPENDS_ON
        assert restored.propagation_mode == PropagationMode.RECOMPUTE
        assert restored.strength == EdgeStrength.HARD
        assert restored.validation_required is True

    def test_from_dict_invalid_enums_default(self):
        d = {
            "edge_type": "fake_edge",
            "propagation_mode": "fake_mode",
            "strength": "fake_strength",
        }
        edge = PropagationEdge.from_dict(d)
        assert edge.edge_type == PropagationEdgeType.DEPENDS_ON
        assert edge.propagation_mode == PropagationMode.NOTIFY_ONLY
        assert edge.strength == EdgeStrength.SOFT

    def test_all_edge_types_serialize(self):
        for et in PropagationEdgeType:
            edge = PropagationEdge(edge_type=et)
            d = edge.to_dict()
            assert d["edge_type"] == et.value

    def test_all_propagation_modes_serialize(self):
        for pm in PropagationMode:
            edge = PropagationEdge(propagation_mode=pm)
            d = edge.to_dict()
            assert d["propagation_mode"] == pm.value

    def test_all_strengths_serialize(self):
        for s in EdgeStrength:
            edge = PropagationEdge(strength=s)
            d = edge.to_dict()
            assert d["strength"] == s.value

    def test_conditions_and_evidence_preserved(self):
        edge = PropagationEdge(
            conditions=["status == active", "risk < medium"],
            evidence=[{"type": "code_reference", "path": "foo.py"}],
        )
        d = edge.to_dict()
        restored = PropagationEdge.from_dict(d)
        assert len(restored.conditions) == 2
        assert restored.evidence[0]["path"] == "foo.py"


# ── PropagationGraph build/traversal ──────────────────────────────────────

class TestPropagationGraphBuild:
    def _make_graph(self) -> PropagationGraph:
        g = PropagationGraph()
        n1 = PropagationNode(node_id="n1", node_type=PropagationNodeType.WORK_PACKET, title="WP1")
        n2 = PropagationNode(node_id="n2", node_type=PropagationNodeType.WORKCELL, title="WC1")
        n3 = PropagationNode(node_id="n3", node_type=PropagationNodeType.ROADMAP_PHASE, title="RP1")
        n4 = PropagationNode(node_id="n4", node_type=PropagationNodeType.API_ROUTE, title="API1")
        g.add_node(n1)
        g.add_node(n2)
        g.add_node(n3)
        g.add_node(n4)
        g.add_edge(PropagationEdge(
            edge_id="e1", from_node_id="n1", to_node_id="n2",
            edge_type=PropagationEdgeType.OWNS,
        ))
        g.add_edge(PropagationEdge(
            edge_id="e2", from_node_id="n1", to_node_id="n3",
            edge_type=PropagationEdgeType.FEEDS,
        ))
        g.add_edge(PropagationEdge(
            edge_id="e3", from_node_id="n3", to_node_id="n4",
            edge_type=PropagationEdgeType.UPDATES,
        ))
        return g

    def test_add_nodes_and_edges(self):
        g = self._make_graph()
        assert len(g.nodes) == 4
        assert len(g.edges) == 3

    def test_upstream_traversal(self):
        g = self._make_graph()
        upstream = g.upstream("n4")
        assert "n3" in upstream
        assert "n1" in upstream

    def test_downstream_traversal(self):
        g = self._make_graph()
        downstream = g.downstream("n1")
        assert "n2" in downstream
        assert "n3" in downstream
        assert "n4" in downstream

    def test_affected_by_change(self):
        g = self._make_graph()
        affected = g.affected_by_change("n1")
        assert len(affected) == 3
        assert "n2" in affected
        assert "n3" in affected
        assert "n4" in affected

    def test_impact_radius(self):
        g = self._make_graph()
        radius = g.impact_radius("n1")
        assert radius["downstream_count"] == 3
        assert radius["upstream_count"] == 0

    def test_orphaned_nodes(self):
        g = PropagationGraph()
        g.add_node(PropagationNode(node_id="orphan1"))
        g.add_node(PropagationNode(node_id="orphan2"))
        g.add_node(PropagationNode(node_id="connected"))
        g.add_edge(PropagationEdge(
            from_node_id="connected", to_node_id="orphan1",
        ))
        orphans = g.orphaned_nodes()
        assert "orphan2" in orphans
        assert "connected" not in orphans
        assert "orphan1" not in orphans

    def test_graph_stats(self):
        g = self._make_graph()
        stats = g.graph_stats()
        assert stats["total_nodes"] == 4
        assert stats["total_edges"] == 3
        assert "work_packet" in stats["node_type_counts"]

    def test_to_dict_and_from_dict(self):
        g = self._make_graph()
        d = g.to_dict()
        restored = PropagationGraph.from_dict(d)
        assert len(restored.nodes) == 4
        assert len(restored.edges) == 3

    def test_to_safe_dict(self):
        g = self._make_graph()
        safe = g.to_safe_dict()
        assert "nodes" not in safe
        assert safe["node_count"] == 4


class TestCycleDetection:
    def test_no_cycles(self):
        g = PropagationGraph()
        g.add_node(PropagationNode(node_id="a"))
        g.add_node(PropagationNode(node_id="b"))
        g.add_edge(PropagationEdge(from_node_id="a", to_node_id="b"))
        assert len(g.detect_cycles()) == 0

    def test_simple_cycle(self):
        g = PropagationGraph()
        g.add_node(PropagationNode(node_id="a"))
        g.add_node(PropagationNode(node_id="b"))
        g.add_edge(PropagationEdge(from_node_id="a", to_node_id="b"))
        g.add_edge(PropagationEdge(from_node_id="b", to_node_id="a"))
        cycles = g.detect_cycles()
        assert len(cycles) > 0

    def test_self_loop(self):
        g = PropagationGraph()
        g.add_node(PropagationNode(node_id="a"))
        g.add_edge(PropagationEdge(from_node_id="a", to_node_id="a"))
        cycles = g.detect_cycles()
        assert len(cycles) > 0


class TestGraphPersistence:
    def test_persist_and_load(self):
        g = PropagationGraph()
        g.add_node(PropagationNode(node_id="p1", title="Test"))
        g.add_edge(PropagationEdge(from_node_id="p1", to_node_id="p1"))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "graph.json")
            g.persist(path)
            loaded = PropagationGraph.load(path)
            assert len(loaded.nodes) == 1
            assert len(loaded.edges) == 1

    def test_load_missing_returns_empty(self):
        g = PropagationGraph.load("/nonexistent/path/graph.json")
        assert len(g.nodes) == 0


# ── ChangeEvent serialization ──────────────────────────────────────────────

class TestChangeEventSerialization:
    def test_to_dict_round_trip(self):
        event = ChangeEvent(
            change_id="ce-test-001",
            change_type=ChangeType.WORK_PACKET_UPDATED,
            source_node_id="pgn-wp-001",
            title="Test change",
            before_state={"status": "planned"},
            after_state={"status": "active"},
            changed_fields=["status"],
        )
        d = event.to_dict()
        restored = ChangeEvent.from_dict(d)
        assert restored.change_id == "ce-test-001"
        assert restored.change_type == ChangeType.WORK_PACKET_UPDATED
        assert restored.changed_fields == ["status"]
        assert restored.before_state["status"] == "planned"

    def test_all_change_types_serialize(self):
        for ct in ChangeType:
            event = ChangeEvent(change_type=ct)
            d = event.to_dict()
            assert d["change_type"] == ct.value

    def test_invalid_change_type_defaults(self):
        d = {"change_type": "invalid_xyz"}
        event = ChangeEvent.from_dict(d)
        assert event.change_type == ChangeType.WORK_PACKET_UPDATED

    def test_persist_and_load(self):
        events = [
            ChangeEvent(title="Event A"),
            ChangeEvent(title="Event B"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "events.jsonl")
            persist_change_events(events, path)
            loaded = load_change_events(path)
            assert len(loaded) == 2
            assert loaded[0].title == "Event A"

    def test_load_missing_returns_empty(self):
        assert load_change_events("/nonexistent/events.jsonl") == []


# ── PropagationPlan serialization ──────────────────────────────────────────

class TestPropagationPlanSerialization:
    def test_to_dict_round_trip(self):
        plan = PropagationPlan(
            plan_id="pp-test",
            change_event_id="ce-test",
            root_node_id="n1",
            affected_nodes=["n2", "n3"],
            execution_mode="dry_run",
        )
        d = plan.to_dict()
        restored = PropagationPlan.from_dict(d)
        assert restored.plan_id == "pp-test"
        assert restored.affected_nodes == ["n2", "n3"]

    def test_waves_serialize(self):
        wave = PropagationWave(
            wave_number=1,
            nodes=["n1", "n2"],
            can_run_parallel=True,
            reconvergence_required=True,
        )
        plan = PropagationPlan(propagation_waves=[wave])
        d = plan.to_dict()
        restored = PropagationPlan.from_dict(d)
        assert len(restored.propagation_waves) == 1
        assert restored.propagation_waves[0].wave_number == 1
        assert restored.propagation_waves[0].reconvergence_required is True


# ── PropagationAction ──────────────────────────────────────────────────────

class TestPropagationAction:
    def test_to_dict_round_trip(self):
        action = PropagationAction(
            action_id="pa-test",
            node_id="n1",
            action_type="recompute",
            risk_class="low",
            status=PropagationActionStatus.PENDING,
        )
        d = action.to_dict()
        restored = PropagationAction.from_dict(d)
        assert restored.action_id == "pa-test"
        assert restored.action_type == "recompute"
        assert restored.status == PropagationActionStatus.PENDING

    def test_all_statuses_serialize(self):
        for s in PropagationActionStatus:
            action = PropagationAction(status=s)
            d = action.to_dict()
            assert d["status"] == s.value


# ── PropagationResult ──────────────────────────────────────────────────────

class TestPropagationResult:
    def test_to_dict_round_trip(self):
        result = PropagationResult(
            result_id="pr-test",
            plan_id="pp-test",
            completed_actions=["pa-1"],
            failed_actions=["pa-2"],
            status="partial",
        )
        d = result.to_dict()
        restored = PropagationResult.from_dict(d)
        assert restored.result_id == "pr-test"
        assert restored.completed_actions == ["pa-1"]
        assert restored.status == "partial"

    def test_persist(self):
        results = [PropagationResult(result_id="pr-1")]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "results.jsonl")
            persist_propagation_results(results, path)
            assert os.path.exists(path)


# ── ImpactAnalyzer ──────────────────────────────────────────────────────────

class TestImpactAnalyzer:
    def _make_graph_and_event(self):
        g = PropagationGraph()
        g.add_node(PropagationNode(node_id="src", node_type=PropagationNodeType.WORK_PACKET, title="Source"))
        g.add_node(PropagationNode(node_id="d1", node_type=PropagationNodeType.WORKCELL, title="Direct1"))
        g.add_node(PropagationNode(node_id="d2", node_type=PropagationNodeType.ROADMAP_PHASE, title="Direct2"))
        g.add_node(PropagationNode(node_id="i1", node_type=PropagationNodeType.API_ROUTE, title="Indirect1"))
        g.add_edge(PropagationEdge(
            from_node_id="src", to_node_id="d1",
            edge_type=PropagationEdgeType.OWNS,
            propagation_mode=PropagationMode.RECOMPUTE,
            strength=EdgeStrength.HARD,
        ))
        g.add_edge(PropagationEdge(
            from_node_id="src", to_node_id="d2",
            edge_type=PropagationEdgeType.FEEDS,
            propagation_mode=PropagationMode.NOTIFY_ONLY,
            strength=EdgeStrength.SOFT,
        ))
        g.add_edge(PropagationEdge(
            from_node_id="d2", to_node_id="i1",
            edge_type=PropagationEdgeType.UPDATES,
            propagation_mode=PropagationMode.REVALIDATE,
            strength=EdgeStrength.SOFT,
        ))
        event = ChangeEvent(
            source_node_id="src",
            change_type=ChangeType.WORK_PACKET_UPDATED,
            title="Test WP update",
        )
        return g, event

    def test_basic_analysis(self):
        g, event = self._make_graph_and_event()
        analyzer = ImpactAnalyzer(g)
        analysis = analyzer.analyze(event)
        assert len(analysis.direct_impact) == 2
        assert len(analysis.indirect_impact) == 1
        assert analysis.impact_depth == 2
        assert analysis.impact_radius == 3

    def test_missing_source_node(self):
        g = PropagationGraph()
        event = ChangeEvent(source_node_id="nonexistent")
        analyzer = ImpactAnalyzer(g)
        analysis = analyzer.analyze(event)
        assert len(analysis.affected_nodes) == 0

    def test_parallelizable_groups(self):
        g, event = self._make_graph_and_event()
        analyzer = ImpactAnalyzer(g)
        analysis = analyzer.analyze(event)
        assert len(analysis.parallelizable_groups) >= 1

    def test_reconvergence_detection(self):
        g = PropagationGraph()
        g.add_node(PropagationNode(node_id="root"))
        g.add_node(PropagationNode(node_id="branch1"))
        g.add_node(PropagationNode(node_id="branch2"))
        g.add_node(PropagationNode(node_id="converge"))
        g.add_edge(PropagationEdge(from_node_id="root", to_node_id="branch1"))
        g.add_edge(PropagationEdge(from_node_id="root", to_node_id="branch2"))
        g.add_edge(PropagationEdge(from_node_id="branch1", to_node_id="converge"))
        g.add_edge(PropagationEdge(from_node_id="branch2", to_node_id="converge"))
        event = ChangeEvent(source_node_id="root")
        analyzer = ImpactAnalyzer(g)
        analysis = analyzer.analyze(event)
        assert "converge" in analysis.reconvergence_required

    def test_risk_summary(self):
        g, event = self._make_graph_and_event()
        analyzer = ImpactAnalyzer(g)
        analysis = analyzer.analyze(event)
        assert "total_affected" in analysis.risk_summary
        assert analysis.risk_summary["total_affected"] == 3

    def test_medium_risk_blocks_non_safe(self):
        g = PropagationGraph()
        g.add_node(PropagationNode(node_id="src"))
        g.add_node(PropagationNode(node_id="target"))
        g.add_edge(PropagationEdge(
            from_node_id="src", to_node_id="target",
            propagation_mode=PropagationMode.REGENERATE,
            strength=EdgeStrength.HARD,
        ))
        event = ChangeEvent(source_node_id="src", risk_class="medium")
        analyzer = ImpactAnalyzer(g)
        analysis = analyzer.analyze(event)
        blocked = [n for n in analysis.affected_nodes if n.is_blocked]
        assert len(blocked) > 0


# ── PropagationPlanner ─────────────────────────────────────────────────────

class TestPropagationPlanner:
    def _make_graph_analysis_event(self):
        g = PropagationGraph()
        g.add_node(PropagationNode(node_id="src", node_type=PropagationNodeType.WORK_PACKET))
        g.add_node(PropagationNode(node_id="wc1", node_type=PropagationNodeType.WORKCELL, title="WC"))
        g.add_node(PropagationNode(node_id="rp1", node_type=PropagationNodeType.ROADMAP_PHASE, title="RP"))
        g.add_node(PropagationNode(node_id="api1", node_type=PropagationNodeType.API_ROUTE, title="API"))
        g.add_edge(PropagationEdge(
            from_node_id="src", to_node_id="wc1",
            edge_type=PropagationEdgeType.OWNS,
            propagation_mode=PropagationMode.RECOMPUTE,
            strength=EdgeStrength.HARD,
        ))
        g.add_edge(PropagationEdge(
            from_node_id="src", to_node_id="rp1",
            edge_type=PropagationEdgeType.FEEDS,
            propagation_mode=PropagationMode.NOTIFY_ONLY,
        ))
        g.add_edge(PropagationEdge(
            from_node_id="rp1", to_node_id="api1",
            edge_type=PropagationEdgeType.UPDATES,
            propagation_mode=PropagationMode.REVALIDATE,
        ))
        event = ChangeEvent(source_node_id="src", title="Test change")
        analyzer = ImpactAnalyzer(g)
        analysis = analyzer.analyze(event)
        return g, analysis, event

    def test_plan_creates_waves(self):
        g, analysis, event = self._make_graph_analysis_event()
        planner = PropagationPlanner(g)
        plan = planner.plan(event, analysis)
        assert len(plan.propagation_waves) > 0

    def test_wave_ordering(self):
        g, analysis, event = self._make_graph_analysis_event()
        planner = PropagationPlanner(g)
        plan = planner.plan(event, analysis)
        wave_numbers = [w.wave_number for w in plan.propagation_waves]
        assert wave_numbers == sorted(wave_numbers)

    def test_parallel_action_grouping(self):
        g, analysis, event = self._make_graph_analysis_event()
        planner = PropagationPlanner(g)
        plan = planner.plan(event, analysis)
        for wave in plan.propagation_waves:
            assert wave.can_run_parallel is True

    def test_idempotency_keys(self):
        g, analysis, event = self._make_graph_analysis_event()
        planner = PropagationPlanner(g)
        plan = planner.plan(event, analysis)
        keys = set()
        for wave in plan.propagation_waves:
            for action in wave.actions:
                assert action.idempotency_key != ""
                assert action.idempotency_key not in keys
                keys.add(action.idempotency_key)

    def test_approval_required_propagation(self):
        g = PropagationGraph()
        g.add_node(PropagationNode(node_id="src"))
        g.add_node(PropagationNode(node_id="approval", node_type=PropagationNodeType.APPROVAL_PACKET))
        g.add_edge(PropagationEdge(
            from_node_id="src", to_node_id="approval",
            edge_type=PropagationEdgeType.REQUIRES_APPROVAL_FROM,
        ))
        event = ChangeEvent(source_node_id="src")
        analyzer = ImpactAnalyzer(g)
        analysis = analyzer.analyze(event)
        planner = PropagationPlanner(g)
        plan = planner.plan(event, analysis)
        assert "approval" in plan.approval_required_nodes

    def test_human_required_propagation(self):
        g = PropagationGraph()
        g.add_node(PropagationNode(node_id="src"))
        g.add_node(PropagationNode(node_id="human", node_type=PropagationNodeType.HUMAN_ACTION))
        g.add_edge(PropagationEdge(
            from_node_id="src", to_node_id="human",
            edge_type=PropagationEdgeType.REQUIRES_HUMAN_ACTION_FROM,
        ))
        event = ChangeEvent(source_node_id="src")
        analyzer = ImpactAnalyzer(g)
        analysis = analyzer.analyze(event)
        planner = PropagationPlanner(g)
        plan = planner.plan(event, analysis)
        assert "human" in plan.human_required_nodes

    def test_medium_risk_blocked(self):
        g = PropagationGraph()
        g.add_node(PropagationNode(node_id="src"))
        g.add_node(PropagationNode(node_id="target"))
        g.add_edge(PropagationEdge(
            from_node_id="src", to_node_id="target",
            propagation_mode=PropagationMode.REGENERATE,
            strength=EdgeStrength.HARD,
        ))
        event = ChangeEvent(source_node_id="src", risk_class="medium")
        analyzer = ImpactAnalyzer(g)
        analysis = analyzer.analyze(event)
        planner = PropagationPlanner(g)
        plan = planner.plan(event, analysis)
        assert "target" in plan.blocked_nodes

    def test_plan_execution_mode_is_dry_run(self):
        g, analysis, event = self._make_graph_analysis_event()
        planner = PropagationPlanner(g)
        plan = planner.plan(event, analysis)
        assert plan.execution_mode == "dry_run"


# ── PropagationExecutor ────────────────────────────────────────────────────

class TestPropagationExecutor:
    def _make_plan(self):
        g = PropagationGraph()
        g.add_node(PropagationNode(node_id="src", title="Source"))
        g.add_node(PropagationNode(node_id="t1", title="Target1"))
        g.add_node(PropagationNode(node_id="t2", title="Target2"))
        g.add_edge(PropagationEdge(from_node_id="src", to_node_id="t1"))
        g.add_edge(PropagationEdge(from_node_id="src", to_node_id="t2"))

        wave = PropagationWave(
            wave_number=1,
            nodes=["t1", "t2"],
            actions=[
                PropagationAction(
                    action_id="a1", node_id="t1",
                    action_type="recompute",
                    idempotency_key="idem-a1",
                ),
                PropagationAction(
                    action_id="a2", node_id="t2",
                    action_type="notify",
                    idempotency_key="idem-a2",
                ),
            ],
        )
        plan = PropagationPlan(
            plan_id="pp-test",
            propagation_waves=[wave],
        )
        return g, plan

    def test_dry_run_execution(self):
        g, plan = self._make_plan()
        executor = PropagationExecutor(g, mode=ExecutionMode.DRY_RUN)
        result = executor.execute(plan)
        assert result.status in ("completed", "completed_with_gates")
        assert len(result.completed_actions) == 2

    def test_idempotency_dedup(self):
        g, plan = self._make_plan()
        plan.propagation_waves[0].actions.append(
            PropagationAction(
                action_id="a3", node_id="t1",
                action_type="recompute",
                idempotency_key="idem-a1",
            )
        )
        executor = PropagationExecutor(g, mode=ExecutionMode.DRY_RUN)
        result = executor.execute(plan)
        assert len(result.no_op_actions) >= 1

    def test_blocked_action(self):
        g, plan = self._make_plan()
        plan.propagation_waves[0].actions[0].status = PropagationActionStatus.BLOCKED
        executor = PropagationExecutor(g, mode=ExecutionMode.DRY_RUN)
        result = executor.execute(plan)
        assert len(result.blocked_actions) >= 1

    def test_approval_required_action(self):
        g, plan = self._make_plan()
        plan.propagation_waves[0].actions[0].status = PropagationActionStatus.APPROVAL_REQUIRED
        executor = PropagationExecutor(g, mode=ExecutionMode.DRY_RUN)
        result = executor.execute(plan)
        assert len(result.approval_required_actions) >= 1

    def test_human_required_action(self):
        g, plan = self._make_plan()
        plan.propagation_waves[0].actions[0].status = PropagationActionStatus.HUMAN_REQUIRED
        executor = PropagationExecutor(g, mode=ExecutionMode.DRY_RUN)
        result = executor.execute(plan)
        assert len(result.human_required_actions) >= 1

    def test_failure_isolation(self):
        g, plan = self._make_plan()
        plan.propagation_waves[0].actions[0].status = PropagationActionStatus.BLOCKED
        executor = PropagationExecutor(g, mode=ExecutionMode.DRY_RUN)
        result = executor.execute(plan)
        assert len(result.completed_actions) >= 1
        assert len(result.blocked_actions) >= 1

    def test_recompute_only_mode(self):
        g, plan = self._make_plan()
        plan.propagation_waves[0].actions[0].action_type = "regenerate"
        executor = PropagationExecutor(g, mode=ExecutionMode.RECOMPUTE_ONLY)
        result = executor.execute(plan)
        skipped = [a for a in result.no_op_actions]
        assert len(skipped) >= 1

    def test_governed_mode_blocked(self):
        g, plan = self._make_plan()
        executor = PropagationExecutor(g, mode=ExecutionMode.GOVERNED)
        result = executor.execute(plan)
        assert len(result.blocked_actions) == 2

    def test_persist_result(self):
        g, plan = self._make_plan()
        executor = PropagationExecutor(g, mode=ExecutionMode.DRY_RUN)
        result = executor.execute(plan)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "results.jsonl")
            executor.persist_result(result, path)
            assert os.path.exists(path)
            with open(path) as f:
                lines = f.readlines()
            assert len(lines) == 1

    def test_wave_ordering_preserved(self):
        g = PropagationGraph()
        g.add_node(PropagationNode(node_id="n1", title="N1"))
        g.add_node(PropagationNode(node_id="n2", title="N2"))
        w1 = PropagationWave(
            wave_number=1, nodes=["n1"],
            actions=[PropagationAction(node_id="n1", idempotency_key="k1")],
        )
        w2 = PropagationWave(
            wave_number=2, nodes=["n2"],
            actions=[PropagationAction(node_id="n2", idempotency_key="k2")],
        )
        plan = PropagationPlan(propagation_waves=[w1, w2])
        executor = PropagationExecutor(g, mode=ExecutionMode.DRY_RUN)
        result = executor.execute(plan)
        assert len(result.wave_results) == 2
        assert result.wave_results[0]["wave_number"] == 1
        assert result.wave_results[1]["wave_number"] == 2


# ── GraphBuilder ───────────────────────────────────────────────────────────

class TestGraphBuilder:
    def test_builder_from_real_state(self):
        from substrate.organism.propagation_graph_builder import PropagationGraphBuilder
        builder = PropagationGraphBuilder()
        graph = builder.build()
        assert len(graph.nodes) > 0

    def test_builder_includes_work_packets(self):
        from substrate.organism.propagation_graph_builder import PropagationGraphBuilder
        builder = PropagationGraphBuilder()
        graph = builder.build()
        wp_nodes = [n for n in graph.nodes.values() if n.node_type == PropagationNodeType.WORK_PACKET]
        assert len(wp_nodes) >= 5

    def test_builder_includes_workcells(self):
        from substrate.organism.propagation_graph_builder import PropagationGraphBuilder
        builder = PropagationGraphBuilder()
        graph = builder.build()
        wc_nodes = [n for n in graph.nodes.values() if n.node_type == PropagationNodeType.WORKCELL]
        assert len(wc_nodes) >= 5

    def test_builder_includes_ptd(self):
        from substrate.organism.propagation_graph_builder import PropagationGraphBuilder
        builder = PropagationGraphBuilder()
        graph = builder.build()
        ptd_nodes = [n for n in graph.nodes.values() if n.node_type == PropagationNodeType.PRODUCTION_TRUTH_DELTA]
        assert len(ptd_nodes) >= 1

    def test_builder_includes_api_routes(self):
        from substrate.organism.propagation_graph_builder import PropagationGraphBuilder
        builder = PropagationGraphBuilder()
        graph = builder.build()
        api_nodes = [n for n in graph.nodes.values() if n.node_type == PropagationNodeType.API_ROUTE]
        assert len(api_nodes) >= 5

    def test_builder_creates_edges(self):
        from substrate.organism.propagation_graph_builder import PropagationGraphBuilder
        builder = PropagationGraphBuilder()
        graph = builder.build()
        assert len(graph.edges) > 0

    def test_no_fake_nodes(self):
        from substrate.organism.propagation_graph_builder import PropagationGraphBuilder
        builder = PropagationGraphBuilder()
        graph = builder.build()
        for node in graph.nodes.values():
            assert node.evidence, f"Node {node.node_id} has no evidence"


# ── UniversalWorkQueue integration ─────────────────────────────────────────

class TestUniversalWorkQueueIntegration:
    def test_packets_visible_as_nodes(self):
        from substrate.organism.propagation_graph_builder import PropagationGraphBuilder
        builder = PropagationGraphBuilder()
        graph = builder.build()
        wp_nodes = [n for n in graph.nodes.values() if n.node_type == PropagationNodeType.WORK_PACKET]
        assert len(wp_nodes) >= 5
        for wp in wp_nodes:
            assert wp.source_type == "work_packet"
            assert wp.source_id != ""

    def test_impact_on_packet_change(self):
        from substrate.organism.propagation_graph_builder import PropagationGraphBuilder
        builder = PropagationGraphBuilder()
        graph = builder.build()
        wp_nodes = [n for n in graph.nodes.values() if n.node_type == PropagationNodeType.WORK_PACKET]
        if wp_nodes:
            event = ChangeEvent(
                source_node_id=wp_nodes[0].node_id,
                change_type=ChangeType.WORK_PACKET_UPDATED,
            )
            analyzer = ImpactAnalyzer(graph)
            analysis = analyzer.analyze(event)
            assert analysis.impact_radius >= 0


# ── Correspondence proof ───────────────────────────────────────────────────

class TestCorrespondenceProof:
    def test_same_pattern_multiple_scales(self):
        g = PropagationGraph()
        g.add_node(PropagationNode(node_id="rp-12", node_type=PropagationNodeType.ROADMAP_PHASE, title="Phase 12"))
        g.add_node(PropagationNode(node_id="wp-eos", node_type=PropagationNodeType.WORK_PACKET, title="EOS Dashboard"))
        g.add_node(PropagationNode(node_id="km-b2b", node_type=PropagationNodeType.KNOWLEDGE_MODEL, title="B2B AI"))
        g.add_node(PropagationNode(node_id="sb-q", node_type=PropagationNodeType.SELF_BUILD_ITEM, title="SB Queue"))
        g.add_node(PropagationNode(node_id="wc-eos", node_type=PropagationNodeType.WORKCELL, title="EOS WC"))
        g.add_node(PropagationNode(node_id="tmpl-1", node_type=PropagationNodeType.TEMPLATE, title="Template"))
        g.add_edge(PropagationEdge(from_node_id="rp-12", to_node_id="sb-q", edge_type=PropagationEdgeType.FEEDS))
        g.add_edge(PropagationEdge(from_node_id="wp-eos", to_node_id="wc-eos", edge_type=PropagationEdgeType.OWNS))
        g.add_edge(PropagationEdge(from_node_id="km-b2b", to_node_id="tmpl-1", edge_type=PropagationEdgeType.UPDATES))

        scales = [
            ("rp-12", ChangeType.ROADMAP_PHASE_UPDATED),
            ("wp-eos", ChangeType.WORK_PACKET_UPDATED),
            ("km-b2b", ChangeType.KNOWLEDGE_MODEL_UPDATED),
        ]
        for source_id, change_type in scales:
            event = ChangeEvent(source_node_id=source_id, change_type=change_type)
            analyzer = ImpactAnalyzer(g)
            analysis = analyzer.analyze(event)
            assert analysis.impact_radius >= 1
            planner = PropagationPlanner(g)
            plan = planner.plan(event, analysis)
            assert len(plan.propagation_waves) >= 1
            executor = PropagationExecutor(g, mode=ExecutionMode.DRY_RUN)
            result = executor.execute(plan)
            assert result.status in ("completed", "completed_with_gates")


# ── API route shapes ──────────────────────────────────────────────────────

class TestAPIRouteShapes:
    def test_routes_module_compiles(self):
        import py_compile
        py_compile.compile(
            "transports/api/cockpit_propagation_graph_routes.py",
            doraise=True,
        )

    def test_router_has_expected_routes(self):
        from transports.api.cockpit_propagation_graph_routes import _build_router
        async def fake_dep():
            pass
        router = _build_router(fake_dep)
        paths = [r.path for r in router.routes]
        assert "/organism/propagation-graph" in paths
        assert "/organism/propagation-graph/summary" in paths
        assert "/organism/propagation-graph/nodes" in paths
        assert "/organism/propagation-graph/edges" in paths
        assert "/organism/propagation-graph/change-events" in paths
        assert "/organism/propagation-graph/results" in paths
        assert "/organism/propagation-graph/correspondence-proof" in paths
        assert "/organism/propagation-graph/impact" in paths
        assert "/organism/propagation-graph/plan" in paths
        assert "/organism/propagation-graph/execute-dry-run" in paths

    def test_post_routes_require_auth(self):
        from transports.api.cockpit_propagation_graph_routes import _build_router
        async def fake_dep():
            pass
        router = _build_router(fake_dep)
        post_routes = [r for r in router.routes if hasattr(r, 'methods') and 'POST' in r.methods]
        for route in post_routes:
            assert len(route.dependencies) > 0, f"POST route {route.path} has no auth dependency"


# ── Cockpit data shapes ───────────────────────────────────────────────────

class TestCockpitDataShape:
    def test_graph_stats_shape(self):
        g = PropagationGraph()
        g.add_node(PropagationNode(node_id="n1"))
        stats = g.graph_stats()
        required_keys = {
            "total_nodes", "total_edges", "node_type_counts",
            "edge_type_counts", "orphaned_node_count", "cycle_count",
            "built_at", "version",
        }
        assert required_keys.issubset(set(stats.keys()))

    def test_impact_analysis_shape(self):
        g = PropagationGraph()
        g.add_node(PropagationNode(node_id="src"))
        event = ChangeEvent(source_node_id="src")
        analyzer = ImpactAnalyzer(g)
        analysis = analyzer.analyze(event)
        d = analysis.to_dict()
        required_keys = {
            "analysis_id", "change_event_id", "source_node_id",
            "affected_nodes", "direct_impact", "indirect_impact",
            "impact_depth", "impact_radius",
        }
        assert required_keys.issubset(set(d.keys()))

    def test_plan_shape(self):
        plan = PropagationPlan()
        d = plan.to_dict()
        required_keys = {
            "plan_id", "change_event_id", "root_node_id",
            "affected_nodes", "propagation_waves", "execution_mode",
        }
        assert required_keys.issubset(set(d.keys()))


# ── Safety invariants ─────────────────────────────────────────────────────

class TestSafetyInvariants:
    def test_no_production_mutation_in_dry_run(self):
        g = PropagationGraph()
        g.add_node(PropagationNode(node_id="src"))
        g.add_node(PropagationNode(node_id="target"))
        g.add_edge(PropagationEdge(
            from_node_id="src", to_node_id="target",
            propagation_mode=PropagationMode.REGENERATE,
        ))
        event = ChangeEvent(source_node_id="src")
        analyzer = ImpactAnalyzer(g)
        analysis = analyzer.analyze(event)
        planner = PropagationPlanner(g)
        plan = planner.plan(event, analysis)
        executor = PropagationExecutor(g, mode=ExecutionMode.DRY_RUN)
        result = executor.execute(plan)
        for wr in result.wave_results:
            for ar in wr.get("action_results", []):
                assert ar["status"] in (
                    "dry_run", "blocked", "approval_required",
                    "human_required", "skipped",
                ), f"Non-dry-run status: {ar['status']}"

    def test_no_fake_data_in_builder(self):
        from substrate.organism.propagation_graph_builder import PropagationGraphBuilder
        builder = PropagationGraphBuilder()
        graph = builder.build()
        for node in graph.nodes.values():
            assert node.evidence, f"Node {node.node_id} lacks evidence"
            for ev in node.evidence:
                assert "type" in ev, f"Evidence missing type: {ev}"

    def test_governed_mode_blocks_everything(self):
        g = PropagationGraph()
        g.add_node(PropagationNode(node_id="n1"))
        wave = PropagationWave(
            wave_number=1, nodes=["n1"],
            actions=[PropagationAction(node_id="n1", idempotency_key="k1")],
        )
        plan = PropagationPlan(propagation_waves=[wave])
        executor = PropagationExecutor(g, mode=ExecutionMode.GOVERNED)
        result = executor.execute(plan)
        assert len(result.blocked_actions) == 1
        assert len(result.completed_actions) == 0
