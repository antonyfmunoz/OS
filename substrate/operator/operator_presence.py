"""Operator Presence Models — types for presence and continuity tracking.

Defines the data structures that model where the operator is, what they
are working on, and what context should survive device switches.

No surveillance, no autonomous execution, no keyboard/mouse automation.
Observation only. Explicit operator-visible state.

Phase 32. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class PresenceState(str, Enum):
    """Operator's current presence state."""

    ACTIVE = "active"
    IDLE = "idle"
    AWAY = "away"
    OFFLINE = "offline"


class PresenceDeviceType(str, Enum):
    """Device type for presence tracking."""

    VPS = "vps"
    WINDOWS = "windows"
    IPAD = "ipad"
    IPHONE = "iphone"
    UNKNOWN = "unknown"


class ContinuityStatus(str, Enum):
    """Status of a continuity checkpoint."""

    CURRENT = "current"
    RESUMABLE = "resumable"
    STALE = "stale"
    LOST = "lost"


@dataclass
class OperatorPresence:
    """Current operator presence state."""

    state: PresenceState
    device_type: PresenceDeviceType
    device_id: str = ""
    node_id: str = ""
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "device_type": self.device_type.value,
            "device_id": self.device_id,
            "node_id": self.node_id,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OperatorPresence:
        return cls(
            state=PresenceState(data.get("state", "offline")),
            device_type=PresenceDeviceType(data.get("device_type", "unknown")),
            device_id=data.get("device_id", ""),
            node_id=data.get("node_id", ""),
            updated_at=data.get("updated_at", time.time()),
        )


@dataclass
class ActiveContext:
    """What the operator is currently working on."""

    workspace_id: str = ""
    workspace_name: str = ""
    session_id: str = ""
    session_type: str = ""
    runtime_id: str = ""
    work_packet_id: str = ""
    action_id: str = ""
    description: str = ""
    started_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "workspace_name": self.workspace_name,
            "session_id": self.session_id,
            "session_type": self.session_type,
            "runtime_id": self.runtime_id,
            "work_packet_id": self.work_packet_id,
            "action_id": self.action_id,
            "description": self.description,
            "started_at": self.started_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActiveContext:
        return cls(
            workspace_id=data.get("workspace_id", ""),
            workspace_name=data.get("workspace_name", ""),
            session_id=data.get("session_id", ""),
            session_type=data.get("session_type", ""),
            runtime_id=data.get("runtime_id", ""),
            work_packet_id=data.get("work_packet_id", ""),
            action_id=data.get("action_id", ""),
            description=data.get("description", ""),
            started_at=data.get("started_at", time.time()),
        )


@dataclass
class ContinuityCheckpoint:
    """A resumable checkpoint for operator continuity."""

    checkpoint_id: str = field(default_factory=lambda: f"ccp-{uuid4().hex[:10]}")
    checkpoint_type: str = ""
    title: str = ""
    detail: str = ""
    device_type: PresenceDeviceType = PresenceDeviceType.UNKNOWN
    device_id: str = ""
    workspace_id: str = ""
    session_id: str = ""
    status: ContinuityStatus = ContinuityStatus.CURRENT
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "checkpoint_type": self.checkpoint_type,
            "title": self.title,
            "detail": self.detail,
            "device_type": self.device_type.value,
            "device_id": self.device_id,
            "workspace_id": self.workspace_id,
            "session_id": self.session_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContinuityCheckpoint:
        return cls(
            checkpoint_id=data.get("checkpoint_id", f"ccp-{uuid4().hex[:10]}"),
            checkpoint_type=data.get("checkpoint_type", ""),
            title=data.get("title", ""),
            detail=data.get("detail", ""),
            device_type=PresenceDeviceType(data.get("device_type", "unknown")),
            device_id=data.get("device_id", ""),
            workspace_id=data.get("workspace_id", ""),
            session_id=data.get("session_id", ""),
            status=ContinuityStatus(data.get("status", "current")),
            created_at=data.get("created_at", time.time()),
            expires_at=data.get("expires_at", 0.0),
        )


@dataclass
class PresenceSnapshot:
    """Complete operator presence and continuity state."""

    operator_state: PresenceState
    active_device: PresenceDeviceType
    active_device_id: str = ""
    active_node_id: str = ""
    active_context: ActiveContext = field(default_factory=ActiveContext)
    continuity_checkpoints: list[ContinuityCheckpoint] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "operator_state": self.operator_state.value,
            "active_device": self.active_device.value,
            "active_device_id": self.active_device_id,
            "active_node_id": self.active_node_id,
            "active_context": self.active_context.to_dict(),
            "continuity_checkpoints": [
                c.to_dict() for c in self.continuity_checkpoints
            ],
            "generated_at": self.generated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PresenceSnapshot:
        return cls(
            operator_state=PresenceState(data.get("operator_state", "offline")),
            active_device=PresenceDeviceType(data.get("active_device", "unknown")),
            active_device_id=data.get("active_device_id", ""),
            active_node_id=data.get("active_node_id", ""),
            active_context=ActiveContext.from_dict(data.get("active_context", {})),
            continuity_checkpoints=[
                ContinuityCheckpoint.from_dict(c)
                for c in data.get("continuity_checkpoints", [])
            ],
            generated_at=data.get("generated_at", time.time()),
        )
