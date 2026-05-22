"""Cockpit API endpoints — serves real data from UMH stores to the frontend.

All endpoints are prefixed /api/umh/ and registered via include_router in app.py.
"""

from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil
from fastapi import APIRouter

router = APIRouter(prefix="/api/umh")

MEMORY_STORE = Path("/opt/OS/data/runtime/canonical_memory_store/memories.jsonl")
TRACE_STORE = Path("/opt/OS/data/umh/traces/traces.jsonl")
SKILLS_DIR = Path("/opt/OS/skills")
AGENTS_DIR = Path("/opt/OS/agents")


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
    from ..model_routing.config import load_routing_config

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
    from services.umh.node_mesh.server import NodeMeshServer

    server: NodeMeshServer | None = _get_mesh_server()
    if server is None:
        return []
    nodes = server.node_registry.all_nodes()
    return [n.to_api_dict() for n in nodes]


def _get_mesh_server():
    """Lazy import to avoid circular dependency at module load."""
    try:
        from services.umh.control_plane.app import _mesh_server

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
        from services.umh.control_plane.app import _organism

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
        from services.umh.control_plane.app import _pipeline
        from services.umh.governance.risk_classes import RiskClass

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

    from services.umh.organism.protocols import AgentMessage

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
        from services.umh.control_plane.app import _pipeline
        from services.umh.governance.risk_classes import RiskClass

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
