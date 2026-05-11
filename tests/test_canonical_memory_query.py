"""Tests for W0 canonical memory query proof -- Phase 96.8V.

Validates deterministic ordering, lineage reconstruction,
rollback traversal, scope enforcement, forbidden action blocking,
mutation blocking, interpretation blocking, and hash reproducibility.
"""

import json
import sys
import unittest
from pathlib import Path

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

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
from core.memory.canonical_memory_query_contracts import (
    ALLOWED_QUERY_SCOPES,
    FORBIDDEN_QUERY_ACTIONS,
    CanonicalMemoryQuery,
    QueryProofArtifact,
    QueryResultReference,
    QueryScope,
)
from core.runtime.adapter_registry_contracts import AdapterRegistry
from core.state.transformation_state_ledger import compute_hash
from runtime.interfaces.discord_interface_adapter_v1 import (
    COMMAND_ACTION_MAP,
    SUPPORTED_COMMANDS,
    build_work_packet_for_router,
)

REGISTRY_PATH = Path(_ROOT) / "data" / "registries" / "local_worker_adapter_registry_v1.json"
QUERY_CONFIG_PATH = Path(_ROOT) / "config" / "w0_canonical_memory_query_proof_v1.json"
PROOF_DIR = Path(_ROOT) / "data" / "runtime" / "canonical_memory_query_proofs"


# ---------------------------------------------------------------------------
# Command registration
# ---------------------------------------------------------------------------


class TestQueryMemoryCommandRegistered(unittest.TestCase):
    def test_command_in_supported_commands(self):
        self.assertIn("!query-memory", SUPPORTED_COMMANDS)

    def test_command_maps_to_action(self):
        self.assertEqual(
            COMMAND_ACTION_MAP["!query-memory"],
            "query_safe_memory_reference",
        )

    def test_action_type_allowed(self):
        self.assertIn("query_safe_memory_reference", ALLOWED_ACTION_TYPES)

    def test_capability_map_has_entry(self):
        self.assertIn("query_safe_memory_reference", ACTION_CAPABILITY_MAP)
        cap = ACTION_CAPABILITY_MAP["query_safe_memory_reference"]
        self.assertEqual(cap.capability_type, CapabilityType.CANONICAL_MEMORY_QUERY)
        self.assertFalse(cap.requires_gui)


# ---------------------------------------------------------------------------
# WorkPacket construction
# ---------------------------------------------------------------------------


class TestQueryMemoryWorkPacket(unittest.TestCase):
    def test_builds_work_packet(self):
        wp = build_work_packet_for_router(
            "!query-memory",
            query_scope="exact_memory_lookup",
            query_lookup_key="CMEM-001",
        )
        self.assertIsNotNone(wp)
        self.assertEqual(wp.action_type, "query_safe_memory_reference")
        self.assertTrue(wp.packet_id.startswith("REQ-W0-QUERY-"))

    def test_no_secret_capture(self):
        wp = build_work_packet_for_router("!query-memory")
        self.assertTrue(wp.payload["no_secret_capture"])

    def test_no_mutation(self):
        wp = build_work_packet_for_router("!query-memory")
        self.assertTrue(wp.payload["no_mutation"])

    def test_source_interface(self):
        wp = build_work_packet_for_router("!query-memory")
        self.assertEqual(wp.source_interface, "discord_interface_adapter_v1")


# ---------------------------------------------------------------------------
# Forbidden actions
# ---------------------------------------------------------------------------


class TestQueryForbiddenActionsBlocked(unittest.TestCase):
    def test_no_forbidden_actions_in_payload(self):
        wp = build_work_packet_for_router("!query-memory")
        payload_str = json.dumps(wp.payload).lower()
        for action in FORBIDDEN_QUERY_ACTIONS:
            self.assertNotIn(
                action,
                payload_str,
                f"forbidden action '{action}' found in payload",
            )

    def test_no_embedding_fields(self):
        wp = build_work_packet_for_router("!query-memory")
        payload = wp.payload
        self.assertNotIn("embedding_model", payload)
        self.assertNotIn("embedding_vector", payload)

    def test_no_interpretation_fields(self):
        wp = build_work_packet_for_router("!query-memory")
        payload = wp.payload
        self.assertNotIn("interpret", payload)
        self.assertNotIn("summarize", payload)

    def test_no_mutation_fields(self):
        wp = build_work_packet_for_router("!query-memory")
        payload = wp.payload
        self.assertNotIn("write_to_memory", payload)
        self.assertNotIn("canonical_target", payload)

    def test_no_expansion_fields(self):
        wp = build_work_packet_for_router("!query-memory")
        payload = wp.payload
        self.assertNotIn("expand_scope", payload)
        self.assertNotIn("auto_expand", payload)


