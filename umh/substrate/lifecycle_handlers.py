"""
Lifecycle event handlers for the event-driven scheduler.

Each handler wraps an existing run_lifecycle.py transition. Handlers
are pure functions: (store, event) → ExecutionResult. They never
modify the store directly — the scheduler applies their mutations.

Guards mirror the lifecycle manager's gate conditions, reading from
the RuntimeStateStore (event-sourced view) rather than RunLifecycleRecord.

Handler chain:
  run_completion_proposed
    → finalization_succeeded
      → publication_confirmed
        → clear_requested
          → clear_confirmed
            → terminal_seal_applied
"""

from __future__ import annotations

import sys
from typing import Any

from umh.substrate.event_scheduler import (
    EventScheduler,
    ExecutionResult,
    GuardFn,
    HandlerFn,
    SchedulerEvent,
)
from umh.substrate.runtime_state_store import RuntimeStateStore

_LOG_PREFIX = "[substrate.lifecycle_handlers]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


# ─── Guards ────────────────────────────────────────────────────────────
#
# Guards read from the RuntimeStateStore (event-sourced state).
# They return True if the handler should execute, False to skip.
# ───────────────────────────────────────────────────────────────────────


def guard_not_finalized(store: RuntimeStateStore, event: SchedulerEvent) -> bool:
    """Allow only if finalization has not already succeeded."""
    return store.get("finalization_status") != "succeeded"


def guard_finalization_succeeded(
    store: RuntimeStateStore, event: SchedulerEvent
) -> bool:
    """Allow only if finalization has succeeded."""
    return store.get("finalization_status") == "succeeded"


def guard_not_published(store: RuntimeStateStore, event: SchedulerEvent) -> bool:
    """Allow only if publication has not yet been confirmed."""
    return store.get("publication_confirmed") is not True


def guard_published(store: RuntimeStateStore, event: SchedulerEvent) -> bool:
    """Allow only if publication has been confirmed."""
    return store.get("publication_confirmed") is True


def guard_clear_not_requested(store: RuntimeStateStore, event: SchedulerEvent) -> bool:
    """Allow only if clear has not yet been requested."""
    return store.get("clear_status") not in (
        "requested",
        "sent",
        "confirmed",
    )


def guard_clear_requested(store: RuntimeStateStore, event: SchedulerEvent) -> bool:
    """Allow only if clear has been requested (but not yet confirmed)."""
    return store.get("clear_status") == "requested"


def guard_not_terminally_finalized(
    store: RuntimeStateStore, event: SchedulerEvent
) -> bool:
    """Allow only if the run is not terminally finalized."""
    return store.get("terminally_finalized") is not True


def guard_terminal_ready(store: RuntimeStateStore, event: SchedulerEvent) -> bool:
    """Allow only if all terminal seal conditions are met.

    Conditions:
      - publication_confirmed == True
      - clear_status in ("confirmed", "stalled_safe") OR no_clear_policy
    """
    if store.get("terminally_finalized") is True:
        return False
    if store.get("publication_confirmed") is not True:
        return False
    clear_status = store.get("clear_status")
    no_clear = store.get("no_clear_policy", False)
    return clear_status in ("confirmed", "stalled_safe") or no_clear is True


# ─── Handlers ──────────────────────────────────────────────────────────
#
# Each handler returns an ExecutionResult with:
#   - mutations: state changes to apply
#   - emitted_events: follow-up events to enqueue
#
# Handlers wrap existing lifecycle transitions without reimplementing them.
# ───────────────────────────────────────────────────────────────────────


def handle_run_completion_proposed(
    store: RuntimeStateStore, event: SchedulerEvent
) -> ExecutionResult:
    """Handle a run completion proposal.

    Sets completion owner and status, then emits finalization_succeeded
    if finalization data is present in the payload, or signals that
    finalization should be attempted.
    """
    source = event.payload.get("source", event.source)
    mutations = [
        {"op": "SET", "key": "completion_owner", "value": source},
        {"op": "SET", "key": "status", "value": "completion_proposed"},
    ]

    # If finalization result is carried in the event, chain directly
    finalization_result = event.payload.get("finalization_result")
    emitted: list[SchedulerEvent] = []
    if finalization_result and finalization_result.get("success"):
        emitted.append(
            SchedulerEvent(
                event_type="finalization_succeeded",
                session_name=event.session_name,
                source=source,
                run_id=event.run_id,
                payload={"finalization_result": finalization_result},
            )
        )

    return ExecutionResult(
        mutations=mutations,
        emitted_events=emitted,
        metadata={"handler": "handle_run_completion_proposed"},
    )


