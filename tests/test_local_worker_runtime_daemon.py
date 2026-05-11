"""Tests for Local Worker Runtime Daemon v1 -- Phase 96.8L."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

import json
import tempfile
import unittest
from pathlib import Path

from core.runtime.worker_runtime_contracts import ProofStatus
from runtime.substrate.local_worker_runtime_daemon import (
    LocalWorkerRuntimeDaemon,
    load_config,
    DEFAULT_CONFIG_PATH,
)


def _make_test_config(tmpdir: str, **overrides: object) -> dict:
    base = {
        "worker_id": "test_worker",
        "poll_interval_seconds": 1,
        "heartbeat_interval_seconds": 5,
        "relay_root": tmpdir,
        "work_inbox": f"{tmpdir}/inbox",
        "state_dir": f"{tmpdir}/state",
        "proof_dir": f"{tmpdir}/proofs",
        "adapter_registry_path": "data/registries/local_worker_adapter_registry_v1.json",
        "supported_capabilities": ["ping", "open_application_url"],
        "enabled_adapters": ["windows_interactive_desktop_relay"],
        "dry_run": True,
        "version": "v1",
    }
    base.update(overrides)
    return base


def _make_daemon(tmpdir: str, **overrides: object) -> LocalWorkerRuntimeDaemon:
    config = _make_test_config(tmpdir, **overrides)
    return LocalWorkerRuntimeDaemon(config, base_dir=Path(_ROOT))


class TestDaemonLoadsConfig(unittest.TestCase):
    def test_default_config_loads(self):
        config = load_config(DEFAULT_CONFIG_PATH)
        self.assertEqual(config["worker_id"], "local_wsl_worker")
        self.assertIn("ping", config["supported_capabilities"])
        self.assertIn("open_application_url", config["supported_capabilities"])

    def test_daemon_initializes_from_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            daemon = _make_daemon(tmpdir)
            self.assertEqual(daemon.worker_id, "test_worker")
            self.assertTrue(daemon.dry_run)
            self.assertEqual(daemon.descriptor.worker_id, "test_worker")


class TestHeartbeatEmission(unittest.TestCase):
    def test_heartbeat_writes_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            daemon = _make_daemon(tmpdir)
            daemon.ensure_directories()
            daemon.emit_heartbeat()
            hb_path = daemon.state_dir / "heartbeat.json"
            self.assertTrue(hb_path.exists())
            data = json.loads(hb_path.read_text())
            self.assertEqual(data["worker_id"], "test_worker")
            self.assertEqual(data["status"], "alive")
            self.assertIn("ping", data["capabilities_active"])

    def test_runtime_status_writes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            daemon = _make_daemon(tmpdir)
            daemon.ensure_directories()
            daemon.write_runtime_status("running")
            status_path = daemon.state_dir / "runtime_status.json"
            self.assertTrue(status_path.exists())
            data = json.loads(status_path.read_text())
            self.assertEqual(data["status"], "running")


class TestPingRouting(unittest.TestCase):
    def test_ping_routes_to_adapter_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            daemon = _make_daemon(tmpdir)
            daemon.ensure_directories()

            packet = {
                "request_id": "REQ-PING-TEST-001",
                "trace_id": "TRACE-TEST-001",
                "action_type": "ping",
            }
            packet_path = daemon.work_inbox / "REQ-PING-TEST-001.json"
            packet_path.write_text(json.dumps(packet))

            proof = daemon.process_packet(packet_path)
            self.assertIsNotNone(proof)
            self.assertEqual(proof.action_type, "ping")
            self.assertEqual(proof.adapter_id, "windows_interactive_desktop_relay")
            self.assertEqual(proof.proof_status, ProofStatus.COMPLETED)

    def test_ping_proof_persisted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            daemon = _make_daemon(tmpdir)
            daemon.ensure_directories()

            packet = {
                "request_id": "REQ-PING-PERSIST-001",
                "trace_id": "TRACE-PERSIST-001",
                "action_type": "ping",
            }
            packet_path = daemon.work_inbox / "REQ-PING-PERSIST-001.json"
            packet_path.write_text(json.dumps(packet))

            proof = daemon.process_packet(packet_path)
            proof_files = list(daemon.proof_dir.glob("PROOF-*.json"))
            self.assertEqual(len(proof_files), 1)
            data = json.loads(proof_files[0].read_text())
            self.assertEqual(data["action_type"], "ping")
            self.assertEqual(data["proof_status"], "completed")


class TestOpenApplicationUrlRouting(unittest.TestCase):
    def test_chrome_open_routes_to_windows_relay_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            daemon = _make_daemon(tmpdir)
            daemon.ensure_directories()

            packet = {
                "request_id": "REQ-CHROME-TEST-001",
                "trace_id": "TRACE-CHROME-001",
                "action_type": "open_application_url",
                "application_id": "google_chrome_windows",
                "launch_method": "direct_executable",
                "url": "https://drive.google.com",
            }
            packet_path = daemon.work_inbox / "REQ-CHROME-TEST-001.json"
            packet_path.write_text(json.dumps(packet))

            proof = daemon.process_packet(packet_path)
            self.assertIsNotNone(proof)
            self.assertEqual(proof.action_type, "open_application_url")
            self.assertEqual(proof.adapter_id, "windows_interactive_desktop_relay")
            self.assertEqual(proof.proof_status, ProofStatus.COMPLETED)


class TestUnsupportedCapabilityRejected(unittest.TestCase):
    def test_unknown_action_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            daemon = _make_daemon(tmpdir)
            daemon.ensure_directories()

            packet = {
                "request_id": "REQ-UNKNOWN-001",
                "trace_id": "TRACE-UNKNOWN-001",
                "action_type": "screenshot_capture",
            }
            packet_path = daemon.work_inbox / "REQ-UNKNOWN-001.json"
            packet_path.write_text(json.dumps(packet))

            proof = daemon.process_packet(packet_path)
            self.assertIsNotNone(proof)
            self.assertEqual(proof.proof_status, ProofStatus.FAILED)
            self.assertEqual(proof.adapter_status, "rejected")
            self.assertFalse(proof.succeeded)

    def test_rejected_packet_moved_to_failed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            daemon = _make_daemon(tmpdir)
            daemon.ensure_directories()

            packet = {
                "request_id": "REQ-FAIL-MOVE-001",
                "action_type": "forbidden_action",
            }
            packet_path = daemon.work_inbox / "REQ-FAIL-MOVE-001.json"
            packet_path.write_text(json.dumps(packet))

            daemon.process_packet(packet_path)
            self.assertFalse(packet_path.exists())
            failed_files = list(daemon.failed_dir.glob("*.json"))
            self.assertEqual(len(failed_files), 1)


class TestMalformedPacketSurvival(unittest.TestCase):
    def test_invalid_json_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            daemon = _make_daemon(tmpdir)
            daemon.ensure_directories()

            packet_path = daemon.work_inbox / "BAD-PACKET.json"
            packet_path.write_text("this is not json {{{")

            proof = daemon.process_packet(packet_path)
            self.assertIsNone(proof)
            self.assertFalse(packet_path.exists())
            failed_files = list(daemon.failed_dir.glob("*.json"))
            self.assertEqual(len(failed_files), 1)

    def test_empty_json_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            daemon = _make_daemon(tmpdir)
            daemon.ensure_directories()

            packet_path = daemon.work_inbox / "EMPTY-PACKET.json"
            packet_path.write_text("{}")

            proof = daemon.process_packet(packet_path)
            self.assertIsNotNone(proof)
            self.assertEqual(proof.proof_status, ProofStatus.FAILED)

    def test_packet_missing_action_type_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            daemon = _make_daemon(tmpdir)
            daemon.ensure_directories()

            packet = {"request_id": "REQ-NOACTION-001"}
            packet_path = daemon.work_inbox / "REQ-NOACTION-001.json"
            packet_path.write_text(json.dumps(packet))

            proof = daemon.process_packet(packet_path)
            self.assertIsNotNone(proof)
            self.assertEqual(proof.proof_status, ProofStatus.FAILED)


class TestProcessedPacketsMoved(unittest.TestCase):
    def test_successful_packet_moved_to_processed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            daemon = _make_daemon(tmpdir)
            daemon.ensure_directories()

            packet = {
                "request_id": "REQ-MOVE-001",
                "action_type": "ping",
            }
            packet_path = daemon.work_inbox / "REQ-MOVE-001.json"
            packet_path.write_text(json.dumps(packet))

            daemon.process_packet(packet_path)
            self.assertFalse(packet_path.exists())
            processed_files = list(daemon.processed_dir.glob("*.json"))
            self.assertEqual(len(processed_files), 1)


class TestDaemonDirectories(unittest.TestCase):
    def test_ensure_directories_creates_all(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            daemon = _make_daemon(tmpdir)
            daemon.ensure_directories()
            self.assertTrue(daemon.work_inbox.exists())
            self.assertTrue(daemon.state_dir.exists())
            self.assertTrue(daemon.proof_dir.exists())
            self.assertTrue(daemon.processed_dir.exists())
            self.assertTrue(daemon.failed_dir.exists())


if __name__ == "__main__":
    unittest.main()
