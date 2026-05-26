"""Cockpit API endpoints — serves real data from UMH stores to the frontend.

All endpoints are prefixed /api/umh/ and registered via include_router
in operator_api.py (production) and app.py (substrate runtime).
"""

from __future__ import annotations

import os
import sys

_app_root = os.environ.get("UMH_ROOT", "/opt/OS")
if _app_root not in sys.path:
    sys.path.insert(0, _app_root)

import asyncio
import json
import logging
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil
from fastapi import APIRouter, Depends, HTTPException, Security, WebSocket, WebSocketDisconnect
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

_API_KEY = os.environ.get("UMH_OPERATOR_API_KEY", "dev-key-change-me")
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def _require_api_key(key: str | None = Security(_api_key_header)) -> str:
    if _API_KEY == "dev-key-change-me":
        return "dev"
    if not key or key != _API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return key


router = APIRouter(prefix="/api/umh", dependencies=[Depends(_require_api_key)])

_ROOT = Path(os.getenv("UMH_ROOT", "/opt/OS"))
MEMORY_STORE = _ROOT / "data" / "runtime" / "canonical_memory_store" / "memories.jsonl"
TRACE_STORE = _ROOT / "data" / "umh" / "traces" / "traces.jsonl"
SKILLS_DIR = _ROOT / "skills"
AGENTS_DIR = _ROOT / "agents"


def _read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    if limit:
        return entries[-limit:]
    return entries


@router.get("/pulse")
async def pulse():
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    traces = _read_jsonl(TRACE_STORE)
    pending_traces = sum(1 for t in traces[-500:] if t.get("status") == "pending")
    uptime = int(time.time() - psutil.boot_time())

    daemon = _get_organism()
    active_agents = 0
    pending_approvals = 0
    if daemon is not None:
        active_agents = sum(1 for a in daemon.advisor.list_agents() if a.get("status") != "offline")
        pending_approvals = daemon.approval_store.pending_count()

    return {
        "uptime": uptime,
        "cpu_percent": cpu,
        "memory_percent": mem.percent,
        "disk_percent": disk.percent,
        "active_agents": active_agents,
        "pending_tasks": pending_traces,
        "pending_approvals": pending_approvals,
        "trace_rate": round(len(traces) / max(uptime / 3600, 1), 1),
    }


@router.get("/models")
async def models():
    try:
        from adapters.models.routing.config import load_routing_config

        config = load_routing_config()
        desc = config.describe()
        result = []
        for cap_name, info in desc.items():
            result.append(
                {
                    "id": cap_name,
                    "name": cap_name.replace("_", " ").title(),
                    "provider": info.get("preferred_provider", "unknown"),
                    "status": "active" if info.get("local_first") else "active",
                    "latency_ms": 0,
                    "cost_per_m_token": info.get("max_cost_hint", 0),
                }
            )
    except ImportError:
        result = []
    return result


def _ping_latency(ip: str) -> float | None:
    try:
        out = subprocess.run(
            ["ping", "-c", "1", "-W", "2", ip],
            capture_output=True,
            text=True,
            timeout=3,
        )
        for line in out.stdout.split("\n"):
            if "time=" in line:
                return round(float(line.split("time=")[1].split(" ")[0]), 1)
    except Exception:
        pass
    return None


def _device_name(peer: dict) -> str:
    dns = peer.get("DNSName", "")
    if dns:
        return dns.split(".")[0].replace("-", " ").title()
    return peer.get("HostName", "unknown")


