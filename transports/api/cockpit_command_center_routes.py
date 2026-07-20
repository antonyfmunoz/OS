"""Cockpit command center routes — agent registry, work packet board, summary.

Phase 14.11E. Composes existing organism, work queue, spine, and approval
data into unified command center views. All routes are read-safe.
Mutation routes reuse existing governance paths.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import APIRouter, Depends, Request

from transports.api.governed import governed_mutation

logger = logging.getLogger(__name__)

_UMH_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_DATA_ROOT = os.path.join(_UMH_ROOT, "data", "umh")
from substrate.state.runtime_paths import runtime_state_dir as _rt_dir  # noqa: E402
from substrate.state.runtime_paths import runtime_state_path as _rt_path  # noqa: E402

_WORKCELL_DIR = str(_rt_dir("organism", create=False) / "workcells")
_WORK_PACKETS_PATH = str(_rt_path("universal_work", "work_packets.jsonl", create_parent=False))
_JOURNAL_PATH = str(_rt_path("organism", "execution_journal.jsonl", create_parent=False))
_APPROVALS_PATH = str(_rt_path("organism", "approvals.jsonl", create_parent=False))
_TRACES_PATH = os.path.join(_DATA_ROOT, "traces", "traces.jsonl")

command_center_router = APIRouter(prefix="/command-center", tags=["command-center"])
_require_operator: Callable | None = None


def configure(require_operator_dep: Callable) -> None:
    global _require_operator
    _require_operator = require_operator_dep


def _detect_env() -> str:
    import platform

    system = platform.system().lower()
    if os.path.exists("/.dockerenv"):
        return "container"
    if system == "linux":
        return "vps"
    if system == "darwin":
        return "macos"
    if system == "windows":
        return "windows"
    return "unknown"


def _load_workcell_heartbeats() -> list[dict[str, Any]]:
    """Load heartbeat data from all workcell directories."""
    heartbeats: list[dict[str, Any]] = []
    if not os.path.isdir(_WORKCELL_DIR):
        return heartbeats
    for entry in sorted(os.listdir(_WORKCELL_DIR)):
        hb_path = os.path.join(_WORKCELL_DIR, entry, "heartbeat.json")
        if os.path.exists(hb_path):
            try:
                with open(hb_path) as f:
                    data = json.load(f)
                data["workcell_dir"] = entry
                heartbeats.append(data)
            except (json.JSONDecodeError, OSError):
                heartbeats.append(
                    {
                        "workcell_id": entry,
                        "workcell_dir": entry,
                        "role": "unknown",
                        "status": "unavailable",
                        "error": "heartbeat unreadable",
                    }
                )
    return heartbeats


def _load_work_packets(
    status_filter: str = "",
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Load work packets from JSONL store."""
    packets: list[dict[str, Any]] = []
    if not os.path.exists(_WORK_PACKETS_PATH):
        return packets
    try:
        with open(_WORK_PACKETS_PATH) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    pkt = json.loads(line)
                    if status_filter and pkt.get("status") != status_filter:
                        continue
                    packets.append(pkt)
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    packets.sort(key=lambda p: p.get("leverage_score", 0), reverse=True)
    return packets[:limit]


def _load_blocked_packets() -> list[dict[str, Any]]:
    """Load work packets with blocked status or non-empty blockers."""
    packets: list[dict[str, Any]] = []
    if not os.path.exists(_WORK_PACKETS_PATH):
        return packets
    try:
        with open(_WORK_PACKETS_PATH) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    pkt = json.loads(line)
                    is_blocked = pkt.get("status") == "blocked" or bool(pkt.get("blockers"))
                    if is_blocked:
                        packets.append(pkt)
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return packets


def _load_approvals(status_filter: str = "pending", limit: int = 20) -> list[dict[str, Any]]:
    """Load approval objects from JSONL store."""
    approvals: list[dict[str, Any]] = []
    if not os.path.exists(_APPROVALS_PATH):
        return approvals
    try:
        with open(_APPROVALS_PATH) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if status_filter and entry.get("status") != status_filter:
                        continue
                    approvals.append(entry)
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return approvals[-limit:]


