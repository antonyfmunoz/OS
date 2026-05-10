"""Runtime lifecycle orchestrator — the first real runnable system loop.

Single entrypoint that:
1. Reads state snapshot
2. Executes ritual (open_day / close_day)
3. Applies mutations to RuntimeStateStore
4. Routes events through AdapterRegistry
5. Returns structured execution result

Design rules:
- NO adapter logic here — adapters are opaque executors
- NO Discord/Notion/voice imports — transport-agnostic
- NO branching outside ritual selection
- PURE orchestration only
- State writes ONLY through state_store
- Always re-reads state after mutation before routing
"""

from __future__ import annotations

import logging
import uuid
import sys
from typing import Any

from umh.adapters.event_router import route_events
from umh.adapters.registry import AdapterRegistry
from umh.runtime_loop.action_executor import (
    ActionExecutionResult,
    ActionRequest,
    execute_action,
)
from umh.runtime_loop.context import RuntimeContext
try:
    from umh.substrate.daily_rituals import CloseDayRequest, OpenDayRequest
except ImportError:
    pass
from umh.substrate.event_scheduler import SchedulerEvent
try:
    from umh.substrate.ritual_execution_driver import (
    RitualExecutionResult,
    execute_close_day,
    execute_open_day,
    execute_resume_day,
    )
except ImportError:
    pass
from umh.substrate.runtime_state_store import RuntimeStateStore

logger = logging.getLogger(__name__)

_VALID_REQUEST_TYPES = frozenset({"open_day", "close_day", "action", "set_objective"})


def _resolve_resume_context(context: RuntimeContext) -> dict | None:
    """Check if this open_day should be a resume instead.

    Returns the previous_session dict if strategy is "resume", else None.
    """
    if not context.previous_session:
        return None
    try:
        from umh.runtime_loop.lifecycle_behaviors import get_resume_context

        rc = get_resume_context(context.runtime_session_id)
        if rc and rc.get("resume_decision", {}).get("strategy") == "resume":
            return context.previous_session
    except Exception:
        pass
    return None


def _build_open_day_request(context: RuntimeContext) -> OpenDayRequest:
    """Build an OpenDayRequest from RuntimeContext."""
    return OpenDayRequest(
        request_id=f"req_{uuid.uuid4().hex[:12]}",
        runtime_session_id=context.runtime_session_id,
        entry_transport=context.transport,
        requested_profile_id=context.requested_profile_id or "",
        requested_at=context.timestamp,
        correlation_id=context.correlation_id,
    )


def _build_close_day_request(context: RuntimeContext) -> CloseDayRequest:
    """Build a CloseDayRequest from RuntimeContext."""
    return CloseDayRequest(
        request_id=f"req_{uuid.uuid4().hex[:12]}",
        runtime_session_id=context.runtime_session_id,
        requested_at=context.timestamp,
        correlation_id=context.correlation_id,
    )


def _build_action_request(context: RuntimeContext) -> ActionRequest:
    """Build an ActionRequest from RuntimeContext."""
    return ActionRequest(
        request_id=f"req_{uuid.uuid4().hex[:12]}",
        runtime_session_id=context.runtime_session_id,
        intent_text=context.intent_text,
        transport=context.transport,
        requested_at=context.timestamp,
        correlation_id=context.correlation_id,
    )


def _update_objective_progress(
    session_id: str,
    events: list[SchedulerEvent],
    correlation_id: str,
) -> list[SchedulerEvent]:
    """Update session progress from events. Returns extra events to emit."""
    from umh.runtime_loop.session_registry import get_registry

    reg = get_registry()
    if reg.get_objective(session_id) is None:
        return []

    updated = reg.update_progress(session_id, events)
    if updated is None or updated.progress is None:
        return []

    extra: list[SchedulerEvent] = [
        SchedulerEvent(
            event_type="progress_updated",
            session_name=session_id,
            source="lifecycle",
            payload={"progress": updated.progress},
            metadata={"correlation_id": correlation_id},
        ),
    ]

    if updated.progress["status"] == "complete":
        extra.append(
            SchedulerEvent(
                event_type="objective_complete",
                session_name=session_id,
                source="lifecycle",
                payload={
                    "objective": updated.objective,
                    "progress": updated.progress,
                },
                metadata={"correlation_id": correlation_id},
            ),
        )
        logger.info(
            "Objective complete: session=%s objective=%r steps=%d",
            session_id,
            updated.objective,
            updated.progress["steps_completed"],
        )

    return extra


def _execute_set_objective(
    state: dict[str, Any],
    context: RuntimeContext,
    timestamp: str,
) -> tuple[list[dict[str, Any]], list[SchedulerEvent], ActionExecutionResult]:
    """Store the objective in the session registry and emit an event."""
    from umh.runtime_loop.session_registry import get_registry

    objective_text = context.intent_text
    session_id = context.runtime_session_id

    get_registry().set_objective(session_id, objective_text)

    mutations: list[dict[str, Any]] = [
        {
            "op": "SET",
            "key": f"session_objective.{session_id}",
            "value": objective_text,
        },
    ]

    events: list[SchedulerEvent] = [
        SchedulerEvent(
            event_type="objective_set",
            session_name=session_id,
            source="lifecycle",
            payload={
                "objective": objective_text,
                "session_id": session_id,
            },
            metadata={"correlation_id": context.correlation_id},
        ),
    ]

    result = ActionExecutionResult(
        runtime_session_id=session_id,
        action_id=f"obj_{uuid.uuid4().hex[:12]}",
        intent_text=objective_text,
        transport=context.transport,
        correlation_id=context.correlation_id,
    )

    return mutations, events, result


