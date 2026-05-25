"""Multi-channel notification engine — substrate-layer abstraction.

Channels register at startup. Substrate code calls send() with a channel
preference list; the engine tries each in order until one succeeds.
Falls back gracefully — never blocks on notification failure.

Channels: discord (webhook), email, sms, push, cockpit (WebSocket).
Transports register concrete implementations via register_channel().
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    DISCORD = "discord"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    COCKPIT = "cockpit"


class NotificationPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Notification:
    title: str
    body: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    channel_preference: list[NotificationChannel] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    target_user: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class NotificationResult:
    sent: bool
    channel: NotificationChannel | None = None
    error: str = ""
    attempts: list[str] = field(default_factory=list)


# Channel handler type: (title, body, metadata) -> bool
ChannelHandler = Callable[..., bool]
AsyncChannelHandler = Callable[..., Awaitable[bool]]


class NotificationEngine:
    """Multi-channel notification dispatcher.

    Register channel handlers at startup. Call send() from anywhere in substrate.
    The engine tries channels in preference order, falling back on failure.
    """

    def __init__(self) -> None:
        self._channels: dict[NotificationChannel, ChannelHandler] = {}
        self._async_channels: dict[NotificationChannel, AsyncChannelHandler] = {}
        self._history: list[dict[str, Any]] = []
        self._max_history = 500

    def register_channel(
        self,
        channel: NotificationChannel,
        handler: ChannelHandler,
    ) -> None:
        self._channels[channel] = handler
        logger.debug("Notification channel registered: %s", channel.value)

    def register_async_channel(
        self,
        channel: NotificationChannel,
        handler: AsyncChannelHandler,
    ) -> None:
        self._async_channels[channel] = handler
        logger.debug("Async notification channel registered: %s", channel.value)

    @property
    def available_channels(self) -> list[str]:
        sync = set(self._channels.keys())
        async_ = set(self._async_channels.keys())
        return sorted(c.value for c in sync | async_)

    def send(self, notification: Notification) -> NotificationResult:
        """Send a notification through preferred channels (sync path)."""
        channels = notification.channel_preference or self._default_channels(notification.priority)
        attempts: list[str] = []

        for channel in channels:
            handler = self._channels.get(channel)
            if not handler:
                attempts.append(f"{channel.value}: no handler registered")
                continue
            try:
                success = handler(
                    title=notification.title,
                    body=notification.body,
                    priority=notification.priority.value,
                    metadata=notification.metadata,
                    source=notification.source,
                    target_user=notification.target_user,
                )
                attempts.append(
                    f"{channel.value}: {'sent' if success else 'handler returned false'}"
                )
                if success:
                    self._record(notification, channel, True)
                    return NotificationResult(sent=True, channel=channel, attempts=attempts)
            except Exception as e:
                attempts.append(f"{channel.value}: {e}")
                logger.warning("Notification via %s failed: %s", channel.value, e)

        self._record(notification, None, False)
        return NotificationResult(sent=False, error="all channels failed", attempts=attempts)

    async def send_async(self, notification: Notification) -> NotificationResult:
        """Send a notification through preferred channels (async path)."""
        channels = notification.channel_preference or self._default_channels(notification.priority)
        attempts: list[str] = []

        for channel in channels:
            handler = self._async_channels.get(channel) or self._channels.get(channel)
            if not handler:
                attempts.append(f"{channel.value}: no handler registered")
                continue
            try:
                import asyncio

                if asyncio.iscoroutinefunction(handler):
                    success = await handler(
                        title=notification.title,
                        body=notification.body,
                        priority=notification.priority.value,
                        metadata=notification.metadata,
                        source=notification.source,
                        target_user=notification.target_user,
                    )
                else:
                    success = handler(
                        title=notification.title,
                        body=notification.body,
                        priority=notification.priority.value,
                        metadata=notification.metadata,
                        source=notification.source,
                        target_user=notification.target_user,
                    )
                attempts.append(
                    f"{channel.value}: {'sent' if success else 'handler returned false'}"
                )
                if success:
                    self._record(notification, channel, True)
                    return NotificationResult(sent=True, channel=channel, attempts=attempts)
            except Exception as e:
                attempts.append(f"{channel.value}: {e}")
                logger.warning("Notification via %s failed: %s", channel.value, e)

        self._record(notification, None, False)
        return NotificationResult(sent=False, error="all channels failed", attempts=attempts)

    def _default_channels(self, priority: NotificationPriority) -> list[NotificationChannel]:
        """Priority-based channel ordering."""
        if priority == NotificationPriority.CRITICAL:
            return [
                NotificationChannel.COCKPIT,
                NotificationChannel.PUSH,
                NotificationChannel.SMS,
                NotificationChannel.DISCORD,
                NotificationChannel.EMAIL,
            ]
        if priority == NotificationPriority.HIGH:
            return [
                NotificationChannel.COCKPIT,
                NotificationChannel.DISCORD,
                NotificationChannel.PUSH,
                NotificationChannel.EMAIL,
            ]
        if priority == NotificationPriority.NORMAL:
            return [
                NotificationChannel.COCKPIT,
                NotificationChannel.DISCORD,
                NotificationChannel.EMAIL,
            ]
        return [NotificationChannel.COCKPIT, NotificationChannel.DISCORD]

    def _record(
        self,
        notification: Notification,
        channel: NotificationChannel | None,
        sent: bool,
    ) -> None:
        self._history.append(
            {
                "title": notification.title,
                "priority": notification.priority.value,
                "channel": channel.value if channel else None,
                "sent": sent,
                "source": notification.source,
                "timestamp": notification.created_at,
            }
        )
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

    def recent_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return list(reversed(self._history[-limit:]))

    @property
    def stats(self) -> dict[str, Any]:
        total = len(self._history)
        sent = sum(1 for h in self._history if h["sent"])
        by_channel: dict[str, int] = {}
        for h in self._history:
            ch = h.get("channel") or "failed"
            by_channel[ch] = by_channel.get(ch, 0) + 1
        return {
            "total": total,
            "sent": sent,
            "failed": total - sent,
            "by_channel": by_channel,
        }


# ── Module-level singleton ───────────────────────────────────────────────────

_engine: NotificationEngine | None = None


def get_notification_engine() -> NotificationEngine:
    global _engine
    if _engine is None:
        _engine = NotificationEngine()
    return _engine
