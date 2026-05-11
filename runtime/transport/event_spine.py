"""
Event Spine — unified structured event model for EOS substrate.

Every significant action in the substrate layer emits an Event through
this model.  Events carry a ``correlation_id`` that threads an entire
workflow (Discord prompt → pipeline → steps → relay → delivery) into
one traceable chain.

Design rules:
- Immutable after creation (status is the only mutable field).
- UUID-based identifiers — no collisions across sessions.
- Serializable to JSON for the append-only event store.
- No DB dependency — works with JSONL flat files.
- No LLM calls — pure data model.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ─── Event Types ────────────────────────────────────────────────────────────


class EventType(str, Enum):
    """Canonical event types emitted across the substrate."""

    PROMPT_RECEIVED = "prompt_received"
    PIPELINE_CREATED = "pipeline_created"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    REPLY_COMPLETE = "reply_complete"
    REPLY_CHUNK = "reply_chunk"
    RELAY_SENT = "relay_sent"
    RELAY_FAILED = "relay_failed"
    DELIVERY_COMPLETE = "delivery_complete"
    PERMISSION_AUTO_APPROVED = "permission_auto_approved"
    PERMISSION_SURFACED = "permission_surfaced"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_DENIED = "permission_denied"
    # Node lifecycle events
    NODE_REGISTERED = "node_registered"
    NODE_RECONNECTED = "node_reconnected"
    NODE_DEGRADED = "node_degraded"
    # Action lifecycle events
    ACTION_DISPATCHED = "action_dispatched"
    ACTION_ACKNOWLEDGED = "action_acknowledged"
    ACTION_COMPLETED = "action_completed"
    ACTION_EXPIRED = "action_expired"
    ACTION_FAILED = "action_failed"
    # Inbound message framing events
    INBOUND_RECEIVED = "inbound_received"
    INBOUND_FINALIZED = "inbound_finalized"
    # Execution fabric lifecycle
    EXECUTION_REQUESTED = "execution_requested"
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    EXECUTION_TIMED_OUT = "execution_timed_out"
    EXECUTION_REJECTED = "execution_rejected"
    EXECUTION_RETRIED = "execution_retried"


class EventStatus(str, Enum):
    """Lifecycle of a single event."""

    CREATED = "created"
    PROCESSING = "processing"
    SENT = "sent"
    COMPLETED = "completed"
    FAILED = "failed"


# ─── Event ──────────────────────────────────────────────────────────────────


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _new_event_id() -> str:
    return uuid.uuid4().hex


def _content_hash(text: str) -> str:
    """Short SHA-256 digest for dedup and tracing."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


@dataclass
class Event:
    """Unified event for the EOS substrate event spine.

    Attributes:
        event_id: Globally unique identifier.
        parent_event_id: ID of the parent event (for chunk→reply linkage).
        correlation_id: Workflow-level ID threading all related events.
        source: Originating subsystem (discord, tmux_session, pipeline, etc).
        source_session: Specific session name (dex_product, dex_builder, etc).
        target: Destination subsystem (discord, local_node, vps, etc).
        event_type: Canonical event type.
        payload: Arbitrary structured data.
        status: Current lifecycle status.
        created_at: ISO timestamp of creation.
        updated_at: ISO timestamp of last status change.
    """

    event_id: str = field(default_factory=_new_event_id)
    parent_event_id: Optional[str] = None
    correlation_id: str = field(default_factory=_new_event_id)
    source: str = ""
    source_session: str = ""
    target: str = ""
    role: str = ""  # operating context: ea_product, builder, etc.
    event_type: EventType = EventType.PROMPT_RECEIVED
    payload: dict[str, Any] = field(default_factory=dict)
    status: EventStatus = EventStatus.CREATED
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def update_status(self, new_status: EventStatus) -> None:
        """Transition status and update timestamp."""
        self.status = new_status
        self.updated_at = _now_iso()

    def serialize(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        return {
            "event_id": self.event_id,
            "parent_event_id": self.parent_event_id,
            "correlation_id": self.correlation_id,
            "source": self.source,
            "source_session": self.source_session,
            "target": self.target,
            "role": self.role,
            "event_type": self.event_type.value,
            "payload": self.payload,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> "Event":
        """Reconstruct an Event from a serialized dict."""
        return cls(
            event_id=data.get("event_id", _new_event_id()),
            parent_event_id=data.get("parent_event_id"),
            correlation_id=data.get("correlation_id", _new_event_id()),
            source=data.get("source", ""),
            source_session=data.get("source_session", ""),
            target=data.get("target", ""),
            role=data.get("role", ""),
            event_type=EventType(data["event_type"]),
            payload=data.get("payload", {}),
            status=EventStatus(data.get("status", "created")),
            created_at=data.get("created_at", _now_iso()),
            updated_at=data.get("updated_at", _now_iso()),
        )


# ─── Factory helpers ────────────────────────────────────────────────────────


def create_event(
    event_type: EventType,
    *,
    source: str = "",
    source_session: str = "",
    target: str = "",
    role: str = "",
    payload: Optional[dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
    parent_event_id: Optional[str] = None,
) -> Event:
    """Create a new Event with a fresh event_id.

    If correlation_id is not provided, a new one is generated.
    """
    return Event(
        event_id=_new_event_id(),
        parent_event_id=parent_event_id,
        correlation_id=correlation_id or _new_event_id(),
        source=source,
        source_session=source_session,
        target=target,
        role=role,
        event_type=event_type,
        payload=payload or {},
        status=EventStatus.CREATED,
    )


# ─── Exports ────────────────────────────────────────────────────────────────

__all__ = [
    "EventType",
    "EventStatus",
    "Event",
    "create_event",
]
