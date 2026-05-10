"""W-GDRIVE-CU-001 Rerun Result Contract.

Defines the result structure for a Drive CU rerun while founder is
present. Evaluates whether the rerun proof is sufficient to finalize
Drive CU at 100%.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class WDriveCURerunStatus(str, Enum):
    PACKET_CREATED = "packet_created"
    DISPATCHED_PENDING = "dispatched_pending"
    EXECUTING = "executing"
    COMPLETED_FOUNDER_CONFIRMED = "completed_founder_confirmed"
    COMPLETED_FOUNDER_DECLINED = "completed_founder_declined"
    FAILED_GOVERNANCE = "failed_governance"
    FAILED_EXECUTION = "failed_execution"


@dataclass
class WDriveCURerunResult:
    run_id: str = "W0-001-CU-RERUN-WHILE-PRESENT-001"
    package_id: str = "W-GDRIVE-CU-001"
    rerun_status: WDriveCURerunStatus = WDriveCURerunStatus.PACKET_CREATED
    founder_present: bool = False
    founder_confirmed_output: bool = False
    chrome_opened: bool = False
    drive_loaded: bool = False
    correct_account: bool = False
    correct_profile: bool = False
    visible_inventory_captured: bool = False
    item_count: int = 0
    expected_items: int = 26
    items_match_expected: bool = False
    api_parity_confirmed: bool = False
    method_computer_use_only: bool = False
    governance_no_gmail: bool = True
    governance_no_account_switch: bool = True
    governance_no_mutation: bool = True
    governance_no_credential_capture: bool = True
    governance_no_playwright: bool = True
    governance_no_cdp: bool = True
    governance_no_screenshots: bool = True
    proof_artifacts: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "package_id": self.package_id,
            "rerun_status": self.rerun_status.value,
            "founder_present": self.founder_present,
            "founder_confirmed_output": self.founder_confirmed_output,
            "chrome_opened": self.chrome_opened,
            "drive_loaded": self.drive_loaded,
            "correct_account": self.correct_account,
            "correct_profile": self.correct_profile,
            "visible_inventory_captured": self.visible_inventory_captured,
            "item_count": self.item_count,
            "expected_items": self.expected_items,
            "items_match_expected": self.items_match_expected,
            "api_parity_confirmed": self.api_parity_confirmed,
            "method_computer_use_only": self.method_computer_use_only,
            "governance_no_gmail": self.governance_no_gmail,
            "governance_no_account_switch": self.governance_no_account_switch,
            "governance_no_mutation": self.governance_no_mutation,
            "governance_no_credential_capture": self.governance_no_credential_capture,
            "governance_no_playwright": self.governance_no_playwright,
            "governance_no_cdp": self.governance_no_cdp,
            "governance_no_screenshots": self.governance_no_screenshots,
            "proof_artifacts": self.proof_artifacts,
            "blockers": self.blockers,
            "notes": self.notes,
        }


def build_w_gdrive_cu_rerun_result(
    founder_present: bool = False,
    founder_confirmed: bool = False,
    chrome_opened: bool = False,
    drive_loaded: bool = False,
    correct_account: bool = False,
    correct_profile: bool = False,
    inventory_captured: bool = False,
    item_count: int = 0,
    api_parity: bool = False,
    method_cu_only: bool = False,
    governance_clean: bool = True,
) -> WDriveCURerunResult:
    result = WDriveCURerunResult()
    result.founder_present = founder_present
    result.founder_confirmed_output = founder_confirmed
    result.chrome_opened = chrome_opened
    result.drive_loaded = drive_loaded
    result.correct_account = correct_account
    result.correct_profile = correct_profile
    result.visible_inventory_captured = inventory_captured
    result.item_count = item_count
    result.items_match_expected = item_count == result.expected_items
    result.api_parity_confirmed = api_parity
    result.method_computer_use_only = method_cu_only

    if not governance_clean:
        result.governance_no_gmail = False
        result.governance_no_mutation = False

    return result


def evaluate_w_gdrive_cu_rerun_result(
    result: WDriveCURerunResult,
) -> WDriveCURerunResult:
    if not result.founder_present:
        result.blockers.append("FOUNDER_NOT_PRESENT")

    if not result.founder_confirmed_output:
        result.blockers.append("FOUNDER_DID_NOT_CONFIRM_OUTPUT")

    governance_passed = all(
        [
            result.governance_no_gmail,
            result.governance_no_account_switch,
            result.governance_no_mutation,
            result.governance_no_credential_capture,
            result.governance_no_playwright,
            result.governance_no_cdp,
            result.governance_no_screenshots,
        ]
    )

    if not governance_passed:
        result.rerun_status = WDriveCURerunStatus.FAILED_GOVERNANCE
        result.blockers.append("GOVERNANCE_FAILURE")
        return result

    proof_checks = [
        result.chrome_opened,
        result.drive_loaded,
        result.correct_account,
        result.correct_profile,
        result.visible_inventory_captured,
        result.items_match_expected,
        result.api_parity_confirmed,
        result.method_computer_use_only,
    ]

    if not all(proof_checks):
        if not result.chrome_opened:
            result.blockers.append("CHROME_NOT_OPENED")
        if not result.drive_loaded:
            result.blockers.append("DRIVE_NOT_LOADED")
        if not result.correct_account:
            result.blockers.append("WRONG_ACCOUNT")
        if not result.correct_profile:
            result.blockers.append("WRONG_PROFILE")
        if not result.visible_inventory_captured:
            result.blockers.append("INVENTORY_NOT_CAPTURED")
        if not result.items_match_expected:
            result.blockers.append(
                f"ITEM_COUNT_MISMATCH: {result.item_count}/{result.expected_items}"
            )
        if not result.api_parity_confirmed:
            result.blockers.append("API_PARITY_NOT_CONFIRMED")
        if not result.method_computer_use_only:
            result.blockers.append("METHOD_NOT_CU_ONLY")

        result.rerun_status = WDriveCURerunStatus.FAILED_EXECUTION
        return result

    if result.founder_present and result.founder_confirmed_output:
        result.rerun_status = WDriveCURerunStatus.COMPLETED_FOUNDER_CONFIRMED
    elif result.founder_present and not result.founder_confirmed_output:
        result.rerun_status = WDriveCURerunStatus.COMPLETED_FOUNDER_DECLINED
    else:
        result.rerun_status = WDriveCURerunStatus.DISPATCHED_PENDING

    return result


def rerun_result_finalizes_drive_cu(
    result: WDriveCURerunResult,
) -> bool:
    return result.rerun_status == WDriveCURerunStatus.COMPLETED_FOUNDER_CONFIRMED


def summarize_w_gdrive_cu_rerun_result(
    result: WDriveCURerunResult,
) -> dict[str, Any]:
    return {
        "run_id": result.run_id,
        "package_id": result.package_id,
        "rerun_status": result.rerun_status.value,
        "founder_present": result.founder_present,
        "founder_confirmed": result.founder_confirmed_output,
        "items": f"{result.item_count}/{result.expected_items}",
        "api_parity": result.api_parity_confirmed,
        "finalizes_drive_cu": rerun_result_finalizes_drive_cu(result),
        "blocker_count": len(result.blockers),
        "blockers": result.blockers,
    }
