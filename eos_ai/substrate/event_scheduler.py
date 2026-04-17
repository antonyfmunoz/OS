"""
Event-driven scheduler for lifecycle execution.

Phase 3 of the event-sourced runtime: replaces pull-based orchestration
with event emission → routing → guard evaluation → handler execution.

Design:
- FIFO event queue with breadth-first drain.
- Subscriber registry maps event_type → list of (guard, handler) pairs.
- Guards are optional predicates: guard(store, event) → bool.
- Handlers return ExecutionResult with mutations + follow-up events.
- The scheduler applies mutations to the store and logs events — handlers
  never touch the store or event log directly.
- Dedup via event_id prevents double-processing during shadow execution.
- Thread-safe via a single execution lock per scheduler instance.

Invariants:
- All state mutations flow through: handler → ExecutionResult → scheduler.
- Events are the ONLY trigger for handler execution.
- Guard evaluation happens BEFORE handler execution.
- Emitted follow-up events go to the back of the queue (breadth-first).
- The scheduler never raises into the caller on handler failure.
"""

from __future__ import annotations

import sys
import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Protocol

from eos_ai.substrate.event_log_runtime import EventLogRuntime
from eos_ai.substrate.runtime_state_store import RuntimeStateStore

# Lazy import to avoid circular dependency; set by register_event_schema_source().
_event_schema_source: Any | None = None


class NonMutatingEventViolation(RuntimeError):
    """Raised when a handler for a non-mutating event returns mutations.

    Non-mutating events (EventSchema.is_mutation=False) are observability-
    only.  Their handlers must never return state mutations.  This is
    enforced structurally at the scheduler execution boundary.
    """


def register_event_schema_source(registry: Any) -> None:
    """Register an EventTypeRegistry for runtime mutation enforcement.

    The scheduler uses this registry to look up EventSchema.is_mutation
    for each event type.  When is_mutation=False and a handler returns
    mutations, NonMutatingEventViolation is raised.

    Args:
        registry: An EventTypeRegistry instance (from llm_planner).
            Must have a .get(event_type) → EventSchema | None method.
    """
    global _event_schema_source
    _event_schema_source = registry


_LOG_PREFIX = "[substrate.event_scheduler]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Data structures ───────────────────────────────────────────────────


@dataclass
class SchedulerEvent:
    """An event flowing through the scheduler.

    event_type drives routing. event_id enables dedup. session_name
    scopes the event to a lifecycle session.
    """

    event_type: str
    session_name: str
    source: str
    event_id: str = ""
    run_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_id:
            self.event_id = f"sev_{uuid.uuid4().hex[:12]}"


@dataclass
class ExecutionResult:
    """Return value from a handler.

    Handlers communicate their effects through this object — they never
    touch the store or event log directly.

    Fields:
        mutations: State mutations to apply to RuntimeStateStore.
        emitted_events: Follow-up SchedulerEvents to enqueue.
        metadata: Optional metadata for logging/forensics.
    """

    mutations: list[dict[str, Any]] = field(default_factory=list)
    emitted_events: list[SchedulerEvent] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# ─── Type aliases ──────────────────────────────────────────────────────

GuardFn = Callable[[RuntimeStateStore, SchedulerEvent], bool]
HandlerFn = Callable[[RuntimeStateStore, SchedulerEvent], ExecutionResult]


@dataclass
class Subscription:
    """A handler registered for an event type, with optional guard."""

    handler: HandlerFn
    guard: GuardFn | None = None
    name: str = ""


@dataclass
class RouteResult:
    """Outcome of routing a single event."""

    event: SchedulerEvent
    handlers_called: int = 0
    handlers_guarded: int = 0
    handlers_failed: int = 0
    mutations_applied: int = 0
    events_emitted: int = 0
    skipped_dedup: bool = False


@dataclass
class RunResult:
    """Outcome of a full scheduler run (queue drain)."""

    events_processed: int = 0
    events_skipped_dedup: int = 0
    total_handlers_called: int = 0
    total_mutations_applied: int = 0
    total_events_emitted: int = 0
    total_handler_failures: int = 0
    route_results: list[RouteResult] = field(default_factory=list)


# ─── EventScheduler ───────────���───────────────────────────────────────


