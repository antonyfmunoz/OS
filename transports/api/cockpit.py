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
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Security,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from transports.api.cockpit_auth import require_clerk_auth, validate_ws_clerk_token

logger = logging.getLogger(__name__)

_API_KEY = os.environ.get("UMH_OPERATOR_API_KEY", "")
_OPERATOR_TOKEN = os.environ.get("UMH_OPERATOR_TOKEN", "")
_WS_TOKEN = os.environ.get("UMH_WS_TOKEN", "") or _API_KEY
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_operator_token_header = APIKeyHeader(name="X-Operator-Token", auto_error=False)

_DEV_BYPASS = os.environ.get("UMH_DEV_BYPASS", "").lower() in ("1", "true", "yes")

import hmac as _hmac
import ipaddress as _ipaddress

_TAILSCALE_CGNAT = _ipaddress.ip_network("100.64.0.0/10")


def _is_private_ip(ip: str) -> bool:
    if not ip:
        return False
    try:
        addr = _ipaddress.ip_address(ip)
        return addr.is_private or addr.is_loopback or addr in _TAILSCALE_CGNAT
    except ValueError:
        return False


_TRUSTED_PROXIES = {"127.0.0.1", "::1"}
_docker_bridge = os.environ.get("UMH_DOCKER_BRIDGE_IP", "172.20.0.1")
if _docker_bridge:
    _TRUSTED_PROXIES.add(_docker_bridge)


def _real_client_ip(request: Request) -> str:
    """Return the real client IP, accounting for trusted reverse proxies.

    Only reads X-Forwarded-For when the TCP source is an explicitly trusted
    proxy (localhost or Docker bridge).  Tailscale CGNAT IPs are real clients
    — not proxies — so their TCP source is used directly.
    """
    tcp_ip = request.client.host if request.client else ""
    if tcp_ip in _TRUSTED_PROXIES:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return tcp_ip


def _dev_bypass_allowed(request: Request) -> bool:
    """Allow token-free access from private IPs when UMH_DEV_BYPASS=true."""
    if not _DEV_BYPASS:
        return False
    return _is_private_ip(_real_client_ip(request))


_RATE_LIMITS: dict[str, dict[str, float]] = {}
_RATE_WINDOWS: dict[str, float] = {
    "promote": 60.0,
    "execute": 30.0,
    "approve": 30.0,
}


def _check_rate_limit(action: str, client_id: str) -> None:
    window = _RATE_WINDOWS.get(action, 60.0)
    bucket = _RATE_LIMITS.setdefault(action, {})
    now = time.time()
    last = bucket.get(client_id, 0.0)
    if now - last < window:
        remaining = int(window - (now - last))
        raise HTTPException(status_code=429, detail=f"Rate limited — retry in {remaining}s")
    bucket[client_id] = now


async def _require_api_key(
    request: Request,
    key: str | None = Security(_api_key_header),
) -> str:
    if not _API_KEY:
        if _dev_bypass_allowed(request):
            return "dev-bypass"
        raise HTTPException(
            status_code=503, detail="API key not configured — set UMH_OPERATOR_API_KEY"
        )
    if not key or not _hmac.compare_digest(key, _API_KEY):
        if _dev_bypass_allowed(request):
            return "dev-bypass"
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return key


async def _require_operator_role(
    request: Request,
    key: str | None = Security(_api_key_header),
    operator_token: str | None = Security(_operator_token_header),
) -> str:
    """Validates operator-level credentials for privileged endpoints."""
    await _require_api_key(request, key)

    if not _OPERATOR_TOKEN:
        if _dev_bypass_allowed(request):
            logger.info("Operator dev-bypass from private IP %s", _real_client_ip(request))
            return "operator-dev-bypass"
        raise HTTPException(
            status_code=503, detail="Operator token not configured — set UMH_OPERATOR_TOKEN"
        )

    if not operator_token or not _hmac.compare_digest(operator_token, _OPERATOR_TOKEN):
        logger.warning(
            "Unauthorized operator access attempt: %s %s from %s",
            request.method,
            request.url.path,
            _real_client_ip(request),
        )
        raise HTTPException(
            status_code=403, detail="Operator token required for privileged actions"
        )

    return "operator"


router = APIRouter(prefix="/api/umh", dependencies=[Depends(require_clerk_auth)])
ws_router = APIRouter(prefix="/api/umh")

_ROOT = Path(os.getenv("UMH_ROOT", "/opt/OS"))
MEMORY_STORE = _ROOT / "data" / "runtime" / "canonical_memory_store" / "memories.jsonl"
TRACE_STORE = _ROOT / "data" / "umh" / "traces" / "traces.jsonl"
SKILLS_DIR = _ROOT / "skills"
AGENTS_DIR = _ROOT / "agents"

_DOCKER_SOCK = "/var/run/docker.sock"
_DEVICE_REGISTRY_PATH = _ROOT / "infra" / "device_registry.json"


def _load_device_registry() -> list[dict[str, Any]]:
    try:
        with open(_DEVICE_REGISTRY_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError, FileNotFoundError):
        return []


def _get_docker_containers() -> list[dict]:
    """Query Docker Engine API via unix socket for running containers."""
    import socket as _socket
    import http.client

    try:
        if not os.path.exists(_DOCKER_SOCK):
            return []

        class _DockerConn(http.client.HTTPConnection):
            def connect(self):
                self.sock = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
                self.sock.settimeout(2)
                self.sock.connect(_DOCKER_SOCK)

        conn = _DockerConn("localhost")
        conn.request("GET", "/containers/json")
        resp = conn.getresponse()
        if resp.status != 200:
            return []
        data = json.loads(resp.read())
        conn.close()
        result = []
        for c in data:
            names = c.get("Names", ["/unknown"])
            name = names[0].lstrip("/") if names else "unknown"
            status = c.get("Status", "unknown")
            state = c.get("State", "unknown")
            result.append({"name": name, "status": status, "state": state})
        return result
    except Exception:
        return []


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


def _compute_build_info() -> dict[str, Any]:
    info: dict[str, Any] = {"backend_start": datetime.now(timezone.utc).isoformat()}
    try:
        sha = gated_subprocess_run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(_ROOT),
        )
        if sha.returncode == 0:
            info["commit_sha"] = sha.stdout.strip()
    except Exception:
        pass
    try:
        ts = gated_subprocess_run(
            ["git", "log", "-1", "--format=%cI"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(_ROOT),
        )
        if ts.returncode == 0:
            info["commit_time"] = ts.stdout.strip()
    except Exception:
        pass
    import re as _re

    index_html = _ROOT / "cockpit" / "dist-web" / "index.html"
    if index_html.is_file():
        html = index_html.read_text()
        js_match = _re.search(r'src="[./]*assets/(index-[^"]+\.js)"', html)
        css_match = _re.search(r'href="[./]*assets/(index-[^"]+\.css)"', html)
        if js_match:
            info["js_hash"] = js_match.group(1)
        if css_match:
            info["css_hash"] = css_match.group(1)
    return info


_BUILD_INFO = _compute_build_info()


@router.get("/build")
async def build_info():
    return _BUILD_INFO


@router.get("/pulse")
async def pulse():
    node_metrics = _build_node_metrics()
    vps = node_metrics.get("vps", {})
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
        "cpu_percent": vps.get("cpu", 0),
        "memory_percent": vps.get("memory", 0),
        "disk_percent": vps.get("disk", 0),
        "active_agents": active_agents,
        "pending_tasks": pending_traces,
        "pending_approvals": pending_approvals,
        "trace_rate": round(len(traces) / max(uptime / 3600, 1), 1),
        "node_metrics": node_metrics,
    }


