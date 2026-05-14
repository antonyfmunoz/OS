"""Tests for W0 safe document ingestion candidate proof -- Phase 96.8T.

Validates ingestion candidate creation, memory candidate creation,
governance boundary enforcement, forbidden action blocking,
content hash determinism, and absence of canonical memory writes.
"""

import hashlib
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
INGESTION_CONFIG_PATH = Path(_ROOT) / "config" / "w0_doc_ingestion_candidate_proof_v1.json"
PROOF_DIR = Path(_ROOT) / "data" / "runtime" / "w0_ingestion_candidates"

SAFE_DOC_URL = "https://docs.google.com/document/d/1_test_doc_placeholder/edit"
SAFE_DOC_TITLE = "EOS W0 Test Document"

FORBIDDEN_ACTIONS = [
    "promote_memory",
    "canonical_write",
    "world_model_update",
    "generate_embeddings",
    "interpret_content",
    "summarize_content",
    "drive_wide_ingestion",
    "arbitrary_url_open",
    "recursive_crawl",
    "take_screenshot",
    "capture_ocr",
    "mutate_drive",
    "mutate_docs",
    "extract_cookies",
    "extract_tokens",
]


class TestIngestCandidateCommandRegistered(unittest.TestCase):
    def test_command_in_supported_commands(self):
        self.assertIn("!ingest-candidate", SUPPORTED_COMMANDS)

    def test_command_maps_to_action(self):
        self.assertEqual(
            COMMAND_ACTION_MAP["!ingest-candidate"],
            "doc_ingestion_candidate_safe_test_doc",
        )

    def test_action_type_allowed(self):
        self.assertIn("doc_ingestion_candidate_safe_test_doc", ALLOWED_ACTION_TYPES)

    def test_capability_map_has_entry(self):
        self.assertIn("doc_ingestion_candidate_safe_test_doc", ACTION_CAPABILITY_MAP)
        cap = ACTION_CAPABILITY_MAP["doc_ingestion_candidate_safe_test_doc"]
        self.assertEqual(cap.capability_type, CapabilityType.INGESTION_CANDIDACY)
        self.assertFalse(cap.requires_gui)


class TestIngestionCandidateWorkPacket(unittest.TestCase):
    def test_builds_work_packet(self):
        wp = build_work_packet_for_router(
            "!ingest-candidate",
            safe_doc_url=SAFE_DOC_URL,
            safe_doc_title=SAFE_DOC_TITLE,
        )
        self.assertIsNotNone(wp)
        self.assertEqual(wp.action_type, "doc_ingestion_candidate_safe_test_doc")
        self.assertTrue(wp.packet_id.startswith("REQ-W0-INGEST-CAND-"))

    def test_uses_configured_safe_url(self):
        wp = build_work_packet_for_router("!ingest-candidate", safe_doc_url=SAFE_DOC_URL)
        self.assertEqual(wp.payload["url"], SAFE_DOC_URL)

    def test_defaults_to_drive_homepage(self):
        wp = build_work_packet_for_router("!ingest-candidate")
        self.assertEqual(wp.payload["url"], "https://drive.google.com/drive/my-drive")

    def test_no_secret_capture(self):
        wp = build_work_packet_for_router("!ingest-candidate", safe_doc_url=SAFE_DOC_URL)
        self.assertTrue(wp.payload["no_secret_capture"])

    def test_no_mutation(self):
        wp = build_work_packet_for_router("!ingest-candidate", safe_doc_url=SAFE_DOC_URL)
        self.assertTrue(wp.payload["no_mutation"])

    def test_notes_mention_no_promotion(self):
        wp = build_work_packet_for_router("!ingest-candidate", safe_doc_url=SAFE_DOC_URL)
        notes_str = " ".join(wp.payload.get("notes", [])).lower()
        self.assertIn("no memory promotion", notes_str)
        self.assertIn("no canonical writes", notes_str)
        self.assertIn("candidate only", notes_str)

    def test_notes_mention_governance(self):
        wp = build_work_packet_for_router("!ingest-candidate", safe_doc_url=SAFE_DOC_URL)
        notes_str = " ".join(wp.payload.get("notes", [])).lower()
        self.assertIn("governance approval required", notes_str)


class TestArbitraryTargetRejected(unittest.TestCase):
    def test_unknown_commands_rejected(self):
        self.assertIsNone(build_work_packet_for_router("!hack"))
        self.assertIsNone(build_work_packet_for_router("!ingest"))
        self.assertIsNone(build_work_packet_for_router("!promote"))
        self.assertIsNone(build_work_packet_for_router("!crawl"))

    def test_action_is_not_extraction(self):
        wp = build_work_packet_for_router("!ingest-candidate")
        self.assertNotEqual(wp.action_type, "doc_extract_safe_test_doc")

    def test_action_is_not_open_url(self):
        wp = build_work_packet_for_router("!ingest-candidate")
        self.assertNotEqual(wp.action_type, "open_application_url")


