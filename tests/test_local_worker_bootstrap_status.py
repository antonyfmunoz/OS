"""Tests for environment_bridge/bootstrap_status.py — Phase 96.8B."""

import sys

sys.path.insert(0, "/opt/OS")

import unittest
from core.environment_bridge.bootstrap_status import (
    BootstrapCheckStatus,
    BootstrapStatusReport,
    check_vps_bootstrap_readiness,
    bootstrap_status_blocks_dispatch,
    summarize_bootstrap_status,
)


class TestVPSBootstrapReadiness(unittest.TestCase):
    def test_check_returns_report(self):
        report = check_vps_bootstrap_readiness()
        self.assertIsInstance(report, BootstrapStatusReport)

    def test_vps_queue_exists(self):
        report = check_vps_bootstrap_readiness()
        self.assertTrue(report.vps_queue_exists)

    def test_vps_outbox_exists(self):
        report = check_vps_bootstrap_readiness()
        self.assertTrue(report.vps_outbox_exists)

    def test_packet_found(self):
        report = check_vps_bootstrap_readiness()
        self.assertTrue(report.packet_found)
        self.assertEqual(report.packet_id, "WP-W0-001-CU-RERUN-001")

    def test_packet_is_approved(self):
        report = check_vps_bootstrap_readiness()
        self.assertTrue(report.packet_approved)

    def test_status_is_ready(self):
        report = check_vps_bootstrap_readiness()
        self.assertEqual(report.status, BootstrapCheckStatus.READY)

    def test_does_not_block_dispatch(self):
        report = check_vps_bootstrap_readiness()
        self.assertFalse(bootstrap_status_blocks_dispatch(report))


class TestBootstrapBlocksDispatch(unittest.TestCase):
    def test_missing_queue_blocks(self):
        report = BootstrapStatusReport(
            status=BootstrapCheckStatus.VPS_QUEUE_MISSING,
        )
        self.assertTrue(bootstrap_status_blocks_dispatch(report))

    def test_missing_packet_blocks(self):
        report = BootstrapStatusReport(
            status=BootstrapCheckStatus.PACKET_MISSING,
        )
        self.assertTrue(bootstrap_status_blocks_dispatch(report))

    def test_not_approved_blocks(self):
        report = BootstrapStatusReport(
            status=BootstrapCheckStatus.PACKET_NOT_APPROVED,
        )
        self.assertTrue(bootstrap_status_blocks_dispatch(report))

    def test_ready_does_not_block(self):
        report = BootstrapStatusReport(
            status=BootstrapCheckStatus.READY,
        )
        self.assertFalse(bootstrap_status_blocks_dispatch(report))


class TestSummarize(unittest.TestCase):
    def test_summarize_returns_dict(self):
        report = check_vps_bootstrap_readiness()
        s = summarize_bootstrap_status(report)
        self.assertIsInstance(s, dict)
        self.assertIn("status", s)
        self.assertIn("can_dispatch", s)
        self.assertIn("packet_approved", s)


class TestToDict(unittest.TestCase):
    def test_to_dict_has_fields(self):
        report = check_vps_bootstrap_readiness()
        d = report.to_dict()
        self.assertIn("vps_queue_exists", d)
        self.assertIn("packet_id", d)
        self.assertIn("status", d)


if __name__ == "__main__":
    unittest.main()