@router.get("/mesh/metrics")
async def mesh_metrics():
    """Per-node metrics — reads from mesh server snapshot (single source of truth)."""
    return _build_node_metrics()


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
        out = gated_subprocess_run(
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
    hostname = dns.split(".")[0] if dns else peer.get("HostName", "unknown")
    registry = _load_device_registry()
    for dev in registry:
        if dev.get("tailscale_name", "") == hostname:
            return dev.get("display_name", hostname)
    return hostname


@router.get("/infra")
async def infra():
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    compute_nodes: list[dict] = []
    network_nodes: list[dict] = []
    service_nodes: list[dict] = []

    registry = _load_device_registry()
    vps_entry = next((d for d in registry if d.get("id") == "vps"), {})
    vps_display = vps_entry.get("display_name", "srv1500858 (VPS)")
    compute_nodes.append(
        {
            "id": "n-vps",
            "name": vps_display,
            "type": "compute",
            "status": "healthy",
            "metrics": {"cpu": cpu, "memory": mem.percent, "disk": disk.percent, "cost": 24},
        }
    )

    try:
        out = gated_subprocess_run(
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
                        "name": name,
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

    for c in _get_docker_containers():
        is_up = c.get("state") == "running"
        service_nodes.append(
            {
                "id": f"n-{c['name']}",
                "name": c["name"],
                "type": "service",
                "status": "healthy" if is_up else "down",
                "metrics": {},
            }
        )

    return compute_nodes + network_nodes + service_nodes


@router.get("/approvals")
async def approvals():
    daemon = _get_organism()
    if daemon is None:
        return []
    return daemon.approval_store.list_approvals()


@router.post("/approvals/{approval_id}/approve", dependencies=[Depends(_require_operator_role)])
async def approve_item(approval_id: str):
    daemon = _get_organism()
    if daemon is None:
        return {"ok": False, "error": "organism not running"}
    result = daemon.approval_store.decide(approval_id, "approved")
    if result is None:
        return {"ok": False, "error": "approval not found"}
    return {"ok": True}


@router.post("/approvals/{approval_id}/deny", dependencies=[Depends(_require_operator_role)])
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
async def memory(source: str = "all", limit: int = 50):
    """Memory entries from typed ConversationMemory and AgentMemory classes,
    with JSONL fallback for legacy ontology data."""
    result = []

    if source in ("all", "conversation"):
        try:
            from substrate.state.memory.memory import ConversationMemory
            from substrate.state.context.context import try_load_context_from_env

            ctx = try_load_context_from_env()
            if ctx:
                conv = ConversationMemory(ctx)
                recent = conv.get_recent(limit=limit)
                for msg in recent:
                    result.append(
                        {
                            "id": getattr(msg, "id", ""),
                            "label": (getattr(msg, "content", "") or "")[:80],
                            "description": (getattr(msg, "content", "") or "")[:300],
                            "memory_type": "CONVERSATION",
                            "authority_tier": "T5",
                            "source_document": "",
                            "primitive_type": "state",
                            "created_at": str(getattr(msg, "created_at", "")),
                            "role": getattr(msg, "role", ""),
                            "channel": getattr(msg, "channel", ""),
                        }
                    )
        except Exception as e:
            logger.debug("conversation memory load: %s", e)

    if source in ("all", "agent"):
        try:
            from substrate.state.memory.memory import AgentMemory

            agent_mem = AgentMemory()
            recent_interactions = agent_mem.get_recent(limit=limit)
            for row in recent_interactions:
                result.append(
                    {
                        "id": str(row.get("id", "")),
                        "label": (str(row.get("input_summary", "")) or "")[:80],
                        "description": (str(row.get("output_summary", "")) or "")[:300],
                        "memory_type": "AGENT",
                        "authority_tier": "T5",
                        "source_document": "",
                        "primitive_type": "action",
                        "created_at": str(row.get("created_at", "")),
                        "agent": str(row.get("agent", "")),
                    }
                )
        except Exception as e:
            logger.debug("agent memory load: %s", e)

    if source in ("all", "ontology"):
        entries = _read_jsonl(MEMORY_STORE)
        for e in entries[:limit]:
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
        sender = m.get("sender", "unknown")
        if sender == "operator":
            direction = "outbound"
        elif m.get("intent") == "report" or m.get("recipient") == "operator":
            direction = "inbound"
        result.append(
            {
                "id": m.get("id", ""),
                "sender": sender,
                "recipient": m.get("recipient", "unknown"),
                "intent": m.get("intent", ""),
                "content": _summarize_message(m),
                "payload": m.get("payload", {}),
                "conversation_id": m.get("conversation_id", ""),
                "parent_message_id": m.get("parent_message_id"),
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
    """Returns all network devices: Tailscale peers + UMH daemon nodes."""
    _registry = _load_device_registry()
    _ROLE_MAP = {
        dev["tailscale_name"]: dev["role"]
        for dev in _registry
        if "tailscale_name" in dev and "role" in dev
    }
    _NAME_MAP = {
        dev["tailscale_name"]: dev["display_name"]
        for dev in _registry
        if "tailscale_name" in dev and "display_name" in dev
    }

    daemon_nodes: dict[str, dict] = {}
    server = _get_mesh_server()
    if server is not None:
        for n in server.node_registry.all_nodes():
            d = n.to_api_dict()
            daemon_nodes[d.get("tailscale_ip", "")] = d

    nodes: list[dict] = []
    seen: set[str] = set()

    def _map_ts_node(n: dict, is_self: bool = False) -> dict | None:
        hostname = n.get("HostName", "")
        dns_name = n.get("DNSName", "").split(".")[0]  # e.g. "iphone-15-pro-max"
        # Use DNSName when HostName is generic (iOS devices report "localhost")
        display = dns_name if hostname.lower() in ("localhost", "") and dns_name else hostname
        key = display.lower()
        if key.startswith("umh-cockpit"):
            return None
        if key in seen:
            return None
        seen.add(key)

        ips = n.get("TailscaleIPs", [])
        ip = ips[0] if ips else ""
        online = n.get("Online", False) or is_self
        os_name = n.get("OS", "")
        last_seen = n.get("LastSeen", "")
        if last_seen == "0001-01-01T00:00:00Z":
            last_seen = ""

        daemon = daemon_nodes.get(ip, {})

        return {
            "node_id": key,
            "hostname": _NAME_MAP.get(key, display),
            "role": _ROLE_MAP.get(key, "mobile" if os_name == "iOS" else "node"),
            "status": "online" if online else "offline",
            "os": os_name,
            "ip": ip,
            "last_seen": last_seen if not online else datetime.now(timezone.utc).isoformat(),
            "daemon_version": daemon.get("daemon_version"),
            "capabilities": daemon.get("capabilities", []),
        }

    def _parse_ts_data(ts: dict) -> None:
        self_node = ts.get("Self")
        if self_node:
            mapped = _map_ts_node(self_node, is_self=True)
            if mapped:
                nodes.append(mapped)
        for p in (ts.get("Peer") or {}).values():
            mapped = _map_ts_node(p)
            if mapped:
                nodes.append(mapped)

    # Try CLI first (works on host), then fall back to snapshot file (works in Docker)
    try:
        result = gated_subprocess_run(
            ["tailscale", "status", "--json"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            _parse_ts_data(json.loads(result.stdout))
    except Exception:
        pass

    if not nodes:
        snapshot = _ROOT / "data" / "runtime" / "tailscale_status.json"
        if snapshot.exists():
            try:
                _parse_ts_data(json.loads(snapshot.read_text(encoding="utf-8")))
            except Exception:
                pass

    if not nodes:
        _fb_registry = _load_device_registry()
        _fb_vps = next((d for d in _fb_registry if d.get("id") == "vps"), {})
        nodes.append(
            {
                "node_id": "vps-primary",
                "hostname": _fb_vps.get("display_name", os.uname().nodename),
                "role": _fb_vps.get("role", "orchestrator"),
                "status": "online",
                "os": "linux",
                "ip": _fb_vps.get("tailscale_ip", ""),
                "last_seen": datetime.now(timezone.utc).isoformat(),
                "daemon_version": None,
                "capabilities": [],
            }
        )

    return nodes


def _get_mesh_server():
    """Lazy import to avoid circular dependency at module load."""
    try:
        from transports.api.app import _mesh_server

        if _mesh_server is not None:
            return _mesh_server
    except (ImportError, AttributeError):
        pass
    try:
        from services.operator_api import _mesh_server_instance

        return _mesh_server_instance
    except (ImportError, AttributeError):
        return None


_MESH_METRICS_FILE = os.path.join(
    os.environ.get("UMH_ROOT", "/opt/OS"),
    "data",
    "umh",
    "organism",
    "mesh_metrics.json",
)


def _read_mesh_metrics_file() -> dict[str, dict[str, Any]]:
    """Read node metrics written by the standalone mesh server process."""
    try:
        with open(_MESH_METRICS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _build_node_metrics() -> dict[str, dict[str, Any]]:
    """Build complete node_metrics dict from the mesh snapshot file.

    The mesh server is the single source of truth for all organism metrics.
    It writes VPS self-metrics + remote node heartbeats to mesh_metrics.json
    on a 5s cadence. This function reads that file and enriches with display
    names from the device registry, adding offline entries for compute nodes
    that aren't reporting.
    """
    registry = _load_device_registry()
    snapshot = _read_mesh_metrics_file()
    result: dict[str, dict[str, Any]] = {}
    for node_id, mdata in snapshot.items():
        dev = next(
            (d for d in registry if d.get("mesh_node_id") == node_id or d.get("id") == node_id), {}
        )
        entry: dict[str, Any] = {
            "name": dev.get("display_name", node_id),
            "cpu": mdata.get("cpu"),
            "memory": mdata.get("memory"),
            "disk": mdata.get("disk"),
            "battery": mdata.get("battery"),
            "status": "online",
            "timestamp": mdata.get("timestamp"),
        }
        gpu = mdata.get("gpu")
        if gpu is not None:
            entry["gpu"] = gpu
        result[node_id] = entry
    for dev in registry:
        if not dev.get("compute"):
            continue
        did = dev.get("id", "")
        mid = dev.get("mesh_node_id", "")
        if did not in result and mid not in result:
            result[did] = {
                "name": dev.get("display_name", did),
                "cpu": None,
                "memory": None,
                "disk": None,
                "status": "offline",
            }
    return result


def _get_organism():
    try:
        from transports.api.app import _organism

        if _organism is not None:
            return _organism
    except (ImportError, AttributeError):
        pass
    try:
        from services.operator_api import _organism_daemon

        return _organism_daemon
    except (ImportError, AttributeError):
        return None


@router.post("/pipeline/submit", dependencies=[Depends(_require_operator_role)])
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


@router.post("/comms/send", dependencies=[Depends(_require_operator_role)])
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


@router.post("/workflows/{workflow_id}/trigger", dependencies=[Depends(_require_operator_role)])
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


@router.patch("/settings", dependencies=[Depends(_require_operator_role)])
async def update_settings(patch: dict):
    """Update cockpit settings (runtime-only, not persisted across restarts)."""
    return {"ok": True, "applied": list(patch.keys())}


@router.post("/organism/control", dependencies=[Depends(_require_operator_role)])
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


@router.patch("/governance", dependencies=[Depends(_require_operator_role)])
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

_dex_conversation = None


def _mirror_to_discord_founders_office(text: str) -> None:
    """Mirror a cockpit DEX response to the Discord Founder's Office channel.

    Fire-and-forget — failures are logged but never block the cockpit response.
    """
    import threading

    def _send():
        try:
            import urllib.request

            _env_path = Path("/opt/OS/services/.env")
            token = os.environ.get("DISCORD_BOT_TOKEN", "")
            channel_id = os.environ.get("DISCORD_FOUNDERS_OFFICE", "")

            if not token and _env_path.exists():
                with open(_env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("DISCORD_BOT_TOKEN="):
                            token = line.split("=", 1)[1].strip()
                        elif line.startswith("DISCORD_FOUNDERS_OFFICE="):
                            channel_id = line.split("=", 1)[1].strip()

            if not token or not channel_id:
                return

            truncated = text[:2000]
            url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
            payload = json.dumps({"content": truncated}).encode()
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Authorization": f"Bot {token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception as exc:
            logger.debug("Discord mirror failed (non-fatal): %s", exc)

    threading.Thread(target=_send, daemon=True).start()


def _get_dex_conversation():
    global _dex_conversation
    if _dex_conversation is not None:
        return _dex_conversation
    daemon = _get_organism()
    if daemon is None:
        return None
    from substrate.organism.dex_conversation import DexConversation

    _dex_conversation = DexConversation(advisor=daemon.advisor, store=daemon.store)
    return _dex_conversation


@router.post("/advisor/converse")
async def advisor_converse(payload: dict):
    """Multi-turn conversational endpoint for the advisor right rail."""
    conv = _get_dex_conversation()
    if conv is None:
        return {"error": "organism not running"}

    content = payload.get("content", "")
    if not content:
        return {"error": "content required"}

    source = payload.get("source", "text")
    routing = payload.get("routing")  # Optional voice routing metadata
    voice_turn_id = payload.get("voice_turn_id", "")  # Idempotency key for voice turns

    response = conv.converse(
        content=content,
        conversation_id=payload.get("conversation_id", ""),
        view_context=payload.get("view_context"),
        source=source,
        routing=routing,
        voice_turn_id=voice_turn_id,
    )

    # Persist both sides to OrganismStore so /chat/history survives refresh
    try:
        from substrate.organism.store import OrganismStore

        store = OrganismStore()
        store.save_conversation_turn(
            content=content,
            response=response.text,
            origin_channel="cockpit",
            responder="dex",
        )
    except Exception as exc:
        logger.debug("Failed to persist conversation to OrganismStore: %s", exc)

    # Mirror to Discord Founder's Office (only for cockpit-originated messages)
    if source != "discord" and response.text:
        _mirror_to_discord_founders_office(response.text)

    result: dict = {
        "message_id": f"advisor-{response.timestamp}",
        "text": response.text,
        "response": response.text,
        "conversation_id": response.conversation_id,
        "intent": response.intent,
        "suggested_actions": response.suggested_actions,
        "metadata": response.metadata,
        "timestamp": response.timestamp,
    }
    if response.spoken_text:
        result["spoken_text"] = response.spoken_text
    if response.routing:
        result["routing"] = response.routing
    return result


@router.post("/dex/converse")
async def dex_converse_compat(payload: dict):
    """Backward-compat shim — canonical route is /advisor/converse."""
    return await advisor_converse(payload)


@router.get("/advisor/history")
async def advisor_history(limit: int = 50):
    """Recent advisor channel exchanges and system reports for the right-rail chat."""
    daemon = _get_organism()
    if daemon is None:
        return []

    messages = daemon.store.list_messages(limit=500)

    exchanges: list[dict[str, Any]] = []

    dex_msgs = [m for m in messages if m.get("payload", {}).get("source") == "cockpit_advisor_channel"]
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

    _REPORT_SENDERS = {"system", "dex"}
    for m in messages:
        if m.get("intent") == "report" and m.get("sender", "") in _REPORT_SENDERS:
            payload = m.get("payload", {})
            title = str(payload.get("title", "Report"))[:200]
            summary = payload.get("summary", "")
            meta = payload.get("metadata", {})
            file_path = str(payload.get("file_path", ""))[:500]
            conv_id = m.get("conversation_id", "")

            provenance: dict[str, Any] = {
                "node": "VPS",
                "harness": "Claude Code",
            }
            if conv_id:
                provenance["session"] = str(conv_id)[:12]
            if meta.get("phase"):
                provenance["phase"] = str(meta["phase"])[:20]
            if meta.get("pr"):
                provenance["pr"] = (
                    int(meta["pr"]) if str(meta["pr"]).isdigit() else str(meta["pr"])[:20]
                )
            if meta.get("task"):
                provenance["task"] = str(meta["task"])[:100]

            attachment = None
            if file_path:
                attachment = {
                    "path": file_path,
                    "filename": file_path.rsplit("/", 1)[-1] if "/" in file_path else file_path,
                }

            exchanges.append(
                {
                    "id": m.get("id", ""),
                    "timestamp": m.get("created_at", ""),
                    "sender": m.get("sender", "system"),
                    "content": "",
                    "response": summary,
                    "intent": "report",
                    "title": title,
                    "provenance": provenance,
                    "attachment": attachment,
                }
            )

    exchanges.sort(key=lambda x: x.get("timestamp", ""))
    return exchanges[-limit:]


@router.get("/dex/history")
async def dex_history_compat(limit: int = 50):
    """Backward-compat shim — canonical route is /advisor/history."""
    return await advisor_history(limit)


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


@router.post("/organism/handoff", dependencies=[Depends(_require_operator_role)])
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


@router.post("/organism/parallel", dependencies=[Depends(_require_operator_role)])
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


@router.post("/notifications/send", dependencies=[Depends(_require_operator_role)])
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
_pending_organism_events: list[dict] = []


def push_organism_event(event_dict: dict) -> None:
    """Called by the organism daemon to push events to WebSocket clients."""
    _pending_organism_events.append(event_dict)
    if len(_pending_organism_events) > 200:
        _pending_organism_events[:] = _pending_organism_events[-100:]


def push_chat_message(message: dict) -> None:
    """Queue a chat message for delivery to connected cockpit WS clients.

    The message gets wrapped as type='chat_message' and included in
    the next WS pulse cycle. Used by Discord bot and other channels
    to push cross-channel messages to the cockpit in near-real-time.
    """
    event = {"type": "chat_message", **message}
    _pending_organism_events.append(event)
    if len(_pending_organism_events) > 200:
        _pending_organism_events[:] = _pending_organism_events[-100:]


def _extract_ws_subprotocol(ws: WebSocket) -> str | None:
    """Return the bearer subprotocol string if the client sent one, else None."""
    for proto in (ws.headers.get("sec-websocket-protocol") or "").split(","):
        proto = proto.strip()
        if proto.startswith("bearer."):
            return proto
    return None


def _extract_ws_token(ws: WebSocket) -> str:
    """Extract auth token from Sec-WebSocket-Protocol header or query param.

    Preferred: client sends subprotocol 'bearer.<token>' — avoids token in URL/logs.
    Fallback: ?token= query param for clients that cannot set subprotocols.
    """
    sub = _extract_ws_subprotocol(ws)
    if sub:
        return sub[7:]
    return ws.query_params.get("token", "")


def _real_ws_client_ip(ws: WebSocket) -> str:
    """Real client IP for WebSocket, same trusted-proxy logic as HTTP."""
    tcp_ip = ws.client.host if ws.client else ""
    if tcp_ip in _TRUSTED_PROXIES:
        forwarded = ws.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return tcp_ip


def _validate_ws_token(ws: WebSocket) -> bool:
    """Validate WS connection auth.

    Tries Clerk JWT first (via cockpit_auth). If a Clerk credential is
    presented but invalid, rejects immediately (no fall-through).
    Falls back to WS token / dev-bypass only when no Clerk credential present.
    """
    try:
        clerk_user = validate_ws_clerk_token(ws)
        if clerk_user is not None:
            return True
    except HTTPException:
        return False
    if _WS_TOKEN:
        token = _extract_ws_token(ws)
        if token and _hmac.compare_digest(token, _WS_TOKEN):
            return True
    client_ip = _real_ws_client_ip(ws)
    if _DEV_BYPASS and _is_private_ip(client_ip):
        return True
    return False


@ws_router.websocket("/ws")
async def cockpit_ws(ws: WebSocket):
    """Stream live system metrics to connected cockpit clients.

    Auth: Sec-WebSocket-Protocol 'bearer.<TOKEN>', or ?token= fallback,
    or dev-bypass from private IP. Rejected with 4001 otherwise.
    """
    if not _validate_ws_token(ws):
        await ws.close(code=4001, reason="Authentication required")
        logger.warning("WS auth rejected from %s", ws.client.host if ws.client else "unknown")
        return
    subprotocol = _extract_ws_subprotocol(ws)
    await ws.accept(subprotocol=subprotocol)
    _cockpit_clients.add(ws)
    event_cursor = len(_pending_organism_events)
    logger.info(f"cockpit ws connected ({len(_cockpit_clients)} clients)")
    try:
        while True:
            node_metrics = _build_node_metrics()
            vps = node_metrics.get("vps", {})
            traces = _read_jsonl(TRACE_STORE)
            recent_traces = traces[-10:] if traces else []
            containers = _get_docker_containers()
            new_events = _pending_organism_events[event_cursor:]
            event_cursor = len(_pending_organism_events)
            snapshot = {
                "type": "pulse",
                "ts": datetime.now(timezone.utc).isoformat(),
                "cpu_percent": vps.get("cpu", 0),
                "memory_percent": vps.get("memory", 0),
                "disk_percent": vps.get("disk", 0),
                "containers": containers,
                "node_metrics": node_metrics,
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
                "organism_events": new_events,
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


# ─── Voice WebSocket Proxy ────────────────────────────────────────────────────

_VOICE_WS_UPSTREAM = os.environ.get("VOICE_WS_UPSTREAM", "ws://host.docker.internal:8096/voice")
_VOICE_PROXY_MAX_MSG = 2 ** 22  # 4 MiB


@ws_router.websocket("/voice/ws")
async def voice_ws_proxy(ws: WebSocket):
    """Proxy browser voice WebSocket to the internal voice server.

    Auth: same as cockpit_ws (subprotocol bearer.<token>, query param, or dev-bypass).
    Forwards binary (PCM audio) and JSON control frames in both directions.
    """
    if not _validate_ws_token(ws):
        await ws.close(code=4001, reason="Authentication required")
        logger.warning("[VoiceProxy] auth rejected from %s", ws.client.host if ws.client else "unknown")
        return

    subprotocol = _extract_ws_subprotocol(ws)
    await ws.accept(subprotocol=subprotocol)
    logger.info("[VoiceProxy] client_connected from %s", ws.client.host if ws.client else "unknown")

    upstream = None
    try:
        import websockets.client
        upstream = await asyncio.wait_for(
            websockets.client.connect(
                _VOICE_WS_UPSTREAM,
                max_size=_VOICE_PROXY_MAX_MSG,
                ping_interval=20,
                ping_timeout=20,
            ),
            timeout=5.0,
        )
        logger.info("[VoiceProxy] upstream_connected %s", _VOICE_WS_UPSTREAM)
    except Exception as e:
        logger.error("[VoiceProxy] upstream_connect_failed: %s", e)
        await ws.send_json({"type": "error", "code": "voice_server_unavailable", "message": "Voice server unreachable"})
        await ws.close(code=1011, reason="Voice server unreachable")
        return

    async def client_to_upstream():
        try:
            while True:
                msg = await ws.receive()
                if msg.get("type") == "websocket.disconnect":
                    break
                if "bytes" in msg and msg["bytes"]:
                    await upstream.send(msg["bytes"])
                elif "text" in msg and msg["text"]:
                    await upstream.send(msg["text"])
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.debug("[VoiceProxy] client_to_upstream error: %s", e)
        finally:
            logger.info("[VoiceProxy] client_closed")

    async def upstream_to_client():
        try:
            async for message in upstream:
                if isinstance(message, bytes):
                    await ws.send_bytes(message)
                else:
                    await ws.send_text(message)
        except Exception as e:
            logger.debug("[VoiceProxy] upstream_to_client error: %s", e)
        finally:
            logger.info("[VoiceProxy] upstream_closed")

    try:
        done, pending = await asyncio.wait(
            [asyncio.ensure_future(client_to_upstream()), asyncio.ensure_future(upstream_to_client())],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    except Exception as e:
        logger.error("[VoiceProxy] error: %s", e)
    finally:
        if upstream:
            await upstream.close()
        try:
            await ws.close()
        except Exception:
            pass
        logger.info("[VoiceProxy] session_ended")


# ─── Vision WebSocket Proxy ───────────────────────────────────────────────────

_VISION_WS_UPSTREAM = os.environ.get("VISION_WS_UPSTREAM", "ws://host.docker.internal:8097/vision")
_VISION_PROXY_MAX_MSG = 2 ** 22  # 4 MiB


@ws_router.websocket("/vision/ws")
async def vision_ws_proxy(ws: WebSocket):
    """Proxy browser vision WebSocket to the internal vision relay."""
    if not _validate_ws_token(ws):
        await ws.close(code=4001, reason="Authentication required")
        logger.warning("[VisionProxy] auth rejected from %s", ws.client.host if ws.client else "unknown")
        return

    subprotocol = _extract_ws_subprotocol(ws)
    await ws.accept(subprotocol=subprotocol)
    logger.info("[VisionProxy] client_connected from %s", ws.client.host if ws.client else "unknown")

    upstream = None
    try:
        import websockets.client
        upstream = await asyncio.wait_for(
            websockets.client.connect(
                _VISION_WS_UPSTREAM,
                max_size=_VISION_PROXY_MAX_MSG,
                ping_interval=20,
                ping_timeout=20,
            ),
            timeout=5.0,
        )
        logger.info("[VisionProxy] upstream_connected %s", _VISION_WS_UPSTREAM)
    except Exception as e:
        logger.error("[VisionProxy] upstream_connect_failed: %s", e)
        await ws.send_json({"type": "error", "code": "vision_relay_unavailable", "message": "Vision relay unreachable"})
        await ws.close(code=1011, reason="Vision relay unreachable")
        return

    async def client_to_upstream():
        try:
            while True:
                msg = await ws.receive()
                if msg.get("type") == "websocket.disconnect":
                    break
                if "bytes" in msg and msg["bytes"]:
                    await upstream.send(msg["bytes"])
                elif "text" in msg and msg["text"]:
                    await upstream.send(msg["text"])
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.debug("[VisionProxy] client_to_upstream error: %s", e)
        finally:
            logger.info("[VisionProxy] client_closed")

    async def upstream_to_client():
        try:
            async for message in upstream:
                if isinstance(message, bytes):
                    await ws.send_bytes(message)
                else:
                    await ws.send_text(message)
        except Exception as e:
            logger.debug("[VisionProxy] upstream_to_client error: %s", e)
        finally:
            logger.info("[VisionProxy] upstream_closed")

    try:
        done, pending = await asyncio.wait(
            [asyncio.ensure_future(client_to_upstream()), asyncio.ensure_future(upstream_to_client())],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    except Exception as e:
        logger.error("[VisionProxy] error: %s", e)
    finally:
        if upstream:
            await upstream.close()
        try:
            await ws.close()
        except Exception:
            pass
        logger.info("[VisionProxy] session_ended")


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


@router.post("/loops/{loop_name}/start", dependencies=[Depends(_require_operator_role)])
async def loop_start(loop_name: str):
    """Start a persistent loop."""
    try:
        ok = _get_loop_registry().start(loop_name)
        return {"started": ok, "loop": loop_name}
    except Exception as e:
        return {"error": str(e)}


@router.post("/loops/{loop_name}/stop", dependencies=[Depends(_require_operator_role)])
async def loop_stop(loop_name: str):
    """Stop a persistent loop."""
    try:
        ok = _get_loop_registry().stop(loop_name)
        return {"stopped": ok, "loop": loop_name}
    except Exception as e:
        return {"error": str(e)}


@router.post("/loops/{loop_name}/run-once", dependencies=[Depends(_require_operator_role)])
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


@router.post("/loops/create", dependencies=[Depends(_require_operator_role)])
async def loop_create(payload: dict):
    """Create a new loop definition at runtime."""
    try:
        from substrate.execution.loop import STAGE_REGISTRY
        from substrate.execution.loop.persistent_loop import LoopDefinition

        registry = _get_loop_registry()

        stages = payload.get("stages", [])
        unknown = [s for s in stages if s not in STAGE_REGISTRY]
        if unknown:
            return {
                "error": f"unknown stages: {unknown}",
                "available": sorted(STAGE_REGISTRY.keys()),
            }

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


@router.delete("/loops/{loop_name}", dependencies=[Depends(_require_operator_role)])
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


# ── Execution Substrate endpoints ────────────────────────────────────────────


@router.get("/execution/status")
async def execution_status():
    """Execution status from live organism spine and work packet engine."""
    try:
        organism = _get_organism()
        spine_status = {}
        pending_count = 0
        active_count = 0
        completed_count = 0

        if organism:
            spine = getattr(organism, "spine", None)
            if spine:
                spine_status = {
                    "mode": getattr(spine, "mode", "unknown"),
                    "guard_mode": getattr(spine, "guard_mode", "unknown"),
                }
            pending = getattr(organism, "get_pending_envelopes", lambda: [])()
            active = getattr(organism, "get_active_envelopes", lambda: [])()
            completed_list = getattr(organism, "get_completed_envelopes", lambda: [])()
            pending_count = len(pending) if pending else 0
            active_count = len(active) if active else 0
            completed_count = len(completed_list) if completed_list else 0

        from substrate.organism.work_packet_engine import WorkPacketEngine

        wpe = WorkPacketEngine()
        packets = wpe.all_packets()
        packet_summary = {}
        for pkt in packets:
            status_val = pkt.status.value if hasattr(pkt.status, "value") else str(pkt.status)
            packet_summary[status_val] = packet_summary.get(status_val, 0) + 1

        return {
            "spine": spine_status,
            "envelopes": {
                "pending": pending_count,
                "active": active_count,
                "completed": completed_count,
            },
            "work_packets": {
                "total": len(packets),
                "by_status": packet_summary,
            },
        }
    except Exception as e:
        logger.debug("execution_status: %s", e)
        return {
            "spine": {},
            "envelopes": {"pending": 0, "active": 0, "completed": 0},
            "work_packets": {"total": 0, "by_status": {}},
            "error": str(e),
        }


@router.get("/execution/log")
async def execution_log(limit: int = 20):
    """Recent execution journal entries from spine."""
    try:
        organism = _get_organism()
        if not organism:
            return {"log": [], "count": 0}
        journal = getattr(organism, "journal", None)
        if not journal:
            return {"log": [], "count": 0}
        recent = getattr(journal, "recent", lambda n: [])(limit)
        entries = []
        for entry in recent:
            entries.append(
                {
                    "id": str(getattr(entry, "id", "")),
                    "event_type": str(getattr(entry, "event_type", "")),
                    "timestamp": str(getattr(entry, "timestamp", "")),
                    "envelope_id": str(getattr(entry, "envelope_id", "")),
                    "summary": str(getattr(entry, "summary", ""))[:200],
                }
            )
        return {"log": entries, "count": len(entries)}
    except Exception as e:
        logger.debug("execution_log: %s", e)
        return {"log": [], "count": 0, "error": str(e)}


@router.get("/execution/authority")
async def execution_authority(layer: str = "native"):
    """Authority preview using live governance engine."""
    try:
        from substrate.governance.policy_engine import PolicyEngine

        engine = PolicyEngine()
        return {
            "layer": layer,
            "authority_class": "operator",
            "safe_roots": engine.safe_roots,
            "risk_class": "LOW",
            "approval_requirement": "none"
            if layer in ("native", "container")
            else "operator_review",
        }
    except Exception as e:
        logger.debug("execution_authority: %s", e)
        return {
            "layer": layer,
            "authority_class": "operator",
            "risk_class": "LOW",
            "approval_requirement": "none",
        }


@router.post("/execution/start", dependencies=[Depends(_require_operator_role)])
async def execution_start(request: Request):
    """Start execution of a work packet through the governed spine."""
    body = await request.json()
    packet_id = body.get("packet_id", "")
    if not packet_id:
        return {"ok": False, "error": "packet_id is required"}

    from substrate.organism.work_packet_engine import WorkPacketEngine
    from substrate.organism.work_packet import PacketLifecycleStatus

    wpe = WorkPacketEngine()
    pkt = wpe.get_packet(packet_id)
    if not pkt:
        return {"ok": False, "error": f"Work packet {packet_id} not found"}

    if pkt.approval_gates and pkt.status != PacketLifecycleStatus.APPROVED:
        return {
            "ok": False,
            "error": "Work packet requires approval before execution",
            "status": pkt.status.value,
            "approval_gates": pkt.approval_gates,
        }

    if pkt.status == PacketLifecycleStatus.APPROVED:
        ok = wpe.update_packet_status(
            packet_id, PacketLifecycleStatus.DELEGATED, "delegated for execution"
        )
        if ok:
            ok = wpe.update_packet_status(
                packet_id, PacketLifecycleStatus.EXECUTING, "execution started"
            )
    elif pkt.status == PacketLifecycleStatus.DELEGATED:
        ok = wpe.update_packet_status(
            packet_id, PacketLifecycleStatus.EXECUTING, "execution started"
        )
    else:
        return {
            "ok": False,
            "error": f"Cannot start execution from status '{pkt.status.value}'",
            "valid_start_statuses": ["approved", "delegated"],
        }

    from substrate.execution.runtime.capability_router import (
        detect_capability,
        route_capability,
    )

    cap = detect_capability(pkt.user_intent or pkt.title)
    routing_result: dict[str, Any] = {
        "capability": cap.value,
        "routed": False,
        "provider": None,
        "error": None,
    }
    try:
        result = route_capability(pkt.user_intent or pkt.title)
        if result is not None:
            routing_result["routed"] = True
            routing_result["provider"] = result.provider_id
        else:
            from adapters.models.model_router import call_with_fallback

            llm_result = call_with_fallback(
                prompt=pkt.user_intent or pkt.title,
                system="Execute this work packet concisely.",
                task_type="command",
            )
            routing_result["routed"] = bool(llm_result)
            routing_result["provider"] = "llm_fallback" if llm_result else None
            if not llm_result:
                routing_result["error"] = "UNAVAILABLE"
    except Exception as exc:
        logger.debug("execution routing failed: %s", exc)
        routing_result["error"] = f"UNAVAILABLE: {exc}"

    return {
        "ok": ok,
        "packet_id": packet_id,
        "status": "executing",
        "routing": routing_result,
    }


@router.post("/execution/stop", dependencies=[Depends(_require_operator_role)], deprecated=True)
async def execution_stop(request: Request):
    """DEPRECATED — use POST /workstation/execution/stop instead."""
    body = await request.json()
    packet_id = body.get("packet_id", "")
    if not packet_id:
        return {"ok": False, "error": "packet_id is required"}
    from substrate.organism.work_packet_engine import WorkPacketEngine
    from substrate.organism.work_packet import PacketLifecycleStatus

    wpe = WorkPacketEngine()
    ok = wpe.update_packet_status(packet_id, PacketLifecycleStatus.BLOCKED, "stopped by operator")
    return {"ok": ok, "packet_id": packet_id, "deprecated": "use POST /workstation/execution/stop"}


@router.post("/execution/pause", dependencies=[Depends(_require_operator_role)], deprecated=True)
async def execution_pause(request: Request):
    """DEPRECATED — use POST /workstation/execution/pause instead."""
    body = await request.json()
    packet_id = body.get("packet_id", "")
    if not packet_id:
        return {"ok": False, "error": "packet_id is required"}
    from substrate.organism.work_packet_engine import WorkPacketEngine
    from substrate.organism.work_packet import PacketLifecycleStatus

    wpe = WorkPacketEngine()
    ok = wpe.update_packet_status(packet_id, PacketLifecycleStatus.BLOCKED, "paused by operator")
    return {"ok": ok, "packet_id": packet_id, "deprecated": "use POST /workstation/execution/pause"}


@router.post("/execution/complete", dependencies=[Depends(_require_operator_role)])
async def execution_complete(request: Request):
    """Mark a work packet as completed, triggering outcome recording and verification."""
    body = await request.json()
    packet_id = body.get("packet_id", "")
    if not packet_id:
        return {"ok": False, "error": "packet_id is required"}
    reason = body.get("reason", "completed by operator")

    from substrate.organism.work_packet_engine import WorkPacketEngine
    from substrate.organism.work_packet import PacketLifecycleStatus

    wpe = WorkPacketEngine()
    pkt = wpe.get_packet(packet_id)
    if not pkt:
        return {"ok": False, "error": f"Work packet {packet_id} not found"}

    if pkt.status == PacketLifecycleStatus.EXECUTING:
        ok = wpe.update_packet_status(
            packet_id, PacketLifecycleStatus.VALIDATING, "validating before completion"
        )
        if ok:
            verification = wpe.run_verification(packet_id)
            pkt = wpe.get_packet(packet_id)
            if pkt and pkt.verification_passed is False:
                wpe.update_packet_status(
                    packet_id, PacketLifecycleStatus.FAILED, "verification failed"
                )
                return {
                    "ok": False,
                    "packet_id": packet_id,
                    "status": "failed",
                    "reason": "verification failed",
                    "verification": verification,
                }
            ok = wpe.update_packet_status(packet_id, PacketLifecycleStatus.COMPLETED, reason)
    elif pkt.status == PacketLifecycleStatus.VALIDATING:
        ok = wpe.update_packet_status(packet_id, PacketLifecycleStatus.COMPLETED, reason)
    else:
        return {
            "ok": False,
            "error": f"Cannot complete from status '{pkt.status.value}'",
            "valid_statuses": ["executing", "validating"],
        }

    return {
        "ok": ok,
        "packet_id": packet_id,
        "status": "completed",
        "outcome_observation_id": pkt.outcome_observation_id if pkt else "",
        "verification_passed": pkt.verification_passed if pkt else None,
    }


@router.post("/execution/fail", dependencies=[Depends(_require_operator_role)])
async def execution_fail(request: Request):
    """Mark a work packet as failed, triggering failure outcome recording."""
    body = await request.json()
    packet_id = body.get("packet_id", "")
    if not packet_id:
        return {"ok": False, "error": "packet_id is required"}
    reason = body.get("reason", "failed")

    from substrate.organism.work_packet_engine import WorkPacketEngine
    from substrate.organism.work_packet import PacketLifecycleStatus

    wpe = WorkPacketEngine()
    pkt = wpe.get_packet(packet_id)
    if not pkt:
        return {"ok": False, "error": f"Work packet {packet_id} not found"}

    if pkt.status not in (
        PacketLifecycleStatus.EXECUTING,
        PacketLifecycleStatus.VALIDATING,
        PacketLifecycleStatus.DELEGATED,
    ):
        return {
            "ok": False,
            "error": f"Cannot fail from status '{pkt.status.value}'",
            "valid_statuses": ["executing", "validating", "delegated"],
        }

    ok = wpe.update_packet_status(packet_id, PacketLifecycleStatus.FAILED, reason)
    return {
        "ok": ok,
        "packet_id": packet_id,
        "status": "failed",
        "outcome_observation_id": pkt.outcome_observation_id if pkt else "",
    }


@router.post("/execution/resume", dependencies=[Depends(_require_operator_role)], deprecated=True)
async def execution_resume(request: Request):
    """DEPRECATED — use POST /workstation/execution/resume instead."""
    body = await request.json()
    packet_id = body.get("packet_id", "")
    if not packet_id:
        return {"ok": False, "error": "packet_id is required"}
    from substrate.organism.work_packet_engine import WorkPacketEngine
    from substrate.organism.work_packet import PacketLifecycleStatus

    wpe = WorkPacketEngine()
    ok = wpe.update_packet_status(
        packet_id, PacketLifecycleStatus.CLASSIFIED, "resumed by operator"
    )
    return {
        "ok": ok,
        "packet_id": packet_id,
        "deprecated": "use POST /workstation/execution/resume",
    }


# ── Provider Health ────────────────────────────────────────────────────────────


@router.get("/providers/health")
async def providers_health():
    """Return the runtime portfolio — roles, slots, provider status, and purpose routing."""
    from adapters.models.model_router import (
        MODEL_REGISTRY,
        ROLE_SLOTS,
        PURPOSE_ROUTING,
        ROLE_FAILOVER,
        ProviderRole,
        get_router,
    )

    router = get_router()
    router._check_availability()

    portfolio = []
    for key, cfg in MODEL_REGISTRY.items():
        # Determine which role this provider fills (if any)
        role = None
        for r, slot_key in ROLE_SLOTS.items():
            if slot_key == key:
                role = r.value
                break

        portfolio.append(
            {
                "key": key,
                "role": role,
                "provider": cfg.provider.value,
                "model": cfg.model_id,
                "available": cfg.available,
                "status": cfg.status_reason or ("healthy" if cfg.available else "unavailable"),
                "base_url": cfg.base_url or None,
                "cost_per_1k": cfg.cost_per_1k,
            }
        )

    slotted = [p for p in portfolio if p["role"]]
    unslotted = [p for p in portfolio if not p["role"]]

    # Count healthy roles
    healthy_roles = sum(1 for p in slotted if p["available"])

    from substrate.execution.cpu_gate import cpu_gate_status

    # Beast GPU status (best-effort, non-blocking)
    beast_gpu = None
    beast_cfg = MODEL_REGISTRY.get("beast-ollama")
    if beast_cfg and beast_cfg.available:
        try:
            import requests as _req

            ps_resp = _req.get(f"{beast_cfg.base_url}/api/ps", timeout=2)
            if ps_resp.status_code == 200:
                ps_data = ps_resp.json()
                beast_gpu = {
                    "node": "beast",
                    "gpu": "GTX 1080 Ti",
                    "vram_total_mb": 11264,
                    "models_loaded": len(ps_data.get("models", [])),
                    "status": "active" if ps_data.get("models") else "idle",
                }
        except Exception:
            pass

    return {
        "portfolio": slotted,
        "unslotted": unslotted,
        "purpose_routing": {k: [r.value for r in v] for k, v in PURPOSE_ROUTING.items()},
        "healthy_roles": healthy_roles,
        "total_roles": len(ROLE_SLOTS),
        "cpu_gate": cpu_gate_status(),
        "beast_gpu": beast_gpu,
        "system_status": "operational"
        if healthy_roles >= 2
        else "degraded"
        if healthy_roles >= 1
        else "critical",
    }


# ── Intent classification (WP-2.1) ────────────────────────────────────────────


@router.post("/intent/classify", dependencies=[Depends(_require_operator_role)])
async def intent_classify(request: Request):
    """Classify operator text through the spine's deterministic intent engine
    and persist the event to ConversationMemory."""
    body = await request.json()
    text = (body.get("text") or "").strip()
    if not text:
        return {"ok": False, "error": "text is required"}

    from substrate.execution.spine import _INTENT_PATTERNS

    intent = "unknown"
    for pattern, matched_intent in _INTENT_PATTERNS:
        if pattern.search(text):
            intent = matched_intent
            break

    event_id = ""
    try:
        from substrate.state.memory.memory import ConversationMemory

        mem = ConversationMemory()
        org_id = os.environ.get("UMH_ORG_ID") or os.environ.get("EOS_ORG_ID", "")
        if org_id:
            event_id = mem.log_event(
                org_id=org_id,
                event_type="intent_classified",
                payload={"text": text[:500], "intent": intent},
                handled_by="cockpit_intent_classify",
            )
    except Exception as exc:
        logger.debug("intent_classify persistence failed: %s", exc)

    return {
        "ok": True,
        "intent": intent,
        "confidence": "deterministic",
        "persisted": bool(event_id),
        "event_id": event_id,
    }


# ── Chat endpoints (operator ↔ DEX right-rail conversation) ───────────────────


@router.get("/chat/history")
async def chat_history():
    """Return chat history for the cockpit right-rail ChatDrawer."""
    try:
        from substrate.organism.store import OrganismStore

        store = OrganismStore()
        messages = store.list_messages(limit=50)
        result = []
        for m in messages:
            intent = m.get("intent", "")
            payload = m.get("payload", {})
            raw_sender = m.get("sender", "system")
            attachment = None
            if intent == "report" and raw_sender in ("system", "dex", ""):
                meta = payload.get("metadata", {})
                title = str(payload.get("title", "Report"))[:200]
                summary = payload.get("summary", "")
                file_path = str(payload.get("file_path", ""))[:500]
                conv_id = m.get("conversation_id", "")
                content = summary
                sender = "assistant"
                provenance: dict[str, Any] = {
                    "node": "VPS",
                    "harness": "Claude Code",
                }
                if conv_id:
                    provenance["session"] = str(conv_id)[:12]
                if meta.get("phase"):
                    provenance["phase"] = str(meta["phase"])[:20]
                if meta.get("pr"):
                    provenance["pr"] = (
                        int(meta["pr"]) if str(meta["pr"]).isdigit() else str(meta["pr"])[:20]
                    )
                if meta.get("task"):
                    provenance["task"] = str(meta["task"])[:100]
                if file_path:
                    filename = file_path.rsplit("/", 1)[-1] if "/" in file_path else file_path
                    attachment = {"path": file_path, "filename": filename}
            elif intent == "converse":
                content = payload.get("content", "")
                sender = "operator" if raw_sender == "operator" else "assistant"
                provenance = None
            else:
                content = (
                    payload.get("content", "") or payload.get("task", "") or str(payload)[:200]
                )
                sender = "operator" if raw_sender == "operator" else "assistant"
                provenance = None
            entry: dict[str, Any] = {
                "id": m.get("id", ""),
                "sender": sender,
                "content": content,
                "timestamp": m.get("created_at", ""),
                "origin_channel": m.get("origin_channel"),
            }
            if intent == "report":
                entry["intent"] = "report"
                entry["title"] = title
                if provenance:
                    entry["provenance"] = {k: v for k, v in provenance.items() if v}
                if attachment:
                    entry["attachment"] = attachment
            result.append(entry)
        return result
    except Exception as e:
        logger.error("chat_history failed: %s", e)
        return []


@router.post("/chat/converse", dependencies=[Depends(_require_operator_role)])
async def chat_converse(request: Request):
    """Route operator message through organism conversation pipeline."""
    body = await request.json()
    content = (body.get("content") or "").strip()
    if not content:
        return JSONResponse({"error": "content is required"}, status_code=400)
    try:
        from substrate.organism.store import OrganismStore

        store = OrganismStore()
        inbound, outbound = store.save_conversation_turn(
            content=content,
            response="Acknowledged. Processing via organism.",
            origin_channel="cockpit",
        )
        return {
            "message_id": str(inbound.id),
            "response": outbound.payload.get("content", "Acknowledged."),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error("chat_converse failed: %s", e)
        return {
            "message_id": f"dex-{int(time.time() * 1000)}",
            "response": "Internal error — check server logs.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.post("/chat/send", dependencies=[Depends(_require_operator_role)])
async def chat_send(request: Request):
    """Send a message — writes to organism store + pushes to cockpit WS."""
    body = await request.json()
    content = (body.get("content") or "").strip()
    if not content:
        return JSONResponse({"error": "content is required"}, status_code=400)
    try:
        from substrate.organism.store import OrganismStore

        store = OrganismStore()
        inbound, _ = store.save_conversation_turn(
            content=content,
            response="",
            origin_channel="cockpit",
        )
        push_chat_message(
            {
                "sender": "operator",
                "content": content,
                "origin_channel": "cockpit",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        return {"success": True, "message_id": str(inbound.id)}
    except Exception as e:
        logger.error("chat_send failed: %s", e)
        return JSONResponse({"error": "internal error"}, status_code=500)


@router.post("/chat/push")
async def chat_push(request: Request):
    """Push a chat message to connected cockpit WS clients."""
    body = await request.json()
    push_chat_message(body)
    return {"ok": True}


@router.get("/chat/attachment")
async def chat_attachment(path: str):
    """Download an attachment file referenced in a chat message."""
    from pathlib import Path as PathLib

    from fastapi.responses import FileResponse

    repo_root = os.environ.get("UMH_ROOT", "/opt/OS")
    if path.startswith("/opt/OS/") and repo_root != "/opt/OS":
        path = os.path.join(repo_root, path[len("/opt/OS/") :])
    allowed_dirs = [
        PathLib(os.path.realpath(os.path.join(repo_root, "docs"))),
        PathLib(os.path.realpath(os.path.join(repo_root, "data", "audits"))),
    ]
    resolved = PathLib(os.path.realpath(path))
    if not any(resolved.is_relative_to(d) for d in allowed_dirs):
        raise HTTPException(status_code=403, detail="Path outside allowed directories")
    if resolved.name.startswith("."):
        raise HTTPException(status_code=403, detail="Hidden files not allowed")
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        str(resolved), filename=resolved.name, media_type="application/octet-stream"
    )


# ── Bootstrap (single-request boot) ──────────────────────────────────────────


@router.get("/bootstrap")
async def bootstrap():
    """Aggregate boot-critical data in one response.

    Replaces ~15 parallel GET requests the cockpit fires on page load.
    Each source is independently faulted — partial data is fine.
    """
    errors: list[str] = []
    result: dict[str, Any] = {"ok": True, "ts": ""}

    import datetime as _dt

    result["ts"] = _dt.datetime.now(_dt.timezone.utc).isoformat()

    # config
    try:
        from substrate.sockets.config_port import get_all_config

        result["config"] = get_all_config()
    except Exception as e:
        errors.append(f"config: {e}")
        result["config"] = {}

    # pulse
    try:
        node_metrics = _build_node_metrics()
        vps = node_metrics.get("vps", {})
        traces = _read_jsonl(TRACE_STORE)
        pending_traces = sum(1 for t in traces[-500:] if t.get("status") == "pending")
        uptime = int(time.time() - psutil.boot_time())
        daemon = _get_organism()
        active_agents = 0
        pending_approvals = 0
        if daemon is not None:
            active_agents = sum(
                1 for a in daemon.advisor.list_agents() if a.get("status") != "offline"
            )
            pending_approvals = daemon.approval_store.pending_count()
        result["pulse"] = {
            "uptime": uptime,
            "cpu_percent": vps.get("cpu", 0),
            "memory_percent": vps.get("memory", 0),
            "disk_percent": vps.get("disk", 0),
            "active_agents": active_agents,
            "pending_tasks": pending_traces,
            "pending_approvals": pending_approvals,
            "trace_rate": round(len(traces) / max(uptime / 3600, 1), 1),
            "node_metrics": node_metrics,
        }
    except Exception as e:
        errors.append(f"pulse: {e}")
        result["pulse"] = {}

    # organism status
    try:
        daemon = _get_organism()
        if daemon is not None:
            result["organism"] = {
                "running": True,
                "agent_count": len(daemon.advisor.list_agents()),
                "workcell_count": len(getattr(daemon, "workcells", [])),
            }
        else:
            result["organism"] = {"running": False}
    except Exception as e:
        errors.append(f"organism: {e}")
        result["organism"] = {"running": False}

    # mode-composite
    try:
        from substrate.workstation.mode_resolver import resolve_composite_mode

        result["mode_composite"] = resolve_composite_mode()
    except Exception as e:
        errors.append(f"mode_composite: {e}")
        result["mode_composite"] = {}

    # continuity — full composite state
    try:
        from substrate.workstation.continuity_engine import ContinuityEngine

        engine = ContinuityEngine()
        composite = engine.get_composite_state()
        result["continuity"] = composite.to_dict()
    except Exception as e:
        # Fallback to basic state machine if engine fails
        try:
            from transports.api.cockpit_workstation_control_routes import _get_continuity_machine

            machine = _get_continuity_machine()
            result["continuity"] = {
                "current_state": machine.current_state.value,
                "valid_transitions": [s.value for s in machine.valid_transitions()],
            }
        except Exception:
            errors.append(f"continuity: {e}")
            result["continuity"] = {}

    # command-center summary (lightweight subset)
    try:
        from transports.api.cockpit_command_center_routes import (
            _load_workcell_heartbeats,
            _load_approvals,
        )

        heartbeats = _load_workcell_heartbeats()
        pending = _load_approvals(status_filter="pending")
        result["command_center"] = {
            "active_workcells": sum(1 for h in heartbeats if h.get("status") == "active"),
            "idle_workcells": sum(1 for h in heartbeats if h.get("status") == "idle"),
            "pending_approvals": len(pending),
        }
    except Exception as e:
        errors.append(f"command_center: {e}")
        result["command_center"] = {}

    # overnight
    try:
        from substrate.workstation.overnight_queue import OvernightQueue

        queue = OvernightQueue()
        result["overnight"] = queue.morning_summary()
    except Exception as e:
        errors.append(f"overnight: {e}")
        result["overnight"] = {}

    # mesh node count
    try:
        nm = result.get("pulse", {}).get("node_metrics") or _build_node_metrics()
        result["mesh"] = {"node_count": len(nm)}
    except Exception as e:
        errors.append(f"mesh: {e}")
        result["mesh"] = {"node_count": 0}

    # chat / dex availability
    try:
        conv = _get_dex_conversation()
        result["dex_available"] = conv is not None
        result["chat_available"] = conv is not None
    except Exception:
        result["dex_available"] = False
        result["chat_available"] = False

    result["_errors"] = errors
    if errors:
        result["ok"] = False
    return result


# ── Config endpoints ──────────────────────────────────────────────────────────


@router.get("/config")
async def config_get():
    """Get resolved config (ai_name, timezone, theme, etc.)."""
    try:
        from substrate.sockets.config_port import get_all_config

        return get_all_config()
    except Exception as e:
        logger.error("config_get failed: %s", e)
        return {}


@router.patch("/config", dependencies=[Depends(_require_operator_role)])
async def config_patch(request: Request):
    """Set a config value. Body: {key, value, layer?}."""
    body = await request.json()
    key = body.get("key")
    value = body.get("value")
    layer = body.get("layer", "system")
    if not key:
        return JSONResponse({"error": "key is required"}, status_code=400)
    if value is None:
        return JSONResponse({"error": "value is required"}, status_code=400)
    try:
        from substrate.state.config.config_store import VALID_KEYS
        from substrate.sockets.config_port import set_config, get_config

        if key not in VALID_KEYS:
            return JSONResponse({"error": f"invalid config key: {key}"}, status_code=400)
        set_config(key, value, layer=layer)
        return {"ok": True, "key": key, "value": get_config(key), "layer": layer}
    except Exception as e:
        logger.error("config_patch failed: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)


# ── Phase 6.1→6.2: Spine routes extracted to cockpit_spine_router.py ─────────


def _mount_spine_router() -> None:
    from transports.api import cockpit_spine_router

    cockpit_spine_router.configure(
        get_organism_fn=_get_organism,
        check_rate_limit_fn=_check_rate_limit,
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_spine_router.spine_router)


_mount_spine_router()

# ── Phase 10.0: Organism core routes extracted to cockpit_organism_routes.py ──


def _mount_organism_router() -> None:
    from transports.api import cockpit_organism_routes

    cockpit_organism_routes.configure(
        get_organism_fn=_get_organism,
        check_rate_limit_fn=_check_rate_limit,
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_organism_routes.organism_router)


_mount_organism_router()


def _mount_entity_router() -> None:
    from transports.api import cockpit_entity_routes

    cockpit_entity_routes.configure(
        get_org_id_fn=_get_org_id,
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_entity_routes.entity_router)


_mount_entity_router()


def _mount_economy_router() -> None:
    from transports.api import cockpit_economy_routes

    cockpit_economy_routes.configure(
        get_organism_fn=_get_organism,
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_economy_routes.economy_router)


def _mount_autonomous_router() -> None:
    from transports.api import cockpit_autonomous_routes

    cockpit_autonomous_routes.configure(
        get_organism_fn=_get_organism,
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_autonomous_routes.autonomous_router)


def _mount_self_build_router() -> None:
    from transports.api import cockpit_self_build_routes

    cockpit_self_build_routes.configure(
        get_organism_fn=_get_organism,
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_self_build_routes.self_build_router)


def _mount_universal_work_router() -> None:
    from transports.api import cockpit_universal_work_routes

    cockpit_universal_work_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_universal_work_routes.universal_work_router)


def _mount_propagation_graph_router() -> None:
    from transports.api import cockpit_propagation_graph_routes

    cockpit_propagation_graph_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_propagation_graph_routes.propagation_graph_router)


def _mount_operator_experience_router() -> None:
    from transports.api import cockpit_operator_experience_routes

    cockpit_operator_experience_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_operator_experience_routes.operator_experience_router)


def _mount_runtime_surface_router() -> None:
    from transports.api import cockpit_runtime_surface_routes

    cockpit_runtime_surface_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_runtime_surface_routes.runtime_surface_router)


_mount_economy_router()
_mount_autonomous_router()
_mount_self_build_router()
_mount_universal_work_router()
_mount_propagation_graph_router()
_mount_operator_experience_router()
_mount_runtime_surface_router()


def _mount_context_assimilation_router() -> None:
    from transports.api import cockpit_context_assimilation_routes

    cockpit_context_assimilation_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_context_assimilation_routes.context_assimilation_router)


_mount_context_assimilation_router()

# ── Phase 14.7A: Reality Model routes ────────────────────────────────────────


def _mount_reality_model_router() -> None:
    from transports.api import cockpit_reality_model_routes

    cockpit_reality_model_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_reality_model_routes.reality_model_router)


_mount_reality_model_router()

# ── Phase 20: Reality Intelligence routes ─────────────────────────────────────


def _mount_reality_intelligence_router() -> None:
    from transports.api import cockpit_reality_intelligence_routes

    cockpit_reality_intelligence_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_reality_intelligence_routes.reality_intelligence_router,
    )


_mount_reality_intelligence_router()

# ── Phase 21: Meta IDE routes ─────────────────────────────────────────────


def _mount_meta_ide_router() -> None:
    from transports.api import cockpit_meta_ide_routes

    cockpit_meta_ide_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_meta_ide_routes.meta_ide_router,
    )


_mount_meta_ide_router()

# ── Phase 22: Engineering Loop routes ─────────────────────────────────────────


def _mount_engineering_loop_router() -> None:
    from transports.api import cockpit_engineering_routes

    cockpit_engineering_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_engineering_routes.engineering_router,
    )


_mount_engineering_loop_router()

# ── Phase 23: Engineering proof loop routes ───────────────────────────────────


def _mount_engineering_review_router() -> None:
    from transports.api import cockpit_engineering_review_routes

    cockpit_engineering_review_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_engineering_review_routes.engineering_review_router,
    )


_mount_engineering_review_router()

# ── Phase 14.7A: Operator loop routes ────────────────────────────────────────


def _mount_operator_loop_router() -> None:
    from transports.api import cockpit_operator_loop_routes

    cockpit_operator_loop_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_operator_loop_routes.operator_loop_router)


_mount_operator_loop_router()

# ── Phase 18: Operator timeline routes ─────────────────────────────────────


def _mount_operator_timeline_router() -> None:
    from transports.api import cockpit_operator_timeline_routes

    cockpit_operator_timeline_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_operator_timeline_routes.operator_timeline_router)


_mount_operator_timeline_router()

# ── Phase 14.7A: Self-improvement loop routes ─────────────────────────────


def _mount_self_improvement_router() -> None:
    from transports.api import cockpit_self_improvement_routes

    cockpit_self_improvement_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_self_improvement_routes.self_improvement_router)


_mount_self_improvement_router()

# ── Phase 14.11A: Workstation execution control routes ──────────────────────


def _mount_workstation_control_router() -> None:
    from transports.api import cockpit_workstation_control_routes

    cockpit_workstation_control_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_workstation_control_routes.workstation_control_router)


_mount_workstation_control_router()

# ── Phase 14.11C: Workspace routes (file browser, diff, tests, logs, proof, health) ──


def _mount_workspace_router() -> None:
    from transports.api import cockpit_workspace_routes

    cockpit_workspace_routes.configure(
        require_operator_dep=_require_operator_role,
        require_api_key_dep=_require_api_key,
    )
    router.include_router(cockpit_workspace_routes.workspace_router)


_mount_workspace_router()

# ── Phase 14.11D: Presence routes (activation, commands, capabilities) ──


def _mount_presence_router() -> None:
    from transports.api import cockpit_presence_routes

    cockpit_presence_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_presence_routes.presence_router)


_mount_presence_router()

# ── Phase 14.11E: Command center routes (agents, work packets, summary) ──


def _mount_command_center_router() -> None:
    from transports.api import cockpit_command_center_routes

    cockpit_command_center_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_command_center_routes.command_center_router)


