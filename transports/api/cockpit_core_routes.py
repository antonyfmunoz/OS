"""Cockpit core routes — extracted inline route handlers.

These were originally inline in cockpit.py. Extracted to bring
cockpit.py under the 3,000-line quality gate.

Phase 25 prerequisite. UMH transport layer.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac as _hmac
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import psutil
from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect

from substrate.execution.cpu_gate import gated_subprocess_run
from transports.api.governed import governed_mutation

logger = logging.getLogger(__name__)

# ── Path constants (same as cockpit.py) ──────────────────────────────────────

_ROOT = Path(os.getenv("UMH_ROOT", "/opt/OS"))
MEMORY_STORE = _ROOT / "data" / "runtime" / "canonical_memory_store" / "memories.jsonl"
TRACE_STORE = _ROOT / "data" / "umh" / "traces" / "traces.jsonl"
SKILLS_DIR = _ROOT / "skills"
AGENTS_DIR = _ROOT / "agents"
_DOCKER_SOCK = "/var/run/docker.sock"
_DEVICE_REGISTRY_PATH = _ROOT / "infra" / "device_registry.json"
_FRONTEND_ARTIFACT_MANIFEST = ".umh-wave2-artifact.json"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")

# ── Module state set by configure() ──────────────────────────────────────────

core_router: APIRouter = APIRouter()
core_ws_router: APIRouter = APIRouter()
_configured: bool = False

# WebSocket auth deps — set by configure()
_is_private_ip_fn: Any = None
_validate_ws_clerk_token_fn: Any = None
_ws_token: str = ""
_dev_bypass: bool = False
_trusted_proxies: set = set()
_dex_conversation: Any = None

# Exposed after configure() — closure functions hoisted to module level
push_chat_message: Any = None
push_organism_event: Any = None
push_mutation_event: Any = None


class _CockpitAssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.module_scripts: list[str] = []
        self.stylesheets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key: value or "" for key, value in attrs}
        if tag == "script" and attr.get("type") == "module" and attr.get("src"):
            self.module_scripts.append(attr["src"])
        if tag == "link" and attr.get("rel") == "stylesheet" and attr.get("href"):
            self.stylesheets.append(attr["href"])


def _asset_name_from_ref(ref: str, suffix: str) -> str:
    normalized = ref.split("?", 1)[0].split("#", 1)[0].lstrip("./")
    prefix = "assets/"
    if not normalized.startswith(prefix) or not normalized.endswith(suffix):
        return ""
    name = normalized[len(prefix) :]
    if "/" in name or not name:
        return ""
    return name


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _current_source_sha(root: Path | None = None) -> str:
    base = root or _ROOT
    for key in (
        "UMH_SOURCE_SHA",
        "SOURCE_SHA",
        "UMH_RELEASE_SHA",
        "UMH_CANDIDATE_SHA",
        "UMH_BUILD_COMMIT",
    ):
        value = os.getenv(key, "").strip()
        if _SHA_RE.match(value):
            return value
    source_file = base / "SOURCE_SHA"
    try:
        value = source_file.read_text(encoding="ascii").strip()
        if _SHA_RE.match(value):
            return value
    except OSError:
        pass
    try:
        result = gated_subprocess_run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(base),
        )
    except Exception:
        return ""
    value = (result.stdout if result is not None and result.returncode == 0 else "").strip()
    return value if _SHA_RE.match(value) else ""


def _cockpit_frontend_artifact_proof(
    dist_web: Path, expected_sha: str, bytes_proof: dict[str, Any] | None = None
) -> dict[str, Any]:
    manifest_path = dist_web / _FRONTEND_ARTIFACT_MANIFEST
    proof: dict[str, Any] = {
        "frontend_artifact_ok": False,
        "frontend_artifact_manifest": str(manifest_path),
        "frontend_artifact_errors": [],
        "expected_sha": expected_sha,
    }
    errors: list[str] = proof["frontend_artifact_errors"]
    if not expected_sha:
        errors.append("expected source SHA unavailable")
        return proof
    if not manifest_path.is_file():
        errors.append("artifact manifest missing")
        return proof
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"artifact manifest unreadable: {type(exc).__name__}")
        return proof
    if not isinstance(manifest, dict):
        errors.append("artifact manifest is not an object")
        return proof
    proof["artifact_candidate_sha"] = manifest.get("candidate_sha")
    proof["artifact_source_head"] = manifest.get("source_head")
    proof["artifact_source_tree"] = manifest.get("source_tree")
    proof["artifact_index_sha256"] = manifest.get("index_sha256")
    proof["artifact_assets"] = manifest.get("assets")
    if manifest.get("candidate_sha") != expected_sha:
        errors.append("artifact candidate SHA mismatch")
    if manifest.get("source_head") != expected_sha:
        errors.append("artifact source HEAD mismatch")
    if not manifest.get("source_tree"):
        errors.append("artifact source tree missing")
    if bytes_proof is None:
        errors.append("artifact bytes proof unavailable")
    else:
        if manifest.get("index_sha256") != bytes_proof.get("index_sha256"):
            errors.append("artifact index hash mismatch")
        if manifest.get("assets") != bytes_proof.get("assets"):
            errors.append("artifact asset hash mismatch")
    proof["frontend_artifact_ok"] = not errors
    return proof


def _cockpit_frontend_asset_info(
    root: Path | None = None, *, expected_sha: str | None = None
) -> dict[str, Any]:
    base = root or _ROOT
    dist_web = base / "cockpit" / "dist-web"
    index_html = dist_web / "index.html"
    if not index_html.is_file():
        proof = (
            _cockpit_frontend_artifact_proof(dist_web, expected_sha)
            if expected_sha is not None
            else {}
        )
        return {
            **proof,
            "frontend_assets_ok": False,
            "frontend_asset_errors": ["index.html missing"],
        }
    parser = _CockpitAssetParser()
    parser.feed(index_html.read_text(encoding="utf-8"))
    index_sha256 = _sha256_file(index_html)
    assets: dict[str, str] = {}
    artifact_assets: dict[str, dict[str, str]] = {}
    errors: list[str] = []
    for key, refs, suffix in (
        ("js", parser.module_scripts, ".js"),
        ("css", parser.stylesheets, ".css"),
    ):
        names = [_asset_name_from_ref(ref, suffix) for ref in refs]
        names = [name for name in names if name]
        if len(names) != 1:
            errors.append(f"expected exactly one {key} asset reference")
            continue
        asset_path = dist_web / "assets" / names[0]
        if not asset_path.is_file():
            errors.append(f"{key} asset missing: {names[0]}")
            continue
        assets[f"{key}_asset"] = names[0]
        assets[f"{key}_hash"] = names[0]
        asset_sha = _sha256_file(asset_path)
        assets[f"{key}_sha256"] = asset_sha
        artifact_assets[key] = {"name": names[0], "sha256": asset_sha}
    bytes_proof = {
        "index_sha256": index_sha256,
        "assets": artifact_assets,
    }
    proof = (
        _cockpit_frontend_artifact_proof(dist_web, expected_sha, bytes_proof)
        if expected_sha is not None
        else {}
    )
    artifact_ok = proof.get("frontend_artifact_ok", True)
    return {
        **proof,
        **assets,
        "index_sha256": index_sha256,
        "assets": artifact_assets,
        "frontend_assets_ok": not errors and artifact_ok is True,
        "frontend_asset_errors": errors,
    }


def configure(
    require_operator_dep: Any,
    is_private_ip_fn: Any = None,
    validate_ws_clerk_token_fn: Any = None,
    ws_token: str = "",
    dev_bypass: bool = False,
    trusted_proxies: set | None = None,
) -> None:
    """Configure and build all core routes."""
    global core_router, core_ws_router, _configured
    global _is_private_ip_fn, _validate_ws_clerk_token_fn
    global _ws_token, _dev_bypass, _trusted_proxies
    global push_chat_message, push_organism_event, push_mutation_event

    _is_private_ip_fn = is_private_ip_fn
    _validate_ws_clerk_token_fn = validate_ws_clerk_token_fn
    _ws_token = ws_token
    _dev_bypass = dev_bypass
    _trusted_proxies = trusted_proxies or set()

    r, ws, _push_chat, _push_event = _build_routers(require_operator_dep)
    core_router = r
    core_ws_router = ws
    push_chat_message = _push_chat
    push_organism_event = _push_event
    _configured = True

    def _push_mutation(domain: str, action: str, payload: dict | None = None) -> None:
        """Push a mutation event for a specific domain/action to WS clients."""
        _push_event(
            {
                "type": "mutation_event",
                "domain": domain,
                "action": action,
                **(payload or {}),
            }
        )

    push_mutation_event = _push_mutation


# ── Helper functions used by both routes and mount functions ──────────────────


def get_organism():
    """Lazy import to avoid circular dependency at module load."""
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


def get_org_id() -> str:
    """Get org_id from context for projection queries."""
    try:
        from substrate.state.context.context import load_context_from_env

        ctx = load_context_from_env()
        return str(ctx.org_id)
    except Exception:
        return ""


def get_mesh_server():
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


def _build_routers(require_operator_dep: Any) -> tuple[APIRouter, APIRouter]:
    """Build core route handlers. All routes defined inside for dependency closure."""
    _require_operator_role = require_operator_dep
    router = APIRouter()
    ws_router = APIRouter()

    def _load_device_registry() -> list[dict[str, Any]]:
        try:
            with open(_DEVICE_REGISTRY_PATH) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError, FileNotFoundError):
            return []

    def _get_docker_containers() -> list[dict]:
        """Query Docker Engine API via unix socket for running containers."""
        import http.client
        import socket as _socket

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
            if sha is not None and sha.returncode == 0:
                info["commit_sha"] = sha.stdout.strip()
        except Exception:
            pass
        if not info.get("commit_sha"):
            source_sha = _current_source_sha(_ROOT)
            if source_sha:
                info["commit_sha"] = source_sha
        try:
            ts = gated_subprocess_run(
                ["git", "log", "-1", "--format=%cI"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=str(_ROOT),
            )
            if ts is not None and ts.returncode == 0:
                info["commit_time"] = ts.stdout.strip()
        except Exception:
            pass
        info.update(
            _cockpit_frontend_asset_info(
                _ROOT,
                expected_sha=str(info.get("commit_sha", "")),
            )
        )
        return info

    _BUILD_INFO = _compute_build_info()

    @router.get("/build")
    def build_info():
        return _BUILD_INFO

    @router.get("/pulse")
    async def pulse():
        loop = asyncio.get_running_loop()
        node_metrics = await loop.run_in_executor(None, _build_node_metrics)
        vps = node_metrics.get("vps", {})
        traces = await loop.run_in_executor(None, _read_jsonl, TRACE_STORE)
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

    @router.get("/auth-check", dependencies=[Depends(_require_operator_role)])
    def auth_check():
        return {"ok": True}

    @router.get("/mesh/metrics")
    def mesh_metrics():
        """Per-node metrics — reads from mesh server snapshot (single source of truth)."""
        return _build_node_metrics()

    @router.get("/models")
    def models():
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
        loop = asyncio.get_running_loop()

        def _collect_infra() -> list[dict]:
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
                    "metrics": {
                        "cpu": cpu,
                        "memory": mem.percent,
                        "disk": disk.percent,
                        "cost": 24,
                    },
                }
            )

            try:
                out = gated_subprocess_run(
                    ["tailscale", "status", "--json"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if out is not None and out.returncode == 0:
                    ts_data = json.loads(out.stdout)
                    peers = ts_data.get("Peer", {})
                    online_count = 0
                    for _key, peer in peers.items():
                        name = _device_name(peer)
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

        return await loop.run_in_executor(None, _collect_infra)

    @router.get("/agents")
    def agents():
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
    def memory(source: str = "all", limit: int = 50):
        """Memory entries from typed ConversationMemory and AgentMemory classes,
        with JSONL fallback for legacy ontology data."""
        result = []

        if source in ("all", "conversation"):
            try:
                from substrate.state.context.context import try_load_context_from_env
                from substrate.state.memory.memory import ConversationMemory

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
    def skills():
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
                        "effort": effort
                        if effort in ("low", "medium", "high", "max")
                        else "medium",
                    }
                )
        return result

    @router.get("/observations")
    def observations():
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
    def tasks():
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
    def comms(limit: int = 100):
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
    def tracking():
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
    def analytics():
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
    def settings():
        from adapters.models.cc_sdk import query_cc_sync
        from adapters.models.model_router import (
            MODEL_REGISTRY,
            PROVIDER_PRIORITY,
            PROVIDER_QUALITY,
            PURPOSE_ROUTING,
            ROLE_FAILOVER,
            ROLE_SLOTS,
            ModelRouter,
        )
        from substrate.contracts.agent_types import ModelProvider

        ModelRouter()

        role_map: dict[str, str] = {}
        for role, key in ROLE_SLOTS.items():
            role_map[key] = role.value

        providers: list[dict[str, Any]] = []

        cc_available = query_cc_sync is not None
        providers.append(
            {
                "provider": "cc_sdk",
                "model_id": "claude-opus-4-8",
                "priority": PROVIDER_PRIORITY.get(ModelProvider.CC_SDK, 3),
                "quality": PROVIDER_QUALITY.get("cc_sdk", 0),
                "enabled": cc_available,
                "available": cc_available,
                "role": role_map.get("cc_sdk"),
                "status": "healthy" if cc_available else "not_installed",
            }
        )

        for key, config in MODEL_REGISTRY.items():
            prov_name = (
                config.provider.value if hasattr(config.provider, "value") else str(config.provider)
            )
            priority_val = PROVIDER_PRIORITY.get(config.provider, 99)
            quality_val = PROVIDER_QUALITY.get(key, PROVIDER_QUALITY.get(prov_name, 0))
            providers.append(
                {
                    "provider": key,
                    "model_id": config.model_id,
                    "priority": priority_val,
                    "quality": quality_val,
                    "enabled": config.available,
                    "available": config.available,
                    "role": role_map.get(key),
                    "status": config.status_reason
                    or ("healthy" if config.available else "unavailable"),
                }
            )

        providers.sort(key=lambda p: (not p["available"], p["priority"]))

        purpose_routing = {
            purpose: [r.value for r in roles] for purpose, roles in PURPOSE_ROUTING.items()
        }
        role_slots = {role.value: key for role, key in ROLE_SLOTS.items()}
        role_failover = {role.value: key for role, key in ROLE_FAILOVER.items() if key}

        return {
            "model_routing": providers,
            "purpose_routing": purpose_routing,
            "role_slots": role_slots,
            "role_failover": role_failover,
            "provider_keys": ["cc_sdk"] + list(MODEL_REGISTRY.keys()),
            "governance": {"auto_approve_low": True, "critical_block": True},
            "persistence_status": "active",
        }

    @router.get("/mesh/nodes")
    async def mesh_nodes():
        """Returns all network devices: Tailscale peers + UMH daemon nodes."""
        loop = asyncio.get_running_loop()

        def _collect_mesh_nodes() -> list[dict]:
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
                dns_name = n.get("DNSName", "").split(".")[0]
                display = (
                    dns_name if hostname.lower() in ("localhost", "") and dns_name else hostname
                )
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
                    "last_seen": last_seen
                    if not online
                    else datetime.now(timezone.utc).isoformat(),
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

            try:
                result = gated_subprocess_run(
                    ["tailscale", "status", "--json"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result is not None and result.returncode == 0:
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

        return await loop.run_in_executor(None, _collect_mesh_nodes)

    _get_mesh_server = get_mesh_server

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
                (d for d in registry if d.get("mesh_node_id") == node_id or d.get("id") == node_id),
                {},
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

    _get_organism = get_organism

    @router.post("/pipeline/submit", dependencies=[Depends(_require_operator_role)])
    async def pipeline_submit(payload: dict):
        """Submit a command through the full execution pipeline from cockpit."""
        content = payload.get("content", "")
        if not content:
            return {"error": "content required"}

        risk_class = payload.get("risk_class", "READ_ONLY")
        adapter = payload.get("adapter", "shell")
        operation = payload.get("operation", "generic")
        params = payload.get("params", {})
        pre_approved = payload.get("pre_approved", False)

        try:
            from substrate.governance.risk_classes import RiskClass
            from transports.api.app import _pipeline

            risk = RiskClass[risk_class]
        except (ImportError, KeyError):
            return {"error": f"invalid risk_class: {risk_class}"}

        def _do_submit():
            result = _pipeline.submit_signal(
                content,
                risk_class=risk,
                adapter_name=adapter,
                operation=operation,
                params=params,
                pre_approved=pre_approved,
            )
            return f"pipeline submitted: trace={result.trace_id}", result.success

        resp = governed_mutation(
            mutation_name="work_packet_create",
            intent=f"pipeline submit: {content[:100]}",
            execute_fn=_do_submit,
            source="cockpit",
            metadata={"adapter": adapter, "risk_class": risk_class},
        )
        return resp.to_http_dict()

    @router.post("/comms/send", dependencies=[Depends(_require_operator_role)])
    def comms_send(payload: dict):
        """Send a message to an organism agent."""
        recipient = payload.get("recipient", "")
        content = payload.get("content", "")
        if not recipient or not content:
            return {"error": "recipient and content required"}

        def _do_send():
            daemon = _get_organism()
            if daemon is None:
                return "organism not running", False
            from substrate.organism.protocols import AgentMessage

            msg = AgentMessage(
                sender="operator",
                recipient=recipient,
                intent=payload.get("intent", "operator_message"),
                payload={"content": content, "source": "cockpit"},
            )
            daemon.store.save_message(msg)
            return f"message sent to {recipient}: {msg.id}", True

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"send message to {recipient}",
            execute_fn=_do_send,
            source="cockpit",
            metadata={"recipient": recipient},
        )
        return resp.to_http_dict()

    @router.post("/workflows/{workflow_id}/trigger", dependencies=[Depends(_require_operator_role)])
    def workflow_trigger(workflow_id: str, payload: dict | None = None):
        """Trigger a workflow run through the pipeline."""
        adapter = workflow_id.replace("wf-", "")
        content = f"Triggered {adapter} workflow from cockpit"
        if payload and payload.get("params"):
            content = payload["params"].get("command", content)

        def _do_trigger():
            try:
                from substrate.governance.risk_classes import RiskClass
                from transports.api.app import _pipeline

                result = _pipeline.submit_signal(
                    content,
                    risk_class=RiskClass.READ_ONLY,
                    adapter_name=adapter if adapter != "system" else "shell",
                    operation=payload.get("operation", "query") if payload else "query",
                    params=payload.get("params", {}) if payload else {},
                )
                return f"workflow {adapter} triggered: trace={result.trace_id}", result.success
            except Exception as exc:
                return str(exc), False

        resp = governed_mutation(
            mutation_name="work_packet_create",
            intent=f"trigger workflow {adapter}",
            execute_fn=_do_trigger,
            source="cockpit",
            metadata={"workflow_id": workflow_id},
        )
        return resp.to_http_dict()

    @router.patch("/settings", dependencies=[Depends(_require_operator_role)])
    async def update_settings(request: Request):
        """Update cockpit settings via mutation runtime — persisted + audited."""
        from transports.api.cockpit_settings_mutations import (
            set_purpose_chain,
            set_role_slot,
            toggle_provider,
        )

        payload = await request.json()
        action = payload.get("action", "")

        if action not in ("toggle_provider", "set_purpose_chain", "set_role_slot"):
            raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

        def _do_settings():
            if action == "toggle_provider":
                result = toggle_provider(
                    payload.get("provider_key", ""), payload.get("enabled", False)
                )
            elif action == "set_purpose_chain":
                result = set_purpose_chain(payload.get("purpose", ""), payload.get("roles", []))
            else:
                result = set_role_slot(payload.get("role", ""), payload.get("provider_key", ""))

            if not result.ok:
                return f"settings update failed: {result.errors}", False

            if push_mutation_event is not None:
                push_mutation_event("settings", "updated", {"action": action})

            return f"settings {action} applied", True

        resp = governed_mutation(
            mutation_name="settings_update",
            intent=f"update settings: {action}",
            execute_fn=_do_settings,
            source="cockpit",
            metadata={"action": action},
        )
        return resp.to_http_dict()

    @router.post("/organism/control", dependencies=[Depends(_require_operator_role)])
    def organism_control(payload: dict):
        """Control organism lifecycle — start/stop."""
        action = payload.get("action", "")

        if action == "status":
            daemon = _get_organism()
            if daemon is None:
                return {"running": False}
            return {"running": daemon.is_running}
        elif action in ("start", "stop"):

            def _do_control():
                daemon = _get_organism()
                if action == "stop":
                    if daemon is not None:
                        daemon.stop()
                    return "organism stopped", True
                else:
                    if daemon is not None:
                        daemon.start()
                    return (
                        f"organism started (running={daemon.is_running if daemon else False})",
                        True,
                    )

            resp = governed_mutation(
                mutation_name="state_mutate",
                intent=f"organism {action}",
                execute_fn=_do_control,
                source="cockpit",
                metadata={"action": action},
            )
            return resp.to_http_dict()
        else:
            return {"error": f"unknown action: {action}"}

    @router.post("/agents/{agent_id}/signal")
    def agent_signal(agent_id: str, payload: dict):
        """Send a signal to a specific organism agent."""
        content = payload.get("content", "")
        if not content:
            return {"error": "content required"}

        def _do_signal():
            daemon = _get_organism()
            if daemon is None:
                return "organism not running", False
            daemon.advisor.handle_signal(content)
            return f"signal sent to {agent_id}", True

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"send signal to agent {agent_id}",
            execute_fn=_do_signal,
            source="cockpit",
            metadata={"agent_id": agent_id},
        )
        return resp.to_http_dict()

    @router.get("/profile")
    def profile():
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
    def activity_stream(limit: int = 200, source: str | None = None):
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

    @router.post("/organism/handoff", dependencies=[Depends(_require_operator_role)])
    def organism_handoff(payload: dict):
        """Submit a task handoff between agents."""
        source = payload.get("source_agent", "")
        target = payload.get("target_agent", "")

        def _do_handoff():
            daemon = _get_organism()
            if daemon is None:
                return "organism not running", False
            daemon.handoff(
                source_agent=source,
                target_agent=target,
                task=payload.get("task", ""),
                context=payload.get("context", ""),
            )
            return f"handoff {source} -> {target}", True

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"handoff from {source} to {target}",
            execute_fn=_do_handoff,
            source="cockpit",
            metadata={"source_agent": source, "target_agent": target},
        )
        return resp.to_http_dict()

    @router.post("/organism/parallel", dependencies=[Depends(_require_operator_role)])
    def organism_parallel(payload: dict):
        """Execute multiple agent tasks in parallel."""
        tasks = payload.get("tasks", [])

        def _do_parallel():
            daemon = _get_organism()
            if daemon is None:
                return "organism not running", False
            daemon.execute_parallel(tasks)
            return f"parallel execution of {len(tasks)} tasks", True

        resp = governed_mutation(
            mutation_name="work_packet_create",
            intent=f"parallel execute {len(tasks)} agent tasks",
            execute_fn=_do_parallel,
            source="cockpit",
            metadata={"task_count": len(tasks)},
        )
        return resp.to_http_dict()

    @router.get("/organism/delegations")
    def organism_delegations():
        """Check for overdue delegations and follow-ups."""
        daemon = _get_organism()
        if daemon is None:
            return {"error": "organism not running", "followups": []}
        return {"followups": daemon.check_delegations()}

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

        If the message has action_required=True, also fires a push notification
        to reach the operator when the cockpit tab is not active.
        """
        event = {"type": "chat_message", **message}
        _pending_organism_events.append(event)
        if len(_pending_organism_events) > 200:
            _pending_organism_events[:] = _pending_organism_events[-100:]

        if message.get("action_required"):
            try:
                from transports.api.cockpit_push_routes import send_push_notification

                send_push_notification(
                    title="UMH — Action Required",
                    body=message.get("content", "")[:200],
                    category="action_required",
                    url="/",
                )
            except Exception:
                pass

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
        if tcp_ip in _trusted_proxies:
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
            clerk_user = _validate_ws_clerk_token_fn(ws)
            if clerk_user is not None:
                return True
        except HTTPException:
            return False
        if _ws_token:
            token = _extract_ws_token(ws)
            if token and _hmac.compare_digest(token, _ws_token):
                return True
        client_ip = _real_ws_client_ip(ws)
        if _dev_bypass and _is_private_ip_fn(client_ip):
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

    # ─── Voice WebSocket ──────────────────────────────────────────────────────────
    # P4S31 Voice Convergence: the phantom voice proxy that used to live here (a
    # ws_router websocket handler forwarding to the standalone voice_server) was
    # REMOVED. The ONE governed voice WS is served directly by the API backend
    # (transports/api/voice.py, mounted in operator_api). Keeping this proxy would
    # double-bind the same governed voice path and re-introduce the retired
    # standalone voice_server dependency. nginx now proxies the path to api_backend.

    # ─── Vision WebSocket Proxy ───────────────────────────────────────────────────

    _VISION_WS_UPSTREAM = os.environ.get(
        "VISION_WS_UPSTREAM", "ws://host.docker.internal:8097/vision"
    )
    _VISION_PROXY_MAX_MSG = 2**22  # 4 MiB

    @ws_router.websocket("/vision/ws")
    async def vision_ws_proxy(ws: WebSocket):
        """Proxy browser vision WebSocket to the internal vision relay."""
        if not _validate_ws_token(ws):
            await ws.close(code=4001, reason="Authentication required")
            logger.warning(
                "[VisionProxy] auth rejected from %s", ws.client.host if ws.client else "unknown"
            )
            return

        subprotocol = _extract_ws_subprotocol(ws)
        await ws.accept(subprotocol=subprotocol)
        logger.info(
            "[VisionProxy] client_connected from %s", ws.client.host if ws.client else "unknown"
        )

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
            await ws.send_json(
                {
                    "type": "error",
                    "code": "vision_relay_unavailable",
                    "message": "Vision relay unreachable",
                }
            )
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
                [
                    asyncio.ensure_future(client_to_upstream()),
                    asyncio.ensure_future(upstream_to_client()),
                ],
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

    # ── Provider Health ────────────────────────────────────────────────────────────

    @router.get("/providers/health")
    def providers_health():
        """Return the runtime portfolio — roles, slots, provider status, and purpose routing."""
        from adapters.models.model_router import (
            MODEL_REGISTRY,
            PURPOSE_ROUTING,
            ROLE_SLOTS,
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

        def _do_classify():
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
            return f"classified as {intent} (persisted={bool(event_id)})", True

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"classify intent: {text[:80]}",
            execute_fn=_do_classify,
            source="cockpit",
        )
        return resp.to_http_dict()

    # ── Projection preview routes (Phase 2.1) ──────────────────────────────────

    @router.get("/projections")
    def list_projections_api():
        """List all registered projections with preview URLs."""
        from substrate.sockets.projection_port import ProjectionPort

        port = ProjectionPort()
        port.seed_from_config()
        return {"projections": [r.to_dict() for r in port.list_registrations()]}

    @router.get("/projections/{projection_id}/preview")
    def projection_preview(projection_id: str):
        """Get preview metadata for a specific projection."""
        from substrate.sockets.projection_port import ProjectionPort

        port = ProjectionPort()
        port.seed_from_config()
        preview = port.get_preview(projection_id)
        if preview is None:
            return {"error": f"projection '{projection_id}' not found"}
        return preview

    # ── Proof packages (Phase 4.5) ─────────────────────────────────────────────

    @router.get("/proofs")
    def list_proofs(status: str = "", limit: int = 50, offset: int = 0):
        from substrate.organism.proof_store import get_proof_store

        store = get_proof_store()
        packages = store.query(status=status, limit=limit, offset=offset)
        return {
            "packages": [p.to_dict() for p in packages],
            "summary": store.summary(),
        }

    @router.get("/proofs/{proof_id}")
    def get_proof(proof_id: str):
        from substrate.organism.proof_store import get_proof_store

        pkg = get_proof_store().get(proof_id)
        if pkg is None:
            return {"error": f"proof '{proof_id}' not found"}
        return pkg.to_dict()

    @router.post("/proofs/{proof_id}/approve", dependencies=[Depends(_require_operator_role)])
    def approve_proof(proof_id: str, payload: dict | None = None):
        notes = (payload or {}).get("notes", "")

        def _do_approve():
            from substrate.organism.proof_store import get_proof_store

            pkg = get_proof_store().approve(proof_id, notes=notes)
            if pkg is None:
                return f"proof '{proof_id}' not found", False
            return f"proof {proof_id} approved", True

        resp = governed_mutation(
            mutation_name="approval_decide",
            intent=f"approve proof {proof_id}",
            execute_fn=_do_approve,
            source="cockpit",
            metadata={"proof_id": proof_id},
        )
        return resp.to_http_dict()

    @router.post("/proofs/{proof_id}/reject", dependencies=[Depends(_require_operator_role)])
    def reject_proof(proof_id: str, payload: dict | None = None):
        notes = (payload or {}).get("notes", "")

        def _do_reject():
            from substrate.organism.proof_store import get_proof_store

            pkg = get_proof_store().reject(proof_id, notes=notes)
            if pkg is None:
                return f"proof '{proof_id}' not found", False
            return f"proof {proof_id} rejected", True

        resp = governed_mutation(
            mutation_name="approval_decide",
            intent=f"reject proof {proof_id}",
            execute_fn=_do_reject,
            source="cockpit",
            metadata={"proof_id": proof_id},
        )
        return resp.to_http_dict()

    # ── Workstation snapshot & resume (Phase 5) ────────────────────────────────

    @router.get("/workstation/snapshot")
    def workstation_snapshot():
        """Full workstation state snapshot for continuity."""
        import time as _time

        snap: dict = {"snapshot_at": _time.time()}
        try:
            from substrate.sockets.projection_port import ProjectionPort

            port = ProjectionPort()
            port.seed_from_config()
            regs = port.list_registrations()
            if regs:
                snap["active_project"] = regs[0].name
                snap["active_preview"] = regs[0].preview_url
        except Exception:
            pass
        try:
            from substrate.organism.executor_runtime import load_executor_preference

            pref = load_executor_preference()
            snap["executor_type"] = pref[0] if pref else "simulation"
        except Exception:
            snap["executor_type"] = "simulation"
        try:
            from substrate.organism.execution_ledger import get_execution_ledger

            ledger = get_execution_ledger()
            entries = ledger.query(limit=1)
            if entries:
                last = entries[0]
                snap["last_execution_status"] = last.status
                snap["last_execution_executor"] = last.executor_type
                snap["last_execution_target"] = last.target_machine
                elapsed = (
                    _time.time() - last.ended_at
                    if last.ended_at
                    else _time.time() - last.created_at
                )
                if elapsed < 60:
                    snap["last_execution_ago"] = f"{int(elapsed)}s ago"
                elif elapsed < 3600:
                    snap["last_execution_ago"] = f"{int(elapsed / 60)}m ago"
                else:
                    snap["last_execution_ago"] = f"{int(elapsed / 3600)}h ago"
        except Exception:
            pass
        try:
            snap["pending_approvals"] = 0
            daemon = _get_organism()
            if daemon and hasattr(daemon, "approval_store"):
                snap["pending_approvals"] = len(daemon.approval_store.list_approvals())
        except Exception:
            pass

        _snapshot_path = os.path.join(
            os.environ.get("UMH_ROOT", "/opt/OS"),
            "data",
            "runtime",
            "workstation_snapshot.json",
        )
        try:
            os.makedirs(os.path.dirname(_snapshot_path), exist_ok=True)
            with open(_snapshot_path, "w") as f:
                json.dump(snap, f, indent=2, default=str)
        except Exception:
            pass

        return snap

    @router.get("/workstation/resume")
    def workstation_resume():
        """Resume brief — what the operator was doing and what happened since."""
        import time as _time

        _snapshot_path = os.path.join(
            os.environ.get("UMH_ROOT", "/opt/OS"),
            "data",
            "runtime",
            "workstation_snapshot.json",
        )
        snap: dict = {}
        try:
            if os.path.exists(_snapshot_path):
                with open(_snapshot_path) as f:
                    snap = json.load(f)
        except Exception:
            pass

        if not snap:
            try:
                from substrate.sockets.projection_port import ProjectionPort

                port = ProjectionPort()
                port.seed_from_config()
                regs = port.list_registrations()
                if regs:
                    snap["active_project"] = regs[0].name
            except Exception:
                pass

        snap.setdefault("active_project", "")
        snap.setdefault("active_repo", "")
        snap.setdefault("active_branch", "")
        snap.setdefault("active_file", "")
        snap.setdefault("current_objective", "")
        snap.setdefault("pending_approvals", 0)
        snap.setdefault("next_action", "")
        snap.setdefault("since_away", [])

        try:
            from substrate.organism.execution_ledger import get_execution_ledger

            ledger = get_execution_ledger()
            entries = ledger.query(limit=1)
            if entries:
                last = entries[0]
                snap["last_execution_status"] = last.status
                snap["last_execution_executor"] = last.executor_type
                snap["last_execution_target"] = last.target_machine
                elapsed = (
                    _time.time() - last.ended_at
                    if last.ended_at
                    else _time.time() - last.created_at
                )
                if elapsed < 60:
                    snap["last_execution_ago"] = f"{int(elapsed)}s ago"
                elif elapsed < 3600:
                    snap["last_execution_ago"] = f"{int(elapsed / 60)}m ago"
                else:
                    snap["last_execution_ago"] = f"{int(elapsed / 3600)}h ago"
        except Exception:
            pass

        try:
            daemon = _get_organism()
            if daemon and hasattr(daemon, "approval_store"):
                snap["pending_approvals"] = len(daemon.approval_store.list_approvals())
        except Exception:
            pass

        return snap

    # ── Workspace context (Phase 3.5) ──────────────────────────────────────────

    @router.get("/workspace/context")
    def workspace_context_api():
        """Current workspace context — active project, repo, branch, file."""
        result: dict[str, str] = {}
        try:
            from substrate.sockets.projection_port import ProjectionPort

            port = ProjectionPort()
            regs = port.list_registrations()
            if regs:
                result["active_project"] = regs[0].name
                result["active_preview"] = regs[0].preview_url
        except Exception:
            pass
        try:
            from substrate.organism.executor_runtime import (
                load_executor_preference,
            )

            pref = load_executor_preference()
            result["executor_type"] = pref[0] if pref else "simulation"
        except Exception:
            result["executor_type"] = "simulation"
        return result

    # ── Execution ledger & executor preference (Phase 3) ──────────────────────

    @router.get("/execution/ledger")
    def execution_ledger_api(
        status: str = "",
        executor_type: str = "",
        limit: int = 50,
        offset: int = 0,
    ):
        """Paginated execution ledger — filterable by status/executor."""
        from substrate.organism.execution_ledger import get_execution_ledger

        ledger = get_execution_ledger()
        entries = ledger.query(
            status=status, executor_type=executor_type, limit=limit, offset=offset
        )
        return {
            "entries": [e.to_dict() for e in entries],
            "summary": ledger.summary(),
        }

    @router.get("/execution/preference")
    def executor_preference_api():
        """Current executor preference order."""
        from substrate.organism.executor_runtime import load_executor_preference

        return {"order": load_executor_preference()}

    @router.patch("/execution/preference", dependencies=[Depends(_require_operator_role)])
    def update_executor_preference(payload: dict):
        """Update executor preference order."""
        order = payload.get("order", [])
        if not isinstance(order, list) or not order:
            return {"error": "order must be a non-empty list of executor types"}

        def _do_update():
            from substrate.organism.executor_runtime import (
                load_executor_preference,
                save_executor_preference,
            )

            save_executor_preference(order)
            return f"executor preference set to {load_executor_preference()}", True

        resp = governed_mutation(
            mutation_name="settings_update",
            intent=f"update executor preference: {order}",
            execute_fn=_do_update,
            source="cockpit",
            metadata={"order": order},
        )
        return resp.to_http_dict()

    # ── Bootstrap, config, session, feedback, governance, EOS routes ──────────
    # Delegated to split files (see end of function)

    # ── Delegated route registrations (Phase 0.3 split) ────────────────────────
    _helpers = {
        "_build_node_metrics": _build_node_metrics,
        "_read_jsonl": _read_jsonl,
        "_get_organism": _get_organism,
    }

    from transports.api.cockpit_core_bootstrap_routes import register_bootstrap_routes
    from transports.api.cockpit_core_creatoros_routes import register_creatoros_routes
    from transports.api.cockpit_core_eos_routes import register_eos_routes
    from transports.api.cockpit_core_feedback_routes import register_feedback_routes
    from transports.api.cockpit_core_governance_routes import register_governance_routes
    from transports.api.cockpit_core_lyfeos_routes import register_lyfeos_routes
    from transports.api.cockpit_core_session_routes import register_session_routes
    from transports.api.cockpit_intent_loop_routes import register_intent_loop_routes
    from transports.api.cockpit_voice_consent_routes import register_voice_consent_routes

    register_bootstrap_routes(router, _require_operator_role, _helpers)
    register_session_routes(router, _require_operator_role, _helpers)
    register_feedback_routes(router, _require_operator_role, _helpers)
    register_governance_routes(router, _require_operator_role, _helpers)
    register_eos_routes(router, _require_operator_role, _helpers)
    register_lyfeos_routes(router, _require_operator_role, _helpers)
    register_creatoros_routes(router, _require_operator_role, _helpers)
    register_intent_loop_routes(router, _require_operator_role, _helpers)
    register_voice_consent_routes(router, _require_operator_role, _helpers)

    return router, ws_router, push_chat_message, push_organism_event
