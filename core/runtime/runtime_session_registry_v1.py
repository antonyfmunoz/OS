"""Runtime Session Registry v1 for the UMH substrate layer.

Manages active runtime sessions. A RuntimeSession binds a worker
to an environment with tracked packets, heartbeat, and health.
The registry is the single source of truth for what's currently
running.

UMH substrate subsystem. Phase 96.8AE.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class RuntimeMode(str, Enum):
    SUPERVISED = "supervised"
    AUTONOMOUS = "autonomous"
    DRY_RUN = "dry_run"


class RuntimeHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    RECOVERING = "recovering"
    STOPPED = "stopped"


@dataclass
class RuntimeSession:
    """A live session binding a worker to an environment."""

    session_id: str
    worker_id: str
    environment_id: str
    active_packets: list[str] = field(default_factory=list)
    completed_packets: list[str] = field(default_factory=list)
    failed_packets: list[str] = field(default_factory=list)
    last_heartbeat: str = ""
    runtime_mode: RuntimeMode = RuntimeMode.SUPERVISED
    runtime_health: RuntimeHealth = RuntimeHealth.STOPPED
    started_at: str = ""
    stopped_at: str = ""
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.started_at:
            self.started_at = datetime.now(timezone.utc).isoformat()

    @property
    def is_active(self) -> bool:
        return self.runtime_health in {RuntimeHealth.HEALTHY, RuntimeHealth.DEGRADED}

    @property
    def packet_count(self) -> int:
        return len(self.active_packets) + len(self.completed_packets) + len(self.failed_packets)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "worker_id": self.worker_id,
            "environment_id": self.environment_id,
            "active_packets": self.active_packets,
            "completed_packets": self.completed_packets,
            "failed_packets": self.failed_packets,
            "last_heartbeat": self.last_heartbeat,
            "runtime_mode": self.runtime_mode.value,
            "runtime_health": self.runtime_health.value,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "is_active": self.is_active,
            "packet_count": self.packet_count,
            "notes": self.notes,
        }


class RuntimeSessionRegistry:
    """Registry of all runtime sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, RuntimeSession] = {}

    def create_session(
        self,
        worker_id: str,
        environment_id: str,
        runtime_mode: RuntimeMode = RuntimeMode.SUPERVISED,
    ) -> RuntimeSession:
        session_id = f"SESSION-{uuid.uuid4().hex[:8]}"
        session = RuntimeSession(
            session_id=session_id,
            worker_id=worker_id,
            environment_id=environment_id,
            runtime_mode=runtime_mode,
            runtime_health=RuntimeHealth.HEALTHY,
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> RuntimeSession | None:
        return self._sessions.get(session_id)

    def get_active_sessions(self) -> list[RuntimeSession]:
        return [s for s in self._sessions.values() if s.is_active]

    def get_sessions_for_worker(self, worker_id: str) -> list[RuntimeSession]:
        return [s for s in self._sessions.values() if s.worker_id == worker_id]

    def assign_packet(self, session_id: str, packet_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session or not session.is_active:
            return False
        if packet_id not in session.active_packets:
            session.active_packets.append(packet_id)
        return True

    def complete_packet(self, session_id: str, packet_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        if packet_id in session.active_packets:
            session.active_packets.remove(packet_id)
        if packet_id not in session.completed_packets:
            session.completed_packets.append(packet_id)
        return True

    def fail_packet(self, session_id: str, packet_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        if packet_id in session.active_packets:
            session.active_packets.remove(packet_id)
        if packet_id not in session.failed_packets:
            session.failed_packets.append(packet_id)
        return True

    def stop_session(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.runtime_health = RuntimeHealth.STOPPED
        session.stopped_at = datetime.now(timezone.utc).isoformat()
        return True

    @property
    def session_count(self) -> int:
        return len(self._sessions)

    @property
    def active_count(self) -> int:
        return len(self.get_active_sessions())

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_sessions": self.session_count,
            "active_sessions": self.active_count,
            "sessions": {sid: s.to_dict() for sid, s in self._sessions.items()},
        }