class TestForbiddenActionsBlocked(unittest.TestCase):
    def test_no_forbidden_actions_in_payload(self):
        wp = build_work_packet_for_router("!ingest-candidate", safe_doc_url=SAFE_DOC_URL)
        payload_str = json.dumps(wp.payload).lower()
        for action in FORBIDDEN_ACTIONS:
            self.assertNotIn(
                action,
                payload_str,
                f"forbidden action '{action}' found in payload",
            )

    def test_no_canonical_write_fields(self):
        wp = build_work_packet_for_router("!ingest-candidate", safe_doc_url=SAFE_DOC_URL)
        payload = wp.payload
        self.assertNotIn("canonical_target", payload)
        self.assertNotIn("write_to_memory", payload)
        self.assertNotIn("memory_table", payload)

    def test_no_embedding_fields(self):
        wp = build_work_packet_for_router("!ingest-candidate", safe_doc_url=SAFE_DOC_URL)
        payload = wp.payload
        self.assertNotIn("embedding_model", payload)
        self.assertNotIn("embedding_vector", payload)
        self.assertNotIn("vector_store", payload)

    def test_no_interpretation_fields(self):
        wp = build_work_packet_for_router("!ingest-candidate", safe_doc_url=SAFE_DOC_URL)
        payload = wp.payload
        self.assertNotIn("interpret", payload)
        self.assertNotIn("summarize", payload)
        self.assertNotIn("llm_analysis", payload)

    def test_no_world_model_fields(self):
        wp = build_work_packet_for_router("!ingest-candidate", safe_doc_url=SAFE_DOC_URL)
        payload = wp.payload
        self.assertNotIn("world_model_target", payload)
        self.assertNotIn("world_model_update", payload)


class TestRouterResolvesIngestionCandidateAction(unittest.TestCase):
    def setUp(self):
        self.registry = AdapterRegistry.from_json_file(REGISTRY_PATH)
        self.router = ControlPlaneRouterV1(registry=self.registry, base_dir=Path(_ROOT))

    def test_dry_run_routes(self):
        wp = WorkPacket(
            packet_id="PKT-INGEST-CAND-TEST-001",
            action_type="doc_ingestion_candidate_safe_test_doc",
        )
        result = self.router.route_dry_run(wp)
        self.assertEqual(result.router_status, RouterStatus.ROUTED)
        self.assertEqual(result.adapter_selected, "windows_interactive_desktop_relay")
        self.assertEqual(result.runtime_target, "local_worker_runtime_daemon")

    def test_capability_matched_is_ingestion_candidacy(self):
        wp = WorkPacket(
            packet_id="PKT-INGEST-CAND-TEST-002",
            action_type="doc_ingestion_candidate_safe_test_doc",
        )
        result = self.router.route_dry_run(wp)
        self.assertEqual(
            result.router_decision.capability_matched,
            "ingestion_candidacy",
        )


class TestIngestionConfig(unittest.TestCase):
    def setUp(self):
        with open(INGESTION_CONFIG_PATH) as f:
            self.config = json.load(f)

    def test_has_safe_doc_url(self):
        self.assertIn("safe_test_doc_url", self.config)

    def test_has_safe_doc_title(self):
        self.assertIn("safe_test_doc_title", self.config)

    def test_has_forbidden_actions(self):
        self.assertIn("forbidden_actions", self.config)
        self.assertGreater(len(self.config["forbidden_actions"]), 0)

    def test_forbidden_includes_promotion(self):
        forbidden = self.config["forbidden_actions"]
        self.assertIn("promote_memory", forbidden)
        self.assertIn("canonical_write", forbidden)
        self.assertIn("world_model_update", forbidden)

    def test_forbidden_includes_embeddings(self):
        self.assertIn("generate_embeddings", self.config["forbidden_actions"])

    def test_forbidden_includes_interpretation(self):
        forbidden = self.config["forbidden_actions"]
        self.assertIn("interpret_content", forbidden)
        self.assertIn("summarize_content", forbidden)

    def test_has_governance_gate(self):
        self.assertIn("governance_gate", self.config)
        gate = self.config["governance_gate"]
        self.assertTrue(gate["required_before_promotion"])
        self.assertEqual(gate["approver"], "founder")


