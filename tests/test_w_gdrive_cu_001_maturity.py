"""Tests for Google Drive CU Maturity Gate (W-GDRIVE-CU-001).

Validates maturity decision construction, gap detection per check,
and that complete Phase 95 proof reaches 100%.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.adapter_package_manager.google_drive_cu_maturity import (
    DriveCUProof,
    GoogleDriveCUMaturityDecision,
    build_w_gdrive_cu_001_gap_report,
    build_w_gdrive_cu_001_hardening_work_orders,
    evaluate_w_gdrive_cu_001_maturity,
    evaluate_w_gdrive_cu_001_maturity_with_proof_audit,
    w_gdrive_cu_001_final_maturity_requires_auditable_proof,
    w_gdrive_cu_001_is_100_percent_mature,
)
from core.adapter_package_manager.cu_proof_audit import (
    CUProofAuditResult,
    CUProofQualityStatus,
    audit_w_gdrive_cu_001_proof,
)


class TestDriveCUMaturityDecision(unittest.TestCase):
    def test_maturity_decision_builds(self) -> None:
        d = evaluate_w_gdrive_cu_001_maturity()
        self.assertIsInstance(d, GoogleDriveCUMaturityDecision)
        self.assertEqual(d.package_id, "W-GDRIVE-CU-001")

    def test_missing_proof_is_not_mature(self) -> None:
        empty = DriveCUProof()
        d = evaluate_w_gdrive_cu_001_maturity(proof=empty)
        self.assertFalse(d.is_100_percent_mature)
        self.assertEqual(d.current_status, "partial_needs_hardening")
        self.assertTrue(len(d.gaps_to_100) > 0)

    def test_drive_not_visible_is_not_mature(self) -> None:
        proof = DriveCUProof(
            gui_ownership_proven=True,
            browser_profile_proven=True,
            account_verified=True,
            drive_visible=False,
            inventory_extractable=True,
            metadata_extractable=True,
            provenance_complete=True,
            parity_against_api=True,
        )
        d = evaluate_w_gdrive_cu_001_maturity(proof=proof)
        self.assertFalse(d.is_100_percent_mature)
        self.assertIn("drive_visible", d.gaps_to_100)
        self.assertFalse(d.drive_visible)

    def test_inventory_not_extractable_is_not_mature(self) -> None:
        proof = DriveCUProof(
            gui_ownership_proven=True,
            browser_profile_proven=True,
            account_verified=True,
            drive_visible=True,
            inventory_extractable=False,
            metadata_extractable=True,
            provenance_complete=True,
            parity_against_api=True,
        )
        d = evaluate_w_gdrive_cu_001_maturity(proof=proof)
        self.assertFalse(d.is_100_percent_mature)
        self.assertIn("inventory_extractable", d.gaps_to_100)

    def test_metadata_missing_is_not_mature(self) -> None:
        proof = DriveCUProof(
            gui_ownership_proven=True,
            browser_profile_proven=True,
            account_verified=True,
            drive_visible=True,
            inventory_extractable=True,
            metadata_extractable=False,
            provenance_complete=True,
            parity_against_api=True,
        )
        d = evaluate_w_gdrive_cu_001_maturity(proof=proof)
        self.assertFalse(d.is_100_percent_mature)
        self.assertIn("metadata_extractable", d.gaps_to_100)

    def test_provenance_missing_is_not_mature(self) -> None:
        proof = DriveCUProof(
            gui_ownership_proven=True,
            browser_profile_proven=True,
            account_verified=True,
            drive_visible=True,
            inventory_extractable=True,
            metadata_extractable=True,
            provenance_complete=False,
            parity_against_api=True,
        )
        d = evaluate_w_gdrive_cu_001_maturity(proof=proof)
        self.assertFalse(d.is_100_percent_mature)
        self.assertIn("provenance_complete", d.gaps_to_100)

    def test_parity_missing_is_not_mature(self) -> None:
        proof = DriveCUProof(
            gui_ownership_proven=True,
            browser_profile_proven=True,
            account_verified=True,
            drive_visible=True,
            inventory_extractable=True,
            metadata_extractable=True,
            provenance_complete=True,
            parity_against_api=False,
        )
        d = evaluate_w_gdrive_cu_001_maturity(proof=proof)
        self.assertFalse(d.is_100_percent_mature)
        self.assertIn("parity_against_api", d.gaps_to_100)

    def test_complete_proof_reaches_100(self) -> None:
        d = evaluate_w_gdrive_cu_001_maturity()
        self.assertTrue(d.is_100_percent_mature)
        self.assertEqual(d.current_maturity_percent, 100.0)
        self.assertEqual(d.current_status, "complete")
        self.assertEqual(d.gaps_to_100, [])
        self.assertEqual(d.blockers, [])

    def test_governance_failure_blocks_maturity(self) -> None:
        proof = DriveCUProof(
            gui_ownership_proven=True,
            browser_profile_proven=True,
            account_verified=True,
            drive_visible=True,
            inventory_extractable=True,
            metadata_extractable=True,
            provenance_complete=True,
            parity_against_api=True,
            no_mutation=False,
        )
        d = evaluate_w_gdrive_cu_001_maturity(proof=proof)
        self.assertFalse(d.is_100_percent_mature)
        self.assertIn("governance_passed", d.gaps_to_100)
        self.assertFalse(d.governance_passed)

    def test_no_tool_mastery_blocks_maturity(self) -> None:
        d = evaluate_w_gdrive_cu_001_maturity(has_tool_mastery=False)
        self.assertFalse(d.is_100_percent_mature)
        self.assertIn("tool_mastery_passed", d.gaps_to_100)

    def test_no_tests_blocks_maturity(self) -> None:
        d = evaluate_w_gdrive_cu_001_maturity(has_tests=False)
        self.assertFalse(d.is_100_percent_mature)
        self.assertIn("tests_present", d.gaps_to_100)

    def test_convenience_is_mature_returns_true(self) -> None:
        self.assertTrue(w_gdrive_cu_001_is_100_percent_mature())

    def test_gap_report_complete(self) -> None:
        report = build_w_gdrive_cu_001_gap_report()
        self.assertEqual(report["package_id"], "W-GDRIVE-CU-001")
        self.assertTrue(report["is_100_percent"])
        self.assertEqual(report["current_maturity"], 100.0)
        self.assertEqual(report["gaps"], [])

    def test_gap_report_with_gaps(self) -> None:
        proof = DriveCUProof()
        report = build_w_gdrive_cu_001_gap_report(proof=proof)
        self.assertFalse(report["is_100_percent"])
        self.assertTrue(len(report["gaps"]) > 0)

    def test_hardening_work_orders_empty_when_complete(self) -> None:
        orders = build_w_gdrive_cu_001_hardening_work_orders()
        self.assertEqual(orders, [])

    def test_hardening_work_orders_populated_when_gaps(self) -> None:
        proof = DriveCUProof()
        orders = build_w_gdrive_cu_001_hardening_work_orders(proof=proof)
        self.assertTrue(len(orders) > 0)
        self.assertTrue(all(o.startswith("WO-GDRIVE-CU-") for o in orders))

    def test_decision_to_dict(self) -> None:
        d = evaluate_w_gdrive_cu_001_maturity()
        out = d.to_dict()
        self.assertEqual(out["package_id"], "W-GDRIVE-CU-001")
        self.assertTrue(out["is_100_percent_mature"])
        self.assertIsNotNone(out["proof"])

    def test_proof_to_dict(self) -> None:
        proof = DriveCUProof(proof_phase="Phase 95.0-95.1")
        out = proof.to_dict()
        self.assertEqual(out["proof_phase"], "Phase 95.0-95.1")

    def test_maturity_percent_partial(self) -> None:
        proof = DriveCUProof(
            gui_ownership_proven=True,
            browser_profile_proven=True,
            account_verified=True,
            drive_visible=True,
        )
        d = evaluate_w_gdrive_cu_001_maturity(proof=proof)
        self.assertGreater(d.current_maturity_percent, 0.0)
        self.assertLess(d.current_maturity_percent, 100.0)


class TestDriveCUMaturityWithProofAudit(unittest.TestCase):
    def test_100_requires_auditable_proof(self) -> None:
        self.assertTrue(w_gdrive_cu_001_final_maturity_requires_auditable_proof())

    def test_without_audit_still_100(self) -> None:
        d = evaluate_w_gdrive_cu_001_maturity_with_proof_audit()
        self.assertTrue(d.is_100_percent_mature)

    def test_with_founder_required_audit_not_final_100(self) -> None:
        audit = audit_w_gdrive_cu_001_proof()
        d = evaluate_w_gdrive_cu_001_maturity_with_proof_audit(
            audit_result=audit
        )
        self.assertFalse(d.is_100_percent_mature)
        self.assertEqual(
            d.current_status, "provisional_100_pending_confirmation"
        )
        self.assertIn(
            "founder_visual_confirmation_required", d.gaps_to_100
        )

    def test_with_auditable_proof_keeps_100(self) -> None:
        audit = CUProofAuditResult(
            proof_status=CUProofQualityStatus.AUDITABLE_PROOF_CONFIRMED,
        )
        d = evaluate_w_gdrive_cu_001_maturity_with_proof_audit(
            audit_result=audit
        )
        self.assertTrue(d.is_100_percent_mature)
        self.assertEqual(d.current_status, "complete")

    def test_with_insufficient_proof_not_100(self) -> None:
        audit = CUProofAuditResult(
            proof_status=CUProofQualityStatus.INSUFFICIENT_PROOF,
        )
        d = evaluate_w_gdrive_cu_001_maturity_with_proof_audit(
            audit_result=audit
        )
        self.assertFalse(d.is_100_percent_mature)
        self.assertIn("proof_audit_failed", d.gaps_to_100)

    def test_static_contract_alone_does_not_finalize(self) -> None:
        audit = CUProofAuditResult(
            proof_status=CUProofQualityStatus.SYNTHETIC_ONLY,
        )
        d = evaluate_w_gdrive_cu_001_maturity_with_proof_audit(
            audit_result=audit
        )
        self.assertFalse(d.is_100_percent_mature)


if __name__ == "__main__":
    unittest.main()