def handle_finalization_succeeded(
    store: RuntimeStateStore, event: SchedulerEvent
) -> ExecutionResult:
    """Handle successful finalization. Emits publication_confirmed."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    mutations = [
        {"op": "SET", "key": "finalization_status", "value": "succeeded"},
        {"op": "SET", "key": "status", "value": "finalized"},
        {"op": "SET", "key": "finalized_at", "value": now},
    ]

    # Chain: finalization → publication
    emitted = [
        SchedulerEvent(
            event_type="publication_confirmed",
            session_name=event.session_name,
            source=event.source,
            run_id=event.run_id,
            payload=event.payload,
        )
    ]

    return ExecutionResult(
        mutations=mutations,
        emitted_events=emitted,
        metadata={"handler": "handle_finalization_succeeded"},
    )


def handle_publication_confirmed(
    store: RuntimeStateStore, event: SchedulerEvent
) -> ExecutionResult:
    """Handle publication confirmation. Emits clear_requested."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    mutations = [
        {"op": "SET", "key": "publication_confirmed", "value": True},
        {"op": "SET", "key": "publication_confirmed_at", "value": now},
    ]

    # Chain: publication → clear request
    emitted = [
        SchedulerEvent(
            event_type="clear_requested",
            session_name=event.session_name,
            source=event.source,
            run_id=event.run_id,
            payload=event.payload,
        )
    ]

    return ExecutionResult(
        mutations=mutations,
        emitted_events=emitted,
        metadata={"handler": "handle_publication_confirmed"},
    )


def handle_clear_requested(
    store: RuntimeStateStore, event: SchedulerEvent
) -> ExecutionResult:
    """Handle clear request. Sets clear_status and emits clear_confirmed.

    In the full system, clear_confirmed would come from the physical
    tmux injection path. For event-driven proof, we chain directly.
    """
    mutations = [
        {"op": "SET", "key": "clear_status", "value": "requested"},
        {"op": "SET", "key": "status", "value": "clear_requested"},
    ]

    # Chain: request → confirmed (in production, this would be async)
    emitted = [
        SchedulerEvent(
            event_type="clear_confirmed",
            session_name=event.session_name,
            source=event.source,
            run_id=event.run_id,
            payload=event.payload,
        )
    ]

    return ExecutionResult(
        mutations=mutations,
        emitted_events=emitted,
        metadata={"handler": "handle_clear_requested"},
    )


def handle_clear_confirmed(
    store: RuntimeStateStore, event: SchedulerEvent
) -> ExecutionResult:
    """Handle clear confirmation. Emits terminal_seal_applied."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    mutations = [
        {"op": "SET", "key": "clear_status", "value": "confirmed"},
        {"op": "SET", "key": "status", "value": "cleared"},
        {"op": "SET", "key": "cleared_at", "value": now},
    ]

    # Chain: clear confirmed → terminal seal
    emitted = [
        SchedulerEvent(
            event_type="terminal_seal_applied",
            session_name=event.session_name,
            source=event.source,
            run_id=event.run_id,
            payload=event.payload,
        )
    ]

    return ExecutionResult(
        mutations=mutations,
        emitted_events=emitted,
        metadata={"handler": "handle_clear_confirmed"},
    )


def handle_terminal_seal(
    store: RuntimeStateStore, event: SchedulerEvent
) -> ExecutionResult:
    """Handle terminal seal. Final lifecycle event — no follow-up."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    mutations = [
        {"op": "SET", "key": "terminally_finalized", "value": True},
        {"op": "SET", "key": "terminally_finalized_at", "value": now},
    ]

    return ExecutionResult(
        mutations=mutations,
        emitted_events=[],
        metadata={"handler": "handle_terminal_seal"},
    )


# ─── Factory ───────────────────────────────────────────────────────────


def create_lifecycle_scheduler(
    store: RuntimeStateStore,
    event_log: EventLogRuntime | None = None,
) -> EventScheduler:
    """Create a fully-wired EventScheduler for lifecycle transitions.

    Returns a scheduler with all handlers and guards registered.
    Caller just needs to emit events and call run().
    """
    from umh.substrate.event_log_runtime import EventLogRuntime

    scheduler = EventScheduler(store=store, event_log=event_log)

    scheduler.subscribe(
        "run_completion_proposed",
        handle_run_completion_proposed,
        guard=guard_not_finalized,
        name="completion_proposal",
    )

    scheduler.subscribe(
        "finalization_succeeded",
        handle_finalization_succeeded,
        guard=guard_not_published,
        name="finalization",
    )

    scheduler.subscribe(
        "publication_confirmed",
        handle_publication_confirmed,
        guard=guard_clear_not_requested,
        name="publication",
    )

    scheduler.subscribe(
        "clear_requested",
        handle_clear_requested,
        guard=guard_clear_not_requested,
        name="clear_request",
    )

    scheduler.subscribe(
        "clear_confirmed",
        handle_clear_confirmed,
        guard=guard_clear_requested,
        name="clear_confirm",
    )

    scheduler.subscribe(
        "terminal_seal_applied",
        handle_terminal_seal,
        guard=guard_terminal_ready,
        name="terminal_seal",
    )

    return scheduler
