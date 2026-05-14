"""Tests for Phase 94D.4 advisor relay runtime."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import pytest

from runtime.substrate.advisor_relay_runtime import (
    apply_human_response_to_worker_state,
    build_worker_result_message,
    build_worker_status_message,
    correlate_response_to_request,
    create_approval_request_message,
    create_approval_response_message,
    route_message_to_interface,
    route_message_to_worker,
)
from runtime.substrate.message_bus_contracts import (
    MessageEnvelope,
    MessagePriority,
    MessageType,
)
from runtime.substrate.worker_node_contracts import (
    WorkerAction,
    WorkerMode,
    WorkerRuntimeState,
    WorkerState,
)


class TestApprovalRequestCreation:
    def test_creates_valid_approval_request(self):
        action = WorkerAction(
            action_type="read_document",
            target="/path/to/doc",
            description="Read Google Doc",
            requires_approval=True,
        )
        state = WorkerRuntimeState(
            worker_id="local_pc_worker",
            state=WorkerState.EXECUTING,
            mode=WorkerMode.AUTO,
        )
        msg = create_approval_request_message(
            action=action,
            worker_state=state,
            work_order_id="wo_test123",
            session_id="sess_1",
        )
        assert msg.message_type == MessageType.APPROVAL_NEEDED
        assert msg.priority == MessagePriority.HIGH
        assert msg.requires_response is True
        assert msg.approval_required is True
        assert msg.payload["work_order_id"] == "wo_test123"
        assert msg.payload["action"] == "read_document"
        assert msg.node_id == "local_pc_worker"

    def test_approval_response_creation(self):
        msg = create_approval_response_message(
            approval_request_id="apr_abc123",
            decision="APPROVE",
            work_order_id="wo_test",
            source_interface="discord",
            reason="Looks safe",
        )
        assert msg.message_type == MessageType.APPROVAL_RESPONSE
        assert msg.sender == "founder"
        assert msg.payload["decision"] == "APPROVE"
        assert msg.payload["reason"] == "Looks safe"


class TestMessageRouting:
    def test_route_to_interface(self):
        original = MessageEnvelope(
            message_type=MessageType.APPROVAL_NEEDED,
            sender="node:w1",
            recipient="advisor",
            payload={"test": True},
            priority=MessagePriority.HIGH,
        )
        routed = route_message_to_interface(original, "discord_channel")
        assert routed.target == "interface:discord_channel"
        assert routed.payload == {"test": True}
        assert routed.message_id == original.message_id

    def test_route_to_worker(self):
        original = MessageEnvelope(
            message_type=MessageType.APPROVAL_RESPONSE,
            sender="founder",
            recipient="advisor",
            payload={"decision": "APPROVE"},
        )
        routed = route_message_to_worker(original, "local_pc_worker")
        assert routed.target == "node:local_pc_worker"
        assert routed.recipient == "node:local_pc_worker"
        assert routed.node_id == "local_pc_worker"


class TestCorrelation:
    def test_correlates_by_approval_id(self):
        request = MessageEnvelope(
            message_type=MessageType.APPROVAL_NEEDED,
            sender="node:w1",
            recipient="advisor",
            payload={"approval_request_id": "apr_abc"},
        )
        response = MessageEnvelope(
            message_type=MessageType.APPROVAL_RESPONSE,
            sender="founder",
            recipient="advisor",
            payload={"approval_request_id": "apr_abc", "decision": "APPROVE"},
        )
        result = correlate_response_to_request(response, [request])
        assert result is not None
        assert result.message_id == request.message_id

    def test_correlates_by_correlation_id(self):
        request = MessageEnvelope(
            message_type=MessageType.QUESTION,
            sender="advisor",
            recipient="founder",
            payload={"text": "Confirm?"},
        )
        response = MessageEnvelope(
            message_type=MessageType.CLARIFICATION_RESPONSE,
            sender="founder",
            recipient="advisor",
            payload={"answer": "yes"},
            correlation_id=request.message_id,
        )
        result = correlate_response_to_request(response, [request])
        assert result is not None

    def test_no_match_returns_none(self):
        response = MessageEnvelope(
            message_type=MessageType.APPROVAL_RESPONSE,
            sender="founder",
            recipient="advisor",
            payload={"approval_request_id": "apr_nonexistent"},
        )
        result = correlate_response_to_request(response, [])
        assert result is None


class TestWorkerStatusMessages:
    def test_build_status_message(self):
        state = WorkerRuntimeState(
            worker_id="w1",
            state=WorkerState.EXECUTING,
            mode=WorkerMode.AUTO,
            actions_completed=2,
            actions_remaining=3,
        )
        msg = build_worker_status_message(state, "wo_test", "Processing step 3")
        assert msg.message_type == MessageType.WORK_ORDER_STATUS
        assert msg.payload["actions_completed"] == 2
        assert msg.payload["actions_remaining"] == 3
        assert msg.payload["detail"] == "Processing step 3"

    def test_build_result_message(self):
        state = WorkerRuntimeState(
            worker_id="w1",
            state=WorkerState.COMPLETE,
            mode=WorkerMode.AUTO,
            actions_completed=5,
        )
        msg = build_worker_result_message(
            state, "wo_test", "success", "All docs exported", "/results/export.json"
        )
        assert msg.message_type == MessageType.RESULT
        assert msg.payload["status"] == "success"
        assert msg.payload["result_path"] == "/results/export.json"


class TestHumanResponseApplication:
    def test_approve_unblocks_worker(self):
        state = WorkerRuntimeState(
            worker_id="w1",
            state=WorkerState.WAITING_FOR_ADVISOR_APPROVAL,
            mode=WorkerMode.AUTO,
            pending_approval_id="apr_test",
        )
        response = MessageEnvelope(
            message_type=MessageType.APPROVAL_RESPONSE,
            sender="founder",
            recipient="advisor",
            payload={"decision": "APPROVE"},
        )
        result = apply_human_response_to_worker_state(response, state)
        assert result.state == WorkerState.EXECUTING
        assert result.pending_approval_id is None

    def test_stop_terminates_worker(self):
        state = WorkerRuntimeState(
            worker_id="w1",
            state=WorkerState.EXECUTING,
            mode=WorkerMode.AUTO,
        )
        response = MessageEnvelope(
            message_type=MessageType.STOP,
            sender="founder",
            recipient="node:w1",
            payload={},
        )
        result = apply_human_response_to_worker_state(response, state)
        assert result.state == WorkerState.FAILED
        assert "stopped" in result.error_detail.lower()

    def test_pause_blocks_worker(self):
        state = WorkerRuntimeState(
            worker_id="w1",
            state=WorkerState.EXECUTING,
            mode=WorkerMode.AUTO,
        )
        response = MessageEnvelope(
            message_type=MessageType.PAUSE,
            sender="founder",
            recipient="node:w1",
            payload={},
        )
        result = apply_human_response_to_worker_state(response, state)
        assert result.state == WorkerState.BLOCKED

    def test_resume_unblocks_paused_worker(self):
        state = WorkerRuntimeState(
            worker_id="w1",
            state=WorkerState.BLOCKED,
            mode=WorkerMode.AUTO,
            error_detail="Paused by founder",
        )
        response = MessageEnvelope(
            message_type=MessageType.RESUME,
            sender="founder",
            recipient="node:w1",
            payload={},
        )
        result = apply_human_response_to_worker_state(response, state)
        assert result.state == WorkerState.EXECUTING
        assert result.error_detail is None
