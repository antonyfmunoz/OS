"""Tests for adapter_engine/external_interaction_contract.py — Phase 96.8A.1."""

import sys

sys.path.insert(0, "/opt/OS")

import unittest
from core.adapter_engine.external_interaction_contract import (
    ExternalInteraction,
    ExternalInteractionStatus,
    ExternalInteractionRisk,
    build_external_interaction,
    external_interaction_has_adapter,
    external_interaction_has_governance,
    external_interaction_has_proof_requirements,
    external_interaction_has_maturity_gate,
    external_interaction_has_capability_contract,
    external_interaction_is_validated,
    summarize_external_interaction,
)


class TestBuild(unittest.TestCase):
    def test_build_returns_interaction(self):
        ix = build_external_interaction(
            interaction_id="ix-001",
            external_system="Google Drive",
        )
        self.assertIsInstance(ix, ExternalInteraction)
        self.assertEqual(ix.interaction_id, "ix-001")

    def test_default_status_is_draft(self):
        ix = build_external_interaction(interaction_id="ix-002")
        self.assertEqual(ix.status, ExternalInteractionStatus.DRAFT)


class TestWithoutAdapterIsInvalid(unittest.TestCase):
    def test_no_adapter_package_or_family(self):
        ix = build_external_interaction(
            interaction_id="ix-010",
            external_system="Google Drive",
        )
        self.assertFalse(external_interaction_has_adapter(ix))
        self.assertFalse(external_interaction_is_validated(ix))


class TestWithoutGovernanceIsInvalid(unittest.TestCase):
    def test_no_governance(self):
        ix = build_external_interaction(
            interaction_id="ix-020",
            required_adapter_package="W-GDRIVE-API-001",
            capability_contract="read_drive_inventory",
            proof_requirements=["some_proof"],
            maturity_gate="mastery_assurance_gate",
        )
        self.assertFalse(external_interaction_has_governance(ix))
        self.assertFalse(external_interaction_is_validated(ix))


class TestWithoutProofIsInvalid(unittest.TestCase):
    def test_no_proof(self):
        ix = build_external_interaction(
            interaction_id="ix-030",
            required_adapter_package="W-GDRIVE-API-001",
            capability_contract="read_drive_inventory",
            governance_policy="cu_governance_v1",
            maturity_gate="mastery_assurance_gate",
        )
        self.assertFalse(external_interaction_has_proof_requirements(ix))
        self.assertFalse(external_interaction_is_validated(ix))


class TestWithoutMaturityGateIsInvalid(unittest.TestCase):
    def test_no_maturity_gate(self):
        ix = build_external_interaction(
            interaction_id="ix-040",
            required_adapter_package="W-GDRIVE-API-001",
            capability_contract="read_drive_inventory",
            governance_policy="cu_governance_v1",
            proof_requirements=["drive_visible"],
        )
        self.assertFalse(external_interaction_has_maturity_gate(ix))
        self.assertFalse(external_interaction_is_validated(ix))


class TestWithoutCapabilityContractIsInvalid(unittest.TestCase):
    def test_no_capability_contract(self):
        ix = build_external_interaction(
            interaction_id="ix-050",
            required_adapter_package="W-GDRIVE-API-001",
            governance_policy="cu_governance_v1",
            proof_requirements=["drive_visible"],
            maturity_gate="mastery_assurance_gate",
        )
        self.assertFalse(external_interaction_has_capability_contract(ix))
        self.assertFalse(external_interaction_is_validated(ix))


class TestValidInteractionPasses(unittest.TestCase):
    def test_full_interaction_is_validated(self):
        ix = build_external_interaction(
            interaction_id="ix-100",
            external_system="Google Drive",
            external_system_type="google_drive",
            adapter_category="saas",
            required_adapter_package="W-GDRIVE-API-001",
            required_adapter_family="google_workspace",
            capability_contract="read_drive_inventory",
            governance_policy="cu_governance_v1",
            proof_requirements=["drive_visible", "inventory_count"],
            maturity_gate="mastery_assurance_gate",
        )
        self.assertTrue(external_interaction_has_adapter(ix))
        self.assertTrue(external_interaction_has_governance(ix))
        self.assertTrue(external_interaction_has_proof_requirements(ix))
        self.assertTrue(external_interaction_has_maturity_gate(ix))
        self.assertTrue(external_interaction_has_capability_contract(ix))
        self.assertTrue(external_interaction_is_validated(ix))


class TestAdapterFamilySuffices(unittest.TestCase):
    def test_family_without_package_still_has_adapter(self):
        ix = build_external_interaction(
            interaction_id="ix-110",
            required_adapter_family="google_workspace",
        )
        self.assertTrue(external_interaction_has_adapter(ix))


class TestSummarize(unittest.TestCase):
    def test_summarize_returns_dict(self):
        ix = build_external_interaction(interaction_id="ix-200")
        s = summarize_external_interaction(ix)
        self.assertIsInstance(s, dict)
        self.assertIn("interaction_id", s)
        self.assertIn("is_validated", s)
        self.assertIn("has_adapter", s)


class TestToDict(unittest.TestCase):
    def test_to_dict_has_all_fields(self):
        ix = build_external_interaction(interaction_id="ix-300")
        d = ix.to_dict()
        self.assertIn("interaction_id", d)
        self.assertIn("external_system_type", d)
        self.assertIn("governance_policy", d)
        self.assertIn("maturity_gate", d)


if __name__ == "__main__":
    unittest.main()
