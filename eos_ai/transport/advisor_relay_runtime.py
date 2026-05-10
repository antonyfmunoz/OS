"""
Advisor relay runtime for Phase 94D.4.

Pure/adaptive relay scaffolding that uses message bus contracts from
Phase 94D.3. Creates, correlates, and routes messages between workers,
the advisor session, and interface projections.

No live network transport. This module provides the runtime logic that
future bridge endpoints call.
"""

from __future__ import annotations

from typing import Any

from eos_ai.substrate.message_bus_contracts import (
    MessageEnvelope,
    MessagePriority,
    MessageStatus,
    MessageType,
)
from eos_ai.substrate.worker_node_contracts import (
    WorkerAction,
    WorkerRuntimeState,
    WorkerState,
)


def create_approval_request_message(
    action: WorkerAction,
    worker_state: WorkerRuntimeState,
    work_order_id: str,
    session_id: str = "",
) -> MessageEnvelope:
    """Build an APPROVAL_NEEDED message from a worker action."""
    return MessageEnvelope(
        message_type=MessageType.APPROVAL_NEEDED,
        sender=f"node:{worker_state.worker_id}",
        recipient="advisor",
        target="advisor",
        source_interface="node",
        session_id=session_id,
        payload={
            "approval_request_id": f"apr_{action.action_id}",
            "work_order_id": work_order_id,
            "node_id": worker_state.worker_id,
            "action": action.action_type,
            "target": action.target,
            "description": action.description,
            "risk_level": action.risk_level,
            "backend": action.backend,
            "blocked_until_approved": True,
        },
        priority=MessagePriority.HIGH,
        requires_response=True,
        approval_required=True,
        work_order_id=work_order_id,
        node_id=worker_state.worker_id,
    )


def create_approval_response_message(
    approval_request_id: str,
    decision: str,
    work_order_id: str,
    source_interface: str = "cli",
    reason: str | None = None,
    modifications: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> MessageEnvelope:
    """Build an APPROVAL_RESPONSE message from the founder/advisor."""
    return MessageEnvelope(
        message_type=MessageType.APPROVAL_RESPONSE,
        sender="founder",
        recipient="advisor",
        target="advisor",
        source_interface=source_interface,
        payload={
            "approval_request_id": approval_request_id,
            "decision": decision,
            "reason": reason,
            "modifications": modifications,
        },
        priority=MessagePriority.HIGH,
        work_order_id=work_order_id,
        correlation_id=correlation_id,
    )


def route_message_to_interface(
    message: MessageEnvelope,
    interface_id: str,
) -> MessageEnvelope:
    """Route a message to a specific interface projection.

    Returns a new envelope with target set to the interface.
    Does not perform transport — caller handles delivery.
    """
    return MessageEnvelope(
        message_type=message.message_type,
        sender=message.sender,
        recipient=message.recipient,
        target=f"interface:{interface_id}",
        source_interface=message.source_interface,
        message_id=message.message_id,
        session_id=message.session_id,
        payload=message.payload,
        priority=message.priority,
        requires_response=message.requires_response,
        approval_required=message.approval_required,
        timestamp=message.timestamp,
        correlation_id=message.correlation_id,
        work_order_id=message.work_order_id,
        node_id=message.node_id,
        status=MessageStatus.PENDING,
        audit_tags=message.audit_tags,
    )


def route_message_to_worker(
    message: MessageEnvelope,
    worker_id: str,
) -> MessageEnvelope:
    """Route a message to a specific worker node.

    Returns a new envelope with target set to the worker.
    Does not perform transport — caller handles delivery.
    """
    return MessageEnvelope(
        message_type=message.message_type,
        sender=message.sender,
        recipient=f"node:{worker_id}",
        target=f"node:{worker_id}",
        source_interface=message.source_interface,
        message_id=message.message_id,
        session_id=message.session_id,
        payload=message.payload,
        priority=message.priority,
        requires_response=message.requires_response,
        timestamp=message.timestamp,
        correlation_id=message.correlation_id,
        work_order_id=message.work_order_id,
        node_id=worker_id,
        status=MessageStatus.PENDING,
        audit_tags=message.audit_tags,
    )


def correlate_response_to_request(
    response: MessageEnvelope,
    pending_requests: list[MessageEnvelope],
) -> MessageEnvelope | None:
    """Find the request that a response correlates to."""
    approval_id = response.payload.get("approval_request_id")
    if not approval_id:
        if response.correlation_id:
            return next(
                (r for r in pending_requests if r.message_id == response.correlation_id),
                None,
            )
        return None

    return next(
        (r for r in pending_requests if r.payload.get("approval_request_id") == approval_id),
        None,
    )


def build_worker_status_message(
    worker_state: WorkerRuntimeState,
    work_order_id: str,
    detail: str,
    session_id: str = "",
) -> MessageEnvelope:
    """Build a WORK_ORDER_STATUS message from worker state."""
    return MessageEnvelope(
        message_type=MessageType.WORK_ORDER_STATUS,
        sender=f"node:{worker_state.worker_id}",
        recipient="advisor",
        target="advisor",
        source_interface="node",
        session_id=session_id,
        payload={
            "work_order_id": work_order_id,
            "node_id": worker_state.worker_id,
            "state": worker_state.state.value,
            "detail": detail,
            "actions_completed": worker_state.actions_completed,
            "actions_remaining": worker_state.actions_remaining,
        },
        work_order_id=work_order_id,
        node_id=worker_state.worker_id,
    )


def build_worker_result_message(
    worker_state: WorkerRuntimeState,
    work_order_id: str,
    status: str,
    summary: str,
    result_path: str | None = None,
    session_id: str = "",
) -> MessageEnvelope:
    """Build a RESULT message from worker."""
    return MessageEnvelope(
        message_type=MessageType.RESULT,
        sender=f"node:{worker_state.worker_id}",
        recipient="advisor",
        target="advisor",
        source_interface="node",
        session_id=session_id,
        payload={
            "work_order_id": work_order_id,
            "node_id": worker_state.worker_id,
            "status": status,
            "summary": summary,
            "result_path": result_path,
            "actions_completed": worker_state.actions_completed,
        },
        work_order_id=work_order_id,
        node_id=worker_state.worker_id,
    )


def apply_human_response_to_worker_state(
    response: MessageEnvelope,
    worker_state: WorkerRuntimeState,
) -> WorkerRuntimeState:
    """Apply a human/founder response to the worker state machine."""
    msg_type = response.message_type

    if msg_type == MessageType.APPROVAL_RESPONSE:
        decision = response.payload.get("decision", "DENY")
        if decision == "APPROVE":
            worker_state.transition(WorkerState.EXECUTING)
            worker_state.pending_approval_id = None
        elif decision == "DENY":
            worker_state.transition(WorkerState.BLOCKED)
            worker_state.pending_approval_id = None
        elif decision == "MODIFY":
            worker_state.transition(WorkerState.EXECUTING)
            worker_state.pending_approval_id = None

    elif msg_type == MessageType.STOP:
        worker_state.state = WorkerState.FAILED
        worker_state.error_detail = "Stopped by founder"

    elif msg_type == MessageType.PAUSE:
        worker_state.state = WorkerState.BLOCKED
        worker_state.error_detail = "Paused by founder"

    elif msg_type == MessageType.RESUME:
        if worker_state.state == WorkerState.BLOCKED:
            worker_state.transition(WorkerState.EXECUTING)
            worker_state.error_detail = None

    return worker_state
