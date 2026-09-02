"""Work Graph — read-only query projection over existing work stores.

WorkGraph owns NOTHING. It persists NOTHING. It is a projection layer only.

Authority remains with the source systems:
  WorkPacketEngine  owns packets
  ExecutionCoordinator  owns plans
  ApprovalInterceptStore  owns approvals
  ProofRuntime  owns proofs

WorkGraph computes its view on every call from existing stores.
No caching. No local state beyond lazy subsystem references.

Gate 3 — Governed Work Runtime. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Enums
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class WorkNodeType(str, Enum):
    PACKET = "packet"
    PLAN = "plan"
    REQUEST = "request"


class BlockerType(str, Enum):
    DEPENDENCY = "dependency"
    APPROVAL = "approval"
    RESOURCE = "resource"
    FAILURE = "failure"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data classes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class WorkBlocker:
    blocker_type: BlockerType = BlockerType.DEPENDENCY
    description: str = ""
    blocking_node_id: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "blocker_type": self.blocker_type.value
            if isinstance(self.blocker_type, BlockerType) else self.blocker_type,
            "description": self.description,
            "blocking_node_id": self.blocking_node_id,
            "created_at": self.created_at,
        }


@dataclass
class WorkResult:
    outcome: str = ""
    proof_id: str = ""
    completed_at: float = 0.0
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "proof_id": self.proof_id,
            "completed_at": self.completed_at,
            "evidence": self.evidence,
        }


@dataclass
class WorkGraphNode:
    node_id: str = ""
    node_type: WorkNodeType = WorkNodeType.PACKET
    status: str = ""
    risk_class: str = "low"
    description: str = ""
    created_at: float = 0.0
    dependencies: list[str] = field(default_factory=list)
    blockers: list[WorkBlocker] = field(default_factory=list)
    result: WorkResult | None = None
    source_packet_id: str = ""
    source_plan_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value
            if isinstance(self.node_type, WorkNodeType) else self.node_type,
            "status": self.status,
            "risk_class": self.risk_class,
            "description": self.description,
            "created_at": self.created_at,
            "dependencies": self.dependencies,
            "blockers": [b.to_dict() for b in self.blockers],
            "result": self.result.to_dict() if self.result else None,
            "source_packet_id": self.source_packet_id,
            "source_plan_id": self.source_plan_id,
        }


@dataclass
class WorkGraphSnapshot:
    nodes: list[WorkGraphNode] = field(default_factory=list)
    total: int = 0
    active: int = 0
    blocked: int = 0
    completed: int = 0
    failed: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "active": self.active,
            "blocked": self.blocked,
            "completed": self.completed,
            "failed": self.failed,
            "timestamp": self.timestamp,
            "nodes": [n.to_dict() for n in self.nodes],
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Status classification helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_ACTIVE_PACKET_STATUSES = frozenset({
    "drafted", "classified", "planned", "ready_for_review",
    "approval_pending", "approved", "delegated", "executing",
    "paused", "reconverging", "validating",
})

_BLOCKED_PACKET_STATUSES = frozenset({"blocked"})

_TERMINAL_PACKET_STATUSES = frozenset({
    "completed", "rejected", "failed", "superseded", "archived",
})

_ACTIVE_PLAN_STATUSES = frozenset({
    "drafted", "approved", "queued", "dispatched", "executing",
})

_TERMINAL_PLAN_STATUSES = frozenset({
    "completed", "failed", "cancelled",
})

_ACTIVE_REQUEST_STATUSES = frozenset({
    "pending", "validating", "preparing", "ready",
    "executing", "monitoring", "completing",
})

_TERMINAL_REQUEST_STATUSES = frozenset({
    "completed", "failed", "cancelled", "cleaned_up",
})


def _is_active(status: str, node_type: WorkNodeType) -> bool:
    if node_type == WorkNodeType.PACKET:
        return status in _ACTIVE_PACKET_STATUSES
    if node_type == WorkNodeType.PLAN:
        return status in _ACTIVE_PLAN_STATUSES
    return status in _ACTIVE_REQUEST_STATUSES


def _is_blocked(status: str, node_type: WorkNodeType) -> bool:
    if node_type == WorkNodeType.PACKET:
        return status in _BLOCKED_PACKET_STATUSES
    return False


def _is_completed(status: str, node_type: WorkNodeType) -> bool:
    if node_type == WorkNodeType.PACKET:
        return status == "completed"
    if node_type == WorkNodeType.PLAN:
        return status == "completed"
    return status == "completed"


def _is_failed(status: str, node_type: WorkNodeType) -> bool:
    if node_type == WorkNodeType.PACKET:
        return status == "failed"
    if node_type == WorkNodeType.PLAN:
        return status == "failed"
    return status == "failed"


def _is_executable(node: WorkGraphNode) -> bool:
    """A node is executable if it's approved and has no blockers."""
    if node.node_type == WorkNodeType.PACKET:
        return node.status == "approved" and not node.blockers
    if node.node_type == WorkNodeType.PLAN:
        return node.status == "approved" and not node.blockers
    return node.status == "ready" and not node.blockers


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WorkGraph
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class WorkGraph:
    """Read-only query projection over existing work stores.

    Owns nothing. Persists nothing. Every method reads live from
    source stores — WorkPacketEngine, PlanStore, ExecutorRequestStore.
    """

    def __init__(
        self,
        packet_engine: Any | None = None,
        plan_store: Any | None = None,
        request_store: Any | None = None,
    ) -> None:
        self._packet_engine = packet_engine
        self._plan_store = plan_store
        self._request_store = request_store

    # ── Lazy subsystem access ────────────────────────────────────

    @property
    def packet_engine(self) -> Any | None:
        if self._packet_engine is None:
            try:
                from substrate.organism.work_packet_engine import WorkPacketEngine
                self._packet_engine = WorkPacketEngine()
            except Exception:
                logger.debug("WorkPacketEngine unavailable")
        return self._packet_engine

    @property
    def plan_store(self) -> Any | None:
        if self._plan_store is None:
            try:
                from substrate.organism.execution_coordinator import PlanStore
                self._plan_store = PlanStore()
            except Exception:
                logger.debug("PlanStore unavailable")
        return self._plan_store

    @property
    def request_store(self) -> Any | None:
        if self._request_store is None:
            try:
                from substrate.organism.executor_runtime import ExecutorRequestStore
                self._request_store = ExecutorRequestStore()
            except Exception:
                logger.debug("ExecutorRequestStore unavailable")
        return self._request_store

    # ── Node conversion ──────────────────────────────────────────

    def _packet_to_node(self, packet: Any) -> WorkGraphNode:
        status_val = packet.status
        if hasattr(status_val, "value"):
            status_val = status_val.value

        blockers: list[WorkBlocker] = []
        for b in getattr(packet, "blockers", []) or []:
            if isinstance(b, str):
                blockers.append(WorkBlocker(
                    blocker_type=BlockerType.DEPENDENCY,
                    description=b,
                ))
            elif isinstance(b, dict):
                blockers.append(WorkBlocker(
                    blocker_type=BlockerType(b.get("type", "dependency"))
                    if b.get("type") in [e.value for e in BlockerType]
                    else BlockerType.DEPENDENCY,
                    description=b.get("description", str(b)),
                ))

        result: WorkResult | None = None
        if status_val == "completed":
            result = WorkResult(
                outcome="success",
                completed_at=getattr(packet, "updated_at", 0.0),
                evidence={"outcome_summary": getattr(packet, "outcome_summary", "")},
            )
        elif status_val == "failed":
            result = WorkResult(
                outcome="failure",
                completed_at=getattr(packet, "updated_at", 0.0),
                evidence={"status_reason": getattr(packet, "status_reason", "")},
            )

        return WorkGraphNode(
            node_id=packet.packet_id,
            node_type=WorkNodeType.PACKET,
            status=status_val,
            risk_class=getattr(packet, "risk_class", "low"),
            description=getattr(packet, "title", "") or getattr(packet, "user_intent", ""),
            created_at=getattr(packet, "created_at", 0.0),
            dependencies=getattr(packet, "dependencies", []) or [],
            blockers=blockers,
            result=result,
        )

    def _plan_to_node(self, plan: Any) -> WorkGraphNode:
        blockers: list[WorkBlocker] = []
        if getattr(plan, "approval_state", "") == "pending":
            blockers.append(WorkBlocker(
                blocker_type=BlockerType.APPROVAL,
                description="Awaiting operator approval",
            ))

        result: WorkResult | None = None
        if plan.status == "completed":
            result = WorkResult(
                outcome="success",
                proof_id=getattr(plan, "proof_id", ""),
                completed_at=getattr(plan, "completed_at", 0.0) or 0.0,
            )
        elif plan.status == "failed":
            result = WorkResult(
                outcome="failure",
                completed_at=getattr(plan, "failed_at", 0.0) or 0.0,
                evidence={"failure_reason": getattr(plan, "failure_reason", "")},
            )

        return WorkGraphNode(
            node_id=plan.execution_plan_id,
            node_type=WorkNodeType.PLAN,
            status=plan.status,
            risk_class=getattr(plan, "risk_class", "low"),
            description=getattr(plan, "description", ""),
            created_at=getattr(plan, "created_at", 0.0),
            blockers=blockers,
            result=result,
            source_packet_id=getattr(plan, "source_workpacket_id", ""),
        )

    def _request_to_node(self, request: Any) -> WorkGraphNode:
        result: WorkResult | None = None
        if request.status in ("completed", "cleaned_up"):
            result = WorkResult(outcome="success", completed_at=request.created_at)
        elif request.status == "failed":
            result = WorkResult(outcome="failure", completed_at=request.created_at)

        return WorkGraphNode(
            node_id=request.request_id,
            node_type=WorkNodeType.REQUEST,
            status=request.status,
            risk_class=getattr(request, "risk_class", "low"),
            description=getattr(request, "description", ""),
            created_at=getattr(request, "created_at", 0.0),
            result=result,
            source_plan_id=getattr(request, "execution_plan_id", ""),
        )

    # ── Query methods ────────────────────────────────────────────

    def _collect_all(self) -> list[WorkGraphNode]:
        """Read live from all source stores. No caching."""
        nodes: list[WorkGraphNode] = []

        if self.packet_engine is not None:
            try:
                from substrate.organism.work_packet import load_packets
                for p in load_packets():
                    nodes.append(self._packet_to_node(p))
            except Exception:
                logger.debug("Failed to load packets")

        if self.plan_store is not None:
            try:
                for p in self.plan_store.all_plans():
                    nodes.append(self._plan_to_node(p))
            except Exception:
                logger.debug("Failed to load plans")

        if self.request_store is not None:
            try:
                for r in self.request_store.all_requests():
                    nodes.append(self._request_to_node(r))
            except Exception:
                logger.debug("Failed to load requests")

        return nodes

    def all_work(self) -> list[WorkGraphNode]:
        return self._collect_all()

    def active_work(self) -> list[WorkGraphNode]:
        return [n for n in self._collect_all() if _is_active(n.status, n.node_type)]

    def blocked_work(self) -> list[WorkGraphNode]:
        return [
            n for n in self._collect_all()
            if _is_blocked(n.status, n.node_type) or n.blockers
        ]

    def executable_work(self) -> list[WorkGraphNode]:
        return [n for n in self._collect_all() if _is_executable(n)]

    def completed_work(self) -> list[WorkGraphNode]:
        return [n for n in self._collect_all() if _is_completed(n.status, n.node_type)]

    def failed_work(self) -> list[WorkGraphNode]:
        return [n for n in self._collect_all() if _is_failed(n.status, n.node_type)]

    def operation_snapshot(self) -> dict[str, WorkGraphNode]:
        """One immutable point-in-time view for the duration of ONE operation.

        This is NOT a cache. Nothing is retained on the instance, nothing is
        shared between calls, and nothing survives the caller's stack frame —
        the caller owns the returned mapping and drops it when its operation
        ends. WorkGraph itself keeps no local state, exactly as its class
        contract requires.

        It exists because a batch operation that classifies N nodes must not
        re-read every source store N times. Reading once per OPERATION is the
        difference between O(N) and O(N^2) full-store parses; at ~1,100 packets
        over a 2.8 MB store the quadratic form does not finish, which is what
        blocked whole-tree validation.

        Operation-scoped consistency is also the correct SEMANTICS, not merely
        the fast path: ``assess_all()`` already freezes its active node list
        once per pass, so letting each node's dependency lookup observe a
        different store generation would produce a mixed-time result in which
        node A is judged against one snapshot and node B against another.
        Admission and governance decisions must be internally coherent.

        Writes committed during a pass are deliberately NOT folded into that
        pass; they become visible to the next public operation, which reads
        fresh state again.
        """
        return {n.node_id: n for n in self._collect_all()}

    def dependencies_of(
        self,
        node_id: str,
        snapshot: dict[str, WorkGraphNode] | None = None,
    ) -> list[WorkGraphNode]:
        """Dependencies of one node.

        Called WITHOUT ``snapshot`` (the default for every independent caller)
        this reads fresh live state exactly as before — the uncached contract is
        unchanged. Called WITH an explicit operation snapshot, it resolves
        against that immutable view so one batch operation performs one
        collection instead of one per node.
        """
        all_nodes = snapshot if snapshot is not None else self.operation_snapshot()
        target = all_nodes.get(node_id)
        if not target:
            return []
        return [all_nodes[d] for d in target.dependencies if d in all_nodes]

    def dependents_of(self, node_id: str) -> list[WorkGraphNode]:
        return [
            n for n in self._collect_all()
            if node_id in n.dependencies
        ]

    def blockers_for(self, node_id: str) -> list[WorkBlocker]:
        for n in self._collect_all():
            if n.node_id == node_id:
                return n.blockers
        return []

    def work_by_status(self, status: str) -> list[WorkGraphNode]:
        return [n for n in self._collect_all() if n.status == status]

    def node(self, node_id: str) -> WorkGraphNode | None:
        for n in self._collect_all():
            if n.node_id == node_id:
                return n
        return None

    def snapshot(self) -> WorkGraphSnapshot:
        nodes = self._collect_all()
        active = sum(1 for n in nodes if _is_active(n.status, n.node_type))
        blocked = sum(
            1 for n in nodes
            if _is_blocked(n.status, n.node_type) or n.blockers
        )
        completed = sum(1 for n in nodes if _is_completed(n.status, n.node_type))
        failed = sum(1 for n in nodes if _is_failed(n.status, n.node_type))

        return WorkGraphSnapshot(
            nodes=nodes,
            total=len(nodes),
            active=active,
            blocked=blocked,
            completed=completed,
            failed=failed,
        )
