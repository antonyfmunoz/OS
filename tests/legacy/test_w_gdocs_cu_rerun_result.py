"""Tests for w_gdocs_cu_rerun_result.py — Phase 96.7H."""

import sys

sys.path.insert(0, "/opt/OS")

import unittest
from core.adapter_package_manager.w_gdocs_cu_rerun_result import (
    WDocsCURerunResult,
    WDocsCURerunStatus,
    build_w_gdocs_cu_rerun_result,
    evaluate_w_gdocs_cu_rerun_result,
    rerun_result_finalizes_docs_cu,
    summarize_w_gdocs_cu_rerun_result,
)


class TestRerunResultDefault(unittest.TestCase):
    def test_default_status_is_packet_created(self):
        result = WDocsCURerunResult()
        self.assertEqual(result.rerun_status, WDocsCURerunStatus.PACKET_CREATED)

    def test_default_not_finalized(self):
        result = WDocsCURerunResult()
        self.assertFalse(rerun_result_finalizes_docs_cu(result))


class TestRerunMissingFounder(unittest.TestCase):
    def test_founder_not_present_adds_blocker(self):
        result = build_w_gdocs_cu_rerun_result(
            founder_present=False,
            docs_openable=True,
            tabs_detectable=True,
            child_tabs_supported=True,
            content_extractable=True,
            scrolling_complete=True,
            per_doc_provenance=True,
            per_tab_provenance=True,
            empty_tabs_marked=True,
            inaccessible_tabs_marked=True,
            parity_against_api=True,
            method_cu_only=True,
        )
        evaluated = evaluate_w_gdocs_cu_rerun_result(result)
        self.assertIn("FOUNDER_NOT_PRESENT", evaluated.blockers)


class TestRerunGovernanceFailure(unittest.TestCase):
    def test_governance_failure_blocks(self):
        result = build_w_gdocs_cu_rerun_result(
            founder_present=True,
            founder_confirmed=True,
            docs_openable=True,
            tabs_detectable=True,
            child_tabs_supported=True,
            content_extractable=True,
            scrolling_complete=True,
            per_doc_provenance=True,
            per_tab_provenance=True,
            empty_tabs_marked=True,
            inaccessible_tabs_marked=True,
            parity_against_api=True,
            method_cu_only=True,
            governance_clean=False,
        )
        evaluated = evaluate_w_gdocs_cu_rerun_result(result)
        self.assertEqual(evaluated.rerun_status, WDocsCURerunStatus.FAILED_GOVERNANCE)
        self.assertIn("GOVERNANCE_FAILURE", evaluated.blockers)
        self.assertFalse(rerun_result_finalizes_docs_cu(evaluated))


class TestRerunGapsRemaining(unittest.TestCase):
    def test_missing_child_tabs_leaves_gap(self):
        result = build_w_gdocs_cu_rerun_result(
            founder_present=True,
            founder_confirmed=True,
            docs_openable=True,
            tabs_detectable=True,
            child_tabs_supported=False,
            content_extractable=True,
            scrolling_complete=True,
            per_doc_provenance=True,
            per_tab_provenance=True,
            empty_tabs_marked=True,
            inaccessible_tabs_marked=True,
            parity_against_api=True,
            method_cu_only=True,
        )
        evaluated = evaluate_w_gdocs_cu_rerun_result(result)
        self.assertIn("child_tabs_supported", evaluated.gaps_remaining)
        self.assertEqual(evaluated.rerun_status, WDocsCURerunStatus.COMPLETED_PARTIAL)
        self.assertFalse(rerun_result_finalizes_docs_cu(evaluated))

    def test_missing_content_extraction_leaves_gap(self):
        result = build_w_gdocs_cu_rerun_result(
            founder_present=True,
            founder_confirmed=True,
            docs_openable=True,
            tabs_detectable=True,
            child_tabs_supported=True,
            content_extractable=False,
            scrolling_complete=True,
            per_doc_provenance=True,
            per_tab_provenance=True,
            empty_tabs_marked=True,
            inaccessible_tabs_marked=True,
            parity_against_api=True,
            method_cu_only=True,
        )
        evaluated = evaluate_w_gdocs_cu_rerun_result(result)
        self.assertIn("content_extractable", evaluated.gaps_remaining)

    def test_missing_parity_leaves_gap(self):
        result = build_w_gdocs_cu_rerun_result(
            founder_present=True,
            founder_confirmed=True,
            docs_openable=True,
            tabs_detectable=True,
            child_tabs_supported=True,
            content_extractable=True,
            scrolling_complete=True,
            per_doc_provenance=True,
            per_tab_provenance=True,
            empty_tabs_marked=True,
            inaccessible_tabs_marked=True,
            parity_against_api=False,
            method_cu_only=True,
        )
        evaluated = evaluate_w_gdocs_cu_rerun_result(result)
        self.assertIn("parity_against_api", evaluated.gaps_remaining)

    def test_multiple_gaps_all_tracked(self):
        result = build_w_gdocs_cu_rerun_result(
            founder_present=True,
            founder_confirmed=True,
            docs_openable=True,
            tabs_detectable=True,
            child_tabs_supported=False,
            content_extractable=False,
            scrolling_complete=False,
            per_doc_provenance=True,
            per_tab_provenance=False,
            empty_tabs_marked=False,
            inaccessible_tabs_marked=False,
            parity_against_api=False,
            method_cu_only=True,
        )
        evaluated = evaluate_w_gdocs_cu_rerun_result(result)
        self.assertEqual(len(evaluated.gaps_remaining), 7)

    def test_all_seven_default_gaps(self):
        result = build_w_gdocs_cu_rerun_result(
            founder_present=True,
            founder_confirmed=True,
            docs_openable=True,
            tabs_detectable=True,
            per_doc_provenance=True,
            method_cu_only=True,
        )
        evaluated = evaluate_w_gdocs_cu_rerun_result(result)
        expected_gaps = [
            "child_tabs_supported",
            "content_extractable",
            "scrolling_complete",
            "per_tab_provenance_complete",
            "empty_tabs_marked",
            "inaccessible_tabs_marked",
            "parity_against_api",
        ]
        for gap in expected_gaps:
            self.assertIn(gap, evaluated.gaps_remaining)


