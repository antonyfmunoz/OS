"""Tests for environment_bridge/work_packet.py — Phase 96.8A."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import unittest
from core.environment_bridge.work_packet import (
    WorkPacket,
    WorkPacketRiskLevel,
    WorkPacketStatus,
    WorkPacketExecutionEnvironment,
    build_work_packet,
    work_packet_requires_approval,
    work_packet_is_executable,
    work_packet_targets_local_gui,
    work_packet_blocks_if_unapproved,
    summarize_work_packet,
)


class TestWorkPacketBuilds(unittest.TestCase):
    def test_build_returns_work_packet(self):
        pkt = build_work_packet(
            packet_id="test-001",
            work_order_id="WO-001",
            title="Test Packet",
        )
        self.assertIsInstance(pkt, WorkPacket)
        self.assertEqual(pkt.packet_id, "test-001")

    def test_default_status_is_draft(self):
        pkt = build_work_packet(
            packet_id="test-002",
            work_order_id="WO-001",
            title="Test",
        )
        self.assertEqual(pkt.status, WorkPacketStatus.DRAFT)


class TestUnapprovedHighRiskBlocks(unittest.TestCase):
    def test_high_risk_unapproved_blocks(self):
        pkt = build_work_packet(
            packet_id="test-003",
            work_order_id="WO-001",
            title="High Risk",
            risk_level=WorkPacketRiskLevel.HIGH,
            approval_status=WorkPacketStatus.DRAFT,
        )
        self.assertTrue(work_packet_blocks_if_unapproved(pkt))

    def test_critical_risk_unapproved_blocks(self):
        pkt = build_work_packet(
            packet_id="test-004",
            work_order_id="WO-001",
            title="Critical",
            risk_level=WorkPacketRiskLevel.CRITICAL,
            approval_status=WorkPacketStatus.DRAFT,
        )
        self.assertTrue(work_packet_blocks_if_unapproved(pkt))

    def test_high_risk_approved_does_not_block(self):
        pkt = build_work_packet(
            packet_id="test-005",
            work_order_id="WO-001",
            title="Approved High",
            risk_level=WorkPacketRiskLevel.HIGH,
            approval_status=WorkPacketStatus.APPROVED,
        )
        self.assertFalse(work_packet_blocks_if_unapproved(pkt))


class TestLocalGUITarget(unittest.TestCase):
    def test_local_gui_target_detected(self):
        pkt = build_work_packet(
            packet_id="test-006",
            work_order_id="WO-001",
            title="GUI Packet",
            target_environment=["local_windows_gui"],
        )
        self.assertTrue(work_packet_targets_local_gui(pkt))

    def test_browser_target_detected(self):
        pkt = build_work_packet(
            packet_id="test-007",
            work_order_id="WO-001",
            title="Browser Packet",
            target_environment=["local_browser"],
        )
        self.assertTrue(work_packet_targets_local_gui(pkt))

    def test_vps_target_not_local_gui(self):
        pkt = build_work_packet(
            packet_id="test-008",
            work_order_id="WO-001",
            title="VPS Packet",
            target_environment=["vps"],
        )
        self.assertFalse(work_packet_targets_local_gui(pkt))


class TestMissingBlockedActions(unittest.TestCase):
    def test_no_blocked_actions_not_executable(self):
        pkt = build_work_packet(
            packet_id="test-009",
            work_order_id="WO-001",
            title="No Blocked",
            approval_status=WorkPacketStatus.APPROVED,
            blocked_actions=[],
        )
        self.assertFalse(work_packet_is_executable(pkt))


class TestApprovedSafePacket(unittest.TestCase):
    def test_approved_with_blocked_actions_is_executable(self):
        pkt = build_work_packet(
            packet_id="test-010",
            work_order_id="WO-001",
            title="Safe Packet",
            approval_status=WorkPacketStatus.APPROVED,
            blocked_actions=["credential_capture", "gmail", "screenshot"],
        )
        self.assertTrue(work_packet_is_executable(pkt))


class TestRequiresApproval(unittest.TestCase):
    def test_low_risk_no_approval_needed(self):
        pkt = build_work_packet(
            packet_id="test-011",
            work_order_id="WO-001",
            title="Low Risk",
            risk_level=WorkPacketRiskLevel.LOW,
        )
        self.assertFalse(work_packet_requires_approval(pkt))

    def test_high_risk_needs_approval(self):
        pkt = build_work_packet(
            packet_id="test-012",
            work_order_id="WO-001",
            title="High Risk",
            risk_level=WorkPacketRiskLevel.HIGH,
        )
        self.assertTrue(work_packet_requires_approval(pkt))


class TestSummarize(unittest.TestCase):
    def test_summarize_returns_dict(self):
        pkt = build_work_packet(
            packet_id="test-013",
            work_order_id="WO-001",
            title="Summary Test",
        )
        s = summarize_work_packet(pkt)
        self.assertIsInstance(s, dict)
        self.assertIn("packet_id", s)
        self.assertIn("is_executable", s)
        self.assertIn("targets_local_gui", s)


class TestToDict(unittest.TestCase):
    def test_to_dict_has_all_fields(self):
        pkt = build_work_packet(
            packet_id="test-014",
            work_order_id="WO-001",
            title="Dict Test",
        )
        d = pkt.to_dict()
        self.assertIn("packet_id", d)
        self.assertIn("blocked_actions", d)
        self.assertIn("proof_requirements", d)
        self.assertIn("risk_level", d)


if __name__ == "__main__":
    unittest.main()