_mount_command_center_router()


def _mount_rooms_router() -> None:
    from transports.api.cockpit_rooms_routes import rooms_router as _rooms_router
    from transports.api.cockpit_rooms_routes import rooms_public_router as _rooms_public

    router.include_router(_rooms_router)
    ws_router.include_router(_rooms_public)


_mount_rooms_router()


def _mount_broadcast_router() -> None:
    from transports.api.cockpit_broadcast_routes import broadcast_router as _br
    from transports.api.cockpit_broadcast_routes import broadcast_ws_router as _bws

    router.include_router(_br)
    ws_router.include_router(_bws)


_mount_broadcast_router()

# ── Claude Code Session Bridge ────────────────────────────────────────


def _log_cc_trace(session: str, text: str, packet_id: str, action: str) -> None:
    """Log Claude Code bridge action to execution journal."""
    import json as _json

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "source": "cc_bridge",
        "action": action,
        "session": session,
        "packet_id": packet_id,
        "text_preview": text[:100] if text else "",
    }
    journal = os.path.join(
        os.environ.get("UMH_ROOT", "/opt/OS"),
        "data",
        "umh",
        "organism",
        "execution_journal.jsonl",
    )
    try:
        os.makedirs(os.path.dirname(journal), exist_ok=True)
        with open(journal, "a") as f:
            f.write(_json.dumps(entry) + "\n")
    except Exception:
        pass


