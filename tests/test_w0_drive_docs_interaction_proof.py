"""Tests for W0 Drive/Docs interaction proof -- Phase 96.8R.

Validates safe document targeting, forbidden action blocking,
router integration, proof artifact schema, and absence of
extraction/memory fields.
"""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

import json
import unittest
from pathlib import Path

from core.control_plane_router.control_plane_router_v1 import (
    ACTION_CAPABILITY_MAP,
    ControlPlaneRouterV1,
)
from core.control_plane_router.router_contracts import (
    ALLOWED_ACTION_TYPES,
    CapabilityType,
    RouterStatus,
    WorkPacket,
)
from core.runtime.adapter_registry_contracts import AdapterRegistry
from eos_ai.interfaces.discord_interface_adapter_v1 import (
    COMMAND_ACTION_MAP,
    SUPPORTED_COMMANDS,
    build_work_packet_for_router,
)

REGISTRY_PATH = Path(_ROOT) / "data" / "registries" / "local_worker_adapter_registry_v1.json"
INTERACTION_CONFIG_PATH = Path(_ROOT) / "config" / "w0_drive_docs_interaction_proof_v1.json"
PROOF_DIR = Path(_ROOT) / "data" / "runtime" / "w0_interaction_proofs"

SAFE_DOC_URL = "https://docs.google.com/document/d/1_test_doc_placeholder/edit"

FORBIDDEN_ACTIONS = [
    "read_document_contents",
    "copy_text",
    "download_file",
    "upload_file",
    "take_screenshot",
    "capture_ocr",
    "mutate_drive",
    "mutate_docs",
    "extract_cookies",
    "extract_tokens",
    "promote_memory",
]


class TestDocCommandRegistered(unittest.TestCase):
    def test_doc_in_supported_commands(self):
        self.assertIn("!doc", SUPPORTED_COMMANDS)

    def test_doc_maps_to_drive_open_safe_test_doc(self):
        self.assertEqual(COMMAND_ACTION_MAP["!doc"], "drive_open_safe_test_doc")

    def test_action_type_allowed(self):
        self.assertIn("drive_open_safe_test_doc", ALLOWED_ACTION_TYPES)

    def test_capability_map_has_entry(self):
        self.assertIn("drive_open_safe_test_doc", ACTION_CAPABILITY_MAP)
        cap = ACTION_CAPABILITY_MAP["drive_open_safe_test_doc"]
        self.assertEqual(cap.capability_type, CapabilityType.WINDOWS_GUI_EXECUTION)
        self.assertTrue(cap.requires_gui)


class TestSafeDocWorkPacket(unittest.TestCase):
    def test_builds_work_packet(self):
        wp = build_work_packet_for_router("!doc", safe_doc_url=SAFE_DOC_URL)
        self.assertIsNotNone(wp)
        self.assertEqual(wp.action_type, "drive_open_safe_test_doc")
        self.assertTrue(wp.packet_id.startswith("REQ-W0-DOC-"))

    def test_uses_configured_safe_url(self):
        wp = build_work_packet_for_router("!doc", safe_doc_url=SAFE_DOC_URL)
        self.assertEqual(wp.payload["url"], SAFE_DOC_URL)

    def test_defaults_to_drive_homepage(self):
        wp = build_work_packet_for_router("!doc")
        self.assertEqual(wp.payload["url"], "https://drive.google.com/drive/my-drive")

    def test_no_secret_capture(self):
        wp = build_work_packet_for_router("!doc", safe_doc_url=SAFE_DOC_URL)
        self.assertTrue(wp.payload["no_secret_capture"])

    def test_no_mutation(self):
        wp = build_work_packet_for_router("!doc", safe_doc_url=SAFE_DOC_URL)
        self.assertTrue(wp.payload["no_mutation"])

    def test_uses_direct_executable(self):
        wp = build_work_packet_for_router("!doc", safe_doc_url=SAFE_DOC_URL)
        self.assertEqual(wp.payload["launch_method"], "direct_executable")

    def test_blocked_launch_methods(self):
        wp = build_work_packet_for_router("!doc", safe_doc_url=SAFE_DOC_URL)
        blocked = wp.payload.get("blocked_launch_methods", [])
        self.assertIn("explorer_url", blocked)
        self.assertIn("default_browser", blocked)


class TestArbitraryUrlRejected(unittest.TestCase):
    def test_unknown_commands_rejected(self):
        self.assertIsNone(build_work_packet_for_router("!hack"))
        self.assertIsNone(build_work_packet_for_router("!url"))
        self.assertIsNone(build_work_packet_for_router("!exec"))

    def test_doc_command_does_not_accept_arbitrary_action(self):
        wp = build_work_packet_for_router("!doc")
        self.assertEqual(wp.action_type, "drive_open_safe_test_doc")
        self.assertNotEqual(wp.action_type, "open_arbitrary_url")


