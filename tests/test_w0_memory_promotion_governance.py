"""Tests for W0 memory promotion governance proof -- Phase 96.8U.

Validates governance review gating, canonical memory write schema,
rollback artifact creation, deterministic content hashing,
forbidden action blocking, and proof artifact correctness.
"""

import hashlib
import json
import sys
import unittest
from pathlib import Path

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

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
from core.runtime.adapter_registry_contracts import AdapterRegistry
from runtime.interfaces.discord_interface_adapter_v1 import (
    COMMAND_ACTION_MAP,
    SUPPORTED_COMMANDS,
    build_work_packet_for_router,
)

REGISTRY_PATH = Path(_ROOT) / "data" / "registries" / "local_worker_adapter_registry_v1.json"
GOVERNANCE_CONFIG_PATH = Path(_ROOT) / "config" / "w0_memory_promotion_governance_proof_v1.json"
PROOF_DIR = Path(_ROOT) / "data" / "runtime" / "w0_memory_governance"

SAFE_DOC_URL = "https://docs.google.com/document/d/1_test_doc_placeholder/edit"
SAFE_DOC_TITLE = "EOS W0 Test Document"

SIMULATED_CONTENT = (
    "This is the EOS W0 Test Document. It exists solely for extraction proof "
    "validation. No sensitive content. No private data. This document is used "
    "to verify that the UMH substrate can perform bounded, policy-restricted "
    "document extraction through the canonical routed path."
)

FORBIDDEN_ACTIONS = [
    "autonomous_promotion",
    "recursive_promotion",
    "self_modifying_rules",
    "generate_embeddings",
    "semantic_interpretation",
    "unbounded_world_model_mutation",
    "drive_wide_promotion",
    "arbitrary_candidate_promotion",
    "take_screenshot",
    "capture_ocr",
    "mutate_drive",
    "mutate_docs",
    "extract_cookies",
    "extract_tokens",
]


# ---------------------------------------------------------------------------
# Command registration
# ---------------------------------------------------------------------------


class TestPromoteMemoryCommandRegistered(unittest.TestCase):
    def test_command_in_supported_commands(self):
        self.assertIn("!promote-memory", SUPPORTED_COMMANDS)

    def test_command_maps_to_action(self):
        self.assertEqual(
            COMMAND_ACTION_MAP["!promote-memory"],
            "promote_safe_memory_candidate",
        )

    def test_action_type_allowed(self):
        self.assertIn("promote_safe_memory_candidate", ALLOWED_ACTION_TYPES)

    def test_capability_map_has_entry(self):
        self.assertIn("promote_safe_memory_candidate", ACTION_CAPABILITY_MAP)
        cap = ACTION_CAPABILITY_MAP["promote_safe_memory_candidate"]
        self.assertEqual(cap.capability_type, CapabilityType.MEMORY_PROMOTION)
        self.assertFalse(cap.requires_gui)


# ---------------------------------------------------------------------------
# WorkPacket construction
# ---------------------------------------------------------------------------


