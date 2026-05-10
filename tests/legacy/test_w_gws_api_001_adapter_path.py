"""Tests for W-GWS-API-001 Adapter Path.

Validates path identity, capabilities, declaration status,
and excluded gaps for the API tab-aware extraction path.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.adapter_package_manager.full_path_maturity import PathDeclarationStatus
from core.adapter_package_manager.google_workspace_api_adapter_path import (
    EXCLUDED_GAPS,
    SUPPORTED_CAPABILITIES,
    W_GWS_API_001_PACKAGE_ID,
    W_GWS_API_001_PATH_ID,
    W_GWS_API_001_PATH_NAME,
    GoogleWorkspaceApiAdapterPath,
    build_google_workspace_api_tab_aware_path,
)


class TestGoogleWorkspaceApiAdapterPath(unittest.TestCase):
    def setUp(self) -> None:
        self.path = build_google_workspace_api_tab_aware_path()

    def test_path_builds(self) -> None:
        self.assertIsInstance(self.path, GoogleWorkspaceApiAdapterPath)

    def test_path_id_is_w_gws_api_001(self) -> None:
        self.assertEqual(self.path.path_id, "W-GWS-API-001")
        self.assertEqual(self.path.path_id, W_GWS_API_001_PATH_ID)

    def test_package_id_is_google_workspace(self) -> None:
        self.assertEqual(self.path.package_id, "google_workspace")
        self.assertEqual(self.path.package_id, W_GWS_API_001_PACKAGE_ID)

    def test_path_name(self) -> None:
        self.assertEqual(self.path.path_name, W_GWS_API_001_PATH_NAME)
        self.assertIn("Tab-Aware", self.path.path_name)

    def test_declaration_status_is_declared(self) -> None:
        self.assertEqual(
            self.path.declaration_status, PathDeclarationStatus.DECLARED
        )

    def test_current_status_complete(self) -> None:
        self.assertEqual(self.path.current_status, "complete")

    def test_target_maturity_is_100(self) -> None:
        self.assertEqual(self.path.target_maturity_percent, 100.0)

    def test_path_type_is_api(self) -> None:
        self.assertEqual(self.path.path_type, "API")

    def test_supports_tab_aware_extraction(self) -> None:
        self.assertIn(
            "google_docs_tab_aware_extraction",
            self.path.supported_capabilities,
        )

    def test_supports_child_tab_traversal(self) -> None:
        self.assertIn(
            "google_docs_child_tab_traversal",
            self.path.supported_capabilities,
        )

    def test_supports_canonical_emission(self) -> None:
        self.assertIn(
            "canonical_source_record_emission",
            self.path.supported_capabilities,
        )

    def test_supports_coverage_validation(self) -> None:
        self.assertIn(
            "ingestion_coverage_validation",
            self.path.supported_capabilities,
        )

    def test_all_supported_capabilities_present(self) -> None:
        self.assertEqual(
            self.path.supported_capabilities, SUPPORTED_CAPABILITIES
        )

    def test_excludes_cu_gap(self) -> None:
        self.assertTrue(
            any("CU" in g for g in self.path.excluded_gaps)
        )

    def test_excludes_mcp_gap(self) -> None:
        self.assertTrue(
            any("MCP" in g for g in self.path.excluded_gaps)
        )

    def test_excludes_cli_gap(self) -> None:
        self.assertTrue(
            any("CLI" in g for g in self.path.excluded_gaps)
        )

    def test_excluded_gaps_match_constant(self) -> None:
        self.assertEqual(self.path.excluded_gaps, EXCLUDED_GAPS)

    def test_known_gaps_empty_at_100(self) -> None:
        self.assertEqual(self.path.known_gaps, [])

    def test_has_auth_method(self) -> None:
        self.assertTrue(len(self.path.required_auth_methods) > 0)
        self.assertIn(
            "OAUTH_USER_CONSENT_OPAQUE_TOKEN_CACHE",
            self.path.required_auth_methods,
        )

    def test_has_tool_mastery_pack_reference(self) -> None:
        self.assertEqual(
            self.path.tool_mastery_pack, "google_docs_tool_mastery_pack"
        )

    def test_has_governance_policy_reference(self) -> None:
        self.assertEqual(
            self.path.governance_policy, "w_gws_api_001_governance_policy"
        )

    def test_has_canonical_contract_reference(self) -> None:
        self.assertEqual(
            self.path.canonical_contract,
            "w_gws_api_001_canonical_contract_mapping",
        )

    def test_has_test_references(self) -> None:
        self.assertTrue(len(self.path.tests) >= 4)
        self.assertIn("test_w_gws_api_001_adapter_path", self.path.tests)
        self.assertIn("test_w_gws_api_001_maturity", self.path.tests)

    def test_to_dict_roundtrip(self) -> None:
        d = self.path.to_dict()
        self.assertEqual(d["path_id"], "W-GWS-API-001")
        self.assertEqual(d["declaration_status"], "declared")
        self.assertEqual(d["current_status"], "complete")
        self.assertIsInstance(d["supported_capabilities"], list)


if __name__ == "__main__":
    unittest.main()
