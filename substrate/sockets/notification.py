"""
Notification socket — substrate-layer abstraction for outbound notifications.

Transport implementations (Discord, Telegram, etc.) register their concrete
functions at startup. Substrate code calls these thin wrappers, never importing
from transports directly.
"""

from typing import Callable, Optional

_notify_fn: Optional[Callable] = None
_chunk_fn: Optional[Callable] = None


def register_notifier(fn: Callable) -> None:
    """Register the concrete webhook-posting function (e.g. post_to_webhook)."""
    global _notify_fn
    _notify_fn = fn


def register_chunker(fn: Callable) -> None:
    """Register the concrete message-chunking function (e.g. chunk_message)."""
    global _chunk_fn
    _chunk_fn = fn


def notify_webhook(
    content: str,
    title: str = '',
    username: str = '',
    webhook_url: str = '',
    **kwargs,
) -> bool:
    """Post content to a webhook via the registered notifier.

    Returns False silently when no notifier is registered (headless mode).
    """
    if _notify_fn:
        return _notify_fn(content, title=title, username=username, webhook_url=webhook_url, **kwargs)
    return False


def chunk_content(content: str, title: str = '') -> list[str]:
    """Chunk content via the registered chunker.

    Falls back to returning the raw content as a single-element list
    when no chunker is registered.
    """
    if _chunk_fn:
        return _chunk_fn(content, title)
    return [content]
