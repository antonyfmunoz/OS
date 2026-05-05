"""Tests for Google Drive Computer Use Adapter Package.

Validates W-GDRIVE-CU-001 is not mature without GUI proof
and has CU hardening gaps.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.adapter_package_manager.google_drive_cu_package import (
    W_GDRIVE_CU_001_ID,
    W_GDRIVE_CU_001_NAME,
    GoogleDriveCuPackage,
    build_google_drive_cu_package,
    drive_cu_blocks_w0_001,
    drive_cu_has_hardening_gaps,
    drive_cu_is_mature,
)


class TestGoogleDriveCuPackage(unittest.TestCase):
    def setUp(self) -> None:
        self.pkg = build_google_drive_cu_package()

    def test_builds(self) -> None:
        self.assertIsInstance(self.pkg, GoogleDriveCuPackage)

    def test_package_id(self) -> None:
        self.assertEqual(self.pkg.package_id, "W-GDRIVE-CU-001")
        self.assertEqual(self.pkg.package_id, W_GDRIVE_CU_001_ID)

    def test_package_name(self) -> None:
        self.assertEqual(self.pkg.package_name, W_GDRIVE_CU_001_NAME)

    def test_family_id(self) -> None:
        self.assertEqual(self.pkg.family_id, "google_workspace")

    def test_core_package_id(self) -> None:
        self.assertEqual(self.pkg.core_package_id, "W-GWS-CORE-001")

    def test_service_type_is_cu(self) -> None:
        self.assertEqual(self.pkg.service_type, "computer_use")

    def test_target_maturity_100(self) -> None:
        self.assertEqual(self.pkg.target_maturity_percent, 100.0)

    def test_not_mature_without_gui_proof(self) -> None:
        self.assertFalse(drive_cu_is_mature(self.pkg))
        self.assertFalse(self.pkg.is_mature)
        self.assertEqual(self.pkg.current_maturity_percent, 0.0)

    def test_has_hardening_gaps(self) -> None:
        self.assertTrue(drive_cu_has_hardening_gaps(self.pkg))
        self.assertTrue(len(self.pkg.hardening_gaps) >= 6)

    def test_blocks_w0_001(self) -> None:
        self.assertTrue(drive_cu_blocks_w0_001(self.pkg))

    def test_governance_no_mutation(self) -> None:
        self.assertIn("no_mutation", self.pkg.governance)

    def test_governance_no_credential_capture(self) -> None:
        self.assertIn("no_credential_capture", self.pkg.governance)

    def test_governance_no_screenshots_unless_approved(self) -> None:
        self.assertIn("no_screenshots_unless_approved", self.pkg.governance)

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
        self.assertEqual(d["package_id"], "W-GDRIVE-CU-001")
        self.assertFalse(d["is_mature"])
        self.assertTrue(len(d["hardening_gaps"]) > 0)


if __name__ == "__main__":
    unittest.main()
