"""Stub event builders for the orchestration intent workflow.

These are placeholder implementations that satisfy imports from
workflow_driver.py, trigger_adapters.py, and intent_coordinator.py.
Each function returns a SchedulerEvent with the correct event_type
and all kwargs packed into the payload.

Replace with full implementations when the workflow event schema
is finalized.
"""

from __future__ import annotations

import sys
from typing import Any

from umh.substrate.event_scheduler import SchedulerEvent

_LOG_PREFIX = "[substrate.workflow_events:stub]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _build_event(name: str, **kwargs: Any) -> SchedulerEvent:
    """Shared builder: creates a SchedulerEvent from function name + kwargs."""
    _log(f"{name} called")
    return SchedulerEvent(
        event_type=name,
        session_name=kwargs.pop("session_name", ""),
        source="workflow_events_stub",
        run_id=kwargs.pop("run_id", None),
        payload=dict(kwargs),
    )


# ── Step-level events ────────────────────────────────────────────────────


def build_orch_intent_step_dispatched_event(
    *,
    intent_id: str = "",
    step_index: int = 0,
    step_event_type: str = "",
    step_event_id: str = "",
    session_name: str = "",
    run_id: str | None = None,
    **kwargs: Any,
) -> SchedulerEvent:
    """Observability event: a workflow step was dispatched."""
    return _build_event(
        "orch_intent_step_dispatched",
        intent_id=intent_id,
        step_index=step_index,
        step_event_type=step_event_type,
        step_event_id=step_event_id,
        session_name=session_name,
        run_id=run_id,
        **kwargs,
    )


def build_orch_intent_step_completed_event(
    *,
    intent_id: str = "",
    step_index: int = 0,
    execution_id: str = "",
    session_name: str = "",
    run_id: str | None = None,
    **kwargs: Any,
) -> SchedulerEvent:
    """Observability event: a workflow step completed successfully."""
    return _build_event(
        "orch_intent_step_completed",
        intent_id=intent_id,
        step_index=step_index,
        execution_id=execution_id,
        session_name=session_name,
        run_id=run_id,
        **kwargs,
    )


def build_orch_intent_step_failed_event(
    *,
    intent_id: str = "",
    step_index: int = 0,
    execution_id: str = "",
    failure_reason: str = "",
    session_name: str = "",
    run_id: str | None = None,
    **kwargs: Any,
) -> SchedulerEvent:
    """Observability event: a workflow step failed."""
    return _build_event(
        "orch_intent_step_failed",
        intent_id=intent_id,
        step_index=step_index,
        execution_id=execution_id,
        failure_reason=failure_reason,
        session_name=session_name,
        run_id=run_id,
        **kwargs,
    )


# ── Intent lifecycle events ──────────────────────────────────────────────


def build_orch_intent_created_event(
    *,
    intent_id: str = "",
    intent_type: str = "",
    goal: dict[str, Any] | None = None,
    priority: int = 100,
    session_name: str = "",
    raw_trigger_event_type: str = "",
    raw_trigger_event_id: str = "",
    run_id: str | None = None,
    **kwargs: Any,
) -> SchedulerEvent:
    """Observability event: a new intent was created."""
    return _build_event(
        "orch_intent_created",
        intent_id=intent_id,
        intent_type=intent_type,
        goal=goal or {},
        priority=priority,
        raw_trigger_event_type=raw_trigger_event_type,
        raw_trigger_event_id=raw_trigger_event_id,
        session_name=session_name,
        run_id=run_id,
        **kwargs,
    )


def build_orch_intent_completed_event(
    *,
    intent_id: str = "",
    intent_type: str = "",
    steps_executed: int = 0,
    session_name: str = "",
    run_id: str | None = None,
    **kwargs: Any,
) -> SchedulerEvent:
    """Observability event: an intent completed all steps successfully."""
    return _build_event(
        "orch_intent_completed",
        intent_id=intent_id,
        intent_type=intent_type,
        steps_executed=steps_executed,
        session_name=session_name,
        run_id=run_id,
        **kwargs,
    )


def build_orch_intent_failed_event(
    *,
    intent_id: str = "",
    intent_type: str = "",
    reason: str = "",
    step_index: int = 0,
    session_name: str = "",
    run_id: str | None = None,
    **kwargs: Any,
) -> SchedulerEvent:
    """Observability event: an intent failed."""
    return _build_event(
        "orch_intent_failed",
        intent_id=intent_id,
        intent_type=intent_type,
        reason=reason,
        step_index=step_index,
        session_name=session_name,
        run_id=run_id,
        **kwargs,
    )