class TestPromoteMemoryWorkPacket(unittest.TestCase):
    def test_builds_work_packet(self):
        wp = build_work_packet_for_router(
            "!promote-memory",
            safe_doc_url=SAFE_DOC_URL,
            safe_doc_title=SAFE_DOC_TITLE,
            candidate_id="CAND-test001",
            governance_review_id="GOV-test001",
        )
        self.assertIsNotNone(wp)
        self.assertEqual(wp.action_type, "promote_safe_memory_candidate")
        self.assertTrue(wp.packet_id.startswith("REQ-W0-PROMOTE-"))

    def test_uses_configured_safe_url(self):
        wp = build_work_packet_for_router("!promote-memory", safe_doc_url=SAFE_DOC_URL)
        self.assertEqual(wp.payload["url"], SAFE_DOC_URL)

    def test_defaults_to_drive_homepage(self):
        wp = build_work_packet_for_router("!promote-memory")
        self.assertEqual(wp.payload["url"], "https://drive.google.com/drive/my-drive")

    def test_no_secret_capture(self):
        wp = build_work_packet_for_router("!promote-memory", safe_doc_url=SAFE_DOC_URL)
        self.assertTrue(wp.payload["no_secret_capture"])

    def test_no_mutation_is_false(self):
        wp = build_work_packet_for_router("!promote-memory", safe_doc_url=SAFE_DOC_URL)
        self.assertFalse(wp.payload["no_mutation"])

    def test_source_interface(self):
        wp = build_work_packet_for_router("!promote-memory")
        self.assertEqual(wp.source_interface, "discord_interface_adapter_v1")

    def test_notes_mention_governance(self):
        wp = build_work_packet_for_router("!promote-memory", safe_doc_url=SAFE_DOC_URL)
        notes_str = " ".join(wp.payload.get("notes", [])).lower()
        self.assertIn("governance review approval", notes_str)

    def test_notes_mention_no_autonomous(self):
        wp = build_work_packet_for_router("!promote-memory", safe_doc_url=SAFE_DOC_URL)
        notes_str = " ".join(wp.payload.get("notes", [])).lower()
        self.assertIn("no autonomous promotion", notes_str)

    def test_notes_mention_no_recursive(self):
        wp = build_work_packet_for_router("!promote-memory", safe_doc_url=SAFE_DOC_URL)
        notes_str = " ".join(wp.payload.get("notes", [])).lower()
        self.assertIn("no recursive promotion", notes_str)

    def test_notes_mention_rollback(self):
        wp = build_work_packet_for_router("!promote-memory", safe_doc_url=SAFE_DOC_URL)
        notes_str = " ".join(wp.payload.get("notes", [])).lower()
        self.assertIn("rollback", notes_str)

    def test_notes_mention_audit(self):
        wp = build_work_packet_for_router("!promote-memory", safe_doc_url=SAFE_DOC_URL)
        notes_str = " ".join(wp.payload.get("notes", [])).lower()
        self.assertIn("audit", notes_str)


# ---------------------------------------------------------------------------
# Arbitrary commands rejected
# ---------------------------------------------------------------------------


class TestArbitraryCommandsRejected(unittest.TestCase):
    def test_unknown_commands_rejected(self):
        self.assertIsNone(build_work_packet_for_router("!hack"))
        self.assertIsNone(build_work_packet_for_router("!promote"))
        self.assertIsNone(build_work_packet_for_router("!auto-promote"))
        self.assertIsNone(build_work_packet_for_router("!memory-write"))

    def test_action_is_not_extraction(self):
        wp = build_work_packet_for_router("!promote-memory")
        self.assertNotEqual(wp.action_type, "doc_extract_safe_test_doc")

    def test_action_is_not_ingestion(self):
        wp = build_work_packet_for_router("!promote-memory")
        self.assertNotEqual(wp.action_type, "doc_ingestion_candidate_safe_test_doc")

    def test_action_is_not_open_url(self):
        wp = build_work_packet_for_router("!promote-memory")
        self.assertNotEqual(wp.action_type, "open_application_url")


# ---------------------------------------------------------------------------
# Forbidden actions
# ---------------------------------------------------------------------------


class TestForbiddenActionsBlocked(unittest.TestCase):
    def test_no_forbidden_actions_in_payload(self):
        wp = build_work_packet_for_router("!promote-memory", safe_doc_url=SAFE_DOC_URL)
        payload_str = json.dumps(wp.payload).lower()
        for action in FORBIDDEN_ACTIONS:
            self.assertNotIn(
                action,
                payload_str,
                f"forbidden action '{action}' found in payload",
            )

    def test_no_embedding_fields(self):
        wp = build_work_packet_for_router("!promote-memory", safe_doc_url=SAFE_DOC_URL)
        payload = wp.payload
        self.assertNotIn("embedding_model", payload)
        self.assertNotIn("embedding_vector", payload)
        self.assertNotIn("vector_store", payload)

    def test_no_interpretation_fields(self):
        wp = build_work_packet_for_router("!promote-memory", safe_doc_url=SAFE_DOC_URL)
        payload = wp.payload
        self.assertNotIn("interpret", payload)
        self.assertNotIn("summarize", payload)
        self.assertNotIn("llm_analysis", payload)

    def test_no_world_model_fields(self):
        wp = build_work_packet_for_router("!promote-memory", safe_doc_url=SAFE_DOC_URL)
        payload = wp.payload
        self.assertNotIn("world_model_target", payload)
        self.assertNotIn("world_model_update", payload)

    def test_no_recursive_trigger(self):
        wp = build_work_packet_for_router("!promote-memory", safe_doc_url=SAFE_DOC_URL)
        payload = wp.payload
        self.assertNotIn("recursive_promotion", payload)
        self.assertNotIn("auto_promote", payload)
        self.assertNotIn("chain_promote", payload)


