"""
Worker node organism runtime for Phase 94D.4.

Pure functions implementing worker lifecycle logic. No network calls.
No computer-use execution. No side effects.

Workers default to AUTO mode — they proceed through their governed
runtime loop automatically and only pause at required gates.
"""

from __future__ import annotations

from typing import Any

from eos_ai.substrate.governance_gate_contracts import (
    GateDecision,
    GovernancePolicy,
    evaluate_action_gate,
)
from eos_ai.substrate.message_bus_contracts import (
    MessageEnvelope,
    MessagePriority,
    MessageType,
)
from eos_ai.substrate.work_order_contracts import WorkOrder
from eos_ai.substrate.worker_node_contracts import (
    WorkerAction,
    WorkerFeedbackEvent,
    WorkerMode,
    WorkerProfile,
    WorkerRuntimeState,
    WorkerState,
)


def validate_worker_can_claim(
    work_order: WorkOrder, worker_profile: WorkerProfile
) -> tuple[bool, str]:
    """Check if a worker can claim a work order based on capabilities."""
    if worker_profile.mode == WorkerMode.DISABLED:
        return False, "Worker is disabled"
    if worker_profile.mode == WorkerMode.PAUSED:
        return False, "Worker is paused"

    required_caps = _infer_required_capabilities(work_order)
    missing = [cap for cap in required_caps if not worker_profile.supports_capability(cap)]
    if missing:
        return False, f"Missing capabilities: {missing}"

    return True, "Worker can claim this work order"


def _infer_required_capabilities(work_order: WorkOrder) -> list[str]:
    """Infer required capabilities from work order task type."""
    task = work_order.task_type.value
    cap_map: dict[str, list[str]] = {
        "GOOGLE_WORKSPACE_DISCOVERY": ["gui_computer_use", "browser_session"],
        "GOOGLE_DOCS_READ_EXPORT": ["gui_computer_use", "browser_session"],
        "AI_CHAT_EXPORT": ["gui_computer_use", "browser_session"],
        "BROWSER_READ_ONLY_NAVIGATION": ["gui_computer_use", "browser_session"],
        "SCREENSHOT_EVIDENCE_CAPTURE": ["gui_computer_use", "screen_control"],
        "OBSIDIAN_VAULT_READ": ["local_files"],
        "RESULT_WRITEBACK": ["file_storage"],
        "LOCAL_SOURCE_INVENTORY": ["local_files"],
    }
    return cap_map.get(task, [])


def create_worker_execution_plan(
    work_order: WorkOrder, worker_profile: WorkerProfile
) -> list[WorkerAction]:
    """Create a sequence of actions from a work order.

    Returns actions in execution order. Actions that require approval
    are marked with requires_approval=True.
    """
    actions: list[WorkerAction] = []

    for allowed in work_order.allowed_actions:
        requires_approval = (
            work_order.authority_mode.value == "APPROVAL_REQUIRED"
            or allowed in work_order.required_approvals
        )
        actions.append(
            WorkerAction(
                action_type=allowed,
                target="",
                description=f"Execute: {allowed}",
                requires_approval=requires_approval,
                work_order_id=work_order.work_order_id,
            )
        )

    return actions


