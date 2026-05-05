"""
Event construction helpers for the intent + planning layer.

Centralises observability event construction for:
    - INTENT_CREATED
    - PLAN_CREATED
    - PLAN_STEP_EMITTED
    - INTENT_COMPLETED

These are diagnostic events — they record what happened for tracing
and auditing.  They must never trigger lifecycle state mutations.

Usage:
    from umh.substrate.planner_events import (
        build_intent_created_event,
        build_plan_created_event,
        build_plan_step_emitted_event,
        build_intent_completed_event,
    )
"""

from __future__ import annotations

from typing import Any

from umh.substrate.event_scheduler import SchedulerEvent


def build_intent_created_event(
    intent_id: str,
    intent_type: str,
    goal: dict[str, Any],
    priority: int,
    session_name: str,
    run_id: str | None = None,
) -> SchedulerEvent:
    """Build INTENT_CREATED observability event."""
    return SchedulerEvent(
        event_type="intent_created",
        session_name=session_name,
        source="planner",
        run_id=run_id,
        payload={
            "intent_id": intent_id,
            "intent_type": intent_type,
            "goal": goal,
            "priority": priority,
        },
        metadata={
            "intent_id": intent_id,
            "intent_type": intent_type,
        },
    )


def build_plan_created_event(
    plan_id: str,
    intent_id: str,
    step_count: int,
    session_name: str,
    run_id: str | None = None,
) -> SchedulerEvent:
    """Build PLAN_CREATED observability event."""
    return SchedulerEvent(
        event_type="plan_created",
        session_name=session_name,
        source="planner",
        run_id=run_id,
        payload={
            "plan_id": plan_id,
            "intent_id": intent_id,
            "step_count": step_count,
        },
        metadata={
            "plan_id": plan_id,
            "intent_id": intent_id,
        },
    )


def build_plan_step_emitted_event(
    plan_id: str,
    intent_id: str,
    step_index: int,
    event_type: str,
    session_name: str,
    run_id: str | None = None,
) -> SchedulerEvent:
    """Build PLAN_STEP_EMITTED observability event."""
    return SchedulerEvent(
        event_type="plan_step_emitted",
        session_name=session_name,
        source="planner",
        run_id=run_id,
        payload={
            "plan_id": plan_id,
            "intent_id": intent_id,
            "step_index": step_index,
            "emitted_event_type": event_type,
        },
        metadata={
            "plan_id": plan_id,
            "intent_id": intent_id,
            "step_index": step_index,
        },
    )


def build_intent_completed_event(
    intent_id: str,
    intent_type: str,
    session_name: str,
    steps_executed: int,
    run_id: str | None = None,
) -> SchedulerEvent:
    """Build INTENT_COMPLETED observability event."""
    return SchedulerEvent(
        event_type="intent_completed",
        session_name=session_name,
        source="planner",
        run_id=run_id,
        payload={
            "intent_id": intent_id,
            "intent_type": intent_type,
            "steps_executed": steps_executed,
        },
        metadata={
            "intent_id": intent_id,
            "intent_type": intent_type,
        },
    )