# ---------------------------------------------------------------------------
# Router resolution
# ---------------------------------------------------------------------------


class TestRouterResolvesPromoteAction(unittest.TestCase):
    def setUp(self):
        self.registry = AdapterRegistry.from_json_file(REGISTRY_PATH)
        self.router = ControlPlaneRouterV1(registry=self.registry, base_dir=Path(_ROOT))

    def test_dry_run_routes(self):
        wp = WorkPacket(
            packet_id="PKT-PROMOTE-TEST-001",
            action_type="promote_safe_memory_candidate",
        )
        result = self.router.route_dry_run(wp)
        self.assertEqual(result.router_status, RouterStatus.ROUTED)
        self.assertEqual(result.adapter_selected, "windows_interactive_desktop_relay")
        self.assertEqual(result.runtime_target, "local_worker_runtime_daemon")

    def test_capability_matched_is_memory_promotion(self):
        wp = WorkPacket(
            packet_id="PKT-PROMOTE-TEST-002",
            action_type="promote_safe_memory_candidate",
        )
        result = self.router.route_dry_run(wp)
        self.assertEqual(
            result.router_decision.capability_matched,
            "memory_promotion",
        )

    def test_unknown_action_rejected(self):
        wp = WorkPacket(
            packet_id="PKT-PROMOTE-TEST-003",
            action_type="auto_promote_all_candidates",
        )
        result = self.router.route_dry_run(wp)
        self.assertNotEqual(result.router_status, RouterStatus.ROUTED)


# ---------------------------------------------------------------------------
# Governance config
# ---------------------------------------------------------------------------


class TestGovernanceConfig(unittest.TestCase):
    def setUp(self):
        with open(GOVERNANCE_CONFIG_PATH) as f:
            self.config = json.load(f)

    def test_has_promotion_rules(self):
        self.assertIn("promotion_rules", self.config)

    def test_governance_review_required(self):
        rules = self.config["promotion_rules"]
        self.assertTrue(rules["governance_review_required"])

    def test_explicit_approval_required(self):
        rules = self.config["promotion_rules"]
        self.assertTrue(rules["explicit_approval_required"])

    def test_approver_is_founder(self):
        rules = self.config["promotion_rules"]
        self.assertEqual(rules["approver"], "founder")

    def test_approval_method_is_explicit_command(self):
        rules = self.config["promotion_rules"]
        self.assertEqual(rules["approval_method"], "explicit_command")

    def test_audit_artifact_required(self):
        rules = self.config["promotion_rules"]
        self.assertTrue(rules["audit_artifact_required"])

    def test_rollback_reference_required(self):
        rules = self.config["promotion_rules"]
        self.assertTrue(rules["rollback_reference_required"])

    def test_deterministic_promotion(self):
        rules = self.config["promotion_rules"]
        self.assertTrue(rules["deterministic_promotion"])

    def test_forbidden_actions_list(self):
        self.assertIn("forbidden_actions", self.config)
        self.assertEqual(len(self.config["forbidden_actions"]), 14)

    def test_forbidden_includes_autonomous_promotion(self):
        self.assertIn("autonomous_promotion", self.config["forbidden_actions"])

    def test_forbidden_includes_recursive_promotion(self):
        self.assertIn("recursive_promotion", self.config["forbidden_actions"])

    def test_forbidden_includes_self_modifying_rules(self):
        self.assertIn("self_modifying_rules", self.config["forbidden_actions"])

    def test_forbidden_includes_generate_embeddings(self):
        self.assertIn("generate_embeddings", self.config["forbidden_actions"])

    def test_forbidden_includes_semantic_interpretation(self):
        self.assertIn("semantic_interpretation", self.config["forbidden_actions"])

    def test_allowed_action_types(self):
        self.assertEqual(
            self.config["allowed_action_types"],
            ["promote_safe_memory_candidate"],
        )

    def test_canonical_memory_target(self):
        self.assertEqual(
            self.config["canonical_memory_target"],
            "w0_safe_test_doc_knowledge",
        )

    def test_has_safe_doc_url(self):
        self.assertIn("safe_test_doc_url", self.config)

    def test_has_safe_doc_title(self):
        self.assertIn("safe_test_doc_title", self.config)


