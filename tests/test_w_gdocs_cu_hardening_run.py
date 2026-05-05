"""Tests for W-GDOCS-CU-001 Hardening Run.

Validates hardening flow including VPS-blocked path with
prior Phase W0-001R proof and gap detection.
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
from core.adapter_package_manager.google_docs_cu_maturity import (
    DocsCUProof,
    evaluate_w_gdocs_cu_001_maturity,
)
from core.adapter_package_manager.w_gdocs_cu_hardening_run import (
    WDocsCUHardeningResult,
    WDocsCUHardeningStatus,
    build_w_gdocs_cu_hardening_report,
    evaluate_w_gdocs_cu_hardening_result,
    run_w_gdocs_cu_hardening,
)


class TestWDocsCUHardeningRun(unittest.TestCase):
    def test_result_builds(self) -> None:
        r = run_w_gdocs_cu_hardening()
        self.assertIsInstance(r, WDocsCUHardeningResult)
        self.assertEqual(r.path_id, "W-GDOCS-CU-001")

    def test_vps_blocked_uses_prior_proof(self) -> None:
        r = run_w_gdocs_cu_hardening()
        self.assertTrue(r.docs_openable)
        self.assertTrue(r.tabs_detectable)
        self.assertFalse(r.child_tabs_supported)
        self.assertFalse(r.content_extractable)

    def test_missing_tab_detection_blocks_final_100(self) -> None:
        r = run_w_gdocs_cu_hardening()
        maturity = evaluate_w_gdocs_cu_001_maturity()
        if not maturity.tabs_detectable:
            self.assertNotEqual(
                r.final_status,
                WDocsCUHardeningStatus.CONFIRMED_FINAL_100,
            )

    def test_missing_child_tab_support_blocks_final_100(self) -> None:
        r = run_w_gdocs_cu_hardening()
        self.assertFalse(r.child_tabs_supported)
        self.assertNotEqual(
            r.final_status,
            WDocsCUHardeningStatus.CONFIRMED_FINAL_100,
        )

    def test_missing_content_extraction_blocks_final_100(self) -> None:
        r = run_w_gdocs_cu_hardening()
        self.assertFalse(r.content_extractable)
        self.assertNotEqual(
            r.final_status,
            WDocsCUHardeningStatus.CONFIRMED_FINAL_100,
        )

    def test_missing_provenance_blocks_final_100(self) -> None:
        r = run_w_gdocs_cu_hardening()
        self.assertFalse(r.per_tab_provenance_complete)
        self.assertTrue(
            any("per_tab_provenance" in b for b in r.blockers)
        )

    def test_missing_parity_blocks_final_100(self) -> None:
        r = run_w_gdocs_cu_hardening()
        self.assertFalse(r.parity_against_api)
        self.assertTrue(
            any("parity_against_api" in b for b in r.blockers)
        )

    def test_partial_status_with_gaps(self) -> None:
        r = run_w_gdocs_cu_hardening()
        self.assertEqual(
            r.final_status,
            WDocsCUHardeningStatus.PARTIAL_NEEDS_HARDENING,
        )

    def test_hardening_work_orders_populated(self) -> None:
        r = run_w_gdocs_cu_hardening()
        self.assertTrue(len(r.hardening_work_orders) > 0)
        self.assertTrue(
            all(o.startswith("WO-GDOCS-CU-") for o in r.hardening_work_orders)
        )

    def test_governance_confirmed(self) -> None:
        r = run_w_gdocs_cu_hardening()
        self.assertTrue(r.governance_passed)
        self.assertTrue(r.no_secret_capture_confirmed)
        self.assertTrue(r.no_mutation_confirmed)

    def test_evaluate_not_final(self) -> None:
        r = run_w_gdocs_cu_hardening()
        self.assertFalse(evaluate_w_gdocs_cu_hardening_result(r))

    def test_report_builds(self) -> None:
        r = run_w_gdocs_cu_hardening()
        report = build_w_gdocs_cu_hardening_report(r)
        self.assertEqual(report["path_id"], "W-GDOCS-CU-001")
        self.assertIn("final_status", report)
        self.assertIn("hardening_work_orders", report)

    def test_result_to_dict(self) -> None:
        r = run_w_gdocs_cu_hardening()
        d = r.to_dict()
        self.assertEqual(d["path_id"], "W-GDOCS-CU-001")

    def test_maturity_percent_matches_evaluator(self) -> None:
        r = run_w_gdocs_cu_hardening()
        maturity = evaluate_w_gdocs_cu_001_maturity()
        self.assertEqual(
            r.final_maturity_percent,
            maturity.current_maturity_percent,
        )

    def test_ready_worker_complete_proof_confirmed(self) -> None:
        complete_proof = DocsCUProof(
            gui_ownership_proven=True,
            browser_profile_proven=True,
            account_verified=True,
            docs_openable=True,
            tabs_detectable=True,
            child_tabs_supported=True,
            content_extractable=True,
            scrolling_complete=True,
            per_doc_provenance_complete=True,
            per_tab_provenance_complete=True,
            empty_tabs_marked=True,
            inaccessible_tabs_marked=True,
            parity_against_api=True,
            no_mutation=True,
            no_credential_capture=True,
            no_screenshot_ocr=True,
        )
        maturity = evaluate_w_gdocs_cu_001_maturity(proof=complete_proof)
        self.assertTrue(maturity.is_100_percent_mature)


if __name__ == "__main__":
    unittest.main()