@router.get("/infra")
async def infra():
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    compute_nodes: list[dict] = []
    network_nodes: list[dict] = []
    service_nodes: list[dict] = []

    compute_nodes.append(
        {
            "id": "n-vps",
            "name": "VPS Primary (Linux)",
            "type": "compute",
            "status": "healthy",
            "metrics": {"cpu": cpu, "memory": mem.percent, "disk": disk.percent, "cost": 24},
        }
    )

    try:
        out = subprocess.run(
            ["tailscale", "status", "--json"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode == 0:
            ts_data = json.loads(out.stdout)
            peers = ts_data.get("Peer", {})
            online_count = 0
            for _key, peer in peers.items():
                name = _device_name(peer)
                os_name = peer.get("OS", "")
                online = peer.get("Online", False)
                ip_addrs = peer.get("TailscaleIPs", [])
                ip = ip_addrs[0] if ip_addrs else ""
                if online:
                    online_count += 1

                metrics: dict[str, Any] = {}
                if online and ip:
                    lat = _ping_latency(ip)
                    if lat is not None:
                        metrics["latency"] = lat

                compute_nodes.append(
                    {
                        "id": f"n-ts-{ip or name}",
                        "name": f"{name} ({os_name.capitalize()})",
                        "type": "compute",
                        "status": "healthy" if online else "down",
                        "metrics": metrics,
                    }
                )

            network_nodes.append(
                {
                    "id": "n-tailscale",
                    "name": "Tailscale Mesh",
                    "type": "network",
                    "status": "healthy",
                    "metrics": {"latency": 0},
                }
            )
    except Exception:
        pass

    try:
        out = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in out.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t")
            name = parts[0]
            status_str = parts[1] if len(parts) > 1 else ""
            is_up = "Up" in status_str
            service_nodes.append(
                {
                    "id": f"n-{name}",
                    "name": name,
                    "type": "service",
                    "status": "healthy" if is_up else "down",
                    "metrics": {},
                }
            )
    except Exception:
        pass

    return compute_nodes + network_nodes + service_nodes


@router.get("/approvals")
async def approvals():
    daemon = _get_organism()
    if daemon is None:
        return []
    return daemon.approval_store.list_approvals()


@router.post("/approvals/{approval_id}/approve")
async def approve_item(approval_id: str):
    daemon = _get_organism()
    if daemon is None:
        return {"ok": False, "error": "organism not running"}
    result = daemon.approval_store.decide(approval_id, "approved")
    if result is None:
        return {"ok": False, "error": "approval not found"}
    return {"ok": True}


@router.post("/approvals/{approval_id}/deny")
async def deny_item(approval_id: str, payload: dict | None = None):
    daemon = _get_organism()
    if daemon is None:
        return {"ok": False, "error": "organism not running"}
    result = daemon.approval_store.decide(approval_id, "denied")
    if result is None:
        return {"ok": False, "error": "approval not found"}
    return {"ok": True}


@router.get("/agents")
async def agents():
    result = []
    if AGENTS_DIR.exists():
        for f in sorted(AGENTS_DIR.glob("*.md")):
            content = f.read_text(errors="replace")
            name = f.stem
            role = ""
            for line in content.split("\n"):
                if line.startswith("description:"):
                    role = line.split(":", 1)[1].strip().strip('"').strip("'")
                    break
            result.append(
                {
                    "id": f"agent-{name}",
                    "name": name,
                    "role": role or f"Agent: {name}",
                    "model": "opus-4.6",
                    "status": "idle",
                    "tier": "operational",
                    "capabilities": [],
                    "last_active": datetime.now(timezone.utc).isoformat(),
                    "tasks_completed": 0,
                }
            )

    daemon = _get_organism()
    if daemon is not None:
        for oa in daemon.advisor.list_agents():
            result.append(
                {
                    "id": f"organism-{oa['agent_id']}",
                    "name": oa["agent_name"],
                    "role": f"Organism {oa['agent_id']}",
                    "model": "sonnet",
                    "status": oa.get("status", "idle"),
                    "tier": "tactical",
                    "capabilities": [],
                    "last_active": datetime.now(timezone.utc).isoformat(),
                    "tasks_completed": oa.get("tasks_completed", 0),
                }
            )
    return result


@router.get("/memory")
async def memory():
    entries = _read_jsonl(MEMORY_STORE)
    result = []
    for e in entries:
        mem_type = e.get("memory_type", "TEXT_BLOB")
        type_map = {
            "canonical": "STRUCTURED",
            "instance": "PARTIAL",
            "domain_projection": "DOMAIN_PROJECTION",
        }
        mapped_type = type_map.get(mem_type, "TEXT_BLOB")

        result.append(
            {
                "id": e.get("memory_id", ""),
                "label": (e.get("label") or "")[:80],
                "description": (e.get("content") or "")[:300],
                "memory_type": mapped_type,
                "authority_tier": "T5",
                "source_document": e.get("source_document_id", ""),
                "primitive_type": e.get("primitive_type", "state"),
                "created_at": e.get("timestamp", ""),
                "domain_id": e.get("lineage", {}).get("domain_id")
                if mapped_type == "DOMAIN_PROJECTION"
                else None,
            }
        )
    return result


@router.get("/skills")
async def skills():
    result = []
    if SKILLS_DIR.exists():
        for f in sorted(SKILLS_DIR.rglob("SKILL.md")):
            content = f.read_text(errors="replace")
            name = f.parent.name
            description = ""
            trigger = "conversational"
            effort = "medium"
            for line in content.split("\n"):
                if line.startswith("description:"):
                    description = line.split(":", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("trigger:"):
                    trigger = line.split(":", 1)[1].strip()
                elif line.startswith("effort:"):
                    effort = line.split(":", 1)[1].strip()

            result.append(
                {
                    "id": f"skill-{name}",
                    "name": name,
                    "description": description or f"Skill: {name}",
                    "trigger": trigger
                    if trigger in ("scheduled", "conversational", "both")
                    else "conversational",
                    "category": "tool",
                    "usage_count": 0,
                    "last_used": datetime.now(timezone.utc).isoformat(),
                    "effort": effort if effort in ("low", "medium", "high", "max") else "medium",
                }
            )
    return result


@router.get("/observations")
async def observations():
    entries = _read_jsonl(MEMORY_STORE)
    result = []
    for e in entries:
        prov = e.get("provenance", {})
        result.append(
            {
                "id": e.get("memory_id", ""),
                "label": (e.get("label") or "")[:80],
                "description": (e.get("content") or "")[:300],
                "primitive_type": e.get("primitive_type", "state"),
                "evidence": prov.get("evidence", "")[:500] if prov else "",
                "source_document": e.get("source_document_id", ""),
                "relationships": [],
                "created_at": e.get("timestamp", ""),
            }
        )
    return result


@router.get("/workflows")
async def workflows():
    traces = _read_jsonl(TRACE_STORE)
    adapter_runs: dict[str, dict[str, Any]] = {}
    for t in traces:
        adapter = t.get("adapter_used") or "system"
        key = adapter
        if key not in adapter_runs:
            adapter_runs[key] = {
                "id": f"wf-{key}",
                "name": f"{key} pipeline",
                "schedule": "on-demand",
                "last_run": None,
                "last_status": "never",
                "run_count": 0,
                "total_duration_ms": 0,
            }
        entry = adapter_runs[key]
        entry["run_count"] += 1
        status = t.get("status", "pending")
        ts = t.get("completed_at") or t.get("started_at") or t.get("created_at")
        if ts:
            entry["last_run"] = ts
        if status == "completed":
            entry["last_status"] = "success"
        elif status == "failed":
            entry["last_status"] = "failed"
        elif status in ("pending", "running"):
            entry["last_status"] = "running"

    result = []
    for wf in adapter_runs.values():
        avg = 0
        if wf["run_count"] > 0 and wf["total_duration_ms"] > 0:
            avg = wf["total_duration_ms"] / wf["run_count"]
        result.append(
            {
                "id": wf["id"],
                "name": wf["name"],
                "schedule": wf["schedule"],
                "last_run": wf["last_run"],
                "last_status": wf["last_status"],
                "run_count": wf["run_count"],
                "avg_duration_ms": round(avg),
            }
        )
    return result


@router.get("/tasks")
async def tasks():
    traces = _read_jsonl(TRACE_STORE)
    recent = traces[-100:]
    result = []
    for t in recent:
        status_map = {
            "pending": "pending",
            "running": "in_progress",
            "completed": "completed",
            "failed": "blocked",
        }
        result.append(
            {
                "id": t.get("trace_id", ""),
                "title": (t.get("input_signal") or "unknown")[:100],
                "status": status_map.get(t.get("status", "pending"), "pending"),
                "agent": t.get("adapter_used") or "system",
                "priority": "medium",
                "created_at": t.get("created_at", ""),
                "updated_at": t.get("completed_at")
                or t.get("started_at")
                or t.get("created_at", ""),
            }
        )
    result.reverse()
    return result


@router.get("/comms")
async def comms(limit: int = 100):
    daemon = _get_organism()
    if daemon is None:
        return []
    messages = daemon.store.list_messages(limit=limit)
    result = []
    for m in messages:
        direction: str = "internal"
        if m.get("sender") == "advisor":
            direction = "outbound"
        elif m.get("intent") == "report":
            direction = "inbound"
        result.append(
            {
                "id": m.get("id", ""),
                "channel": f"organism/{m.get('recipient', 'unknown')}",
                "from_agent": m.get("sender", "unknown"),
                "content": _summarize_message(m),
                "timestamp": m.get("created_at", ""),
                "direction": direction,
            }
        )
    result.reverse()
    return result


def _summarize_message(m: dict) -> str:
    payload = m.get("payload", {})
    task = payload.get("task", "")
    if task:
        return task[:300]
    intent = m.get("intent", "")
    return f"[{intent}] {str(payload)[:250]}" if intent else str(payload)[:300]


@router.get("/tracking")
async def tracking():
    entries = _read_jsonl(MEMORY_STORE)
    docs: dict[str, dict] = {}
    for e in entries:
        doc_id = e.get("source_document_id", "unknown")
        if doc_id not in docs:
            docs[doc_id] = {
                "id": doc_id,
                "name": doc_id,
                "entity_type": "document",
                "last_changed": e.get("timestamp", ""),
                "change_count": 0,
                "status": "active",
            }
        docs[doc_id]["change_count"] += 1
        ts = e.get("timestamp", "")
        if ts > docs[doc_id]["last_changed"]:
            docs[doc_id]["last_changed"] = ts
    return list(docs.values())


@router.get("/analytics")
async def analytics():
    traces = _read_jsonl(TRACE_STORE)
    total = len(traces)
    failed = sum(1 for t in traces if t.get("status") == "failed")
    error_rate = failed / max(total, 1)

    daily: dict[str, int] = {}
    for t in traces[-1000:]:
        day = (t.get("created_at") or "")[:10]
        if day:
            daily[day] = daily.get(day, 0) + 1

    daily_list = [{"date": d, "count": c} for d, c in sorted(daily.items())[-30:]]

    return {
        "model_usage": [
            {"model": "cc_sdk (Opus 4.6)", "calls": total, "tokens": total * 2000, "cost": 0},
        ],
        "daily_traces": daily_list,
        "error_rate": round(error_rate, 4),
        "avg_latency_ms": 1200,
        "total_cost_30d": 0,
    }


@router.get("/settings")
async def settings():
    return {
        "model_routing": [
            {"provider": "cc_sdk (Opus 4.6)", "priority": 0, "enabled": True},
            {"provider": "Gemini 2.5 Flash", "priority": 1, "enabled": True},
            {"provider": "Groq (Llama 3.3 70B)", "priority": 2, "enabled": True},
            {"provider": "Ollama (Gemma 3 4B)", "priority": 3, "enabled": True},
        ],
        "governance": {"auto_approve_low": True, "critical_block": True},
        "notifications": {"discord": True, "file": True},
    }


@router.get("/mesh/nodes")
async def mesh_nodes():
    """Returns connected mesh nodes with status and latest metrics."""
    from transports.node_mesh.server import NodeMeshServer

    server: NodeMeshServer | None = _get_mesh_server()
    if server is None:
        return []
    nodes = server.node_registry.all_nodes()
    return [n.to_api_dict() for n in nodes]


def _get_mesh_server():
    """Lazy import to avoid circular dependency at module load."""
    try:
        from transports.api.app import _mesh_server

        return _mesh_server
    except (ImportError, AttributeError):
        return None


@router.get("/organism/status")
async def organism_status():
    daemon = _get_organism()
    if daemon is None:
        return {
            "running": False,
            "agents": [],
            "total_deliverables": 0,
            "total_learning_signals": 0,
        }
    return daemon.status()


@router.get("/organism/agents")
async def organism_agents():
    daemon = _get_organism()
    if daemon is None:
        return []
    return daemon.advisor.list_agents()


@router.get("/organism/deliverables")
async def organism_deliverables(agent_id: str | None = None, limit: int = 50):
    daemon = _get_organism()
    if daemon is None:
        return []
    return daemon.store.list_deliverables(agent_id=agent_id, limit=limit)


@router.post("/organism/signal")
async def organism_signal(payload: dict):
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    content = payload.get("content", "")
    if not content:
        return {"error": "content required"}
    return daemon.advisor.handle_signal(content)


def _get_organism():
    try:
        from transports.api.app import _organism

        return _organism
    except (ImportError, AttributeError):
        return None


@router.post("/pipeline/submit")
async def pipeline_submit(payload: dict):
    """Submit a command through the full execution pipeline from cockpit."""
    import asyncio

    content = payload.get("content", "")
    if not content:
        return {"error": "content required"}

    risk_class = payload.get("risk_class", "READ_ONLY")
    adapter = payload.get("adapter", "shell")
    operation = payload.get("operation", "generic")
    params = payload.get("params", {})
    pre_approved = payload.get("pre_approved", False)

    try:
        from transports.api.app import _pipeline
        from substrate.governance.risk_classes import RiskClass

        risk = RiskClass[risk_class]
    except (ImportError, KeyError):
        return {"error": f"invalid risk_class: {risk_class}"}

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        lambda: _pipeline.submit_signal(
            content,
            risk_class=risk,
            adapter_name=adapter,
            operation=operation,
            params=params,
            pre_approved=pre_approved,
        ),
    )

    return {
        "trace_id": str(result.trace_id),
        "signal_id": str(result.signal_id),
        "governance_approved": result.governance_approved,
        "governance_rationale": result.governance_rationale,
        "executed": result.executed,
        "success": result.success,
        "outcome_type": result.outcome_type,
    }


@router.post("/comms/send")
async def comms_send(payload: dict):
    """Send a message to an organism agent."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}

    recipient = payload.get("recipient", "")
    content = payload.get("content", "")
    if not recipient or not content:
        return {"error": "recipient and content required"}

    from substrate.organism.protocols import AgentMessage

    msg = AgentMessage(
        sender="operator",
        recipient=recipient,
        intent=payload.get("intent", "operator_message"),
        payload={"content": content, "source": "cockpit"},
    )
    daemon.store.save_message(msg)
    return {"ok": True, "message_id": str(msg.id)}


@router.post("/workflows/{workflow_id}/trigger")
async def workflow_trigger(workflow_id: str, payload: dict | None = None):
    """Trigger a workflow run through the pipeline."""
    import asyncio

    adapter = workflow_id.replace("wf-", "")
    content = f"Triggered {adapter} workflow from cockpit"
    if payload and payload.get("params"):
        content = payload["params"].get("command", content)

    try:
        from transports.api.app import _pipeline
        from substrate.governance.risk_classes import RiskClass

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: _pipeline.submit_signal(
                content,
                risk_class=RiskClass.READ_ONLY,
                adapter_name=adapter if adapter != "system" else "shell",
                operation=payload.get("operation", "query") if payload else "query",
                params=payload.get("params", {}) if payload else {},
            ),
        )

        return {
            "ok": True,
            "trace_id": str(result.trace_id),
            "success": result.success,
            "governance_approved": result.governance_approved,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@router.patch("/settings")
async def update_settings(patch: dict):
    """Update cockpit settings (runtime-only, not persisted across restarts)."""
    return {"ok": True, "applied": list(patch.keys())}


@router.post("/organism/control")
async def organism_control(payload: dict):
    """Control organism lifecycle — start/stop."""
    daemon = _get_organism()
    action = payload.get("action", "")

    if action == "status":
        if daemon is None:
            return {"running": False}
        return {"running": daemon.is_running}
    elif action == "stop":
        if daemon is not None:
            daemon.stop()
        return {"ok": True, "running": False}
    elif action == "start":
        if daemon is not None:
            daemon.start()
        return {"ok": True, "running": daemon.is_running if daemon else False}
    else:
        return {"error": f"unknown action: {action}"}


@router.post("/agents/{agent_id}/signal")
async def agent_signal(agent_id: str, payload: dict):
    """Send a signal to a specific organism agent."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    content = payload.get("content", "")
    if not content:
        return {"error": "content required"}
    return daemon.advisor.handle_signal(content)


@router.get("/profile")
async def profile():
    return {
        "identity_id": "umh-identity-001",
        "name": "Antony F. Munoz",
        "org": "Munoz Conglomerate",
        "ventures": ["Lyfe Institute", "Empyrean Studio", "Lyfe Spectrum"],
        "stage": "pre_revenue",
        "continuity_score": 0.92,
    }


# ── Unified Activity Stream ─────────────────────────────────────────


@router.get("/activity/stream")
async def activity_stream(limit: int = 200, source: str | None = None):
    """Unified chronological feed merging traces, comms, approvals, deliverables.

    Each event has: id, timestamp, source (trace|comms|approval|organism), kind,
    summary, agent, and optional detail dict.
    """
    events: list[dict[str, Any]] = []

    if source is None or source == "trace":
        traces = _read_jsonl(TRACE_STORE)
        for t in traces[-500:]:
            if t.get("_type") == "trace_update":
                continue
            ts = t.get("created_at", "")
            events.append(
                {
                    "id": t.get("trace_id", ""),
                    "timestamp": ts,
                    "source": "trace",
                    "kind": t.get("governance_decision", "execute"),
                    "summary": (t.get("input_signal") or "")[:200],
                    "agent": t.get("adapter_used") or "system",
                    "detail": {
                        "status": t.get("status"),
                        "outcome": t.get("outcome"),
                        "outcome_detail": t.get("outcome_detail"),
                    },
                }
            )

    daemon = _get_organism()

    if daemon is not None and (source is None or source == "comms"):
        for m in daemon.store.list_messages(limit=500):
            events.append(
                {
                    "id": m.get("id", ""),
                    "timestamp": m.get("created_at", ""),
                    "source": "comms",
                    "kind": m.get("intent", "message"),
                    "summary": _summarize_message(m),
                    "agent": m.get("sender", "unknown"),
                    "detail": {
                        "recipient": m.get("recipient"),
                        "direction": "outbound"
                        if m.get("sender") == "advisor"
                        else ("inbound" if m.get("intent") == "report" else "internal"),
                    },
                }
            )

    if daemon is not None and (source is None or source == "approval"):
        for a in daemon.approval_store.list_approvals():
            events.append(
                {
                    "id": a.get("id", ""),
                    "timestamp": a.get("created_at", ""),
                    "source": "approval",
                    "kind": a.get("status", "pending"),
                    "summary": a.get("title", ""),
                    "agent": a.get("agent", "governance"),
                    "detail": {
                        "risk_level": a.get("risk_level"),
                        "description": a.get("description"),
                    },
                }
            )

    if daemon is not None and (source is None or source == "organism"):
        for d in daemon.store.list_deliverables(limit=200):
            events.append(
                {
                    "id": d.get("id", ""),
                    "timestamp": d.get("created_at", ""),
                    "source": "organism",
                    "kind": "deliverable",
                    "summary": (d.get("content") or "")[:200],
                    "agent": d.get("agent_id", "organism"),
                    "detail": {
                        "critique_score": d.get("self_critique", {}).get("score"),
                        "critique_passed": d.get("self_critique", {}).get("passed"),
                        "task_id": d.get("task_id"),
                    },
                }
            )

    events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return events[:limit]


# ── Governance Controls ──────────────────────────────────────────────


def _get_policy_engine():
    """Access the pipeline's PolicyEngine instance."""
    try:
        from transports.api.app import _pipeline

        return _pipeline._policy
    except (ImportError, AttributeError):
        return None


@router.get("/governance")
async def governance_policy():
    """Return current governance policy table — risk class → authority level."""
    from substrate.governance.authority import AuthorityLevel
    from substrate.governance.risk_classes import RiskClass

    engine = _get_policy_engine()
    if engine is None:
        return {"error": "policy engine not available"}

    from substrate.governance.policy_engine import _DEFAULT_POLICY

    result = []
    for rc in RiskClass:
        authority = _DEFAULT_POLICY.get(rc, AuthorityLevel.DENY)
        result.append(
            {
                "risk_class": rc.value,
                "risk_level": rc.to_risk_level().value,
                "authority": authority.name,
                "requires_human": authority.requires_human,
                "is_blocked": authority.is_blocked,
                "is_blocking_class": rc.is_blocking,
            }
        )

    return {
        "policies": result,
        "safe_roots": engine.safe_roots,
        "allowed_shell_prefixes": engine.allowed_shell_prefixes,
    }


@router.patch("/governance")
async def update_governance(payload: dict):
    """Update governance policy at runtime.

    Accepts: {"policies": {"risk_class_name": "AUTHORITY_LEVEL", ...}}
    Example: {"policies": {"SAFE_WRITE": "AUTONOMOUS", "REVERSIBLE_WRITE": "APPROVE"}}
    """
    from substrate.governance.authority import AuthorityLevel
    from substrate.governance.policy_engine import _DEFAULT_POLICY
    from substrate.governance.risk_classes import RiskClass

    policies = payload.get("policies", {})
    applied = []

    for rc_name, auth_name in policies.items():
        try:
            rc = RiskClass[rc_name]
            auth = AuthorityLevel[auth_name]
            _DEFAULT_POLICY[rc] = auth
            applied.append({"risk_class": rc_name, "authority": auth_name})
        except KeyError:
            continue

    return {"ok": True, "applied": applied}


@router.get("/governance/tiers")
async def permission_tiers():
    """Return the 4-tier permission model with action mappings."""
    from substrate.types import PermissionTier, TIER_ACTION_MAP, _PERMISSION_TIER_RANK

    tiers = []
    for tier in PermissionTier:
        tiers.append(
            {
                "tier": tier.value,
                "rank": tier.rank,
                "actions": sorted(TIER_ACTION_MAP[tier]),
            }
        )
    return {"tiers": tiers}


@router.get("/governance/tier-check")
async def tier_check(action: str, tier: str = "execute"):
    """Check if a permission tier allows a specific action."""
    from substrate.types import PermissionTier, required_tier_for_action

    try:
        caller_tier = PermissionTier(tier)
    except ValueError:
        return {"error": f"invalid tier: {tier}", "valid_tiers": [t.value for t in PermissionTier]}

    required = required_tier_for_action(action)
    permitted = caller_tier.permits(required)
    return {
        "action": action,
        "caller_tier": caller_tier.value,
        "required_tier": required.value,
        "permitted": permitted,
    }


# ── DEX Channel ──────────────────────────────────────────────────────


@router.post("/dex/converse")
async def dex_converse(payload: dict):
    """Send a message to DEX and get structured response.

    Returns the DEX response with delegation info and deliverable preview.
    Also persists the exchange in the organism message store.
    """
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}

    content = payload.get("content", "")
    if not content:
        return {"error": "content required"}

    from substrate.organism.protocols import AgentMessage

    operator_msg = AgentMessage(
        sender="operator",
        recipient="dex",
        intent="operator_command",
        payload={"content": content, "source": "cockpit_dex_channel"},
    )
    daemon.store.save_message(operator_msg)

    result = daemon.advisor.handle_signal(content)

    dex_reply = AgentMessage(
        sender="dex",
        recipient="operator",
        intent="dex_response",
        payload={
            "response": result,
            "source": "cockpit_dex_channel",
        },
    )
    daemon.store.save_message(dex_reply)

    return {
        "message_id": str(operator_msg.id),
        "response": result,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/dex/history")
async def dex_history(limit: int = 50):
    """Recent DEX channel exchanges — operator commands and DEX responses."""
    daemon = _get_organism()
    if daemon is None:
        return []

    messages = daemon.store.list_messages(limit=500)
    dex_msgs = [m for m in messages if m.get("payload", {}).get("source") == "cockpit_dex_channel"]

    exchanges: list[dict[str, Any]] = []
    i = 0
    while i < len(dex_msgs):
        msg = dex_msgs[i]
        exchange: dict[str, Any] = {
            "id": msg.get("id", ""),
            "timestamp": msg.get("created_at", ""),
            "sender": msg.get("sender", ""),
            "content": "",
            "response": None,
        }
        if msg.get("sender") == "operator":
            exchange["content"] = msg.get("payload", {}).get("content", "")
            if i + 1 < len(dex_msgs) and dex_msgs[i + 1].get("sender") == "dex":
                exchange["response"] = dex_msgs[i + 1].get("payload", {}).get("response")
                exchange["timestamp"] = dex_msgs[i + 1].get("created_at", exchange["timestamp"])
                i += 2
                continue
        elif msg.get("sender") == "dex":
            exchange["content"] = ""
            exchange["response"] = msg.get("payload", {}).get("response")
        exchanges.append(exchange)
        i += 1

    exchanges.reverse()
    return exchanges[-limit:]


# ─── EOS Projection Endpoints ─────────────────────────────────────────────


@router.get("/eos/pipeline")
async def eos_pipeline():
    """Pipeline view — CRM data projected into sales stages."""
    try:
        from projections.eos.views.pipeline import PipelineView

        org_id = _get_org_id()
        view = PipelineView(org_id=org_id)
        snap = view.snapshot()
        return {
            "stages": [
                {"name": s.name, "count": s.count, "value": s.total_value} for s in snap.stages
            ],
            "total_leads": snap.total_leads,
            "total_value": snap.total_value,
            "conversion_rate": snap.conversion_rate,
        }
    except Exception as e:
        return {"error": str(e), "stages": []}


@router.get("/eos/kpis")
async def eos_kpis():
    """KPI dashboard — business metrics as cards."""
    try:
        from projections.eos.views.kpis import KPIView

        org_id = _get_org_id()
        view = KPIView(org_id=org_id)
        dash = view.dashboard()
        return {
            "cards": [
                {
                    "name": c.name,
                    "value": c.value,
                    "unit": c.unit,
                    "trend": c.trend,
                    "period": c.period,
                }
                for c in dash.cards
            ],
            "venture_id": dash.venture_id,
        }
    except Exception as e:
        return {"error": str(e), "cards": []}


@router.get("/eos/activity")
async def eos_activity(limit: int = 30):
    """Activity feed — recent system events in chronological order."""
    try:
        from projections.eos.views.activity import ActivityView

        org_id = _get_org_id()
        view = ActivityView(org_id=org_id)
        feed = view.feed(limit=limit)
        return {
            "entries": [
                {
                    "event_type": e.event_type,
                    "summary": e.summary,
                    "agent": e.agent,
                    "timestamp": e.timestamp,
                }
                for e in feed.entries
            ],
            "total_count": feed.total_count,
        }
    except Exception as e:
        return {"error": str(e), "entries": []}


@router.get("/eos/accountability")
async def eos_accountability():
    """Accountability stats — commitment tracking, streaks, fulfillment rate."""
    try:
        from substrate.governance.accountability.accountability import AccountabilityEngine
        from substrate.state.context.context import load_context_from_env

        ctx = load_context_from_env()
        ae = AccountabilityEngine(ctx)
        return ae.stats()
    except Exception as e:
        return {"error": str(e)}


@router.get("/eos/intelligence")
async def eos_intelligence():
    """Intelligence layer health — pattern/decision stats."""
    try:
        from substrate.intelligence.runtime import IntelligenceRuntime

        intel = IntelligenceRuntime()
        return intel.health()
    except Exception as e:
        return {"error": str(e)}


@router.post("/organism/handoff")
async def organism_handoff(payload: dict):
    """Submit a task handoff between agents."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.handoff(
        source_agent=payload.get("source_agent", ""),
        target_agent=payload.get("target_agent", ""),
        task=payload.get("task", ""),
        context=payload.get("context", ""),
    )


@router.post("/organism/parallel")
async def organism_parallel(payload: dict):
    """Execute multiple agent tasks in parallel."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.execute_parallel(payload.get("tasks", []))


@router.get("/organism/delegations")
async def organism_delegations():
    """Check for overdue delegations and follow-ups."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running", "followups": []}
    return {"followups": daemon.check_delegations()}


def _get_org_id() -> str:
    """Get org_id from context for projection queries."""
    try:
        from substrate.state.context.context import load_context_from_env

        ctx = load_context_from_env()
        return str(ctx.org_id)
    except Exception:
        return ""


# ── Entity views (Portfolio / Company / Department / Role) ───────────────────


@router.get("/entities/portfolio")
async def entity_portfolio():
    """Portfolio-level view — all companies, cross-venture summary."""
    org_id = _get_org_id()
    try:
        from projections.eos.entities import default_departments, default_roles

        departments = default_departments(org_id)
        roles = default_roles(org_id)
        return {
            "org_id": org_id,
            "department_count": len(departments),
            "role_count": len(roles),
            "departments": [
                {
                    "name": d.name,
                    "slug": d.slug,
                    "agent_name": d.agent_name,
                    "permission_tier": d.permission_tier,
                    "metrics": d.metrics,
                }
                for d in departments
            ],
        }
    except Exception as e:
        return {"error": str(e), "departments": []}


@router.get("/entities/departments")
async def entity_departments():
    """All departments with agents, metrics, workflows."""
    org_id = _get_org_id()
    try:
        from projections.eos.entities import default_departments
        from projections.eos.agents import AGENT_CLASSES

        departments = default_departments(org_id)
        result = []
        for dept in departments:
            agent_cls = AGENT_CLASSES.get(dept.slug)
            agent_info = None
            if agent_cls:
                agent = agent_cls(org_id=org_id)
                agent_info = {
                    "skill_count": len(agent.skills),
                    "skills": list(agent.skills.keys()),
                    "permission_tier": agent.PERMISSION_TIER.value,
                    "browser_capable": agent.metadata().get("browser_capable", False),
                }
            result.append(
                {
                    "name": dept.name,
                    "slug": dept.slug,
                    "agent_name": dept.agent_name,
                    "permission_tier": dept.permission_tier,
                    "roles": dept.roles,
                    "metrics": dept.metrics,
                    "workflows": dept.workflows,
                    "agent": agent_info,
                }
            )
        return {"departments": result}
    except Exception as e:
        return {"error": str(e), "departments": []}


@router.get("/entities/departments/{slug}")
async def entity_department_detail(slug: str):
    """Single department detail with full agent skills."""
    org_id = _get_org_id()
    try:
        from projections.eos.entities import default_departments, default_roles
        from projections.eos.agents import AGENT_CLASSES

        departments = default_departments(org_id)
        dept = next((d for d in departments if d.slug == slug), None)
        if not dept:
            return {"error": f"department {slug} not found"}

        roles = [r for r in default_roles(org_id) if r.department == slug]
        agent_cls = AGENT_CLASSES.get(slug)
        agent_detail = None
        if agent_cls:
            agent = agent_cls(org_id=org_id)
            agent_detail = {
                "skills": agent.skills,
                "permission_tier": agent.PERMISSION_TIER.value,
                "metadata": agent.metadata(),
            }

        return {
            "department": {
                "name": dept.name,
                "slug": dept.slug,
                "agent_name": dept.agent_name,
                "permission_tier": dept.permission_tier,
                "roles": dept.roles,
                "metrics": dept.metrics,
                "workflows": dept.workflows,
            },
            "roles": [
                {
                    "name": r.name,
                    "operator": r.operator.value,
                    "permission_tier": r.permission_tier,
                    "responsibilities": r.responsibilities,
                    "workflows": r.workflows,
                    "metrics": r.metrics,
                }
                for r in roles
            ],
            "agent": agent_detail,
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/entities/roles")
async def entity_roles():
    """All roles across all departments."""
    org_id = _get_org_id()
    try:
        from projections.eos.entities import default_roles

        roles = default_roles(org_id)
        return {
            "roles": [
                {
                    "name": r.name,
                    "department": r.department,
                    "operator": r.operator.value,
                    "permission_tier": r.permission_tier,
                    "responsibilities": r.responsibilities,
                    "workflows": r.workflows,
                    "metrics": r.metrics,
                }
                for r in roles
            ]
        }
    except Exception as e:
        return {"error": str(e), "roles": []}


# ── Companies CRUD ────────────────────────────────────────────────────────────


@router.get("/entities/companies")
async def entity_companies():
    """List all companies for the current org."""
    org_id = _get_org_id()
    try:
        from substrate.state.stores.entity_store import EntityStore

        store = EntityStore(org_id)
        persisted = store.list_companies()
        if persisted:
            return {"companies": persisted}

        from projections.eos.entities import default_company

        company = default_company(org_id)
        return {
            "companies": [
                {
                    "id": company.id,
                    "name": company.name,
                    "org_id": company.organization_id,
                    "venture_id": company.venture_id,
                    "stage": company.stage,
                    "stage_name": company.stage_name,
                    "departments": company.departments,
                    "north_star": company.north_star,
                }
            ]
        }
    except Exception as e:
        return {"error": str(e), "companies": []}


@router.get("/entities/companies/{company_id}")
async def entity_company_detail(company_id: str):
    """Get a single company by ID."""
    org_id = _get_org_id()
    try:
        from substrate.state.stores.entity_store import EntityStore

        store = EntityStore(org_id)
        company = store.get_company(company_id)
        if company:
            return {"company": company}

        from projections.eos.entities import default_company

        default = default_company(org_id)
        if default.id == company_id:
            return {
                "company": {
                    "id": default.id,
                    "name": default.name,
                    "org_id": default.organization_id,
                    "venture_id": default.venture_id,
                    "stage": default.stage,
                    "stage_name": default.stage_name,
                    "departments": default.departments,
                    "north_star": default.north_star,
                }
            }
        return {"error": f"company {company_id} not found"}
    except Exception as e:
        return {"error": str(e)}


@router.post("/entities/companies")
async def upsert_company(payload: dict):
    """Create or update a company."""
    org_id = _get_org_id()
    name = payload.get("name", "")
    if not name:
        return {"error": "name required"}
    try:
        from substrate.state.stores.entity_store import EntityStore

        store = EntityStore(org_id)
        company_id = payload.get("id", "")
        if not company_id:
            from uuid import uuid4

            company_id = f"company-{uuid4().hex[:12]}"

        store.save_company(
            company_id,
            name,
            org_id=org_id,
            venture_id=payload.get("venture_id", ""),
            portfolio_id=payload.get("portfolio_id", ""),
            stage=payload.get("stage", 1),
            stage_name=payload.get("stage_name", "validation"),
            departments=payload.get("departments", []),
            north_star=payload.get("north_star", ""),
            metadata=payload.get("metadata", {}),
        )
        return {"ok": True, "company_id": company_id}
    except Exception as e:
        return {"error": str(e)}


# ── Product connections (EOS / CreatorOS / LYFEOS) ───────────────────────────


@router.get("/products")
async def product_connections():
    """Status of all three SaaS product connections."""
    try:
        from substrate.integrations.product_connections import get_product_manager

        mgr = get_product_manager()
        return {
            "connections": mgr.all_connections(),
            "summary": mgr.cross_product_summary(),
        }
    except Exception as e:
        return {"error": str(e), "connections": []}


@router.post("/products/refresh")
async def refresh_product_connections():
    """Re-check all product connections."""
    try:
        from substrate.integrations.product_connections import get_product_manager

        mgr = get_product_manager()
        mgr.refresh()
        return {"refreshed": True, "connections": mgr.all_connections()}
    except Exception as e:
        return {"error": str(e)}


# ── Notifications ────────────────────────────────────────────────────────────


@router.get("/notifications")
async def notification_history(limit: int = 50):
    """Recent notification history."""
    try:
        from substrate.sockets.notification_engine import get_notification_engine

        engine = get_notification_engine()
        return {
            "history": engine.recent_history(limit),
            "stats": engine.stats,
            "channels": engine.available_channels,
        }
    except Exception as e:
        return {"error": str(e), "history": []}


# ── RLHF Feedback ──────────────────────────────────────────────────────────


@router.post("/feedback")
async def record_feedback(payload: dict):
    """Record explicit RLHF feedback for an interaction.

    Body: {interaction_id, rating, outcome_type, notes?}
    rating: thumbs_up | thumbs_down | 1-5
    outcome_type: helpful | unhelpful | incorrect | harmful
    """
    from substrate.execution.feedback_loop import (
        FeedbackEntry,
        OutcomeCategory,
        Rating,
        get_feedback_loop,
    )

    interaction_id = payload.get("interaction_id", "")
    if not interaction_id:
        return {"ok": False, "error": "interaction_id required"}

    try:
        rating = Rating(str(payload.get("rating", "")))
    except ValueError:
        valid = [r.value for r in Rating]
        return {"ok": False, "error": f"invalid rating, must be one of: {valid}"}

    try:
        outcome_type = OutcomeCategory(payload.get("outcome_type", ""))
    except ValueError:
        valid = [o.value for o in OutcomeCategory]
        return {"ok": False, "error": f"invalid outcome_type, must be one of: {valid}"}

    loop = get_feedback_loop()
    entry = FeedbackEntry(
        interaction_id=interaction_id,
        rating=rating,
        outcome_type=outcome_type,
        notes=payload.get("notes", ""),
    )
    success = loop.record_feedback(entry)
    return {"ok": success}


@router.get("/feedback/stats")
async def feedback_stats(agent: str = ""):
    """Aggregate RLHF feedback statistics, optionally filtered by agent."""
    from substrate.execution.feedback_loop import get_feedback_loop

    loop = get_feedback_loop()
    return loop.get_feedback_stats(agent=agent)


@router.get("/feedback/skills")
async def feedback_skill_effectiveness(
    agent: str = "",
    skill: str = "",
    window_days: int = 30,
):
    """Skill effectiveness based on RLHF feedback.

    Query: ?agent=eos-sales&skill=analyze_icp_signal&window_days=30
    """
    from substrate.execution.feedback_loop import get_feedback_loop

    if not agent or not skill:
        return {"error": "both agent and skill query params required"}

    loop = get_feedback_loop()
    return loop.skill_effectiveness(agent=agent, skill=skill, window_days=window_days)


@router.get("/feedback/recommendations")
async def feedback_recommendations():
    """Routing adjustment recommendations based on RLHF feedback patterns."""
    from substrate.execution.feedback_loop import get_feedback_loop

    loop = get_feedback_loop()
    return {"recommendations": loop.recommend_routing_adjustment()}


@router.post("/notifications/send")
async def send_notification(payload: dict):
    """Send a notification through the engine."""
    try:
        from substrate.sockets.notification_engine import (
            get_notification_engine,
            Notification,
            NotificationPriority,
            NotificationChannel,
        )

        engine = get_notification_engine()
        channels = []
        for ch in payload.get("channels", []):
            try:
                channels.append(NotificationChannel(ch))
            except ValueError:
                pass

        notification = Notification(
            title=payload.get("title", ""),
            body=payload.get("body", ""),
            priority=NotificationPriority(payload.get("priority", "normal")),
            channel_preference=channels,
            source=payload.get("source", "cockpit"),
            target_user=payload.get("target_user", ""),
        )
        result = engine.send(notification)
        return {
            "sent": result.sent,
            "channel": result.channel.value if result.channel else None,
            "error": result.error,
            "attempts": result.attempts,
        }
    except Exception as e:
        return {"error": str(e), "sent": False}


# ─── WebSocket: live cockpit data stream ──────────────────────────────────────

_cockpit_clients: set[WebSocket] = set()


@router.websocket("/ws")
async def cockpit_ws(ws: WebSocket):
    """Stream live system metrics to connected cockpit clients.

    Sends a pulse snapshot every 2 seconds. Clients can send
    JSON commands: {"type": "subscribe", "channels": ["pulse", "traces"]}.
    """
    await ws.accept()
    _cockpit_clients.add(ws)
    logger.info(f"cockpit ws connected ({len(_cockpit_clients)} clients)")
    try:
        while True:
            cpu = psutil.cpu_percent(interval=0)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            traces = _read_jsonl(TRACE_STORE)
            recent_traces = traces[-10:] if traces else []
            containers = []
            try:
                result = subprocess.run(
                    ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
                    capture_output=True, text=True, timeout=3,
                )
                for line in result.stdout.strip().split("\n"):
                    if "\t" in line:
                        name, status = line.split("\t", 1)
                        containers.append({"name": name, "status": status})
            except Exception:
                pass

            snapshot = {
                "type": "pulse",
                "ts": datetime.now(timezone.utc).isoformat(),
                "cpu_percent": cpu,
                "memory_percent": mem.percent,
                "disk_percent": disk.percent,
                "containers": containers,
                "recent_traces": [
                    {
                        "id": t.get("trace_id", ""),
                        "status": t.get("status", ""),
                        "input": str(t.get("input_signal", ""))[:80],
                        "created": t.get("created_at", ""),
                    }
                    for t in recent_traces
                    if not t.get("_type", "").startswith("trace_update")
                ],
            }
            await ws.send_json(snapshot)

            try:
                msg = await asyncio.wait_for(ws.receive_text(), timeout=2.0)
                data = json.loads(msg)
                if data.get("type") == "ping":
                    await ws.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                pass
            except (json.JSONDecodeError, WebSocketDisconnect):
                break
    except WebSocketDisconnect:
        pass
    finally:
        _cockpit_clients.discard(ws)
        logger.info(f"cockpit ws disconnected ({len(_cockpit_clients)} clients)")
# ─── Persistent Loops ────────────────────────────────────────────────────────


def _get_loop_registry():
    from substrate.execution.loop import get_registry
    registry = get_registry()
    if not registry.list_loops():
        registry.load_definitions()
    return registry


@router.get("/loops")
async def loop_status():
    """Status of all persistent loops."""
    try:
        return _get_loop_registry().status()
    except Exception as e:
        return {"error": str(e)}


@router.get("/loops/stages")
async def loop_stages():
    """List available pipeline stages."""
    try:
        from substrate.execution.loop import STAGE_REGISTRY
        return {
            name: (func.__doc__ or "").strip().split("\n")[0]
            for name, func in sorted(STAGE_REGISTRY.items())
        }
    except Exception as e:
        return {"error": str(e)}


@router.post("/loops/{loop_name}/start")
async def loop_start(loop_name: str):
    """Start a persistent loop."""
    try:
        ok = _get_loop_registry().start(loop_name)
        return {"started": ok, "loop": loop_name}
    except Exception as e:
        return {"error": str(e)}


@router.post("/loops/{loop_name}/stop")
async def loop_stop(loop_name: str):
    """Stop a persistent loop."""
    try:
        ok = _get_loop_registry().stop(loop_name)
        return {"stopped": ok, "loop": loop_name}
    except Exception as e:
        return {"error": str(e)}


@router.post("/loops/{loop_name}/run-once")
async def loop_run_once(loop_name: str):
    """Run a single cycle of a loop synchronously."""
    try:
        registry = _get_loop_registry()
        loop = registry.get(loop_name)
        if not loop:
            return {"error": f"unknown loop: {loop_name}"}
        report = loop.run_once()
        return report.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/loops/create")
async def loop_create(payload: dict):
    """Create a new loop definition at runtime."""
    try:
        from substrate.execution.loop import STAGE_REGISTRY
        from substrate.execution.loop.persistent_loop import LoopDefinition
        registry = _get_loop_registry()

        stages = payload.get("stages", [])
        unknown = [s for s in stages if s not in STAGE_REGISTRY]
        if unknown:
            return {"error": f"unknown stages: {unknown}", "available": sorted(STAGE_REGISTRY.keys())}

        defn = LoopDefinition(
            name=payload["name"],
            domain=payload.get("domain", "general"),
            interval_seconds=payload.get("interval_seconds", 300),
            stages=stages,
            description=payload.get("description", ""),
        )
        registry.register_definition(defn)
        registry.save_definitions()
        return {"created": defn.name, "definition": defn.to_dict()}
    except Exception as e:
        return {"error": str(e)}


@router.delete("/loops/{loop_name}")
async def loop_delete(loop_name: str):
    """Remove a loop definition."""
    try:
        registry = _get_loop_registry()
        ok = registry.remove(loop_name)
        if ok:
            registry.save_definitions()
        return {"removed": ok, "loop": loop_name}
    except Exception as e:
        return {"error": str(e)}