# ---------------------------------------------------------------------------
# Governance review artifact schema
# ---------------------------------------------------------------------------


class TestGovernanceReviewSchema(unittest.TestCase):
    def setUp(self):
        path = PROOF_DIR / "w0_governance_review_example.json"
        self.data = json.loads(path.read_text())

    def test_has_required_fields(self):
        required = [
            "review_id",
            "candidate_id",
            "review_status",
            "reviewer",
            "decision_reason",
            "allowed_actions",
            "blocked_actions",
            "promotion_allowed",
            "rollback_required",
            "timestamp",
        ]
        for field in required:
            self.assertIn(field, self.data, f"missing field: {field}")

    def test_review_status_approved(self):
        self.assertEqual(self.data["review_status"], "approved")

    def test_reviewer_is_founder(self):
        self.assertEqual(self.data["reviewer"], "founder")

    def test_promotion_allowed(self):
        self.assertTrue(self.data["promotion_allowed"])

    def test_rollback_required(self):
        self.assertTrue(self.data["rollback_required"])

    def test_allowed_actions_includes_promote(self):
        self.assertIn("promote_to_canonical_memory", self.data["allowed_actions"])

    def test_allowed_actions_includes_audit(self):
        self.assertIn("create_audit_artifact", self.data["allowed_actions"])

    def test_allowed_actions_includes_rollback(self):
        self.assertIn("create_rollback_reference", self.data["allowed_actions"])

    def test_blocked_actions_includes_autonomous(self):
        self.assertIn("autonomous_promotion", self.data["blocked_actions"])

    def test_blocked_actions_includes_recursive(self):
        self.assertIn("recursive_promotion", self.data["blocked_actions"])

    def test_blocked_actions_includes_embeddings(self):
        self.assertIn("generate_embeddings", self.data["blocked_actions"])

    def test_blocked_actions_includes_interpretation(self):
        self.assertIn("semantic_interpretation", self.data["blocked_actions"])

    def test_blocked_actions_includes_self_modifying(self):
        self.assertIn("self_modifying_rules", self.data["blocked_actions"])


# ---------------------------------------------------------------------------
# Canonical memory artifact schema
# ---------------------------------------------------------------------------


class TestCanonicalMemorySchema(unittest.TestCase):
    def setUp(self):
        path = PROOF_DIR / "w0_canonical_memory_example.json"
        self.data = json.loads(path.read_text())

    def test_has_required_fields(self):
        required = [
            "canonical_memory_id",
            "source_candidate_id",
            "source_document",
            "memory_type",
            "memory_scope",
            "normalized_content",
            "content_hash",
            "promotion_reason",
            "governance_review_id",
            "approved_by",
            "promotion_timestamp",
            "rollback_reference",
            "canonical_version",
            "promotion_status",
        ]
        for field in required:
            self.assertIn(field, self.data, f"missing field: {field}")

    def test_promotion_status_is_promoted(self):
        self.assertEqual(self.data["promotion_status"], "promoted")

    def test_approved_by_founder(self):
        self.assertEqual(self.data["approved_by"], "founder")

    def test_canonical_version_is_one(self):
        self.assertEqual(self.data["canonical_version"], 1)

    def test_memory_type(self):
        self.assertEqual(self.data["memory_type"], "document_knowledge")

    def test_memory_scope(self):
        self.assertEqual(self.data["memory_scope"], "safe_test_doc")

    def test_source_document(self):
        self.assertEqual(self.data["source_document"], "EOS W0 Test Document")

    def test_content_hash_is_sha256(self):
        self.assertEqual(len(self.data["content_hash"]), 64)

    def test_content_hash_deterministic(self):
        expected = hashlib.sha256(SIMULATED_CONTENT.encode("utf-8")).hexdigest()
        self.assertEqual(self.data["content_hash"], expected)

    def test_content_hash_matches_normalized_content(self):
        rehash = hashlib.sha256(self.data["normalized_content"].encode("utf-8")).hexdigest()
        self.assertEqual(self.data["content_hash"], rehash)

    def test_governance_review_id_present(self):
        self.assertTrue(self.data["governance_review_id"].startswith("GOV-REVIEW-"))

    def test_rollback_reference_present(self):
        self.assertTrue(self.data["rollback_reference"].startswith("ROLLBACK-"))

    def test_references_governance_review(self):
        review_path = PROOF_DIR / "w0_governance_review_example.json"
        review = json.loads(review_path.read_text())
        self.assertEqual(self.data["governance_review_id"], review["review_id"])

    def test_references_candidate(self):
        review_path = PROOF_DIR / "w0_governance_review_example.json"
        review = json.loads(review_path.read_text())
        self.assertEqual(self.data["source_candidate_id"], review["candidate_id"])


