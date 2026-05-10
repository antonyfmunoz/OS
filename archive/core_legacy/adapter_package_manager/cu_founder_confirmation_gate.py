"""CU Founder Confirmation Gate.

When CU acts through a local visible GUI and the remote orchestrator
cannot independently verify the visible result, founder visual
confirmation can be required before final maturity is accepted.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .cu_proof_audit import CUProofAuditResult, CUProofQualityStatus


class FounderConfirmationStatus(str, Enum):
    CONFIRMED = "confirmed"
    NOT_CONFIRMED = "not_confirmed"
    NOT_REQUIRED = "not_required"
    REQUIRED = "required"
    EXPIRED = "expired"
    INVALID = "invalid"


@dataclass
class FounderConfirmationGate:
    gate_id: str = ""
    package_id: str = ""
    required_confirmation: str = ""
    confirmation_status: FounderConfirmationStatus = FounderConfirmationStatus.NOT_CONFIRMED
    required_observation: str = ""
    founder_response: str = ""
    expires_at: str = ""
    can_finalize_maturity: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "package_id": self.package_id,
            "required_confirmation": self.required_confirmation,
            "confirmation_status": self.confirmation_status.value,
            "required_observation": self.required_observation,
            "founder_response": self.founder_response,
            "expires_at": self.expires_at,
            "can_finalize_maturity": self.can_finalize_maturity,
            "notes": self.notes,
        }


def build_w_gdrive_cu_founder_confirmation_gate() -> FounderConfirmationGate:
    return FounderConfirmationGate(
        gate_id="GATE-GDRIVE-CU-FOUNDER-CONFIRM",
        package_id="W-GDRIVE-CU-001",
        required_confirmation=(
            "Founder visually confirms that Google Drive Computer Use "
            "inventory executed correctly on the local Windows desktop: "
            "Chrome opened, Drive page loaded, 26 files visible, "
            "correct account (antonyfm@empyreanstudios.co)."
        ),
        confirmation_status=FounderConfirmationStatus.REQUIRED,
        required_observation=(
            "Either: (1) founder was present during a CU inventory run "
            "and saw the Chrome window display Drive contents, or "
            "(2) founder re-runs CU inventory while physically present "
            "and confirms the output matches."
        ),
        founder_response="",
        expires_at="",
        can_finalize_maturity=False,
        notes=[
            "Phase 95 CU inventory was driven remotely from VPS via "
            "Task Scheduler /IT. Founder was not present.",
            "Evidence file (visible_drive_inventory.json) exists with "
            "26 items, correct account, COMPUTER_USE_ONLY method.",
            "Evidence is strong but not independently verifiable from "
            "the VPS node — requires founder visual confirmation.",
        ],
    )


def founder_confirmation_required_for_cu(
    audit_result: CUProofAuditResult,
) -> bool:
    return (
        audit_result.proof_status
        == CUProofQualityStatus.FOUNDER_CONFIRMATION_REQUIRED
    )


def apply_founder_confirmation(
    gate: FounderConfirmationGate,
    confirmation_status: FounderConfirmationStatus,
    founder_response: str = "",
) -> FounderConfirmationGate:
    gate.confirmation_status = confirmation_status
    gate.founder_response = founder_response

    if confirmation_status == FounderConfirmationStatus.CONFIRMED:
        gate.can_finalize_maturity = True
    elif confirmation_status == FounderConfirmationStatus.NOT_REQUIRED:
        gate.can_finalize_maturity = True
    else:
        gate.can_finalize_maturity = False

    return gate


def founder_confirmation_blocks_final_maturity(
    gate: FounderConfirmationGate,
) -> bool:
    return not gate.can_finalize_maturity
