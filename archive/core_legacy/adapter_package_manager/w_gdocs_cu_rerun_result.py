"""W-GDOCS-CU-001 Rerun Result Contract.

Defines the result structure for a Docs CU rerun while founder is
present. Evaluates whether the rerun proof closes all 7 gaps and
reaches final 100%.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


W0_001_DOCS_PARITY_BASELINE = {
    "expected_docs": 28,
    "expected_tabs": 321,
    "expected_child_tabs": 134,
    "expected_words": 283831,
}


class WDocsCURerunStatus(str, Enum):
    PACKET_CREATED = "packet_created"
    DISPATCHED_PENDING = "dispatched_pending"
    EXECUTING = "executing"
    COMPLETED_FOUNDER_CONFIRMED = "completed_founder_confirmed"
    COMPLETED_FOUNDER_DECLINED = "completed_founder_declined"
    COMPLETED_PARTIAL = "completed_partial"
    FAILED_GOVERNANCE = "failed_governance"
    FAILED_EXECUTION = "failed_execution"


@dataclass
class WDocsCURerunResult:
    run_id: str = "W0-001-CU-RERUN-WHILE-PRESENT-001"
    package_id: str = "W-GDOCS-CU-001"
    rerun_status: WDocsCURerunStatus = WDocsCURerunStatus.PACKET_CREATED
    founder_present: bool = False
    founder_confirmed_output: bool = False
    docs_openable: bool = False
    tabs_detectable: bool = False
    child_tabs_supported: bool = False
    content_extractable: bool = False
    scrolling_complete: bool = False
    per_doc_provenance_complete: bool = False
    per_tab_provenance_complete: bool = False
    empty_tabs_marked: bool = False
    inaccessible_tabs_marked: bool = False
    parity_against_api: bool = False
    actual_docs: int = 0
    expected_docs: int = 28
    actual_tabs: int = 0
    expected_tabs: int = 321
    actual_child_tabs: int = 0
    expected_child_tabs: int = 134
    actual_words: int = 0
    expected_words: int = 283831
    method_computer_use_only: bool = False
    governance_no_gmail: bool = True
    governance_no_account_switch: bool = True
    governance_no_mutation: bool = True
    governance_no_credential_capture: bool = True
    governance_no_playwright: bool = True
    governance_no_cdp: bool = True
    governance_no_screenshots: bool = True
    gaps_remaining: list[str] = field(default_factory=list)
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
            "docs_openable": self.docs_openable,
            "tabs_detectable": self.tabs_detectable,
            "child_tabs_supported": self.child_tabs_supported,
            "content_extractable": self.content_extractable,
            "scrolling_complete": self.scrolling_complete,
            "per_doc_provenance_complete": self.per_doc_provenance_complete,
            "per_tab_provenance_complete": self.per_tab_provenance_complete,
            "empty_tabs_marked": self.empty_tabs_marked,
            "inaccessible_tabs_marked": self.inaccessible_tabs_marked,
            "parity_against_api": self.parity_against_api,
            "actual_docs": self.actual_docs,
            "expected_docs": self.expected_docs,
            "actual_tabs": self.actual_tabs,
            "expected_tabs": self.expected_tabs,
            "actual_child_tabs": self.actual_child_tabs,
            "expected_child_tabs": self.expected_child_tabs,
            "actual_words": self.actual_words,
            "expected_words": self.expected_words,
            "method_computer_use_only": self.method_computer_use_only,
            "gaps_remaining": self.gaps_remaining,
            "proof_artifacts": self.proof_artifacts,
            "blockers": self.blockers,
            "notes": self.notes,
        }


def build_w_gdocs_cu_rerun_result(
    founder_present: bool = False,
    founder_confirmed: bool = False,
    docs_openable: bool = False,
    tabs_detectable: bool = False,
    child_tabs_supported: bool = False,
    content_extractable: bool = False,
    scrolling_complete: bool = False,
    per_doc_provenance: bool = False,
    per_tab_provenance: bool = False,
    empty_tabs_marked: bool = False,
    inaccessible_tabs_marked: bool = False,
    parity_against_api: bool = False,
    actual_docs: int = 0,
    actual_tabs: int = 0,
    actual_child_tabs: int = 0,
    actual_words: int = 0,
    method_cu_only: bool = False,
    governance_clean: bool = True,
) -> WDocsCURerunResult:
    result = WDocsCURerunResult()
    result.founder_present = founder_present
    result.founder_confirmed_output = founder_confirmed
    result.docs_openable = docs_openable
    result.tabs_detectable = tabs_detectable
    result.child_tabs_supported = child_tabs_supported
    result.content_extractable = content_extractable
    result.scrolling_complete = scrolling_complete
    result.per_doc_provenance_complete = per_doc_provenance
    result.per_tab_provenance_complete = per_tab_provenance
    result.empty_tabs_marked = empty_tabs_marked
    result.inaccessible_tabs_marked = inaccessible_tabs_marked
    result.parity_against_api = parity_against_api
    result.actual_docs = actual_docs
    result.actual_tabs = actual_tabs
    result.actual_child_tabs = actual_child_tabs
    result.actual_words = actual_words
    result.method_computer_use_only = method_cu_only

    if not governance_clean:
        result.governance_no_gmail = False
        result.governance_no_mutation = False

    return result


def evaluate_w_gdocs_cu_rerun_result(
    result: WDocsCURerunResult,
) -> WDocsCURerunResult:
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
        result.rerun_status = WDocsCURerunStatus.FAILED_GOVERNANCE
        result.blockers.append("GOVERNANCE_FAILURE")
        return result

    gap_checks = {
        "child_tabs_supported": result.child_tabs_supported,
        "content_extractable": result.content_extractable,
        "scrolling_complete": result.scrolling_complete,
        "per_tab_provenance_complete": result.per_tab_provenance_complete,
        "empty_tabs_marked": result.empty_tabs_marked,
        "inaccessible_tabs_marked": result.inaccessible_tabs_marked,
        "parity_against_api": result.parity_against_api,
    }

    base_checks = {
        "docs_openable": result.docs_openable,
        "tabs_detectable": result.tabs_detectable,
        "per_doc_provenance_complete": result.per_doc_provenance_complete,
        "method_computer_use_only": result.method_computer_use_only,
    }

    for check_name, passed in base_checks.items():
        if not passed:
            result.blockers.append(f"BASE_CHECK_FAILED: {check_name}")

    gaps_open = []
    for gap_name, closed in gap_checks.items():
        if not closed:
            gaps_open.append(gap_name)
    result.gaps_remaining = gaps_open

    if not all(base_checks.values()):
        result.rerun_status = WDocsCURerunStatus.FAILED_EXECUTION
        return result

    if gaps_open:
        if result.founder_present:
            result.rerun_status = WDocsCURerunStatus.COMPLETED_PARTIAL
        else:
            result.rerun_status = WDocsCURerunStatus.DISPATCHED_PENDING
        for g in gaps_open:
            result.blockers.append(f"GAP_STILL_OPEN: {g}")
        return result

    if result.founder_present and result.founder_confirmed_output:
        result.rerun_status = WDocsCURerunStatus.COMPLETED_FOUNDER_CONFIRMED
    elif result.founder_present and not result.founder_confirmed_output:
        result.rerun_status = WDocsCURerunStatus.COMPLETED_FOUNDER_DECLINED
    else:
        result.rerun_status = WDocsCURerunStatus.DISPATCHED_PENDING

    return result


def rerun_result_finalizes_docs_cu(
    result: WDocsCURerunResult,
) -> bool:
    return result.rerun_status == WDocsCURerunStatus.COMPLETED_FOUNDER_CONFIRMED


def summarize_w_gdocs_cu_rerun_result(
    result: WDocsCURerunResult,
) -> dict[str, Any]:
    return {
        "run_id": result.run_id,
        "package_id": result.package_id,
        "rerun_status": result.rerun_status.value,
        "founder_present": result.founder_present,
        "founder_confirmed": result.founder_confirmed_output,
        "docs": f"{result.actual_docs}/{result.expected_docs}",
        "tabs": f"{result.actual_tabs}/{result.expected_tabs}",
        "child_tabs": f"{result.actual_child_tabs}/{result.expected_child_tabs}",
        "words": f"{result.actual_words}/{result.expected_words}",
        "gaps_remaining": len(result.gaps_remaining),
        "gaps": result.gaps_remaining,
        "finalizes_docs_cu": rerun_result_finalizes_docs_cu(result),
        "blocker_count": len(result.blockers),
        "blockers": result.blockers,
    }
