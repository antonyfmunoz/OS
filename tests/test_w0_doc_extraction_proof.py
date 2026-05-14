"""Tests for W0 safe document extraction proof -- Phase 96.8S.

Validates bounded extraction targeting, forbidden action blocking,
extraction result schema, router integration, proof artifact schema,
and absence of ingestion/memory fields.
"""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

import json
import unittest
from pathlib import Path

from control_plane.router.control_plane_router_v1 import (
    ACTION_CAPABILITY_MAP,
    ControlPlaneRouterV1,
)
from control_plane.router.router_contracts import (
    ALLOWED_ACTION_TYPES,
    CapabilityType,
    RouterStatus,
    WorkPacket,
)
from adapters.adapter_engine.adapter_registry_contracts import AdapterRegistry
from runtime.interfaces.discord_interface_adapter_v1 import (
    COMMAND_ACTION_MAP,
    SUPPORTED_COMMANDS,
    build_work_packet_for_router,
)

REGISTRY_PATH = Path(_ROOT) / "data" / "registries" / "local_worker_adapter_registry_v1.json"
EXTRACTION_CONFIG_PATH = Path(_ROOT) / "config" / "w0_doc_extraction_proof_v1.json"
PROOF_DIR = Path(_ROOT) / "data" / "runtime" / "w0_extraction_proofs"

SAFE_DOC_URL = "https://docs.google.com/document/d/1_test_doc_placeholder/edit"
SAFE_DOC_TITLE = "EOS W0 Test Document"

FORBIDDEN_ACTIONS = [
    "drive_wide_search",
    "arbitrary_url_open",
    "take_screenshot",
    "capture_ocr",
    "mutate_drive",
    "mutate_docs",
    "download_file",
    "upload_file",
    "extract_cookies",
    "extract_tokens",
    "promote_memory",
    "ingest_to_memory",
    "interpret_content",
    "summarize_content",
]


class TestExtractCommandRegistered(unittest.TestCase):
    def test_extract_in_supported_commands(self):
        self.assertIn("!extract", SUPPORTED_COMMANDS)

    def test_extract_maps_to_doc_extract_safe_test_doc(self):
        self.assertEqual(COMMAND_ACTION_MAP["!extract"], "doc_extract_safe_test_doc")

    def test_action_type_allowed(self):
        self.assertIn("doc_extract_safe_test_doc", ALLOWED_ACTION_TYPES)

    def test_capability_map_has_entry(self):
        self.assertIn("doc_extract_safe_test_doc", ACTION_CAPABILITY_MAP)
        cap = ACTION_CAPABILITY_MAP["doc_extract_safe_test_doc"]
        self.assertEqual(cap.capability_type, CapabilityType.DOCUMENT_EXTRACTION)
        self.assertTrue(cap.requires_gui)


class TestExtractionWorkPacket(unittest.TestCase):
    def test_builds_work_packet(self):
        wp = build_work_packet_for_router(
            "!extract", safe_doc_url=SAFE_DOC_URL, safe_doc_title=SAFE_DOC_TITLE
        )
        self.assertIsNotNone(wp)
        self.assertEqual(wp.action_type, "doc_extract_safe_test_doc")
        self.assertTrue(wp.packet_id.startswith("REQ-W0-EXTRACT-"))

    def test_uses_configured_safe_url(self):
        wp = build_work_packet_for_router("!extract", safe_doc_url=SAFE_DOC_URL)
        self.assertEqual(wp.payload["url"], SAFE_DOC_URL)

    def test_defaults_to_drive_homepage(self):
        wp = build_work_packet_for_router("!extract")
        self.assertEqual(wp.payload["url"], "https://drive.google.com/drive/my-drive")

    def test_no_secret_capture(self):
        wp = build_work_packet_for_router("!extract", safe_doc_url=SAFE_DOC_URL)
        self.assertTrue(wp.payload["no_secret_capture"])

    def test_no_mutation(self):
        wp = build_work_packet_for_router("!extract", safe_doc_url=SAFE_DOC_URL)
        self.assertTrue(wp.payload["no_mutation"])

    def test_uses_direct_executable(self):
        wp = build_work_packet_for_router("!extract", safe_doc_url=SAFE_DOC_URL)
        self.assertEqual(wp.payload["launch_method"], "direct_executable")

    def test_blocked_launch_methods(self):
        wp = build_work_packet_for_router("!extract", safe_doc_url=SAFE_DOC_URL)
        blocked = wp.payload.get("blocked_launch_methods", [])
        self.assertIn("explorer_url", blocked)
        self.assertIn("default_browser", blocked)

    def test_notes_mention_bounded_extraction(self):
        wp = build_work_packet_for_router(
            "!extract", safe_doc_url=SAFE_DOC_URL, safe_doc_title=SAFE_DOC_TITLE
        )
        notes_str = " ".join(wp.payload.get("notes", [])).lower()
        self.assertIn("bounded extraction", notes_str)
        self.assertIn("no drive-wide search", notes_str)
        self.assertIn("no memory promotion", notes_str)