def _load_journal_recent(limit: int = 20) -> list[dict[str, Any]]:
    """Load recent execution journal entries."""
    entries: list[dict[str, Any]] = []
    if not os.path.exists(_JOURNAL_PATH):
        return entries
    try:
        with open(_JOURNAL_PATH) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return entries[-limit:]


def _load_traces_recent(limit: int = 10) -> list[dict[str, Any]]:
    """Load recent execution traces."""
    traces: list[dict[str, Any]] = []
    if not os.path.exists(_TRACES_PATH):
        return traces
    try:
        with open(_TRACES_PATH) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    traces.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return traces[-limit:]


def _label_environment(item: dict[str, Any]) -> dict[str, Any]:
    """Add environment label to an item based on available context."""
    env = _detect_env()
    node = os.uname().nodename
    item["environment"] = item.get("environment", env)
    item["node"] = item.get("node", node)
    item["source_env"] = env
    return item


# ── Gate 4: Operator-question endpoints (compose OperatorSnapshotRuntime) ────


def _get_snapshot_runtime() -> Any:
    if not hasattr(_get_snapshot_runtime, "_instance"):
        try:
            from substrate.operator.operator_snapshot_runtime import OperatorSnapshotRuntime

            _get_snapshot_runtime._instance = OperatorSnapshotRuntime()
        except Exception:
            logger.debug("OperatorSnapshotRuntime unavailable")
            _get_snapshot_runtime._instance = None
    return _get_snapshot_runtime._instance


@command_center_router.get("/situation")
def _situation(request: Request) -> dict[str, Any]:
    """Answers: 'Where am I? What's the context?'"""
    rt = _get_snapshot_runtime()
    if rt is None:
        return {"ok": True, "situation": {}}
    return {"ok": True, "situation": rt.situation()}


@command_center_router.get("/attention")
def _attention(request: Request) -> dict[str, Any]:
    """Answers: 'What needs me right now?'"""
    rt = _get_snapshot_runtime()
    if rt is None:
        return {"ok": True, "attention": []}
    items = rt.attention()
    return {"ok": True, "attention": [i.to_dict() if hasattr(i, "to_dict") else i for i in items]}


@command_center_router.get("/changes")
def _changes(request: Request) -> dict[str, Any]:
    """Answers: 'What changed since I last looked?'"""
    since = float(request.query_params.get("since", "0"))
    limit = min(int(request.query_params.get("limit", "50")), 200)
    rt = _get_snapshot_runtime()
    if rt is None:
        return {"ok": True, "changes": []}
    return {"ok": True, "changes": rt.changes(since=since, limit=limit)}


@command_center_router.get("/decisions")
def _decisions(request: Request) -> dict[str, Any]:
    """Answers: 'What's waiting for my decision?'"""
    rt = _get_snapshot_runtime()
    if rt is None:
        return {"ok": True, "decisions": []}
    return {"ok": True, "decisions": rt.decisions()}


@command_center_router.get("/next-actions")
def _next_actions(request: Request) -> dict[str, Any]:
    """Answers: 'What should I do next?'"""
    rt = _get_snapshot_runtime()
    if rt is None:
        return {"ok": True, "next_actions": []}
    return {"ok": True, "next_actions": rt.next_actions()}


@command_center_router.get("/snapshot")
def _full_snapshot(request: Request) -> dict[str, Any]:
    """Full operator question snapshot — all 5 questions in one request."""
    rt = _get_snapshot_runtime()
    if rt is None:
        return {"ok": True, "snapshot": {}}
    return {"ok": True, "snapshot": rt.snapshot().to_dict()}


# ── Existing command center routes ─────────────────────────────────


