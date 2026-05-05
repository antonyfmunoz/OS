"""Tests for Phase 94D.5 advisor bridge transport."""

import sys

sys.path.insert(0, "/opt/OS")

import json

import pytest

from eos_ai.substrate.advisor_bridge_transport import (
    BRIDGE_HEALTH_URL,
    BRIDGE_MESSAGE_URL,
    AdvisorMessageFile,
    build_bridge_health_command,
    build_forward_to_local_payload,
    build_local_inbox_path,
    build_local_outbox_path,
    build_mkdir_local_dirs_command,
    build_poll_local_outbox_command,
    build_ssh_health_command,
    build_write_local_inbox_command,
    create_advisor_response_file,
    create_worker_approval_request_file,
)
from eos_ai.substrate.message_bus_contracts import (
    MessageEnvelope,
    MessagePriority,
    MessageType,
)


class TestLocalPaths:
    def test_inbox_path_builds(self):
        path = build_local_inbox_path("umh_core")
        assert "eos_inbox" in path
        assert "umh_core.txt" in path

    def test_inbox_path_custom_session(self):
        path = build_local_inbox_path("test_session")
        assert "test_session.txt" in path

    def test_outbox_path_builds(self):
        path = build_local_outbox_path("WO-TEST-001")
        assert "eos_outbox" in path
        assert "WO-TEST-001" in path

    def test_outbox_path_default(self):
        path = build_local_outbox_path()
        assert "advisor_request.json" in path


class TestApprovalRequestFile:
    def test_serializes(self):
        msg = create_worker_approval_request_file(
            work_order_id="WO-TEST-001",
            action="OPEN_GOOGLE_DRIVE",
            target="antonyfm@empyreanstudios.co",
            description="Open Google Drive for pilot test",
            risk_level="MEDIUM",
        )
        d = msg.to_dict()
        assert d["message_type"] == "APPROVAL_NEEDED"
        assert d["work_order_id"] == "WO-TEST-001"
        assert d["payload"]["action"] == "OPEN_GOOGLE_DRIVE"
        assert d["requires_response"] is True

    def test_json_roundtrip(self):
        msg = create_worker_approval_request_file(
            work_order_id="WO-TEST-002",
            action="read_document",
            target="doc_123",
            description="Read a document",
        )
        json_str = msg.to_json()
        restored = AdvisorMessageFile.from_json(json_str)
        assert restored.work_order_id == "WO-TEST-002"
        assert restored.payload["action"] == "read_document"


class TestApprovalResponseFile:
    def test_approve_serializes(self):
        msg = create_advisor_response_file(
            approval_request_id="apr_abc123",
            decision="APPROVE",
            work_order_id="WO-TEST-001",
            reason="Looks safe",
        )
        d = msg.to_dict()
        assert d["message_type"] == "APPROVAL_RESPONSE"
        assert d["payload"]["decision"] == "APPROVE"
        assert d["payload"]["reason"] == "Looks safe"

    def test_stop_serializes(self):
        msg = create_advisor_response_file(
            approval_request_id="apr_xyz",
            decision="STOP",
            work_order_id="WO-TEST-001",
        )
        assert msg.to_dict()["payload"]["decision"] == "STOP"

    def test_pause_serializes(self):
        msg = create_advisor_response_file(
            approval_request_id="apr_pause",
            decision="PAUSE",
            work_order_id="WO-TEST-001",
        )
        assert msg.to_dict()["payload"]["decision"] == "PAUSE"

    def test_no_response_implies_wait(self):
        msg = create_worker_approval_request_file(
            work_order_id="WO-TEST-001",
            action="test",
            target="test",
            description="test",
        )
        assert msg.requires_response is True
        assert msg.payload["blocked_until_approved"] is True


class TestForwardPayload:
    def test_includes_work_order_id(self):
        msg = create_worker_approval_request_file(
            work_order_id="WO-TEST-001",
            action="test",
            target="test",
            description="test",
        )
        payload = build_forward_to_local_payload(msg)
        assert payload["work_order_id"] == "WO-TEST-001"
        assert payload["transport"] == "http_bridge"
        assert "text" in payload
        assert json.loads(payload["text"])["message_type"] == "APPROVAL_NEEDED"


class TestEnvelopeConversion:
    def test_from_envelope(self):
        env = MessageEnvelope(
            message_type=MessageType.APPROVAL_NEEDED,
            sender="node:local_pc_worker",
            recipient="advisor",
            payload={"test": True},
            priority=MessagePriority.HIGH,
            work_order_id="WO-TEST-001",
        )
        msg_file = AdvisorMessageFile.from_envelope(env)
        assert msg_file.message_type == "APPROVAL_NEEDED"
        assert msg_file.work_order_id == "WO-TEST-001"
        assert msg_file.priority == "HIGH"


class TestCommands:
    def test_ssh_health_command(self):
        cmd = build_ssh_health_command()
        assert "SSH_OK" in cmd
        assert "BatchMode=yes" in cmd

    def test_bridge_health_command(self):
        cmd = build_bridge_health_command()
        assert "curl" in cmd
        assert "8766" in cmd

    def test_poll_outbox_command(self):
        cmd = build_poll_local_outbox_command("WO-001")
        assert "eos_outbox" in cmd
        assert "WO-001" in cmd

    def test_mkdir_command(self):
        cmd = build_mkdir_local_dirs_command()
        assert "eos_inbox" in cmd
        assert "eos_outbox" in cmd
        assert "eos_advisor_messages" in cmd
