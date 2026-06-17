"""Tests for Gate 8 — Execution Graph (lineage validation).

Verifies:
- Types: ExecutionNodeType, LineageGap, ExecutionGraphNode
- Lineage validation: complete chains, gap detection
- Chain validation: multi-node chains, orphan detection
- Replay: chain reconstruction
- ExecutionGraph runtime: record, get, list, trace, audit
- Receipt composition: IntentReceipt → graph node
- Persistence: JSONL roundtrip
- Type coherence: canonical_types registration
- Routes: cockpit route mounting
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


class TestTypes(unittest.TestCase):
    def test_execution_node_type_enum(self) -> None:
        from substrate.organism.execution_graph import ExecutionNodeType

        assert ExecutionNodeType.INTENT.value == "intent"
        assert ExecutionNodeType.DECISION.value == "decision"
        assert ExecutionNodeType.WORK_PACKET.value == "work_packet"
        assert ExecutionNodeType.EXECUTION.value == "execution"
        assert ExecutionNodeType.PROOF.value == "proof"
        assert ExecutionNodeType.OUTCOME.value == "outcome"
        assert len(ExecutionNodeType) == 6

    def test_lineage_gap_enum(self) -> None:
        from substrate.organism.execution_graph import LineageGap

        assert LineageGap.MISSING_INTENT.value == "missing_intent"
        assert LineageGap.ORPHAN_NODE.value == "orphan_node"
        assert len(LineageGap) == 7

    def test_node_creation(self) -> None:
        from substrate.organism.execution_graph import (
            ExecutionGraphNode,
            ExecutionNodeType,
        )

        node = ExecutionGraphNode(
            action="deploy service",
            node_type=ExecutionNodeType.EXECUTION,
            intent_id="int-1",
            execution_id="exec-1",
        )
        assert node.action == "deploy service"
        assert node.intent_id == "int-1"
        assert node.node_id.startswith("egn-")

    def test_node_to_dict(self) -> None:
        from substrate.organism.execution_graph import ExecutionGraphNode

        node = ExecutionGraphNode(action="test")
        d = node.to_dict()
        assert d["action"] == "test"
        assert d["node_type"] == "execution"
        assert isinstance(d["children"], list)

    def test_node_from_dict(self) -> None:
        from substrate.organism.execution_graph import (
            ExecutionGraphNode,
            ExecutionNodeType,
        )

        d = {
            "node_id": "egn-abc",
            "node_type": "intent",
            "action": "express goal",
            "intent_id": "int-1",
        }
        node = ExecutionGraphNode.from_dict(d)
        assert node.node_id == "egn-abc"
        assert node.node_type == ExecutionNodeType.INTENT
        assert node.action == "express goal"

    def test_invalid_node_type_defaults(self) -> None:
        from substrate.organism.execution_graph import (
            ExecutionGraphNode,
            ExecutionNodeType,
        )

        node = ExecutionGraphNode.from_dict({"node_type": "invalid"})
        assert node.node_type == ExecutionNodeType.EXECUTION


class TestLineageValidation(unittest.TestCase):
    def test_complete_node_has_no_gaps(self) -> None:
        from substrate.organism.execution_graph import (
            ExecutionGraphNode,
            validate_lineage,
        )

        node = ExecutionGraphNode(
            action="full chain",
            intent_id="i1",
            decision_id="d1",
            work_packet_id="wp1",
            execution_id="e1",
            proof_id="p1",
            outcome_id="o1",
        )
        result = validate_lineage(node)
        assert result["complete"] is True
        assert result["completeness"] == 1.0
        assert result["gaps"] == []

    def test_missing_intent_detected(self) -> None:
        from substrate.organism.execution_graph import (
            ExecutionGraphNode,
            validate_lineage,
        )

        node = ExecutionGraphNode(
            action="no intent",
            decision_id="d1",
            execution_id="e1",
        )
        result = validate_lineage(node)
        assert result["complete"] is False
        assert "missing_intent" in result["gaps"]

    def test_missing_proof_detected(self) -> None:
        from substrate.organism.execution_graph import (
            ExecutionGraphNode,
            validate_lineage,
        )

        node = ExecutionGraphNode(
            action="no proof",
            intent_id="i1",
            decision_id="d1",
            work_packet_id="wp1",
            execution_id="e1",
            outcome_id="o1",
        )
        result = validate_lineage(node)
        assert result["complete"] is False
        assert "missing_proof" in result["gaps"]
        assert result["completeness"] == round(5 / 6, 3)

    def test_empty_node_all_gaps(self) -> None:
        from substrate.organism.execution_graph import (
            ExecutionGraphNode,
            validate_lineage,
        )

        node = ExecutionGraphNode(action="empty")
        result = validate_lineage(node)
        assert result["complete"] is False
        assert len(result["gaps"]) == 6
        assert result["completeness"] == 0.0


class TestChainValidation(unittest.TestCase):
    def test_complete_chain(self) -> None:
        from substrate.organism.execution_graph import (
            ExecutionGraphNode,
            ExecutionNodeType,
            validate_chain,
        )

        root = ExecutionGraphNode(
            action="root",
            node_type=ExecutionNodeType.INTENT,
            intent_id="i1",
            decision_id="d1",
            work_packet_id="wp1",
            execution_id="e1",
            proof_id="p1",
            outcome_id="o1",
        )
        child = ExecutionGraphNode(
            action="child",
            node_type=ExecutionNodeType.EXECUTION,
            intent_id="i1",
            decision_id="d1",
            work_packet_id="wp1",
            execution_id="e2",
            proof_id="p2",
            outcome_id="o2",
            parent_node_id=root.node_id,
        )
        result = validate_chain([root, child])
        assert result["complete"] is True
        assert result["chain_length"] == 2

    def test_orphan_detection(self) -> None:
        from substrate.organism.execution_graph import (
            ExecutionGraphNode,
            ExecutionNodeType,
            validate_chain,
        )

        orphan = ExecutionGraphNode(
            action="orphan execution",
            node_type=ExecutionNodeType.EXECUTION,
            intent_id="i1",
            decision_id="d1",
            work_packet_id="wp1",
            execution_id="e1",
            proof_id="p1",
            outcome_id="o1",
        )
        result = validate_chain([orphan])
        assert result["complete"] is False
        assert orphan.node_id in result["orphan_nodes"]

    def test_empty_chain(self) -> None:
        from substrate.organism.execution_graph import validate_chain

        result = validate_chain([])
        assert result["complete"] is False
        assert "empty_chain" in result["gaps"]

    def test_intent_root_not_orphan(self) -> None:
        from substrate.organism.execution_graph import (
            ExecutionGraphNode,
            ExecutionNodeType,
            validate_chain,
        )

        root = ExecutionGraphNode(
            action="intent root",
            node_type=ExecutionNodeType.INTENT,
            intent_id="i1",
            decision_id="d1",
            work_packet_id="wp1",
            execution_id="e1",
            proof_id="p1",
            outcome_id="o1",
        )
        result = validate_chain([root])
        assert result["complete"] is True
        assert result["orphan_nodes"] == []


class TestReplay(unittest.TestCase):
    def test_full_chain_replay(self) -> None:
        from substrate.organism.execution_graph import (
            ExecutionGraphNode,
            replay_node,
        )

        node = ExecutionGraphNode(
            action="deploy",
            intent_id="i1",
            decision_id="d1",
            work_packet_id="wp1",
            execution_id="e1",
            proof_id="p1",
            outcome_id="o1",
        )
        result = replay_node(node)
        assert result["full_chain"] is True
        assert result["chain_length"] == 6
        assert result["chain"][0]["type"] == "intent"
        assert result["chain"][-1]["type"] == "outcome"

    def test_partial_chain_replay(self) -> None:
        from substrate.organism.execution_graph import (
            ExecutionGraphNode,
            replay_node,
        )

        node = ExecutionGraphNode(
            action="partial",
            intent_id="i1",
            execution_id="e1",
        )
        result = replay_node(node)
        assert result["full_chain"] is False
        assert result["chain_length"] == 2


class TestExecutionGraph(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        self._path = os.path.join(self._tmp, "nodes.jsonl")

    def _make_graph(self) -> "ExecutionGraph":
        from substrate.organism.execution_graph import ExecutionGraph

        return ExecutionGraph(store_path=self._path)

    def test_record_and_get(self) -> None:
        g = self._make_graph()
        node = g.record(action="test action", intent_id="i1")
        assert node.action == "test action"
        fetched = g.get(node.node_id)
        assert fetched is not None
        assert fetched.action == "test action"

    def test_get_nonexistent(self) -> None:
        g = self._make_graph()
        assert g.get("nonexistent") is None

    def test_list_all(self) -> None:
        g = self._make_graph()
        g.record(action="a1")
        g.record(action="a2")
        nodes = g.list_nodes()
        assert len(nodes) == 2

    def test_list_by_type(self) -> None:
        from substrate.organism.execution_graph import ExecutionNodeType

        g = self._make_graph()
        g.record(action="intent", node_type=ExecutionNodeType.INTENT)
        g.record(action="exec", node_type=ExecutionNodeType.EXECUTION)
        intents = g.list_nodes(node_type=ExecutionNodeType.INTENT)
        assert len(intents) == 1
        assert intents[0].action == "intent"

    def test_list_by_intent(self) -> None:
        g = self._make_graph()
        g.record(action="a1", intent_id="i1")
        g.record(action="a2", intent_id="i2")
        g.record(action="a3", intent_id="i1")
        nodes = g.list_nodes(intent_id="i1")
        assert len(nodes) == 2

    def test_trace_full(self) -> None:
        g = self._make_graph()
        node = g.record(
            action="full trace",
            intent_id="i1",
            decision_id="d1",
            work_packet_id="wp1",
            execution_id="e1",
            proof_id="p1",
            outcome_id="o1",
        )
        result = g.trace_full(node.node_id)
        assert result["validation"]["complete"] is True
        assert result["replay"]["full_chain"] is True

    def test_trace_full_nonexistent(self) -> None:
        g = self._make_graph()
        result = g.trace_full("nope")
        assert "error" in result

    def test_trace_from_intent(self) -> None:
        g = self._make_graph()
        g.record(action="a1", intent_id="i1", execution_id="e1")
        g.record(action="a2", intent_id="i1", execution_id="e2")
        result = g.trace_from_intent("i1")
        assert result["chain_length"] == 2

    def test_trace_from_execution(self) -> None:
        g = self._make_graph()
        node = g.record(action="exec", execution_id="exec-123")
        result = g.trace_from_execution("exec-123")
        assert result["node"]["node_id"] == node.node_id

    def test_trace_from_execution_missing(self) -> None:
        g = self._make_graph()
        result = g.trace_from_execution("nope")
        assert "error" in result

    def test_validate_completeness(self) -> None:
        g = self._make_graph()
        node = g.record(action="partial", intent_id="i1")
        result = g.validate_completeness(node.node_id)
        assert result["complete"] is False
        assert "missing_decision" in result["gaps"]

    def test_audit_completeness(self) -> None:
        g = self._make_graph()
        g.record(
            action="complete",
            intent_id="i1",
            decision_id="d1",
            work_packet_id="wp1",
            execution_id="e1",
            proof_id="p1",
            outcome_id="o1",
        )
        g.record(action="incomplete", intent_id="i2")
        audit = g.audit_completeness()
        assert audit["audited"] == 2
        assert audit["complete"] == 1
        assert audit["incomplete"] == 1
        assert 0.0 < audit["completeness_rate"] < 1.0

    def test_replay(self) -> None:
        g = self._make_graph()
        node = g.record(action="replay test", intent_id="i1", execution_id="e1")
        result = g.replay(node.node_id)
        assert result["chain_length"] == 2

    def test_record_from_receipt(self) -> None:
        g = self._make_graph()
        receipt = {
            "intent_id": "i1",
            "raw_input": "deploy the service",
            "route_type": "execution",
            "confidence": 0.9,
            "governance_decision_id": "d1",
            "work_packet_id": "wp1",
            "execution_bundle_id": "eb1",
            "reality_update_id": "ru1",
            "final_status": "completed",
        }
        node = g.record_from_receipt(receipt)
        assert node is not None
        assert node.intent_id == "i1"
        assert node.decision_id == "d1"
        assert node.work_packet_id == "wp1"
        assert node.execution_id == "eb1"
        assert node.proof_id == "ru1"
        assert node.outcome_id == "completed"

    def test_record_from_receipt_no_intent(self) -> None:
        g = self._make_graph()
        assert g.record_from_receipt({}) is None

    def test_attach_proof(self) -> None:
        g = self._make_graph()
        node = g.record(action="attach test")
        assert g.attach_proof(node.node_id, "proof-123")
        assert g.get(node.node_id).proof_id == "proof-123"

    def test_attach_outcome(self) -> None:
        g = self._make_graph()
        node = g.record(action="attach test")
        assert g.attach_outcome(node.node_id, "outcome-456")
        assert g.get(node.node_id).outcome_id == "outcome-456"

    def test_attach_proof_nonexistent(self) -> None:
        g = self._make_graph()
        assert g.attach_proof("nope", "p1") is False

    def test_parent_child_linking(self) -> None:
        g = self._make_graph()
        parent = g.record(action="parent", intent_id="i1")
        child = g.record(
            action="child",
            intent_id="i1",
            parent_node_id=parent.node_id,
        )
        updated_parent = g.get(parent.node_id)
        assert child.node_id in updated_parent.children

    def test_summary(self) -> None:
        from substrate.organism.execution_graph import ExecutionNodeType

        g = self._make_graph()
        g.record(action="a1", node_type=ExecutionNodeType.INTENT)
        g.record(action="a2", node_type=ExecutionNodeType.EXECUTION)
        s = g.summary()
        assert s["total_nodes"] == 2
        assert "intent" in s["by_type"]
        assert "execution" in s["by_type"]


class TestPersistence(unittest.TestCase):
    def test_jsonl_roundtrip(self) -> None:
        from substrate.organism.execution_graph import ExecutionGraph

        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "nodes.jsonl")
        g1 = ExecutionGraph(store_path=path)
        g1.record(action="persist test", intent_id="i1")
        g1.record(action="persist test 2", intent_id="i2")

        g2 = ExecutionGraph(store_path=path)
        assert len(g2.list_nodes()) == 2
        nodes = g2.list_nodes(intent_id="i1")
        assert len(nodes) == 1

    def test_malformed_jsonl_skipped(self) -> None:
        from substrate.organism.execution_graph import ExecutionGraph

        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "nodes.jsonl")
        with open(path, "w") as f:
            f.write("not valid json\n")
            f.write(json.dumps({"node_id": "egn-ok", "action": "valid"}) + "\n")

        g = ExecutionGraph(store_path=path)
        assert len(g.list_nodes()) == 1


class TestTypeCoherence(unittest.TestCase):
    def test_canonical_types_registered(self) -> None:
        from substrate.canonical_types import CANONICAL_TYPES

        for name in [
            "ExecutionNodeType",
            "LineageGap",
            "ExecutionGraphNode",
            "ExecutionGraph",
        ]:
            assert name in CANONICAL_TYPES, f"{name} not in canonical_types"
            assert "substrate.organism.execution_graph" in CANONICAL_TYPES[name]


class TestRoutes(unittest.TestCase):
    def test_routes_importable(self) -> None:
        from transports.api.cockpit_execution_graph_routes import (
            execution_graph_router,
        )

        assert execution_graph_router is not None

    def test_cockpit_mounts_execution_graph_routes(self) -> None:
        import transports.api.cockpit as c

        route_paths = [r.path for r in c.router.routes]
        assert any("/execution-graph/nodes" in p for p in route_paths)
        assert any("/execution-graph/summary" in p for p in route_paths)
        assert any("/execution-graph/audit" in p for p in route_paths)


if __name__ == "__main__":
    unittest.main()