@command_center_router.get("/agents")
def _agents(request: Request) -> dict[str, Any]:
    """Agent registry — unified view of workcell heartbeats + organism agents."""
    heartbeats = _load_workcell_heartbeats()
    journal = _load_journal_recent(50)

    agents: list[dict[str, Any]] = []
    for hb in heartbeats:
        agent_id = hb.get("workcell_id", hb.get("workcell_dir", "unknown"))
        role = hb.get("role", "unknown")
        status = hb.get("status", "unknown")
        ts = hb.get("timestamp", 0)

        last_journal = None
        for j in reversed(journal):
            if j.get("source", "") == role or agent_id in j.get("source", ""):
                last_journal = j
                break

        agent = {
            "agent_id": agent_id,
            "display_name": role.replace("_", " ").title(),
            "role": role,
            "status": status,
            "current_task": "",
            "runtime": "organism_daemon",
            "authority_level": "workcell",
            "last_heartbeat": ts,
            "last_heartbeat_iso": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
            if ts
            else "",
            "messages_processed": hb.get("messages_processed", 0),
            "inbox_depth": hb.get("inbox_depth", 0),
            "generation": hb.get("generation", 0),
            "last_trace": last_journal.get("entry_id", "") if last_journal else "",
            "last_outcome": last_journal.get("phase", "") if last_journal else "",
        }
        _label_environment(agent)
        agents.append(agent)

    active = [a for a in agents if a["status"] == "active"]
    idle = [a for a in agents if a["status"] == "idle"]
    unavailable = [a for a in agents if a["status"] not in ("active", "idle", "waiting")]

    return {
        "ok": True,
        "agents": agents,
        "summary": {
            "total": len(agents),
            "active": len(active),
            "idle": len(idle),
            "unavailable": len(unavailable),
        },
        "source": "workcell_heartbeats",
        "source_env": _detect_env(),
    }


@command_center_router.get("/work-packets")
def _work_packets(request: Request) -> dict[str, Any]:
    """Work packet board — all packets with lifecycle status and environment."""
    status_filter = request.query_params.get("status", "")
    limit = min(int(request.query_params.get("limit", "50")), 100)

    packets = _load_work_packets(status_filter=status_filter, limit=limit)
    traces = _load_traces_recent(50)
    approvals = _load_approvals(status_filter="", limit=100)

    enriched: list[dict[str, Any]] = []
    for pkt in packets:
        pid = pkt.get("packet_id", "")

        related_traces = [
            t
            for t in traces
            if t.get("packet_id") == pid or pid in str(t.get("correlation_id", ""))
        ]
        related_approvals = [
            a for a in approvals if a.get("trace_id", "") == pid or pid in a.get("description", "")
        ]

        item = {
            "packet_id": pid,
            "title": pkt.get("title", ""),
            "objective": pkt.get("desired_end_state", pkt.get("user_intent", "")),
            "status": pkt.get("status", "unknown"),
            "status_reason": pkt.get("status_reason", ""),
            "owner": pkt.get("delegation_topology_id", ""),
            "risk_class": pkt.get("risk_class", ""),
            "leverage_score": pkt.get("leverage_score", 0),
            "priority": pkt.get("priority", ""),
            "urgency": pkt.get("urgency", ""),
            "blockers": pkt.get("blockers", []),
            "dependencies": pkt.get("dependencies", []),
            "approval_gates": pkt.get("approval_gates", []),
            "approval_state": "pending"
            if related_approvals and any(a.get("status") == "pending" for a in related_approvals)
            else "none",
            "latest_trace": related_traces[-1].get("entry_id", "") if related_traces else "",
            "latest_proof": pkt.get("linked_pr_url", ""),
            "next_action": pkt.get("status_reason", ""),
            "resume_target": pkt.get("linked_roadmap_phase", ""),
            "created_at": pkt.get("created_at", ""),
            "updated_at": pkt.get("updated_at", ""),
        }
        _label_environment(item)
        enriched.append(item)

    by_status: dict[str, int] = {}
    for p in enriched:
        s = p["status"]
        by_status[s] = by_status.get(s, 0) + 1

    return {
        "ok": True,
        "packets": enriched,
        "summary": {
            "total": len(enriched),
            "by_status": by_status,
            "blocked": sum(1 for p in enriched if p["blockers"]),
            "approval_pending": sum(1 for p in enriched if p["approval_state"] == "pending"),
        },
        "source_env": _detect_env(),
    }


