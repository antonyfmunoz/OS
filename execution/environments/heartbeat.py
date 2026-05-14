"""Worker heartbeat for the Environment Bridge.

Tracks local worker liveness via file-based heartbeat. The local
worker writes a heartbeat file periodically; the VPS reads it to
determine if the worker is online/stale/offline.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class WorkerHeartbeatStatus(str, Enum):
    ONLINE = "online"
    STALE = "stale"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


@dataclass
class WorkerHeartbeat:
    worker_id: str = ""
    host: str = ""
    environment: str = ""
    tmux_session: str = ""
    last_seen_at: str = ""
    active_packet_id: str = ""
    status: WorkerHeartbeatStatus = WorkerHeartbeatStatus.UNKNOWN
    capabilities: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "host": self.host,
            "environment": self.environment,
            "tmux_session": self.tmux_session,
            "last_seen_at": self.last_seen_at,
            "active_packet_id": self.active_packet_id,
            "status": self.status.value,
            "capabilities": self.capabilities,
            "notes": self.notes,
        }


def build_worker_heartbeat(
    worker_id: str = "local-windows-worker",
    host: str = "DESKTOP-LVGUIQ9",
    environment: str = "local_wsl",
    tmux_session: str = "eos-worker",
    capabilities: list[str] | None = None,
) -> WorkerHeartbeat:
    return WorkerHeartbeat(
        worker_id=worker_id,
        host=host,
        environment=environment,
        tmux_session=tmux_session,
        last_seen_at=datetime.now(timezone.utc).isoformat(),
        status=WorkerHeartbeatStatus.ONLINE,
        capabilities=capabilities
        or [
            "local_windows_gui",
            "local_browser",
            "local_tmux",
            "chrome_visible",
            "accessibility_tree",
        ],
    )


def heartbeat_is_stale(
    heartbeat: WorkerHeartbeat,
    current_time: datetime | None = None,
    threshold_seconds: int = 60,
) -> bool:
    if not heartbeat.last_seen_at:
        return True
    now = current_time or datetime.now(timezone.utc)
    try:
        last_seen = datetime.fromisoformat(heartbeat.last_seen_at)
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)
        delta = (now - last_seen).total_seconds()
        return delta > threshold_seconds
    except (ValueError, TypeError):
        return True


def write_heartbeat(path: str, heartbeat: WorkerHeartbeat) -> bool:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(heartbeat.to_dict(), indent=2))
        return True
    except OSError:
        return False


def read_heartbeat(path: str) -> WorkerHeartbeat | None:
    p = Path(path)
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text())
        hb = WorkerHeartbeat(
            worker_id=data.get("worker_id", ""),
            host=data.get("host", ""),
            environment=data.get("environment", ""),
            tmux_session=data.get("tmux_session", ""),
            last_seen_at=data.get("last_seen_at", ""),
            active_packet_id=data.get("active_packet_id", ""),
            status=WorkerHeartbeatStatus(data.get("status", "unknown")),
            capabilities=data.get("capabilities", []),
            notes=data.get("notes", []),
        )
        return hb
    except (json.JSONDecodeError, OSError, ValueError):
        return None


def summarize_heartbeat(heartbeat: WorkerHeartbeat) -> dict[str, Any]:
    return {
        "worker_id": heartbeat.worker_id,
        "host": heartbeat.host,
        "status": heartbeat.status.value,
        "last_seen_at": heartbeat.last_seen_at,
        "stale": heartbeat_is_stale(heartbeat),
        "active_packet": heartbeat.active_packet_id or "none",
        "capabilities": heartbeat.capabilities,
    }
