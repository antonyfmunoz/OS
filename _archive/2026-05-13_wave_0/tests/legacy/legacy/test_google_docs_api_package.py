"""Tests for Google Docs API Adapter Package.

Validates W-GDOCS-API-001 tab-aware extraction requirements,
coverage contract, governance, and legacy provenance.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.adapter_package_manager.google_docs_api_package import (
    W_GDOCS_API_001_ID,
    W_GDOCS_API_001_NAME,
    W0_001_DOCS_COVERAGE,
    GoogleDocsApiPackage,
    build_google_docs_api_package,
    docs_api_has_w0_001_coverage,
    docs_api_inherits_from_legacy,
    docs_api_is_read_only,
    docs_api_rejects_first_tab_only,
    docs_api_requires_child_tabs_recursion,
    docs_api_requires_include_tabs_content,
    docs_api_requires_tabs_traversal,
)


class TestGoogleDocsApiPackage(unittest.TestCase):
    def setUp(self) -> None:
        self.pkg = build_google_docs_api_package()

    def test_builds(self) -> None:
        self.assertIsInstance(self.pkg, GoogleDocsApiPackage)

    def test_package_id(self) -> None:
        self.assertEqual(self.pkg.package_id, "W-GDOCS-API-001")
        self.assertEqual(self.pkg.package_id, W_GDOCS_API_001_ID)

    def test_package_name(self) -> None:
        self.assertEqual(self.pkg.package_name, W_GDOCS_API_001_NAME)

    def test_family_id(self) -> None:
        self.assertEqual(self.pkg.family_id, "google_workspace")

    def test_core_package_id(self) -> None:
        self.assertEqual(self.pkg.core_package_id, "W-GWS-CORE-001")

    def test_requires_include_tabs_content(self) -> None:
        self.assertTrue(docs_api_requires_include_tabs_content(self.pkg))

    def test_requires_tabs_traversal(self) -> None:
        self.assertTrue(docs_api_requires_tabs_traversal(self.pkg))

    def test_requires_child_tabs_recursion(self) -> None:
        self.assertTrue(docs_api_requires_child_tabs_recursion(self.pkg))

    def test_rejects_first_tab_only(self) -> None:
        self.assertTrue(docs_api_rejects_first_tab_only(self.pkg))

    def test_has_w0_001_coverage(self) -> None:
        self.assertTrue(docs_api_has_w0_001_coverage(self.pkg))

    def test_coverage_docs_28(self) -> None:
        self.assertEqual(self.pkg.w0_001_coverage["expected_docs"], 28)

    def test_coverage_tabs_321(self) -> None:
        self.assertEqual(self.pkg.w0_001_coverage["expected_tabs"], 321)

    def test_coverage_child_tabs_134(self) -> None:
        self.assertEqual(self.pkg.w0_001_coverage["expected_child_tabs"], 134)

    def test_coverage_words_283831(self) -> None:
        self.assertEqual(self.pkg.w0_001_coverage["expected_words"], 283831)

    def test_read_only_governance(self) -> None:
        self.assertTrue(docs_api_is_read_only(self.pkg))

    def test_no_credential_capture(self) -> None:
        self.assertIn("no_credential_capture", self.pkg.governance)

    def test_no_memory_promotion(self) -> None:
        self.assertIn("no_memory_promotion", self.pkg.governance)

    def test_target_maturity_100(self) -> None:
        self.assertEqual(self.pkg.target_maturity_percent, 100.0)

    def test_is_mature(self) -> None:
        self.assertTrue(self.pkg.is_mature)
        self.assertEqual(self.pkg.current_maturity_percent, 100.0)

    def test_inherits_from_w_gws_api_001(self) -> None:
        self.assertTrue(docs_api_inherits_from_legacy(self.pkg))
        self.assertEqual(self.pkg.legacy_provenance, "W-GWS-API-001")

    def test_has_required_components(self) -> None:
        self.assertTrue(self.pkg.has_contract_mapping)
        self.assertTrue(self.pkg.has_governance)
        self.assertTrue(self.pkg.has_tests)
        self.assertTrue(self.pkg.has_tool_mastery)
        self.assertTrue(self.pkg.has_auth)

    def test_no_known_gaps(self) -> None:
        self.assertEqual(self.pkg.known_gaps, [])

    def test_capabilities_include_tab_aware(self) -> None:
        self.assertIn(
            "documents_get_with_include_tabs_content", self.pkg.capabilities
        )

    def test_to_dict(self) -> None:
        d = self.pkg.to_dict()
        self.assertEqual(d["package_id"], "W-GDOCS-API-001")
        self.assertTrue(d["is_mature"])
        self.assertEqual(d["legacy_provenance"], "W-GWS-API-001")


if __name__ == "__main__":
    unittest.main()
