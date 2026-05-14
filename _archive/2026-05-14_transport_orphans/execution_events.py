"""
Event construction helpers for the execution fabric.

Thin builders that produce correctly-typed SchedulerEvents for every
execution lifecycle transition. Centralising construction here prevents
payload-schema drift across the worker, authority, and result handler.

Usage:
    from runtime.transport.execution_events import (
        build_execution_requested_event,
        build_execution_completed_event,
        build_execution_failed_event,
        build_execution_timed_out_event,
        build_execution_rejected_event,
        build_execution_retried_event,
    )
"""

from __future__ import annotations

from runtime.transport.execution_contract import ExecutionRequest, ExecutionResult
from runtime.transport.event_scheduler import SchedulerEvent


def build_execution_requested_event(
    request: ExecutionRequest,
    session_name: str,
    run_id: str | None = None,
) -> SchedulerEvent:
    """Build EXECUTION_REQUESTED event from an ExecutionRequest."""
    return SchedulerEvent(
        event_type="execution_requested",
        session_name=session_name,
        source="execution_authority",
        run_id=run_id,
        payload={"request": request.to_dict()},
        metadata={
            "execution_id": request.execution_id,
            "primitive_name": request.primitive_name,
            "target_node_id": request.target.node_id,
        },
    )


def build_execution_completed_event(
    result: ExecutionResult,
    request_event_id: str,
    session_name: str,
    run_id: str | None = None,
) -> SchedulerEvent:
    """Build EXECUTION_COMPLETED event from an ExecutionResult."""
    return SchedulerEvent(
        event_type="execution_completed",
        session_name=session_name,
        source="execution_worker",
        run_id=run_id,
        payload={
            "result": result.to_dict(),
            "request_event_id": request_event_id,
        },
        metadata={
            "execution_id": result.execution_id,
            "primitive_name": result.primitive_name,
            "node_id": result.node_id,
        },
    )


def build_execution_failed_event(
    result: ExecutionResult,
    request_event_id: str,
    session_name: str,
    failure_reason: str,
    run_id: str | None = None,
) -> SchedulerEvent:
    """Build EXECUTION_FAILED event."""
    return SchedulerEvent(
        event_type="execution_failed",
        session_name=session_name,
        source="execution_worker",
        run_id=run_id,
        payload={
            "result": result.to_dict(),
            "request_event_id": request_event_id,
            "failure_reason": failure_reason,
        },
        metadata={
            "execution_id": result.execution_id,
            "primitive_name": result.primitive_name,
            "node_id": result.node_id,
        },
    )


def build_execution_timed_out_event(
    result: ExecutionResult,
    request_event_id: str,
    session_name: str,
    run_id: str | None = None,
) -> SchedulerEvent:
    """Build EXECUTION_TIMED_OUT event."""
    return SchedulerEvent(
        event_type="execution_timed_out",
        session_name=session_name,
        source="execution_worker",
        run_id=run_id,
        payload={
            "result": result.to_dict(),
            "request_event_id": request_event_id,
            "failure_reason": "timeout",
        },
        metadata={
            "execution_id": result.execution_id,
            "primitive_name": result.primitive_name,
            "node_id": result.node_id,
        },
    )


def build_execution_rejected_event(
    result: ExecutionResult,
    request_event_id: str,
    session_name: str,
    rejection_reason: str,
    run_id: str | None = None,
) -> SchedulerEvent:
    """Build EXECUTION_REJECTED event."""
    return SchedulerEvent(
        event_type="execution_rejected",
        session_name=session_name,
        source="execution_authority",
        run_id=run_id,
        payload={
            "result": result.to_dict(),
            "request_event_id": request_event_id,
            "failure_reason": rejection_reason,
        },
        metadata={
            "execution_id": result.execution_id,
            "primitive_name": result.primitive_name,
            "node_id": result.node_id,
        },
    )


def build_execution_retried_event(
    request: ExecutionRequest,
    original_execution_id: str,
    session_name: str,
    run_id: str | None = None,
) -> SchedulerEvent:
    """Build EXECUTION_RETRIED event (a new request with incremented retry_count)."""
    return SchedulerEvent(
        event_type="execution_retried",
        session_name=session_name,
        source="result_handler",
        run_id=run_id,
        payload={
            "request": request.to_dict(),
            "original_execution_id": original_execution_id,
            "retry_count": request.retry_count,
        },
        metadata={
            "execution_id": request.execution_id,
            "primitive_name": request.primitive_name,
        },
    )