@command_center_router.get("/blocked")
def _blocked(request: Request) -> dict[str, Any]:
    """Blocked work — packets and tasks that are stuck."""
    blocked_packets = _load_blocked_packets()
    journal = _load_journal_recent(50)
    failed_entries = [
        j
        for j in journal
        if j.get("phase") in ("EXECUTION_FAILED", "VERIFICATION_FAILED", "REJECTED")
    ]

    items: list[dict[str, Any]] = []
    for pkt in blocked_packets:
        item = {
            "type": "work_packet",
            "id": pkt.get("packet_id", ""),
            "title": pkt.get("title", ""),
            "status": pkt.get("status", "blocked"),
            "blockers": pkt.get("blockers", []),
            "risk_class": pkt.get("risk_class", ""),
            "owner": pkt.get("delegation_topology_id", ""),
        }
        _label_environment(item)
        items.append(item)

    for entry in failed_entries[-10:]:
        item = {
            "type": "execution_failure",
            "id": entry.get("entry_id", ""),
            "title": entry.get("details", {}).get("intent", entry.get("source", "")),
            "status": entry.get("phase", ""),
            "blockers": [entry.get("details", {}).get("error", "execution failed")],
            "risk_class": entry.get("details", {}).get("risk_level", ""),
            "owner": entry.get("source", ""),
        }
        _label_environment(item)
        items.append(item)

    return {
        "ok": True,
        "blocked": items,
        "summary": {
            "total": len(items),
            "packets": len(blocked_packets),
            "execution_failures": len(failed_entries),
        },
        "source_env": _detect_env(),
    }


@command_center_router.get("/approvals")
def _approvals_view(request: Request) -> dict[str, Any]:
    """Approval/blocked-work integration — pending approvals with context."""
    pending = _load_approvals(status_filter="pending")
    journal = _load_journal_recent(50)
    pending_journal = [
        j
        for j in journal
        if j.get("phase") in ("PROPOSED", "GOVERNANCE_CHECK")
        and j.get("details", {}).get("status") != "approved"
    ]

    items: list[dict[str, Any]] = []
    for a in pending:
        item = {
            "type": "approval",
            "id": a.get("id", ""),
            "title": a.get("title", ""),
            "description": a.get("description", ""),
            "risk_level": a.get("risk_level", ""),
            "status": a.get("status", "pending"),
            "agent": a.get("agent", ""),
            "trace_id": a.get("trace_id", ""),
            "governance_rationale": a.get("governance_rationale", ""),
            "created_at": a.get("created_at", ""),
            "resume_path": "approve or deny via /organism/spine/approve or /approvals POST",
        }
        _label_environment(item)
        items.append(item)

    for j in pending_journal[-10:]:
        if any(i["id"] == j.get("envelope_id") for i in items):
            continue
        item = {
            "type": "spine_envelope",
            "id": j.get("envelope_id", j.get("entry_id", "")),
            "title": j.get("details", {}).get("intent", j.get("source", "")),
            "description": j.get("details", {}).get("action_type", ""),
            "risk_level": j.get("details", {}).get("risk_level", ""),
            "status": j.get("phase", ""),
            "agent": j.get("source", ""),
            "trace_id": j.get("correlation_id", ""),
            "governance_rationale": j.get("details", {}).get("blast_radius", ""),
            "created_at": str(j.get("timestamp", "")),
            "resume_path": "approve via /organism/spine/approve/{id}",
        }
        _label_environment(item)
        items.append(item)

    return {
        "ok": True,
        "approvals": items,
        "summary": {
            "total": len(items),
            "store_pending": len(pending),
            "spine_pending": len(pending_journal),
        },
        "source_env": _detect_env(),
    }


