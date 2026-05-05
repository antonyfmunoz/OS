"""Phase 84 interface events — typed descriptive event model.

Events are descriptive records. No execution. No state mutation.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.core.clock import iso_now as _iso_now


class InterfaceEventType(str, Enum):
    SURFACE_OPENED = "surface_opened"
    SURFACE_CLOSED = "surface_closed"
    SURFACE_EXPANDED = "surface_expanded"
    SURFACE_MINIMIZED = "surface_minimized"
    SURFACE_HIDDEN = "surface_hidden"
    SURFACE_DRAGGED = "surface_dragged"
    COMMAND_RECEIVED = "command_received"
    COMMAND_VALIDATED = "command_validated"
    COMMAND_REJECTED = "command_rejected"
    COMMAND_ROUTED = "command_routed"
    APPROVAL_SHOWN = "approval_shown"
    APPROVAL_RESPONDED = "approval_responded"
    NOTIFICATION_SHOWN = "notification_shown"
    NOTIFICATION_ACKED = "notification_acked"
    VOICE_IDLE = "voice_idle"
    VOICE_LISTENING = "voice_listening"
    VOICE_THINKING = "voice_thinking"
    VOICE_SPEAKING = "voice_speaking"
    VOICE_MUTED = "voice_muted"
    EXECUTION_STATUS_CHANGED = "execution_status_changed"
    DASHBOARD_REFRESHED = "dashboard_refreshed"
    UNKNOWN = "unknown"


class InterfaceEventSource(str, Enum):
    USER = "user"
    SYSTEM = "system"
    WORKSTATION = "workstation"
    CONTROL_PLANE = "control_plane"
    OBSERVABILITY = "observability"
    GOVERNANCE = "governance"
    STORAGE = "storage"
    REGISTRY = "registry"
    ONTOLOGY = "ontology"
    MIGRATION = "migration"
    UNKNOWN = "unknown"


def normalize_event_type(value: str) -> InterfaceEventType:
    try:
        return InterfaceEventType(value.lower().strip())
    except (ValueError, AttributeError):
        return InterfaceEventType.UNKNOWN


def normalize_event_source(value: str) -> InterfaceEventSource:
    try:
        return InterfaceEventSource(value.lower().strip())
    except (ValueError, AttributeError):
        return InterfaceEventSource.UNKNOWN


@dataclass
class InterfaceEvent:
    event_id: str
    event_type: InterfaceEventType = InterfaceEventType.UNKNOWN
    source: InterfaceEventSource = InterfaceEventSource.UNKNOWN
    surface_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    command_id: str | None = None
    timestamp: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    read_only: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value
            if isinstance(self.event_type, Enum)
            else self.event_type,
            "source": self.source.value if isinstance(self.source, Enum) else self.source,
            "surface_id": self.surface_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "command_id": self.command_id,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "read_only": self.read_only,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InterfaceEvent:
        return cls(
            event_id=data.get("event_id", ""),
            event_type=normalize_event_type(data.get("event_type", "unknown")),
            source=normalize_event_source(data.get("source", "unknown")),
            surface_id=data.get("surface_id"),
            user_id=data.get("user_id"),
            session_id=data.get("session_id"),
            command_id=data.get("command_id"),
            timestamp=data.get("timestamp"),
            payload=data.get("payload", {}),
            read_only=data.get("read_only", True),
            metadata=data.get("metadata", {}),
        )


@dataclass
class InterfaceEventBatch:
    batch_id: str
    events: list[dict[str, Any]] = field(default_factory=list)
    total: int = 0
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "events": self.events,
            "total": self.total,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def create_interface_event(
    event_type: InterfaceEventType = InterfaceEventType.UNKNOWN,
    source: InterfaceEventSource = InterfaceEventSource.UNKNOWN,
    *,
    surface_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    command_id: str | None = None,
    payload: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> InterfaceEvent:
    eid = f"evt_{hashlib.sha256(f'{event_type.value}{_iso_now()}'.encode()).hexdigest()[:10]}"
    return InterfaceEvent(
        event_id=eid,
        event_type=event_type,
        source=source,
        surface_id=surface_id,
        user_id=user_id,
        session_id=session_id,
        command_id=command_id,
        timestamp=_iso_now(),
        payload=payload or {},
        read_only=True,
        metadata=metadata or {},
    )


def build_event_batch(events: list[InterfaceEvent], limit: int = 100) -> InterfaceEventBatch:
    bounded = events[:limit]
    warnings: list[str] = []
    if len(events) > limit:
        warnings.append(f"Truncated {len(events)} events to limit {limit}")
    bid = f"batch_{hashlib.sha256(_iso_now().encode()).hexdigest()[:10]}"
    return InterfaceEventBatch(
        batch_id=bid,
        events=[e.to_dict() for e in bounded],
        total=len(bounded),
        warnings=warnings,
    )
