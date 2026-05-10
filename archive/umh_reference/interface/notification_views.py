"""Phase 84 notification views — display-only notification records.

No sending through external channels. No cron/schedule implementation.
Heartbeat is a notification type only, not runtime behavior.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.core.clock import iso_now as _iso_now


class NotificationType(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    APPROVAL_REQUIRED = "approval_required"
    EXECUTION_COMPLETE = "execution_complete"
    EXECUTION_FAILED = "execution_failed"
    MEMORY_REVIEW = "memory_review"
    STORAGE_WARNING = "storage_warning"
    MIGRATION_WARNING = "migration_warning"
    SYSTEM_HEALTH = "system_health"
    HEARTBEAT = "heartbeat"
    REMINDER = "reminder"
    UNKNOWN = "unknown"


class NotificationPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    UNKNOWN = "unknown"


class NotificationChannel(str, Enum):
    COMMAND_CENTER = "command_center"
    DESKTOP_OVERLAY = "desktop_overlay"
    MOBILE_PUSH = "mobile_push"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    EMAIL = "email"
    CLI = "cli"
    API = "api"
    UNKNOWN = "unknown"


class NotificationStatus(str, Enum):
    CREATED = "created"
    DISPLAYED = "displayed"
    ACKED = "acked"
    DISMISSED = "dismissed"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


def normalize_notification_type(value: str) -> NotificationType:
    try:
        return NotificationType(value.lower().strip())
    except (ValueError, AttributeError):
        return NotificationType.UNKNOWN


def normalize_notification_priority(value: str) -> NotificationPriority:
    try:
        return NotificationPriority(value.lower().strip())
    except (ValueError, AttributeError):
        return NotificationPriority.UNKNOWN


def normalize_notification_channel(value: str) -> NotificationChannel:
    try:
        return NotificationChannel(value.lower().strip())
    except (ValueError, AttributeError):
        return NotificationChannel.UNKNOWN


def normalize_notification_status(value: str) -> NotificationStatus:
    try:
        return NotificationStatus(value.lower().strip())
    except (ValueError, AttributeError):
        return NotificationStatus.UNKNOWN


@dataclass
class InterfaceNotification:
    notification_id: str
    notification_type: NotificationType = NotificationType.UNKNOWN
    priority: NotificationPriority = NotificationPriority.NORMAL
    title: str = ""
    message: str = ""
    channel: NotificationChannel = NotificationChannel.UNKNOWN
    surface_id: str | None = None
    user_id: str | None = None
    related_trace_id: str | None = None
    related_approval_id: str | None = None
    related_memory_candidate_id: str | None = None
    status: NotificationStatus = NotificationStatus.CREATED
    created_at: str | None = None
    expires_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "notification_id": self.notification_id,
            "notification_type": self.notification_type.value
            if isinstance(self.notification_type, Enum)
            else self.notification_type,
            "priority": self.priority.value if isinstance(self.priority, Enum) else self.priority,
            "title": self.title,
            "message": self.message,
            "channel": self.channel.value if isinstance(self.channel, Enum) else self.channel,
            "surface_id": self.surface_id,
            "user_id": self.user_id,
            "related_trace_id": self.related_trace_id,
            "related_approval_id": self.related_approval_id,
            "related_memory_candidate_id": self.related_memory_candidate_id,
            "status": self.status.value if isinstance(self.status, Enum) else self.status,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "metadata": self.metadata,
        }


@dataclass
class NotificationAck:
    ack_id: str
    notification_id: str = ""
    surface_id: str = ""
    user_id: str | None = None
    timestamp: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ack_id": self.ack_id,
            "notification_id": self.notification_id,
            "surface_id": self.surface_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


def create_notification(
    notification_type: NotificationType = NotificationType.INFO,
    *,
    title: str = "",
    message: str = "",
    priority: NotificationPriority = NotificationPriority.NORMAL,
    channel: NotificationChannel = NotificationChannel.UNKNOWN,
    surface_id: str | None = None,
    user_id: str | None = None,
    related_trace_id: str | None = None,
    related_approval_id: str | None = None,
    related_memory_candidate_id: str | None = None,
    expires_at: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> InterfaceNotification:
    nid = (
        f"ntf_{hashlib.sha256(f'{notification_type.value}{_iso_now()}'.encode()).hexdigest()[:10]}"
    )
    return InterfaceNotification(
        notification_id=nid,
        notification_type=notification_type,
        priority=priority,
        title=title,
        message=message,
        channel=channel,
        surface_id=surface_id,
        user_id=user_id,
        related_trace_id=related_trace_id,
        related_approval_id=related_approval_id,
        related_memory_candidate_id=related_memory_candidate_id,
        status=NotificationStatus.CREATED,
        created_at=_iso_now(),
        expires_at=expires_at,
        metadata=metadata or {},
    )