# ---------------------------------------------------------------------------
# Arbitrary commands rejected
# ---------------------------------------------------------------------------


class TestArbitraryQueryCommandsRejected(unittest.TestCase):
    def test_unknown_commands_rejected(self):
        self.assertIsNone(build_work_packet_for_router("!query"))
        self.assertIsNone(build_work_packet_for_router("!search-memory"))
        self.assertIsNone(build_work_packet_for_router("!expand-memory"))

    def test_action_is_not_promotion(self):
        wp = build_work_packet_for_router("!query-memory")
        self.assertNotEqual(wp.action_type, "promote_safe_memory_candidate")

    def test_action_is_not_extraction(self):
        wp = build_work_packet_for_router("!query-memory")
        self.assertNotEqual(wp.action_type, "doc_extract_safe_test_doc")


# ---------------------------------------------------------------------------
# Router resolution
# ---------------------------------------------------------------------------


class TestRouterResolvesQueryAction(unittest.TestCase):
    def setUp(self):
        self.registry = AdapterRegistry.from_json_file(REGISTRY_PATH)
        self.router = ControlPlaneRouterV1(registry=self.registry, base_dir=Path(_ROOT))

    def test_dry_run_routes(self):
        wp = WorkPacket(
            packet_id="PKT-QUERY-TEST-001",
            action_type="query_safe_memory_reference",
        )
        result = self.router.route_dry_run(wp)
        self.assertEqual(result.router_status, RouterStatus.ROUTED)
        self.assertEqual(result.adapter_selected, "windows_interactive_desktop_relay")

    def test_capability_matched(self):
        wp = WorkPacket(
            packet_id="PKT-QUERY-TEST-002",
            action_type="query_safe_memory_reference",
        )
        result = self.router.route_dry_run(wp)
        self.assertEqual(
            result.router_decision.capability_matched,
            "canonical_memory_query",
        )

    def test_unknown_query_action_rejected(self):
        wp = WorkPacket(
            packet_id="PKT-QUERY-TEST-003",
            action_type="query_all_memories_globally",
        )
        result = self.router.route_dry_run(wp)
        self.assertNotEqual(result.router_status, RouterStatus.ROUTED)


# ---------------------------------------------------------------------------
# Query config
# ---------------------------------------------------------------------------


class TestQueryConfig(unittest.TestCase):
    def setUp(self):
        with open(QUERY_CONFIG_PATH) as f:
            self.config = json.load(f)

    def test_has_query_rules(self):
        self.assertIn("query_rules", self.config)

    def test_deterministic_ordering(self):
        self.assertTrue(self.config["query_rules"]["deterministic_ordering"])

    def test_lineage_required(self):
        self.assertTrue(self.config["query_rules"]["lineage_required"])

    def test_no_mutation(self):
        self.assertTrue(self.config["query_rules"]["no_mutation"])

    def test_no_interpretation(self):
        self.assertTrue(self.config["query_rules"]["no_interpretation"])

    def test_no_expansion(self):
        self.assertTrue(self.config["query_rules"]["no_expansion"])

    def test_query_proof_required(self):
        self.assertTrue(self.config["query_rules"]["query_proof_required"])

    def test_forbidden_actions_count(self):
        self.assertEqual(len(self.config["forbidden_actions"]), 11)

    def test_allowed_query_scopes(self):
        self.assertEqual(len(self.config["allowed_query_scopes"]), 5)

    def test_allowed_action_types(self):
        self.assertEqual(
            self.config["allowed_action_types"],
            ["query_safe_memory_reference"],
        )


# ---------------------------------------------------------------------------
# Deterministic query
# ---------------------------------------------------------------------------


