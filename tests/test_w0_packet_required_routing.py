"""Tests for W0-001 packet routing fields — Phase 96.8D."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import unittest
from execution.environments.w0_packet_builder import (
    W0_001_TARGET_ACCOUNT,
    W0_001_WORKER_MODE,
    W0_001_APPROVAL_ROUTING,
    W0_001_PREFERRED_BACKEND,
    W0_001_REQUIRED_ROUTING_FIELDS,
    build_w0_001_packet,
    w0_001_packet_has_required_routing,
    w0_001_packet_blocks_playwright,
)
from execution.environments.work_packet import (
    WorkPacket,
    WorkPacketRiskLevel,
    WorkPacketStatus,
    build_work_packet,
)
from execution.environments.packet_validator import (
    PacketValidationStatus,
    CU_REQUIRED_BLOCKED_ACTIONS,
    validate_work_packet,
)


class TestBuiltPacketHasRoutingFields(unittest.TestCase):
    def test_generated_packet_has_target_account(self):
        pkt = build_w0_001_packet()
        self.assertEqual(pkt["target_account"], W0_001_TARGET_ACCOUNT)

    def test_generated_packet_has_worker_mode(self):
        pkt = build_w0_001_packet()
        self.assertEqual(pkt["worker_mode"], W0_001_WORKER_MODE)

    def test_generated_packet_has_approval_routing(self):
        pkt = build_w0_001_packet()
        self.assertEqual(pkt["approval_routing"], W0_001_APPROVAL_ROUTING)

    def test_generated_packet_has_preferred_backend(self):
        pkt = build_w0_001_packet()
        self.assertEqual(pkt["preferred_backend"], W0_001_PREFERRED_BACKEND)

    def test_generated_packet_passes_routing_check(self):
        pkt = build_w0_001_packet()
        missing = w0_001_packet_has_required_routing(pkt)
        self.assertEqual(missing, [])

    def test_generated_packet_blocks_playwright(self):
        pkt = build_w0_001_packet()
        self.assertTrue(w0_001_packet_blocks_playwright(pkt))

    def test_generated_packet_has_all_required_fields(self):
        pkt = build_w0_001_packet()
        for field_name in W0_001_REQUIRED_ROUTING_FIELDS:
            self.assertIn(field_name, pkt, f"Missing field: {field_name}")
            self.assertTrue(pkt[field_name], f"Empty field: {field_name}")


class TestMissingRoutingFieldsFail(unittest.TestCase):
    def test_missing_target_account(self):
        pkt = build_w0_001_packet()
        pkt["target_account"] = ""
        missing = w0_001_packet_has_required_routing(pkt)
        self.assertIn("target_account", missing)

    def test_missing_worker_mode(self):
        pkt = build_w0_001_packet()
        pkt["worker_mode"] = ""
        missing = w0_001_packet_has_required_routing(pkt)
        self.assertIn("worker_mode", missing)

    def test_missing_approval_routing(self):
        pkt = build_w0_001_packet()
        pkt["approval_routing"] = ""
        missing = w0_001_packet_has_required_routing(pkt)
        self.assertIn("approval_routing", missing)

    def test_missing_preferred_backend(self):
        pkt = build_w0_001_packet()
        pkt["preferred_backend"] = ""
        missing = w0_001_packet_has_required_routing(pkt)
        self.assertIn("preferred_backend", missing)

    def test_all_four_missing(self):
        pkt = build_w0_001_packet()
        pkt["target_account"] = ""
        pkt["worker_mode"] = ""
        pkt["approval_routing"] = ""
        pkt["preferred_backend"] = ""
        missing = w0_001_packet_has_required_routing(pkt)
        self.assertEqual(len(missing), 4)


class TestPacketValidatorCatchesMissingRouting(unittest.TestCase):
    def _valid_work_packet(self) -> WorkPacket:
        pkt = build_work_packet(
            packet_id="W0-001-test",
            work_order_id="WO-001",
            title="Test CU Packet",
            action_type="cu_rerun_while_present",
            target_environment=["local_windows_gui", "local_browser"],
            risk_level=WorkPacketRiskLevel.HIGH,
            approval_status=WorkPacketStatus.APPROVED,
            founder_confirmation_required=True,
            blocked_actions=list(CU_REQUIRED_BLOCKED_ACTIONS),
            proof_requirements=["drive_visible", "founder_confirmation"],
        )
        pkt.target_account = W0_001_TARGET_ACCOUNT
        pkt.worker_mode = W0_001_WORKER_MODE
        pkt.approval_routing = W0_001_APPROVAL_ROUTING
        pkt.preferred_backend = W0_001_PREFERRED_BACKEND
        pkt.required_environment_adapters = ["environment_bridge"]
        pkt.required_human_approval_adapters = ["founder_visual_confirmation"]
        pkt.required_worker_runtime = "local-windows-worker"
        pkt.required_mastery_categories = ["tool", "environment"]
        pkt.proof_artifact_requirements = ["visible_chrome_launch_proof"]
        return pkt

    def test_valid_packet_passes(self):
        pkt = self._valid_work_packet()
        result = validate_work_packet(pkt)
        self.assertEqual(result.status, PacketValidationStatus.VALID)
        self.assertTrue(result.can_execute)

    def test_missing_target_account_fails(self):
        pkt = self._valid_work_packet()
        pkt.target_account = ""
        result = validate_work_packet(pkt)
        self.assertEqual(result.status, PacketValidationStatus.MISSING_ROUTING_FIELDS)
        self.assertFalse(result.can_execute)

    def test_missing_worker_mode_fails(self):
        pkt = self._valid_work_packet()
        pkt.worker_mode = ""
        result = validate_work_packet(pkt)
        self.assertEqual(result.status, PacketValidationStatus.MISSING_ROUTING_FIELDS)

    def test_missing_approval_routing_fails(self):
        pkt = self._valid_work_packet()
        pkt.approval_routing = ""
        result = validate_work_packet(pkt)
        self.assertEqual(result.status, PacketValidationStatus.MISSING_ROUTING_FIELDS)

    def test_missing_preferred_backend_fails(self):
        pkt = self._valid_work_packet()
        pkt.preferred_backend = ""
        result = validate_work_packet(pkt)
        self.assertEqual(result.status, PacketValidationStatus.MISSING_ROUTING_FIELDS)


class TestPlaywrightBlocking(unittest.TestCase):
    def test_playwright_enabled_fails(self):
        pkt = build_w0_001_packet()
        pkt["playwright_enabled"] = True
        self.assertFalse(w0_001_packet_blocks_playwright(pkt))

    def test_screenshot_enabled_fails(self):
        pkt = build_w0_001_packet()
        pkt["screenshot_capture"] = True
        self.assertFalse(w0_001_packet_blocks_playwright(pkt))

    def test_cdp_enabled_fails(self):
        pkt = build_w0_001_packet()
        pkt["cdp_enabled"] = True
        self.assertFalse(w0_001_packet_blocks_playwright(pkt))


if __name__ == "__main__":
    unittest.main()
