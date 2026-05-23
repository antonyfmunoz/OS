"""Workstation Relay Heartbeat v1.

Extends the existing RuntimeHeartbeat with workstation-specific
fields (desktop state, Chrome availability, relay identity).
Read/write from the canonical heartbeat path.

UMH substrate subsystem.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from substrate.execution.runtime.runtime_heartbeat_v1 import (

    HEARTBEAT_TIMEOUT_SECONDS,
    HeartbeatHealth,
)

import os
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"



RELAY_HEARTBEAT_PATH = Path("data/runtime/workstation_relay/heartbeat.json")

RELAY_HEARTBEAT_STALE_SECONDS = 60


@dataclass
class RelayHeartbeat:
    """Heartbeat from a workstation relay node."""

    node_id: str = ""
    machine_name: str = ""
    user_name: str = ""
    os: str = ""
    relay_pid: int = 0
    relay_version: str = "v1"
    repo_commit: str = ""
    relay_script_hash: str = ""
    desktop_session_active: bool = False
    desktop_unlocked: bool = False
    monitor_detected: bool = False
    chrome_available: bool = False
    capabilities: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "machine_name": self.machine_name,
            "user_name": self.user_name,
            "os": self.os,
            "relay_pid": self.relay_pid,
            "relay_version": self.relay_version,
            "repo_commit": self.repo_commit,
            "relay_script_hash": self.relay_script_hash,
            "desktop_session_active": self.desktop_session_active,
            "desktop_unlocked": self.desktop_unlocked,
            "monitor_detected": self.monitor_detected,
            "chrome_available": self.chrome_available,
            "capabilities": self.capabilities,
            "timestamp": self.timestamp,
        }


def write_relay_heartbeat(
    heartbeat: RelayHeartbeat,
    base_dir: Path = Path(_ROOT),
) -> Path:
    """Write relay heartbeat to the canonical path."""
    path = base_dir / RELAY_HEARTBEAT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(heartbeat.to_dict(), indent=2))
    return path


def read_relay_heartbeat(
    base_dir: Path = Path(_ROOT),
) -> RelayHeartbeat | None:
    """Read relay heartbeat from the canonical path."""
    path = base_dir / RELAY_HEARTBEAT_PATH
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text())
        return RelayHeartbeat(
            node_id=data.get("node_id", ""),
            machine_name=data.get("machine_name", ""),
            user_name=data.get("user_name", ""),
            os=data.get("os", ""),
            relay_pid=data.get("relay_pid", 0),
            relay_version=data.get("relay_version", "v1"),
            repo_commit=data.get("repo_commit", ""),
            relay_script_hash=data.get("relay_script_hash", ""),
            desktop_session_active=data.get("desktop_session_active", False),
            desktop_unlocked=data.get("desktop_unlocked", False),
            monitor_detected=data.get("monitor_detected", False),
            chrome_available=data.get("chrome_available", False),
            capabilities=data.get("capabilities", []),
            timestamp=data.get("timestamp", ""),
        )
    except (json.JSONDecodeError, OSError):
        return None


def evaluate_relay_health(
    heartbeat: RelayHeartbeat | None,
    now: datetime | None = None,
    stale_seconds: float = RELAY_HEARTBEAT_STALE_SECONDS,
) -> HeartbeatHealth:
    """Evaluate relay heartbeat freshness."""
    if heartbeat is None:
        return HeartbeatHealth.DEAD
    if not heartbeat.timestamp:
        return HeartbeatHealth.DEAD

    current = now or datetime.now(timezone.utc)
    try:
        ts = datetime.fromisoformat(heartbeat.timestamp.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age = (current - ts).total_seconds()
    except (ValueError, TypeError):
        return HeartbeatHealth.DEAD

    if age > stale_seconds:
        return HeartbeatHealth.TIMEOUT
    if age > stale_seconds / 2:
        return HeartbeatHealth.DEGRADED
    return HeartbeatHealth.ALIVE


def is_relay_online(
    base_dir: Path = Path(_ROOT),
    stale_seconds: float = RELAY_HEARTBEAT_STALE_SECONDS,
) -> tuple[bool, str]:
    """Check if the relay is online. Returns (online, reason)."""
    hb = read_relay_heartbeat(base_dir)
    if hb is None:
        return False, "no_heartbeat_file"
    health = evaluate_relay_health(hb, stale_seconds=stale_seconds)
    if health == HeartbeatHealth.DEAD:
        return False, "heartbeat_dead"
    if health == HeartbeatHealth.TIMEOUT:
        return False, "heartbeat_stale"
    if not hb.desktop_session_active:
        return False, "no_desktop_session"
    return True, health.value
