"""Workstation Relay Node v1.

Represents a Windows workstation relay node that can receive
commands from the VPS control plane and execute real GUI actions.
This is the identity and contract layer — not execution.

UMH substrate subsystem. Phase 96.8AO.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RELAY_CAPABILITIES = (
    "launch_chrome",
    "focus_window",
    "navigate_url",
    "capture_screenshot",
    "report_hwnd",
    "report_foreground_window",
    "report_desktop_state",
)


@dataclass
class WorkstationRelayNode:
    """Identity and state of a Windows workstation relay node."""

    node_id: str = ""
    machine_name: str = ""
    user_name: str = ""
    os: str = ""
    environment_type: str = "local_windows_desktop"
    relay_version: str = "v1"
    repo_commit: str = ""
    relay_script_hash: str = ""
    desktop_session_active: bool = False
    desktop_unlocked: bool = False
    monitor_detected: bool = False
    chrome_available: bool = False
    last_heartbeat_at: str = ""
    status: str = "offline"
    capabilities: list[str] = field(default_factory=lambda: list(RELAY_CAPABILITIES))
    relay_pid: int = 0

    def __post_init__(self) -> None:
        if not self.node_id and self.machine_name:
            raw = f"{self.machine_name}:{self.user_name}:{self.environment_type}"
            self.node_id = f"WRN-{hashlib.sha256(raw.encode()).hexdigest()[:8]}"

    @property
    def is_online(self) -> bool:
        return self.status in ("online", "active", "idle")

    @property
    def is_execution_capable(self) -> bool:
        return (
            self.is_online
            and self.desktop_session_active
            and self.desktop_unlocked
            and self.chrome_available
        )

    @property
    def maturity_ceiling_reason(self) -> str:
        if not self.is_online:
            return "relay_offline"
        if not self.desktop_session_active:
            return "no_desktop_session"
        if not self.desktop_unlocked:
            return "desktop_locked"
        if not self.chrome_available:
            return "chrome_unavailable"
        return "execution_capable"

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "machine_name": self.machine_name,
            "user_name": self.user_name,
            "os": self.os,
            "environment_type": self.environment_type,
            "relay_version": self.relay_version,
            "repo_commit": self.repo_commit,
            "relay_script_hash": self.relay_script_hash,
            "desktop_session_active": self.desktop_session_active,
            "desktop_unlocked": self.desktop_unlocked,
            "monitor_detected": self.monitor_detected,
            "chrome_available": self.chrome_available,
            "last_heartbeat_at": self.last_heartbeat_at,
            "status": self.status,
            "capabilities": self.capabilities,
            "relay_pid": self.relay_pid,
            "is_online": self.is_online,
            "is_execution_capable": self.is_execution_capable,
            "maturity_ceiling_reason": self.maturity_ceiling_reason,
        }


def load_relay_node_from_heartbeat(heartbeat_path: Path) -> WorkstationRelayNode | None:
    """Load a relay node state from its heartbeat file."""
    if not heartbeat_path.is_file():
        return None
    try:
        data = json.loads(heartbeat_path.read_text())
        return WorkstationRelayNode(
            node_id=data.get("node_id", ""),
            machine_name=data.get("machine_name", ""),
            user_name=data.get("user_name", ""),
            os=data.get("os", ""),
            relay_version=data.get("relay_version", "v1"),
            repo_commit=data.get("repo_commit", ""),
            relay_script_hash=data.get("relay_script_hash", ""),
            desktop_session_active=data.get("desktop_session_active", False),
            desktop_unlocked=data.get("desktop_unlocked", False),
            monitor_detected=data.get("monitor_detected", False),
            chrome_available=data.get("chrome_available", False),
            last_heartbeat_at=data.get("timestamp", ""),
            status="online",
            capabilities=data.get("capabilities", list(RELAY_CAPABILITIES)),
            relay_pid=data.get("relay_pid", 0),
        )
    except (json.JSONDecodeError, OSError):
        return None