@command_center_router.get("/traces")
def _traces_view(request: Request) -> dict[str, Any]:
    """Trace/proof linkage — recent execution traces with proof artifacts."""
    limit = min(int(request.query_params.get("limit", "20")), 50)
    traces = _load_traces_recent(limit)
    journal = _load_journal_recent(limit)

    proof_dir = os.path.join(_DATA_ROOT, "runtime", "canonical_memory_store", "proofs")
    proof_files: list[str] = []
    if os.path.isdir(proof_dir):
        try:
            proof_files = sorted(os.listdir(proof_dir))[-20:]
        except OSError:
            pass

    items: list[dict[str, Any]] = []
    for j in journal:
        item = {
            "type": "journal_entry",
            "id": j.get("entry_id", ""),
            "envelope_id": j.get("envelope_id", ""),
            "phase": j.get("phase", ""),
            "source": j.get("source", ""),
            "timestamp": j.get("timestamp", ""),
            "correlation_id": j.get("correlation_id", ""),
            "details": j.get("details", {}),
        }
        _label_environment(item)
        items.append(item)

    return {
        "ok": True,
        "traces": items,
        "recent_proofs": proof_files,
        "trace_count": len(traces),
        "journal_count": len(journal),
        "source_env": _detect_env(),
    }


@command_center_router.get("/summary")
def _summary(request: Request) -> dict[str, Any]:
    """Command center summary — answers all operational questions at once."""
    heartbeats = _load_workcell_heartbeats()
    packets = _load_work_packets(limit=100)
    blocked = _load_blocked_packets()
    pending_approvals = _load_approvals(status_filter="pending")
    journal = _load_journal_recent(50)

    active_agents = [h for h in heartbeats if h.get("status") == "active"]
    idle_agents = [h for h in heartbeats if h.get("status") == "idle"]

    completed = [j for j in journal if j.get("phase") == "EXECUTION_COMPLETED"]
    failed = [j for j in journal if j.get("phase") in ("EXECUTION_FAILED", "VERIFICATION_FAILED")]

    by_status: dict[str, int] = {}
    for p in packets:
        s = p.get("status", "unknown")
        by_status[s] = by_status.get(s, 0) + 1

    executing = [p for p in packets if p.get("status") in ("executing", "delegated")]
    next_packet = None
    ready = [p for p in packets if p.get("status") in ("approved", "ready_for_review", "planned")]
    if ready:
        ready.sort(key=lambda p: p.get("leverage_score", 0), reverse=True)
        next_packet = {
            "packet_id": ready[0].get("packet_id", ""),
            "title": ready[0].get("title", ""),
            "status": ready[0].get("status", ""),
            "leverage_score": ready[0].get("leverage_score", 0),
        }

    checkpoint_path = os.path.join(_DATA_ROOT, "workstation_state", "latest_checkpoint.json")
    checkpoint_detail: dict[str, Any] = {}
    continuity_state = "active"
    if os.path.exists(checkpoint_path):
        try:
            with open(checkpoint_path) as f:
                checkpoint_detail = json.load(f)
            continuity_state = checkpoint_detail.get(
                "continuity_state",
                checkpoint_detail.get("new_continuity_state", "active"),
            )
        except (json.JSONDecodeError, OSError):
            pass

    summary = {
        "ok": True,
        "checkpoint": {
            "last_checkpoint_id": checkpoint_detail.get("checkpoint_id", ""),
            "continuity_state": continuity_state,
            "lifecycle_mode": checkpoint_detail.get("lifecycle_mode", ""),
            "active_node": checkpoint_detail.get("active_node", ""),
            "active_environment": checkpoint_detail.get("active_environment", ""),
            "open_loops": checkpoint_detail.get("open_loops", []),
            "recommended_next_action": checkpoint_detail.get("recommended_next_action", ""),
            "transition_reason": checkpoint_detail.get("transition_reason", ""),
        },
        "what_is_happening": {
            "continuity_state": continuity_state,
            "active_agents": len(active_agents),
            "idle_agents": len(idle_agents),
            "total_agents": len(heartbeats),
            "executing_packets": len(executing),
        },
        "who_is_working": [
            {
                "agent_id": h.get("workcell_id", ""),
                "role": h.get("role", ""),
                "status": h.get("status", ""),
            }
            for h in heartbeats
        ],
        "what_is_blocked": {
            "count": len(blocked),
            "items": [
                {
                    "id": b.get("packet_id", ""),
                    "title": b.get("title", ""),
                    "blockers": b.get("blockers", []),
                }
                for b in blocked[:5]
            ],
        },
        "what_needs_approval": {
            "count": len(pending_approvals),
            "items": [
                {
                    "id": a.get("id", ""),
                    "title": a.get("title", ""),
                    "risk_level": a.get("risk_level", ""),
                }
                for a in pending_approvals[:5]
            ],
        },
        "what_finished": {
            "recent_completed": len(completed),
            "latest": completed[-1].get("details", {}).get("intent", "") if completed else "",
        },
        "what_failed": {
            "recent_failed": len(failed),
            "latest": failed[-1].get("details", {}).get("error", failed[-1].get("source", ""))
            if failed
            else "",
        },
        "what_should_resume_next": next_packet,
        "packets_by_status": by_status,
        "total_packets": len(packets),
        "source_env": _detect_env(),
        "node": os.uname().nodename,
    }
    return summary


