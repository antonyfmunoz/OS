"""Tests for Discord Interface Adapter v1 -- Phase 96.8M + 96.8O.

Tests the interface adapter's command parsing, packet generation,
proof formatting, router integration, and error handling.
Does NOT require a live Discord connection.
"""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import json
import tempfile
import unittest
from pathlib import Path

from eos_ai.interfaces.discord_interface_adapter_v1 import (
    COMMAND_ACTION_MAP,
    SUPPORTED_COMMANDS,
    DiscordInterfaceAdapter,
    build_work_packet,
    build_work_packet_for_router,
    format_proof_summary,
    format_router_result,
    load_config,
    poll_for_proof,
    write_work_packet,
    DEFAULT_CONFIG_PATH,
)
from core.control_plane_router.router_contracts import (
    RouterDecision,
    RouterResult,
    RouterStatus,
    RuntimeProofReference,
    WorkPacket,
)


class TestCommandParsing(unittest.TestCase):
    def test_ping_is_supported(self):
        self.assertIn("!ping", SUPPORTED_COMMANDS)

    def test_chrome_is_supported(self):
        self.assertIn("!chrome", SUPPORTED_COMMANDS)

    def test_status_is_supported(self):
        self.assertIn("!status", SUPPORTED_COMMANDS)

    def test_unknown_command_not_supported(self):
        self.assertNotIn("!hack", SUPPORTED_COMMANDS)
        self.assertNotIn("!shell", SUPPORTED_COMMANDS)
        self.assertNotIn("!exec", SUPPORTED_COMMANDS)


class TestUnsupportedCommandRejection(unittest.TestCase):
    def test_build_packet_returns_none_for_unknown(self):
        self.assertIsNone(build_work_packet("!hack"))
        self.assertIsNone(build_work_packet("!shell"))
        self.assertIsNone(build_work_packet("!arbitrary"))

    def test_build_packet_returns_none_for_empty(self):
        self.assertIsNone(build_work_packet(""))