_RISKY_KEYWORDS = [
    "delete",
    "drop",
    "rm -rf",
    "force push",
    "reset --hard",
    "truncate",
    "--no-verify",
    "destroy",
]


@router.post("/claude-session/send")
async def claude_session_send(payload: dict) -> dict:  # type: ignore[type-arg]
    """Send a prompt to a Claude Code session via tmux bridge. Governed."""
    from substrate.execution.bridge.claude_session_bridge import (
        ensure_session,
        send_message,
    )

    session_name = payload.get("session_name", "")
    text = payload.get("text", "")
    target = payload.get("target", "local")
    work_packet_id = payload.get("work_packet_id", "")
    if not session_name or not text:
        return {"error": "session_name and text required"}
    text_lower = text.lower()
    blocked = [kw for kw in _RISKY_KEYWORDS if kw in text_lower]
    if blocked:
        return {
            "error": "risky_prompt_blocked",
            "reason": "Prompt contains risky keywords.",
            "blocked_keywords": blocked,
        }
    ensure_result = ensure_session(target, session_name)
    if not ensure_result.get("ok"):
        return {"error": "session not available: %s" % ensure_result.get("reason", "unknown")}
    send_result = send_message(target, session_name, text)
    _log_cc_trace(session_name, text, work_packet_id, "send")
    base: dict = send_result if isinstance(send_result, dict) else {"ok": True}  # type: ignore[assignment]
    return {**base, "work_packet_id": work_packet_id, "traced": True}