class TestIngestionCandidateSchema(unittest.TestCase):
    def setUp(self):
        path = PROOF_DIR / "w0_doc_ingestion_candidate_example.json"
        self.data = json.loads(path.read_text())

    def test_has_required_fields(self):
        required = [
            "candidate_id",
            "source_type",
            "source_title",
            "source_id_or_url",
            "extraction_reference_id",
            "normalized_text_preview",
            "normalized_character_count",
            "content_hash",
            "source_confidence",
            "extraction_confidence",
            "candidate_status",
            "promotion_status",
            "governance_required",
            "forbidden_actions_confirmed",
            "timestamp",
        ]
        for field in required:
            self.assertIn(field, self.data, f"missing field: {field}")

    def test_promotion_status_is_candidate_only(self):
        self.assertEqual(self.data["promotion_status"], "candidate_only")

    def test_governance_required(self):
        self.assertTrue(self.data["governance_required"])

    def test_forbidden_actions_confirmed(self):
        self.assertTrue(self.data["forbidden_actions_confirmed"])

    def test_preview_length_bounded(self):
        with open(INGESTION_CONFIG_PATH) as f:
            config = json.load(f)
        max_chars = config["extraction_preview_max_chars"]
        self.assertLessEqual(len(self.data["normalized_text_preview"]), max_chars)

    def test_content_hash_is_sha256(self):
        self.assertEqual(len(self.data["content_hash"]), 64)

    def test_content_hash_deterministic(self):
        text = self.data["normalized_text_preview"]
        full_text = (
            "This is the EOS W0 Test Document. It exists solely for extraction proof "
            "validation. No sensitive content. No private data. This document is used "
            "to verify that the UMH substrate can perform bounded, policy-restricted "
            "document extraction through the canonical routed path."
        )
        expected_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest()
        self.assertEqual(self.data["content_hash"], expected_hash)

    def test_source_title_is_safe_test_doc(self):
        self.assertEqual(self.data["source_title"], "EOS W0 Test Document")

    def test_candidate_status_is_created(self):
        self.assertEqual(self.data["candidate_status"], "created")


class TestMemoryCandidateSchema(unittest.TestCase):
    def setUp(self):
        path = PROOF_DIR / "w0_doc_memory_candidate_example.json"
        self.data = json.loads(path.read_text())

    def test_has_required_fields(self):
        required = [
            "memory_candidate_id",
            "candidate_id",
            "memory_type",
            "scope",
            "source",
            "confidence",
            "content_preview",
            "promotion_status",
            "requires_review",
            "allowed_next_actions",
            "blocked_next_actions",
            "timestamp",
        ]
        for field in required:
            self.assertIn(field, self.data, f"missing field: {field}")

    def test_promotion_status_is_candidate_only(self):
        self.assertEqual(self.data["promotion_status"], "candidate_only")

    def test_requires_review(self):
        self.assertTrue(self.data["requires_review"])

    def test_promote_to_memory_blocked(self):
        self.assertIn("promote_to_memory", self.data["blocked_next_actions"])

    def test_write_to_canonical_blocked(self):
        self.assertIn("write_to_canonical", self.data["blocked_next_actions"])

    def test_update_world_model_blocked(self):
        self.assertIn("update_world_model", self.data["blocked_next_actions"])

    def test_generate_embeddings_blocked(self):
        self.assertIn("generate_embeddings", self.data["blocked_next_actions"])

    def test_interpret_content_blocked(self):
        self.assertIn("interpret_content", self.data["blocked_next_actions"])

    def test_summarize_content_blocked(self):
        self.assertIn("summarize_content", self.data["blocked_next_actions"])

    def test_review_is_allowed(self):
        self.assertIn("review_candidate", self.data["allowed_next_actions"])

    def test_approve_is_allowed(self):
        self.assertIn("approve_for_promotion", self.data["allowed_next_actions"])

    def test_reject_is_allowed(self):
        self.assertIn("reject_candidate", self.data["allowed_next_actions"])

    def test_content_preview_bounded(self):
        with open(INGESTION_CONFIG_PATH) as f:
            config = json.load(f)
        max_chars = config["extraction_preview_max_chars"]
        self.assertLessEqual(len(self.data["content_preview"]), max_chars)

    def test_references_ingestion_candidate(self):
        cand_path = PROOF_DIR / "w0_doc_ingestion_candidate_example.json"
        cand = json.loads(cand_path.read_text())
        self.assertEqual(self.data["candidate_id"], cand["candidate_id"])


class TestProofArtifactSchemas(unittest.TestCase):
    def test_work_packet_artifact_exists(self):
        path = PROOF_DIR / "w0_doc_ingestion_work_packet_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertEqual(data["action_type"], "doc_ingestion_candidate_safe_test_doc")
        self.assertTrue(data["payload"]["no_secret_capture"])
        self.assertTrue(data["payload"]["no_mutation"])

    def test_runtime_proof_artifact_exists(self):
        path = PROOF_DIR / "w0_doc_ingestion_runtime_proof_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertEqual(data["proof_status"], "completed")
        self.assertFalse(data["evidence"]["canonical_memory_written"])
        self.assertFalse(data["evidence"]["world_model_updated"])
        self.assertFalse(data["evidence"]["embeddings_generated"])

    def test_router_result_artifact_exists(self):
        path = PROOF_DIR / "w0_doc_ingestion_router_result_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertEqual(data["router_status"], "completed")

    def test_no_secrets_in_artifacts(self):
        for name in [
            "w0_doc_ingestion_work_packet_example.json",
            "w0_doc_ingestion_runtime_proof_example.json",
            "w0_doc_ingestion_router_result_example.json",
            "w0_doc_ingestion_candidate_example.json",
            "w0_doc_memory_candidate_example.json",
        ]:
            path = PROOF_DIR / name
            raw = path.read_text().lower()
            for keyword in ["password", "api_key", "secret_key", "bearer", "token_value"]:
                self.assertNotIn(keyword, raw, f"secret keyword '{keyword}' in {name}")


if __name__ == "__main__":
    unittest.main()