class TestDeterministicQuery(unittest.TestCase):
    def test_same_query_same_hash(self):
        q1 = CanonicalMemoryQuery(
            query_id="Q1",
            scope=QueryScope.EXACT_MEMORY_LOOKUP,
            lookup_key="CMEM-001",
        )
        q2 = CanonicalMemoryQuery(
            query_id="Q2",
            scope=QueryScope.EXACT_MEMORY_LOOKUP,
            lookup_key="CMEM-001",
        )
        self.assertEqual(q1.compute_query_hash(), q2.compute_query_hash())

    def test_different_scope_different_hash(self):
        q1 = CanonicalMemoryQuery(
            query_id="Q1",
            scope=QueryScope.EXACT_MEMORY_LOOKUP,
            lookup_key="CMEM-001",
        )
        q2 = CanonicalMemoryQuery(
            query_id="Q2",
            scope=QueryScope.LINEAGE_TRAVERSAL,
            lookup_key="CMEM-001",
        )
        self.assertNotEqual(q1.compute_query_hash(), q2.compute_query_hash())

    def test_different_key_different_hash(self):
        q1 = CanonicalMemoryQuery(
            query_id="Q1",
            scope=QueryScope.EXACT_MEMORY_LOOKUP,
            lookup_key="CMEM-001",
        )
        q2 = CanonicalMemoryQuery(
            query_id="Q2",
            scope=QueryScope.EXACT_MEMORY_LOOKUP,
            lookup_key="CMEM-002",
        )
        self.assertNotEqual(q1.compute_query_hash(), q2.compute_query_hash())

    def test_same_results_same_hash(self):
        results = [{"canonical_memory_id": "CMEM-001", "content": "test"}]
        r1 = QueryResultReference(
            query_id="Q1",
            scope="exact_memory_lookup",
            result_count=1,
            results=results,
        )
        r2 = QueryResultReference(
            query_id="Q2",
            scope="exact_memory_lookup",
            result_count=1,
            results=results,
        )
        self.assertEqual(r1.compute_result_hash(), r2.compute_result_hash())

    def test_query_hash_excludes_timestamp(self):
        q1 = CanonicalMemoryQuery(
            query_id="Q1",
            scope=QueryScope.EXACT_MEMORY_LOOKUP,
            lookup_key="CMEM-001",
            timestamp="2026-01-01T00:00:00+00:00",
        )
        q2 = CanonicalMemoryQuery(
            query_id="Q2",
            scope=QueryScope.EXACT_MEMORY_LOOKUP,
            lookup_key="CMEM-001",
            timestamp="2026-12-31T23:59:59+00:00",
        )
        self.assertEqual(q1.compute_query_hash(), q2.compute_query_hash())


# ---------------------------------------------------------------------------
# Query proof artifact
# ---------------------------------------------------------------------------


class TestQueryProofArtifact(unittest.TestCase):
    def test_passed_when_no_violations(self):
        proof = QueryProofArtifact(
            proof_id="QP-001",
            query_id="Q-001",
            query_hash="abc",
            result_hash="def",
            scope="exact_memory_lookup",
            result_count=1,
            forbidden_actions_checked=11,
            forbidden_actions_found=0,
        )
        self.assertTrue(proof.passed)

    def test_fails_on_mutation(self):
        proof = QueryProofArtifact(
            proof_id="QP-002",
            query_id="Q-002",
            query_hash="abc",
            result_hash="def",
            scope="exact_memory_lookup",
            result_count=1,
            mutation_attempted=True,
        )
        self.assertFalse(proof.passed)

    def test_fails_on_interpretation(self):
        proof = QueryProofArtifact(
            proof_id="QP-003",
            query_id="Q-003",
            query_hash="abc",
            result_hash="def",
            scope="exact_memory_lookup",
            result_count=1,
            interpretation_attempted=True,
        )
        self.assertFalse(proof.passed)

    def test_fails_on_expansion(self):
        proof = QueryProofArtifact(
            proof_id="QP-004",
            query_id="Q-004",
            query_hash="abc",
            result_hash="def",
            scope="exact_memory_lookup",
            result_count=1,
            expansion_attempted=True,
        )
        self.assertFalse(proof.passed)

    def test_fails_on_forbidden_actions_found(self):
        proof = QueryProofArtifact(
            proof_id="QP-005",
            query_id="Q-005",
            query_hash="abc",
            result_hash="def",
            scope="exact_memory_lookup",
            result_count=1,
            forbidden_actions_found=2,
        )
        self.assertFalse(proof.passed)

    def test_to_dict_has_passed_field(self):
        proof = QueryProofArtifact(
            proof_id="QP-006",
            query_id="Q-006",
            query_hash="abc",
            result_hash="def",
            scope="exact_memory_lookup",
            result_count=1,
        )
        d = proof.to_dict()
        self.assertIn("passed", d)
        self.assertTrue(d["passed"])


