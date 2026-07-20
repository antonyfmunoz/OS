"""Grounding registry — source data requirements for deterministic status answers.

Every status-class query has declared data sources. If the source is available,
the answer is formatted from real data. If the source is missing, the answer
says so explicitly. The LLM never fills gaps.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import http.client
import json
import logging
import os
import socket
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

_REPO = os.environ.get("UMH_ROOT", "/opt/OS")


@dataclass
class GroundingSource:
    source_id: str
    display_name: str
    freshness_max_s: int = 60
    required: bool = False


@dataclass
class GroundedResult:
    source: str
    freshness_s: float
    data: dict[str, Any]
    summary: str
    missing: list[str] = field(default_factory=list)
    confidence: str = "deterministic"
    collector_errors: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "freshness": round(self.freshness_s, 1),
            "data": self.data,
            "summary": self.summary,
            "missing": self.missing,
            "confidence": self.confidence,
        }


# ── Collectors ────────────────────────────────────────────────────────────────
# Each returns (data_dict, summary_str) or raises on failure.


def _collect_docker() -> tuple[dict[str, Any], str]:
    sock_path = "/var/run/docker.sock"
    if not os.path.exists(sock_path):
        raise FileNotFoundError("Docker socket not available")

    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(sock_path)
    s.settimeout(10)
    conn = http.client.HTTPConnection("localhost")
    conn.sock = s
    conn.request("GET", "/containers/json?all=false")
    resp = conn.getresponse()
    containers = json.loads(resp.read())

    items = []
    for c in containers:
        name = c["Names"][0].lstrip("/")
        status = c.get("Status", c.get("State", ""))
        ports = ", ".join(
            f"{p.get('IP', '0.0.0.0')}:{p['PublicPort']}->{p['PrivatePort']}"
            for p in c.get("Ports", [])
            if p.get("PublicPort")
        )
        items.append({"name": name, "status": status, "ports": ports})

    names = [i["name"] for i in items]
    summary = (
        f"{len(items)} containers running: {', '.join(names)}" if items else "No containers running"
    )
    return {"containers": items}, summary


def _collect_providers() -> tuple[dict[str, Any], str]:
    from substrate.sockets.intelligence_port import get_model_registry

    MODEL_REGISTRY = get_model_registry()

    providers = []
    for name, config in MODEL_REGISTRY.items():
        providers.append(
            {
                "name": name,
                "available": config.available,
                "model": getattr(config, "model", ""),
            }
        )
    healthy = [p for p in providers if p["available"]]
    summary = f"{len(healthy)}/{len(providers)} providers healthy" + (
        f" — {', '.join(p['name'] for p in healthy)}" if healthy else ""
    )
    return {"providers": providers}, summary


def _collect_voice() -> tuple[dict[str, Any], str]:
    stt = os.environ.get("UMH_STT_PROVIDER", "browser_native")
    tts = os.environ.get("UMH_TTS_PROVIDER", "kokoro")
    tts_host = os.environ.get("KOKORO_TTS_HOST", "")

    data: dict[str, Any] = {"stt_provider": stt, "tts_provider": tts}
    parts = [f"STT: {stt}", f"TTS: {tts}"]

    if tts_host:
        try:
            import urllib.request

            req = urllib.request.Request(f"http://{tts_host}/health", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data["tts_reachable"] = True
                parts.append(f"TTS server ({tts_host}): reachable")
        except Exception:
            data["tts_reachable"] = False
            parts.append(f"TTS server ({tts_host}): unreachable")
    else:
        data["tts_reachable"] = False
        parts.append("TTS server: not configured")

    return data, "; ".join(parts)


def _collect_vision() -> tuple[dict[str, Any], str]:
    relay_port = int(os.environ.get("VISION_RELAY_PORT", "8097"))
    health_port = relay_port + 1
    data: dict[str, Any] = {"relay_port": relay_port}

    try:
        import urllib.request

        req = urllib.request.Request(f"http://127.0.0.1:{health_port}/health", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            health = json.loads(resp.read())
            data.update(health)
            status = health.get("status", "unknown")
            viewers = health.get("viewer_count", 0)
            beast = "connected" if health.get("beast_connected") else "offline"
            cam = "streaming" if health.get("camera_streaming") else "off"
            fps = health.get("frame_fps", 0)
            blockers = health.get("blockers", [])
            recovery = health.get("recovery_action", "")
            parts = [f"Vision: {status}", f"beast={beast}", f"camera={cam}"]
            if fps:
                parts.append(f"{fps}fps")
            parts.append(f"{viewers} viewer(s)")
            if blockers:
                parts.append(f"blockers: {'; '.join(blockers)}")
            if recovery:
                parts.append(f"recovery: {recovery}")
            summary = ", ".join(parts)
    except Exception:
        data["relay_reachable"] = False
        summary = "Vision relay: unreachable (health endpoint not responding)"

    return data, summary


def _collect_work_packets() -> tuple[dict[str, Any], str]:
    wp_path = _work_packets_path()
    if not wp_path.exists():
        raise FileNotFoundError("work_packets.jsonl not found")

    active = 0
    blocked = 0
    total = 0
    with open(wp_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            if '"active"' in line or '"in_progress"' in line:
                active += 1
            if '"blocked"' in line:
                blocked += 1

    data = {"total": total, "active": active, "blocked": blocked}
    summary = f"{active} active, {blocked} blocked, {total} total work packets"
    return data, summary


def _collect_blocked_packets() -> tuple[dict[str, Any], str]:
    wp_path = _work_packets_path()
    if not wp_path.exists():
        raise FileNotFoundError("work_packets.jsonl not found")

    blocked_items: list[dict[str, Any]] = []
    with open(wp_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if '"blocked"' in line:
                try:
                    pkt = json.loads(line)
                    blocked_items.append(
                        {
                            "id": pkt.get("id", "?"),
                            "title": pkt.get("title", pkt.get("description", ""))[:80],
                            "reason": pkt.get("blocked_reason", ""),
                        }
                    )
                except json.JSONDecodeError:
                    pass

    data = {"blocked": blocked_items}
    if not blocked_items:
        summary = "No blocked work packets"
    else:
        summary = f"{len(blocked_items)} blocked: " + ", ".join(
            b["title"] or b["id"] for b in blocked_items[:5]
        )
    return data, summary


def _state_root() -> Path:
    """Runtime-state root for THIS module's reads.

    Resolves through the canonical runtime-state boundary, but anchored on the
    module-level ``_REPO`` so tests that patch ``_REPO`` (the established
    injection point for grounding isolation) still redirect these reads to a
    temp tree. Without this anchor the resolver would read live runtime state
    during "missing data" tests and fabricate grounded answers — exactly what
    this firewall exists to prevent.
    """
    import os as _os

    from substrate.state.runtime_paths import runtime_state_root

    prev = _os.environ.get("UMH_ROOT")
    override = _os.environ.get("UMH_STATE_DIR")
    if override and prev == _REPO:
        # explicit deployment override, module not redirected — honor it
        return runtime_state_root()
    try:
        _os.environ["UMH_ROOT"] = _REPO
        _os.environ.pop("UMH_STATE_DIR", None)
        return runtime_state_root()
    finally:
        if prev is None:
            _os.environ.pop("UMH_ROOT", None)
        else:
            _os.environ["UMH_ROOT"] = prev
        if override is not None:
            _os.environ["UMH_STATE_DIR"] = override


def _work_packets_path() -> Path:
    return _state_root() / "universal_work" / "work_packets.jsonl"


def _collect_workcell_heartbeats() -> tuple[dict[str, Any], str]:
    wc_dir = _state_root() / "organism" / "workcells"
    if not wc_dir.exists():
        raise FileNotFoundError("workcells directory not found")

    cells: list[dict[str, Any]] = []
    for hb in wc_dir.glob("*/heartbeat.json"):
        name = hb.parent.name
        try:
            with open(hb) as f:
                info = json.loads(f.read())
            cells.append(
                {
                    "name": name,
                    "status": info.get("status", "unknown"),
                    "last_beat": info.get("timestamp", info.get("last_heartbeat", "")),
                }
            )
        except Exception:
            cells.append({"name": name, "status": "unreadable"})

    data = {"workcells": cells}
    if not cells:
        summary = "No workcells reporting"
    else:
        names = [c["name"] for c in cells]
        summary = f"{len(cells)} workcells: {', '.join(names)}"
    return data, summary


def _collect_beast_health() -> tuple[dict[str, Any], str]:
    mesh_path = Path(_REPO) / "data" / "runtime" / "mesh_nodes.json"
    if not mesh_path.exists():
        raise FileNotFoundError("mesh_nodes.json not found")

    with open(mesh_path) as f:
        nodes = json.loads(f.read())

    beast = None
    for node in nodes if isinstance(nodes, list) else nodes.get("nodes", []):
        nid = node.get("node_id", node.get("id", ""))
        if "beast" in nid.lower() or "windows" in nid.lower():
            beast = node
            break

    if beast is None:
        raise ValueError("Beast node not found in mesh data")

    connected = beast.get("connected", beast.get("status") == "connected")
    summary = f"Beast: {'connected' if connected else 'disconnected'}"
    return {"beast": beast, "connected": connected}, summary


def _collect_recent_reports() -> tuple[dict[str, Any], str]:
    rpt_path = _state_root() / "organism" / "reports.jsonl"
    if not rpt_path.exists():
        raise FileNotFoundError("reports.jsonl not found")

    reports: list[dict[str, Any]] = []
    with open(rpt_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                reports.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    recent = reports[-5:] if reports else []
    data = {"recent": recent, "total": len(reports)}
    if not recent:
        summary = "No reports"
    else:
        summary = f"{len(reports)} total reports, latest: {recent[-1].get('title', recent[-1].get('type', '?'))}"
    return data, summary


def _collect_approvals() -> tuple[dict[str, Any], str]:
    wp_path = _work_packets_path()
    if not wp_path.exists():
        raise FileNotFoundError("work_packets.jsonl not found")

    pending: list[dict[str, Any]] = []
    with open(wp_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if (
                '"needs_approval"' in line
                or '"pending_approval"' in line
                or '"awaiting_approval"' in line
            ):
                try:
                    pkt = json.loads(line)
                    pending.append(
                        {
                            "id": pkt.get("id", "?"),
                            "title": pkt.get("title", pkt.get("description", ""))[:80],
                            "risk": pkt.get("risk", "unknown"),
                        }
                    )
                except json.JSONDecodeError:
                    pass

    data = {"pending_approvals": pending}
    if not pending:
        summary = "No items awaiting approval"
    else:
        summary = f"{len(pending)} items awaiting approval: " + ", ".join(
            a["title"] or a["id"] for a in pending[:5]
        )
    return data, summary


def _collect_recent_deployments() -> tuple[dict[str, Any], str]:
    from substrate.execution.cpu_gate import gated_subprocess_run

    result = gated_subprocess_run(
        ["git", "-C", _REPO, "log", "--oneline", "-10", "--format=%h %s (%cr)"],
        caller="grounding:deployments",
    )
    if result is None:
        raise RuntimeError("CPU gate blocked — cannot read git log")

    stdout = result.stdout or b""
    if isinstance(stdout, bytes):
        stdout = stdout.decode("utf-8", errors="replace")
    lines = stdout.strip().split("\n")

    commits = [l.strip() for l in lines if l.strip()]
    data = {"recent_commits": commits[:10]}
    if not commits:
        summary = "No recent commits found"
    else:
        summary = f"{len(commits)} recent commits, latest: {commits[0]}"
    return data, summary


def _collect_hermes_status() -> tuple[dict[str, Any], str]:
    data: dict[str, Any] = {"configured": False, "verified": False, "available": False}

    try:
        import adapters.models.hermes_cli as hcli

        data["configured"] = True
        data["available"] = hcli.is_available()
        data["verified"] = hcli.is_verified()

        if data["verified"]:
            summary = "Hermes: verified and callable"
        elif data["available"]:
            summary = "Hermes: reachable but not yet verified by a real call"
        else:
            summary = "Hermes: configured but not reachable"
    except ImportError:
        summary = "Hermes: adapter not installed"
    except Exception as exc:
        summary = f"Hermes: check failed ({exc})"

    return data, summary


def _collect_webhook_health() -> tuple[dict[str, Any], str]:
    sock_path = "/var/run/docker.sock"
    if not os.path.exists(sock_path):
        raise FileNotFoundError("Docker socket not available")

    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(sock_path)
    s.settimeout(10)
    conn = http.client.HTTPConnection("localhost")
    conn.sock = s
    conn.request("GET", "/containers/json?all=true")
    resp = conn.getresponse()
    containers = json.loads(resp.read())

    webhook = None
    for c in containers:
        name = c["Names"][0].lstrip("/")
        if "webhook" in name.lower():
            webhook = {
                "name": name,
                "status": c.get("Status", c.get("State", "")),
                "state": c.get("State", ""),
            }
            break

    if webhook is None:
        raise ValueError("os-webhook container not found")

    data = {"webhook": webhook}
    summary = f"Webhook: {webhook['status']}"
    return data, summary


# ── Collector registry ────────────────────────────────────────────────────────

_COLLECTORS: dict[str, Callable[[], tuple[dict[str, Any], str]]] = {
    "docker": _collect_docker,
    "providers": _collect_providers,
    "voice": _collect_voice,
    "vision": _collect_vision,
    "work_packets": _collect_work_packets,
    "blocked_packets": _collect_blocked_packets,
    "workcells": _collect_workcell_heartbeats,
    "beast": _collect_beast_health,
    "reports": _collect_recent_reports,
    "approvals": _collect_approvals,
    "deployments": _collect_recent_deployments,
    "hermes": _collect_hermes_status,
    "webhook": _collect_webhook_health,
}

# Which collectors are needed for each query type
_QUERY_SOURCES: dict[str, list[str]] = {
    "docker_status": ["docker"],
    "provider_health": ["providers"],
    "voice_health": ["voice"],
    "vision_status": ["vision"],
    "beast_health": ["beast"],
    "work_packets": ["work_packets"],
    "blocked_packets": ["blocked_packets"],
    "agent_status": ["workcells"],
    "recent_reports": ["reports"],
    "approval_status": ["approvals"],
    "recent_deployments": ["deployments"],
    "hermes_status": ["hermes"],
    "webhook_health": ["webhook"],
    "visual_query": ["vision"],
    "system_status": [
        "docker",
        "providers",
        "work_packets",
        "workcells",
        "voice",
        "vision",
        "beast",
    ],
    "composite_blockers": [
        "blocked_packets",
        "providers",
        "beast",
        "docker",
        "vision",
        "voice",
    ],
}

# Which sources are required (missing = blocker) vs optional (missing = partial)
_REQUIRED_SOURCES: dict[str, set[str]] = {
    "docker_status": {"docker"},
    "provider_health": {"providers"},
    "beast_health": {"beast"},
    "webhook_health": {"webhook"},
    "visual_query": {"vision"},
}


def collect_grounding(query_type: str) -> GroundedResult:
    """Collect all source data for a query type. Never raises."""
    source_ids = _QUERY_SOURCES.get(query_type, ["providers", "work_packets", "workcells"])
    required = _REQUIRED_SOURCES.get(query_type, set())

    all_data: dict[str, Any] = {}
    summaries: list[str] = []
    missing: list[str] = []
    errors: dict[str, str] = {}

    start = time.monotonic()

    for sid in source_ids:
        collector = _COLLECTORS.get(sid)
        if collector is None:
            missing.append(sid)
            errors[sid] = "no collector registered"
            continue
        try:
            data, summary = collector()
            all_data[sid] = data
            summaries.append(f"**{sid.replace('_', ' ').title()}:** {summary}")
        except Exception as exc:
            missing.append(sid)
            errors[sid] = str(exc)
            logger.debug("Grounding collector %s failed: %s", sid, exc)

    elapsed = time.monotonic() - start

    has_required_missing = bool(required & set(missing))
    if has_required_missing:
        confidence = "blocked"
    elif missing:
        confidence = "partial"
    else:
        confidence = "deterministic"

    combined_summary = "\n".join(summaries) if summaries else ""

    return GroundedResult(
        source=query_type,
        freshness_s=elapsed,
        data=all_data,
        summary=combined_summary,
        missing=missing,
        confidence=confidence,
        collector_errors=errors,
    )


# ── Status-seeking detection for conversation mode ────────────────────────────

_STATUS_SEEKING_PATTERNS: list[tuple[str, str]] = [
    # Docker
    ("docker", "docker_status"),
    ("container", "docker_status"),
    ("containers running", "docker_status"),
    # Providers
    ("provider", "provider_health"),
    ("providers online", "provider_health"),
    ("providers healthy", "provider_health"),
    ("model health", "provider_health"),
    ("llm status", "provider_health"),
    # Voice
    ("voice health", "voice_health"),
    ("voice status", "voice_health"),
    ("voice service", "voice_health"),
    ("tts status", "voice_health"),
    ("stt status", "voice_health"),
    # Vision / Camera
    ("camera status", "vision_status"),
    ("vision status", "vision_status"),
    ("vision service", "vision_status"),
    ("camera stream", "vision_status"),
    ("camera active", "vision_status"),
    ("camera is", "vision_status"),
    # Visual queries — require a real frame
    ("what do you see", "visual_query"),
    ("what can you see", "visual_query"),
    ("describe what", "visual_query"),
    ("look at the screen", "visual_query"),
    ("what's on screen", "visual_query"),
    ("whats on screen", "visual_query"),
    ("what is on the screen", "visual_query"),
    # Beast
    ("beast status", "beast_health"),
    ("beast health", "beast_health"),
    ("beast daemon", "beast_health"),
    ("beast online", "beast_health"),
    # Work packets
    ("work packet", "work_packets"),
    ("active packets", "work_packets"),
    # Blockers
    ("blocked packet", "blocked_packets"),
    ("what is blocked", "blocked_packets"),
    ("what's blocked", "blocked_packets"),
    ("whats blocked", "blocked_packets"),
    # Reports
    ("recent reports", "recent_reports"),
    ("latest reports", "recent_reports"),
    ("reports created", "recent_reports"),
    ("reports today", "recent_reports"),
    ("what reports", "recent_reports"),
    ("show reports", "recent_reports"),
    ("list reports", "recent_reports"),
    # Approvals
    ("needs approval", "approval_status"),
    ("what needs approval", "approval_status"),
    ("pending approval", "approval_status"),
    ("approval queue", "approval_status"),
    ("awaiting approval", "approval_status"),
    # Deployments
    ("what did we deploy", "recent_deployments"),
    ("recent deploy", "recent_deployments"),
    ("latest deploy", "recent_deployments"),
    ("what did we ship", "recent_deployments"),
    ("what shipped", "recent_deployments"),
    ("deploy last", "recent_deployments"),
    ("last deploy", "recent_deployments"),
    # Hermes
    ("hermes status", "hermes_status"),
    ("hermes available", "hermes_status"),
    ("hermes health", "hermes_status"),
    ("is hermes", "hermes_status"),
    # Webhook
    ("webhook status", "webhook_health"),
    ("webhook health", "webhook_health"),
    # System composite
    ("system status", "system_status"),
    ("overall status", "system_status"),
    ("how is everything", "system_status"),
    ("how are things", "system_status"),
    ("current system state", "system_status"),
    ("summarize the current system", "system_status"),
]


def detect_status_seeking(text: str) -> str | None:
    """Return a query_type if text contains status-seeking language, else None."""
    lowered = text.lower()
    for pattern, qtype in _STATUS_SEEKING_PATTERNS:
        if pattern in lowered:
            return qtype
    return None
