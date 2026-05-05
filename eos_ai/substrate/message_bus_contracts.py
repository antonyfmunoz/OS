"""
Message bus contracts for Phase 94D.3.

Additive-only module. Defines the interface-agnostic message envelope,
message types, source interfaces, and serialization helpers.

Does not import from or modify any existing substrate module.
Does not implement transport, routing, or persistence — only contracts.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class MessageType(str, Enum):
    # Founder-originated
    INTENT = "INTENT"
    COMMAND = "COMMAND"
    APPROVAL_RESPONSE = "APPROVAL_RESPONSE"
    CLARIFICATION_RESPONSE = "CLARIFICATION_RESPONSE"
    STOP = "STOP"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    MODIFY_CONSTRAINTS = "MODIFY_CONSTRAINTS"
    SWITCH_INTERFACE = "SWITCH_INTERFACE"

    # Advisor-originated
    ADVISORY = "ADVISORY"
    PLAN = "PLAN"
    QUESTION = "QUESTION"
    APPROVAL_REQUEST = "APPROVAL_REQUEST"
    STATUS_SUMMARY = "STATUS_SUMMARY"
    RISK_WARNING = "RISK_WARNING"
    RECOMMENDED_ACTION = "RECOMMENDED_ACTION"
    MEMORY_CANDIDATE_REVIEW = "MEMORY_CANDIDATE_REVIEW"

    # Node-originated
    NODE_HEALTH = "NODE_HEALTH"
    WORK_ORDER_CLAIMED = "WORK_ORDER_CLAIMED"
    WORK_ORDER_STATUS = "WORK_ORDER_STATUS"
    APPROVAL_NEEDED = "APPROVAL_NEEDED"
    ERROR = "ERROR"
    BLOCKED = "BLOCKED"
    RESULT = "RESULT"
    EVIDENCE_AVAILABLE = "EVIDENCE_AVAILABLE"
    COMPLETION_REPORT = "COMPLETION_REPORT"

    # System-originated
    AUDIT_EVENT = "AUDIT_EVENT"
    POLICY_BLOCK = "POLICY_BLOCK"
    GOVERNANCE_WARNING = "GOVERNANCE_WARNING"
    ROUTING_DECISION = "ROUTING_DECISION"
    HEARTBEAT = "HEARTBEAT"


FOUNDER_MESSAGE_TYPES: frozenset[MessageType] = frozenset(
    {
        MessageType.INTENT,
        MessageType.COMMAND,
        MessageType.APPROVAL_RESPONSE,
        MessageType.CLARIFICATION_RESPONSE,
        MessageType.STOP,
        MessageType.PAUSE,
        MessageType.RESUME,
        MessageType.MODIFY_CONSTRAINTS,
        MessageType.SWITCH_INTERFACE,
    }
)

ADVISOR_MESSAGE_TYPES: frozenset[MessageType] = frozenset(
    {
        MessageType.ADVISORY,
        MessageType.PLAN,
        MessageType.QUESTION,
        MessageType.APPROVAL_REQUEST,
        MessageType.STATUS_SUMMARY,
        MessageType.RISK_WARNING,
        MessageType.RECOMMENDED_ACTION,
        MessageType.MEMORY_CANDIDATE_REVIEW,
    }
)

NODE_MESSAGE_TYPES: frozenset[MessageType] = frozenset(
    {
        MessageType.NODE_HEALTH,
        MessageType.WORK_ORDER_CLAIMED,
        MessageType.WORK_ORDER_STATUS,
        MessageType.APPROVAL_NEEDED,
        MessageType.ERROR,
        MessageType.BLOCKED,
        MessageType.RESULT,
        MessageType.EVIDENCE_AVAILABLE,
        MessageType.COMPLETION_REPORT,
    }
)

SYSTEM_MESSAGE_TYPES: frozenset[MessageType] = frozenset(
    {
        MessageType.AUDIT_EVENT,
        MessageType.POLICY_BLOCK,
        MessageType.GOVERNANCE_WARNING,
        MessageType.ROUTING_DECISION,
        MessageType.HEARTBEAT,
    }
)


class SourceInterface(str, Enum):
    CLI = "cli"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    MOBILE_APP = "mobile_app"
    WORKSTATION_UI = "workstation_ui"
    VOICE = "voice"
    BROWSER_OVERLAY = "browser_overlay"
    WEB_DASHBOARD = "web_dashboard"
    NODE = "node"
    SYSTEM = "system"


class MessagePriority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class MessageStatus(str, Enum):
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


def _new_message_id() -> str:
    return f"msg_{uuid.uuid4().hex[:12]}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class MessageEnvelope:
    message_type: MessageType
    sender: str
    recipient: str
    payload: dict[str, Any]
    target: str = "advisor"
    source_interface: str = "system"
    message_id: str = field(default_factory=_new_message_id)
    session_id: str = ""
    conversation_id: str | None = None
    priority: MessagePriority = MessagePriority.NORMAL
    requires_response: bool = False
    approval_required: bool = False
    timestamp: str = field(default_factory=_now_iso)
    correlation_id: str | None = None
    parent_message_id: str | None = None
    work_order_id: str | None = None
    node_id: str | None = None
    status: MessageStatus = MessageStatus.PENDING
    audit_tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["message_type"] = self.message_type.value
        d["priority"] = self.priority.value
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MessageEnvelope:
        return cls(
            message_id=data.get("message_id", _new_message_id()),
            session_id=data.get("session_id", ""),
            conversation_id=data.get("conversation_id"),
            source_interface=data.get("source_interface", "system"),
            target=data.get("target", "advisor"),
            sender=data["sender"],
            recipient=data["recipient"],
            message_type=MessageType(data["message_type"]),
            payload=data.get("payload", {}),
            priority=MessagePriority(data.get("priority", "NORMAL")),
            requires_response=data.get("requires_response", False),
            approval_required=data.get("approval_required", False),
            timestamp=data.get("timestamp", _now_iso()),
            correlation_id=data.get("correlation_id"),
            parent_message_id=data.get("parent_message_id"),
            work_order_id=data.get("work_order_id"),
            node_id=data.get("node_id"),
            status=MessageStatus(data.get("status", "PENDING")),
            audit_tags=data.get("audit_tags", []),
        )

    def is_approval_flow(self) -> bool:
        return self.message_type in (
            MessageType.APPROVAL_NEEDED,
            MessageType.APPROVAL_REQUEST,
            MessageType.APPROVAL_RESPONSE,
        )

    def is_control_flow(self) -> bool:
        return self.message_type in (
            MessageType.STOP,
            MessageType.PAUSE,
            MessageType.RESUME,
        )
