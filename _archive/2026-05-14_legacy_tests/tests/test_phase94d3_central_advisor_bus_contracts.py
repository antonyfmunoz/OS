"""
Tests for Phase 94D.3 contracts:
- Message bus contracts
- Interface projection contracts
- Advisor session contracts
- Computer-use backend contracts
"""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import json

import pytest

from runtime.substrate.message_bus_contracts import (
    ADVISOR_MESSAGE_TYPES,
    FOUNDER_MESSAGE_TYPES,
    NODE_MESSAGE_TYPES,
    SYSTEM_MESSAGE_TYPES,
    MessageEnvelope,
    MessagePriority,
    MessageStatus,
    MessageType,
    SourceInterface,
)
from runtime.substrate.interface_projection_contracts import (
    ApprovalMode,
    InterfaceCapability,
    InterfaceProjection,
    InterfaceType,
    CLI_VPS,
    DISCORD_CHANNEL,
    WORKSTATION_JARVIS,
)
from runtime.substrate.advisor_session_contracts import (
    AdvisorEventKind,
    AdvisorSessionCommand,
    AdvisorSessionEvent,
    AdvisorSessionState,
    PendingApproval,
)
from runtime.substrate.computer_use_backend_contracts import (
    BackendPolicy,
    BackendSelectionReason,
    ComputerUseBackend,
    DEFAULT_BACKEND_BY_TASK_TYPE,
    requires_approval_for_browser_automation,
    select_backend,
)
from runtime.substrate.work_order_contracts import WorkOrderTaskType


class TestMessageBusContracts:
    def test_message_envelope_serializes(self):
        env = MessageEnvelope(
            message_type=MessageType.APPROVAL_NEEDED,
            sender="node:local_pc_worker",
            recipient="founder",
            payload={"action": "open_folder", "target": "Coaching"},
            work_order_id="WO-001",
            node_id="local_pc_worker",
            priority=MessagePriority.HIGH,
            requires_response=True,
            approval_required=True,
        )
        d = env.to_dict()
        assert d["message_type"] == "APPROVAL_NEEDED"
        assert d["sender"] == "node:local_pc_worker"
        assert d["priority"] == "HIGH"
        assert d["requires_response"] is True
        serialized = json.dumps(d)
        assert len(serialized) > 0

    def test_message_envelope_roundtrip(self):
        env = MessageEnvelope(
            message_type=MessageType.COMMAND,
            sender="founder",
            recipient="advisor",
            payload={"action": "dispatch_work_order", "target": "WO-002"},
            source_interface="cli",
        )
        d = env.to_dict()
        restored = MessageEnvelope.from_dict(d)
        assert restored.message_type == MessageType.COMMAND
        assert restored.sender == "founder"
        assert restored.payload["action"] == "dispatch_work_order"

    def test_approval_request_is_a_message_type(self):
        assert MessageType.APPROVAL_NEEDED in NODE_MESSAGE_TYPES
        assert MessageType.APPROVAL_REQUEST in ADVISOR_MESSAGE_TYPES
        assert MessageType.APPROVAL_RESPONSE in FOUNDER_MESSAGE_TYPES

    def test_cli_is_only_one_source_interface(self):
        interfaces = list(SourceInterface)
        assert SourceInterface.CLI in interfaces
        assert len(interfaces) == 10
        assert SourceInterface.DISCORD in interfaces
        assert SourceInterface.VOICE in interfaces
        assert SourceInterface.MOBILE_APP in interfaces

    def test_stop_pause_resume_serialize(self):
        for msg_type in (MessageType.STOP, MessageType.PAUSE, MessageType.RESUME):
            env = MessageEnvelope(
                message_type=msg_type,
                sender="founder",
                recipient="advisor",
                payload={"scope": "all"},
            )
            d = env.to_dict()
            serialized = json.dumps(d)
            assert msg_type.value in serialized

    def test_node_result_message_serializes(self):
        env = MessageEnvelope(
            message_type=MessageType.RESULT,
            sender="node:local_pc_worker",
            recipient="advisor",
            payload={
                "work_order_id": "WO-001",
                "status": "COMPLETE",
                "summary": "24 folders discovered",
                "items_processed": 87,
            },
            node_id="local_pc_worker",
            work_order_id="WO-001",
        )
        d = env.to_dict()
        assert d["message_type"] == "RESULT"
        assert d["payload"]["items_processed"] == 87
        serialized = json.dumps(d)
        assert "COMPLETE" in serialized

    def test_message_type_categories_are_disjoint(self):
        all_types = (
            FOUNDER_MESSAGE_TYPES
            | ADVISOR_MESSAGE_TYPES
            | NODE_MESSAGE_TYPES
            | SYSTEM_MESSAGE_TYPES
        )
        assert len(all_types) == len(MessageType)

    def test_is_approval_flow(self):
        env = MessageEnvelope(
            message_type=MessageType.APPROVAL_NEEDED,
            sender="node:x",
            recipient="advisor",
            payload={},
        )
        assert env.is_approval_flow() is True

        env2 = MessageEnvelope(
            message_type=MessageType.STATUS_SUMMARY,
            sender="advisor",
            recipient="founder",
            payload={},
        )
        assert env2.is_approval_flow() is False

    def test_is_control_flow(self):
        for t in (MessageType.STOP, MessageType.PAUSE, MessageType.RESUME):
            env = MessageEnvelope(message_type=t, sender="founder", recipient="advisor", payload={})
            assert env.is_control_flow() is True


