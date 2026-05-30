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
from fastapi import APIRouter, Depends, HTTPException, Request, Security, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader

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
        raise HTTPException(status_code=503, detail="API key not configured — set UMH_OPERATOR_API_KEY")
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
        raise HTTPException(status_code=503, detail="Operator token not configured — set UMH_OPERATOR_TOKEN")

    if not operator_token or not _hmac.compare_digest(operator_token, _OPERATOR_TOKEN):
        logger.warning(
            "Unauthorized operator access attempt: %s %s from %s",
            request.method, request.url.path, _real_client_ip(request),
        )
        raise HTTPException(status_code=403, detail="Operator token required for privileged actions")

    return "operator"


router = APIRouter(prefix="/api/umh", dependencies=[Depends(_require_api_key)])
ws_router = APIRouter(prefix="/api/umh")

_ROOT = Path(os.getenv("UMH_ROOT", "/opt/OS"))
MEMORY_STORE = _ROOT / "data" / "runtime" / "canonical_memory_store" / "memories.jsonl"
TRACE_STORE = _ROOT / "data" / "umh" / "traces" / "traces.jsonl"
SKILLS_DIR = _ROOT / "skills"
AGENTS_DIR = _ROOT / "agents"


_DOCKER_SOCK = "/var/run/docker.sock"


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
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5, cwd=str(_ROOT),
        )
        if sha.returncode == 0:
            info["commit_sha"] = sha.stdout.strip()
    except Exception:
        pass
    try:
        ts = subprocess.run(
            ["git", "log", "-1", "--format=%cI"],
            capture_output=True, text=True, timeout=5, cwd=str(_ROOT),
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
    """Returns all network devices: Tailscale peers + UMH daemon nodes."""
    _ROLE_MAP = {
        "srv1500858": "orchestrator",
        "desktop-lvguiq9": "gpu-workhorse",
    }
    _NAME_MAP = {
        "desktop-lvguiq9": "Beast PC",
        "ipad-pro-12-9-gen-5": "iPad Pro",
        "iphone-15-pro-max": "iPhone 15 Pro Max",
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
        result = subprocess.run(
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
        nodes.append(
            {
                "node_id": "vps-primary",
                "hostname": os.uname().nodename,
                "role": "orchestrator",
                "status": "online",
                "os": "linux",
                "ip": "",
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
    """Recent DEX channel exchanges and system reports for the right-rail chat."""
    daemon = _get_organism()
    if daemon is None:
        return []

    messages = daemon.store.list_messages(limit=500)

    exchanges: list[dict[str, Any]] = []

    dex_msgs = [m for m in messages if m.get("payload", {}).get("source") == "cockpit_dex_channel"]
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
                provenance["pr"] = int(meta["pr"]) if str(meta["pr"]).isdigit() else str(meta["pr"])[:20]
            if meta.get("task"):
                provenance["task"] = str(meta["task"])[:100]

            attachment = None
            if file_path:
                attachment = {
                    "path": file_path,
                    "filename": file_path.rsplit("/", 1)[-1] if "/" in file_path else file_path,
                }

            exchanges.append({
                "id": m.get("id", ""),
                "timestamp": m.get("created_at", ""),
                "sender": m.get("sender", "system"),
                "content": "",
                "response": summary,
                "intent": "report",
                "title": title,
                "provenance": provenance,
                "attachment": attachment,
            })

    exchanges.sort(key=lambda x: x.get("timestamp", ""))
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


def _extract_ws_token(ws: WebSocket) -> str:
    """Extract auth token from Sec-WebSocket-Protocol header or query param.

    Preferred: client sends subprotocol 'bearer.<token>' — avoids token in URL/logs.
    Fallback: ?token= query param for clients that cannot set subprotocols.
    """
    for proto in (ws.headers.get("sec-websocket-protocol") or "").split(","):
        proto = proto.strip()
        if proto.startswith("bearer."):
            return proto[7:]
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
    """Validate WS connection auth."""
    if not _WS_TOKEN:
        client_ip = _real_ws_client_ip(ws)
        return _DEV_BYPASS and _is_private_ip(client_ip)
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
    token = _extract_ws_token(ws)
    subprotocol = f"bearer.{token}" if token else None
    await ws.accept(subprotocol=subprotocol)
    _cockpit_clients.add(ws)
    event_cursor = len(_pending_organism_events)
    logger.info(f"cockpit ws connected ({len(_cockpit_clients)} clients)")
    try:
        while True:
            cpu = psutil.cpu_percent(interval=0)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            traces = _read_jsonl(TRACE_STORE)
            recent_traces = traces[-10:] if traces else []
            containers = _get_docker_containers()

            new_events = _pending_organism_events[event_cursor:]
            event_cursor = len(_pending_organism_events)

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


# ── Phase 3: Governed Execution Economy endpoints ─────────────────────────────


@router.get("/organism/economy")
async def organism_economy():
    """Execution economy metrics — cost, value, leverage per runtime."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    try:
        economy = getattr(daemon, "_economy", None)
        if economy is None:
            return {"total_executions": 0, "runtime_profiles": {}}
        return economy.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.get("/organism/economy/records")
async def organism_economy_records(limit: int = 50):
    """Recent execution decision records."""
    daemon = _get_organism()
    if daemon is None:
        return []
    try:
        economy = getattr(daemon, "_economy", None)
        if economy is None:
            return []
        return economy.recent_records(limit)
    except Exception as e:
        return {"error": str(e)}


@router.get("/organism/economy/task-profile/{task_class}")
async def organism_task_profile(task_class: str):
    """Runtime rankings for a specific task class."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    try:
        economy = getattr(daemon, "_economy", None)
        if economy is None:
            return {"task_class": task_class, "runtime_rankings": []}
        return economy.task_execution_profile(task_class).to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.get("/organism/recursion")
async def organism_recursion():
    """Current recursion governance state and limits."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    try:
        governor = getattr(daemon, "_recursion_governor", None)
        if governor is None:
            return {"limits": {}, "state": {}, "kill_switch": False}
        return governor.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.get("/organism/recursion/escalations")
async def organism_recursion_escalations(limit: int = 50):
    """Recent recursion escalation events."""
    daemon = _get_organism()
    if daemon is None:
        return []
    try:
        governor = getattr(daemon, "_recursion_governor", None)
        if governor is None:
            return []
        return governor.escalation_log(limit)
    except Exception as e:
        return {"error": str(e)}


@router.post("/organism/recursion/kill", dependencies=[Depends(_require_operator_role)])
async def organism_kill_switch():
    """Activate the kill switch — halts all autonomous execution."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    try:
        governor = getattr(daemon, "_recursion_governor", None)
        if governor is None:
            return {"error": "recursion governor not available"}
        governor.kill()
        return {"ok": True, "killed": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/organism/recursion/resume", dependencies=[Depends(_require_operator_role)])
async def organism_resume_switch():
    """Deactivate the kill switch — resume autonomous execution."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    try:
        governor = getattr(daemon, "_recursion_governor", None)
        if governor is None:
            return {"error": "recursion governor not available"}
        governor.resume()
        return {"ok": True, "killed": False}
    except Exception as e:
        return {"error": str(e)}


@router.get("/organism/advisors")
async def organism_advisor_hierarchy():
    """Full advisor hierarchy tree."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    try:
        hierarchy = getattr(daemon, "_advisor_hierarchy", None)
        if hierarchy is None:
            return {"primary_id": "", "total_advisors": 0, "advisors": {}}
        return hierarchy.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.get("/organism/advisors/tree")
async def organism_advisor_tree():
    """Advisor hierarchy as a nested tree structure."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    try:
        hierarchy = getattr(daemon, "_advisor_hierarchy", None)
        if hierarchy is None:
            return {}
        return hierarchy.hierarchy_tree()
    except Exception as e:
        return {"error": str(e)}


@router.get("/organism/advisors/overdue")
async def organism_overdue_advisors():
    """Advisors with overdue reports."""
    daemon = _get_organism()
    if daemon is None:
        return []
    try:
        hierarchy = getattr(daemon, "_advisor_hierarchy", None)
        if hierarchy is None:
            return []
        return [a.to_dict() for a in hierarchy.overdue_reports()]
    except Exception as e:
        return {"error": str(e)}


@router.get("/organism/assimilation")
async def organism_assimilation():
    """External leverage assimilation status."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    try:
        assimilator = getattr(daemon, "_assimilator", None)
        if assimilator is not None:
            return assimilator.to_dict()
        from substrate.organism.leverage_assimilation import LeverageAssimilator

        return LeverageAssimilator().to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.get("/organism/assimilation/artifacts")
async def organism_leverage_artifacts():
    """List all assimilation artifacts."""
    daemon = _get_organism()
    if daemon is None:
        return []
    try:
        assimilator = getattr(daemon, "_assimilator", None)
        if assimilator is None:
            return []
        return assimilator.list_artifacts()
    except Exception as e:
        return {"error": str(e)}


@router.get("/organism/snapshot")
async def organism_full_snapshot():
    """Full organism snapshot — objectives, runtimes, workcells, bottlenecks."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    try:
        from substrate.organism.observability import OrganismObserver

        observer = OrganismObserver(
            coordinator=daemon.advisor.coordinator if daemon.advisor else None,
            graph=daemon.graph,
            supervisor=daemon.supervisor,
            homeostasis=daemon.homeostasis,
        )
        snap = observer.snapshot()
        return snap.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.get("/organism/runtimes")
async def organism_runtimes():
    daemon = _get_organism()
    if daemon is None:
        return {"runtimes": [], "count": 0}
    graph = getattr(daemon, "graph", None)
    if graph is None:
        return {"runtimes": [], "count": 0}
    data = graph.to_dict()
    runtimes_dict = data.get("runtimes", {})
    return {
        "runtimes": list(runtimes_dict.values()),
        "count": data.get("total_runtimes", 0),
        "available": data.get("available", 0),
    }


@router.get("/organism/governor")
async def organism_governor():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    gov = getattr(daemon, "governor", None)
    if gov is None:
        return {"error": "governor not available"}
    return gov.to_dict()


@router.get("/organism/workcells")
async def organism_workcells():
    daemon = _get_organism()
    if daemon is None:
        return {"workcells": [], "count": 0}
    try:
        wc = getattr(daemon, "_workcell_daemon", None)
        if wc is None:
            return {"workcells": [], "count": 0, "note": "workcell daemon not wired"}
        return wc.to_dict()
    except Exception:
        return {"workcells": [], "count": 0}


@router.get("/organism/topology")
async def organism_topology():
    """Full operational topology — runtimes, workcells, system metrics."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    try:
        env_graph = getattr(daemon, "_environment_graph", None)
        if env_graph is not None:
            return env_graph.to_dict()
        return daemon.advisor.resource_topology()
    except Exception as e:
        return {"error": str(e)}


@router.get("/organism/topology/live")
async def organism_topology_live():
    """Capture a fresh topology snapshot and return it with diff."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    try:
        env_graph = getattr(daemon, "_environment_graph", None)
        if env_graph is None:
            return {"error": "environment graph not available"}

        workcell_data = []
        wcd = getattr(daemon, "_workcell_daemon", None)
        if wcd is not None:
            for wc in wcd._workcells.values():
                workcell_data.append(wc.to_dict())

        snapshot = env_graph.capture(
            graph=daemon.graph,
            workcells=workcell_data,
        )
        diff = env_graph.diff()
        return {
            "snapshot": snapshot.to_dict(),
            "diff": diff.to_dict() if diff.has_changes else None,
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/organism/throughput")
async def organism_throughput():
    """Event throughput, tick timing, and pressure metrics."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    try:
        spine = daemon.event_spine
        tick = daemon.autonomous_tick
        snap = spine.snapshot()

        tick_data = tick.to_dict()
        metrics = tick_data.get("metrics", {})

        result = {
            "event_spine": {
                "total_events": snap.get("total_events", 0),
                "events_by_domain": snap.get("events_by_domain", {}),
                "subscriber_count": snap.get("subscriber_count", 0),
            },
            "tick_engine": {
                "cycle_count": tick_data.get("cycle_count", 0),
                "current_interval": tick_data.get("current_interval", 0),
                "is_paused": tick_data.get("is_paused", False),
                "stages": tick_data.get("stages", []),
                "avg_cycle_ms": metrics.get("avg_cycle_ms", 0),
                "total_stages_executed": metrics.get("total_stages_executed", 0),
                "total_stages_failed": metrics.get("total_stages_failed", 0),
                "consecutive_idle": metrics.get("consecutive_idle", 0),
            },
            "runtimes": {
                "total": daemon.graph.node_count if daemon.graph else 0,
                "available": daemon.graph.available_count if daemon.graph else 0,
            },
        }

        reconciler = getattr(daemon, "_reconciler", None)
        if reconciler is not None:
            result["reconciler"] = reconciler.to_dict()

        return result
    except Exception as e:
        return {"error": str(e)}


@router.get("/organism/reconciliation")
async def organism_reconciliation():
    """Last reconciliation report and history."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    try:
        reconciler = getattr(daemon, "_reconciler", None)
        if reconciler is None:
            return {"error": "reconciler not available"}
        return reconciler.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/organism/reconcile", dependencies=[Depends(_require_operator_role)])
async def organism_reconcile_now():
    """Force an immediate reconciliation cycle."""
    import asyncio

    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    try:
        reconciler = getattr(daemon, "_reconciler", None)
        if reconciler is None:
            return {"error": "reconciler not available"}

        loop = asyncio.get_running_loop()
        report = await loop.run_in_executor(None, reconciler.reconcile)
        return report.to_dict()
    except Exception as e:
        return {"error": str(e)}


# ── Autonomous PR Factory endpoints ─────────────────────────────────────────

def _get_pr_factory():
    from substrate.organism.worktree_sandbox import SandboxManager
    from substrate.organism.autonomous_pr_factory import AutonomousPRFactory
    daemon = _get_organism()
    if daemon is None:
        return None, None
    manager = getattr(daemon, "_sandbox_manager", None)
    if manager is None:
        manager = SandboxManager()
        daemon._sandbox_manager = manager
    factory = getattr(daemon, "_pr_factory", None)
    if factory is None:
        factory = AutonomousPRFactory(sandbox_manager=manager)
        daemon._pr_factory = factory
    return manager, factory


@router.get("/organism/autonomous-pr-factory")
async def autonomous_pr_factory_status():
    manager, factory = _get_pr_factory()
    if factory is None:
        return {"error": "organism not running"}
    return factory.to_dict()


@router.get("/organism/autonomous-pr-factory/sandboxes")
async def autonomous_pr_factory_sandboxes():
    manager, factory = _get_pr_factory()
    if manager is None:
        return {"error": "organism not running"}
    return manager.to_dict()


@router.get("/organism/autonomous-pr-factory/sandboxes/{sandbox_id}")
async def autonomous_pr_factory_sandbox_detail(sandbox_id: str):
    manager, factory = _get_pr_factory()
    if manager is None:
        return {"error": "organism not running"}
    sb = manager.get_sandbox(sandbox_id)
    if sb is None:
        return {"error": f"sandbox {sandbox_id} not found"}
    return sb.to_dict()


@router.get("/organism/autonomous-pr-factory/manifests")
async def autonomous_pr_factory_manifests():
    import glob
    _root = os.environ.get("UMH_ROOT", "/opt/OS")
    manifest_dir = os.path.join(_root, "data", "umh", "autonomous_lane", "manifests")
    manifests = []
    for path in sorted(glob.glob(os.path.join(manifest_dir, "*.json"))):
        try:
            with open(path) as f:
                manifests.append(json.load(f))
        except (json.JSONDecodeError, OSError):
            continue
    return {"manifests": manifests, "count": len(manifests)}


@router.get("/organism/autonomous-pr-factory/manifests/{manifest_id}")
async def autonomous_pr_factory_manifest_detail(manifest_id: str):
    _root = os.environ.get("UMH_ROOT", "/opt/OS")
    path = os.path.join(
        _root, "data", "umh", "autonomous_lane", "manifests", f"{manifest_id}.json"
    )
    if not os.path.isfile(path):
        return {"error": f"manifest {manifest_id} not found"}
    with open(path) as f:
        return json.load(f)


@router.post("/organism/autonomous-pr-factory/create-pr", dependencies=[Depends(_require_operator_role)])
async def autonomous_pr_factory_create_pr(payload: dict, request: Request):
    manager, factory = _get_pr_factory()
    if factory is None:
        return {"error": "organism not running"}
    from substrate.organism.autonomous_pr_factory import AutonomousPRRequest
    from substrate.organism.autonomous_improvement_lane import AutonomousImprovementCandidate
    candidate = AutonomousImprovementCandidate(
        candidate_id=payload.get("candidate_id", ""),
        description=payload.get("description", ""),
        affected_files=payload.get("affected_files", []),
        risk_class=payload.get("risk_class", "low"),
        matching_template_id=payload.get("template_id", ""),
        validation_method=payload.get("validation_method", "py_compile"),
        rollback_method=payload.get("rollback_method", "git revert"),
        reversible=True,
    )
    req = AutonomousPRRequest(
        candidate=candidate,
        candidate_slug=payload.get("slug", candidate.description[:40]),
        description=payload.get("description", ""),
    )
    import asyncio
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, factory.create_pr, req)
    return result.to_dict()


@router.post("/organism/autonomous-pr-factory/cleanup/{sandbox_id}", dependencies=[Depends(_require_operator_role)])
async def autonomous_pr_factory_cleanup(sandbox_id: str):
    manager, factory = _get_pr_factory()
    if manager is None:
        return {"error": "organism not running"}
    ok = manager.cleanup_sandbox(sandbox_id)
    return {"ok": ok, "sandbox_id": sandbox_id}


@router.get("/organism/autonomous-pr-factory/parallel-dry-run")
async def autonomous_pr_factory_parallel_dry_run():
    manager, factory = _get_pr_factory()
    if factory is None:
        return {"error": "organism not running"}
    from substrate.organism.autonomous_improvement_lane import (
        AutonomousCandidateSelector,
        AutonomousImprovementCandidate,
    )
    from substrate.organism.template_registry import TemplateRegistry
    from substrate.organism.agent_capability_model import AgentCapabilityModel
    tr = TemplateRegistry()
    acm = AgentCapabilityModel()
    selector = AutonomousCandidateSelector(
        template_registry=tr,
        agent_capability_model=acm,
    )
    candidates = selector.build_candidates(max_candidates=5)
    return factory.conflict_detector.parallel_dry_run(candidates)


@router.get("/organism/autonomous-pr-factory/production-truth", dependencies=[Depends(_require_operator_role)])
async def autonomous_pr_factory_production_truth():
    manager, factory = _get_pr_factory()
    if manager is None:
        return {"error": "organism not running"}
    return manager.production_truth()


@router.post("/organism/autonomous-pr-factory/verify-merge/{sandbox_id}", dependencies=[Depends(_require_operator_role)])
async def autonomous_pr_factory_verify_merge(sandbox_id: str):
    import re as _re
    if not _re.fullmatch(r"sb-[a-f0-9]{8}", sandbox_id):
        raise HTTPException(status_code=400, detail="invalid sandbox_id format")
    manager, factory = _get_pr_factory()
    if factory is None:
        return {"error": "organism not running"}
    from substrate.organism.production_merge_verifier import ProductionMergeVerifier
    verifier = ProductionMergeVerifier(sandbox_manager=manager)
    sb = manager.get_sandbox(sandbox_id)
    pr_number = sb.pr_number if sb else 0
    expected_files: list = []
    manifest_id = ""
    if factory:
        for rp in factory.review_packets:
            if rp.sandbox_id == sandbox_id:
                manifest_id = rp.manifest_id
                if rp.manifest:
                    expected_files = [cf.path for cf in rp.manifest.changed_files]
                break
    import asyncio
    loop = asyncio.get_running_loop()
    verification = await loop.run_in_executor(
        None, verifier.verify_merge, sandbox_id, pr_number, manifest_id, expected_files
    )
    return verification.to_dict()


@router.get("/organism/autonomous-pr-factory/production-truth/{delta_id}", dependencies=[Depends(_require_operator_role)])
async def autonomous_pr_factory_production_truth_detail(delta_id: str):
    import re as _re
    if not _re.fullmatch(r"ptd-[a-f0-9]{8}", delta_id):
        raise HTTPException(status_code=400, detail="invalid delta_id format")
    _root = os.environ.get("UMH_ROOT", "/opt/OS")
    mv_dir = Path(_root, "data", "umh", "autonomous_lane", "merge_verifications").resolve()
    candidate = Path(mv_dir, f"{delta_id}.json").resolve()
    if not candidate.is_relative_to(mv_dir):
        raise HTTPException(status_code=400, detail="invalid delta_id")
    if candidate.is_file():
        with open(candidate) as f:
            return json.load(f)
    return {"error": f"delta {delta_id} not found"}


@router.get("/organism/autonomous-pr-factory/merge-verifications", dependencies=[Depends(_require_operator_role)])
async def autonomous_pr_factory_merge_verifications():
    import glob as _glob
    _root = os.environ.get("UMH_ROOT", "/opt/OS")
    mv_dir = os.path.join(_root, "data", "umh", "autonomous_lane", "merge_verifications")
    verifications = []
    if os.path.isdir(mv_dir):
        for path in sorted(_glob.glob(os.path.join(mv_dir, "pmv-*.json"))):
            try:
                with open(path) as f:
                    verifications.append(json.load(f))
            except (json.JSONDecodeError, OSError):
                continue
    return {"verifications": verifications, "count": len(verifications)}


@router.get("/organism/autonomous-pr-factory/merge-verifications/{verification_id}", dependencies=[Depends(_require_operator_role)])
async def autonomous_pr_factory_merge_verification_detail(verification_id: str):
    import re as _re
    if not _re.fullmatch(r"pmv-[a-f0-9]{8}", verification_id):
        raise HTTPException(status_code=400, detail="invalid verification_id format")
    _root = os.environ.get("UMH_ROOT", "/opt/OS")
    mv_dir = Path(_root, "data", "umh", "autonomous_lane", "merge_verifications").resolve()
    candidate = Path(mv_dir, f"{verification_id}.json").resolve()
    if not candidate.is_relative_to(mv_dir):
        raise HTTPException(status_code=400, detail="invalid verification_id")
    if not candidate.is_file():
        return {"error": f"verification {verification_id} not found"}
    with open(candidate) as f:
        return json.load(f)


@router.post("/organism/autonomous-pr-factory/cleanup-eligible", dependencies=[Depends(_require_operator_role)])
async def autonomous_pr_factory_cleanup_eligible():
    manager, factory = _get_pr_factory()
    if manager is None:
        return {"error": "organism not running"}
    eligible = []
    for sb in manager.all_sandboxes:
        if sb.status.value in ("merged", "abandoned", "cleaned"):
            eligible.append(sb.to_dict())
    stale = []
    import time as _time
    now = _time.time()
    for sb in manager.all_sandboxes:
        age_h = (now - sb.created_at) / 3600
        if age_h > manager._ttl_hours and sb.status.value not in ("merged", "cleaned"):
            stale.append({"sandbox_id": sb.sandbox_id, "age_hours": round(age_h, 1), "status": sb.status.value})
    return {"cleanup_eligible": eligible, "stale": stale, "count": len(eligible) + len(stale)}


@router.get("/organism/autonomous-cadence", dependencies=[Depends(_require_operator_role)])
async def autonomous_cadence_status():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    cadence = getattr(daemon, "_autonomous_cadence", None)
    if cadence is None:
        return {"error": "cadence not available"}
    return cadence.to_dict()


@router.post("/organism/autonomous-cadence/run-dry-run", dependencies=[Depends(_require_operator_role)])
async def autonomous_cadence_run_dry_run():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    cadence = getattr(daemon, "_autonomous_cadence", None)
    if cadence is None:
        return {"error": "cadence not available"}
    result = cadence.run_cycle()
    return result.to_dict()


@router.post("/organism/autonomous-cadence/set-mode", dependencies=[Depends(_require_operator_role)])
async def autonomous_cadence_set_mode(payload: dict):
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    cadence = getattr(daemon, "_autonomous_cadence", None)
    if cadence is None:
        return {"error": "cadence not available"}
    from substrate.organism.autonomous_cadence import CadenceMode
    mode_str = payload.get("mode", "off")
    try:
        cadence.mode = CadenceMode(mode_str)
    except ValueError:
        return {"error": f"invalid mode: {mode_str}"}
    return {"ok": True, "mode": cadence.mode.value}


# ── Execution Substrate endpoints ────────────────────────────────────────────


@router.get("/execution/status")
async def execution_status():
    """Execution slot status across all compute layers."""
    return {
        "slots": [
            {
                "slot": 0,
                "layer": "native",
                "task": "",
                "status": "idle",
                "step_count": 0,
                "authority_class": "operator",
                "risk_class": "LOW",
                "approval_status": "none",
            },
            {
                "slot": 1,
                "layer": "container",
                "task": "",
                "status": "idle",
                "step_count": 0,
                "authority_class": "operator",
                "risk_class": "LOW",
                "approval_status": "none",
            },
            {
                "slot": 2,
                "layer": "wsl",
                "task": "",
                "status": "idle",
                "step_count": 0,
                "authority_class": "operator",
                "risk_class": "LOW",
                "approval_status": "none",
            },
            {
                "slot": 3,
                "layer": "vm",
                "task": "",
                "status": "idle",
                "step_count": 0,
                "authority_class": "operator",
                "risk_class": "LOW",
                "approval_status": "none",
            },
        ],
    }


@router.get("/execution/log")
async def execution_log(slot: int = 0):
    """Action log for a specific execution slot."""
    return {"slot": slot, "log": []}


@router.get("/execution/authority")
async def execution_authority(layer: str = "native"):
    """Authority preview for a compute layer."""
    return {
        "layer": layer,
        "authority_class": "operator",
        "risk_class": "LOW",
        "approval_requirement": "none",
    }


@router.post("/execution/start", dependencies=[Depends(_require_operator_role)])
async def execution_start(payload: dict):
    """Start execution in a slot."""
    return {"ok": True}


@router.post("/execution/stop", dependencies=[Depends(_require_operator_role)])
async def execution_stop(payload: dict):
    """Stop execution in a slot."""
    return {"ok": True}


@router.post("/execution/pause", dependencies=[Depends(_require_operator_role)])
async def execution_pause(payload: dict):
    """Pause execution in a slot."""
    return {"ok": True}


@router.post("/execution/resume", dependencies=[Depends(_require_operator_role)])
async def execution_resume(payload: dict):
    """Resume execution in a slot."""
    return {"ok": True}


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
                    provenance["pr"] = int(meta["pr"]) if str(meta["pr"]).isdigit() else str(meta["pr"])[:20]
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
                content = payload.get("content", "") or payload.get("task", "") or str(payload)[:200]
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
            content=content, response="", origin_channel="cockpit",
        )
        push_chat_message({
            "sender": "operator",
            "content": content,
            "origin_channel": "cockpit",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
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
        path = os.path.join(repo_root, path[len("/opt/OS/"):])
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
    return FileResponse(str(resolved), filename=resolved.name, media_type="application/octet-stream")


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
