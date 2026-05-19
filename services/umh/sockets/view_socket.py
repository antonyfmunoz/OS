"""View socket — broadcast pipeline state frames to observers."""

from __future__ import annotations

import logging

from services.umh.sockets.envelopes import ViewFrame
from services.umh.sockets.protocols import ViewSubscriber

logger = logging.getLogger(__name__)


class ViewSocket:
    """Broadcasts pipeline state frames to all subscribers.

    Registered as an on_event() listener on ExecutionPipeline.
    Every _emit() call produces a ViewFrame broadcast to all
    subscribers. The cockpit's WebSocketBridge is the primary
    subscriber (Phase 2).
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, ViewSubscriber] = {}

    def subscribe(self, subscriber: ViewSubscriber) -> None:
        """Add a subscriber to the broadcast list.

        Raises ValueError if subscriber_id is already registered.
        """
        sid = subscriber.subscriber_id
        if sid in self._subscribers:
            raise ValueError(f"subscriber '{sid}' already registered")
        self._subscribers[sid] = subscriber
        logger.info("view subscriber registered: %s", sid)

    def unsubscribe(self, subscriber_id: str) -> None:
        """Remove a subscriber from the broadcast list."""
        if subscriber_id in self._subscribers:
            del self._subscribers[subscriber_id]
            logger.info("view subscriber removed: %s", subscriber_id)

    def broadcast(self, frame: ViewFrame) -> None:
        """Send a frame to all subscribers whose filter matches."""
        for subscriber in self._subscribers.values():
            accepted = subscriber.accepts_events()
            if accepted and frame.event_type not in accepted:
                continue
            try:
                subscriber.on_frame(frame)
            except Exception as exc:
                logger.error(
                    "view subscriber '%s' raised %s: %s",
                    subscriber.subscriber_id,
                    type(exc).__name__,
                    exc,
                )

    def subscriber_count(self) -> int:
        return len(self._subscribers)

    def active_subscribers(self) -> list[str]:
        return list(self._subscribers.keys())
