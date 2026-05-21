"""UMH Event Stream — structured event emission for all core state transitions.

Provides an append-only, in-memory event log with synchronous publish/subscribe.
Every execution, approval, and identity action produces a typed event that can
be queried historically or streamed in real time via SSE.

Usage:
    from umh.events.stream import get_event_stream, publish

    stream = get_event_stream()
    stream.publish(Event(type="execution.started", payload={...}))

    # Or use the module-level shortcut:
    publish("execution.started", payload={...}, actor_id="id_abc123")
"""

from __future__ import annotations

import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Callable

from umh.core.clock import iso_now as _iso_now


@dataclass(frozen=True)
class Event:
    id: str
    type: str
    timestamp: str
    payload: dict
    actor_id: str = ""
    execution_id: str = ""
    approval_id: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "actor_id": self.actor_id,
            "execution_id": self.execution_id,
            "approval_id": self.approval_id,
        }


Callback = Callable[[Event], None]

_MAX_EVENTS = 10_000


class EventStream:
    """Thread-safe, append-only event stream with pub/sub."""

    def __init__(self, max_events: int = _MAX_EVENTS) -> None:
        self._events: deque[Event] = deque(maxlen=max_events)
        self._subscribers: list[Callback] = []
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)

    def publish(self, event: Event) -> None:
        with self._condition:
            self._events.append(event)
            subscribers = list(self._subscribers)
            self._condition.notify_all()
        for cb in subscribers:
            try:
                cb(event)
            except Exception:
                pass

    def subscribe(self, callback: Callback) -> None:
        with self._lock:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callback) -> None:
        with self._lock:
            try:
                self._subscribers.remove(callback)
            except ValueError:
                pass

    def list_events(self, limit: int = 100) -> list[Event]:
        with self._lock:
            events = list(self._events)
        return events[-limit:]

    def wait_for_event(self, timeout: float = 5.0) -> Event | None:
        """Block until a new event is published or timeout. For SSE."""
        with self._condition:
            count_before = len(self._events)
            self._condition.wait(timeout=timeout)
            if len(self._events) > count_before:
                return self._events[-1]
            return None

    def count(self) -> int:
        with self._lock:
            return len(self._events)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            self._subscribers.clear()


_stream: EventStream | None = None
_stream_lock = threading.Lock()


def get_event_stream() -> EventStream:
    global _stream
    if _stream is None:
        with _stream_lock:
            if _stream is None:
                _stream = EventStream()
    return _stream


def reset_event_stream() -> EventStream:
    global _stream
    with _stream_lock:
        _stream = EventStream()
    return _stream


def publish(
    event_type: str,
    payload: dict | None = None,
    *,
    actor_id: str = "",
    execution_id: str = "",
    approval_id: str = "",
) -> Event:
    """Module-level publish shortcut. Creates Event and publishes."""
    event = Event(
        id=f"evt_{uuid.uuid4().hex[:12]}",
        type=event_type,
        timestamp=_iso_now(),
        payload=payload or {},
        actor_id=actor_id,
        execution_id=execution_id,
        approval_id=approval_id,
    )
    get_event_stream().publish(event)
    return event