@router.post("/claude-session/capture")
async def claude_session_capture(payload: dict) -> dict:  # type: ignore[type-arg]
    """Capture output from a Claude Code session."""
    from substrate.execution.bridge.claude_session_bridge import capture_output

    session_name = payload.get("session_name", "")
    target = payload.get("target", "local")
    work_packet_id = payload.get("work_packet_id", "")
    if not session_name:
        return {"error": "session_name required"}
    result = capture_output(target, session_name)
    _log_cc_trace(session_name, "", work_packet_id, "capture")
    base: dict = result if isinstance(result, dict) else {"output": str(result)}  # type: ignore[assignment]
    return {**base, "work_packet_id": work_packet_id}


@router.get("/claude-session/list")
async def claude_session_list() -> dict:  # type: ignore[type-arg]
    """List active Claude Code sessions."""
    from substrate.execution.bridge.claude_session_bridge import list_sessions

    return list_sessions()  # type: ignore[return-value]


@router.post("/tmux/send")
async def tmux_send(payload: dict) -> dict:  # type: ignore[type-arg]
    """Send keys to a tmux session (governed via TmuxOperationalAdapter)."""
    session_name = payload.get("session_name", "")
    text = payload.get("text", "")
    if not session_name or not text:
        return {"error": "session_name and text required"}
    try:
        from substrate.execution.workers.workstation.tmux_operational_adapter_v1 import (
            TmuxOperationalAdapter,
        )

        adapter = TmuxOperationalAdapter()
        result = adapter.send_approved_command(session_name, text)
        if hasattr(result, "to_dict"):
            return result.to_dict()  # type: ignore[union-attr]
        return result if isinstance(result, dict) else {"ok": True}
    except Exception as exc:
        return {"error": str(exc)}


