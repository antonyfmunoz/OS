"""Migration pin: WorkPacket validation.

Pins §34 item 3: work packets carry risk level, approval status,
blocked actions, and proof requirements. Validation functions
enforce these constraints.
"""

import os
import sys

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")

from execution.environments.work_packet import (
    WorkPacket,
    WorkPacketRiskLevel,
    WorkPacketStatus,
    WorkPacketExecutionEnvironment,
    build_work_packet,
    work_packet_blocks_if_unapproved,
    work_packet_is_executable,
    work_packet_requires_approval,
    work_packet_targets_local_gui,
)

pytestmark = pytest.mark.migration


class TestWorkPacketConstruction:
    def test_build_returns_work_packet(self):
        pkt = build_work_packet(
            packet_id="mig-001",
            work_order_id="WO-MIG",
            title="Migration Test",
        )
        assert isinstance(pkt, WorkPacket)
        assert pkt.packet_id == "mig-001"
        assert pkt.work_order_id == "WO-MIG"

    def test_default_status_is_draft(self):
        pkt = build_work_packet(
            packet_id="mig-002",
            work_order_id="WO-MIG",
            title="Draft Test",
        )
        assert pkt.status == WorkPacketStatus.DRAFT

    def test_default_risk_is_low(self):
        pkt = build_work_packet(
            packet_id="mig-003",
            work_order_id="WO-MIG",
            title="Low Risk Default",
        )
        assert pkt.risk_level == WorkPacketRiskLevel.LOW

    def test_roundtrip_via_to_dict(self):
        pkt = build_work_packet(
            packet_id="mig-004",
            work_order_id="WO-MIG",
            title="Roundtrip",
            risk_level=WorkPacketRiskLevel.HIGH,
            blocked_actions=["delete_all"],
            proof_requirements=["screenshot"],
        )
        d = pkt.to_dict()
        assert d["packet_id"] == "mig-004"
        assert d["risk_level"] == "high"
        assert "delete_all" in d["blocked_actions"]
        assert "screenshot" in d["proof_requirements"]


class TestApprovalGates:
    def test_high_risk_requires_approval(self):
        pkt = build_work_packet(
            packet_id="mig-010",
            work_order_id="WO-MIG",
            title="High",
            risk_level=WorkPacketRiskLevel.HIGH,
        )
        assert work_packet_requires_approval(pkt) is True

    def test_critical_risk_requires_approval(self):
        pkt = build_work_packet(
            packet_id="mig-011",
            work_order_id="WO-MIG",
            title="Critical",
            risk_level=WorkPacketRiskLevel.CRITICAL,
        )
        assert work_packet_requires_approval(pkt) is True

    def test_low_risk_no_approval_needed(self):
        pkt = build_work_packet(
            packet_id="mig-012",
            work_order_id="WO-MIG",
            title="Low",
            risk_level=WorkPacketRiskLevel.LOW,
        )
        assert work_packet_requires_approval(pkt) is False

    def test_medium_risk_no_approval_needed(self):
        pkt = build_work_packet(
            packet_id="mig-013",
            work_order_id="WO-MIG",
            title="Medium",
            risk_level=WorkPacketRiskLevel.MEDIUM,
        )
        assert work_packet_requires_approval(pkt) is False


class TestBlockedActions:
    def test_high_risk_unapproved_blocks(self):
        pkt = build_work_packet(
            packet_id="mig-020",
            work_order_id="WO-MIG",
            title="Blocked",
            risk_level=WorkPacketRiskLevel.HIGH,
            approval_status=WorkPacketStatus.DRAFT,
        )
        assert work_packet_blocks_if_unapproved(pkt) is True

    def test_low_risk_draft_does_not_block(self):
        pkt = build_work_packet(
            packet_id="mig-021",
            work_order_id="WO-MIG",
            title="Not Blocked",
            risk_level=WorkPacketRiskLevel.LOW,
            approval_status=WorkPacketStatus.DRAFT,
        )
        assert work_packet_blocks_if_unapproved(pkt) is False


class TestExecutability:
    def test_approved_with_blocked_actions_is_executable(self):
        pkt = build_work_packet(
            packet_id="mig-030",
            work_order_id="WO-MIG",
            title="Executable",
            approval_status=WorkPacketStatus.APPROVED,
            blocked_actions=["rm_rf"],
        )
        assert work_packet_is_executable(pkt) is True

    def test_unapproved_is_not_executable(self):
        pkt = build_work_packet(
            packet_id="mig-031",
            work_order_id="WO-MIG",
            title="Not Executable",
            approval_status=WorkPacketStatus.DRAFT,
            blocked_actions=["rm_rf"],
        )
        assert work_packet_is_executable(pkt) is False

    def test_approved_without_blocked_actions_not_executable(self):
        pkt = build_work_packet(
            packet_id="mig-032",
            work_order_id="WO-MIG",
            title="Missing blocked_actions",
            approval_status=WorkPacketStatus.APPROVED,
        )
        assert work_packet_is_executable(pkt) is False


class TestLocalGUITargeting:
    def test_windows_gui_is_local_gui(self):
        pkt = build_work_packet(
            packet_id="mig-040",
            work_order_id="WO-MIG",
            title="GUI",
            target_environment=[WorkPacketExecutionEnvironment.LOCAL_WINDOWS_GUI.value],
        )
        assert work_packet_targets_local_gui(pkt) is True

    def test_vps_is_not_local_gui(self):
        pkt = build_work_packet(
            packet_id="mig-041",
            work_order_id="WO-MIG",
            title="VPS",
            target_environment=[WorkPacketExecutionEnvironment.VPS.value],
        )
        assert work_packet_targets_local_gui(pkt) is False
