"""Tests for Google Docs Computer Use Adapter Package.

Validates W-GDOCS-CU-001 is not mature without tab/content/parity proof
and has CU hardening gaps.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.adapter_package_manager.google_docs_cu_package import (
    W_GDOCS_CU_001_ID,
    W_GDOCS_CU_001_NAME,
    GoogleDocsCuPackage,
    build_google_docs_cu_package,
    docs_cu_blocks_w0_001,
    docs_cu_has_hardening_gaps,
    docs_cu_is_mature,
    docs_cu_requires_api_parity,
)


class TestGoogleDocsCuPackage(unittest.TestCase):
    def setUp(self) -> None:
        self.pkg = build_google_docs_cu_package()

    def test_builds(self) -> None:
        self.assertIsInstance(self.pkg, GoogleDocsCuPackage)

    def test_package_id(self) -> None:
        self.assertEqual(self.pkg.package_id, "W-GDOCS-CU-001")
        self.assertEqual(self.pkg.package_id, W_GDOCS_CU_001_ID)

    def test_package_name(self) -> None:
        self.assertEqual(self.pkg.package_name, W_GDOCS_CU_001_NAME)

    def test_family_id(self) -> None:
        self.assertEqual(self.pkg.family_id, "google_workspace")

    def test_core_package_id(self) -> None:
        self.assertEqual(self.pkg.core_package_id, "W-GWS-CORE-001")

    def test_service_type_is_cu(self) -> None:
        self.assertEqual(self.pkg.service_type, "computer_use")

    def test_target_maturity_100(self) -> None:
        self.assertEqual(self.pkg.target_maturity_percent, 100.0)

    def test_not_mature_without_proof(self) -> None:
        self.assertFalse(docs_cu_is_mature(self.pkg))
        self.assertFalse(self.pkg.is_mature)
        self.assertEqual(self.pkg.current_maturity_percent, 0.0)

    def test_has_hardening_gaps(self) -> None:
        self.assertTrue(docs_cu_has_hardening_gaps(self.pkg))
        self.assertTrue(len(self.pkg.hardening_gaps) >= 9)

    def test_blocks_w0_001(self) -> None:
        self.assertTrue(docs_cu_blocks_w0_001(self.pkg))

    def test_requires_api_parity(self) -> None:
        self.assertTrue(docs_cu_requires_api_parity(self.pkg))
        self.assertEqual(self.pkg.parity_baseline, "W-GDOCS-API-001")

    def test_governance_no_mutation(self) -> None:
        self.assertIn("no_mutation", self.pkg.governance)

    def test_governance_no_credential_capture(self) -> None:
        self.assertIn("no_credential_capture", self.pkg.governance)

    def test_governance_no_playwright_unless_approved(self) -> None:
        self.assertIn(
            "no_playwright_cdp_unless_approved", self.pkg.governance
        )

    def test_capabilities_include_tab_detection(self) -> None:
        self.assertIn(
            "document_tabs_detectable", self.pkg.capabilities_required
        )

    def test_capabilities_include_parity(self) -> None:
        self.assertIn(
            "parity_against_w_gdocs_api_001_baseline",
            self.pkg.capabilities_required,
        )

    def test_missing_contract_mapping(self) -> None:
        self.assertFalse(self.pkg.has_contract_mapping)

    def test_missing_tests(self) -> None:
        self.assertFalse(self.pkg.has_tests)

    def test_missing_tool_mastery(self) -> None:
        self.assertFalse(self.pkg.has_tool_mastery)

    def test_missing_auth(self) -> None:
        self.assertFalse(self.pkg.has_auth)

    def test_to_dict(self) -> None:
        d = self.pkg.to_dict()
        self.assertEqual(d["package_id"], "W-GDOCS-CU-001")
        self.assertFalse(d["is_mature"])
        self.assertEqual(d["parity_baseline"], "W-GDOCS-API-001")


if __name__ == "__main__":
    unittest.main()