# ── Mutation routes (governance-gated, operator-authenticated) ─────────

_VALID_SOURCE_TYPES = frozenset(
    {
        "jarvis_command",
        "cockpit_ui",
        "operator_manual",
        "cadence_auto",
    }
)

_MAX_INTENT_LEN = 2000
_MAX_END_STATE_LEN = 2000
_MAX_CONSTRAINTS = 20


def _get_operator_dep():
    if _require_operator:
        return Depends(_require_operator)
    return None


def _sanitize_text(text: str, max_len: int = 500) -> str:
    """Strip control characters and cap length for journal safety."""
    import re

    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    return cleaned[:max_len]


@command_center_router.post("/approvals/{approval_id}/decide")
async def _approval_decide(request: Request, approval_id: str) -> dict[str, Any]:
    """Approve or deny a pending approval. Operator-authenticated."""
    if _require_operator:
        await _require_operator(request)
    body = await request.json()
    decision = body.get("decision", "")
    if decision not in ("approved", "denied"):
        return {"ok": False, "error": "decision must be 'approved' or 'denied'"}
    decided_by = _sanitize_text(str(body.get("decided_by", "operator")), 100)

    def _do_decide():
        try:
            from substrate.organism.approval_store import ApprovalStore

            store = ApprovalStore()
            result = store.decide(approval_id, decision, decided_by=decided_by)
        except Exception as exc:
            logger.warning("approval decide failed: %s", exc)
            return str(exc), False

        if result is None:
            return f"approval {approval_id} not found", False

        _log_journal_entry(
            {
                "event": "approval_decided",
                "approval_id": _sanitize_text(approval_id, 100),
                "decision": decision,
                "decided_by": decided_by,
            }
        )
        return decision, True

    resp = governed_mutation(
        mutation_name="approval_decide",
        intent=f"{decision} approval {approval_id}",
        execute_fn=_do_decide,
        source="cockpit",
        metadata={"approval_id": approval_id, "decision": decision},
    )
    return resp.to_http_dict()


