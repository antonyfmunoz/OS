"""Tests for w_gdrive_cu_rerun_result.py — Phase 96.7H."""

import sys

sys.path.insert(0, "/opt/OS")

import unittest
from core.adapter_package_manager.w_gdrive_cu_rerun_result import (
    WDriveCURerunResult,
    WDriveCURerunStatus,
    build_w_gdrive_cu_rerun_result,
    evaluate_w_gdrive_cu_rerun_result,
    rerun_result_finalizes_drive_cu,
    summarize_w_gdrive_cu_rerun_result,
)


class TestRerunResultDefault(unittest.TestCase):
    def test_default_status_is_packet_created(self):
        result = WDriveCURerunResult()
        self.assertEqual(result.rerun_status, WDriveCURerunStatus.PACKET_CREATED)

    def test_default_not_finalized(self):
        result = WDriveCURerunResult()
        self.assertFalse(rerun_result_finalizes_drive_cu(result))

    def test_packet_created_does_not_finalize(self):
        result = build_w_gdrive_cu_rerun_result()
        evaluated = evaluate_w_gdrive_cu_rerun_result(result)
        self.assertFalse(rerun_result_finalizes_drive_cu(evaluated))


class TestRerunMissingFounder(unittest.TestCase):
    def test_founder_not_present_adds_blocker(self):
        result = build_w_gdrive_cu_rerun_result(
            founder_present=False,
            chrome_opened=True,
            drive_loaded=True,
            correct_account=True,
            correct_profile=True,
            inventory_captured=True,
            item_count=26,
            api_parity=True,
            method_cu_only=True,
        )
        evaluated = evaluate_w_gdrive_cu_rerun_result(result)
        self.assertIn("FOUNDER_NOT_PRESENT", evaluated.blockers)

    def test_dispatched_pending_when_all_pass_but_no_founder(self):
        result = build_w_gdrive_cu_rerun_result(
            founder_present=False,
            founder_confirmed=False,
            chrome_opened=True,
            drive_loaded=True,
            correct_account=True,
            correct_profile=True,
            inventory_captured=True,
            item_count=26,
            api_parity=True,
            method_cu_only=True,
        )
        evaluated = evaluate_w_gdrive_cu_rerun_result(result)
        self.assertEqual(evaluated.rerun_status, WDriveCURerunStatus.DISPATCHED_PENDING)


class TestRerunGovernanceFailure(unittest.TestCase):
    def test_governance_failure_blocks(self):
        result = build_w_gdrive_cu_rerun_result(
            founder_present=True,
            founder_confirmed=True,
            chrome_opened=True,
            drive_loaded=True,
            correct_account=True,
            correct_profile=True,
            inventory_captured=True,
            item_count=26,
            api_parity=True,
            method_cu_only=True,
            governance_clean=False,
        )
        evaluated = evaluate_w_gdrive_cu_rerun_result(result)
        self.assertEqual(evaluated.rerun_status, WDriveCURerunStatus.FAILED_GOVERNANCE)
        self.assertIn("GOVERNANCE_FAILURE", evaluated.blockers)
        self.assertFalse(rerun_result_finalizes_drive_cu(evaluated))


class TestRerunExecutionFailure(unittest.TestCase):
    def test_chrome_not_opened_fails(self):
        result = build_w_gdrive_cu_rerun_result(
            founder_present=True,
            founder_confirmed=True,
            chrome_opened=False,
            drive_loaded=True,
            correct_account=True,
            correct_profile=True,
            inventory_captured=True,
            item_count=26,
            api_parity=True,
            method_cu_only=True,
        )
        evaluated = evaluate_w_gdrive_cu_rerun_result(result)
        self.assertEqual(evaluated.rerun_status, WDriveCURerunStatus.FAILED_EXECUTION)
        self.assertIn("CHROME_NOT_OPENED", evaluated.blockers)

    def test_item_count_mismatch_fails(self):
        result = build_w_gdrive_cu_rerun_result(
            founder_present=True,
            founder_confirmed=True,
            chrome_opened=True,
            drive_loaded=True,
            correct_account=True,
            correct_profile=True,
            inventory_captured=True,
            item_count=20,
            api_parity=True,
            method_cu_only=True,
        )
        evaluated = evaluate_w_gdrive_cu_rerun_result(result)
        self.assertEqual(evaluated.rerun_status, WDriveCURerunStatus.FAILED_EXECUTION)
        blocker_text = " ".join(evaluated.blockers)
        self.assertIn("ITEM_COUNT_MISMATCH", blocker_text)

    def test_wrong_account_fails(self):
        result = build_w_gdrive_cu_rerun_result(
            founder_present=True,
            founder_confirmed=True,
            chrome_opened=True,
            drive_loaded=True,
            correct_account=False,
            correct_profile=True,
            inventory_captured=True,
            item_count=26,
            api_parity=True,
            method_cu_only=True,
        )
        evaluated = evaluate_w_gdrive_cu_rerun_result(result)
        self.assertEqual(evaluated.rerun_status, WDriveCURerunStatus.FAILED_EXECUTION)
        self.assertIn("WRONG_ACCOUNT", evaluated.blockers)


class TestRerunSuccess(unittest.TestCase):
    def test_full_rerun_founder_confirmed_finalizes(self):
        result = build_w_gdrive_cu_rerun_result(
            founder_present=True,
            founder_confirmed=True,
            chrome_opened=True,
            drive_loaded=True,
            correct_account=True,
            correct_profile=True,
            inventory_captured=True,
            item_count=26,
            api_parity=True,
            method_cu_only=True,
        )
        evaluated = evaluate_w_gdrive_cu_rerun_result(result)
        self.assertEqual(
            evaluated.rerun_status,
            WDriveCURerunStatus.COMPLETED_FOUNDER_CONFIRMED,
        )
        self.assertTrue(rerun_result_finalizes_drive_cu(evaluated))
        self.assertEqual(len(evaluated.blockers), 0)

    def test_founder_present_but_declined(self):
        result = build_w_gdrive_cu_rerun_result(
            founder_present=True,
            founder_confirmed=False,
            chrome_opened=True,
            drive_loaded=True,
            correct_account=True,
            correct_profile=True,
            inventory_captured=True,
            item_count=26,
            api_parity=True,
            method_cu_only=True,
        )
        evaluated = evaluate_w_gdrive_cu_rerun_result(result)
        self.assertEqual(
            evaluated.rerun_status,
            WDriveCURerunStatus.COMPLETED_FOUNDER_DECLINED,
        )
        self.assertFalse(rerun_result_finalizes_drive_cu(evaluated))


class TestSummarize(unittest.TestCase):
    def test_summarize_returns_dict(self):
        result = WDriveCURerunResult()
        summary = summarize_w_gdrive_cu_rerun_result(result)
        self.assertIsInstance(summary, dict)
        self.assertIn("rerun_status", summary)
        self.assertIn("finalizes_drive_cu", summary)


class TestToDict(unittest.TestCase):
    def test_to_dict_has_all_fields(self):
        result = WDriveCURerunResult()
        d = result.to_dict()
        self.assertIn("run_id", d)
        self.assertIn("rerun_status", d)
        self.assertIn("founder_present", d)
        self.assertIn("governance_no_gmail", d)
        self.assertIn("item_count", d)


if __name__ == "__main__":
    unittest.main()
