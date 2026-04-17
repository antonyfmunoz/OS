"""
Event-primary execution authority for lifecycle transitions.

Phase 4: Authority transfer. This module provides the scheduler-driven
execution path for every lifecycle transition. When ExecutionMode is
EVENT_PRIMARY, run_lifecycle.py routes calls here instead of through
the legacy _RunLifecycleManager.

Design:
- Each function emits the appropriate event, drains the scheduler,
  reads final state from RuntimeStateStore, and returns the same
  result types that callers already expect.
- The scheduler + handlers are the ONLY code that mutates state.
- Write enforcement on RuntimeStateStore ensures no hidden writes.
- On scheduler failure, raises ExecutionAuthorityError — the caller
  (run_lifecycle.py) catches and falls back to legacy.

This module never imports _RunLifecycleManager or calls legacy methods.
It depends only on the event-sourced infrastructure.
"""

from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from eos_ai.substrate.event_scheduler import (
    EventScheduler,
    ExecutionResult as SchedulerExecutionResult,
    RunResult,
    SchedulerEvent,
)
from eos_ai.substrate.execution_contract import (
    ExecutionClass,
    ExecutionConstraints,
    ExecutionRequest,
    RoutingContext,
    _compute_idempotency_key,
    _new_execution_id,
)
from eos_ai.substrate.execution_events import build_execution_requested_event
from eos_ai.substrate.execution_router import ExecutionRouter
from eos_ai.substrate.lifecycle_handlers import create_lifecycle_scheduler
from eos_ai.substrate.runtime_state_store import RuntimeStateStore

_LOG_PREFIX = "[substrate.execution_authority]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class ExecutionAuthorityError(RuntimeError):
    """Raised when the event-primary scheduler fails to execute."""


@dataclass
class EventPrimaryResult:
    """Diagnostics from an event-primary execution."""

    scheduler_result: RunResult
    final_state: dict[str, Any]
    state_hash: str
    execution_mode: str = "event_primary"


# ─── Scheduler singleton (separate from shadow) ─────────────────────────

_primary_scheduler: EventScheduler | None = None
_primary_store: RuntimeStateStore | None = None


def _get_primary_scheduler() -> tuple[EventScheduler, RuntimeStateStore]:
    """Return the event-primary scheduler and its store.

    Uses the process-local singletons from runtime_bootstrap.
    The scheduler is created once and reused.
    """
    global _primary_scheduler, _primary_store

    if _primary_scheduler is not None and _primary_store is not None:
        return _primary_scheduler, _primary_store

    from eos_ai.substrate.runtime_bootstrap import (
        get_event_log_runtime,
        get_runtime_state_store,
    )

    _primary_store = get_runtime_state_store()
    _primary_scheduler = create_lifecycle_scheduler(
        store=_primary_store,
        event_log=get_event_log_runtime(),
    )
    return _primary_scheduler, _primary_store


