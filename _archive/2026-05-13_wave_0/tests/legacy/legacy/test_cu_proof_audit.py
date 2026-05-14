"""Tests for CU Proof Audit.

Validates that static tests alone are insufficient proof,
missing evidence triggers downgrade, stale proof blocks final maturity,
and auditable GUI proof allows 100%.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.adapter_package_manager.cu_proof_audit import (
    CUProofAuditResult,
    CUProofQualityStatus,
    audit_w_gdrive_cu_001_proof,
    build_cu_proof_audit_report,
    cu_proof_requires_downgrade,
    cu_proof_requires_founder_confirmation,
    evidence_supports_100_percent_maturity,
)


class TestCUProofAudit(unittest.TestCase):
    def test_audit_result_builds(self) -> None:
        result = audit_w_gdrive_cu_001_proof()
        self.assertIsInstance(result, CUProofAuditResult)
        self.assertEqual(result.package_id, "W-GDRIVE-CU-001")

    def test_static_tests_alone_insufficient(self) -> None:
        result = audit_w_gdrive_cu_001_proof(
            evidence_paths=[], base_dir="/nonexistent"
        )
        self.assertFalse(evidence_supports_100_percent_maturity(result))

    def test_missing_evidence_requires_confirmation_or_downgrade(self) -> None:
        result = audit_w_gdrive_cu_001_proof(
            evidence_paths=[], base_dir="/nonexistent"
        )
        self.assertIn(result.proof_status, (
            CUProofQualityStatus.SYNTHETIC_ONLY,
            CUProofQualityStatus.INSUFFICIENT_PROOF,
        ))

    def test_synthetic_only_when_no_inventory(self) -> None:
        result = audit_w_gdrive_cu_001_proof(
            evidence_paths=[], base_dir="/nonexistent"
        )
        self.assertEqual(
            result.proof_status, CUProofQualityStatus.SYNTHETIC_ONLY
        )
        self.assertEqual(result.audited_maturity_percent, 0.0)

    def test_real_evidence_detected(self) -> None:
        result = audit_w_gdrive_cu_001_proof()
        self.assertTrue(result.live_gui_execution_confirmed)
        self.assertTrue(result.local_worker_confirmed)
        self.assertTrue(result.account_verified)
        self.assertTrue(result.inventory_verified)
        self.assertTrue(result.api_parity_verified)
        self.assertTrue(result.governance_verified)

    def test_founder_confirmation_absent(self) -> None:
        result = audit_w_gdrive_cu_001_proof()
        self.assertFalse(result.founder_visual_confirmation_present)
        self.assertIn("founder_visual_confirmation_absent", result.proof_gaps)

    def test_founder_confirmation_required_status(self) -> None:
        result = audit_w_gdrive_cu_001_proof()
        self.assertEqual(
            result.proof_status,
            CUProofQualityStatus.FOUNDER_CONFIRMATION_REQUIRED,
        )

    def test_does_not_support_final_100_without_founder(self) -> None:
        result = audit_w_gdrive_cu_001_proof()
        self.assertFalse(evidence_supports_100_percent_maturity(result))

    def test_does_not_require_downgrade_when_founder_needed(self) -> None:
        result = audit_w_gdrive_cu_001_proof()
        self.assertFalse(cu_proof_requires_downgrade(result))

    def test_requires_founder_confirmation(self) -> None:
        result = audit_w_gdrive_cu_001_proof()
        self.assertTrue(cu_proof_requires_founder_confirmation(result))

    def test_audited_maturity_still_100_pending_confirmation(self) -> None:
        result = audit_w_gdrive_cu_001_proof()
        self.assertEqual(result.audited_maturity_percent, 100.0)

    def test_recommended_status_provisional(self) -> None:
        result = audit_w_gdrive_cu_001_proof()
        self.assertEqual(
            result.recommended_status,
            "provisional_100_pending_confirmation",
        )

    def test_evidence_files_exist_checked(self) -> None:
        result = audit_w_gdrive_cu_001_proof()
        self.assertTrue(len(result.evidence_files) > 0)
        self.assertTrue(any(result.evidence_files_exist))

    def test_proof_audit_report_builds(self) -> None:
        result = audit_w_gdrive_cu_001_proof()
        report = build_cu_proof_audit_report(result)
        self.assertEqual(report["package_id"], "W-GDRIVE-CU-001")
        self.assertIn("proof_status", report)
        self.assertIn("proof_gaps", report)
        self.assertIn("recommended_action", report)

    def test_governance_verified_from_evidence(self) -> None:
        result = audit_w_gdrive_cu_001_proof()
        self.assertTrue(result.governance_verified)
        self.assertTrue(result.no_secret_capture_verified)
        self.assertTrue(result.no_mutation_verified)

    def test_api_parity_verified_from_evidence(self) -> None:
        result = audit_w_gdrive_cu_001_proof()
        self.assertTrue(result.api_parity_verified)

    def test_result_to_dict(self) -> None:
        result = audit_w_gdrive_cu_001_proof()
        d = result.to_dict()
        self.assertEqual(d["package_id"], "W-GDRIVE-CU-001")
        self.assertEqual(
            d["proof_status"], "founder_confirmation_required"
        )

    def test_downgrade_required_for_insufficient(self) -> None:
        result = CUProofAuditResult(
            proof_status=CUProofQualityStatus.INSUFFICIENT_PROOF,
        )
        self.assertTrue(cu_proof_requires_downgrade(result))

    def test_downgrade_required_for_synthetic(self) -> None:
        result = CUProofAuditResult(
            proof_status=CUProofQualityStatus.SYNTHETIC_ONLY,
        )
        self.assertTrue(cu_proof_requires_downgrade(result))

    def test_no_downgrade_for_auditable(self) -> None:
        result = CUProofAuditResult(
            proof_status=CUProofQualityStatus.AUDITABLE_PROOF_CONFIRMED,
        )
        self.assertFalse(cu_proof_requires_downgrade(result))


if __name__ == "__main__":
    unittest.main()