class EventScheduler:
    """Event-driven scheduler with FIFO queue, guards, and dedup.

    Usage:
        scheduler = EventScheduler(store, event_log)
        scheduler.subscribe("finalization_succeeded", handler, guard=my_guard)
        scheduler.emit(SchedulerEvent(event_type="finalization_succeeded", ...))
        result = scheduler.run()
    """

    def __init__(
        self,
        store: RuntimeStateStore,
        event_log: EventLogRuntime | None = None,
    ) -> None:
        self._store = store
        self._event_log = event_log
        self._queue: deque[SchedulerEvent] = deque()
        self._dedup: set[str] = set()
        self._subscribers: dict[str, list[Subscription]] = {}
        self._lock = threading.Lock()
        self._max_iterations = 1000  # circuit breaker

    # ── Public API ���────────────────────────────────────────────────

    def emit(self, event: SchedulerEvent) -> None:
        """Enqueue an event for processing. Returns immediately."""
        with self._lock:
            self._queue.append(event)

    def subscribe(
        self,
        event_type: str,
        handler: HandlerFn,
        guard: GuardFn | None = None,
        name: str = "",
    ) -> None:
        """Register a handler for an event type with optional guard.

        Multiple handlers can subscribe to the same event type.
        Guards are evaluated before handler execution.
        """
        sub = Subscription(handler=handler, guard=guard, name=name)
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(sub)
            _log(f"subscribed: {name or 'anonymous'} → {event_type}")

    def run(self) -> RunResult:
        """Drain the event queue. Process events breadth-first.

        Each event is routed to its subscribers. Follow-up events from
        handlers go to the back of the queue. Dedup prevents double-
        processing. Circuit breaker at max_iterations prevents infinite loops.
        """
        result = RunResult()
        iterations = 0

        while True:
            with self._lock:
                if not self._queue:
                    break
                event = self._queue.popleft()

            iterations += 1
            if iterations > self._max_iterations:
                _log(f"CIRCUIT BREAKER: {iterations} iterations, aborting queue drain")
                break

            # Dedup check
            if event.event_id in self._dedup:
                result.events_skipped_dedup += 1
                result.route_results.append(
                    RouteResult(event=event, skipped_dedup=True)
                )
                continue

            self._dedup.add(event.event_id)
            route_result = self._route(event)
            result.events_processed += 1
            result.total_handlers_called += route_result.handlers_called
            result.total_mutations_applied += route_result.mutations_applied
            result.total_events_emitted += route_result.events_emitted
            result.total_handler_failures += route_result.handlers_failed
            result.route_results.append(route_result)

        return result

    def reset(self) -> None:
        """Clear queue, dedup set, and subscribers. For testing."""
        with self._lock:
            self._queue.clear()
            self._dedup.clear()
            self._subscribers.clear()

    def pending_count(self) -> int:
        """Return number of events in the queue."""
        with self._lock:
            return len(self._queue)

    # ── Internal routing ──────────���────────────────────────────────

    def _route(self, event: SchedulerEvent) -> RouteResult:
        """Route an event to all matching subscribers."""
        route_result = RouteResult(event=event)

        with self._lock:
            subs = list(self._subscribers.get(event.event_type, []))

        if not subs:
            _log(f"no subscribers for: {event.event_type}")
            return route_result

        for sub in subs:
            # Evaluate guard
            if sub.guard is not None:
                try:
                    if not sub.guard(self._store, event):
                        route_result.handlers_guarded += 1
                        _log(
                            f"guard blocked: {sub.name or 'anonymous'} "
                            f"for {event.event_type}"
                        )
                        continue
                except Exception as exc:
                    route_result.handlers_guarded += 1
                    _log(
                        f"guard error: {sub.name or 'anonymous'} "
                        f"for {event.event_type}: {exc}"
                    )
                    continue

            # Execute handler
            try:
                exec_result = sub.handler(self._store, event)
                route_result.handlers_called += 1
            except Exception as exc:
                route_result.handlers_failed += 1
                _log(
                    f"handler error: {sub.name or 'anonymous'} "
                    f"for {event.event_type}: {exc}"
                )
                continue

            # Enforce non-mutating event constraint.
            # If a registered EventSchema has is_mutation=False, handlers
            # for that event type must NEVER return mutations.
            if exec_result.mutations and _event_schema_source is not None:
                schema = _event_schema_source.get(event.event_type)
                if schema is not None and not schema.is_mutation:
                    raise NonMutatingEventViolation(
                        f"Handler '{sub.name or 'anonymous'}' returned "
                        f"{len(exec_result.mutations)} mutation(s) for "
                        f"non-mutating event '{event.event_type}'. "
                        f"Observability events must not mutate state."
                    )

            # Apply mutations (via scheduler write context for enforcement)
            if exec_result.mutations:
                with self._store.scheduler_write_context():
                    self._store.apply_mutations(exec_result.mutations)
                route_result.mutations_applied += len(exec_result.mutations)

                # Log to durable event log
                if self._event_log is not None:
                    try:
                        self._event_log.append(
                            event_type=event.event_type,
                            session_name=event.session_name,
                            source=f"scheduler:{sub.name or event.source}",
                            run_id=event.run_id,
                            payload=event.payload,
                            state_mutations=exec_result.mutations,
                            metadata={
                                **event.metadata,
                                "scheduler_handler": sub.name or "anonymous",
                                **(exec_result.metadata or {}),
                            },
                        )
                    except Exception as exc:
                        _log(f"event log append failed: {exc}")

            # Enqueue follow-up events
            for follow_up in exec_result.emitted_events:
                route_result.events_emitted += 1
                self.emit(follow_up)

        return route_result
