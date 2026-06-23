"""Execution Telemetry — live event pipeline for executor lifecycle.

Provides real-time observability into executor operations as they progress
through validate → prepare → execute → cleanup.

Components:
  - TelemetryEventType: canonical event types (14 lifecycle + command events)
  - ExecutionTelemetryEvent: immutable event record with sequence numbering
  - ExecutionTelemetryEmitter: singleton emitter with subscribe/emit/query
  - InMemoryExecutionTelemetryStore: bounded in-memory event store
  - redact_telemetry_payload(): strips secrets from payloads

Design constraints:
  - Telemetry NEVER blocks execution — all emit() calls are try/except guarded
  - In-memory only for this phase (no Redis, no Kafka, no DB)
  - Bounded store (max 10,000 events, oldest evicted)
  - Secret-aware redaction on all payloads
  - Thread-safe via threading.Lock

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Telemetry Event Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TelemetryEventType(str, Enum):
    """Canonical telemetry event types for executor lifecycle."""

    EXECUTION_REQUESTED = "execution_requested"
    EXECUTION_VALIDATING = "execution_validating"
    EXECUTION_APPROVED = "execution_approved"
    EXECUTION_PREPARING = "execution_preparing"
    EXECUTION_STARTED = "execution_started"
    COMMAND_STARTED = "command_started"
    STDOUT_CHUNK = "stdout_chunk"
    STDERR_CHUNK = "stderr_chunk"
    COMMAND_COMPLETED = "command_completed"
    PROOF_GENERATED = "proof_generated"
    EXECUTION_CLEANING_UP = "execution_cleaning_up"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    EXECUTION_CANCELLED = "execution_cancelled"
    # Phase 15C: Approval Intercepts
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_VIEWED = "approval_viewed"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_REJECTED = "approval_rejected"
    APPROVAL_EXPIRED = "approval_expired"
    EXECUTION_PAUSED = "execution_paused"
    EXECUTION_RESUMED = "execution_resumed"
    # C26B: Deploy Verification
    DEPLOY_VERIFICATION_STARTED = "deploy_verification_started"
    DEPLOY_VERIFICATION_PASSED = "deploy_verification_passed"
    DEPLOY_VERIFICATION_FAILED = "deploy_verification_failed"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Telemetry Event
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class ExecutionTelemetryEvent:
    """A single telemetry event in the execution lifecycle."""

    event_id: str = field(
        default_factory=lambda: f"extel-{uuid4().hex[:12]}"
    )
    execution_id: str = ""
    request_id: str = ""
    executor_type: str = ""
    operation: str = ""
    event_type: str = ""
    timestamp: float = field(default_factory=time.time)
    status: str = ""
    sequence_number: int = 0
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "execution_id": self.execution_id,
            "request_id": self.request_id,
            "executor_type": self.executor_type,
            "operation": self.operation,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "status": self.status,
            "sequence_number": self.sequence_number,
            "payload": self.payload,
        }

    def to_sse(self) -> str:
        """Format as Server-Sent Event."""
        data = json.dumps(self.to_dict())
        return f"id: {self.sequence_number}\nevent: {self.event_type}\ndata: {data}\n\n"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionTelemetryEvent:
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Payload Redaction
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_SECRET_PATTERNS: list[str] = [
    "token",
    "api_key",
    "apikey",
    "api-key",
    "authorization",
    "cookie",
    "password",
    "passwd",
    "secret",
    "private_key",
    "private-key",
    "credentials",
    "aws_access",
    "aws_secret",
]

_SECRET_REGEX = re.compile(
    "|".join(re.escape(p) for p in _SECRET_PATTERNS),
    re.IGNORECASE,
)

_CREDENTIAL_SHAPES = re.compile(
    "|".join([
        r"sk-[a-z]+-[A-Za-z0-9_-]{20,}",
        r"sk-ant-[A-Za-z0-9_-]{20,}",
        r"ghp_[A-Za-z0-9]{36}",
        r"gho_[A-Za-z0-9]{36}",
        r"github_pat_[A-Za-z0-9_]{22,}",
        r"AKIA[0-9A-Z]{16}",
        r"xox[bp]-[A-Za-z0-9\-]{20,}",
        r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
        r"://[^/\s]+:[^@\s]+@",
        r"[A-Za-z0-9+/]{40,}={0,2}",
        r"[0-9a-f]{40,}",
    ])
)


def _value_looks_secret(value: str) -> bool:
    if _SECRET_REGEX.search(value):
        return True
    if _CREDENTIAL_SHAPES.search(value):
        return True
    return False


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return "[REDACTED]" if _value_looks_secret(value) else value
    if isinstance(value, dict):
        return redact_telemetry_payload(value)
    if isinstance(value, (list, tuple)):
        return [_redact_value(item) for item in value]
    return value


def redact_telemetry_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Redact secret-looking values from telemetry payloads."""
    if not payload:
        return payload

    redacted: dict[str, Any] = {}
    for key, value in payload.items():
        if _SECRET_REGEX.search(key):
            redacted[key] = "[REDACTED]"
        else:
            redacted[key] = _redact_value(value)
    return redacted


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# In-Memory Store
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_MAX_EVENTS = 10_000


