"""Event router — bridges substrate SchedulerEvents to adapter execution surfaces.

This is the ONLY module that connects substrate event output to the
outside world. Substrate never imports adapters. Adapters import
substrate types read-only.

Flow:
    SchedulerEvent → registry.get_handlers(event.type)
                   → handler.handle(event, context) for each
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Sequence

from umh.adapters.contracts import AdapterContext
from umh.adapters.registry import AdapterRegistry
from umh.substrate.event_scheduler import SchedulerEvent

logger = logging.getLogger(__name__)


def _build_context(
    event: SchedulerEvent,
    state: dict[str, Any],
) -> AdapterContext:
    """Build an AdapterContext from a SchedulerEvent and state snapshot."""
    return AdapterContext(
        state_snapshot=state,
        runtime_session_id=event.session_name,
        correlation_id=event.metadata.get(
            "correlation_id", f"cor_{uuid.uuid4().hex[:12]}"
        ),
        metadata={
            "event_id": event.event_id,
            "run_id": event.run_id,
            "source": event.source,
        },
    )


def route_events(
    events: Sequence[SchedulerEvent],
    state: dict[str, Any],
    registry: AdapterRegistry,
) -> list[dict[str, Any]]:
    """Route a batch of SchedulerEvents to registered adapters.

    Args:
        events: SchedulerEvents emitted by the substrate.
        state: Current runtime state snapshot (read-only for adapters).
        registry: AdapterRegistry containing registered adapters.

    Returns:
        List of dispatch records for observability. Each record contains:
        - event_id, event_type, adapter, status, error (if any).
    """
    dispatch_log: list[dict[str, Any]] = []

    for event in events:
        handlers = registry.get_handlers(event.event_type)

        if not handlers:
            logger.debug(
                "No handlers for event_type=%s event_id=%s",
                event.event_type,
                event.event_id,
            )
            dispatch_log.append(
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "adapter": None,
                    "status": "no_handler",
                }
            )
            continue

        context = _build_context(event, state)

        for handler in handlers:
            adapter_name = type(handler).__name__
            try:
                handler.handle(event, context)
                dispatch_log.append(
                    {
                        "event_id": event.event_id,
                        "event_type": event.event_type,
                        "adapter": adapter_name,
                        "status": "ok",
                    }
                )
                logger.info(
                    "Dispatched event_type=%s → %s (event_id=%s)",
                    event.event_type,
                    adapter_name,
                    event.event_id,
                )
            except Exception:
                logger.exception(
                    "Adapter %s failed on event_type=%s event_id=%s",
                    adapter_name,
                    event.event_type,
                    event.event_id,
                )
                dispatch_log.append(
                    {
                        "event_id": event.event_id,
                        "event_type": event.event_type,
                        "adapter": adapter_name,
                        "status": "error",
                    }
                )

    return dispatch_log
