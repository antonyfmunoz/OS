"""Tests for UnifiedExecutionSurfaceRuntime — Campaign 3.3.

Covers: stream collection/merging, status mapping, approval collection/routing,
deduplication, snapshot composition, type serialization, graceful degradation.
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.workstation.unified_execution_surface_runtime import (
    ExecutionStreamStatus,
    ExecutionStreamType,
    ExecutionSurfaceSnapshot,
    UnifiedApprovalItem,
    UnifiedExecutionStream,
    UnifiedExecutionSurfaceRuntime,
)


# ── Mock subsystems ───────────────────────────────────────────────────────


class MockGovernedWork:
    def __init__(self, active=None, queue=None, blocked=None):
        self._active = active or []
        self._queue = queue or []
        self._blocked = blocked or []

    def active(self):
        return self._active

    def queue(self):
        return self._queue

    def blocked(self):
        return self._blocked

    def approve_work(self, work_id):
        return {"approved": work_id}

    def reject_work(self, work_id, reason=""):
        return {"rejected": work_id, "reason": reason}


class MockAgentFleet:
    def __init__(self, dispatches=None, health=None):
        self._dispatches = dispatches or []
        self._health = health or {}

    def active_dispatches(self):
        return self._dispatches

    def fleet_health(self):
        return self._health


class MockComputeFabric:
    def __init__(self, executions=None, health=None):
        self._executions = executions or []
        self._health = health or {}

    def active_executions(self):
        return self._executions

    def health(self):
        return self._health


class MockProofRuntime:
    def __init__(self, proofs=None):
        self._proofs = proofs or {}

    def package_for(self, source_id):
        return self._proofs.get(source_id)


class MockCompoundingEngine:
    def __init__(self, candidates=None, summary=None):
        self._candidates = candidates or []
        self._summary = summary or {}

    def list_candidates(self, status="proposed"):
        return [c for c in self._candidates if c.get("status") == status]

    def approve(self, candidate_id):
        return {"approved": candidate_id}

    def reject(self, candidate_id, reason=""):
        return {"rejected": candidate_id, "reason": reason}

    def summary(self):
        return self._summary


class MockExecutionGraph:
    def __init__(self, nodes=None):
        self._nodes = nodes or []

    def list_nodes(self):
        return self._nodes

    def trace_full(self, node_id):
        return {"trace": node_id}


# ── Type serialization ────────────────────────────────────────────────────


class TestExecutionStreamSerialization:
    def test_to_dict_has_all_fields(self) -> None:
        s = UnifiedExecutionStream(
            stream_id="wp-123",
            stream_type=ExecutionStreamType.WORK_PACKET,
            status=ExecutionStreamStatus.EXECUTING,
            description="test work",
            risk_class="low",
        )
        d = s.to_dict()
        assert d["stream_id"] == "wp-123"
        assert d["stream_type"] == "work_packet"
        assert d["status"] == "executing"
        assert d["description"] == "test work"
        assert d["risk_class"] == "low"

    def test_enum_values_serialize_as_strings(self) -> None:
        s = UnifiedExecutionStream(
            stream_id="ad-1",
            stream_type=ExecutionStreamType.AGENT_DISPATCH,
            status=ExecutionStreamStatus.QUEUED,
            description="test",
        )
        d = s.to_dict()
        assert isinstance(d["stream_type"], str)
        assert isinstance(d["status"], str)

    def test_default_values(self) -> None:
        s = UnifiedExecutionStream(
            stream_id="ct-1",
            stream_type=ExecutionStreamType.COMPUTE_TASK,
            status=ExecutionStreamStatus.COMPLETED,
            description="done",
        )
        d = s.to_dict()
        assert d["agent_type"] == ""
        assert d["compute_node_id"] == ""
        assert d["started_at"] == 0.0
        assert d["proof_id"] == ""


class TestApprovalItemSerialization:
    def test_to_dict_has_all_fields(self) -> None:
        a = UnifiedApprovalItem(
            approval_id="gw-456",
            source_system="governed_work",
            title="test approval",
            description="needs review",
            risk_class="high",
        )
        d = a.to_dict()
        assert d["approval_id"] == "gw-456"
        assert d["source_system"] == "governed_work"
        assert d["title"] == "test approval"

    def test_default_values(self) -> None:
        a = UnifiedApprovalItem(
            approval_id="ce-1",
            source_system="compounding",
            title="x",
            description="y",
        )
        d = a.to_dict()
        assert d["risk_class"] == ""
        assert d["waiting_since"] == 0.0
        assert d["work_id"] == ""


class TestSnapshotSerialization:
    def test_snapshot_to_dict(self) -> None:
        snap = ExecutionSurfaceSnapshot(
            active_streams=[],
            queued_streams=[],
            blocked_streams=[],
            pending_approvals=[],
            recent_completions=[],
        )
        d = snap.to_dict()
        assert "active_streams" in d
        assert "queued_streams" in d
        assert "blocked_streams" in d
        assert "pending_approvals" in d
        assert "recent_completions" in d
        assert "fleet_health" in d
        assert d["generated_at"] > 0

    def test_snapshot_with_streams(self) -> None:
        s = UnifiedExecutionStream(
            stream_id="wp-1",
            stream_type=ExecutionStreamType.WORK_PACKET,
            status=ExecutionStreamStatus.EXECUTING,
            description="test",
        )
        snap = ExecutionSurfaceSnapshot(
            active_streams=[s],
            queued_streams=[],
            blocked_streams=[],
            pending_approvals=[],
            recent_completions=[],
        )
        d = snap.to_dict()
        assert len(d["active_streams"]) == 1
        assert d["active_streams"][0]["stream_id"] == "wp-1"


# ── Status mapping ────────────────────────────────────────────────────────


class TestStatusMapping:
    def test_executing_variants(self) -> None:
        rt = UnifiedExecutionSurfaceRuntime()
        assert rt._map_status("executing") == ExecutionStreamStatus.EXECUTING
        assert rt._map_status("running") == ExecutionStreamStatus.EXECUTING
        assert rt._map_status("active") == ExecutionStreamStatus.EXECUTING

    def test_queued_variants(self) -> None:
        rt = UnifiedExecutionSurfaceRuntime()
        assert rt._map_status("queued") == ExecutionStreamStatus.QUEUED
        assert rt._map_status("pending") == ExecutionStreamStatus.QUEUED

    def test_completed_variants(self) -> None:
        rt = UnifiedExecutionSurfaceRuntime()
        assert rt._map_status("completed") == ExecutionStreamStatus.COMPLETED
        assert rt._map_status("done") == ExecutionStreamStatus.COMPLETED

    def test_failed_variants(self) -> None:
        rt = UnifiedExecutionSurfaceRuntime()
        assert rt._map_status("failed") == ExecutionStreamStatus.FAILED
        assert rt._map_status("error") == ExecutionStreamStatus.FAILED

    def test_blocked(self) -> None:
        rt = UnifiedExecutionSurfaceRuntime()
        assert rt._map_status("blocked") == ExecutionStreamStatus.BLOCKED

    def test_approval_pending(self) -> None:
        rt = UnifiedExecutionSurfaceRuntime()
        assert rt._map_status("approval_pending") == ExecutionStreamStatus.APPROVAL_PENDING
        assert rt._map_status("awaiting_approval") == ExecutionStreamStatus.APPROVAL_PENDING

    def test_unknown_defaults_to_executing(self) -> None:
        rt = UnifiedExecutionSurfaceRuntime()
        assert rt._map_status("unknown_status") == ExecutionStreamStatus.EXECUTING

    def test_case_insensitive(self) -> None:
        rt = UnifiedExecutionSurfaceRuntime()
        assert rt._map_status("EXECUTING") == ExecutionStreamStatus.EXECUTING
        assert rt._map_status("Queued") == ExecutionStreamStatus.QUEUED


# ── Graceful degradation ─────────────────────────────────────────────────


class TestGracefulDegradation:
    def test_all_none_subsystems(self) -> None:
        rt = UnifiedExecutionSurfaceRuntime()
        assert rt.active_streams() == []
        assert rt.queued_streams() == []
        assert rt.blocked_streams() == []
        assert rt.pending_approvals() == []
        assert rt.recent_completions() == []

    def test_snapshot_with_no_subsystems(self) -> None:
        rt = UnifiedExecutionSurfaceRuntime()
        snap = rt.snapshot()
        assert isinstance(snap, ExecutionSurfaceSnapshot)
        assert snap.active_streams == []
        assert snap.fleet_health == {}
        assert snap.compute_health == {}
        assert snap.compounding_summary == {}

    def test_stream_detail_not_found(self) -> None:
        rt = UnifiedExecutionSurfaceRuntime()
        detail = rt.stream_detail("nonexistent-id")
        assert detail["error"] == "stream_not_found"


# ── Active stream collection ─────────────────────────────────────────────


class TestActiveStreams:
    def test_work_packets_from_governed_work(self) -> None:
        gw = MockGovernedWork(active=[
            {"work_id": "w1", "title": "fix bug", "status": "executing", "risk_class": "low"},
            {"work_id": "w2", "title": "deploy", "status": "executing", "risk_class": "high"},
        ])
        rt = UnifiedExecutionSurfaceRuntime(governed_work=gw)
        streams = rt.active_streams()
        assert len(streams) == 2
        assert all(s.stream_type == ExecutionStreamType.WORK_PACKET for s in streams)

    def test_agent_dispatches_from_fleet(self) -> None:
        af = MockAgentFleet(dispatches=[
            {"dispatch_id": "d1", "description": "research task", "agent_type": "researcher"},
        ])
        rt = UnifiedExecutionSurfaceRuntime(agent_fleet=af)
        streams = rt.active_streams()
        assert len(streams) == 1
        assert streams[0].stream_type == ExecutionStreamType.AGENT_DISPATCH
        assert streams[0].agent_type == "researcher"

    def test_compute_tasks_from_fabric(self) -> None:
        cf = MockComputeFabric(executions=[
            {"task_id": "t1", "description": "build project", "node_id": "vps-1"},
        ])
        rt = UnifiedExecutionSurfaceRuntime(compute_fabric=cf)
        streams = rt.active_streams()
        assert len(streams) == 1
        assert streams[0].stream_type == ExecutionStreamType.COMPUTE_TASK
        assert streams[0].compute_node_id == "vps-1"

    def test_merged_streams_from_all_sources(self) -> None:
        gw = MockGovernedWork(active=[
            {"work_id": "w1", "title": "work", "status": "executing"},
        ])
        af = MockAgentFleet(dispatches=[
            {"dispatch_id": "d1", "description": "agent work"},
        ])
        cf = MockComputeFabric(executions=[
            {"task_id": "t1", "description": "compute"},
        ])
        rt = UnifiedExecutionSurfaceRuntime(
            governed_work=gw, agent_fleet=af, compute_fabric=cf,
        )
        streams = rt.active_streams()
        types = {s.stream_type for s in streams}
        assert ExecutionStreamType.WORK_PACKET in types
        assert ExecutionStreamType.AGENT_DISPATCH in types
        assert ExecutionStreamType.COMPUTE_TASK in types


# ── Queued and blocked streams ────────────────────────────────────────────


class TestQueuedAndBlocked:
    def test_queued_streams(self) -> None:
        gw = MockGovernedWork(queue=[
            {"work_id": "q1", "title": "queued item", "status": "queued"},
        ])
        rt = UnifiedExecutionSurfaceRuntime(governed_work=gw)
        queued = rt.queued_streams()
        assert len(queued) == 1
        assert queued[0].status == ExecutionStreamStatus.QUEUED

    def test_blocked_streams(self) -> None:
        gw = MockGovernedWork(blocked=[
            {"work_id": "b1", "title": "blocked item", "status": "blocked"},
        ])
        rt = UnifiedExecutionSurfaceRuntime(governed_work=gw)
        blocked = rt.blocked_streams()
        assert len(blocked) == 1
        assert blocked[0].status == ExecutionStreamStatus.BLOCKED


# ── Approval collection ──────────────────────────────────────────────────


class TestApprovalCollection:
    def test_governed_work_approvals(self) -> None:
        gw = MockGovernedWork(queue=[
            {"work_id": "a1", "title": "needs approval", "status": "approval_pending", "risk_class": "high"},
            {"work_id": "a2", "title": "just queued", "status": "queued"},
        ])
        rt = UnifiedExecutionSurfaceRuntime(governed_work=gw)
        approvals = rt.pending_approvals()
        assert len(approvals) == 1
        assert approvals[0].source_system == "governed_work"

    def test_compounding_approvals(self) -> None:
        ce = MockCompoundingEngine(candidates=[
            {"candidate_id": "c1", "title": "new pattern", "status": "proposed"},
            {"candidate_id": "c2", "title": "old pattern", "status": "approved"},
        ])
        rt = UnifiedExecutionSurfaceRuntime(compounding_engine=ce)
        approvals = rt.pending_approvals()
        assert len(approvals) == 1
        assert approvals[0].source_system == "compounding"

    def test_merged_approvals(self) -> None:
        gw = MockGovernedWork(queue=[
            {"work_id": "a1", "title": "work approval", "status": "pending"},
        ])
        ce = MockCompoundingEngine(candidates=[
            {"candidate_id": "c1", "title": "compound approval", "status": "proposed"},
        ])
        rt = UnifiedExecutionSurfaceRuntime(governed_work=gw, compounding_engine=ce)
        approvals = rt.pending_approvals()
        sources = {a.source_system for a in approvals}
        assert "governed_work" in sources
        assert "compounding" in sources


# ── Approve / reject routing ─────────────────────────────────────────────


class TestApproveReject:
    def test_approve_governed_work(self) -> None:
        gw = MockGovernedWork()
        rt = UnifiedExecutionSurfaceRuntime(governed_work=gw)
        result = rt.approve("gw-w1", "governed_work")
        assert result["status"] == "approved"

    def test_approve_compounding(self) -> None:
        ce = MockCompoundingEngine()
        rt = UnifiedExecutionSurfaceRuntime(compounding_engine=ce)
        result = rt.approve("ce-c1", "compounding")
        assert result["status"] == "approved"

    def test_reject_governed_work(self) -> None:
        gw = MockGovernedWork()
        rt = UnifiedExecutionSurfaceRuntime(governed_work=gw)
        result = rt.reject("gw-w1", "governed_work", reason="not ready")
        assert result["status"] == "rejected"
        assert result["reason"] == "not ready"

    def test_reject_compounding(self) -> None:
        ce = MockCompoundingEngine()
        rt = UnifiedExecutionSurfaceRuntime(compounding_engine=ce)
        result = rt.reject("ce-c1", "compounding", reason="poor quality")
        assert result["status"] == "rejected"

    def test_approve_unknown_source(self) -> None:
        rt = UnifiedExecutionSurfaceRuntime()
        result = rt.approve("x-1", "unknown_system")
        assert result["status"] == "error"
        assert "unknown" in result["message"]

    def test_reject_unknown_source(self) -> None:
        rt = UnifiedExecutionSurfaceRuntime()
        result = rt.reject("x-1", "unknown_system")
        assert result["status"] == "error"

    def test_approve_none_subsystem_returns_error(self) -> None:
        rt = UnifiedExecutionSurfaceRuntime()
        result = rt.approve("gw-1", "governed_work")
        assert result["status"] == "error"


# ── Stream detail ─────────────────────────────────────────────────────────


class TestStreamDetail:
    def test_detail_found_in_active(self) -> None:
        gw = MockGovernedWork(active=[
            {"work_id": "w1", "title": "detail test", "status": "executing"},
        ])
        rt = UnifiedExecutionSurfaceRuntime(governed_work=gw)
        streams = rt.active_streams()
        sid = streams[0].stream_id
        detail = rt.stream_detail(sid)
        assert detail["stream_id"] == sid
        assert detail.get("error") is None

    def test_detail_with_proof(self) -> None:
        gw = MockGovernedWork(active=[
            {"work_id": "w1", "title": "proved", "status": "executing"},
        ])
        pr = MockProofRuntime(proofs={"w1": {"proof": "evidence"}})
        rt = UnifiedExecutionSurfaceRuntime(governed_work=gw, proof_runtime=pr)
        streams = rt.active_streams()
        sid = streams[0].stream_id
        detail = rt.stream_detail(sid)
        assert detail.get("proof") == {"proof": "evidence"}

    def test_detail_not_found(self) -> None:
        rt = UnifiedExecutionSurfaceRuntime()
        detail = rt.stream_detail("nonexistent")
        assert detail["error"] == "stream_not_found"


# ── Recent completions ────────────────────────────────────────────────────


class TestRecentCompletions:
    def test_empty_by_default(self) -> None:
        rt = UnifiedExecutionSurfaceRuntime()
        assert rt.recent_completions() == []

    def test_respects_limit(self) -> None:
        rt = UnifiedExecutionSurfaceRuntime()
        for i in range(30):
            rt._completed.append(UnifiedExecutionStream(
                stream_id=f"c-{i}",
                stream_type=ExecutionStreamType.WORK_PACKET,
                status=ExecutionStreamStatus.COMPLETED,
                description=f"completed {i}",
            ))
        assert len(rt.recent_completions(limit=10)) == 10
        assert len(rt.recent_completions(limit=20)) == 20
        assert len(rt.recent_completions()) == 20  # default


# ── Snapshot composition ─────────────────────────────────────────────────


class TestSnapshotComposition:
    def test_snapshot_aggregates_all(self) -> None:
        gw = MockGovernedWork(
            active=[{"work_id": "w1", "title": "active", "status": "executing"}],
            queue=[{"work_id": "q1", "title": "pending", "status": "approval_pending"}],
            blocked=[{"work_id": "b1", "title": "blocked", "status": "blocked"}],
        )
        af = MockAgentFleet(
            dispatches=[{"dispatch_id": "d1", "description": "agent"}],
            health={"total": 5, "active": 1},
        )
        cf = MockComputeFabric(
            executions=[{"task_id": "t1", "description": "compute"}],
            health={"nodes": 2, "load": 0.5},
        )
        ce = MockCompoundingEngine(
            candidates=[{"candidate_id": "c1", "title": "pattern", "status": "proposed"}],
            summary={"total": 10},
        )
        rt = UnifiedExecutionSurfaceRuntime(
            governed_work=gw,
            agent_fleet=af,
            compute_fabric=cf,
            compounding_engine=ce,
        )
        snap = rt.snapshot()
        assert len(snap.active_streams) >= 2
        assert len(snap.pending_approvals) >= 1
        assert snap.fleet_health == {"total": 5, "active": 1}
        assert snap.compute_health == {"nodes": 2, "load": 0.5}
        assert snap.compounding_summary == {"total": 10}

    def test_snapshot_to_dict_is_serializable(self) -> None:
        rt = UnifiedExecutionSurfaceRuntime()
        d = rt.snapshot().to_dict()
        assert isinstance(d, dict)
        assert isinstance(d["active_streams"], list)
        assert isinstance(d["fleet_health"], dict)


# ── Enum values ───────────────────────────────────────────────────────────


class TestEnumValues:
    def test_stream_types(self) -> None:
        assert ExecutionStreamType.WORK_PACKET.value == "work_packet"
        assert ExecutionStreamType.AGENT_DISPATCH.value == "agent_dispatch"
        assert ExecutionStreamType.COMPUTE_TASK.value == "compute_task"

    def test_stream_statuses(self) -> None:
        assert ExecutionStreamStatus.QUEUED.value == "queued"
        assert ExecutionStreamStatus.EXECUTING.value == "executing"
        assert ExecutionStreamStatus.BLOCKED.value == "blocked"
        assert ExecutionStreamStatus.APPROVAL_PENDING.value == "approval_pending"
        assert ExecutionStreamStatus.COMPLETED.value == "completed"
        assert ExecutionStreamStatus.FAILED.value == "failed"


# ── ID extraction ─────────────────────────────────────────────────────────


class TestIdExtraction:
    def test_work_stream_ids_prefixed(self) -> None:
        gw = MockGovernedWork(active=[
            {"work_id": "abc123", "title": "test", "status": "executing"},
        ])
        rt = UnifiedExecutionSurfaceRuntime(governed_work=gw)
        streams = rt.active_streams()
        assert streams[0].stream_id.startswith("wp-")
        assert "abc123" in streams[0].stream_id

    def test_agent_stream_ids_prefixed(self) -> None:
        af = MockAgentFleet(dispatches=[
            {"dispatch_id": "d1", "description": "test"},
        ])
        rt = UnifiedExecutionSurfaceRuntime(agent_fleet=af)
        streams = rt.active_streams()
        assert streams[0].stream_id.startswith("ad-")

    def test_compute_stream_ids_prefixed(self) -> None:
        cf = MockComputeFabric(executions=[
            {"task_id": "t1", "description": "test"},
        ])
        rt = UnifiedExecutionSurfaceRuntime(compute_fabric=cf)
        streams = rt.active_streams()
        assert streams[0].stream_id.startswith("ct-")

    def test_dict_id_extraction(self) -> None:
        gw = MockGovernedWork(active=[
            {"id": "fallback_id", "title": "test", "status": "executing"},
        ])
        rt = UnifiedExecutionSurfaceRuntime(governed_work=gw)
        streams = rt.active_streams()
        assert "fallback_id" in streams[0].stream_id