@command_center_router.post("/work-packets/create")
async def _work_packet_create(request: Request) -> dict[str, Any]:
    """Create a work packet from a Jarvis command draft. Operator-authenticated."""
    if _require_operator:
        await _require_operator(request)
    body = await request.json()
    user_intent = body.get("user_intent", "")
    if not user_intent:
        return {"ok": False, "error": "user_intent is required"}
    if len(user_intent) > _MAX_INTENT_LEN:
        return {"ok": False, "error": f"user_intent exceeds {_MAX_INTENT_LEN} chars"}

    desired_end_state = str(body.get("desired_end_state", ""))[:_MAX_END_STATE_LEN]
    constraints = body.get("constraints", [])
    if not isinstance(constraints, list):
        constraints = []
    constraints = constraints[:_MAX_CONSTRAINTS]
    source_type = body.get("source_type", "jarvis_command")
    if source_type not in _VALID_SOURCE_TYPES:
        source_type = "jarvis_command"
    source_id = _sanitize_text(str(body.get("source_id", "")), 200)

    def _do_create():
        try:
            from substrate.organism.work_packet import load_packets, persist_packets
            from substrate.organism.work_packet_engine import WorkPacketEngine

            engine = WorkPacketEngine()
            packet = engine.create_packet_from_intent(
                user_intent=user_intent,
                desired_end_state=desired_end_state,
                constraints=constraints,
                source_type=source_type,
                source_id=source_id,
            )
            all_packets = load_packets()
            all_packets.append(packet)
            persist_packets(all_packets)
        except Exception as exc:
            logger.warning("work packet create failed: %s", exc)
            return str(exc), False

        _log_journal_entry(
            {
                "event": "work_packet_created",
                "packet_id": packet.packet_id,
                "title": _sanitize_text(packet.title, 200),
                "risk_class": packet.risk_class,
                "source_type": source_type,
                "user_intent": _sanitize_text(user_intent, 200),
            }
        )
        return f"created packet {packet.packet_id}", True

    resp = governed_mutation(
        mutation_name="work_packet_create",
        intent=f"create work packet: {_sanitize_text(user_intent, 100)}",
        execute_fn=_do_create,
        source="cockpit",
        metadata={"source_type": source_type},
    )
    return resp.to_http_dict()


@command_center_router.post("/work-packets/decompose")
async def _work_packet_decompose(request: Request) -> dict[str, Any]:
    """Decompose a complex intent into a batch of linked work packets."""
    if _require_operator:
        await _require_operator(request)
    body = await request.json()
    user_intent = body.get("user_intent", "")
    if not user_intent:
        return {"ok": False, "error": "user_intent is required"}
    if len(user_intent) > _MAX_INTENT_LEN:
        return {"ok": False, "error": f"user_intent exceeds {_MAX_INTENT_LEN} chars"}

    desired_end_state = str(body.get("desired_end_state", ""))[:_MAX_END_STATE_LEN]
    constraints = body.get("constraints", [])
    if not isinstance(constraints, list):
        constraints = []
    constraints = constraints[:_MAX_CONSTRAINTS]
    idempotency_key = _sanitize_text(str(body.get("idempotency_key", "")), 100)

    def _do_decompose():
        try:
            from substrate.organism.work_packet_engine import WorkPacketEngine

            engine = WorkPacketEngine()
            result = engine.decompose_intent_to_batch(
                user_intent=user_intent,
                desired_end_state=desired_end_state,
                constraints=constraints,
                idempotency_key=idempotency_key,
            )
        except Exception as exc:
            logger.warning("work packet decompose failed: %s", exc)
            return str(exc), False

        _log_journal_entry(
            {
                "event": "work_packet_decomposed",
                "batch_id": result.get("batch_id", ""),
                "created_count": result.get("created_count", 0),
                "user_intent": _sanitize_text(user_intent, 200),
            }
        )
        return f"decomposed into {result.get('created_count', 0)} packets", True

    resp = governed_mutation(
        mutation_name="work_packet_create",
        intent=f"decompose intent: {_sanitize_text(user_intent, 100)}",
        execute_fn=_do_decompose,
        source="cockpit",
        metadata={"idempotency_key": idempotency_key},
    )
    return resp.to_http_dict()


def _log_journal_entry(entry: dict[str, Any]) -> None:
    """Append an entry to the execution journal."""
    entry.setdefault("ts", datetime.now(timezone.utc).isoformat())
    entry.setdefault("source", "command_center")
    try:
        os.makedirs(os.path.dirname(_JOURNAL_PATH), exist_ok=True)
        with open(_JOURNAL_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError as exc:
        logger.warning("journal write failed: %s", exc)
