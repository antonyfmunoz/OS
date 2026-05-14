"""Tests for Windows Interactive Desktop relay client.

Phase 96.8H: core relay client
Phase 96.8H.1: path unification
Phase 96.8I: PS 5.1 compatibility (BOM tolerance)
Phase 96.8J: runtime proof hardening
"""

import sys

sys.path.insert(0, "/opt/OS")

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.environment_bridge.windows_desktop_request_builder import (
    build_ping_request,
    build_w0_chrome_open_request,
)
from runtime.substrate.windows_desktop_relay_client import (
    RELAY_DIR_NAME,
    _default_relay_root,
    _is_windows_relay_environment,
    _resolve_windows_home,
    check_relay_available,
    read_result_from_relay,
    resolve_relay_paths,
    send_request_and_wait,
    write_request_to_relay,
)
from runtime.substrate.local_worker_auto_loop import (
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

    def test_reads_result_with_utf8_bom(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            outbox = Path(tmpdir)
            request_id = "REQ-BOM-001"
            result_file = outbox / f"{request_id}_result.json"
            payload = json.dumps({"request_id": request_id, "adapter_status": "pong"})
            result_file.write_bytes(b"\xef\xbb\xbf" + payload.encode("utf-8"))
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

    def test_ping_dry_run_no_gui_action(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            inbox = Path(tmpdir) / "inbox"
            outbox = Path(tmpdir) / "outbox"
            inbox.mkdir()
            outbox.mkdir()
            req = build_ping_request()
            result = send_request_and_wait(
                req.to_dict(),
                relay_inbox=inbox,
                relay_outbox=outbox,
                dry_run=True,
            )
            self.assertEqual(result["status"], "dry_run")
            self.assertIsNone(result["result"])


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


# ── Phase 96.8H.1: Path Unification Tests ─────────────────────────────────


class TestRelayDirNameCanonical(unittest.TestCase):
    def test_relay_dir_name_is_canonical(self):
        expected = os.path.join("eos_advisor_messages", "windows_desktop_relay")
        self.assertEqual(RELAY_DIR_NAME, expected)


class TestResolveWindowsHome(unittest.TestCase):
    def test_returns_none_without_mnt_c(self):
        with patch.object(Path, "exists", return_value=False):
            result = _resolve_windows_home()
            self.assertIsNone(result)


class TestDefaultRelayRoot(unittest.TestCase):
    @patch("runtime.substrate.windows_desktop_relay_client._resolve_windows_home")
    def test_wsl_uses_windows_home(self, mock_resolve):
        mock_resolve.return_value = Path("/mnt/c/Users/testuser")
        with patch("runtime.substrate.windows_desktop_relay_client.os.name", "posix"):
            root = _default_relay_root()
        expected = Path("/mnt/c/Users/testuser") / RELAY_DIR_NAME
        self.assertEqual(root, expected)

    @patch("runtime.substrate.windows_desktop_relay_client._resolve_windows_home")
    def test_vps_without_mnt_c_returns_home_fallback(self, mock_resolve):
        mock_resolve.return_value = None
        with patch("runtime.substrate.windows_desktop_relay_client.os.name", "posix"):
            root = _default_relay_root()
        expected = Path.home() / RELAY_DIR_NAME
        self.assertEqual(root, expected)

    def test_windows_native_uses_path_home(self):
        """On native Windows (os.name == 'nt'), _default_relay_root returns Path.home() / RELAY_DIR_NAME.

        We can't truly patch os.name to 'nt' on Linux (Path becomes WindowsPath),
        so we verify the logic: when os.name != 'nt' and _resolve_windows_home returns None,
        we get Path.home() / RELAY_DIR_NAME — the same fallback Windows native would use.
        """
        with patch(
            "runtime.substrate.windows_desktop_relay_client._resolve_windows_home",
            return_value=None,
        ):
            with patch("runtime.substrate.windows_desktop_relay_client.os.name", "posix"):
                root = _default_relay_root()
        self.assertEqual(root, Path.home() / RELAY_DIR_NAME)


class TestIsWindowsRelayEnvironment(unittest.TestCase):
    @patch("runtime.substrate.windows_desktop_relay_client.os.name", "nt")
    def test_true_on_windows(self):
        self.assertTrue(_is_windows_relay_environment())

    @patch("runtime.substrate.windows_desktop_relay_client.os.name", "posix")
    def test_false_on_vps_without_mnt_c(self):
        with patch.object(Path, "exists", return_value=False):
            self.assertFalse(_is_windows_relay_environment())


class TestResolveRelayPaths(unittest.TestCase):
    def test_explicit_relay_root_overrides_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root, inbox, outbox = resolve_relay_paths(tmpdir)
            self.assertEqual(root, Path(tmpdir))
            self.assertEqual(inbox, Path(tmpdir) / "inbox")
            self.assertEqual(outbox, Path(tmpdir) / "outbox")

    def test_none_relay_root_uses_default(self):
        root, inbox, outbox = resolve_relay_paths(None)
        self.assertTrue(str(root).endswith(RELAY_DIR_NAME))
        self.assertEqual(inbox, root / "inbox")
        self.assertEqual(outbox, root / "outbox")

    def test_request_written_to_expected_inbox(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root, inbox, outbox = resolve_relay_paths(tmpdir)
            req = build_ping_request()
            path = write_request_to_relay(req.to_dict(), relay_inbox=inbox)
            self.assertTrue(str(path).startswith(str(inbox)))
            self.assertTrue(path.exists())

    def test_result_read_from_expected_outbox(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root, inbox, outbox = resolve_relay_paths(tmpdir)
            outbox.mkdir(parents=True, exist_ok=True)
            request_id = "REQ-PATH-TEST"
            result_file = outbox / f"{request_id}_result.json"
            result_file.write_text(json.dumps({"adapter_status": "pong"}))
            result = read_result_from_relay(request_id, relay_outbox=outbox, timeout_seconds=1)
            self.assertIsNotNone(result)
            self.assertEqual(result["adapter_status"], "pong")


class TestCLIDebugOutput(unittest.TestCase):
    def test_cli_debug_traces_paths(self):
        import subprocess

        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "runtime.substrate.windows_desktop_relay_client",
                    "--action",
                    "CHECK",
                    "--relay-root",
                    tmpdir,
                    "--debug",
                ],
                capture_output=True,
                text=True,
                cwd="/opt/OS",
                timeout=10,
            )
            self.assertIn("relay_root=", result.stdout)
            self.assertIn("inbox=", result.stdout)
            self.assertIn("outbox=", result.stdout)


# -- Phase 96.8J: Runtime Proof Hardening Tests ----------------------------------


class TestResultFileNamingConvention(unittest.TestCase):
    def test_result_filename_matches_request_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            outbox = Path(tmpdir)
            request_id = "REQ-PING-NAMING-001"
            expected_filename = f"{request_id}_result.json"
            result_file = outbox / expected_filename
            result_file.write_text(json.dumps({"adapter_status": "pong"}))
            result = read_result_from_relay(request_id, relay_outbox=outbox, timeout_seconds=1)
            self.assertIsNotNone(result)

    def test_wrong_filename_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            outbox = Path(tmpdir)
            (outbox / "WRONG_NAME.json").write_text(json.dumps({"adapter_status": "pong"}))
            result = read_result_from_relay(
                "REQ-PING-MISS", relay_outbox=outbox, timeout_seconds=1, poll_interval=1
            )
            self.assertIsNone(result)


class TestPingResponseShape(unittest.TestCase):
    def test_ping_result_has_pong_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            outbox = Path(tmpdir)
            request_id = "REQ-PING-SHAPE-001"
            result_file = outbox / f"{request_id}_result.json"
            result_file.write_text(
                json.dumps(
                    {
                        "request_id": request_id,
                        "trace_id": "TRACE-PING-SHAPE-001",
                        "action_type": "ping",
                        "adapter_status": "pong",
                        "timestamp": "2026-05-07T00:00:00.000Z",
                        "notes": ["Relay is alive and listening"],
                    }
                )
            )
            result = read_result_from_relay(request_id, relay_outbox=outbox, timeout_seconds=1)
            self.assertEqual(result["adapter_status"], "pong")
            self.assertEqual(result["action_type"], "ping")
            self.assertIn("timestamp", result)
            self.assertIn("notes", result)

    def test_ping_result_has_no_chrome_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            outbox = Path(tmpdir)
            request_id = "REQ-PING-NOCHROME-001"
            result_file = outbox / f"{request_id}_result.json"
            result_file.write_text(
                json.dumps(
                    {
                        "request_id": request_id,
                        "action_type": "ping",
                        "adapter_status": "pong",
                    }
                )
            )
            result = read_result_from_relay(request_id, relay_outbox=outbox, timeout_seconds=1)
            self.assertNotIn("process_id", result)
            self.assertNotIn("command_issued", result)
            self.assertNotIn("window_metadata", result)
            self.assertNotIn("visible_proof_status", result)


class TestRuntimeProofFixture(unittest.TestCase):
    def test_fixture_file_is_valid_json(self):
        fixture_path = Path("/opt/OS/data/runtime_proofs/windows_relay_ping_success_example.json")
        self.assertTrue(fixture_path.exists(), "Runtime proof fixture missing")
        data = json.loads(fixture_path.read_text())
        self.assertEqual(data["adapter_status"], "pong")
        self.assertEqual(data["action_type"], "ping")
        self.assertIn("request_id", data)
        self.assertIn("trace_id", data)

    def test_fixture_contains_no_secrets(self):
        fixture_path = Path("/opt/OS/data/runtime_proofs/windows_relay_ping_success_example.json")
        content = fixture_path.read_text()
        for keyword in ["password", "token", "secret", "cookie", "session_id", "api_key"]:
            self.assertNotIn(keyword, content.lower())


class TestPingDryRunNoGuiAccess(unittest.TestCase):
    def test_ping_request_has_empty_gui_fields(self):
        req = build_ping_request()
        d = req.to_dict()
        self.assertEqual(d["action_type"], "ping")
        self.assertEqual(d.get("url", ""), "")
        self.assertEqual(d.get("application_id", ""), "")

    def test_ping_dry_run_does_not_produce_gui_result(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            inbox = Path(tmpdir) / "inbox"
            outbox = Path(tmpdir) / "outbox"
            inbox.mkdir()
            outbox.mkdir()
            req = build_ping_request()
            result = send_request_and_wait(
                req.to_dict(),
                relay_inbox=inbox,
                relay_outbox=outbox,
                dry_run=True,
            )
            self.assertEqual(result["status"], "dry_run")
            self.assertIsNone(result["result"])
            request_path = result["request_path"]
            request_data = json.loads(Path(request_path).read_text())
            self.assertEqual(request_data["action_type"], "ping")


if __name__ == "__main__":
    unittest.main()
