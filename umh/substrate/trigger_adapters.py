"""
Trigger adapters — thin ingress translation helpers.

Each function builds one of the four raw ingress SchedulerEvents
with explicit provenance metadata.  No orchestration logic lives here.

Usage:
    from umh.substrate.trigger_adapters import from_decision, from_operator

    event = from_operator(
        intent_type="lifecycle_finalize",
        goal={"session_name": "s1"},
        priority=10,
        session_name="s1",
        operator_id="antony",
    )
    scheduler.emit(event)
"""

from __future__ import annotations

from typing import Any

from umh.substrate.event_scheduler import SchedulerEvent
from umh.substrate.workflow_events import (
    build_cron_intent_requested_event,
    build_decision_intent_proposed_event,
    build_operator_intent_requested_event,
    build_result_intent_requested_event,
)


def from_decision(
    intent_type: str,
    goal: dict[str, Any],
    priority: int = 100,
    session_name: str = "",
    run_id: str | None = None,
    source_context: dict[str, Any] | None = None,
) -> SchedulerEvent:
    """Build a decision_intent_proposed event from the decision engine."""
    return build_decision_intent_proposed_event(
        intent_type=intent_type,
        goal=goal,
        priority=priority,
        session_name=session_name,
        run_id=run_id,
        source_context=source_context,
    )


def from_operator(
    intent_type: str,
    goal: dict[str, Any],
    priority: int = 100,
    session_name: str = "",
    operator_id: str = "",
    run_id: str | None = None,
    source_context: dict[str, Any] | None = None,
) -> SchedulerEvent:
    """Build an operator_intent_requested event from a human operator."""
    return build_operator_intent_requested_event(
        intent_type=intent_type,
        goal=goal,
        priority=priority,
        session_name=session_name,
        operator_id=operator_id,
        run_id=run_id,
        source_context=source_context,
    )


def from_cron(
    intent_type: str,
    goal: dict[str, Any],
    priority: int = 100,
    session_name: str = "",
    cron_source: str = "",
    run_id: str | None = None,
    source_context: dict[str, Any] | None = None,
) -> SchedulerEvent:
    """Build a cron_intent_requested event from a scheduled trigger."""
    return build_cron_intent_requested_event(
        intent_type=intent_type,
        goal=goal,
        priority=priority,
        session_name=session_name,
        cron_source=cron_source,
        run_id=run_id,
        source_context=source_context,
    )


def from_result(
    intent_type: str,
    goal: dict[str, Any],
    priority: int = 100,
    session_name: str = "",
    triggering_intent_id: str = "",
    run_id: str | None = None,
    source_context: dict[str, Any] | None = None,
) -> SchedulerEvent:
    """Build a result_intent_requested event from an execution result."""
    return build_result_intent_requested_event(
        intent_type=intent_type,
        goal=goal,
        priority=priority,
        session_name=session_name,
        triggering_intent_id=triggering_intent_id,
        run_id=run_id,
        source_context=source_context,
    )