class TestWorkPacketGeneration(unittest.TestCase):
    def test_ping_packet_has_correct_action(self):
        packet = build_work_packet("!ping")
        self.assertIsNotNone(packet)
        self.assertEqual(packet["action_type"], "ping")
        self.assertIn("request_id", packet)
        self.assertTrue(packet["request_id"].startswith("REQ-PING-"))

    def test_chrome_packet_has_correct_action(self):
        packet = build_work_packet("!chrome")
        self.assertIsNotNone(packet)
        self.assertEqual(packet["action_type"], "open_application_url")
        self.assertEqual(packet["application_id"], "google_chrome_windows")
        self.assertEqual(packet["launch_method"], "direct_executable")

    def test_chrome_packet_uses_safe_url(self):
        packet = build_work_packet("!chrome")
        self.assertEqual(packet["url"], "https://drive.google.com/drive/my-drive")

    def test_chrome_packet_blocks_unsafe_methods(self):
        packet = build_work_packet("!chrome")
        blocked = packet.get("blocked_launch_methods", [])
        self.assertIn("explorer_url", blocked)
        self.assertIn("default_browser", blocked)

    def test_packet_written_to_inbox(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            inbox = Path(tmpdir) / "inbox"
            packet = build_work_packet("!ping")
            path = write_work_packet(packet, inbox)
            self.assertTrue(path.exists())
            data = json.loads(path.read_text())
            self.assertEqual(data["action_type"], "ping")


class TestRuntimeProofFormatting(unittest.TestCase):
    def test_completed_proof_format(self):
        proof = {
            "proof_status": "completed",
            "adapter_status": "pong",
            "adapter_id": "windows_interactive_desktop_relay",
            "request_id": "REQ-PING-001",
            "action_type": "ping",
        }
        summary = format_proof_summary(proof, "!ping")
        self.assertIn("completed", summary)
        self.assertIn("pong", summary)
        self.assertIn("REQ-PING-001", summary)

    def test_timeout_proof_format(self):
        summary = format_proof_summary(None, "!ping")
        self.assertIn("timeout", summary)
        self.assertIn("daemon running", summary)

    def test_proof_with_window_title(self):
        proof = {
            "proof_status": "completed",
            "adapter_status": "completed",
            "adapter_id": "windows_interactive_desktop_relay",
            "request_id": "REQ-CHROME-001",
            "action_type": "open_application_url",
            "evidence": {
                "main_window_title": "Google Drive - Google Chrome",
            },
        }
        summary = format_proof_summary(proof, "!chrome")
        self.assertIn("Google Drive", summary)

    def test_failed_proof_format(self):
        proof = {
            "proof_status": "failed",
            "adapter_status": "rejected",
            "adapter_id": "none",
            "request_id": "REQ-BAD-001",
            "action_type": "unknown",
        }
        summary = format_proof_summary(proof, "!bad")
        self.assertIn("failed", summary)
        self.assertIn("rejected", summary)


class TestProofPolling(unittest.TestCase):
    def test_finds_matching_proof(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proof_dir = Path(tmpdir)
            proof_file = proof_dir / "PROOF-abc123.json"
            proof_file.write_text(
                json.dumps(
                    {
                        "proof_id": "PROOF-abc123",
                        "request_id": "REQ-PING-FIND-001",
                        "proof_status": "completed",
                        "adapter_status": "pong",
                    }
                )
            )
            result = poll_for_proof(
                "REQ-PING-FIND-001", proof_dir, timeout_seconds=2, poll_interval=0.5
            )
            self.assertIsNotNone(result)
            self.assertEqual(result["adapter_status"], "pong")

    def test_returns_none_on_timeout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proof_dir = Path(tmpdir)
            result = poll_for_proof("REQ-MISSING", proof_dir, timeout_seconds=1, poll_interval=0.5)
            self.assertIsNone(result)

    def test_ignores_non_matching_proof(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proof_dir = Path(tmpdir)
            proof_file = proof_dir / "PROOF-other.json"
            proof_file.write_text(
                json.dumps(
                    {
                        "proof_id": "PROOF-other",
                        "request_id": "REQ-OTHER-001",
                        "proof_status": "completed",
                    }
                )
            )
            result = poll_for_proof(
                "REQ-WANT-THIS", proof_dir, timeout_seconds=1, poll_interval=0.5
            )
            self.assertIsNone(result)


class TestMalformedProofHandling(unittest.TestCase):
    def test_malformed_proof_file_skipped(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proof_dir = Path(tmpdir)
            bad_file = proof_dir / "PROOF-bad.json"
            bad_file.write_text("not valid json {{{")
            good_file = proof_dir / "PROOF-good.json"
            good_file.write_text(
                json.dumps(
                    {
                        "proof_id": "PROOF-good",
                        "request_id": "REQ-TARGET-001",
                        "proof_status": "completed",
                    }
                )
            )
            result = poll_for_proof(
                "REQ-TARGET-001", proof_dir, timeout_seconds=2, poll_interval=0.5
            )
            self.assertIsNotNone(result)
            self.assertEqual(result["request_id"], "REQ-TARGET-001")


class TestConfigLoading(unittest.TestCase):
    def test_default_config_loads(self):
        config = load_config(DEFAULT_CONFIG_PATH)
        self.assertIn("discord_token_env_var", config)
        self.assertIn("work_inbox", config)
        self.assertIn("proof_dir", config)

    def test_adapter_initializes_without_token(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "discord_token_env_var": "NONEXISTENT_VAR",
                "allowed_channel_ids": [],
                "work_inbox": f"{tmpdir}/inbox",
                "proof_dir": f"{tmpdir}/proofs",
                "state_dir": f"{tmpdir}/state",
                "poll_interval_seconds": 1,
                "request_timeout_seconds": 5,
                "relay_root": None,
            }
            adapter = DiscordInterfaceAdapter(config)
            self.assertEqual(adapter.token, "")


class TestNoArbitraryExecution(unittest.TestCase):
    def test_no_shell_command(self):
        self.assertIsNone(build_work_packet("!shell"))

    def test_no_exec_command(self):
        self.assertIsNone(build_work_packet("!exec"))

    def test_no_url_command(self):
        self.assertIsNone(build_work_packet("!url"))

    def test_chrome_url_is_hardcoded(self):
        packet = build_work_packet("!chrome")
        self.assertEqual(packet["url"], "https://drive.google.com/drive/my-drive")


class TestCommandActionMap(unittest.TestCase):
    def test_ping_maps_to_ping(self):
        self.assertEqual(COMMAND_ACTION_MAP["!ping"], "ping")

    def test_chrome_maps_to_open_application_url(self):
        self.assertEqual(COMMAND_ACTION_MAP["!chrome"], "open_application_url")

    def test_status_not_in_map(self):
        self.assertNotIn("!status", COMMAND_ACTION_MAP)

    def test_unknown_not_in_map(self):
        self.assertNotIn("!hack", COMMAND_ACTION_MAP)


class TestWorkPacketForRouter(unittest.TestCase):
    def test_ping_builds_work_packet(self):
        wp = build_work_packet_for_router("!ping")
        self.assertIsNotNone(wp)
        self.assertIsInstance(wp, WorkPacket)
        self.assertEqual(wp.action_type, "ping")
        self.assertTrue(wp.packet_id.startswith("REQ-PING-"))
        self.assertEqual(wp.source_interface, "discord_interface_adapter_v1")

    def test_chrome_builds_work_packet(self):
        wp = build_work_packet_for_router("!chrome")
        self.assertIsNotNone(wp)
        self.assertIsInstance(wp, WorkPacket)
        self.assertEqual(wp.action_type, "open_application_url")
        self.assertTrue(wp.packet_id.startswith("REQ-W0-"))

    def test_chrome_payload_has_safe_url(self):
        wp = build_work_packet_for_router("!chrome")
        self.assertEqual(wp.payload["url"], "https://drive.google.com/drive/my-drive")

    def test_unknown_command_returns_none(self):
        self.assertIsNone(build_work_packet_for_router("!hack"))
        self.assertIsNone(build_work_packet_for_router("!shell"))

    def test_empty_command_returns_none(self):
        self.assertIsNone(build_work_packet_for_router(""))

    def test_status_command_returns_none(self):
        self.assertIsNone(build_work_packet_for_router("!status"))


class TestRouterResultFormatting(unittest.TestCase):
    def test_completed_result(self):
        decision = RouterDecision(
            packet_id="PKT-001",
            action_type="ping",
            runtime_target="local_worker_runtime_daemon",
            adapter_selected="windows_interactive_desktop_relay",
            capability_matched="shell_execution",
        )
        proof_ref = RuntimeProofReference(
            proof_id="PROOF-abc",
            proof_status="completed",
            adapter_status="pong",
            request_id="PKT-001",
        )
        result = RouterResult(
            router_status=RouterStatus.COMPLETED,
            router_decision=decision,
            runtime_target="local_worker_runtime_daemon",
            adapter_selected="windows_interactive_desktop_relay",
            runtime_proof_reference=proof_ref,
        )
        summary = format_router_result(result, "!ping")
        self.assertIn("completed", summary)
        self.assertIn("pong", summary)
        self.assertIn("windows_interactive_desktop_relay", summary)

    def test_timeout_result(self):
        result = RouterResult(router_status=RouterStatus.TIMEOUT)
        summary = format_router_result(result, "!ping")
        self.assertIn("timeout", summary)
        self.assertIn("daemon running", summary)

    def test_invalid_packet_result(self):
        result = RouterResult(
            router_status=RouterStatus.INVALID_PACKET,
            error_message="missing packet_id",
        )
        summary = format_router_result(result, "!bad")
        self.assertIn("rejected", summary)
        self.assertIn("missing packet_id", summary)

    def test_no_adapter_result(self):
        result = RouterResult(
            router_status=RouterStatus.NO_ADAPTER,
            error_message="no adapter registered",
        )
        summary = format_router_result(result, "!unknown")
        self.assertIn("no_adapter", summary)

    def test_failed_result_with_error(self):
        decision = RouterDecision(
            packet_id="PKT-F1",
            action_type="ping",
            runtime_target="local_worker_runtime_daemon",
            adapter_selected="windows_interactive_desktop_relay",
            capability_matched="shell_execution",
        )
        result = RouterResult(
            router_status=RouterStatus.FAILED,
            router_decision=decision,
            error_message="adapter exception",
        )
        summary = format_router_result(result, "!ping")
        self.assertIn("failed", summary)
        self.assertIn("adapter exception", summary)


def _write_test_registry(tmpdir: str) -> None:
    """Write a minimal adapter registry fixture into a temp dir."""
    reg_dir = Path(tmpdir) / "data" / "registries"
    reg_dir.mkdir(parents=True, exist_ok=True)
    registry = {
        "workers": {},
        "adapters": {
            "windows_interactive_desktop_relay": {
                "adapter_type": "gui_actuator",
                "environment_type": "local_windows_desktop",
                "authority_domain": "local_gui",
                "message_bus": "filesystem_json",
                "capabilities": [
                    {
                        "capability_id": "ping",
                        "action_type": "ping",
                        "requires_gui": False,
                        "required_authority": "local_shell",
                    }
                ],
            }
        },
    }
    with open(reg_dir / "local_worker_adapter_registry_v1.json", "w") as f:
        json.dump(registry, f)


class TestAdapterInitializesWithRouter(unittest.TestCase):
    def test_adapter_has_router(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_test_registry(tmpdir)
            config = {
                "discord_token_env_var": "NONEXISTENT_VAR",
                "allowed_channel_ids": [],
                "state_dir": f"{tmpdir}/state",
                "request_timeout_seconds": 5,
            }
            adapter = DiscordInterfaceAdapter(config, base_dir=Path(tmpdir))
            self.assertIsNotNone(adapter.router)
            self.assertIsInstance(adapter.router, ControlPlaneRouterV1)

    def test_adapter_router_uses_config_timeout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_test_registry(tmpdir)
            config = {
                "discord_token_env_var": "NONEXISTENT_VAR",
                "allowed_channel_ids": [],
                "state_dir": f"{tmpdir}/state",
                "request_timeout_seconds": 30,
            }
            adapter = DiscordInterfaceAdapter(config, base_dir=Path(tmpdir))
            self.assertEqual(adapter.router.default_timeout, 30)

    def test_write_status_no_attribute_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_test_registry(tmpdir)
            config = {
                "discord_token_env_var": "NONEXISTENT_VAR",
                "allowed_channel_ids": [],
                "state_dir": f"{tmpdir}/state",
                "request_timeout_seconds": 5,
            }
            adapter = DiscordInterfaceAdapter(config, base_dir=Path(tmpdir))
            adapter._write_status("starting")
            status_path = Path(tmpdir) / "state" / "adapter_status.json"
            self.assertTrue(status_path.exists())
            data = json.loads(status_path.read_text())
            self.assertEqual(data["status"], "starting")
            self.assertIn("work_inbox", data)
            self.assertIn("proof_dir", data)


from core.control_plane_router.control_plane_router_v1 import ControlPlaneRouterV1


if __name__ == "__main__":
    unittest.main()