class TestRerunBaseCheckFailure(unittest.TestCase):
    def test_docs_not_openable_fails_execution(self):
        result = build_w_gdocs_cu_rerun_result(
            founder_present=True,
            founder_confirmed=True,
            docs_openable=False,
            tabs_detectable=True,
            child_tabs_supported=True,
            content_extractable=True,
            scrolling_complete=True,
            per_doc_provenance=True,
            per_tab_provenance=True,
            empty_tabs_marked=True,
            inaccessible_tabs_marked=True,
            parity_against_api=True,
            method_cu_only=True,
        )
        evaluated = evaluate_w_gdocs_cu_rerun_result(result)
        self.assertEqual(evaluated.rerun_status, WDocsCURerunStatus.FAILED_EXECUTION)
        blocker_text = " ".join(evaluated.blockers)
        self.assertIn("docs_openable", blocker_text)


class TestRerunSuccess(unittest.TestCase):
    def test_full_rerun_founder_confirmed_finalizes(self):
        result = build_w_gdocs_cu_rerun_result(
            founder_present=True,
            founder_confirmed=True,
            docs_openable=True,
            tabs_detectable=True,
            child_tabs_supported=True,
            content_extractable=True,
            scrolling_complete=True,
            per_doc_provenance=True,
            per_tab_provenance=True,
            empty_tabs_marked=True,
            inaccessible_tabs_marked=True,
            parity_against_api=True,
            actual_docs=28,
            actual_tabs=321,
            actual_child_tabs=134,
            actual_words=283831,
            method_cu_only=True,
        )
        evaluated = evaluate_w_gdocs_cu_rerun_result(result)
        self.assertEqual(
            evaluated.rerun_status,
            WDocsCURerunStatus.COMPLETED_FOUNDER_CONFIRMED,
        )
        self.assertTrue(rerun_result_finalizes_docs_cu(evaluated))
        self.assertEqual(len(evaluated.gaps_remaining), 0)
        self.assertEqual(len(evaluated.blockers), 0)

    def test_founder_present_but_declined(self):
        result = build_w_gdocs_cu_rerun_result(
            founder_present=True,
            founder_confirmed=False,
            docs_openable=True,
            tabs_detectable=True,
            child_tabs_supported=True,
            content_extractable=True,
            scrolling_complete=True,
            per_doc_provenance=True,
            per_tab_provenance=True,
            empty_tabs_marked=True,
            inaccessible_tabs_marked=True,
            parity_against_api=True,
            method_cu_only=True,
        )
        evaluated = evaluate_w_gdocs_cu_rerun_result(result)
        self.assertEqual(
            evaluated.rerun_status,
            WDocsCURerunStatus.COMPLETED_FOUNDER_DECLINED,
        )
        self.assertFalse(rerun_result_finalizes_docs_cu(evaluated))


class TestSummarize(unittest.TestCase):
    def test_summarize_returns_dict(self):
        result = WDocsCURerunResult()
        summary = summarize_w_gdocs_cu_rerun_result(result)
        self.assertIsInstance(summary, dict)
        self.assertIn("rerun_status", summary)
        self.assertIn("finalizes_docs_cu", summary)
        self.assertIn("gaps_remaining", summary)
        self.assertIn("gaps", summary)


class TestToDict(unittest.TestCase):
    def test_to_dict_has_all_fields(self):
        result = WDocsCURerunResult()
        d = result.to_dict()
        self.assertIn("run_id", d)
        self.assertIn("rerun_status", d)
        self.assertIn("founder_present", d)
        self.assertIn("child_tabs_supported", d)
        self.assertIn("parity_against_api", d)
        self.assertIn("actual_words", d)
        self.assertIn("gaps_remaining", d)


if __name__ == "__main__":
    unittest.main()
