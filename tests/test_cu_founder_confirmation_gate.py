"""Tests for CU Founder Confirmation Gate.

Validates gate construction, confirmation flow, and blocking behavior.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.adapter_package_manager.cu_founder_confirmation_gate import (
    FounderConfirmationGate,
    FounderConfirmationStatus,
    apply_founder_confirmation,
    build_w_gdrive_cu_founder_confirmation_gate,
    founder_confirmation_blocks_final_maturity,
    founder_confirmation_required_for_cu,
)
from core.adapter_package_manager.cu_proof_audit import (
    CUProofAuditResult,
    CUProofQualityStatus,
    audit_w_gdrive_cu_001_proof,
)


class TestFounderConfirmationGate(unittest.TestCase):
    def test_gate_builds(self) -> None:
        gate = build_w_gdrive_cu_founder_confirmation_gate()
        self.assertIsInstance(gate, FounderConfirmationGate)
        self.assertEqual(gate.package_id, "W-GDRIVE-CU-001")

    def test_confirmation_required_when_gui_proof_remote(self) -> None:
        audit = audit_w_gdrive_cu_001_proof()
        self.assertTrue(founder_confirmation_required_for_cu(audit))

    def test_not_confirmed_blocks_final_maturity(self) -> None:
        gate = build_w_gdrive_cu_founder_confirmation_gate()
        self.assertTrue(founder_confirmation_blocks_final_maturity(gate))
        self.assertFalse(gate.can_finalize_maturity)

    def test_confirmed_allows_finalization(self) -> None:
        gate = build_w_gdrive_cu_founder_confirmation_gate()
        gate = apply_founder_confirmation(
            gate,
            FounderConfirmationStatus.CONFIRMED,
            "I visually confirmed Drive CU on my Windows desktop",
        )
        self.assertTrue(gate.can_finalize_maturity)
        self.assertFalse(founder_confirmation_blocks_final_maturity(gate))

    def test_not_required_allows_finalization(self) -> None:
        gate = build_w_gdrive_cu_founder_confirmation_gate()
        gate = apply_founder_confirmation(
            gate, FounderConfirmationStatus.NOT_REQUIRED
        )
        self.assertTrue(gate.can_finalize_maturity)

    def test_expired_blocks_final_maturity(self) -> None:
        gate = build_w_gdrive_cu_founder_confirmation_gate()
        gate = apply_founder_confirmation(
            gate, FounderConfirmationStatus.EXPIRED
        )
        self.assertFalse(gate.can_finalize_maturity)
        self.assertTrue(founder_confirmation_blocks_final_maturity(gate))

    def test_invalid_blocks_final_maturity(self) -> None:
        gate = build_w_gdrive_cu_founder_confirmation_gate()
        gate = apply_founder_confirmation(
            gate, FounderConfirmationStatus.INVALID
        )
        self.assertFalse(gate.can_finalize_maturity)

    def test_required_status_initial(self) -> None:
        gate = build_w_gdrive_cu_founder_confirmation_gate()
        self.assertEqual(
            gate.confirmation_status, FounderConfirmationStatus.REQUIRED
        )

    def test_gate_to_dict(self) -> None:
        gate = build_w_gdrive_cu_founder_confirmation_gate()
        d = gate.to_dict()
        self.assertEqual(d["gate_id"], "GATE-GDRIVE-CU-FOUNDER-CONFIRM")
        self.assertEqual(d["confirmation_status"], "required")

    def test_gate_notes_populated(self) -> None:
        gate = build_w_gdrive_cu_founder_confirmation_gate()
        self.assertTrue(len(gate.notes) > 0)

    def test_confirmation_not_required_for_auditable(self) -> None:
        audit = CUProofAuditResult(
            proof_status=CUProofQualityStatus.AUDITABLE_PROOF_CONFIRMED,
        )
        self.assertFalse(founder_confirmation_required_for_cu(audit))

    def test_founder_response_stored(self) -> None:
        gate = build_w_gdrive_cu_founder_confirmation_gate()
        gate = apply_founder_confirmation(
            gate,
            FounderConfirmationStatus.CONFIRMED,
            "Confirmed on 2026-05-05",
        )
        self.assertEqual(gate.founder_response, "Confirmed on 2026-05-05")

    def test_status_enum_values(self) -> None:
        self.assertEqual(FounderConfirmationStatus.CONFIRMED.value, "confirmed")
        self.assertEqual(FounderConfirmationStatus.REQUIRED.value, "required")
        self.assertEqual(FounderConfirmationStatus.EXPIRED.value, "expired")


if __name__ == "__main__":
    unittest.main()