class TestArbitraryTargetRejected(unittest.TestCase):
    def test_unknown_commands_rejected(self):
        self.assertIsNone(build_work_packet_for_router("!hack"))
        self.assertIsNone(build_work_packet_for_router("!url"))
        self.assertIsNone(build_work_packet_for_router("!exec"))
        self.assertIsNone(build_work_packet_for_router("!search"))

    def test_extract_command_does_not_accept_arbitrary_action(self):
        wp = build_work_packet_for_router("!extract")
        self.assertEqual(wp.action_type, "doc_extract_safe_test_doc")
        self.assertNotEqual(wp.action_type, "extract_arbitrary_doc")

    def test_extract_action_is_not_open_url(self):
        wp = build_work_packet_for_router("!extract")
        self.assertNotEqual(wp.action_type, "open_application_url")
        self.assertNotEqual(wp.action_type, "drive_open_safe_test_doc")


class TestForbiddenActionsBlocked(unittest.TestCase):
    def test_no_forbidden_actions_in_payload(self):
        wp = build_work_packet_for_router("!extract", safe_doc_url=SAFE_DOC_URL)
        payload_str = json.dumps(wp.payload).lower()
        for action in FORBIDDEN_ACTIONS:
            self.assertNotIn(
                action,
                payload_str,
                f"forbidden action '{action}' found in payload",
            )

    def test_no_ingestion_fields(self):
        wp = build_work_packet_for_router("!extract", safe_doc_url=SAFE_DOC_URL)
        payload = wp.payload
        self.assertNotIn("ingest_target", payload)
        self.assertNotIn("ingest_to_memory", payload)
        self.assertNotIn("memory_target", payload)
        self.assertNotIn("knowledge_base_target", payload)

    def test_no_interpretation_fields(self):
        wp = build_work_packet_for_router("!extract", safe_doc_url=SAFE_DOC_URL)
        payload = wp.payload
        self.assertNotIn("interpret", payload)
        self.assertNotIn("summarize", payload)
        self.assertNotIn("llm_analysis", payload)

    def test_no_memory_promotion_fields(self):
        wp = build_work_packet_for_router("!extract", safe_doc_url=SAFE_DOC_URL)
        payload = wp.payload
        self.assertNotIn("promote_to_memory", payload)
        self.assertNotIn("memory_target", payload)
        self.assertNotIn("ingest", payload)

    def test_no_screenshot_fields(self):
        wp = build_work_packet_for_router("!extract", safe_doc_url=SAFE_DOC_URL)
        payload = wp.payload
        self.assertNotIn("screenshot_path", payload)
        self.assertNotIn("ocr_result", payload)
        self.assertNotIn("capture_image", payload)


class TestRouterResolvesExtractAction(unittest.TestCase):
    def setUp(self):
        self.registry = AdapterRegistry.from_json_file(REGISTRY_PATH)
        self.router = ControlPlaneRouterV1(registry=self.registry, base_dir=Path(_ROOT))

    def test_dry_run_routes_extract(self):
        wp = WorkPacket(
            packet_id="PKT-EXTRACT-TEST-001",
            action_type="doc_extract_safe_test_doc",
        )
        result = self.router.route_dry_run(wp)
        self.assertEqual(result.router_status, RouterStatus.ROUTED)
        self.assertEqual(result.adapter_selected, "windows_interactive_desktop_relay")
        self.assertEqual(result.runtime_target, "local_worker_runtime_daemon")

    def test_capability_matched_is_document_extraction(self):
        wp = WorkPacket(
            packet_id="PKT-EXTRACT-TEST-002",
            action_type="doc_extract_safe_test_doc",
        )
        result = self.router.route_dry_run(wp)
        self.assertEqual(
            result.router_decision.capability_matched,
            "document_extraction",
        )