def build_orch_intent_cancelled_event(
    *,
    intent_id: str = "",
    intent_type: str = "",
    reason: str = "",
    session_name: str = "",
    run_id: str | None = None,
    **kwargs: Any,
) -> SchedulerEvent:
    """Observability event: an intent was cancelled."""
    return _build_event(
        "orch_intent_cancelled",
        intent_id=intent_id,
        intent_type=intent_type,
        reason=reason,
        session_name=session_name,
        run_id=run_id,
        **kwargs,
    )


def build_orch_intent_rejected_event(
    *,
    attempted_intent_type: str = "",
    reason: str = "",
    source_type: str = "",
    session_name: str = "",
    root_intent_id: str = "",
    parent_intent_id: str = "",
    attempted_chain_depth: int = 0,
    attempted_follow_on_count: int = 0,
    goal_summary: dict[str, Any] | None = None,
    raw_trigger_event_type: str = "",
    raw_trigger_event_id: str = "",
    run_id: str | None = None,
    **kwargs: Any,
) -> SchedulerEvent:
    """Observability event: an intent ingress was rejected by policy."""
    return _build_event(
        "orch_intent_rejected",
        attempted_intent_type=attempted_intent_type,
        reason=reason,
        source_type=source_type,
        root_intent_id=root_intent_id,
        parent_intent_id=parent_intent_id,
        attempted_chain_depth=attempted_chain_depth,
        attempted_follow_on_count=attempted_follow_on_count,
        goal_summary=goal_summary or {},
        raw_trigger_event_type=raw_trigger_event_type,
        raw_trigger_event_id=raw_trigger_event_id,
        session_name=session_name,
        run_id=run_id,
        **kwargs,
    )


# ── Trigger adapter events ───────────────────────────────────────────────


def build_decision_intent_proposed_event(
    *,
    intent_type: str = "",
    goal: dict[str, Any] | None = None,
    priority: int = 100,
    session_name: str = "",
    run_id: str | None = None,
    source_context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> SchedulerEvent:
    """Ingress event: decision engine proposes a new intent."""
    return _build_event(
        "decision_intent_proposed",
        intent_type=intent_type,
        goal=goal or {},
        priority=priority,
        source_context=source_context or {},
        session_name=session_name,
        run_id=run_id,
        **kwargs,
    )


def build_operator_intent_requested_event(
    *,
    intent_type: str = "",
    goal: dict[str, Any] | None = None,
    priority: int = 100,
    session_name: str = "",
    operator_id: str = "",
    run_id: str | None = None,
    source_context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> SchedulerEvent:
    """Ingress event: human operator requests a new intent."""
    return _build_event(
        "operator_intent_requested",
        intent_type=intent_type,
        goal=goal or {},
        priority=priority,
        operator_id=operator_id,
        source_context=source_context or {},
        session_name=session_name,
        run_id=run_id,
        **kwargs,
    )


def build_cron_intent_requested_event(
    *,
    intent_type: str = "",
    goal: dict[str, Any] | None = None,
    priority: int = 100,
    session_name: str = "",
    cron_source: str = "",
    run_id: str | None = None,
    source_context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> SchedulerEvent:
    """Ingress event: cron schedule triggers a new intent."""
    return _build_event(
        "cron_intent_requested",
        intent_type=intent_type,
        goal=goal or {},
        priority=priority,
        cron_source=cron_source,
        source_context=source_context or {},
        session_name=session_name,
        run_id=run_id,
        **kwargs,
    )


def build_result_intent_requested_event(
    *,
    intent_type: str = "",
    goal: dict[str, Any] | None = None,
    priority: int = 100,
    session_name: str = "",
    triggering_intent_id: str = "",
    run_id: str | None = None,
    source_context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> SchedulerEvent:
    """Ingress event: a completed execution triggers a follow-on intent."""
    return _build_event(
        "result_intent_requested",
        intent_type=intent_type,
        goal=goal or {},
        priority=priority,
        triggering_intent_id=triggering_intent_id,
        source_context=source_context or {},
        session_name=session_name,
        run_id=run_id,
        **kwargs,
    )
