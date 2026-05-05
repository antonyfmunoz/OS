"""Tests for adapter_engine/adapter_boundary_validator.py — Phase 96.8A.1."""

import sys

sys.path.insert(0, "/opt/OS")

import unittest
from core.adapter_engine.external_interaction_contract import (
    build_external_interaction,
)
from core.adapter_engine.adapter_boundary_validator import (
    AdapterBoundaryValidationStatus,
    validate_adapter_boundary,
    adapter_boundary_blocks_execution,
)


def _full_interaction(**overrides):
    defaults = dict(
        interaction_id="abv-valid",
        external_system="Google Drive",
        external_system_type="google_drive",
        adapter_category="saas",
        required_adapter_package="W-GDRIVE-API-001",
        capability_contract="read_drive_inventory",
        governance_policy="cu_governance_v1",
        proof_requirements=["drive_visible"],
        maturity_gate="mastery_assurance_gate",
    )
    defaults.update(overrides)
    return build_external_interaction(**defaults)


class TestMissingAdapterBlocksExecution(unittest.TestCase):
    def test_no_adapter_blocks(self):
        ix = build_external_interaction(
            interaction_id="abv-001",
            external_system="Google Drive",
            external_system_type="google_drive",
            governance_policy="some_policy",
            proof_requirements=["proof"],
            maturity_gate="gate",
        )
        result = validate_adapter_boundary(ix)
        self.assertFalse(result.can_execute)
        self.assertTrue(adapter_boundary_blocks_execution(result))
        self.assertEqual(
            result.status,
            AdapterBoundaryValidationStatus.DIRECT_EXTERNAL_USE_DETECTED,
        )


class TestMissingEnvironmentAdapterBlocks(unittest.TestCase):
    def test_local_gui_without_adapter(self):
        ix = build_external_interaction(
            interaction_id="abv-010",
            external_system="Windows GUI",
            external_system_type="local_windows_gui",
            governance_policy="gui_governance",
            proof_requirements=["visible"],
            maturity_gate="gate",
        )
        result = validate_adapter_boundary(ix)
        self.assertFalse(result.can_execute)
        self.assertTrue(
            any("ENVIRONMENT_ADAPTER" in e or "DIRECT_EXTERNAL" in e for e in result.errors)
        )

    def test_tmux_without_adapter(self):
        ix = build_external_interaction(
            interaction_id="abv-011",
            external_system="tmux",
            external_system_type="tmux",
        )
        result = validate_adapter_boundary(ix)
        self.assertFalse(result.can_execute)


class TestMissingHumanApprovalAdapterBlocks(unittest.TestCase):
    def test_founder_confirmation_without_adapter(self):
        ix = build_external_interaction(
            interaction_id="abv-020",
            external_system="Founder",
            external_system_type="founder_confirmation",
        )
        result = validate_adapter_boundary(ix)
        self.assertFalse(result.can_execute)
        self.assertTrue(
            any("HUMAN_APPROVAL_ADAPTER" in e or "DIRECT_EXTERNAL" in e for e in result.errors)
        )


class TestMissingModelAdapterBlocks(unittest.TestCase):
    def test_anthropic_api_without_adapter(self):
        ix = build_external_interaction(
            interaction_id="abv-030",
            external_system="Anthropic API",
            external_system_type="anthropic_api",
        )
        result = validate_adapter_boundary(ix)
        self.assertFalse(result.can_execute)


class TestMissingDataSourceAdapterBlocks(unittest.TestCase):
    def test_database_without_adapter(self):
        ix = build_external_interaction(
            interaction_id="abv-040",
            external_system="Neon Postgres",
            external_system_type="database",
        )
        result = validate_adapter_boundary(ix)
        self.assertFalse(result.can_execute)

    def test_filesystem_without_adapter(self):
        ix = build_external_interaction(
            interaction_id="abv-041",
            external_system="Local Filesystem",
            external_system_type="filesystem",
        )
        result = validate_adapter_boundary(ix)
        self.assertFalse(result.can_execute)


class TestMissingGovernanceBlocks(unittest.TestCase):
    def test_no_governance(self):
        ix = _full_interaction(
            interaction_id="abv-050",
            governance_policy="",
        )
        result = validate_adapter_boundary(ix)
        self.assertFalse(result.can_execute)
        self.assertTrue(any("GOVERNANCE_MISSING" in e for e in result.errors))


class TestMissingProofBlocks(unittest.TestCase):
    def test_no_proof(self):
        ix = _full_interaction(
            interaction_id="abv-060",
            proof_requirements=[],
        )
        result = validate_adapter_boundary(ix)
        self.assertFalse(result.can_execute)
        self.assertTrue(any("PROOF_MISSING" in e for e in result.errors))


class TestValidBoundaryAllowsExecution(unittest.TestCase):
    def test_full_valid_interaction(self):
        ix = _full_interaction(interaction_id="abv-100")
        result = validate_adapter_boundary(ix)
        self.assertTrue(result.can_execute)
        self.assertEqual(result.status, AdapterBoundaryValidationStatus.VALID)
        self.assertFalse(adapter_boundary_blocks_execution(result))

    def test_environment_with_adapter(self):
        ix = _full_interaction(
            interaction_id="abv-110",
            external_system="WSL",
            external_system_type="local_wsl",
            adapter_category="environment",
            required_adapter_package="env-bridge-local-wsl",
        )
        result = validate_adapter_boundary(ix)
        self.assertTrue(result.can_execute)

    def test_human_approval_with_adapter(self):
        ix = _full_interaction(
            interaction_id="abv-120",
            external_system="Founder",
            external_system_type="founder_confirmation",
            adapter_category="human_approval",
            required_adapter_package="human-approval-founder",
        )
        result = validate_adapter_boundary(ix)
        self.assertTrue(result.can_execute)

    def test_model_with_adapter(self):
        ix = _full_interaction(
            interaction_id="abv-130",
            external_system="Anthropic API",
            external_system_type="anthropic_api",
            adapter_category="model",
            required_adapter_package="model-anthropic-001",
        )
        result = validate_adapter_boundary(ix)
        self.assertTrue(result.can_execute)


class TestToDict(unittest.TestCase):
    def test_to_dict_has_fields(self):
        ix = _full_interaction(interaction_id="abv-200")
        result = validate_adapter_boundary(ix)
        d = result.to_dict()
        self.assertIn("can_execute", d)
        self.assertIn("status", d)
        self.assertIn("errors", d)


if __name__ == "__main__":
    unittest.main()
