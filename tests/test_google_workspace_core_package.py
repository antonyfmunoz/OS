"""Tests for Google Workspace Core Foundation Package.

Validates W-GWS-CORE-001 shared auth, no-secret policy,
shared governance, and scope limitations.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.adapter_package_manager.google_workspace_core_package import (
    W_GWS_CORE_001_ID,
    W_GWS_CORE_001_NAME,
    GoogleWorkspaceCorePackage,
    build_google_workspace_core_package,
    core_does_not_imply_gmail,
    core_does_not_imply_sheets,
    core_has_no_secret_policy,
    core_has_shared_auth,
    core_has_shared_governance,
)


class TestGoogleWorkspaceCorePackage(unittest.TestCase):
    def setUp(self) -> None:
        self.pkg = build_google_workspace_core_package()

    def test_builds(self) -> None:
        self.assertIsInstance(self.pkg, GoogleWorkspaceCorePackage)

    def test_package_id(self) -> None:
        self.assertEqual(self.pkg.package_id, "W-GWS-CORE-001")
        self.assertEqual(self.pkg.package_id, W_GWS_CORE_001_ID)

    def test_package_name(self) -> None:
        self.assertEqual(self.pkg.package_name, W_GWS_CORE_001_NAME)

    def test_has_shared_auth(self) -> None:
        self.assertTrue(core_has_shared_auth(self.pkg))
        self.assertIn(
            "OAUTH_USER_CONSENT_OPAQUE_TOKEN_CACHE",
            self.pkg.shared_auth_models,
        )

    def test_has_no_secret_policy(self) -> None:
        self.assertTrue(core_has_no_secret_policy(self.pkg))
        self.assertIn("no_credential_capture", self.pkg.no_secret_policy)
        self.assertIn("no_token_reading", self.pkg.no_secret_policy)
        self.assertIn("no_cookie_reading", self.pkg.no_secret_policy)

    def test_has_shared_governance(self) -> None:
        self.assertTrue(core_has_shared_governance(self.pkg))
        self.assertIn(
            "read_only_default", self.pkg.shared_governance_defaults
        )

    def test_has_rate_limit_doctrine(self) -> None:
        self.assertTrue(len(self.pkg.rate_limit_doctrine) > 0)
        self.assertIn(
            "respect_google_api_quota", self.pkg.rate_limit_doctrine
        )

    def test_does_not_imply_gmail_maturity(self) -> None:
        self.assertTrue(core_does_not_imply_gmail(self.pkg))
        self.assertFalse(self.pkg.implies_gmail_maturity)

    def test_does_not_imply_sheets_maturity(self) -> None:
        self.assertTrue(core_does_not_imply_sheets(self.pkg))
        self.assertFalse(self.pkg.implies_sheets_maturity)

    def test_does_not_imply_slides_maturity(self) -> None:
        self.assertFalse(self.pkg.implies_slides_maturity)

    def test_is_mature_for_w0_001(self) -> None:
        self.assertTrue(self.pkg.is_mature)
        self.assertEqual(self.pkg.current_maturity_percent, 100.0)

    def test_scoped_to_w0_001(self) -> None:
        self.assertTrue(self.pkg.scoped_to_w0_001)

    def test_target_maturity_100(self) -> None:
        self.assertEqual(self.pkg.target_maturity_percent, 100.0)

    def test_has_workspace_tool_mastery_pack(self) -> None:
        self.assertEqual(
            self.pkg.workspace_tool_mastery_pack,
            "google_workspace_tool_mastery_pack",
        )

    def test_governance_includes_instance_scope(self) -> None:
        self.assertIn(
            "instance_scope_preservation",
            self.pkg.shared_governance_defaults,
        )

    def test_governance_includes_no_memory_promotion(self) -> None:
        self.assertIn(
            "no_memory_promotion", self.pkg.shared_governance_defaults
        )

    def test_to_dict(self) -> None:
        d = self.pkg.to_dict()
        self.assertEqual(d["package_id"], "W-GWS-CORE-001")
        self.assertTrue(d["is_mature"])
        self.assertFalse(d["implies_gmail_maturity"])


if __name__ == "__main__":
    unittest.main()
