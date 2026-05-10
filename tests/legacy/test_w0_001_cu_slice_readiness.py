"""Tests for W0-001 CU Slice Readiness.

Validates combined Drive CU + Docs CU readiness evaluation,
including the distinction between READY, HARDENING_READY, and NOT_READY.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.adapter_package_manager.google_drive_cu_maturity import (
    DriveCUProof,
    evaluate_w_gdrive_cu_001_maturity,
)
from core.adapter_package_manager.google_docs_cu_maturity import (
    DocsCUProof,
    evaluate_w_gdocs_cu_001_maturity,
)
from core.adapter_package_manager.w0_001_cu_slice_readiness import (
    W0001CUSliceReadiness,
    W0001CUSliceStatus,
    evaluate_w0_001_cu_slice_readiness,
    summarize_w0_001_cu_slice_readiness,
    w0_001_cu_slice_blocks_full_triple_test,
)


def _complete_docs_proof() -> DocsCUProof:
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
    )


class TestCUSliceReadiness(unittest.TestCase):
    def test_readiness_builds(self) -> None:
        r = evaluate_w0_001_cu_slice_readiness()
        self.assertIsInstance(r, W0001CUSliceReadiness)

    def test_cu_slice_not_ready_if_drive_cu_incomplete(self) -> None:
        drive_d = evaluate_w_gdrive_cu_001_maturity(proof=DriveCUProof())
        docs_d = evaluate_w_gdocs_cu_001_maturity(proof=_complete_docs_proof())
        r = evaluate_w0_001_cu_slice_readiness(drive_d, docs_d)
        self.assertFalse(r.can_mark_cu_slice_ready)
        self.assertNotEqual(r.cu_slice_status, W0001CUSliceStatus.READY)

    def test_cu_slice_not_ready_if_docs_cu_incomplete(self) -> None:
        drive_d = evaluate_w_gdrive_cu_001_maturity()
        docs_d = evaluate_w_gdocs_cu_001_maturity()
        r = evaluate_w0_001_cu_slice_readiness(drive_d, docs_d)
        self.assertFalse(r.can_mark_cu_slice_ready)
        self.assertNotEqual(r.cu_slice_status, W0001CUSliceStatus.READY)

    def test_cu_slice_ready_when_both_100(self) -> None:
        drive_d = evaluate_w_gdrive_cu_001_maturity()
        docs_d = evaluate_w_gdocs_cu_001_maturity(proof=_complete_docs_proof())
        r = evaluate_w0_001_cu_slice_readiness(drive_d, docs_d)
        self.assertTrue(r.can_mark_cu_slice_ready)
        self.assertEqual(r.cu_slice_status, W0001CUSliceStatus.READY)
        self.assertTrue(r.can_run_cu_production_parity)
        self.assertTrue(r.can_run_cu_hardening_test)

    def test_hardening_ready_when_governance_passes_but_incomplete(self) -> None:
        drive_d = evaluate_w_gdrive_cu_001_maturity()
        docs_d = evaluate_w_gdocs_cu_001_maturity()
        self.assertTrue(drive_d.governance_passed)
        self.assertTrue(docs_d.governance_passed)
        r = evaluate_w0_001_cu_slice_readiness(drive_d, docs_d)
        self.assertEqual(r.cu_slice_status, W0001CUSliceStatus.HARDENING_READY)
        self.assertTrue(r.can_run_cu_hardening_test)
        self.assertFalse(r.can_run_cu_production_parity)

    def test_full_triple_test_blocked_when_cu_slice_incomplete(self) -> None:
        drive_d = evaluate_w_gdrive_cu_001_maturity()
        docs_d = evaluate_w_gdocs_cu_001_maturity()
        r = evaluate_w0_001_cu_slice_readiness(drive_d, docs_d)
        self.assertTrue(w0_001_cu_slice_blocks_full_triple_test(r))

    def test_full_triple_test_not_blocked_when_ready(self) -> None:
        drive_d = evaluate_w_gdrive_cu_001_maturity()
        docs_d = evaluate_w_gdocs_cu_001_maturity(proof=_complete_docs_proof())
        r = evaluate_w0_001_cu_slice_readiness(drive_d, docs_d)
        self.assertFalse(w0_001_cu_slice_blocks_full_triple_test(r))

    def test_blockers_populated_when_gaps(self) -> None:
        r = evaluate_w0_001_cu_slice_readiness()
        self.assertTrue(len(r.blockers) > 0)
        self.assertTrue(any("W-GDOCS-CU-001" in b for b in r.blockers))

    def test_next_actions_populated(self) -> None:
        r = evaluate_w0_001_cu_slice_readiness()
        self.assertTrue(len(r.next_actions) > 0)

    def test_notes_present(self) -> None:
        r = evaluate_w0_001_cu_slice_readiness()
        self.assertTrue(len(r.notes) > 0)

    def test_readiness_to_dict(self) -> None:
        r = evaluate_w0_001_cu_slice_readiness()
        d = r.to_dict()
        self.assertIn("cu_slice_status", d)
        self.assertIn("blockers", d)

    def test_summarize(self) -> None:
        r = evaluate_w0_001_cu_slice_readiness()
        s = summarize_w0_001_cu_slice_readiness(r)
        self.assertIn("cu_slice_status", s)
        self.assertIn("drive_cu", s)
        self.assertIn("docs_cu", s)
        self.assertIn("can_mark_ready", s)
        self.assertIn("blocker_count", s)

    def test_not_ready_when_governance_fails(self) -> None:
        proof = DriveCUProof(no_mutation=False)
        drive_d = evaluate_w_gdrive_cu_001_maturity(proof=proof)
        docs_d = evaluate_w_gdocs_cu_001_maturity()
        r = evaluate_w0_001_cu_slice_readiness(drive_d, docs_d)
        self.assertEqual(r.cu_slice_status, W0001CUSliceStatus.NOT_READY)

    def test_maturity_percentages_tracked(self) -> None:
        r = evaluate_w0_001_cu_slice_readiness()
        self.assertEqual(r.drive_cu_maturity, 100.0)
        self.assertEqual(r.docs_cu_maturity, 56.2)

    def test_status_enum_values(self) -> None:
        self.assertEqual(W0001CUSliceStatus.READY.value, "ready")
        self.assertEqual(W0001CUSliceStatus.HARDENING_READY.value, "hardening_ready")
        self.assertEqual(W0001CUSliceStatus.NOT_READY.value, "not_ready")


if __name__ == "__main__":
    unittest.main()
