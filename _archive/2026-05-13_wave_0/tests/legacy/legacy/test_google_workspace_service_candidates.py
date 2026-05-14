"""Tests for Google Workspace Future Service Candidates.

Validates future candidates are not declared for W0-001,
do not block W0-001, and target 100% when declared.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.adapter_package_manager.google_workspace_service_candidates import (
    FutureServiceCandidate,
    all_candidates_require_own_package,
    build_google_workspace_future_service_candidates,
    candidate_blocks_w0_001,
    candidate_is_declared_for_w0_001,
    no_candidate_blocks_w0_001,
)


class TestGoogleWorkspaceServiceCandidates(unittest.TestCase):
    def setUp(self) -> None:
        self.candidates = build_google_workspace_future_service_candidates()

    def test_candidates_build(self) -> None:
        self.assertIsInstance(self.candidates, list)
        self.assertTrue(len(self.candidates) >= 7)

    def test_gmail_is_candidate(self) -> None:
        gmail = [c for c in self.candidates if c.service_name == "Gmail"]
        self.assertEqual(len(gmail), 1)

    def test_sheets_is_candidate(self) -> None:
        sheets = [
            c for c in self.candidates if c.service_name == "Google Sheets"
        ]
        self.assertEqual(len(sheets), 1)

    def test_slides_is_candidate(self) -> None:
        slides = [
            c for c in self.candidates if c.service_name == "Google Slides"
        ]
        self.assertEqual(len(slides), 1)

    def test_calendar_is_candidate(self) -> None:
        cal = [
            c for c in self.candidates if c.service_name == "Google Calendar"
        ]
        self.assertEqual(len(cal), 1)

    def test_forms_is_candidate(self) -> None:
        forms = [
            c for c in self.candidates if c.service_name == "Google Forms"
        ]
        self.assertEqual(len(forms), 1)

    def test_meet_is_candidate(self) -> None:
        meet = [
            c for c in self.candidates if c.service_name == "Google Meet"
        ]
        self.assertEqual(len(meet), 1)

    def test_admin_is_candidate(self) -> None:
        admin = [c for c in self.candidates if "Admin" in c.service_name]
        self.assertEqual(len(admin), 1)

    def test_no_candidate_declared_for_w0_001(self) -> None:
        for c in self.candidates:
            self.assertFalse(
                candidate_is_declared_for_w0_001(c),
                f"{c.service_name} should not be declared for W0-001",
            )

    def test_no_candidate_blocks_w0_001(self) -> None:
        for c in self.candidates:
            self.assertFalse(
                candidate_blocks_w0_001(c),
                f"{c.service_name} should not block W0-001",
            )

    def test_no_candidate_blocks_aggregate(self) -> None:
        self.assertTrue(no_candidate_blocks_w0_001(self.candidates))

    def test_all_target_100_when_declared(self) -> None:
        for c in self.candidates:
            self.assertEqual(
                c.target_maturity_when_declared,
                100.0,
                f"{c.service_name} should target 100% when declared",
            )

    def test_all_require_own_package(self) -> None:
        self.assertTrue(all_candidates_require_own_package(self.candidates))

    def test_all_require_own_tool_mastery(self) -> None:
        for c in self.candidates:
            self.assertTrue(
                c.requires_own_tool_mastery_pack,
                f"{c.service_name} should require own TME pack",
            )

    def test_candidate_to_dict(self) -> None:
        d = self.candidates[0].to_dict()
        self.assertIn("service_name", d)
        self.assertFalse(d["declared_for_w0_001"])
        self.assertFalse(d["blocks_w0_001"])


if __name__ == "__main__":
    unittest.main()