# ---------------------------------------------------------------------------
# Rollback artifact schema
# ---------------------------------------------------------------------------


class TestRollbackArtifactSchema(unittest.TestCase):
    def setUp(self):
        path = PROOF_DIR / "w0_memory_rollback_example.json"
        self.data = json.loads(path.read_text())

    def test_has_required_fields(self):
        required = [
            "rollback_id",
            "canonical_memory_id",
            "rollback_trigger",
            "rollback_status",
            "rollback_timestamp",
            "restored_state_reference",
        ]
        for field in required:
            self.assertIn(field, self.data, f"missing field: {field}")

    def test_rollback_status_available(self):
        self.assertEqual(self.data["rollback_status"], "available")

    def test_restored_state_is_candidate_only(self):
        self.assertEqual(self.data["restored_state_reference"], "candidate_only")

    def test_references_canonical_memory(self):
        canonical_path = PROOF_DIR / "w0_canonical_memory_example.json"
        canonical = json.loads(canonical_path.read_text())
        self.assertEqual(self.data["canonical_memory_id"], canonical["canonical_memory_id"])

    def test_rollback_id_matches_canonical_reference(self):
        canonical_path = PROOF_DIR / "w0_canonical_memory_example.json"
        canonical = json.loads(canonical_path.read_text())
        self.assertEqual(self.data["rollback_id"], canonical["rollback_reference"])


# ---------------------------------------------------------------------------
# Runtime proof artifact
# ---------------------------------------------------------------------------


class TestRuntimeProofArtifact(unittest.TestCase):
    def setUp(self):
        path = PROOF_DIR / "w0_memory_promotion_runtime_proof_example.json"
        self.data = json.loads(path.read_text())

    def test_proof_status_completed(self):
        self.assertEqual(self.data["proof_status"], "completed")

    def test_action_type(self):
        self.assertEqual(self.data["action_type"], "promote_safe_memory_candidate")

    def test_adapter_id(self):
        self.assertEqual(self.data["adapter_id"], "windows_interactive_desktop_relay")

    def test_evidence_governance_completed(self):
        self.assertTrue(self.data["evidence"]["governance_review_completed"])

    def test_evidence_canonical_written(self):
        self.assertTrue(self.data["evidence"]["canonical_memory_written"])

    def test_evidence_audit_created(self):
        self.assertTrue(self.data["evidence"]["audit_artifact_created"])

    def test_evidence_rollback_created(self):
        self.assertTrue(self.data["evidence"]["rollback_reference_created"])

    def test_evidence_deterministic(self):
        self.assertTrue(self.data["evidence"]["deterministic_promotion"])

    def test_evidence_no_autonomous(self):
        self.assertFalse(self.data["evidence"]["autonomous_promotion"])

    def test_evidence_no_recursive(self):
        self.assertFalse(self.data["evidence"]["recursive_promotion"])

    def test_evidence_no_embeddings(self):
        self.assertFalse(self.data["evidence"]["embeddings_generated"])

    def test_evidence_no_interpretation(self):
        self.assertFalse(self.data["evidence"]["interpretation_performed"])


# ---------------------------------------------------------------------------
# Router result artifact
# ---------------------------------------------------------------------------