# ---------------------------------------------------------------------------
# Proof artifacts
# ---------------------------------------------------------------------------


class TestProofArtifacts(unittest.TestCase):
    def test_canonical_query_example_exists(self):
        path = PROOF_DIR / "canonical_query_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertEqual(data["scope"], "exact_memory_lookup")
        self.assertTrue(data["no_mutation"])
        self.assertTrue(data["no_interpretation"])
        self.assertTrue(data["no_expansion"])

    def test_lineage_query_example_exists(self):
        path = PROOF_DIR / "lineage_query_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertIn("lineage", data)
        self.assertGreater(len(data["lineage"]), 0)
        self.assertIn("rollback_chain", data)

    def test_rollback_reference_query_example_exists(self):
        path = PROOF_DIR / "rollback_reference_query_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertEqual(data["scope"], "rollback_traversal")
        self.assertTrue(data["no_mutation_confirmed"])

    def test_query_proof_artifact_exists(self):
        path = PROOF_DIR / "query_proof_artifact_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertTrue(data["passed"])
        self.assertFalse(data["mutation_attempted"])
        self.assertFalse(data["interpretation_attempted"])
        self.assertFalse(data["expansion_attempted"])
        self.assertEqual(data["forbidden_actions_found"], 0)

    def test_lineage_has_governance_reference(self):
        path = PROOF_DIR / "lineage_query_example.json"
        data = json.loads(path.read_text())
        has_gov = any(lr.get("governance_reference", "") != "" for lr in data["lineage"])
        self.assertTrue(has_gov)

    def test_lineage_has_rollback_reference(self):
        path = PROOF_DIR / "lineage_query_example.json"
        data = json.loads(path.read_text())
        has_rollback = any(lr.get("rollback_reference", "") != "" for lr in data["lineage"])
        self.assertTrue(has_rollback)

    def test_no_secrets_in_artifacts(self):
        for name in [
            "canonical_query_example.json",
            "lineage_query_example.json",
            "rollback_reference_query_example.json",
            "query_proof_artifact_example.json",
        ]:
            raw = (PROOF_DIR / name).read_text().lower()
            for keyword in ["password", "api_key", "secret_key", "bearer", "token_value"]:
                self.assertNotIn(keyword, raw, f"secret keyword '{keyword}' in {name}")


# ---------------------------------------------------------------------------
# Cross-artifact integrity
# ---------------------------------------------------------------------------


class TestCrossArtifactIntegrity(unittest.TestCase):
    def setUp(self):
        self.query = json.loads((PROOF_DIR / "canonical_query_example.json").read_text())
        self.lineage = json.loads((PROOF_DIR / "lineage_query_example.json").read_text())
        self.proof = json.loads((PROOF_DIR / "query_proof_artifact_example.json").read_text())

    def test_query_id_matches_across_artifacts(self):
        self.assertEqual(self.query["query_id"], self.lineage["query_id"])
        self.assertEqual(self.query["query_id"], self.proof["query_id"])

    def test_query_hash_matches(self):
        self.assertEqual(self.lineage["query_hash"], self.proof["query_hash"])

    def test_result_hash_matches(self):
        self.assertEqual(self.lineage["result_hash"], self.proof["result_hash"])


# ---------------------------------------------------------------------------
# Query scope enforcement
# ---------------------------------------------------------------------------


class TestQueryScopes(unittest.TestCase):
    def test_all_allowed_scopes_enumerated(self):
        for scope in ALLOWED_QUERY_SCOPES:
            self.assertIsInstance(scope, QueryScope)

    def test_five_scopes_defined(self):
        self.assertEqual(len(ALLOWED_QUERY_SCOPES), 5)

    def test_forbidden_actions_count(self):
        self.assertEqual(len(FORBIDDEN_QUERY_ACTIONS), 11)


if __name__ == "__main__":
    unittest.main()
