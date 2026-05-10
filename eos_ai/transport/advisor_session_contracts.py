"""
Advisor session contracts for Phase 94D.3.

Additive-only module. Defines the state model and event types for the
central advisor session — the founder-facing command/intelligence layer.

Does not import from or modify any existing substrate module.
Does not implement session persistence, routing, or LLM calls — only contracts.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class AdvisorSessionState(str, Enum):
    ACTIVE = "ACTIVE"
    IDLE = "IDLE"
    SLEEPING = "SLEEPING"
    PAUSED = "PAUSED"


class AdvisorEventKind(str, Enum):
    SESSION_STARTED = "SESSION_STARTED"
    SESSION_RESUMED = "SESSION_RESUMED"
    INTERFACE_CONNECTED = "INTERFACE_CONNECTED"
    INTERFACE_DISCONNECTED = "INTERFACE_DISCONNECTED"
    WORK_ORDER_DISPATCHED = "WORK_ORDER_DISPATCHED"
    WORK_ORDER_CLAIMED = "WORK_ORDER_CLAIMED"
    WORK_ORDER_COMPLETED = "WORK_ORDER_COMPLETED"
    APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
    APPROVAL_RESOLVED = "APPROVAL_RESOLVED"
    FOUNDER_COMMAND = "FOUNDER_COMMAND"
    NODE_ERROR = "NODE_ERROR"
    SESSION_PAUSED = "SESSION_PAUSED"
    SESSION_STOPPED = "SESSION_STOPPED"


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AdvisorSessionEvent:
    kind: AdvisorEventKind
    detail: str
    event_id: str = field(default_factory=_new_id)
    session_id: str = ""
    work_order_id: str | None = None
    node_id: str | None = None
    interface_id: str | None = None
    timestamp: str = field(default_factory=_now_iso)
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "detail": self.detail,
            "session_id": self.session_id,
            "work_order_id": self.work_order_id,
            "node_id": self.node_id,
            "interface_id": self.interface_id,
            "timestamp": self.timestamp,
            "data": self.data,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AdvisorSessionEvent:
        return cls(
            event_id=data.get("event_id", _new_id()),
            kind=AdvisorEventKind(data["kind"]),
            detail=data["detail"],
            session_id=data.get("session_id", ""),
            work_order_id=data.get("work_order_id"),
            node_id=data.get("node_id"),
            interface_id=data.get("interface_id"),
            timestamp=data.get("timestamp", _now_iso()),
            data=data.get("data", {}),
        )


@dataclass
class AdvisorSessionCommand:
    """A command the advisor session can issue to a node or transport."""

    command_type: str
    target_node: str
    payload: dict[str, Any]
    command_id: str = field(default_factory=_new_id)
    work_order_id: str | None = None
    issued_at: str = field(default_factory=_now_iso)
    issued_by: str = "advisor"

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_id": self.command_id,
            "command_type": self.command_type,
            "target_node": self.target_node,
            "payload": self.payload,
            "work_order_id": self.work_order_id,
            "issued_at": self.issued_at,
            "issued_by": self.issued_by,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AdvisorSessionCommand:
        return cls(
            command_id=data.get("command_id", _new_id()),
            command_type=data["command_type"],
            target_node=data["target_node"],
            payload=data.get("payload", {}),
            work_order_id=data.get("work_order_id"),
            issued_at=data.get("issued_at", _now_iso()),
            issued_by=data.get("issued_by", "advisor"),
        )


@dataclass
class PendingApproval:
    """Tracks an approval request awaiting founder response."""

    approval_id: str
    work_order_id: str
    node_id: str
    action_description: str
    risk_level: str
    requested_at: str = field(default_factory=_now_iso)
    resolved: bool = False
    resolution: str | None = None
    resolved_at: str | None = None
    resolved_via_interface: str | None = None

    def resolve(self, decision: str, interface_id: str) -> None:
        self.resolved = True
        self.resolution = decision
        self.resolved_at = _now_iso()
        self.resolved_via_interface = interface_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "work_order_id": self.work_order_id,
            "node_id": self.node_id,
            "action_description": self.action_description,
            "risk_level": self.risk_level,
            "requested_at": self.requested_at,
            "resolved": self.resolved,
            "resolution": self.resolution,
            "resolved_at": self.resolved_at,
            "resolved_via_interface": self.resolved_via_interface,
        }
