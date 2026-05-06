"""Tests for environment_bridge/packet_validator.py — Phase 96.8A."""

import sys

sys.path.insert(0, "/opt/OS")

import unittest
from core.environment_bridge.work_packet import (
    WorkPacketRiskLevel,
    WorkPacketStatus,
    build_work_packet,
)
from core.environment_bridge.packet_validator import (
    PacketValidationStatus,
    CU_REQUIRED_BLOCKED_ACTIONS,
    validate_work_packet,
    packet_has_required_governance,
    packet_has_required_proof,
    packet_contains_blocked_action_violation,
    packet_validator_blocks_execution,
)


class TestMissingApproval(unittest.TestCase):
    def test_high_risk_unapproved_catches(self):
        pkt = build_work_packet(
            packet_id="val-001",
            work_order_id="WO-001",
            title="Unapproved High",
            action_type="cu_rerun",
            risk_level=WorkPacketRiskLevel.HIGH,
            approval_status=WorkPacketStatus.DRAFT,
            blocked_actions=list(CU_REQUIRED_BLOCKED_ACTIONS),
            proof_requirements=["some_proof"],
        )
        result = validate_work_packet(pkt)
        self.assertEqual(result.status, PacketValidationStatus.MISSING_APPROVAL)
        self.assertFalse(result.can_execute)


class TestExpiredPacket(unittest.TestCase):
    def test_expired_noted(self):
        pkt = build_work_packet(
            packet_id="val-002",
            work_order_id="WO-001",
            title="Expired",
            action_type="cu_rerun",
            approval_status=WorkPacketStatus.APPROVED,
            blocked_actions=list(CU_REQUIRED_BLOCKED_ACTIONS),
            proof_requirements=["some_proof"],
        )
        pkt.expires_at = "2020-01-01T00:00:00+00:00"
        result = validate_work_packet(pkt)
        self.assertTrue(any("expiry" in n.lower() for n in result.notes))


class TestBlockedActionViolation(unittest.TestCase):
    def test_overlap_caught(self):
        pkt = build_work_packet(
            packet_id="val-003",
            work_order_id="WO-001",
            title="Overlap",
            action_type="test",
            approval_status=WorkPacketStatus.APPROVED,
            allowed_actions=["gmail", "open_drive"],
            blocked_actions=list(CU_REQUIRED_BLOCKED_ACTIONS),
            proof_requirements=["some_proof"],
        )
        result = validate_work_packet(pkt)
        self.assertEqual(result.status, PacketValidationStatus.UNSAFE_ACTION)
        self.assertTrue(len(result.safety_errors) > 0)


class TestMissingProofRequirements(unittest.TestCase):
    def test_no_proof_catches(self):
        pkt = build_work_packet(
            packet_id="val-004",
            work_order_id="WO-001",
            title="No Proof",
            action_type="test",
            approval_status=WorkPacketStatus.APPROVED,
            blocked_actions=["credential_capture"],
            proof_requirements=[],
        )
        result = validate_work_packet(pkt)
        self.assertEqual(result.status, PacketValidationStatus.MISSING_PROOF_REQUIREMENTS)


class TestMissingGovernance(unittest.TestCase):
    def test_no_blocked_actions_catches(self):
        pkt = build_work_packet(
            packet_id="val-005",
            work_order_id="WO-001",
            title="No Governance",
            action_type="test",
            approval_status=WorkPacketStatus.APPROVED,
            blocked_actions=[],
        )
        result = validate_work_packet(pkt)
        self.assertEqual(result.status, PacketValidationStatus.MISSING_GOVERNANCE)

    def test_cu_packet_missing_required_blocked_actions(self):
        pkt = build_work_packet(
            packet_id="val-006",
            work_order_id="WO-001",
            title="Partial CU Governance",
            action_type="cu_rerun",
            target_environment=["local_windows_gui"],
            approval_status=WorkPacketStatus.APPROVED,
            blocked_actions=["credential_capture"],
            proof_requirements=["some_proof"],
        )
        result = validate_work_packet(pkt)
        self.assertEqual(result.status, PacketValidationStatus.MISSING_GOVERNANCE)
        self.assertTrue(len(result.governance_errors) > 0)


class TestValidCUPacket(unittest.TestCase):
    def test_full_cu_packet_passes(self):
        pkt = build_work_packet(
            packet_id="val-007",
            work_order_id="WO-001",
            title="Valid CU",
            action_type="cu_rerun",
            target_environment=["local_windows_gui", "local_browser"],
            risk_level=WorkPacketRiskLevel.HIGH,
            approval_status=WorkPacketStatus.APPROVED,
            allowed_actions=["open_google_drive", "read_inventory"],
            blocked_actions=list(CU_REQUIRED_BLOCKED_ACTIONS),
            proof_requirements=["correct_account", "drive_inventory"],
        )
        pkt.required_environment_adapters = ["env-bridge-local-gui"]
        pkt.required_worker_runtime = "local-windows-worker"
        pkt.required_mastery_categories = ["tool", "environment"]
        pkt.proof_artifact_requirements = ["screenshot", "inventory_json"]
        result = validate_work_packet(pkt)
        self.assertEqual(result.status, PacketValidationStatus.VALID)
        self.assertTrue(result.can_execute)


class TestHelpers(unittest.TestCase):
    def test_has_required_governance(self):
        pkt = build_work_packet(
            packet_id="val-008",
            work_order_id="WO-001",
            title="Gov",
            blocked_actions=list(CU_REQUIRED_BLOCKED_ACTIONS),
            target_environment=["local_windows_gui"],
        )
        self.assertTrue(packet_has_required_governance(pkt))

    def test_has_required_proof(self):
        pkt = build_work_packet(
            packet_id="val-009",
            work_order_id="WO-001",
            title="Proof",
            proof_requirements=["account_visible"],
        )
        self.assertTrue(packet_has_required_proof(pkt))

    def test_validator_blocks(self):
        from core.environment_bridge.packet_validator import PacketValidationResult

        r = PacketValidationResult(can_execute=False)
        self.assertTrue(packet_validator_blocks_execution(r))


if __name__ == "__main__":
    unittest.main()