class TestForbiddenActionsBlocked(unittest.TestCase):
    def test_no_forbidden_actions_in_payload(self):
        wp = build_work_packet_for_router("!doc", safe_doc_url=SAFE_DOC_URL)
        payload_str = json.dumps(wp.payload).lower()
        for action in FORBIDDEN_ACTIONS:
            self.assertNotIn(
                action,
                payload_str,
                f"forbidden action '{action}' found in payload",
            )

    def test_no_extraction_fields(self):
        wp = build_work_packet_for_router("!doc", safe_doc_url=SAFE_DOC_URL)
        payload = wp.payload
        self.assertNotIn("document_content", payload)
        self.assertNotIn("extracted_text", payload)
        self.assertNotIn("file_contents", payload)
        self.assertNotIn("screenshot_path", payload)

    def test_no_memory_promotion_fields(self):
        wp = build_work_packet_for_router("!doc", safe_doc_url=SAFE_DOC_URL)
        payload = wp.payload
        self.assertNotIn("promote_to_memory", payload)
        self.assertNotIn("memory_target", payload)
        self.assertNotIn("ingest", payload)


class TestRouterResolvesDocAction(unittest.TestCase):
    def setUp(self):
        self.registry = AdapterRegistry.from_json_file(REGISTRY_PATH)
        self.router = ControlPlaneRouterV1(registry=self.registry, base_dir=Path(_ROOT))

    def test_dry_run_routes_doc(self):
        wp = WorkPacket(
            packet_id="PKT-DOC-TEST-001",
            action_type="drive_open_safe_test_doc",
        )
        result = self.router.route_dry_run(wp)
        self.assertEqual(result.router_status, RouterStatus.ROUTED)
        self.assertEqual(result.adapter_selected, "windows_interactive_desktop_relay")
        self.assertEqual(result.runtime_target, "local_worker_runtime_daemon")

    def test_capability_matched_is_gui(self):
        wp = WorkPacket(
            packet_id="PKT-DOC-TEST-002",
            action_type="drive_open_safe_test_doc",
        )
        result = self.router.route_dry_run(wp)
        self.assertEqual(
            result.router_decision.capability_matched,
            "windows_gui_execution",
        )


class TestInteractionConfig(unittest.TestCase):
    def setUp(self):
        with open(INTERACTION_CONFIG_PATH) as f:
            self.config = json.load(f)

    def test_has_safe_urls(self):
        self.assertIn("safe_drive_url", self.config)
        self.assertIn("safe_test_doc_url", self.config)

    def test_has_forbidden_actions(self):
        self.assertIn("forbidden_actions", self.config)
        self.assertGreater(len(self.config["forbidden_actions"]), 0)

    def test_forbidden_includes_extraction(self):
        forbidden = self.config["forbidden_actions"]
        self.assertIn("read_document_contents", forbidden)
        self.assertIn("copy_text", forbidden)
        self.assertIn("download_file", forbidden)
        self.assertIn("take_screenshot", forbidden)
        self.assertIn("capture_ocr", forbidden)

    def test_forbidden_includes_mutation(self):
        forbidden = self.config["forbidden_actions"]
        self.assertIn("mutate_drive", forbidden)
        self.assertIn("mutate_docs", forbidden)

    def test_forbidden_includes_secrets(self):
        forbidden = self.config["forbidden_actions"]
        self.assertIn("extract_cookies", forbidden)
        self.assertIn("extract_tokens", forbidden)
        self.assertIn("promote_memory", forbidden)


class TestProofArtifactSchemas(unittest.TestCase):
    def test_work_packet_artifact_exists(self):
        path = PROOF_DIR / "w0_drive_docs_work_packet_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertEqual(data["action_type"], "drive_open_safe_test_doc")
        self.assertIn("payload", data)
        self.assertTrue(data["payload"]["no_secret_capture"])
        self.assertTrue(data["payload"]["no_mutation"])

    def test_runtime_proof_artifact_exists(self):
        path = PROOF_DIR / "w0_drive_docs_runtime_proof_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertEqual(data["proof_status"], "completed")
        self.assertEqual(data["adapter_id"], "windows_interactive_desktop_relay")
        self.assertIn("evidence", data)

    def test_router_result_artifact_exists(self):
        path = PROOF_DIR / "w0_drive_docs_router_result_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertEqual(data["router_status"], "completed")
        self.assertEqual(data["adapter_selected"], "windows_interactive_desktop_relay")

    def test_no_secrets_in_artifacts(self):
        for name in [
            "w0_drive_docs_work_packet_example.json",
            "w0_drive_docs_runtime_proof_example.json",
            "w0_drive_docs_router_result_example.json",
        ]:
            path = PROOF_DIR / name
            raw = path.read_text().lower()
            for keyword in ["password", "api_key", "secret_key", "bearer", "token_value"]:
                self.assertNotIn(keyword, raw, f"secret keyword '{keyword}' in {name}")


if __name__ == "__main__":
    unittest.main()
