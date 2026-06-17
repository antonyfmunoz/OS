"""Execution Graph — evidence-grade lineage validation over existing execution infrastructure.

Answers: "Pick any action. Trace Intent → Decision → Execution → Proof → Outcome. No gaps."

This gate is primarily VALIDATION over existing infrastructure, not greenfield.
It composes TraceRecorder, FeedbackCapture, ProofRuntime, IntentRuntime,
IntentReceiptStore, OutcomeLearningLoop, and WorkPacketEngine into a unified
lineage graph that proves execution chains are complete and evidence-grade.

Gate 8 — Execution Graph. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_GRAPH_DIR = os.path.join(_REPO_ROOT, "data", "umh", "execution_graph")
_GRAPH_PATH = os.path.join(_GRAPH_DIR, "nodes.jsonl")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ExecutionNodeType(str, Enum):
    INTENT = "intent"
    DECISION = "decision"
    WORK_PACKET = "work_packet"
    EXECUTION = "execution"
    PROOF = "proof"
    OUTCOME = "outcome"


class LineageGap(str, Enum):
    MISSING_INTENT = "missing_intent"
    MISSING_DECISION = "missing_decision"
    MISSING_WORK_PACKET = "missing_work_packet"
    MISSING_EXECUTION = "missing_execution"
    MISSING_PROOF = "missing_proof"
    MISSING_OUTCOME = "missing_outcome"
    ORPHAN_NODE = "orphan_node"


@dataclass
class ExecutionGraphNode:
    node_id: str = field(default_factory=lambda: f"egn-{uuid4().hex[:8]}")
    node_type: ExecutionNodeType = ExecutionNodeType.EXECUTION
    action: str = ""
    intent_id: str = ""
    decision_id: str = ""
    work_packet_id: str = ""
    execution_id: str = ""
    proof_id: str = ""
    outcome_id: str = ""
    parent_node_id: str = ""
    children: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["node_type"] = self.node_type.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ExecutionGraphNode:
        d = dict(d)
        try:
            d["node_type"] = ExecutionNodeType(d.get("node_type", "execution"))
        except ValueError:
            d["node_type"] = ExecutionNodeType.EXECUTION
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Lineage validation — deterministic
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


_REQUIRED_CHAIN = [
    ("intent_id", LineageGap.MISSING_INTENT),
    ("decision_id", LineageGap.MISSING_DECISION),
    ("work_packet_id", LineageGap.MISSING_WORK_PACKET),
    ("execution_id", LineageGap.MISSING_EXECUTION),
    ("proof_id", LineageGap.MISSING_PROOF),
    ("outcome_id", LineageGap.MISSING_OUTCOME),
]


def validate_lineage(node: ExecutionGraphNode) -> dict[str, Any]:
    """Deterministic completeness check for a single execution node.

    Returns gaps in the Intent→Decision→WorkPacket→Execution→Proof→Outcome chain.
    """
    gaps: list[str] = []
    present: list[str] = []
    for field_name, gap_type in _REQUIRED_CHAIN:
        val = getattr(node, field_name, "")
        if val:
            present.append(field_name)
        else:
            gaps.append(gap_type.value)

    completeness = len(present) / len(_REQUIRED_CHAIN) if _REQUIRED_CHAIN else 0.0
    return {
        "node_id": node.node_id,
        "complete": len(gaps) == 0,
        "completeness": round(completeness, 3),
        "present": present,
        "gaps": gaps,
    }


def validate_chain(nodes: list[ExecutionGraphNode]) -> dict[str, Any]:
    """Validate a chain of nodes for structural integrity."""
    if not nodes:
        return {"chain_length": 0, "complete": False, "gaps": ["empty_chain"]}

    node_results = [validate_lineage(n) for n in nodes]
    all_complete = all(r["complete"] for r in node_results)
    avg_completeness = sum(r["completeness"] for r in node_results) / len(node_results)
    total_gaps = [g for r in node_results for g in r["gaps"]]

    orphans = [
        n.node_id for n in nodes if not n.parent_node_id and n.node_type != ExecutionNodeType.INTENT
    ]
    if orphans:
        total_gaps.extend([LineageGap.ORPHAN_NODE.value] * len(orphans))

    return {
        "chain_length": len(nodes),
        "complete": all_complete and not orphans,
        "average_completeness": round(avg_completeness, 3),
        "gaps": total_gaps,
        "orphan_nodes": orphans,
        "node_results": node_results,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Replay — deterministic reconstruction
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def replay_node(node: ExecutionGraphNode) -> dict[str, Any]:
    """Reconstruct the full execution path for a node."""
    chain: list[dict[str, str]] = []
    if node.intent_id:
        chain.append({"type": "intent", "id": node.intent_id})
    if node.decision_id:
        chain.append({"type": "decision", "id": node.decision_id})
    if node.work_packet_id:
        chain.append({"type": "work_packet", "id": node.work_packet_id})
    if node.execution_id:
        chain.append({"type": "execution", "id": node.execution_id})
    if node.proof_id:
        chain.append({"type": "proof", "id": node.proof_id})
    if node.outcome_id:
        chain.append({"type": "outcome", "id": node.outcome_id})
    return {
        "node_id": node.node_id,
        "action": node.action,
        "chain": chain,
        "chain_length": len(chain),
        "full_chain": len(chain) == 6,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Runtime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ExecutionGraph:
    """Graph layer over existing execution infrastructure.

    Composes (does not replace):
    - IntentReceipt → origin nodes
    - WorkPacketEngine → work packet lifecycle
    - TraceRecorder → execution trace
    - ProofRuntime → proof packages
    - OutcomeLearning → terminal outcomes
    """

    def __init__(self, store_path: str = _GRAPH_PATH) -> None:
        self._path = store_path
        self._lock = threading.Lock()
        self._nodes: dict[str, ExecutionGraphNode] = {}
        self._by_intent: dict[str, list[str]] = {}
        self._by_execution: dict[str, str] = {}
        self._load()

    # ── Persistence ────────────────────────────────────────────────

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                        node = ExecutionGraphNode.from_dict(d)
                        self._nodes[node.node_id] = node
                        self._index_node(node)
                    except (json.JSONDecodeError, TypeError, KeyError) as e:
                        logger.debug("Skip malformed JSONL line: %s", e)
        except OSError as e:
            logger.debug("Cannot read %s: %s", self._path, e)

    def _index_node(self, node: ExecutionGraphNode) -> None:
        if node.intent_id:
            self._by_intent.setdefault(node.intent_id, []).append(node.node_id)
        if node.execution_id:
            self._by_execution[node.execution_id] = node.node_id

    def _append(self, node: ExecutionGraphNode) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "a") as f:
            f.write(json.dumps(node.to_dict(), default=str) + "\n")

    def _rewrite(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w") as f:
            for node in self._nodes.values():
                f.write(json.dumps(node.to_dict(), default=str) + "\n")

    # ── Registration ───────────────────────────────────────────────

    def record(
        self,
        action: str,
        node_type: ExecutionNodeType = ExecutionNodeType.EXECUTION,
        intent_id: str = "",
        decision_id: str = "",
        work_packet_id: str = "",
        execution_id: str = "",
        proof_id: str = "",
        outcome_id: str = "",
        parent_node_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionGraphNode:
        node = ExecutionGraphNode(
            node_type=node_type,
            action=action,
            intent_id=intent_id,
            decision_id=decision_id,
            work_packet_id=work_packet_id,
            execution_id=execution_id,
            proof_id=proof_id,
            outcome_id=outcome_id,
            parent_node_id=parent_node_id,
            metadata=metadata or {},
        )
        with self._lock:
            self._nodes[node.node_id] = node
            self._index_node(node)
            if parent_node_id and parent_node_id in self._nodes:
                self._nodes[parent_node_id].children.append(node.node_id)
                self._rewrite()
            else:
                self._append(node)
        logger.info("Recorded execution node: %s (%s)", node.action, node.node_id)
        return node

    def get(self, node_id: str) -> ExecutionGraphNode | None:
        return self._nodes.get(node_id)

    def list_nodes(
        self,
        node_type: ExecutionNodeType | None = None,
        intent_id: str | None = None,
        limit: int = 100,
    ) -> list[ExecutionGraphNode]:
        result = list(self._nodes.values())
        if node_type is not None:
            result = [n for n in result if n.node_type == node_type]
        if intent_id is not None:
            nids = set(self._by_intent.get(intent_id, []))
            result = [n for n in result if n.node_id in nids]
        result.sort(key=lambda n: n.timestamp, reverse=True)
        return result[:limit]

    # ── Lineage traversal ─────────────────────────────────────────

    def trace_full(self, node_id: str) -> dict[str, Any]:
        """Full lineage for a single node: intent→decision→execution→proof→outcome."""
        node = self._nodes.get(node_id)
        if node is None:
            return {"error": f"node {node_id} not found"}
        validation = validate_lineage(node)
        replay = replay_node(node)
        return {
            "node": node.to_dict(),
            "validation": validation,
            "replay": replay,
        }

    def trace_from_intent(self, intent_id: str) -> dict[str, Any]:
        """All execution nodes traced from a single intent."""
        nids = self._by_intent.get(intent_id, [])
        nodes = [self._nodes[nid] for nid in nids if nid in self._nodes]
        if not nodes:
            return {"error": f"no nodes for intent {intent_id}", "nodes": []}
        chain_result = validate_chain(nodes)
        return {
            "intent_id": intent_id,
            "nodes": [n.to_dict() for n in nodes],
            **chain_result,
        }

    def trace_from_execution(self, execution_id: str) -> dict[str, Any]:
        """Find the graph node for a given execution ID."""
        nid = self._by_execution.get(execution_id)
        if nid is None:
            return {"error": f"no node for execution {execution_id}"}
        return self.trace_full(nid)

    # ── Completeness validation ────────────────────────────────────

    def validate_completeness(self, node_id: str) -> dict[str, Any]:
        """Check a single node for lineage gaps."""
        node = self._nodes.get(node_id)
        if node is None:
            return {"error": f"node {node_id} not found"}
        return validate_lineage(node)

    def audit_completeness(self, limit: int = 100) -> dict[str, Any]:
        """Audit the most recent nodes for lineage completeness."""
        nodes = sorted(self._nodes.values(), key=lambda n: n.timestamp, reverse=True)[:limit]
        results = [validate_lineage(n) for n in nodes]
        complete_count = sum(1 for r in results if r["complete"])
        gap_distribution: dict[str, int] = {}
        for r in results:
            for g in r["gaps"]:
                gap_distribution[g] = gap_distribution.get(g, 0) + 1

        return {
            "audited": len(results),
            "complete": complete_count,
            "incomplete": len(results) - complete_count,
            "completeness_rate": round(complete_count / len(results), 3) if results else 0.0,
            "gap_distribution": gap_distribution,
        }

    # ── Replay ─────────────────────────────────────────────────────

    def replay(self, node_id: str) -> dict[str, Any]:
        """Replay the execution chain for a node."""
        node = self._nodes.get(node_id)
        if node is None:
            return {"error": f"node {node_id} not found"}
        return replay_node(node)

    # ── Receipt composition ────────────────────────────────────────

    def record_from_receipt(self, receipt_dict: dict[str, Any]) -> ExecutionGraphNode | None:
        """Create a graph node from an IntentReceipt dict.

        Composes with IntentReceiptStore — receipts already contain
        the full chain: intent_id, work_packet_id, governance_decision_id,
        execution_bundle_id. This method maps them into the graph.
        """
        intent_id = receipt_dict.get("intent_id", "")
        if not intent_id:
            return None
        return self.record(
            action=receipt_dict.get("raw_input", "")[:200],
            node_type=ExecutionNodeType.EXECUTION,
            intent_id=intent_id,
            decision_id=receipt_dict.get("governance_decision_id", ""),
            work_packet_id=receipt_dict.get("work_packet_id", ""),
            execution_id=receipt_dict.get("execution_bundle_id", ""),
            proof_id=receipt_dict.get("reality_update_id", ""),
            outcome_id=receipt_dict.get("final_status", ""),
            metadata={
                "route_type": receipt_dict.get("route_type", ""),
                "confidence": receipt_dict.get("confidence", 0.0),
            },
        )

    # ── Update ─────────────────────────────────────────────────────

    def attach_proof(self, node_id: str, proof_id: str) -> bool:
        node = self._nodes.get(node_id)
        if node is None:
            return False
        with self._lock:
            node.proof_id = proof_id
            self._rewrite()
        return True

    def attach_outcome(self, node_id: str, outcome_id: str) -> bool:
        node = self._nodes.get(node_id)
        if node is None:
            return False
        with self._lock:
            node.outcome_id = outcome_id
            self._rewrite()
        return True

    # ── Summary ────────────────────────────────────────────────────

    def summary(self) -> dict[str, Any]:
        by_type: dict[str, int] = {}
        for node in self._nodes.values():
            t = node.node_type.value
            by_type[t] = by_type.get(t, 0) + 1

        audit = self.audit_completeness(limit=min(len(self._nodes), 200))
        return {
            "total_nodes": len(self._nodes),
            "by_type": by_type,
            "completeness_rate": audit.get("completeness_rate", 0.0),
            "gap_distribution": audit.get("gap_distribution", {}),
        }