def next_worker_state(
    current_state: WorkerState,
    event: str,
    mode: WorkerMode = WorkerMode.AUTO,
) -> WorkerState:
    """Determine next worker state given current state and event."""
    transitions: dict[tuple[WorkerState, str], WorkerState] = {
        (WorkerState.BOOTING, "boot_complete"): WorkerState.IDLE,
        (WorkerState.IDLE, "work_available"): WorkerState.CLAIMING_WORK,
        (WorkerState.CLAIMING_WORK, "claimed"): WorkerState.VALIDATING_WORK,
        (WorkerState.CLAIMING_WORK, "claim_failed"): WorkerState.IDLE,
        (WorkerState.VALIDATING_WORK, "valid"): WorkerState.PLANNING,
        (WorkerState.VALIDATING_WORK, "invalid"): WorkerState.BLOCKED,
        (WorkerState.PLANNING, "plan_ready"): WorkerState.EXECUTING,
        (WorkerState.PLANNING, "approval_needed"): WorkerState.WAITING_FOR_ADVISOR_APPROVAL,
        (WorkerState.WAITING_FOR_ADVISOR_APPROVAL, "approved"): WorkerState.EXECUTING,
        (WorkerState.WAITING_FOR_ADVISOR_APPROVAL, "denied"): WorkerState.BLOCKED,
        (WorkerState.EXECUTING, "action_complete"): WorkerState.OBSERVING,
        (WorkerState.EXECUTING, "approval_needed"): WorkerState.WAITING_FOR_ADVISOR_APPROVAL,
        (WorkerState.EXECUTING, "all_done"): WorkerState.REPORTING,
        (WorkerState.EXECUTING, "error"): WorkerState.FAILED,
        (WorkerState.OBSERVING, "continue"): WorkerState.EXECUTING,
        (WorkerState.OBSERVING, "report"): WorkerState.REPORTING,
        (WorkerState.REPORTING, "feedback"): WorkerState.FEEDBACK_SYNC,
        (WorkerState.REPORTING, "complete"): WorkerState.COMPLETE,
        (WorkerState.FEEDBACK_SYNC, "synced"): WorkerState.COMPLETE,
        (WorkerState.BLOCKED, "unblocked"): WorkerState.EXECUTING,
        (WorkerState.BLOCKED, "approval_needed"): WorkerState.WAITING_FOR_ADVISOR_APPROVAL,
    }

    return transitions.get((current_state, event), current_state)


def should_request_advisor_approval(
    action: WorkerAction, governance_policy: GovernancePolicy
) -> bool:
    """Determine if an action requires advisor approval."""
    gate = evaluate_action_gate(action.action_type, governance_policy)
    return gate.decision in (
        GateDecision.REQUIRE_ADVISOR_APPROVAL,
        GateDecision.PAUSE_FOR_HUMAN,
    )


def build_approval_request_for_action(
    action: WorkerAction,
    work_order_id: str,
    worker_state: WorkerRuntimeState,
) -> MessageEnvelope:
    """Build a message bus approval request for an action."""
    return MessageEnvelope(
        message_type=MessageType.APPROVAL_NEEDED,
        sender=f"node:{worker_state.worker_id}",
        recipient="advisor",
        target="advisor",
        payload={
            "approval_request_id": f"apr_{action.action_id}",
            "work_order_id": work_order_id,
            "node_id": worker_state.worker_id,
            "action": action.action_type,
            "target": action.target,
            "description": action.description,
            "risk_level": action.risk_level,
            "backend": action.backend,
        },
        priority=MessagePriority.HIGH,
        requires_response=True,
        approval_required=True,
        work_order_id=work_order_id,
        node_id=worker_state.worker_id,
    )


def apply_advisor_response(
    response: MessageEnvelope, worker_state: WorkerRuntimeState
) -> WorkerRuntimeState:
    """Apply an advisor approval/denial response to worker state."""
    decision = response.payload.get("decision", "DENY")

    if decision == "APPROVE":
        worker_state.transition(WorkerState.EXECUTING)
        worker_state.pending_approval_id = None
    elif decision == "DENY":
        worker_state.transition(WorkerState.BLOCKED)
        worker_state.pending_approval_id = None
        worker_state.error_detail = f"Advisor denied: {response.payload.get('reason', 'no reason')}"
    elif decision == "MODIFY":
        worker_state.transition(WorkerState.EXECUTING)
        worker_state.pending_approval_id = None
    elif decision == "STOP":
        worker_state.state = WorkerState.FAILED
        worker_state.error_detail = "Stopped by advisor"

    return worker_state


def create_worker_feedback_event(
    worker_id: str,
    work_order_id: str,
    event_type: str,
    detail: str,
    data: dict[str, Any] | None = None,
) -> WorkerFeedbackEvent:
    """Create a feedback event for the organism."""
    return WorkerFeedbackEvent(
        worker_id=worker_id,
        work_order_id=work_order_id,
        event_type=event_type,
        detail=detail,
        data=data or {},
    )
