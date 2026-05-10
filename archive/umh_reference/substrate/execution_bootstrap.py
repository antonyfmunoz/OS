"""
Execution fabric bootstrap — wires ExecutionWorker and ExecutionResultHandler
into an EventScheduler instance.

Mirrors the pattern of lifecycle_handlers.create_lifecycle_scheduler and
orchestration_bootstrap.bootstrap_orchestration: small bootstrap functions
that attach subscribers and return the component for inspection/testing.

Usage:
    from umh.substrate.execution_bootstrap import (
        bootstrap_execution_worker,
        bootstrap_execution_result_handler,
    )

    worker = bootstrap_execution_worker(scheduler, store)
    handler = bootstrap_execution_result_handler(scheduler)
"""

from __future__ import annotations

import sys

from umh.substrate.event_scheduler import EventScheduler
from umh.substrate.execution_result_handler import ExecutionResultHandler
from umh.substrate.execution_worker import ExecutionWorker
from umh.substrate.runtime_state_store import RuntimeStateStore

_LOG_PREFIX = "[substrate.execution_bootstrap]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


_EXECUTION_REQUEST_EVENTS = (
    "execution_requested",
    "execution_retried",
)

_EXECUTION_RESULT_EVENTS = (
    "execution_completed",
    "execution_failed",
    "execution_timed_out",
    "execution_rejected",
)


def bootstrap_execution_worker(
    scheduler: EventScheduler,
    store: RuntimeStateStore,
) -> ExecutionWorker:
    """Wire an ExecutionWorker into the scheduler.

    Subscribes to execution_requested and execution_retried events.
    Returns the worker instance so callers can register adapters.
    """
    worker = ExecutionWorker(store)

    scheduler.subscribe(
        event_type="execution_requested",
        handler=worker.handle_execution_requested,
        name="execution_worker",
    )
    scheduler.subscribe(
        event_type="execution_retried",
        handler=worker.handle_execution_requested,
        name="execution_worker_retry",
    )

    _log("execution worker wired: 2 subscriptions")
    return worker


def bootstrap_execution_result_handler(
    scheduler: EventScheduler,
    primitive_emission_map: dict[str, list[str]] | None = None,
    primitive_conditional_map: dict[str, dict[str, str]] | None = None,
) -> ExecutionResultHandler:
    """Wire an ExecutionResultHandler into the scheduler.

    Subscribes to all 4 execution result event types.
    Returns the handler instance for inspection.
    """
    handler = ExecutionResultHandler(
        primitive_emission_map=primitive_emission_map,
        primitive_conditional_map=primitive_conditional_map,
    )

    for event_type in _EXECUTION_RESULT_EVENTS:
        scheduler.subscribe(
            event_type=event_type,
            handler=handler.handle_result,
            name=f"exec_result.{event_type}",
        )

    _log(
        f"execution result handler wired: {len(_EXECUTION_RESULT_EVENTS)} subscriptions"
    )
    return handler
