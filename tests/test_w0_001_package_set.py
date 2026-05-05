"""Tests for W0-001 Adapter Package Set.

Validates package set composition, API/CU slice readiness,
triple-test readiness, and future candidate exclusion.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.adapter_package_manager.package_set_contracts import (
    PackageSetStatus,
    package_set_all_required_members_mature,
    package_set_api_ready,
    package_set_cu_ready,
)
from core.adapter_package_manager.w0_001_package_set import (
    W0_001_PACKAGE_SET_ID,
    W0001PackageSetReadiness,
    build_w0_001_adapter_package_set,
    build_w0_001_package_set_report,
    evaluate_w0_001_package_set_readiness,
    w0_001_api_slice_is_ready,
    w0_001_cu_slice_is_ready,
    w0_001_full_triple_test_ready,
)


class TestW0001PackageSet(unittest.TestCase):
    def setUp(self) -> None:
        self.ps = build_w0_001_adapter_package_set()

    def test_package_set_builds(self) -> None:
        self.assertIsNotNone(self.ps)

    def test_package_set_id(self) -> None:
        self.assertEqual(self.ps.package_set_id, "W0-001")
        self.assertEqual(self.ps.package_set_id, W0_001_PACKAGE_SET_ID)

    def test_family_id(self) -> None:
        self.assertEqual(self.ps.family_id, "google_workspace")

    def test_includes_core(self) -> None:
        ids = [m.package_id for m in self.ps.included_packages]
        self.assertIn("W-GWS-CORE-001", ids)

    def test_includes_drive_api(self) -> None:
        ids = [m.package_id for m in self.ps.included_packages]
        self.assertIn("W-GDRIVE-API-001", ids)

    def test_includes_docs_api(self) -> None:
        ids = [m.package_id for m in self.ps.included_packages]
        self.assertIn("W-GDOCS-API-001", ids)

    def test_includes_drive_cu(self) -> None:
        ids = [m.package_id for m in self.ps.included_packages]
        self.assertIn("W-GDRIVE-CU-001", ids)

    def test_includes_docs_cu(self) -> None:
        ids = [m.package_id for m in self.ps.included_packages]
        self.assertIn("W-GDOCS-CU-001", ids)

    def test_has_5_members(self) -> None:
        self.assertEqual(len(self.ps.included_packages), 5)

    def test_api_slice_ready(self) -> None:
        self.assertTrue(package_set_api_ready(self.ps))
        self.assertTrue(w0_001_api_slice_is_ready())

    def test_cu_slice_not_ready(self) -> None:
        self.assertFalse(package_set_cu_ready(self.ps))
        self.assertFalse(w0_001_cu_slice_is_ready())

    def test_not_all_mature(self) -> None:
        self.assertFalse(package_set_all_required_members_mature(self.ps))

    def test_full_triple_test_not_ready(self) -> None:
        self.assertFalse(w0_001_full_triple_test_ready())

    def test_status_is_api_ready(self) -> None:
        self.assertEqual(self.ps.current_status, PackageSetStatus.API_READY)

    def test_gmail_excluded(self) -> None:
        self.assertIn("Gmail", self.ps.excluded_future_candidates)

    def test_sheets_excluded(self) -> None:
        self.assertIn("Google Sheets", self.ps.excluded_future_candidates)

    def test_slides_excluded(self) -> None:
        self.assertIn("Google Slides", self.ps.excluded_future_candidates)

    def test_calendar_excluded(self) -> None:
        self.assertIn("Google Calendar", self.ps.excluded_future_candidates)

    def test_gmail_does_not_block(self) -> None:
        ids = [m.package_id for m in self.ps.included_packages]
        self.assertNotIn("W-GMAIL-001", ids)

    def test_sheets_does_not_block(self) -> None:
        ids = [m.package_id for m in self.ps.included_packages]
        self.assertNotIn("W-GSHEETS-001", ids)

    def test_has_blockers(self) -> None:
        self.assertTrue(len(self.ps.blockers) > 0)

    def test_cu_members_in_blockers(self) -> None:
        blocker_text = " ".join(self.ps.blockers)
        self.assertIn("W-GDRIVE-CU-001", blocker_text)
        self.assertIn("W-GDOCS-CU-001", blocker_text)


class TestW0001Readiness(unittest.TestCase):
    def test_readiness_evaluates(self) -> None:
        r = evaluate_w0_001_package_set_readiness()
        self.assertIsInstance(r, W0001PackageSetReadiness)

    def test_api_slice_ready(self) -> None:
        r = evaluate_w0_001_package_set_readiness()
        self.assertTrue(r.api_slice_ready)

    def test_cu_slice_not_ready(self) -> None:
        r = evaluate_w0_001_package_set_readiness()
        self.assertFalse(r.cu_slice_ready)

    def test_full_triple_test_not_ready(self) -> None:
        r = evaluate_w0_001_package_set_readiness()
        self.assertFalse(r.full_triple_test_ready)

    def test_memory_activation_not_ready(self) -> None:
        r = evaluate_w0_001_package_set_readiness()
        self.assertFalse(r.memory_activation_ready)

    def test_current_status_api_ready(self) -> None:
        r = evaluate_w0_001_package_set_readiness()
        self.assertEqual(r.current_status, "api_ready")

    def test_readiness_to_dict(self) -> None:
        r = evaluate_w0_001_package_set_readiness()
        d = r.to_dict()
        self.assertTrue(d["api_slice_ready"])
        self.assertFalse(d["cu_slice_ready"])

    def test_report_builds(self) -> None:
        report = build_w0_001_package_set_report()
        self.assertIn("package_set", report)
        self.assertIn("readiness", report)
        self.assertTrue(report["readiness"]["api_slice_ready"])


if __name__ == "__main__":
    unittest.main()