class TestInterfaceProjectionContracts:
    def test_cli_is_one_interface(self):
        assert CLI_VPS.interface_type == InterfaceType.CLI
        assert DISCORD_CHANNEL.interface_type == InterfaceType.DISCORD
        assert len(InterfaceType) == 8

    def test_workstation_can_observe_computer_use(self):
        assert WORKSTATION_JARVIS.can_observe_computer_use() is True
        assert CLI_VPS.can_observe_computer_use() is False

    def test_discord_has_button_approval(self):
        assert DISCORD_CHANNEL.approval_mode == ApprovalMode.BUTTON
        assert DISCORD_CHANNEL.can_handle_approval() is True

    def test_interface_projection_serializes(self):
        d = CLI_VPS.to_dict()
        assert d["interface_id"] == "cli_vps_main"
        assert d["interface_type"] == "cli"
        serialized = json.dumps(d)
        assert len(serialized) > 0


class TestAdvisorSessionContracts:
    def test_session_states(self):
        assert len(AdvisorSessionState) == 4
        assert AdvisorSessionState.ACTIVE.value == "ACTIVE"

    def test_session_event_serializes(self):
        event = AdvisorSessionEvent(
            kind=AdvisorEventKind.APPROVAL_REQUESTED,
            detail="Node wants to open folder",
            work_order_id="WO-001",
            node_id="local_pc_worker",
        )
        d = event.to_dict()
        assert d["kind"] == "APPROVAL_REQUESTED"
        assert d["work_order_id"] == "WO-001"

    def test_session_event_roundtrip(self):
        event = AdvisorSessionEvent(
            kind=AdvisorEventKind.WORK_ORDER_DISPATCHED,
            detail="Dispatched WO-001 to local",
            session_id="sess_main",
        )
        d = event.to_dict()
        restored = AdvisorSessionEvent.from_dict(d)
        assert restored.kind == AdvisorEventKind.WORK_ORDER_DISPATCHED
        assert restored.detail == "Dispatched WO-001 to local"

    def test_session_command_serializes(self):
        cmd = AdvisorSessionCommand(
            command_type="dispatch_work_order",
            target_node="local_pc_worker",
            payload={"work_order_id": "WO-001"},
            work_order_id="WO-001",
        )
        d = cmd.to_dict()
        assert d["command_type"] == "dispatch_work_order"
        assert d["target_node"] == "local_pc_worker"

    def test_pending_approval_resolve(self):
        approval = PendingApproval(
            approval_id="apr_001",
            work_order_id="WO-001",
            node_id="local_pc_worker",
            action_description="Open Coaching Frameworks folder",
            risk_level="LOW",
        )
        assert approval.resolved is False
        approval.resolve("APPROVE", "cli_vps_main")
        assert approval.resolved is True
        assert approval.resolution == "APPROVE"
        assert approval.resolved_via_interface == "cli_vps_main"
        assert approval.resolved_at is not None


