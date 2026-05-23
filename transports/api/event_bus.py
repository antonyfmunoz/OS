"""Event bus — pub/sub backbone for the substrate's internal communication."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Event(BaseModel):
    """A typed event on the bus."""

    id: UUID = Field(default_factory=uuid4)
    event_type: str = Field(max_length=120)
    source: str = Field(max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: UUID | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """Async pub/sub event bus for decoupled communication between substrate components."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._history: list[Event] = []
        self._max_history: int = 1000

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    async def publish(self, event: Event) -> None:
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

        handlers = self._handlers.get(event.event_type, [])
        if not handlers:
            logger.debug(f"No handlers for event type: {event.event_type}")
            return

        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Event handler error for {event.event_type}: {e}")

    async def publish_and_wait(self, event: Event) -> None:
        """Publish and wait for all handlers to complete."""
        await self.publish(event)

    def recent_events(self, event_type: str | None = None, limit: int = 50) -> list[Event]:
        if event_type:
            return [e for e in self._history if e.event_type == event_type][-limit:]
        return self._history[-limit:]

    def clear_history(self) -> None:
        self._history.clear()
