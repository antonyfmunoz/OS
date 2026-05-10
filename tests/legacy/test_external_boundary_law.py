"""Tests for adapter_engine/external_boundary_law.py — Phase 96.8A.1."""

import sys

sys.path.insert(0, "/opt/OS")

import unittest
from core.adapter_engine.external_interaction_contract import (
    build_external_interaction,
)
from core.adapter_engine.external_boundary_law import (
    BoundaryLawStatus,
    evaluate_external_boundary_law,
    external_boundary_blocks_execution,
    summarize_boundary_law_decision,
)


def _valid_interaction(**overrides):
    defaults = dict(
        interaction_id="law-valid",
        external_system="Google Drive",
        external_system_type="google_drive",
        adapter_category="saas",
        required_adapter_package="W-GDRIVE-API-001",
        capability_contract="read_drive_inventory",
        governance_policy="cu_governance_v1",
        mastery_requirements=["tool:google_drive_api"],
        proof_requirements=["drive_visible"],
        maturity_gate="mastery_assurance_gate",
    )
    defaults.update(overrides)
    return build_external_interaction(**defaults)


class TestDirectToolUseViolatesLaw(unittest.TestCase):
    def test_no_adapter_is_violation(self):
        ix = build_external_interaction(
            interaction_id="law-001",
            external_system="Google Drive",
            external_system_type="google_drive",
        )
        decision = evaluate_external_boundary_law(ix)
        self.assertFalse(decision.compliant)
        self.assertTrue(external_boundary_blocks_execution(decision))
        self.assertTrue(any("MISSING_ADAPTER" in v for v in decision.violations))


class TestDirectEnvironmentUseViolatesLaw(unittest.TestCase):
    def test_direct_tmux_use(self):
        ix = build_external_interaction(
            interaction_id="law-002",
            external_system="tmux",
            external_system_type="tmux",
        )
        decision = evaluate_external_boundary_law(ix)
        self.assertFalse(decision.compliant)
        self.assertTrue(external_boundary_blocks_execution(decision))

    def test_direct_local_gui_use(self):
        ix = build_external_interaction(
            interaction_id="law-003",
            external_system="Windows GUI",
            external_system_type="local_windows_gui",
        )
        decision = evaluate_external_boundary_law(ix)
        self.assertFalse(decision.compliant)


class TestDirectHumanApprovalUseViolatesLaw(unittest.TestCase):
    def test_direct_founder_confirmation(self):
        ix = build_external_interaction(
            interaction_id="law-004",
            external_system="Founder",
            external_system_type="founder_confirmation",
        )
        decision = evaluate_external_boundary_law(ix)
        self.assertFalse(decision.compliant)
        self.assertTrue(any("MISSING_ADAPTER" in v for v in decision.violations))


class TestDirectModelUseViolatesLaw(unittest.TestCase):
    def test_direct_anthropic_api(self):
        ix = build_external_interaction(
            interaction_id="law-005",
            external_system="Anthropic API",
            external_system_type="anthropic_api",
        )
        decision = evaluate_external_boundary_law(ix)
        self.assertFalse(decision.compliant)


class TestDirectDataSourceUseViolatesLaw(unittest.TestCase):
    def test_direct_database_use(self):
        ix = build_external_interaction(
            interaction_id="law-006",
            external_system="Neon Postgres",
            external_system_type="database",
        )
        decision = evaluate_external_boundary_law(ix)
        self.assertFalse(decision.compliant)

    def test_direct_filesystem_use(self):
        ix = build_external_interaction(
            interaction_id="law-007",
            external_system="Local Filesystem",
            external_system_type="filesystem",
        )
        decision = evaluate_external_boundary_law(ix)
        self.assertFalse(decision.compliant)


class TestCompliantInteraction(unittest.TestCase):
    def test_full_adapter_contract_governance_proof_maturity(self):
        ix = _valid_interaction(interaction_id="law-100")
        decision = evaluate_external_boundary_law(ix)
        self.assertTrue(decision.compliant)
        self.assertEqual(decision.status, BoundaryLawStatus.COMPLIANT)
        self.assertFalse(external_boundary_blocks_execution(decision))
        self.assertEqual(len(decision.violations), 0)


class TestMissingGovernanceBlocks(unittest.TestCase):
    def test_no_governance_policy(self):
        ix = _valid_interaction(interaction_id="law-200", governance_policy="")
        decision = evaluate_external_boundary_law(ix)
        self.assertFalse(decision.compliant)
        self.assertTrue(any("MISSING_GOVERNANCE" in v for v in decision.violations))


class TestMissingProofBlocks(unittest.TestCase):
    def test_no_proof_requirements(self):
        ix = _valid_interaction(interaction_id="law-300", proof_requirements=[])
        decision = evaluate_external_boundary_law(ix)
        self.assertFalse(decision.compliant)
        self.assertTrue(any("MISSING_PROOF" in v for v in decision.violations))


class TestMissingMaturityGateBlocks(unittest.TestCase):
    def test_no_maturity_gate(self):
        ix = _valid_interaction(interaction_id="law-400", maturity_gate="")
        decision = evaluate_external_boundary_law(ix)
        self.assertFalse(decision.compliant)
        self.assertTrue(any("MISSING_MATURITY" in v for v in decision.violations))


class TestUnknownExternalSystem(unittest.TestCase):
    def test_unknown_system_type(self):
        ix = build_external_interaction(
            interaction_id="law-500",
            external_system="Something",
            external_system_type="",
        )
        decision = evaluate_external_boundary_law(ix)
        self.assertFalse(decision.compliant)
        self.assertEqual(decision.status, BoundaryLawStatus.UNKNOWN_EXTERNAL_SYSTEM)


class TestSummarize(unittest.TestCase):
    def test_summarize_returns_dict(self):
        ix = _valid_interaction(interaction_id="law-600")
        decision = evaluate_external_boundary_law(ix)
        s = summarize_boundary_law_decision(decision)
        self.assertIsInstance(s, dict)
        self.assertIn("compliant", s)
        self.assertIn("violation_count", s)


if __name__ == "__main__":
    unittest.main()