class InMemoryExecutionTelemetryStore:
    """Bounded in-memory store for telemetry events.

    Thread-safe. Events older than the cap are evicted FIFO.
    Indexed by execution_id for fast per-execution queries.
    """

    def __init__(self, max_events: int = _MAX_EVENTS) -> None:
        self._lock = threading.Lock()
        self._events: list[ExecutionTelemetryEvent] = []
        self._by_execution: dict[str, list[ExecutionTelemetryEvent]] = defaultdict(list)
        self._max = max_events
        self._seq = 0

    def append(self, event: ExecutionTelemetryEvent) -> ExecutionTelemetryEvent:
        """Add event, assign sequence number, evict if over capacity."""
        with self._lock:
            self._seq += 1
            event.sequence_number = self._seq
            event.payload = redact_telemetry_payload(event.payload)

            self._events.append(event)
            if event.execution_id:
                self._by_execution[event.execution_id].append(event)

            while len(self._events) > self._max:
                evicted = self._events.pop(0)
                exec_list = self._by_execution.get(evicted.execution_id, [])
                if exec_list and exec_list[0].event_id == evicted.event_id:
                    exec_list.pop(0)

            return event

    def get_events(self, execution_id: str) -> list[ExecutionTelemetryEvent]:
        """All events for a specific execution."""
        with self._lock:
            return list(self._by_execution.get(execution_id, []))

    def get_events_after(
        self, execution_id: str, after_sequence: int
    ) -> list[ExecutionTelemetryEvent]:
        """Events for an execution after a given sequence number (for polling)."""
        with self._lock:
            events = self._by_execution.get(execution_id, [])
            return [e for e in events if e.sequence_number > after_sequence]

    def get_latest(self, limit: int = 50) -> list[ExecutionTelemetryEvent]:
        """Most recent events across all executions."""
        with self._lock:
            return list(self._events[-limit:])

    def clear(self) -> None:
        """Clear all events."""
        with self._lock:
            self._events.clear()
            self._by_execution.clear()
            self._seq = 0

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._events)

    @property
    def sequence(self) -> int:
        with self._lock:
            return self._seq


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Telemetry Emitter
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


TelemetrySubscriber = Callable[[ExecutionTelemetryEvent], None]


class ExecutionTelemetryEmitter:
    """Emitter for execution telemetry events.

    Subscribers receive events in real-time. The store persists
    events for polling/query. Emit never raises — failures are
    logged and swallowed.
    """

    def __init__(self, store: InMemoryExecutionTelemetryStore | None = None) -> None:
        self._store = store or InMemoryExecutionTelemetryStore()
        self._subscribers: dict[str, list[TelemetrySubscriber]] = defaultdict(list)
        self._global_subscribers: list[TelemetrySubscriber] = []
        self._lock = threading.Lock()

    @property
    def store(self) -> InMemoryExecutionTelemetryStore:
        return self._store

    def emit(
        self,
        event_type: str,
        *,
        execution_id: str = "",
        request_id: str = "",
        executor_type: str = "",
        operation: str = "",
        status: str = "",
        payload: dict[str, Any] | None = None,
    ) -> ExecutionTelemetryEvent | None:
        """Emit a telemetry event. Never raises."""
        try:
            event = ExecutionTelemetryEvent(
                execution_id=execution_id or request_id,
                request_id=request_id,
                executor_type=executor_type,
                operation=operation,
                event_type=event_type,
                status=status,
                payload=payload or {},
            )
            self._store.append(event)

            with self._lock:
                subs = list(self._subscribers.get(execution_id, []))
                global_subs = list(self._global_subscribers)

            for sub in subs + global_subs:
                try:
                    sub(event)
                except Exception:
                    logger.debug("Telemetry subscriber error", exc_info=True)

            return event
        except Exception:
            logger.debug("Telemetry emit error", exc_info=True)
            return None

    def subscribe(
        self,
        execution_id: str,
        callback: TelemetrySubscriber,
    ) -> None:
        """Subscribe to events for a specific execution."""
        with self._lock:
            self._subscribers[execution_id].append(callback)

    def unsubscribe(
        self,
        execution_id: str,
        callback: TelemetrySubscriber,
    ) -> None:
        """Remove a subscriber."""
        with self._lock:
            subs = self._subscribers.get(execution_id, [])
            if callback in subs:
                subs.remove(callback)

    def subscribe_all(self, callback: TelemetrySubscriber) -> None:
        """Subscribe to all execution events."""
        with self._lock:
            self._global_subscribers.append(callback)

    def unsubscribe_all(self, callback: TelemetrySubscriber) -> None:
        """Remove a global subscriber."""
        with self._lock:
            if callback in self._global_subscribers:
                self._global_subscribers.remove(callback)

    def get_events(self, execution_id: str) -> list[ExecutionTelemetryEvent]:
        """Get all events for an execution."""
        return self._store.get_events(execution_id)

    def get_events_after(
        self, execution_id: str, after_sequence: int
    ) -> list[ExecutionTelemetryEvent]:
        """Get events after a sequence number (polling support)."""
        return self._store.get_events_after(execution_id, after_sequence)

    def get_latest(self, limit: int = 50) -> list[ExecutionTelemetryEvent]:
        """Get most recent events."""
        return self._store.get_latest(limit)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Singleton
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_singleton: ExecutionTelemetryEmitter | None = None


def get_telemetry_emitter() -> ExecutionTelemetryEmitter:
    """Get the global telemetry emitter singleton."""
    global _singleton
    if _singleton is None:
        _singleton = ExecutionTelemetryEmitter()
    return _singleton


def reset_telemetry_emitter() -> None:
    """Reset the singleton (for testing)."""
    global _singleton
    _singleton = None
