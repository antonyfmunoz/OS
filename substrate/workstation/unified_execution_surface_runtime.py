"""Unified Execution Surface Runtime — single view across all execution subsystems.

Answers: "What is happening right now?" — merges execution + agents + compute +
work + approvals + proof into one coherent stream.

Campaign 3, Workstream 3. UMH substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ExecutionStreamType(str, Enum):
    WORK_PACKET = "work_packet"
    AGENT_DISPATCH = "agent_dispatch"
    COMPUTE_TASK = "compute_task"


class ExecutionStreamStatus(str, Enum):
    QUEUED = "queued"
    EXECUTING = "executing"
    BLOCKED = "blocked"
    APPROVAL_PENDING = "approval_pending"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class UnifiedExecutionStream:
    stream_id: str
    stream_type: ExecutionStreamType
    status: ExecutionStreamStatus
    description: str
    agent_type: str = ""
    compute_node_id: str = ""
    risk_class: str = ""
    started_at: float = 0.0
    proof_id: str = ""
    lineage_node_id: str = ""
    source_id: str = ""
    source_system: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "stream_id": self.stream_id,
            "stream_type": self.stream_type.value,
            "status": self.status.value,
            "description": self.description,
            "agent_type": self.agent_type,
            "compute_node_id": self.compute_node_id,
            "risk_class": self.risk_class,
            "started_at": self.started_at,
            "proof_id": self.proof_id,
            "lineage_node_id": self.lineage_node_id,
            "source_id": self.source_id,
            "source_system": self.source_system,
        }


@dataclass
class UnifiedApprovalItem:
    approval_id: str
    source_system: str
    title: str
    description: str
    risk_class: str = ""
    waiting_since: float = 0.0
    work_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "source_system": self.source_system,
            "title": self.title,
            "description": self.description,
            "risk_class": self.risk_class,
            "waiting_since": self.waiting_since,
            "work_id": self.work_id,
        }


@dataclass
class ExecutionSurfaceSnapshot:
    active_streams: list[UnifiedExecutionStream]
    queued_streams: list[UnifiedExecutionStream]
    blocked_streams: list[UnifiedExecutionStream]
    pending_approvals: list[UnifiedApprovalItem]
    recent_completions: list[UnifiedExecutionStream]
    fleet_health: dict[str, Any] = field(default_factory=dict)
    compute_health: dict[str, Any] = field(default_factory=dict)
    compounding_summary: dict[str, Any] = field(default_factory=dict)
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_streams": [s.to_dict() for s in self.active_streams],
            "queued_streams": [s.to_dict() for s in self.queued_streams],
            "blocked_streams": [s.to_dict() for s in self.blocked_streams],
            "pending_approvals": [a.to_dict() for a in self.pending_approvals],
            "recent_completions": [s.to_dict() for s in self.recent_completions],
            "fleet_health": self.fleet_health,
            "compute_health": self.compute_health,
            "compounding_summary": self.compounding_summary,
            "generated_at": self.generated_at,
        }


def _safe_call(obj: Any, method: str, *args: Any, **kwargs: Any) -> Any:
    """Call method on obj if obj is not None, return None on failure."""
    if obj is None:
        return None
    fn = getattr(obj, method, None)
    if fn is None:
        return None
    try:
        return fn(*args, **kwargs)
    except Exception:
        logger.debug("safe_call %s.%s failed", type(obj).__name__, method, exc_info=True)
        return None


def _extract_id(item: Any, *keys: str) -> str:
    """Extract an ID from an item by trying multiple attribute/key names."""
    for k in keys:
        if isinstance(item, dict):
            v = item.get(k, "")
            if v:
                return str(v)
        else:
            v = getattr(item, k, "")
            if v:
                return str(v)
    return ""


def _extract_str(item: Any, key: str, default: str = "") -> str:
    if isinstance(item, dict):
        return str(item.get(key, default))
    return str(getattr(item, key, default))


def _extract_float(item: Any, key: str, default: float = 0.0) -> float:
    if isinstance(item, dict):
        v = item.get(key, default)
    else:
        v = getattr(item, key, default)
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


class UnifiedExecutionSurfaceRuntime:
    """Composes execution subsystems into a single operator-facing view.

    All subsystems are optional — graceful degradation when None.
    """

    def __init__(
        self,
        execution_graph: Any | None = None,
        agent_fleet: Any | None = None,
        compute_fabric: Any | None = None,
        governed_work: Any | None = None,
        proof_runtime: Any | None = None,
        compounding_engine: Any | None = None,
    ) -> None:
        self._execution_graph = execution_graph
        self._agent_fleet = agent_fleet
        self._compute_fabric = compute_fabric
        self._governed_work = governed_work
        self._proof_runtime = proof_runtime
        self._compounding_engine = compounding_engine
        self._completed: list[UnifiedExecutionStream] = []

    # ── Stream collection ──────────────────────────────────────────────

    def _work_streams(self, filter_status: str | None = None) -> list[UnifiedExecutionStream]:
        items = _safe_call(self._governed_work, "active") or []
        if filter_status == "queued":
            items = _safe_call(self._governed_work, "queue") or []
        elif filter_status == "blocked":
            items = _safe_call(self._governed_work, "blocked") or []

        streams: list[UnifiedExecutionStream] = []
        for item in items:
            wid = _extract_id(item, "work_id", "id", "packet_id")
            status_raw = _extract_str(item, "status", "executing")
            status = self._map_status(status_raw)
            if filter_status and status.value != filter_status:
                continue
            streams.append(
                UnifiedExecutionStream(
                    stream_id=f"wp-{wid}" if wid else f"wp-{uuid4().hex[:8]}",
                    stream_type=ExecutionStreamType.WORK_PACKET,
                    status=status,
                    description=_extract_str(
                        item, "title", _extract_str(item, "description", "work packet")
                    ),
                    risk_class=_extract_str(item, "risk_class", _extract_str(item, "risk", "")),
                    started_at=_extract_float(
                        item, "created_at", _extract_float(item, "started_at")
                    ),
                    source_id=wid,
                    source_system="governed_work",
                )
            )
        return streams

    def _agent_streams(self) -> list[UnifiedExecutionStream]:
        dispatches = _safe_call(self._agent_fleet, "active_dispatches") or []
        streams: list[UnifiedExecutionStream] = []
        for d in dispatches:
            did = _extract_id(d, "dispatch_id", "id")
            streams.append(
                UnifiedExecutionStream(
                    stream_id=f"ad-{did}" if did else f"ad-{uuid4().hex[:8]}",
                    stream_type=ExecutionStreamType.AGENT_DISPATCH,
                    status=ExecutionStreamStatus.EXECUTING,
                    description=_extract_str(
                        d, "description", _extract_str(d, "task", "agent dispatch")
                    ),
                    agent_type=_extract_str(d, "agent_type", _extract_str(d, "agent", "")),
                    compute_node_id=_extract_str(d, "node_id", ""),
                    risk_class=_extract_str(d, "risk_class", ""),
                    started_at=_extract_float(d, "dispatched_at", _extract_float(d, "started_at")),
                    source_id=did,
                    source_system="agent_fleet",
                )
            )
        return streams

    def _compute_streams(self) -> list[UnifiedExecutionStream]:
        tasks = _safe_call(self._compute_fabric, "active_executions") or []
        streams: list[UnifiedExecutionStream] = []
        for t in tasks:
            tid = _extract_id(t, "task_id", "execution_id", "id")
            streams.append(
                UnifiedExecutionStream(
                    stream_id=f"ct-{tid}" if tid else f"ct-{uuid4().hex[:8]}",
                    stream_type=ExecutionStreamType.COMPUTE_TASK,
                    status=ExecutionStreamStatus.EXECUTING,
                    description=_extract_str(
                        t, "description", _extract_str(t, "task", "compute task")
                    ),
                    compute_node_id=_extract_str(t, "node_id", _extract_str(t, "device_id", "")),
                    risk_class=_extract_str(t, "risk_class", ""),
                    started_at=_extract_float(t, "started_at"),
                    source_id=tid,
                    source_system="compute_fabric",
                )
            )
        return streams

    @staticmethod
    def _map_status(raw: str) -> ExecutionStreamStatus:
        mapping = {
            "queued": ExecutionStreamStatus.QUEUED,
            "pending": ExecutionStreamStatus.QUEUED,
            "executing": ExecutionStreamStatus.EXECUTING,
            "running": ExecutionStreamStatus.EXECUTING,
            "active": ExecutionStreamStatus.EXECUTING,
            "blocked": ExecutionStreamStatus.BLOCKED,
            "approval_pending": ExecutionStreamStatus.APPROVAL_PENDING,
            "awaiting_approval": ExecutionStreamStatus.APPROVAL_PENDING,
            "completed": ExecutionStreamStatus.COMPLETED,
            "done": ExecutionStreamStatus.COMPLETED,
            "failed": ExecutionStreamStatus.FAILED,
            "error": ExecutionStreamStatus.FAILED,
        }
        return mapping.get(raw.lower(), ExecutionStreamStatus.EXECUTING)

    def _dedup_streams(self, streams: list[UnifiedExecutionStream]) -> list[UnifiedExecutionStream]:
        """If an agent dispatch references a work packet, merge them."""
        work_by_source: dict[str, UnifiedExecutionStream] = {}
        agent_streams: list[UnifiedExecutionStream] = []
        other: list[UnifiedExecutionStream] = []

        for s in streams:
            if s.stream_type == ExecutionStreamType.WORK_PACKET and s.source_id:
                work_by_source[s.source_id] = s
            elif s.stream_type == ExecutionStreamType.AGENT_DISPATCH:
                agent_streams.append(s)
            else:
                other.append(s)

        for a in agent_streams:
            work_id = _extract_str(a, "source_id", "")
            if work_id in work_by_source:
                wp = work_by_source[work_id]
                wp.agent_type = a.agent_type or wp.agent_type
                wp.compute_node_id = a.compute_node_id or wp.compute_node_id
            else:
                other.append(a)

        return list(work_by_source.values()) + other

    # ── Approval collection ────────────────────────────────────────────

    def _governed_work_approvals(self) -> list[UnifiedApprovalItem]:
        queue = _safe_call(self._governed_work, "queue") or []
        items: list[UnifiedApprovalItem] = []
        for w in queue:
            status_raw = _extract_str(w, "status", "")
            if status_raw.lower() not in ("approval_pending", "awaiting_approval", "pending"):
                continue
            wid = _extract_id(w, "work_id", "id", "packet_id")
            items.append(
                UnifiedApprovalItem(
                    approval_id=f"gw-{wid}" if wid else f"gw-{uuid4().hex[:8]}",
                    source_system="governed_work",
                    title=_extract_str(w, "title", "work item"),
                    description=_extract_str(w, "description", ""),
                    risk_class=_extract_str(w, "risk_class", _extract_str(w, "risk", "")),
                    waiting_since=_extract_float(w, "created_at"),
                    work_id=wid,
                )
            )
        return items

    def _compounding_approvals(self) -> list[UnifiedApprovalItem]:
        candidates = (
            _safe_call(self._compounding_engine, "list_candidates", status="proposed") or []
        )
        items: list[UnifiedApprovalItem] = []
        for c in candidates:
            cid = _extract_id(c, "candidate_id", "id")
            items.append(
                UnifiedApprovalItem(
                    approval_id=f"ce-{cid}" if cid else f"ce-{uuid4().hex[:8]}",
                    source_system="compounding",
                    title=_extract_str(
                        c, "title", _extract_str(c, "name", "compounding candidate")
                    ),
                    description=_extract_str(c, "description", ""),
                    risk_class="low",
                    waiting_since=_extract_float(c, "proposed_at", _extract_float(c, "created_at")),
                    work_id=cid,
                )
            )
        return items

    def _approval_gate_approvals(self) -> list[UnifiedApprovalItem]:
        try:
            from substrate.organism.approval_gate import OperatorApprovalGate

            gate = OperatorApprovalGate()
            packets = gate.pending_packets() or []
        except Exception:
            return []
        items: list[UnifiedApprovalItem] = []
        for p in packets:
            pid = _extract_id(p, "packet_id", "id")
            items.append(
                UnifiedApprovalItem(
                    approval_id=f"ag-{pid}" if pid else f"ag-{uuid4().hex[:8]}",
                    source_system="approval_gate",
                    title=_extract_str(p, "title", "approval gate packet"),
                    description=_extract_str(p, "description", ""),
                    risk_class=_extract_str(p, "risk_class", ""),
                    waiting_since=_extract_float(p, "created_at"),
                    work_id=pid,
                )
            )
        return items

    # ── Public API ─────────────────────────────────────────────────────

    def active_streams(self) -> list[UnifiedExecutionStream]:
        raw = self._work_streams() + self._agent_streams() + self._compute_streams()
        return self._dedup_streams(raw)

    def queued_streams(self) -> list[UnifiedExecutionStream]:
        return self._work_streams(filter_status="queued")

    def blocked_streams(self) -> list[UnifiedExecutionStream]:
        return self._work_streams(filter_status="blocked")

    def pending_approvals(self) -> list[UnifiedApprovalItem]:
        return (
            self._governed_work_approvals()
            + self._compounding_approvals()
            + self._approval_gate_approvals()
        )

    def recent_completions(self, limit: int = 20) -> list[UnifiedExecutionStream]:
        return self._completed[-limit:]

    def stream_detail(self, stream_id: str) -> dict[str, Any]:
        for s in (
            self.active_streams() + self.queued_streams() + self.blocked_streams() + self._completed
        ):
            if s.stream_id == stream_id:
                detail = s.to_dict()
                if s.source_id and self._proof_runtime is not None:
                    proof = _safe_call(self._proof_runtime, "package_for", s.source_id)
                    if proof is not None:
                        if hasattr(proof, "to_dict"):
                            detail["proof"] = proof.to_dict()
                        elif isinstance(proof, dict):
                            detail["proof"] = proof
                if s.lineage_node_id and self._execution_graph is not None:
                    trace = _safe_call(self._execution_graph, "trace_full", s.lineage_node_id)
                    if trace is not None:
                        detail["lineage_trace"] = (
                            trace if isinstance(trace, (dict, list)) else str(trace)
                        )
                return detail
        return {"error": "stream_not_found", "stream_id": stream_id}

    def approve(self, approval_id: str, source_system: str) -> dict[str, Any]:
        work_id = approval_id.split("-", 1)[-1] if "-" in approval_id else approval_id
        if source_system == "governed_work":
            result = _safe_call(self._governed_work, "approve_work", work_id)
        elif source_system == "compounding":
            result = _safe_call(self._compounding_engine, "approve", work_id)
        elif source_system == "approval_gate":
            try:
                from substrate.organism.approval_gate import OperatorApprovalGate

                gate = OperatorApprovalGate()
                result = gate.approve(work_id)
            except Exception as exc:
                return {"status": "error", "message": str(exc)}
        else:
            return {"status": "error", "message": f"unknown source_system: {source_system}"}

        if result is None:
            return {"status": "error", "message": "subsystem returned None"}
        return {"status": "approved", "approval_id": approval_id, "source_system": source_system}

    def reject(self, approval_id: str, source_system: str, reason: str = "") -> dict[str, Any]:
        work_id = approval_id.split("-", 1)[-1] if "-" in approval_id else approval_id
        if source_system == "governed_work":
            result = _safe_call(self._governed_work, "reject_work", work_id, reason)
        elif source_system == "compounding":
            result = _safe_call(self._compounding_engine, "reject", work_id, reason)
        elif source_system == "approval_gate":
            try:
                from substrate.organism.approval_gate import OperatorApprovalGate

                gate = OperatorApprovalGate()
                result = gate.reject(work_id, reason)
            except Exception as exc:
                return {"status": "error", "message": str(exc)}
        else:
            return {"status": "error", "message": f"unknown source_system: {source_system}"}

        if result is None:
            return {"status": "error", "message": "subsystem returned None"}
        return {
            "status": "rejected",
            "approval_id": approval_id,
            "source_system": source_system,
            "reason": reason,
        }

    def snapshot(self) -> ExecutionSurfaceSnapshot:
        fleet_health = _safe_call(self._agent_fleet, "fleet_health")
        compute_health = _safe_call(self._compute_fabric, "health")
        comp_summary = _safe_call(self._compounding_engine, "summary")

        def _to_dict_safe(val: Any) -> dict[str, Any]:
            if val is None:
                return {}
            if isinstance(val, dict):
                return val
            if hasattr(val, "to_dict"):
                return val.to_dict()
            return {}

        return ExecutionSurfaceSnapshot(
            active_streams=self.active_streams(),
            queued_streams=self.queued_streams(),
            blocked_streams=self.blocked_streams(),
            pending_approvals=self.pending_approvals(),
            recent_completions=self.recent_completions(),
            fleet_health=_to_dict_safe(fleet_health),
            compute_health=_to_dict_safe(compute_health),
            compounding_summary=_to_dict_safe(comp_summary),
        )
