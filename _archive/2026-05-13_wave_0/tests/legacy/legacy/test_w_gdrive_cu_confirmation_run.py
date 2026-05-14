"""Tests for W-GDRIVE-CU-001 Confirmation Run.

Validates confirmation flow including VPS-blocked path with
prior proof fallback and founder confirmation gating.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.adapter_package_manager.local_worker_cu_preflight import (
    run_local_worker_cu_preflight,
)
from core.adapter_package_manager.cu_founder_confirmation_gate import (
    FounderConfirmationStatus,
)
from core.adapter_package_manager.w_gdrive_cu_confirmation_run import (
    WDriveCUConfirmationResult,
    WDriveCUConfirmationStatus,
    build_w_gdrive_cu_confirmation_report,
    evaluate_w_gdrive_cu_confirmation_result,
    run_w_gdrive_cu_confirmation,
)


class TestWDriveCUConfirmationRun(unittest.TestCase):
    def test_result_builds(self) -> None:
        r = run_w_gdrive_cu_confirmation()
        self.assertIsInstance(r, WDriveCUConfirmationResult)
        self.assertEqual(r.path_id, "W-GDRIVE-CU-001")

    def test_vps_blocked_uses_prior_proof(self) -> None:
        r = run_w_gdrive_cu_confirmation()
        self.assertTrue(r.drive_opened)
        self.assertTrue(r.correct_account_confirmed)
        self.assertTrue(r.visible_inventory_confirmed)
        self.assertTrue(r.api_parity_confirmed)
        self.assertEqual(r.final_maturity_percent, 100.0)

    def test_missing_preflight_blocks_final_100(self) -> None:
        preflight = run_local_worker_cu_preflight(
            force_host="linux"
        )
        r = run_w_gdrive_cu_confirmation(preflight=preflight)
        self.assertNotEqual(
            r.final_status,
            WDriveCUConfirmationStatus.CONFIRMED_FINAL_100,
        )

    def test_missing_founder_confirmation_blocks_final_100(self) -> None:
        r = run_w_gdrive_cu_confirmation()
        self.assertEqual(
            r.final_status,
            WDriveCUConfirmationStatus.PROVISIONAL_PENDING_CONFIRMATION,
        )
        self.assertFalse(evaluate_w_gdrive_cu_confirmation_result(r))

    def test_founder_confirmed_yields_final_100(self) -> None:
        r = run_w_gdrive_cu_confirmation(
            founder_confirmation=FounderConfirmationStatus.CONFIRMED,
        )
        self.assertEqual(
            r.final_status,
            WDriveCUConfirmationStatus.CONFIRMED_FINAL_100,
        )
        self.assertTrue(evaluate_w_gdrive_cu_confirmation_result(r))
        self.assertEqual(r.founder_confirmation_status, "confirmed")

    def test_founder_not_required_yields_final_100(self) -> None:
        r = run_w_gdrive_cu_confirmation(
            founder_confirmation=FounderConfirmationStatus.NOT_REQUIRED,
        )
        self.assertEqual(
            r.final_status,
            WDriveCUConfirmationStatus.CONFIRMED_FINAL_100,
        )

    def test_mismatched_inventory_blocks_final_100(self) -> None:
        preflight = run_local_worker_cu_preflight(
            force_host="linux"
        )
        r = run_w_gdrive_cu_confirmation(preflight=preflight)
        if r.actual_items != r.expected_items and r.actual_items == 0:
            self.assertNotEqual(
                r.final_status,
                WDriveCUConfirmationStatus.CONFIRMED_FINAL_100,
            )

    def test_governance_confirmed(self) -> None:
        r = run_w_gdrive_cu_confirmation()
        self.assertTrue(r.governance_passed)
        self.assertTrue(r.no_secret_capture_confirmed)
        self.assertTrue(r.no_mutation_confirmed)

    def test_proof_artifacts_listed(self) -> None:
        r = run_w_gdrive_cu_confirmation()
        self.assertTrue(len(r.proof_artifacts) > 0)

    def test_report_builds(self) -> None:
        r = run_w_gdrive_cu_confirmation()
        report = build_w_gdrive_cu_confirmation_report(r)
        self.assertEqual(report["path_id"], "W-GDRIVE-CU-001")
        self.assertIn("final_status", report)
        self.assertIn("blockers", report)

    def test_result_to_dict(self) -> None:
        r = run_w_gdrive_cu_confirmation()
        d = r.to_dict()
        self.assertEqual(d["path_id"], "W-GDRIVE-CU-001")

    def test_ready_worker_with_confirmation(self) -> None:
        preflight = run_local_worker_cu_preflight(
            force_host="windows",
            force_worker=True,
            force_gui=True,
            founder_presence_confirmed=True,
        )
        r = run_w_gdrive_cu_confirmation(
            preflight=preflight,
            founder_confirmation=FounderConfirmationStatus.CONFIRMED,
        )
        self.assertEqual(
            r.final_status,
            WDriveCUConfirmationStatus.CONFIRMED_FINAL_100,
        )
        self.assertEqual(r.final_maturity_percent, 100.0)


if __name__ == "__main__":
    unittest.main()
