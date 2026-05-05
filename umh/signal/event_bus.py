"""UMH EventBus — reactive coordination layer for agent systems.

Decouples event producers from consumers. Any component can publish a
typed event; registered handlers fire synchronously or in a background
thread.

Persistence is optional — inject an EventLogger to audit/replay events.
Without one, events are fire-and-forget.

Handler registration is supported individually via subscribe() or in
bulk via EventRegistry for wiring up default handler sets at startup.

Pure pattern. No database imports, no LLM calls.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------


@dataclass
class Event:
    """A typed event with payload."""

    event_type: str
    payload: dict[str, Any]
    timestamp: str = ""
    source: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class EventResult:
    """Result of publishing an event."""

    event_type: str
    handlers_called: int
    results: list[Any] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    logged: bool = False


# ---------------------------------------------------------------------------
# Logger protocol — optional persistence
# ---------------------------------------------------------------------------


@runtime_checkable
class EventLogger(Protocol):
    """Protocol for event persistence. Inject to enable audit/replay."""

    def log_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        handled_by: list[str],
    ) -> None: ...


class NullLogger:
    """No-op logger for when persistence is not needed."""

    def log_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        handled_by: list[str],
    ) -> None:
        pass


# ---------------------------------------------------------------------------
# EventBus
# ---------------------------------------------------------------------------

HandlerFn = Callable[[dict[str, Any]], Any]


class EventBus:
    """Pub/sub event bus with optional persistence and async dispatch.

    Thread-safe. Not a singleton — create one per scope.
    """

    def __init__(
        self,
        *,
        logger: EventLogger | None = None,
        allowed_types: frozenset[str] | None = None,
    ) -> None:
        self._handlers: dict[str, list[HandlerFn]] = {}
        self._logger: EventLogger = logger or NullLogger()
        self._allowed_types = allowed_types
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, handler: HandlerFn) -> None:
        """Register a handler for an event type."""
        if self._allowed_types and event_type not in self._allowed_types:
            raise ValueError(
                f"unknown event type {event_type!r} — "
                f"allowed: {sorted(self._allowed_types)}"
            )
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: HandlerFn) -> bool:
        """Remove a handler. Returns True if found and removed."""
        with self._lock:
            handlers = self._handlers.get(event_type, [])
            try:
                handlers.remove(handler)
                return True
            except ValueError:
                return False

    def publish(self, event_type: str, payload: dict[str, Any]) -> EventResult:
        """Fire all handlers synchronously. Returns results."""
        with self._lock:
            handlers = list(self._handlers.get(event_type, []))

        results: list[Any] = []
        errors: list[str] = []
        handled_by: list[str] = []

        for handler in handlers:
            name = getattr(handler, "__name__", repr(handler))
            try:
                result = handler(payload)
                results.append(result)
                handled_by.append(name)
            except Exception as exc:
                errors.append(f"{name}: {exc}")
                handled_by.append(f"{name}:ERROR")

        self._logger.log_event(event_type, payload, handled_by)

        return EventResult(
            event_type=event_type,
            handlers_called=len(handlers),
            results=results,
            errors=errors,
            logged=not isinstance(self._logger, NullLogger),
        )

    def publish_async(self, event_type: str, payload: dict[str, Any]) -> None:
        """Fire all handlers in a background daemon thread."""
        thread = threading.Thread(
            target=self.publish,
            args=(event_type, payload),
            daemon=True,
            name=f"eventbus-{event_type}",
        )
        thread.start()

    def handler_count(self, event_type: str) -> int:
        """Number of handlers registered for this event type."""
        with self._lock:
            return len(self._handlers.get(event_type, []))

    @property
    def registered_types(self) -> list[str]:
        """All event types that have at least one handler."""
        with self._lock:
            return sorted(k for k, v in self._handlers.items() if v)

    def clear(self) -> None:
        """Remove all handlers."""
        with self._lock:
            self._handlers.clear()


# ---------------------------------------------------------------------------
# EventRegistry — bulk handler wiring
# ---------------------------------------------------------------------------


class EventRegistry:
    """Registers a set of event_type → handler mappings onto a bus.

    Use at startup to wire default handler sets. Each handler is
    a Callable[[dict], Any] — the bus passes the event payload dict.
    """

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._mappings: list[tuple[str, HandlerFn]] = []

    def add(self, event_type: str, handler: HandlerFn) -> "EventRegistry":
        """Add a mapping. Returns self for chaining."""
        self._mappings.append((event_type, handler))
        return self

    def register_all(self) -> int:
        """Subscribe all accumulated mappings. Returns count registered."""
        for event_type, handler in self._mappings:
            self._bus.subscribe(event_type, handler)
        return len(self._mappings)

    @property
    def pending(self) -> int:
        return len(self._mappings)


__all__ = [
    "Event",
    "EventBus",
    "EventLogger",
    "EventRegistry",
    "EventResult",
    "HandlerFn",
    "NullLogger",
]
