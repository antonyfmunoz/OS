"""Unified organism event spine — canonical organism-level event transport.

This is NOT a replacement for lower-layer event systems (ControlPlane
EventBus, execution bridge EventSpine, ViewFrame/ViewSocket). Those
serve their own layers. This spine is the organism-level transport
that connects existing subsystems (Advisor, Coordinator, RuntimeGraph,
RuntimeSupervisor, HomeostasisEngine, etc.) into a coherent observable
flow.

The existing Advisor._emit_event() already broadcasts ViewFrames to
cockpit observers. This spine sits alongside that — subsystems emit
organism events here, and projection consumers (cockpit, EOS, etc.)
subscribe to receive them.

Design:
  - In-memory, append-only, bounded deque
  - Thread-safe (organism stages may run in PersistentLoop threads)
  - Subscriber error isolation
  - Domain-filtered subscriptions
  - Replay support for late-joining observers
  - Correlation ID threads related events across subsystems

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)


class EventDomain(str, Enum):
    RUNTIME = "runtime"
    GOVERNANCE = "governance"
    ADVISOR = "advisor"
    WORKCELL = "workcell"
    OBJECTIVE = "objective"
    EXECUTION = "execution"
    LEVERAGE = "leverage"
    SUPERVISOR = "supervisor"
    FILESYSTEM = "filesystem"
    TMUX = "tmux"
    DOCKER = "docker"
    PROJECTION = "projection"
    TRANSPORT = "transport"
    RECURSION = "recursion"
    MEMORY = "memory"
    OBSERVABILITY = "observability"


class EventPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class OrganismEvent:
    domain: EventDomain
    event_type: str
    source: str
    data: dict[str, Any]
    priority: EventPriority = EventPriority.NORMAL
    event_id: str = field(default_factory=lambda: uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    correlation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "domain": self.domain.value,
            "event_type": self.event_type,
            "source": self.source,
            "priority": self.priority.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
        }


EventHandler = Callable[[OrganismEvent], None]


@dataclass
class _Subscriber:
    subscriber_id: str
    handler: EventHandler
    domains: frozenset[EventDomain] | None


_MAX_JSONL_BYTES = 10 * 1024 * 1024  # 10 MB rotation threshold


class EventSpine:
    """Canonical organism event transport.

    Thread-safe, bounded, append-only event log with filtered pub/sub.
    Optionally persists events to JSONL for crash recovery.
    """

    def __init__(
        self,
        max_events: int = 10_000,
        persist_path: str | None = None,
    ) -> None:
        self._events: deque[OrganismEvent] = deque(maxlen=max_events)
        self._subscribers: dict[str, _Subscriber] = {}
        self._lock = threading.Lock()
        self._persist_path = Path(persist_path) if persist_path else None
        self._persist_file: Any = None
        if self._persist_path is not None:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)

    def emit(
        self,
        domain: EventDomain,
        event_type: str,
        source: str,
        data: dict[str, Any],
        priority: EventPriority = EventPriority.NORMAL,
        correlation_id: str | None = None,
    ) -> OrganismEvent:
        event = OrganismEvent(
            domain=domain,
            event_type=event_type,
            source=source,
            data=data,
            priority=priority,
            correlation_id=correlation_id,
        )
        with self._lock:
            self._events.append(event)
            subscribers = list(self._subscribers.values())

        self._persist_event(event)

        for sub in subscribers:
            if sub.domains is not None and domain not in sub.domains:
                continue
            try:
                sub.handler(event)
            except Exception as exc:
                logger.warning(
                    "event subscriber '%s' raised %s: %s",
                    sub.subscriber_id, type(exc).__name__, exc,
                )

        return event

    def subscribe(
        self,
        subscriber_id: str,
        handler: EventHandler,
        domains: set[EventDomain] | None = None,
    ) -> None:
        frozen = frozenset(domains) if domains is not None else None
        with self._lock:
            self._subscribers[subscriber_id] = _Subscriber(
                subscriber_id=subscriber_id,
                handler=handler,
                domains=frozen,
            )
        logger.debug("event subscriber registered: %s", subscriber_id)

    def unsubscribe(self, subscriber_id: str) -> None:
        with self._lock:
            self._subscribers.pop(subscriber_id, None)
        logger.debug("event subscriber removed: %s", subscriber_id)

    def recent(self, limit: int = 50) -> list[OrganismEvent]:
        with self._lock:
            events = list(self._events)
        return events[-limit:] if len(events) > limit else events

    def replay(
        self,
        domains: set[EventDomain] | None = None,
        since: float | None = None,
    ) -> list[OrganismEvent]:
        with self._lock:
            events = list(self._events)

        result = []
        for event in events:
            if since is not None and event.timestamp <= since:
                continue
            if domains is not None and event.domain not in domains:
                continue
            result.append(event)
        return result

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            events = list(self._events)

        by_domain: dict[str, int] = {}
        for event in events:
            domain_val = event.domain.value
            by_domain[domain_val] = by_domain.get(domain_val, 0) + 1

        return {
            "total_events": len(events),
            "events_by_domain": by_domain,
            "subscriber_count": len(self._subscribers),
            "subscribers": list(self._subscribers.keys()),
            "oldest_timestamp": events[0].timestamp if events else None,
            "newest_timestamp": events[-1].timestamp if events else None,
            "persist_path": str(self._persist_path) if self._persist_path else None,
        }

    def _persist_event(self, event: OrganismEvent) -> None:
        if self._persist_path is None:
            return
        try:
            self._rotate_if_needed()
            with open(self._persist_path, "a") as f:
                f.write(json.dumps(event.to_dict(), default=str) + "\n")
        except Exception as exc:
            logger.warning("event persist failed: %s", exc)

    def _rotate_if_needed(self) -> None:
        if self._persist_path is None or not self._persist_path.exists():
            return
        try:
            size = self._persist_path.stat().st_size
        except OSError:
            return
        if size < _MAX_JSONL_BYTES:
            return
        rotated = self._persist_path.with_suffix(".jsonl.old")
        try:
            if rotated.exists():
                rotated.unlink()
            self._persist_path.rename(rotated)
            logger.info("event spine rotated %s -> %s", self._persist_path, rotated)
        except OSError as exc:
            logger.warning("event rotation failed: %s", exc)

    def recover(self) -> int:
        """Recover events from JSONL persistence into memory.

        Returns the number of events recovered.
        """
        if self._persist_path is None or not self._persist_path.exists():
            return 0
        recovered = 0
        try:
            with open(self._persist_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        event = OrganismEvent(
                            domain=EventDomain(data["domain"]),
                            event_type=data["event_type"],
                            source=data["source"],
                            data=data.get("data", {}),
                            priority=EventPriority(data.get("priority", "normal")),
                            event_id=data.get("event_id", uuid4().hex[:12]),
                            timestamp=data.get("timestamp", 0.0),
                            correlation_id=data.get("correlation_id"),
                        )
                        with self._lock:
                            self._events.append(event)
                        recovered += 1
                    except (KeyError, ValueError) as exc:
                        logger.debug("skipping malformed event line: %s", exc)
        except Exception as exc:
            logger.warning("event recovery failed: %s", exc)
        if recovered > 0:
            logger.info("recovered %d events from %s", recovered, self._persist_path)
        return recovered

    def flush(self) -> None:
        """Ensure all buffered writes are flushed to disk."""
        pass
