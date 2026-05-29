"""
Notification socket — substrate-layer abstraction for outbound notifications.

Transport implementations (Discord, Telegram, etc.) register their concrete
functions at startup. Substrate code calls these thin wrappers, never importing
from transports directly.

Three notification types:
  1. Webhook — post to a webhook URL (Discord webhook, Slack, etc.)
  2. Chat push — push a message to all connected cockpit WS clients
  3. Approval alert — notify all channels about a new governance approval
"""

from __future__ import annotations

from typing import Any, Callable, Optional

_notify_fn: Optional[Callable] = None
_chunk_fn: Optional[Callable] = None
_chat_push_fn: Optional[Callable[..., None]] = None
_approval_alert_fn: Optional[Callable[..., None]] = None


def register_notifier(fn: Callable) -> None:
    """Register the concrete webhook-posting function (e.g. post_to_webhook)."""
    global _notify_fn
    _notify_fn = fn


def register_chunker(fn: Callable) -> None:
    """Register the concrete message-chunking function (e.g. chunk_message)."""
    global _chunk_fn
    _chunk_fn = fn


def register_chat_push(fn: Callable[..., None]) -> None:
    """Register a function that pushes a chat message to cockpit WS clients."""
    global _chat_push_fn
    _chat_push_fn = fn


def register_approval_alert(fn: Callable[..., None]) -> None:
    """Register a function that sends approval notifications to all channels."""
    global _approval_alert_fn
    _approval_alert_fn = fn



def notify_webhook(
    content: str,
    title: str = '',
    username: str = '',
    webhook_url: str = '',
    **kwargs: Any,
) -> bool:
    """Post content to a webhook via the registered notifier.

    Returns False silently when no notifier is registered (headless mode).
    """
    if _notify_fn:
        return _notify_fn(content, title=title, username=username, webhook_url=webhook_url, **kwargs)
    return False


def push_chat(message: dict[str, Any]) -> None:
    """Push a chat message to connected cockpit WS clients.

    No-op when no chat push function is registered (headless mode).
    """
    if _chat_push_fn:
        _chat_push_fn(message)


def alert_approval(approval: dict[str, Any]) -> None:
    """Notify all channels about a new governance approval request.

    No-op when no approval alert function is registered (headless mode).
    """
    if _approval_alert_fn:
        _approval_alert_fn(approval)


def chunk_content(content: str, title: str = '') -> list[str]:
    """Chunk content via the registered chunker.

    Falls back to returning the raw content as a single-element list
    when no chunker is registered.
    """
    if _chunk_fn:
        return _chunk_fn(content, title)
    return [content]
