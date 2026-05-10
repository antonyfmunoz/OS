"""Tests for Google Docs CU Maturity Gate (W-GDOCS-CU-001).

Validates maturity decision construction, gap detection per check,
and that complete proof reaches 100% while Phase W0-001R proof
correctly scores ~56% with 7 known gaps.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.adapter_package_manager.google_docs_cu_maturity import (
    DocsCUProof,
    GoogleDocsCUMaturityDecision,
    build_w_gdocs_cu_001_gap_report,
    build_w_gdocs_cu_001_hardening_work_orders,
    evaluate_w_gdocs_cu_001_maturity,
    w_gdocs_cu_001_is_100_percent_mature,
)


def _complete_proof() -> DocsCUProof:
    return DocsCUProof(
        gui_ownership_proven=True,
        browser_profile_proven=True,
        account_verified=True,
        docs_openable=True,
        tabs_detectable=True,
        tabs_detected_count=8,
        tabs_expected_count=8,
        child_tabs_supported=True,
        content_extractable=True,
        scrolling_complete=True,
        per_doc_provenance_complete=True,
        per_tab_provenance_complete=True,
        empty_tabs_marked=True,
        inaccessible_tabs_marked=True,
        parity_docs=28,
        parity_tabs=321,
        parity_child_tabs=134,
        parity_words=283831,
        parity_against_api=True,
        no_mutation=True,
        no_credential_capture=True,
        no_screenshot_ocr=True,
        proof_source="complete_test_proof",
        proof_phase="test",
    )


class TestDocsCUMaturityDecision(unittest.TestCase):
    def test_maturity_decision_builds(self) -> None:
        d = evaluate_w_gdocs_cu_001_maturity()
        self.assertIsInstance(d, GoogleDocsCUMaturityDecision)
        self.assertEqual(d.package_id, "W-GDOCS-CU-001")

    def test_missing_proof_is_not_mature(self) -> None:
        empty = DocsCUProof()
        d = evaluate_w_gdocs_cu_001_maturity(proof=empty)
        self.assertFalse(d.is_100_percent_mature)
        self.assertEqual(d.current_status, "partial_needs_hardening")

    def test_docs_not_openable_is_not_mature(self) -> None:
        proof = _complete_proof()
        proof.docs_openable = False
        d = evaluate_w_gdocs_cu_001_maturity(proof=proof)
        self.assertFalse(d.is_100_percent_mature)
        self.assertIn("docs_openable", d.gaps_to_100)
        self.assertFalse(d.docs_openable)

    def test_tabs_not_detectable_is_not_mature(self) -> None:
        proof = _complete_proof()
        proof.tabs_detectable = False
        d = evaluate_w_gdocs_cu_001_maturity(proof=proof)
        self.assertFalse(d.is_100_percent_mature)
        self.assertIn("tabs_detectable", d.gaps_to_100)

    def test_child_tabs_unsupported_is_not_mature(self) -> None:
        proof = _complete_proof()
        proof.child_tabs_supported = False
        d = evaluate_w_gdocs_cu_001_maturity(proof=proof)
        self.assertFalse(d.is_100_percent_mature)
        self.assertIn("child_tabs_supported", d.gaps_to_100)

    def test_content_not_extractable_is_not_mature(self) -> None:
        proof = _complete_proof()
        proof.content_extractable = False
        d = evaluate_w_gdocs_cu_001_maturity(proof=proof)
        self.assertFalse(d.is_100_percent_mature)
        self.assertIn("content_extractable", d.gaps_to_100)

    def test_scrolling_incomplete_is_not_mature(self) -> None:
        proof = _complete_proof()
        proof.scrolling_complete = False
        d = evaluate_w_gdocs_cu_001_maturity(proof=proof)
        self.assertFalse(d.is_100_percent_mature)
        self.assertIn("scrolling_complete", d.gaps_to_100)

    def test_per_tab_provenance_missing_is_not_mature(self) -> None:
        proof = _complete_proof()
        proof.per_tab_provenance_complete = False
        d = evaluate_w_gdocs_cu_001_maturity(proof=proof)
        self.assertFalse(d.is_100_percent_mature)
        self.assertIn("per_tab_provenance_complete", d.gaps_to_100)

    def test_parity_missing_is_not_mature(self) -> None:
        proof = _complete_proof()
        proof.parity_against_api = False
        d = evaluate_w_gdocs_cu_001_maturity(proof=proof)
        self.assertFalse(d.is_100_percent_mature)
        self.assertIn("parity_against_api", d.gaps_to_100)

    def test_complete_proof_reaches_100(self) -> None:
        proof = _complete_proof()
        d = evaluate_w_gdocs_cu_001_maturity(proof=proof)
        self.assertTrue(d.is_100_percent_mature)
        self.assertEqual(d.current_maturity_percent, 100.0)
        self.assertEqual(d.current_status, "complete")
        self.assertEqual(d.gaps_to_100, [])
        self.assertEqual(d.blockers, [])

    def test_default_proof_is_not_100(self) -> None:
        d = evaluate_w_gdocs_cu_001_maturity()
        self.assertFalse(d.is_100_percent_mature)
        self.assertEqual(d.current_status, "partial_needs_hardening")

    def test_default_proof_has_7_gaps(self) -> None:
        d = evaluate_w_gdocs_cu_001_maturity()
        expected_gaps = {
            "child_tabs_supported",
            "content_extractable",
            "scrolling_complete",
            "per_tab_provenance_complete",
            "empty_tabs_marked",
            "inaccessible_tabs_marked",
            "parity_against_api",
        }
        self.assertEqual(set(d.gaps_to_100), expected_gaps)

    def test_default_proof_maturity_percent(self) -> None:
        d = evaluate_w_gdocs_cu_001_maturity()
        self.assertEqual(d.current_maturity_percent, 56.2)

    def test_governance_failure_blocks_maturity(self) -> None:
        proof = _complete_proof()
        proof.no_mutation = False
        d = evaluate_w_gdocs_cu_001_maturity(proof=proof)
        self.assertFalse(d.is_100_percent_mature)
        self.assertIn("governance_passed", d.gaps_to_100)
        self.assertFalse(d.governance_passed)

    def test_no_tool_mastery_blocks_maturity(self) -> None:
        proof = _complete_proof()
        d = evaluate_w_gdocs_cu_001_maturity(proof=proof, has_tool_mastery=False)
        self.assertFalse(d.is_100_percent_mature)
        self.assertIn("tool_mastery_passed", d.gaps_to_100)

    def test_no_tests_blocks_maturity(self) -> None:
        proof = _complete_proof()
        d = evaluate_w_gdocs_cu_001_maturity(proof=proof, has_tests=False)
        self.assertFalse(d.is_100_percent_mature)
        self.assertIn("tests_present", d.gaps_to_100)

    def test_convenience_is_mature_returns_false(self) -> None:
        self.assertFalse(w_gdocs_cu_001_is_100_percent_mature())

    def test_gap_report_default(self) -> None:
        report = build_w_gdocs_cu_001_gap_report()
        self.assertEqual(report["package_id"], "W-GDOCS-CU-001")
        self.assertFalse(report["is_100_percent"])
        self.assertEqual(len(report["gaps"]), 7)

    def test_hardening_work_orders_populated(self) -> None:
        orders = build_w_gdocs_cu_001_hardening_work_orders()
        self.assertEqual(len(orders), 7)
        self.assertTrue(all(o.startswith("WO-GDOCS-CU-") for o in orders))

    def test_hardening_work_orders_empty_when_complete(self) -> None:
        proof = _complete_proof()
        orders = build_w_gdocs_cu_001_hardening_work_orders(proof=proof)
        self.assertEqual(orders, [])

    def test_decision_to_dict(self) -> None:
        d = evaluate_w_gdocs_cu_001_maturity()
        out = d.to_dict()
        self.assertEqual(out["package_id"], "W-GDOCS-CU-001")
        self.assertFalse(out["is_100_percent_mature"])

    def test_proof_to_dict(self) -> None:
        proof = DocsCUProof(proof_phase="Phase W0-001R")
        out = proof.to_dict()
        self.assertEqual(out["proof_phase"], "Phase W0-001R")

    def test_content_extraction_blocker_in_blockers(self) -> None:
        d = evaluate_w_gdocs_cu_001_maturity()
        blocker_text = " ".join(d.blockers)
        self.assertIn("foreground", blocker_text.lower())

    def test_empty_tabs_marked_gap(self) -> None:
        proof = _complete_proof()
        proof.empty_tabs_marked = False
        d = evaluate_w_gdocs_cu_001_maturity(proof=proof)
        self.assertIn("empty_tabs_marked", d.gaps_to_100)

    def test_inaccessible_tabs_marked_gap(self) -> None:
        proof = _complete_proof()
        proof.inaccessible_tabs_marked = False
        d = evaluate_w_gdocs_cu_001_maturity(proof=proof)
        self.assertIn("inaccessible_tabs_marked", d.gaps_to_100)


if __name__ == "__main__":
    unittest.main()