def _execute_ritual(
    state: dict[str, Any],
    request_type: str,
    context: RuntimeContext,
    timestamp: str,
) -> tuple[
    list[dict[str, Any]],
    list[SchedulerEvent],
    RitualExecutionResult | ActionExecutionResult,
]:
    """Dispatch to the correct executor. Raises on unknown type."""
    if request_type == "set_objective":
        return _execute_set_objective(state, context, timestamp)
    elif request_type == "open_day":
        request = _build_open_day_request(context)
        resume_ctx = _resolve_resume_context(context)
        if resume_ctx:
            logger.info(
                "Execution branch: resume_day (previous=%s)",
                resume_ctx.get("session_id", "?"),
            )
            return execute_resume_day(state, request, resume_ctx, timestamp=timestamp)
        return execute_open_day(state, request, timestamp=timestamp)
    elif request_type == "close_day":
        request = _build_close_day_request(context)
        return execute_close_day(state, request, timestamp=timestamp)
    elif request_type == "action":
        request = _build_action_request(context)
        return execute_action(state, request, timestamp=timestamp)
    else:
        raise ValueError(
            f"Unknown request_type: {request_type!r}. "
            f"Valid types: {sorted(_VALID_REQUEST_TYPES)}"
        )


def run_lifecycle(
    state_store: RuntimeStateStore,
    registry: AdapterRegistry,
    context: RuntimeContext,
    request_type: str,
) -> dict[str, Any]:
    """Execute a full lifecycle: ritual → mutations → routing → result.

    Args:
        state_store: Mutable runtime state store.
        registry: AdapterRegistry with registered adapters.
        context: Immutable runtime context for this invocation.
        request_type: "open_day" or "close_day".

    Returns:
        Structured dict with result, dispatch_log, and counts.

    Raises:
        ValueError: If request_type is invalid.
        Any exception from ritual execution propagates (by design).
        Adapter failures are captured in dispatch_log, never raised.
    """
    logger.info(
        "Lifecycle START: request_type=%s session=%s correlation=%s",
        request_type,
        context.runtime_session_id,
        context.correlation_id,
    )

    # Step 0 — Inject session objective + progress into context if available
    if request_type in ("action", "open_day"):
        from umh.runtime_loop.session_registry import get_registry as _get_reg

        _reg = _get_reg()
        _sid = context.runtime_session_id
        _obj = context.objective or _reg.get_objective(_sid)
        _prog = context.progress or _reg.get_progress(_sid)
        if _obj or _prog:
            context = RuntimeContext(
                runtime_session_id=context.runtime_session_id,
                transport=context.transport,
                timestamp=context.timestamp,
                correlation_id=context.correlation_id,
                requested_profile_id=context.requested_profile_id,
                trigger=context.trigger,
                intent_text=context.intent_text,
                previous_session=context.previous_session,
                objective=_obj,
                progress=_prog,
            )

    # Step 1 — Load state snapshot
    state = state_store.snapshot()

    # Step 2 — Execute ritual (raises on failure — by design)
    mutations, events, result = _execute_ritual(
        state, request_type, context, timestamp=context.timestamp
    )

    # Unified ID for logging: plan_id for rituals, action_id for actions
    execution_id = getattr(result, "plan_id", None) or getattr(
        result, "action_id", "unknown"
    )
    logger.info(
        "Executor complete: mutations=%d events=%d execution_id=%s",
        len(mutations),
        len(events),
        execution_id,
    )

    # Step 2b — Update objective progress from emitted events
    if request_type != "set_objective" and events:
        progress_events = _update_objective_progress(
            context.runtime_session_id, events, context.correlation_id
        )
        if progress_events:
            events.extend(progress_events)

    # Step 3 — Apply mutations
    state_store.apply_mutations(mutations)

    # Step 4 — Re-read state after mutation (fresh snapshot for adapters)
    post_mutation_state = state_store.snapshot()

    # Step 5 — Route events through adapters (failures captured, never raised)
    dispatch_log = route_events(events, post_mutation_state, registry)

    logger.info(
        "Lifecycle COMPLETE: dispatched=%d ok=%d errors=%d no_handler=%d",
        len(dispatch_log),
        sum(1 for d in dispatch_log if d["status"] == "ok"),
        sum(1 for d in dispatch_log if d["status"] == "error"),
        sum(1 for d in dispatch_log if d["status"] == "no_handler"),
    )

    # Step 6 — Return structured output
    return {
        "result": result.to_dict(),
        "dispatch_log": dispatch_log,
        "events_count": len(events),
        "mutations_count": len(mutations),
        "state_hash": state_store.compute_state_hash(),
    }
