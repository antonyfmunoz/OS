"""Tests for Google Drive API Adapter Package.

Validates W-GDRIVE-API-001 capabilities, governance, maturity,
and legacy provenance from W-GWS-API-001.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.adapter_package_manager.google_drive_api_package import (
    W_GDRIVE_API_001_ID,
    W_GDRIVE_API_001_NAME,
    GoogleDriveApiPackage,
    build_google_drive_api_package,
    drive_api_inherits_from_legacy,
    drive_api_is_read_only,
    drive_api_supports_inventory,
    drive_api_supports_metadata,
)


class TestGoogleDriveApiPackage(unittest.TestCase):
    def setUp(self) -> None:
        self.pkg = build_google_drive_api_package()

    def test_builds(self) -> None:
        self.assertIsInstance(self.pkg, GoogleDriveApiPackage)

    def test_package_id(self) -> None:
        self.assertEqual(self.pkg.package_id, "W-GDRIVE-API-001")
        self.assertEqual(self.pkg.package_id, W_GDRIVE_API_001_ID)

    def test_package_name(self) -> None:
        self.assertEqual(self.pkg.package_name, W_GDRIVE_API_001_NAME)

    def test_family_id(self) -> None:
        self.assertEqual(self.pkg.family_id, "google_workspace")

    def test_core_package_id(self) -> None:
        self.assertEqual(self.pkg.core_package_id, "W-GWS-CORE-001")

    def test_supports_drive_inventory(self) -> None:
        self.assertTrue(drive_api_supports_inventory(self.pkg))

    def test_supports_drive_metadata(self) -> None:
        self.assertTrue(drive_api_supports_metadata(self.pkg))

    def test_read_only_governance(self) -> None:
        self.assertTrue(drive_api_is_read_only(self.pkg))

    def test_no_credential_capture(self) -> None:
        self.assertIn("no_credential_capture", self.pkg.governance)

    def test_target_maturity_100(self) -> None:
        self.assertEqual(self.pkg.target_maturity_percent, 100.0)

    def test_is_mature(self) -> None:
        self.assertTrue(self.pkg.is_mature)
        self.assertEqual(self.pkg.current_maturity_percent, 100.0)

    def test_inherits_from_w_gws_api_001(self) -> None:
        self.assertTrue(drive_api_inherits_from_legacy(self.pkg))
        self.assertEqual(self.pkg.legacy_provenance, "W-GWS-API-001")

    def test_has_required_components(self) -> None:
        self.assertTrue(self.pkg.has_contract_mapping)
        self.assertTrue(self.pkg.has_governance)
        self.assertTrue(self.pkg.has_tests)
        self.assertTrue(self.pkg.has_tool_mastery)
        self.assertTrue(self.pkg.has_auth)

    def test_no_known_gaps(self) -> None:
        self.assertEqual(self.pkg.known_gaps, [])

    def test_capabilities_count(self) -> None:
        self.assertTrue(len(self.pkg.capabilities) >= 8)

    def test_to_dict(self) -> None:
        d = self.pkg.to_dict()
        self.assertEqual(d["package_id"], "W-GDRIVE-API-001")
        self.assertTrue(d["is_mature"])
        self.assertEqual(d["legacy_provenance"], "W-GWS-API-001")


if __name__ == "__main__":
    unittest.main()
