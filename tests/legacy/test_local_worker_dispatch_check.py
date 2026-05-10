"""Tests for local_worker_dispatch_check.py — Phase 96.7H."""

import sys

sys.path.insert(0, "/opt/OS")

import unittest
from core.adapter_package_manager.local_worker_dispatch_check import (
    LocalWorkerDispatchCheck,
    LocalWorkerDispatchStatus,
    check_local_worker_dispatch_readiness,
    build_w0_001_cu_dispatch_packet,
    local_worker_dispatch_blocks_run,
    summarize_dispatch_check,
)


class TestDispatchCheckBuilds(unittest.TestCase):
    def test_dispatch_check_returns_dataclass(self):
        result = check_local_worker_dispatch_readiness(
            force_station_dir=True,
            force_inbox=True,
            force_outbox=True,
            force_ssh_key=True,
            force_packet=True,
        )
        self.assertIsInstance(result, LocalWorkerDispatchCheck)

    def test_dispatch_ready_when_all_present(self):
        result = check_local_worker_dispatch_readiness(
            force_station_dir=True,
            force_inbox=True,
            force_outbox=True,
            force_ssh_key=True,
            force_packet=True,
        )
        self.assertEqual(result.dispatch_status, LocalWorkerDispatchStatus.DISPATCH_READY)
        self.assertTrue(result.can_dispatch_via_station)
        self.assertTrue(result.can_dispatch_via_ssh)
        self.assertFalse(result.manual_run_required)


class TestDispatchCheckBlockers(unittest.TestCase):
    def test_missing_packet_blocks(self):
        result = check_local_worker_dispatch_readiness(
            force_station_dir=True,
            force_inbox=True,
            force_outbox=True,
            force_ssh_key=True,
            force_packet=False,
        )
        self.assertEqual(result.dispatch_status, LocalWorkerDispatchStatus.PACKET_MISSING)
        self.assertIn("RERUN_PACKET_MISSING", result.blockers)

    def test_missing_inbox_requires_manual(self):
        result = check_local_worker_dispatch_readiness(
            force_station_dir=True,
            force_inbox=False,
            force_outbox=True,
            force_ssh_key=False,
            force_packet=True,
        )
        self.assertEqual(result.dispatch_status, LocalWorkerDispatchStatus.MANUAL_RUN_REQUIRED)
        self.assertTrue(result.manual_run_required)
        self.assertIn("WORKSTATION_INBOX_MISSING", result.blockers)

    def test_missing_outbox_requires_manual(self):
        result = check_local_worker_dispatch_readiness(
            force_station_dir=True,
            force_inbox=True,
            force_outbox=False,
            force_ssh_key=False,
            force_packet=True,
        )
        self.assertEqual(result.dispatch_status, LocalWorkerDispatchStatus.MANUAL_RUN_REQUIRED)
        self.assertIn("WORKSTATION_OUTBOX_MISSING", result.blockers)

    def test_ssh_only_dispatch_ready(self):
        result = check_local_worker_dispatch_readiness(
            force_station_dir=False,
            force_inbox=False,
            force_outbox=False,
            force_ssh_key=True,
            force_packet=True,
        )
        self.assertEqual(result.dispatch_status, LocalWorkerDispatchStatus.DISPATCH_READY)
        self.assertTrue(result.can_dispatch_via_ssh)
        self.assertFalse(result.can_dispatch_via_station)


class TestManualRunRequired(unittest.TestCase):
    def test_manual_instructions_provided(self):
        result = check_local_worker_dispatch_readiness(
            force_station_dir=False,
            force_inbox=False,
            force_outbox=False,
            force_ssh_key=False,
            force_packet=True,
        )
        self.assertTrue(result.manual_run_required)
        self.assertTrue(len(result.manual_instructions) > 0)

    def test_manual_instructions_mention_inbox(self):
        result = check_local_worker_dispatch_readiness(
            force_station_dir=False,
            force_inbox=False,
            force_outbox=False,
            force_ssh_key=False,
            force_packet=True,
        )
        instructions_text = " ".join(result.manual_instructions)
        self.assertIn("inbox", instructions_text)


class TestDispatchPacket(unittest.TestCase):
    def test_build_packet_returns_dict(self):
        packet = build_w0_001_cu_dispatch_packet()
        self.assertIsInstance(packet, dict)
        if "error" not in packet:
            self.assertEqual(packet["run_id"], "W0-001-CU-RERUN-WHILE-PRESENT-001")

    def test_packet_has_tasks(self):
        packet = build_w0_001_cu_dispatch_packet()
        if "error" not in packet:
            self.assertIn("tasks", packet)
            self.assertEqual(len(packet["tasks"]), 2)


class TestBlocksRun(unittest.TestCase):
    def test_packet_missing_blocks(self):
        check = LocalWorkerDispatchCheck()
        check.dispatch_status = LocalWorkerDispatchStatus.PACKET_MISSING
        self.assertTrue(local_worker_dispatch_blocks_run(check))

    def test_dispatch_ready_does_not_block(self):
        check = LocalWorkerDispatchCheck()
        check.dispatch_status = LocalWorkerDispatchStatus.DISPATCH_READY
        self.assertFalse(local_worker_dispatch_blocks_run(check))

    def test_manual_required_does_not_block(self):
        check = LocalWorkerDispatchCheck()
        check.dispatch_status = LocalWorkerDispatchStatus.MANUAL_RUN_REQUIRED
        self.assertFalse(local_worker_dispatch_blocks_run(check))


class TestSummarize(unittest.TestCase):
    def test_summarize_returns_dict(self):
        result = check_local_worker_dispatch_readiness(
            force_station_dir=True,
            force_inbox=True,
            force_outbox=True,
            force_ssh_key=True,
            force_packet=True,
        )
        summary = summarize_dispatch_check(result)
        self.assertIsInstance(summary, dict)
        self.assertIn("dispatch_status", summary)
        self.assertEqual(summary["dispatch_status"], "dispatch_ready")


class TestToDict(unittest.TestCase):
    def test_to_dict_returns_all_fields(self):
        result = check_local_worker_dispatch_readiness(
            force_station_dir=True,
            force_inbox=True,
            force_outbox=True,
            force_ssh_key=True,
            force_packet=True,
        )
        d = result.to_dict()
        self.assertIn("station_dir_exists", d)
        self.assertIn("dispatch_status", d)
        self.assertIn("can_dispatch_via_ssh", d)
        self.assertIn("manual_run_required", d)


if __name__ == "__main__":
    unittest.main()