class TestExtractionConfig(unittest.TestCase):
    def setUp(self):
        with open(EXTRACTION_CONFIG_PATH) as f:
            self.config = json.load(f)

    def test_has_safe_doc_url(self):
        self.assertIn("safe_test_doc_url", self.config)

    def test_has_safe_doc_title(self):
        self.assertIn("safe_test_doc_title", self.config)

    def test_has_extraction_method(self):
        self.assertIn("extraction_method", self.config)

    def test_has_preview_max(self):
        self.assertIn("extraction_preview_max_chars", self.config)
        self.assertIsInstance(self.config["extraction_preview_max_chars"], int)
        self.assertGreater(self.config["extraction_preview_max_chars"], 0)

    def test_has_forbidden_actions(self):
        self.assertIn("forbidden_actions", self.config)
        self.assertGreater(len(self.config["forbidden_actions"]), 0)

    def test_forbidden_includes_drive_wide_search(self):
        self.assertIn("drive_wide_search", self.config["forbidden_actions"])

    def test_forbidden_includes_mutation(self):
        forbidden = self.config["forbidden_actions"]
        self.assertIn("mutate_drive", forbidden)
        self.assertIn("mutate_docs", forbidden)

    def test_forbidden_includes_secrets(self):
        forbidden = self.config["forbidden_actions"]
        self.assertIn("extract_cookies", forbidden)
        self.assertIn("extract_tokens", forbidden)

    def test_forbidden_includes_memory_promotion(self):
        forbidden = self.config["forbidden_actions"]
        self.assertIn("promote_memory", forbidden)
        self.assertIn("ingest_to_memory", forbidden)

    def test_forbidden_includes_interpretation(self):
        forbidden = self.config["forbidden_actions"]
        self.assertIn("interpret_content", forbidden)
        self.assertIn("summarize_content", forbidden)


class TestExtractionResultSchema(unittest.TestCase):
    def setUp(self):
        path = PROOF_DIR / "w0_doc_extraction_result_example.json"
        self.data = json.loads(path.read_text())

    def test_has_required_fields(self):
        required = [
            "request_id",
            "action_type",
            "target_doc_id_or_title",
            "extraction_method",
            "extracted_text_preview",
            "extracted_character_count",
            "extraction_confidence",
            "proof_status",
            "forbidden_actions_confirmed",
            "timestamp",
        ]
        for field in required:
            self.assertIn(field, self.data, f"missing field: {field}")

    def test_action_type_is_extraction(self):
        self.assertEqual(self.data["action_type"], "doc_extract_safe_test_doc")

    def test_proof_status_completed(self):
        self.assertEqual(self.data["proof_status"], "completed")

    def test_forbidden_actions_confirmed(self):
        self.assertTrue(self.data["forbidden_actions_confirmed"])

    def test_preview_length_bounded(self):
        with open(EXTRACTION_CONFIG_PATH) as f:
            config = json.load(f)
        max_chars = config["extraction_preview_max_chars"]
        preview = self.data["extracted_text_preview"]
        self.assertLessEqual(len(preview), max_chars)

    def test_extraction_confidence_valid(self):
        self.assertIn(self.data["extraction_confidence"], ("high", "medium", "low"))

    def test_character_count_positive(self):
        self.assertGreater(self.data["extracted_character_count"], 0)

    def test_target_doc_is_safe_test_doc(self):
        self.assertEqual(self.data["target_doc_id_or_title"], "EOS W0 Test Document")


class TestProofArtifactSchemas(unittest.TestCase):
    def test_work_packet_artifact_exists(self):
        path = PROOF_DIR / "w0_doc_extraction_work_packet_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertEqual(data["action_type"], "doc_extract_safe_test_doc")
        self.assertIn("payload", data)
        self.assertTrue(data["payload"]["no_secret_capture"])
        self.assertTrue(data["payload"]["no_mutation"])

    def test_runtime_proof_artifact_exists(self):
        path = PROOF_DIR / "w0_doc_extraction_runtime_proof_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertEqual(data["proof_status"], "completed")
        self.assertEqual(data["adapter_id"], "windows_interactive_desktop_relay")
        self.assertIn("evidence", data)
        self.assertTrue(data["evidence"]["extraction_completed"])

    def test_router_result_artifact_exists(self):
        path = PROOF_DIR / "w0_doc_extraction_router_result_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertEqual(data["router_status"], "completed")
        self.assertEqual(data["adapter_selected"], "windows_interactive_desktop_relay")

    def test_extraction_result_artifact_exists(self):
        path = PROOF_DIR / "w0_doc_extraction_result_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertEqual(data["action_type"], "doc_extract_safe_test_doc")
        self.assertTrue(data["forbidden_actions_confirmed"])

    def test_no_secrets_in_artifacts(self):
        for name in [
            "w0_doc_extraction_work_packet_example.json",
            "w0_doc_extraction_runtime_proof_example.json",
            "w0_doc_extraction_router_result_example.json",
            "w0_doc_extraction_result_example.json",
        ]:
            path = PROOF_DIR / name
            raw = path.read_text().lower()
            for keyword in ["password", "api_key", "secret_key", "bearer", "token_value"]:
                self.assertNotIn(keyword, raw, f"secret keyword '{keyword}' in {name}")


if __name__ == "__main__":
    unittest.main()
