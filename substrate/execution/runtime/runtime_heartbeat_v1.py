"""Runtime Heartbeat v1 for the UMH substrate layer.

Persistent heartbeat system for runtime workers. Extends the
environment bridge heartbeat with runtime-specific lifecycle
tracking, timeout detection, and health state transitions.

Composes: core/environment_bridge/heartbeat.py

UMH substrate subsystem. Phase 96.8AE.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class HeartbeatHealth(str, Enum):
    ALIVE = "alive"
    DEGRADED = "degraded"
    TIMEOUT = "timeout"
    DEAD = "dead"


HEARTBEAT_TIMEOUT_SECONDS = 30
HEARTBEAT_DEGRADED_SECONDS = 15


@dataclass
class RuntimeHeartbeat:
    """Periodic liveness signal from a runtime worker."""

    worker_id: str
    session_id: str = ""
    timestamp: str = ""
    health: HeartbeatHealth = HeartbeatHealth.ALIVE
    active_packet_id: str = ""
    capabilities: list[str] = field(default_factory=list)
    environment_type: str = ""
    uptime_seconds: float = 0.0
    packets_completed: int = 0
    packets_failed: int = 0
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "health": self.health.value,
            "active_packet_id": self.active_packet_id,
            "capabilities": self.capabilities,
            "environment_type": self.environment_type,
            "uptime_seconds": self.uptime_seconds,
            "packets_completed": self.packets_completed,
            "packets_failed": self.packets_failed,
            "notes": self.notes,
        }


def evaluate_heartbeat_health(
    heartbeat: RuntimeHeartbeat,
    now: datetime | None = None,
) -> HeartbeatHealth:
    """Evaluate heartbeat freshness and return health state."""
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

    if age > HEARTBEAT_TIMEOUT_SECONDS:
        return HeartbeatHealth.TIMEOUT
    if age > HEARTBEAT_DEGRADED_SECONDS:
        return HeartbeatHealth.DEGRADED
    return HeartbeatHealth.ALIVE


def write_runtime_heartbeat(path: Path, heartbeat: RuntimeHeartbeat) -> bool:
    """Persist heartbeat to filesystem."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(heartbeat.to_dict(), indent=2))
        return True
    except OSError:
        return False


def read_runtime_heartbeat(path: Path) -> RuntimeHeartbeat | None:
    """Read heartbeat from filesystem."""
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text())
        return RuntimeHeartbeat(
            worker_id=data.get("worker_id", ""),
            session_id=data.get("session_id", ""),
            timestamp=data.get("timestamp", ""),
            health=HeartbeatHealth(data.get("health", "dead")),
            active_packet_id=data.get("active_packet_id", ""),
            capabilities=data.get("capabilities", []),
            environment_type=data.get("environment_type", ""),
            uptime_seconds=data.get("uptime_seconds", 0.0),
            packets_completed=data.get("packets_completed", 0),
            packets_failed=data.get("packets_failed", 0),
            notes=data.get("notes", []),
        )
    except (json.JSONDecodeError, OSError, ValueError):
        return None