class TestComputerUseBackendContracts:
    def test_gui_computer_use_is_preferred_for_wo001(self):
        default = DEFAULT_BACKEND_BY_TASK_TYPE[WorkOrderTaskType.GOOGLE_WORKSPACE_DISCOVERY]
        assert default == ComputerUseBackend.GUI_COMPUTER_USE

    def test_browser_automation_is_not_default(self):
        for task_type, backend in DEFAULT_BACKEND_BY_TASK_TYPE.items():
            assert backend != ComputerUseBackend.BROWSER_AUTOMATION, (
                f"{task_type} should not default to BROWSER_AUTOMATION"
            )

    def test_manual_fallback_requires_explicit_selection(self):
        policy = select_backend(
            WorkOrderTaskType.GOOGLE_WORKSPACE_DISCOVERY,
            work_order_id="WO-001",
        )
        assert policy.selected_backend == ComputerUseBackend.GUI_COMPUTER_USE
        assert policy.selection_reason == BackendSelectionReason.DEFAULT
        assert policy.browser_automation_allowed is False

    def test_browser_automation_requires_approval(self):
        policy = BackendPolicy(
            work_order_id="WO-001",
            task_type=WorkOrderTaskType.GOOGLE_WORKSPACE_DISCOVERY,
            selected_backend=ComputerUseBackend.BROWSER_AUTOMATION,
            selection_reason=BackendSelectionReason.FOUNDER_OVERRIDE,
            browser_automation_allowed=False,
        )
        assert requires_approval_for_browser_automation(policy) is True

        policy.browser_automation_allowed = True
        assert requires_approval_for_browser_automation(policy) is False

    def test_founder_override_selects_backend(self):
        policy = select_backend(
            WorkOrderTaskType.GOOGLE_WORKSPACE_DISCOVERY,
            work_order_id="WO-001",
            founder_override=ComputerUseBackend.MANUAL_FALLBACK,
        )
        assert policy.selected_backend == ComputerUseBackend.MANUAL_FALLBACK
        assert policy.selection_reason == BackendSelectionReason.FOUNDER_OVERRIDE

    def test_work_order_can_reference_central_advisor_session(self):
        env = MessageEnvelope(
            message_type=MessageType.WORK_ORDER_CLAIMED,
            sender="node:local_pc_worker",
            recipient="advisor",
            payload={
                "work_order_id": "WO-LOCAL-PILOT-GDRIVE-GDOCS-001",
                "execution_backend": "GUI_COMPUTER_USE",
            },
            work_order_id="WO-LOCAL-PILOT-GDRIVE-GDOCS-001",
            target="advisor",
        )
        assert env.target == "advisor"
        assert env.work_order_id == "WO-LOCAL-PILOT-GDRIVE-GDOCS-001"
        assert env.payload["execution_backend"] == "GUI_COMPUTER_USE"

    def test_backend_policy_serializes(self):
        policy = select_backend(
            WorkOrderTaskType.GOOGLE_DOCS_READ_EXPORT,
            work_order_id="WO-001",
        )
        d = policy.to_dict()
        assert d["selected_backend"] == "GUI_COMPUTER_USE"
        restored = BackendPolicy.from_dict(d)
        assert restored.selected_backend == ComputerUseBackend.GUI_COMPUTER_USE