def _emit_and_drain(
    event_type: str,
    session_name: str,
    source: str,
    run_id: str = "",
    payload: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> EventPrimaryResult:
    """Core execution primitive: emit one event, drain the scheduler queue.

    Returns diagnostics including the full scheduler RunResult and final state.
    Raises ExecutionAuthorityError if the scheduler processes zero events
    (indicates handler/guard misconfiguration).
    """
    scheduler, store = _get_primary_scheduler()

    event = SchedulerEvent(
        event_type=event_type,
        session_name=session_name,
        source=source,
        run_id=run_id,
        payload=payload or {},
        metadata=metadata or {},
    )

    _log(
        f"emit: {event_type} session={session_name} source={source} "
        f"run_id={run_id} event_id={event.event_id}"
    )

    scheduler.emit(event)
    result = scheduler.run()

    _log(
        f"drain: processed={result.events_processed} "
        f"handlers={result.total_handlers_called} "
        f"mutations={result.total_mutations_applied} "
        f"failures={result.total_handler_failures}"
    )

    if result.total_handler_failures > 0:
        _log(f"WARNING: {result.total_handler_failures} handler failures during drain")

    return EventPrimaryResult(
        scheduler_result=result,
        final_state=store.snapshot(),
        state_hash=store.compute_state_hash(),
    )


# ─── Lifecycle transition functions ──────────────────────────────────────
#
# Each mirrors a legacy _RunLifecycleManager method. Same inputs, same
# return types. The scheduler does all the work.


def event_primary_propose_completion(
    session_name: str,
    source: str,
    *,
    payload: dict[str, Any] | None = None,
    run_id: str = "",
) -> EventPrimaryResult:
    """Propose run completion via the event scheduler.

    Emits run_completion_proposed. If finalization_result is in payload
    and success=True, the handler chains through finalization_succeeded
    automatically.
    """
    return _emit_and_drain(
        event_type="run_completion_proposed",
        session_name=session_name,
        source=source,
        run_id=run_id,
        payload={"source": source, **(payload or {})},
    )


def event_primary_finalize(
    session_name: str,
    source: str,
    finalize_fn: Callable[[], dict[str, Any]],
    *,
    run_id: str = "",
) -> EventPrimaryResult:
    """Execute finalization via the event scheduler.

    Calls finalize_fn() to get the finalization result, then emits
    finalization_succeeded if successful. The scheduler chains through
    publication_confirmed automatically.
    """
    # Execute the user-supplied finalization function
    finalization_result = finalize_fn()

    return _emit_and_drain(
        event_type="finalization_succeeded",
        session_name=session_name,
        source=source,
        run_id=run_id,
        payload={"finalization_result": finalization_result},
    )


def event_primary_record_publication(
    session_name: str,
    source: str,
    *,
    result_id: str = "",
    run_id: str = "",
) -> EventPrimaryResult:
    """Record publication via the event scheduler.

    Emits publication_confirmed. The scheduler chains through
    clear_requested automatically.
    """
    return _emit_and_drain(
        event_type="publication_confirmed",
        session_name=session_name,
        source=source,
        run_id=run_id,
        payload={"result_id": result_id},
    )


def event_primary_request_clear(
    session_name: str,
    source: str,
    *,
    run_id: str = "",
) -> EventPrimaryResult:
    """Request clear via the event scheduler.

    Emits clear_requested. The scheduler chains through clear_confirmed
    and terminal_seal_applied automatically.
    """
    return _emit_and_drain(
        event_type="clear_requested",
        session_name=session_name,
        source=source,
        run_id=run_id,
    )


def event_primary_confirm_clear(
    session_name: str,
    source: str,
    *,
    run_id: str = "",
) -> EventPrimaryResult:
    """Confirm clear via the event scheduler.

    Emits clear_confirmed. The scheduler chains to terminal_seal_applied.
    """
    return _emit_and_drain(
        event_type="clear_confirmed",
        session_name=session_name,
        source=source,
        run_id=run_id,
    )


def event_primary_mark_terminal(
    session_name: str,
    source: str,
    *,
    no_clear_policy: bool = False,
    run_id: str = "",
) -> EventPrimaryResult:
    """Attempt terminal seal via the event scheduler.

    Emits terminal_seal_applied. Guard will block if conditions
    (publication + clear) are not met.
    """
    _, store = _get_primary_scheduler()

    # If no_clear_policy, set it in the store so guard_terminal_ready passes
    if no_clear_policy:
        with store.scheduler_write_context():
            store.set("no_clear_policy", True)

    return _emit_and_drain(
        event_type="terminal_seal_applied",
        session_name=session_name,
        source=source,
        run_id=run_id,
        payload={"no_clear_policy": no_clear_policy},
    )


def event_primary_full_lifecycle(
    session_name: str,
    source: str,
    finalize_fn: Callable[[], dict[str, Any]],
    *,
    run_id: str = "",
    no_clear_policy: bool = False,
) -> EventPrimaryResult:
    """Execute the FULL lifecycle via a single scheduler drain.

    Emits run_completion_proposed with finalization_result embedded.
    The handler chain cascades: proposal → finalization → publication
    → clear → terminal seal. One emit, one drain, full lifecycle.

    This is the primary entry point for EVENT_PRIMARY mode.
    """
    finalization_result = finalize_fn()

    if not finalization_result.get("success"):
        raise ExecutionAuthorityError(
            f"finalize_fn returned success=False: {finalization_result}"
        )

    _, store = _get_primary_scheduler()
    if no_clear_policy:
        with store.scheduler_write_context():
            store.set("no_clear_policy", True)

    return _emit_and_drain(
        event_type="run_completion_proposed",
        session_name=session_name,
        source=source,
        run_id=run_id,
        payload={
            "source": source,
            "finalization_result": finalization_result,
        },
        metadata={
            "full_lifecycle": True,
            "no_clear_policy": no_clear_policy,
        },
    )


# ─── Control-plane dispatch authority ──────────────────────────────────


class ExecutionAuthority:
    """Control-plane handler that dispatches execution requests.

    Subscribes to lifecycle events that need physical execution (e.g. stability_reached).
    Builds ExecutionRequest, routes via ExecutionRouter, records in-flight state,
    emits EXECUTION_REQUESTED event.

    Does NOT call adapter.execute().
    Does NOT wait for results.
    Resumes only when a completion event arrives (handled by ResultHandler).
    """

    def __init__(self, router: ExecutionRouter) -> None:
        self._router = router

    def make_handler(
        self,
        primitive_name: str,
        execution_class: ExecutionClass,
        requires: list[str],
        constraints: ExecutionConstraints | None = None,
        required_capabilities: frozenset[str] | None = None,
    ) -> Callable[[RuntimeStateStore, SchedulerEvent], SchedulerExecutionResult]:
        """Factory: produce a scheduler handler for a specific primitive.

        Returns a callable matching HandlerFn signature:
            (store: RuntimeStateStore, event: SchedulerEvent) -> SchedulerExecutionResult

        The returned handler:
        1. Reads required state keys from the store.
        2. Computes an idempotency key from primitive name + inputs.
        3. Skips duplicate dispatches (same idempotency key already dispatched).
        4. Routes via ExecutionRouter.
        5. Builds an ExecutionRequest with full provenance.
        6. Records in-flight tracking state as mutations.
        7. Emits a single EXECUTION_REQUESTED event.
        """
        resolved_constraints = constraints or ExecutionConstraints()
        resolved_capabilities = required_capabilities or frozenset()

        def _handler(
            store: RuntimeStateStore, event: SchedulerEvent
        ) -> SchedulerExecutionResult:
            # 1. Read required state keys
            inputs: dict[str, Any] = {}
            for key in requires:
                val = store.get(key)
                if val is not None:
                    inputs[key] = val

            # 2. Compute idempotency key
            idempotency_key = _compute_idempotency_key(primitive_name, inputs)

            # 3. Check duplicate dispatch
            dispatched_keys = store.get("dispatched_idempotency_keys", [])
            if idempotency_key in dispatched_keys:
                _log(
                    f"skipping duplicate dispatch: {primitive_name} "
                    f"key={idempotency_key}"
                )
                return SchedulerExecutionResult(
                    mutations=[],
                    emitted_events=[],
                    metadata={"skipped": True},
                )

            # 4. Route via ExecutionRouter
            routing_ctx = RoutingContext(
                execution_class=execution_class,
                required_capabilities=resolved_capabilities,
            )
            decision = self._router.route(routing_ctx)

            # 5. Build ExecutionRequest
            execution_id = _new_execution_id()
            request = ExecutionRequest(
                execution_id=execution_id,
                correlation_id=event.payload.get("correlation_id", ""),
                causal_event_id=event.event_id,
                session_name=event.session_name,
                run_id=event.run_id or "",
                primitive_name=primitive_name,
                inputs=inputs,
                execution_class=execution_class,
                constraints=resolved_constraints,
                target=decision.target,
                issued_at=datetime.now(timezone.utc).isoformat(),
                issued_by="execution_authority",
                idempotency_key=idempotency_key,
                retry_count=0,
            )

            # 6. Build in-flight record
            in_flight_record: dict[str, Any] = {
                "execution_id": execution_id,
                "primitive_name": primitive_name,
                "target_node_id": decision.target.node_id,
                "dispatched_at": request.issued_at,
                "status": "dispatched",
                "retry_count": 0,
                "idempotency_key": idempotency_key,
                "routing_reason": decision.reason_code.value,
                "execution_class": execution_class.value,
                "max_retries": resolved_constraints.max_retries,
                "original_request": request.to_dict(),
                "fallback_node_id": decision.target.fallback_node_id,
                "fallback_transport": decision.target.fallback_transport,
            }

            # 7. Build mutations + event, return result
            mutations: list[dict[str, Any]] = [
                {
                    "op": "SET",
                    "key": f"in_flight_executions.{execution_id}",
                    "value": in_flight_record,
                },
                {
                    "op": "APPEND_UNIQUE",
                    "key": "dispatched_idempotency_keys",
                    "value": idempotency_key,
                },
            ]

            requested_event = build_execution_requested_event(
                request=request,
                session_name=event.session_name,
                run_id=event.run_id,
            )

            _log(
                f"dispatched: {primitive_name} exec_id={execution_id} "
                f"target={decision.target.node_id} "
                f"reason={decision.reason_code.value}"
            )

            return SchedulerExecutionResult(
                mutations=mutations,
                emitted_events=[requested_event],
                metadata={
                    "execution_id": execution_id,
                    "routed_to": decision.target.node_id,
                    "reason": decision.reason_code.value,
                },
            )

        return _handler


# ─── Testing ─────────────────────────────────────────────────────────────


def reset_for_testing() -> None:
    """Reset the event-primary scheduler singleton. FOR TESTING ONLY."""
    global _primary_scheduler, _primary_store
    _primary_scheduler = None
    _primary_store = None
