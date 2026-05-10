"""Tests for Google Workspace Adapter Family.

Validates family structure, core package reference, declared W0-001
services, future candidates, and non-monolithic architecture.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.adapter_package_manager.adapter_family_contracts import (
    AdapterFamilyStatus,
    ServicePackageStatus,
    adapter_family_is_monolithic,
    family_can_be_fully_mature,
    list_declared_services,
    list_future_candidate_services,
)
from core.adapter_package_manager.google_workspace_family import (
    GWS_CORE_PACKAGE_ID,
    GWS_FAMILY_ID,
    GWS_FAMILY_NAME,
    build_google_workspace_adapter_family,
)


class TestGoogleWorkspaceFamily(unittest.TestCase):
    def setUp(self) -> None:
        self.family = build_google_workspace_adapter_family()

    def test_family_builds(self) -> None:
        self.assertIsNotNone(self.family)

    def test_family_id(self) -> None:
        self.assertEqual(self.family.family_id, "google_workspace")
        self.assertEqual(self.family.family_id, GWS_FAMILY_ID)

    def test_family_name(self) -> None:
        self.assertEqual(self.family.family_name, GWS_FAMILY_NAME)
        self.assertIn("Adapter Family", self.family.family_name)

    def test_core_package_id(self) -> None:
        self.assertEqual(self.family.core_package_id, "W-GWS-CORE-001")
        self.assertEqual(self.family.core_package_id, GWS_CORE_PACKAGE_ID)

    def test_family_is_not_monolithic(self) -> None:
        self.assertFalse(adapter_family_is_monolithic(self.family))

    def test_status_is_partial(self) -> None:
        self.assertEqual(self.family.status, AdapterFamilyStatus.PARTIAL)

    def test_drive_is_declared_for_w0_001(self) -> None:
        declared = list_declared_services(self.family)
        drive_pkgs = [s for s in declared if s.service_name == "Google Drive"]
        self.assertTrue(len(drive_pkgs) >= 1)

    def test_docs_is_declared_for_w0_001(self) -> None:
        declared = list_declared_services(self.family)
        docs_pkgs = [s for s in declared if s.service_name == "Google Docs"]
        self.assertTrue(len(docs_pkgs) >= 1)

    def test_gmail_is_future_candidate(self) -> None:
        candidates = list_future_candidate_services(self.family)
        gmail = [c for c in candidates if c.service_name == "Gmail"]
        self.assertEqual(len(gmail), 1)
        self.assertEqual(
            gmail[0].declaration_status, ServicePackageStatus.FUTURE_CANDIDATE
        )

    def test_sheets_is_future_candidate(self) -> None:
        candidates = list_future_candidate_services(self.family)
        sheets = [c for c in candidates if c.service_name == "Google Sheets"]
        self.assertEqual(len(sheets), 1)

    def test_slides_is_future_candidate(self) -> None:
        candidates = list_future_candidate_services(self.family)
        slides = [c for c in candidates if c.service_name == "Google Slides"]
        self.assertEqual(len(slides), 1)

    def test_calendar_is_future_candidate(self) -> None:
        candidates = list_future_candidate_services(self.family)
        cal = [c for c in candidates if c.service_name == "Google Calendar"]
        self.assertEqual(len(cal), 1)

    def test_future_candidates_do_not_block_w0_001(self) -> None:
        candidates = list_future_candidate_services(self.family)
        for c in candidates:
            self.assertFalse(
                c.blocks_current_test,
                f"{c.service_name} should not block W0-001",
            )

    def test_family_does_not_claim_full_suite_maturity(self) -> None:
        self.assertNotEqual(
            self.family.status, AdapterFamilyStatus.FULLY_MATURE
        )

    def test_family_cannot_be_fully_mature_with_cu_partial(self) -> None:
        self.assertFalse(family_can_be_fully_mature(self.family))

    def test_has_shared_auth_models(self) -> None:
        self.assertTrue(len(self.family.shared_auth_models) > 0)
        self.assertIn(
            "OAUTH_USER_CONSENT_OPAQUE_TOKEN_CACHE",
            self.family.shared_auth_models,
        )

    def test_has_shared_governance(self) -> None:
        self.assertTrue(len(self.family.shared_governance) > 0)
        self.assertIn("no_credential_capture", self.family.shared_governance)

    def test_has_shared_tool_mastery(self) -> None:
        self.assertTrue(len(self.family.shared_tool_mastery) > 0)

    def test_declared_service_count(self) -> None:
        declared = list_declared_services(self.family)
        self.assertEqual(len(declared), 4)

    def test_future_candidate_count(self) -> None:
        candidates = list_future_candidate_services(self.family)
        self.assertEqual(len(candidates), 7)

    def test_to_dict(self) -> None:
        d = self.family.to_dict()
        self.assertEqual(d["family_id"], "google_workspace")
        self.assertEqual(d["core_package_id"], "W-GWS-CORE-001")
        self.assertIsInstance(d["service_packages"], list)


if __name__ == "__main__":
    unittest.main()
