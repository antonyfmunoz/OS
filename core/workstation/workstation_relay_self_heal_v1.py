"""Workstation Relay Self-Heal v1.

VPS-side relay health assessment and self-heal logic.
Reads heartbeat, detects staleness, reports autostart state,
and determines whether relay is available for execution dispatch.

UMH substrate subsystem. Phase 96.8AP.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.runtime.runtime_heartbeat_v1 import HeartbeatHealth
from core.workstation.workstation_relay_heartbeat_v1 import (
    RELAY_HEARTBEAT_STALE_SECONDS,
    RelayHeartbeat,
    evaluate_relay_health,
    read_relay_heartbeat,
)


AUTOSTART_MARKER_PATH = Path("data/runtime/workstation_relay/autostart_marker.json")
RELAY_LOG_DIR = Path("data/runtime/workstation_relay/logs")
RELAY_PROOF_DIR = Path("data/runtime/workstation_relay/proofs")


@dataclass
class RelayHealthReport:
    """Comprehensive relay health report for !relay-status."""

    online: bool = False
    health: str = "dead"
    autostart_installed: bool = False
    autostart_task_name: str = ""
    autostart_installed_at: str = ""
    heartbeat_age_seconds: float = -1
    heartbeat_stale: bool = True
    heartbeat_fresh: bool = False
    restart_recommended: bool = False
    execution_allowed: bool = False
    denial_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "online": self.online,
            "health": self.health,
            "autostart_installed": self.autostart_installed,
            "autostart_task_name": self.autostart_task_name,
            "autostart_installed_at": self.autostart_installed_at,
            "heartbeat_age_seconds": round(self.heartbeat_age_seconds, 1),
            "heartbeat_stale": self.heartbeat_stale,
            "heartbeat_fresh": self.heartbeat_fresh,
            "restart_recommended": self.restart_recommended,
            "execution_allowed": self.execution_allowed,
            "denial_reason": self.denial_reason,
        }


def read_autostart_marker(
    base_dir: Path = Path("/opt/OS"),
) -> dict[str, Any] | None:
    """Read the autostart marker if it exists."""
    path = base_dir / AUTOSTART_MARKER_PATH
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def compute_heartbeat_age(
    heartbeat: RelayHeartbeat | None,
    now: datetime | None = None,
) -> float:
    """Return heartbeat age in seconds. Returns -1 if no valid heartbeat."""
    if heartbeat is None or not heartbeat.timestamp:
        return -1
    current = now or datetime.now(timezone.utc)
    try:
        ts = datetime.fromisoformat(heartbeat.timestamp.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return (current - ts).total_seconds()
    except (ValueError, TypeError):
        return -1


def assess_relay_health(
    base_dir: Path = Path("/opt/OS"),
    now: datetime | None = None,
    stale_seconds: float = RELAY_HEARTBEAT_STALE_SECONDS,
) -> RelayHealthReport:
    """Full relay health assessment for !relay-status and dispatch gating."""
    report = RelayHealthReport()

    marker = read_autostart_marker(base_dir)
    if marker:
        report.autostart_installed = True
        report.autostart_task_name = marker.get("task_name", "")
        report.autostart_installed_at = marker.get("installed_at", "")

    hb = read_relay_heartbeat(base_dir)
    health = evaluate_relay_health(hb, now=now, stale_seconds=stale_seconds)
    report.health = health.value

    if hb is not None:
        age = compute_heartbeat_age(hb, now)
        report.heartbeat_age_seconds = age
        report.heartbeat_stale = age > stale_seconds or age < 0
        report.heartbeat_fresh = 0 <= age <= stale_seconds

    if health in (HeartbeatHealth.ALIVE, HeartbeatHealth.DEGRADED):
        report.online = True
    else:
        report.online = False
        report.restart_recommended = True

    if report.online and hb is not None:
        if not hb.desktop_session_active:
            report.execution_allowed = False
            report.denial_reason = "no_desktop_session"
        elif not hb.chrome_available:
            report.execution_allowed = False
            report.denial_reason = "chrome_unavailable"
        else:
            report.execution_allowed = True
    else:
        report.execution_allowed = False
        if not report.online:
            report.denial_reason = "relay_offline"

    return report


def should_allow_chrome_proof(
    base_dir: Path = Path("/opt/OS"),
) -> tuple[bool, str]:
    """Gate check for !chrome-proof dispatch.

    Returns (allowed, reason).
    """
    report = assess_relay_health(base_dir)
    if not report.online:
        return False, f"relay_offline (health={report.health})"
    if not report.execution_allowed:
        return False, report.denial_reason
    if report.heartbeat_stale:
        return False, "heartbeat_stale"
    return True, "relay_healthy"
