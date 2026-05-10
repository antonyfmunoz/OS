"""Tests for environment_bridge/result_ingestion.py — Phase 96.8A."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import unittest
from core.environment_bridge.result_ingestion import (
    BridgeResult,
    BridgeResultStatus,
    build_bridge_result,
    validate_bridge_result,
    result_satisfies_proof_requirements,
    result_has_governance_compliance,
    ingest_bridge_result,
    summarize_bridge_result,
)
from core.environment_bridge.work_packet import build_work_packet


class TestResultBuilds(unittest.TestCase):
    def test_build_returns_bridge_result(self):
        r = build_bridge_result(packet_id="r-001")
        self.assertIsInstance(r, BridgeResult)
        self.assertEqual(r.packet_id, "r-001")
        self.assertEqual(r.status, BridgeResultStatus.RECEIVED)


class TestMissingProofBlocks(unittest.TestCase):
    def test_no_proof_artifacts_blocks(self):
        r = build_bridge_result(
            packet_id="r-002",
            no_secret_confirmed=True,
            no_mutation_confirmed=True,
            proof_artifacts=[],
        )
        validated = validate_bridge_result(r)
        self.assertEqual(validated.status, BridgeResultStatus.PROOF_INCOMPLETE)


class TestGovernanceViolationBlocks(unittest.TestCase):
    def test_governance_violation_blocks(self):
        r = build_bridge_result(
            packet_id="r-003",
            no_secret_confirmed=True,
            no_mutation_confirmed=True,
            proof_artifacts=["proof.json"],
            governance_report={"no_gmail": True, "no_playwright": False},
        )
        validated = validate_bridge_result(r)
        self.assertEqual(validated.status, BridgeResultStatus.GOVERNANCE_VIOLATION)


class TestNoSecretNoMutationRequired(unittest.TestCase):
    def test_missing_secret_confirmation_invalid(self):
        r = build_bridge_result(
            packet_id="r-004",
            no_secret_confirmed=False,
            no_mutation_confirmed=True,
            proof_artifacts=["proof.json"],
        )
        validated = validate_bridge_result(r)
        self.assertEqual(validated.status, BridgeResultStatus.INVALID)
        self.assertIn("NO_SECRET_CONFIRMATION_MISSING", validated.errors)

    def test_missing_mutation_confirmation_invalid(self):
        r = build_bridge_result(
            packet_id="r-005",
            no_secret_confirmed=True,
            no_mutation_confirmed=False,
            proof_artifacts=["proof.json"],
        )
        validated = validate_bridge_result(r)
        self.assertEqual(validated.status, BridgeResultStatus.INVALID)
        self.assertIn("NO_MUTATION_CONFIRMATION_MISSING", validated.errors)


class TestValidResultIngests(unittest.TestCase):
    def test_valid_result_ingests(self):
        r = build_bridge_result(
            packet_id="r-006",
            no_secret_confirmed=True,
            no_mutation_confirmed=True,
            proof_artifacts=["drive_inventory.json", "governance.json"],
            governance_report={"no_gmail": True, "no_playwright": True},
        )
        validated = validate_bridge_result(r)
        self.assertEqual(validated.status, BridgeResultStatus.VALID)

        ingested = ingest_bridge_result(validated)
        self.assertEqual(ingested.status, BridgeResultStatus.INGESTED)


class TestGovernanceCompliance(unittest.TestCase):
    def test_compliant_result(self):
        r = build_bridge_result(
            packet_id="r-007",
            no_secret_confirmed=True,
            no_mutation_confirmed=True,
        )
        self.assertTrue(result_has_governance_compliance(r))

    def test_non_compliant_result(self):
        r = build_bridge_result(
            packet_id="r-008",
            no_secret_confirmed=False,
            no_mutation_confirmed=True,
        )
        self.assertFalse(result_has_governance_compliance(r))


class TestProofSatisfaction(unittest.TestCase):
    def test_valid_result_satisfies_proof(self):
        pkt = build_work_packet(
            packet_id="pkt-001",
            work_order_id="WO-001",
            title="Test",
            proof_requirements=["account_visible"],
        )
        r = build_bridge_result(
            packet_id="r-009",
            no_secret_confirmed=True,
            no_mutation_confirmed=True,
            proof_artifacts=["proof.json"],
        )
        r = validate_bridge_result(r)
        self.assertTrue(result_satisfies_proof_requirements(r, pkt))


class TestSummarize(unittest.TestCase):
    def test_summarize_returns_dict(self):
        r = build_bridge_result(packet_id="r-010")
        s = summarize_bridge_result(r)
        self.assertIsInstance(s, dict)
        self.assertIn("packet_id", s)
        self.assertIn("governance_compliant", s)


if __name__ == "__main__":
    unittest.main()