class TestRouterResultArtifact(unittest.TestCase):
    def setUp(self):
        path = PROOF_DIR / "w0_memory_promotion_router_result_example.json"
        self.data = json.loads(path.read_text())

    def test_router_status_completed(self):
        self.assertEqual(self.data["router_status"], "completed")

    def test_action_type(self):
        self.assertEqual(
            self.data["router_decision"]["action_type"],
            "promote_safe_memory_candidate",
        )

    def test_capability_matched(self):
        self.assertEqual(
            self.data["router_decision"]["capability_matched"],
            "memory_promotion",
        )

    def test_adapter_selected(self):
        self.assertEqual(
            self.data["adapter_selected"],
            "windows_interactive_desktop_relay",
        )

    def test_runtime_target(self):
        self.assertEqual(
            self.data["runtime_target"],
            "local_worker_runtime_daemon",
        )

    def test_proof_reference_present(self):
        self.assertIn("runtime_proof_reference", self.data)
        ref = self.data["runtime_proof_reference"]
        self.assertEqual(ref["proof_status"], "completed")


# ---------------------------------------------------------------------------
# Cross-artifact integrity
# ---------------------------------------------------------------------------


class TestCrossArtifactIntegrity(unittest.TestCase):
    def setUp(self):
        self.review = json.loads((PROOF_DIR / "w0_governance_review_example.json").read_text())
        self.canonical = json.loads((PROOF_DIR / "w0_canonical_memory_example.json").read_text())
        self.rollback = json.loads((PROOF_DIR / "w0_memory_rollback_example.json").read_text())
        self.proof = json.loads(
            (PROOF_DIR / "w0_memory_promotion_runtime_proof_example.json").read_text()
        )
        self.result = json.loads(
            (PROOF_DIR / "w0_memory_promotion_router_result_example.json").read_text()
        )

    def test_review_to_canonical_link(self):
        self.assertEqual(self.canonical["governance_review_id"], self.review["review_id"])

    def test_canonical_to_rollback_link(self):
        self.assertEqual(
            self.rollback["canonical_memory_id"],
            self.canonical["canonical_memory_id"],
        )

    def test_rollback_id_in_canonical(self):
        self.assertEqual(self.canonical["rollback_reference"], self.rollback["rollback_id"])

    def test_candidate_chain(self):
        self.assertEqual(self.canonical["source_candidate_id"], self.review["candidate_id"])

    def test_proof_matches_result(self):
        ref = self.result["runtime_proof_reference"]
        self.assertEqual(ref["proof_id"], self.proof["proof_id"])
        self.assertEqual(ref["request_id"], self.proof["request_id"])

    def test_no_secrets_in_artifacts(self):
        for name in [
            "w0_governance_review_example.json",
            "w0_canonical_memory_example.json",
            "w0_memory_rollback_example.json",
            "w0_memory_promotion_runtime_proof_example.json",
            "w0_memory_promotion_router_result_example.json",
        ]:
            raw = (PROOF_DIR / name).read_text().lower()
            for keyword in [
                "password",
                "api_key",
                "secret_key",
                "bearer",
                "token_value",
            ]:
                self.assertNotIn(keyword, raw, f"secret keyword '{keyword}' in {name}")


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterministicPromotion(unittest.TestCase):
    def test_same_content_same_hash(self):
        h1 = hashlib.sha256(SIMULATED_CONTENT.encode("utf-8")).hexdigest()
        h2 = hashlib.sha256(SIMULATED_CONTENT.encode("utf-8")).hexdigest()
        self.assertEqual(h1, h2)

    def test_different_content_different_hash(self):
        h1 = hashlib.sha256(SIMULATED_CONTENT.encode("utf-8")).hexdigest()
        h2 = hashlib.sha256(b"different content").hexdigest()
        self.assertNotEqual(h1, h2)

    def test_canonical_hash_reproducible(self):
        canonical = json.loads((PROOF_DIR / "w0_canonical_memory_example.json").read_text())
        expected = hashlib.sha256(canonical["normalized_content"].encode("utf-8")).hexdigest()
        self.assertEqual(canonical["content_hash"], expected)


if __name__ == "__main__":
    unittest.main()