@router.post("/council/review")
async def council_review(payload: dict) -> dict:  # type: ignore[type-arg]
    """Trigger council review for a decision."""
    from substrate.organism.council import Council

    council = Council()
    review = council.review(
        decision_context=payload.get("context", ""),
        proposed_plan=payload.get("plan", ""),
        artifacts=payload.get("artifacts"),
    )
    return {"ok": True, "review": review.to_dict()}


# ─── Device Presence Registry ─────────────────────────────────────────────────

@router.post("/device/register")
async def device_register(payload: dict) -> dict:
    """Register a device session with the presence registry."""
    from substrate.workstation.device_presence import DeviceSession, get_registry

    session_id = payload.get("session_id", "")
    device_id = payload.get("device_id", "")
    if not session_id or not device_id:
        raise HTTPException(status_code=400, detail="session_id and device_id required")

    session = DeviceSession(
        device_id=device_id,
        session_id=session_id,
        operator_id=payload.get("operator_id", "default"),
        client_type=payload.get("client_type", "desktop_browser"),
        device_label=payload.get("device_label", ""),
        control_surface=payload.get("control_surface", "fly_cockpit"),
        current_panel=payload.get("current_panel", ""),
        can_capture_audio=bool(payload.get("can_capture_audio", True)),
        can_play_audio=bool(payload.get("can_play_audio", True)),
        reachable_nodes=payload.get("reachable_nodes", ["cockpit", "vps"]),
    )
    get_registry().register_session(session)
    return {"ok": True, "session_id": session_id}


@router.post("/device/heartbeat")
async def device_heartbeat(payload: dict) -> dict:
    """Heartbeat — refresh session last_seen and apply optional field updates."""
    from substrate.workstation.device_presence import get_registry

    session_id = payload.get("session_id", "")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    updates = {k: v for k, v in payload.items() if k != "session_id"}
    found = get_registry().heartbeat(session_id, updates=updates or None)
    if not found:
        return {"ok": False, "reason": "session not found"}
    return {"ok": True}


@router.get("/device/sessions")
async def device_sessions() -> dict:
    """List all active device sessions."""
    from substrate.workstation.device_presence import get_registry

    sessions = get_registry().get_active_sessions()
    return {"sessions": [s.to_dict() for s in sessions]}


@router.post("/device/disconnect")
async def device_disconnect(payload: dict) -> dict:
    """Mark a session as disconnected."""
    from substrate.workstation.device_presence import get_registry

    session_id = payload.get("session_id", "")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    get_registry().mark_disconnected(session_id)
    return {"ok": True}

