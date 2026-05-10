"""W0-001 CU Slice Readiness.

Evaluates combined Drive CU + Docs CU readiness for the W0-001
triple-test. CU slice is READY only when both packages are 100%.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .google_drive_cu_maturity import (
    GoogleDriveCUMaturityDecision,
    evaluate_w_gdrive_cu_001_maturity,
)
from .google_docs_cu_maturity import (
    GoogleDocsCUMaturityDecision,
    evaluate_w_gdocs_cu_001_maturity,
)


class W0001CUSliceStatus(str, Enum):
    READY = "ready"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    HARDENING_READY = "hardening_ready"
    NOT_READY = "not_ready"


@dataclass
class W0001CUSliceReadiness:
    drive_cu_maturity: float = 0.0
    docs_cu_maturity: float = 0.0
    drive_cu_status: str = "not_ready"
    docs_cu_status: str = "not_ready"
    cu_slice_status: W0001CUSliceStatus = W0001CUSliceStatus.NOT_READY
    can_run_cu_hardening_test: bool = False
    can_run_cu_production_parity: bool = False
    can_mark_cu_slice_ready: bool = False
    blockers: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "drive_cu_maturity": self.drive_cu_maturity,
            "docs_cu_maturity": self.docs_cu_maturity,
            "drive_cu_status": self.drive_cu_status,
            "docs_cu_status": self.docs_cu_status,
            "cu_slice_status": self.cu_slice_status.value,
            "can_run_cu_hardening_test": self.can_run_cu_hardening_test,
            "can_run_cu_production_parity": self.can_run_cu_production_parity,
            "can_mark_cu_slice_ready": self.can_mark_cu_slice_ready,
            "blockers": self.blockers,
            "next_actions": self.next_actions,
            "notes": self.notes,
        }


def evaluate_w0_001_cu_slice_readiness(
    drive_decision: GoogleDriveCUMaturityDecision | None = None,
    docs_decision: GoogleDocsCUMaturityDecision | None = None,
) -> W0001CUSliceReadiness:
    if drive_decision is None:
        drive_decision = evaluate_w_gdrive_cu_001_maturity()
    if docs_decision is None:
        docs_decision = evaluate_w_gdocs_cu_001_maturity()

    readiness = W0001CUSliceReadiness()
    readiness.drive_cu_maturity = drive_decision.current_maturity_percent
    readiness.docs_cu_maturity = docs_decision.current_maturity_percent
    readiness.drive_cu_status = drive_decision.current_status
    readiness.docs_cu_status = docs_decision.current_status

    drive_ready = drive_decision.is_100_percent_mature
    docs_ready = docs_decision.is_100_percent_mature

    if drive_ready and docs_ready:
        readiness.cu_slice_status = W0001CUSliceStatus.READY
        readiness.can_mark_cu_slice_ready = True
        readiness.can_run_cu_production_parity = True
        readiness.can_run_cu_hardening_test = True
    elif drive_decision.governance_passed and docs_decision.governance_passed:
        readiness.cu_slice_status = W0001CUSliceStatus.HARDENING_READY
        readiness.can_run_cu_hardening_test = True
        readiness.can_run_cu_production_parity = False
        readiness.can_mark_cu_slice_ready = False
    else:
        readiness.cu_slice_status = W0001CUSliceStatus.NOT_READY

    blockers = []
    next_actions = []

    if not drive_ready:
        for gap in drive_decision.gaps_to_100:
            blockers.append(f"W-GDRIVE-CU-001: {gap}")
        next_actions.append("Harden Drive CU gaps")

    if not docs_ready:
        for gap in docs_decision.gaps_to_100:
            blockers.append(f"W-GDOCS-CU-001: {gap}")
        next_actions.append("Harden Docs CU gaps")

    readiness.blockers = blockers
    readiness.next_actions = next_actions
    readiness.notes = [
        "CU slice READY only when both Drive CU and Docs CU are 100%",
        "Full triple-test requires API slice + CU slice both ready",
    ]
    return readiness


def w0_001_cu_slice_blocks_full_triple_test(
    readiness: W0001CUSliceReadiness,
) -> bool:
    return readiness.cu_slice_status != W0001CUSliceStatus.READY


def summarize_w0_001_cu_slice_readiness(
    readiness: W0001CUSliceReadiness,
) -> dict[str, Any]:
    return {
        "cu_slice_status": readiness.cu_slice_status.value,
        "drive_cu": f"{readiness.drive_cu_maturity}% ({readiness.drive_cu_status})",
        "docs_cu": f"{readiness.docs_cu_maturity}% ({readiness.docs_cu_status})",
        "can_mark_ready": readiness.can_mark_cu_slice_ready,
        "blocker_count": len(readiness.blockers),
        "next_actions": readiness.next_actions,
    }
