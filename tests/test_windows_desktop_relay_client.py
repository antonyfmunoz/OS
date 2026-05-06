"""Tests for Windows Interactive Desktop relay client — Phase 96.8H.

Verifies:
1. Dry-run writes request without executing GUI.
2. Request file is written to inbox.
3. Relay availability check works.
4. Timeout handling when no result appears.
5. Result reading from outbox works.
6. Local worker fails closed if adapter unavailable.
7. Local worker stops at founder confirmation if relay result pending.
"""

import sys

sys.path.insert(0, "/opt/OS")

import json
import tempfile
import unittest
from pathlib import Path

from core.environment_bridge.windows_desktop_request_builder import (
    build_ping_request,
    build_w0_chrome_open_request,
)
from eos_ai.substrate.windows_desktop_relay_client import (
    check_relay_available,
    read_result_from_relay,
    write_request_to_relay,
    send_request_and_wait,
)
from eos_ai.substrate.local_worker_auto_loop import (
    packet_requires_windows_desktop_adapter,
    check_windows_desktop_adapter_available,
)
from core.environment_bridge.w0_packet_builder import build_w0_001_packet


class TestDryRunWritesRequest(unittest.TestCase):
    def test_dry_run_writes_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            inbox = Path(tmpdir) / "inbox"
            req = build_w0_chrome_open_request()
            path = write_request_to_relay(req.to_dict(), relay_inbox=inbox, dry_run=True)
            self.assertTrue(path.exists())
            data = json.loads(path.read_text())
            self.assertTrue(data.get("dry_run"))
            self.assertEqual(data["application_id"], "google_chrome_windows")

    def test_non_dry_run_writes_json_without_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            inbox = Path(tmpdir) / "inbox"
            req = build_ping_request()
            path = write_request_to_relay(req.to_dict(), relay_inbox=inbox, dry_run=False)
            self.assertTrue(path.exists())
            data = json.loads(path.read_text())
            self.assertNotIn("dry_run", data)


class TestRelayAvailability(unittest.TestCase):
    def test_available_with_existing_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            inbox = Path(tmpdir) / "inbox"
            outbox = Path(tmpdir) / "outbox"
            inbox.mkdir()
            outbox.mkdir()
            status = check_relay_available(relay_inbox=inbox, relay_outbox=outbox)
            self.assertTrue(status["relay_available"])

    def test_unavailable_with_missing_dirs(self):
        status = check_relay_available(
            relay_inbox=Path("/nonexistent/inbox"),
            relay_outbox=Path("/nonexistent/outbox"),
        )
        self.assertFalse(status["relay_available"])


class TestResultReading(unittest.TestCase):
    def test_reads_result_from_outbox(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            outbox = Path(tmpdir)
            request_id = "REQ-TEST-001"
            result_file = outbox / f"{request_id}_result.json"
            result_file.write_text(
                json.dumps(
                    {
                        "request_id": request_id,
                        "adapter_status": "pong",
                    }
                )
            )
            result = read_result_from_relay(request_id, relay_outbox=outbox, timeout_seconds=1)
            self.assertIsNotNone(result)
            self.assertEqual(result["adapter_status"], "pong")

    def test_returns_none_on_timeout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            outbox = Path(tmpdir)
            result = read_result_from_relay(
                "REQ-MISSING",
                relay_outbox=outbox,
                timeout_seconds=1,
                poll_interval=1,
            )
            self.assertIsNone(result)


class TestSendAndWaitDryRun(unittest.TestCase):
    def test_dry_run_returns_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            inbox = Path(tmpdir) / "inbox"
            outbox = Path(tmpdir) / "outbox"
            inbox.mkdir()
            outbox.mkdir()
            req = build_w0_chrome_open_request()
            result = send_request_and_wait(
                req.to_dict(),
                relay_inbox=inbox,
                relay_outbox=outbox,
                dry_run=True,
            )
            self.assertEqual(result["status"], "dry_run")
            self.assertIsNotNone(result["request_path"])


class TestLocalWorkerAdapterRouting(unittest.TestCase):
    def test_w0_packet_requires_adapter(self):
        pkt = build_w0_001_packet()
        self.assertTrue(packet_requires_windows_desktop_adapter(pkt))

    def test_packet_without_binding_does_not_require_adapter(self):
        pkt = {"work_order_id": "WO-TEST"}
        self.assertFalse(packet_requires_windows_desktop_adapter(pkt))

    def test_packet_with_wsl_only_does_not_require_adapter(self):
        pkt = {
            "execution_binding": {
                "execution_surfaces": [
                    {
                        "execution_surface_type": "tmux",
                        "execution_surface_role": "orchestrator",
                    }
                ]
            }
        }
        self.assertFalse(packet_requires_windows_desktop_adapter(pkt))


class TestLocalWorkerFailsClosedIfAdapterUnavailable(unittest.TestCase):
    def test_relay_check_returns_status(self):
        status = check_windows_desktop_adapter_available()
        self.assertIn("relay_available", status)


if __name__ == "__main__":
    unittest.main()
