"""Tests for environment_bridge/local_pull_protocol.py — Phase 96.8A."""

import sys

sys.path.insert(0, "/opt/OS")

import json
import tempfile
import unittest
from pathlib import Path

from core.environment_bridge.local_pull_protocol import (
    LocalPullStatus,
    LocalPullCycleResult,
    discover_remote_packets,
    copy_remote_packet_to_local,
    claim_local_packet,
    mark_packet_running,
    mark_packet_completed,
    mark_packet_failed,
    write_local_result,
    run_local_pull_cycle,
)


class TestNoRemoteQueue(unittest.TestCase):
    def test_force_unavailable_returns_empty(self):
        packets = discover_remote_packets("/nonexistent", force_available=False)
        self.assertEqual(packets, [])

    def test_no_remote_queue_cycle(self):
        result = run_local_pull_cycle(
            remote_outbox="/nonexistent",
            local_inbox="/nonexistent",
            local_results_dir="/nonexistent",
            force_remote_available=False,
        )
        self.assertEqual(result.status, LocalPullStatus.NO_REMOTE_QUEUE)


class TestNoPackets(unittest.TestCase):
    def test_empty_outbox_returns_no_packets(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            outbox = Path(tmpdir) / "outbox"
            outbox.mkdir()
            inbox = Path(tmpdir) / "inbox"
            results = Path(tmpdir) / "results"

            result = run_local_pull_cycle(
                remote_outbox=str(outbox),
                local_inbox=str(inbox),
                local_results_dir=str(results),
            )
            self.assertEqual(result.status, LocalPullStatus.NO_PACKETS)


class TestValidPacketClaimed(unittest.TestCase):
    def test_packet_can_be_claimed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkt_path = Path(tmpdir) / "test.json"
            pkt_path.write_text(
                json.dumps(
                    {
                        "packet_id": "test-001",
                        "status": "approved",
                    }
                )
            )
            claimed = claim_local_packet(str(pkt_path))
            self.assertIsNotNone(claimed)
            self.assertEqual(claimed["status"], "claimed")
            self.assertIn("claimed_at", claimed)


class TestInvalidPacketBlocked(unittest.TestCase):
    def test_nonexistent_packet_returns_none(self):
        claimed = claim_local_packet("/nonexistent/packet.json")
        self.assertIsNone(claimed)

    def test_validator_blocks_invalid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            outbox = Path(tmpdir) / "outbox"
            outbox.mkdir()
            inbox = Path(tmpdir) / "inbox"
            results = Path(tmpdir) / "results"

            pkt = {"packet_id": "bad-001", "status": "approved"}
            (outbox / "bad.json").write_text(json.dumps(pkt))

            def reject_all(pkt_data):
                return False

            result = run_local_pull_cycle(
                remote_outbox=str(outbox),
                local_inbox=str(inbox),
                local_results_dir=str(results),
                validator_fn=reject_all,
            )
            self.assertEqual(result.packets_blocked, 1)
            self.assertEqual(result.packets_executed, 0)


class TestResultWritten(unittest.TestCase):
    def test_result_can_be_written(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_local_result(tmpdir, "test-001", {"status": "completed"})
            self.assertIsNotNone(path)
            self.assertTrue(Path(path).is_file())
            data = json.loads(Path(path).read_text())
            self.assertEqual(data["status"], "completed")
            self.assertIn("written_at", data)


class TestSyncFailure(unittest.TestCase):
    def test_force_sync_failure(self):
        from core.environment_bridge.local_pull_protocol import (
            sync_local_results_to_remote,
        )

        result = sync_local_results_to_remote("/nonexistent", "/nonexistent", force_success=False)
        self.assertEqual(result, [])


class TestPacketStatusUpdates(unittest.TestCase):
    def test_mark_running(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkt_path = Path(tmpdir) / "test.json"
            pkt_path.write_text(json.dumps({"status": "claimed"}))
            self.assertTrue(mark_packet_running(str(pkt_path)))
            data = json.loads(pkt_path.read_text())
            self.assertEqual(data["status"], "running")

    def test_mark_completed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkt_path = Path(tmpdir) / "test.json"
            pkt_path.write_text(json.dumps({"status": "running"}))
            self.assertTrue(mark_packet_completed(str(pkt_path)))
            data = json.loads(pkt_path.read_text())
            self.assertEqual(data["status"], "completed")

    def test_mark_failed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkt_path = Path(tmpdir) / "test.json"
            pkt_path.write_text(json.dumps({"status": "running"}))
            self.assertTrue(mark_packet_failed(str(pkt_path), error="timeout"))
            data = json.loads(pkt_path.read_text())
            self.assertEqual(data["status"], "failed")
            self.assertEqual(data["error"], "timeout")


class TestFullCycle(unittest.TestCase):
    def test_full_cycle_executes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            outbox = Path(tmpdir) / "outbox"
            outbox.mkdir()
            inbox = Path(tmpdir) / "inbox"
            results = Path(tmpdir) / "results"

            pkt = {"packet_id": "cycle-001", "status": "approved"}
            (outbox / "packet.json").write_text(json.dumps(pkt))

            result = run_local_pull_cycle(
                remote_outbox=str(outbox),
                local_inbox=str(inbox),
                local_results_dir=str(results),
            )
            self.assertEqual(result.status, LocalPullStatus.RESULT_WRITTEN)
            self.assertEqual(result.packets_seen, 1)
            self.assertEqual(result.packets_claimed, 1)
            self.assertEqual(result.packets_executed, 1)
            self.assertEqual(result.results_written, 1)


if __name__ == "__main__":
    unittest.main()
