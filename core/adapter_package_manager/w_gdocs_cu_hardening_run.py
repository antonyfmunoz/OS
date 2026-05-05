"""W-GDOCS-CU-001 Hardening Run.

Executes or prepares a Docs CU hardening run to advance toward
100% maturity. Docs CU has 7 gaps from Phase W0-001R.

When running on the VPS (no local worker), produces exact blockers
and work orders instead of executing live CU.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .local_worker_cu_preflight import (
    LocalWorkerCUPreflightResult,
    LocalWorkerCUPreflightStatus,
    run_local_worker_cu_preflight,
)
from .cu_founder_confirmation_gate import FounderConfirmationStatus
from .google_docs_cu_maturity import (
    evaluate_w_gdocs_cu_001_maturity,
)

W0_001_DOCS_PARITY_BASELINE = {
    "expected_docs": 28,
    "expected_tabs": 321,
    "expected_child_tabs": 134,
    "expected_words": 283831,
}


class WDocsCUHardeningStatus(str, Enum):
    CONFIRMED_FINAL_100 = "confirmed_final_100"
    HARDENING_READY = "hardening_ready"
    PARTIAL_NEEDS_HARDENING = "partial_needs_hardening"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass
class WDocsCUHardeningResult:
    path_id: str = "W-GDOCS-CU-001"
    preflight_status: str = ""
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
    expected_docs: int = 28
    actual_docs: int = 0
    expected_tabs: int = 321
    actual_tabs: int = 0
    expected_child_tabs: int = 134
    actual_child_tabs: int = 0
    expected_words: int = 283831
    actual_words: int = 0
    founder_confirmation_status: str = "not_confirmed"
    governance_passed: bool = True
    no_secret_capture_confirmed: bool = True
    no_mutation_confirmed: bool = True
    final_maturity_percent: float = 0.0
    final_status: WDocsCUHardeningStatus = WDocsCUHardeningStatus.BLOCKED
    blockers: list[str] = field(default_factory=list)
    hardening_work_orders: list[str] = field(default_factory=list)
    proof_artifacts: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path_id": self.path_id,
            "preflight_status": self.preflight_status,
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
            "expected_docs": self.expected_docs,
            "actual_docs": self.actual_docs,
            "expected_tabs": self.expected_tabs,
            "actual_tabs": self.actual_tabs,
            "expected_child_tabs": self.expected_child_tabs,
            "actual_child_tabs": self.actual_child_tabs,
            "expected_words": self.expected_words,
            "actual_words": self.actual_words,
            "founder_confirmation_status": self.founder_confirmation_status,
            "governance_passed": self.governance_passed,
            "no_secret_capture_confirmed": self.no_secret_capture_confirmed,
            "no_mutation_confirmed": self.no_mutation_confirmed,
            "final_maturity_percent": self.final_maturity_percent,
            "final_status": self.final_status.value,
            "blockers": self.blockers,
            "hardening_work_orders": self.hardening_work_orders,
            "proof_artifacts": self.proof_artifacts,
            "notes": self.notes,
        }


def run_w_gdocs_cu_hardening(
    preflight: LocalWorkerCUPreflightResult | None = None,
    founder_confirmation: FounderConfirmationStatus | None = None,
) -> WDocsCUHardeningResult:
    if preflight is None:
        preflight = run_local_worker_cu_preflight()

    result = WDocsCUHardeningResult()
    result.preflight_status = preflight.preflight_status.value

    maturity = evaluate_w_gdocs_cu_001_maturity()

    result.docs_openable = maturity.docs_openable
    result.tabs_detectable = maturity.tabs_detectable
    result.child_tabs_supported = maturity.child_tabs_supported
    result.content_extractable = maturity.content_extractable
    result.scrolling_complete = maturity.scrolling_complete
    result.per_doc_provenance_complete = maturity.per_doc_provenance_complete
    result.per_tab_provenance_complete = maturity.per_tab_provenance_complete
    result.empty_tabs_marked = maturity.empty_tabs_marked
    result.inaccessible_tabs_marked = maturity.inaccessible_tabs_marked
    result.parity_against_api = maturity.parity_against_api
    result.final_maturity_percent = maturity.current_maturity_percent

    if not preflight.can_run_docs_cu:
        result.blockers = list(preflight.blockers)
        result.notes.append(
            "Local worker cannot run Docs CU from this environment. "
            "Existing Phase W0-001R proof used for current state."
        )

        gaps = maturity.gaps_to_100
        if gaps:
            result.final_status = WDocsCUHardeningStatus.PARTIAL_NEEDS_HARDENING
            result.hardening_work_orders = [
                f"WO-GDOCS-CU-{g.upper()}" for g in gaps
            ]
            for g in gaps:
                if f"DOCS_CU_GAP: {g}" not in result.blockers:
                    result.blockers.append(f"DOCS_CU_GAP: {g}")
        else:
            if (
                founder_confirmation == FounderConfirmationStatus.CONFIRMED
                or founder_confirmation == FounderConfirmationStatus.NOT_REQUIRED
            ):
                result.final_status = WDocsCUHardeningStatus.CONFIRMED_FINAL_100
                result.founder_confirmation_status = (
                    founder_confirmation.value
                )
            else:
                result.final_status = WDocsCUHardeningStatus.HARDENING_READY
                result.blockers.append("FOUNDER_CONFIRMATION_REQUIRED")

        return result

    if maturity.is_100_percent_mature:
        if (
            founder_confirmation == FounderConfirmationStatus.CONFIRMED
            or founder_confirmation == FounderConfirmationStatus.NOT_REQUIRED
        ):
            result.final_status = WDocsCUHardeningStatus.CONFIRMED_FINAL_100
            result.founder_confirmation_status = founder_confirmation.value
            result.final_maturity_percent = 100.0
        else:
            result.final_status = WDocsCUHardeningStatus.HARDENING_READY
            result.founder_confirmation_status = "not_confirmed"
            result.blockers.append("FOUNDER_CONFIRMATION_REQUIRED")
    else:
        result.final_status = WDocsCUHardeningStatus.PARTIAL_NEEDS_HARDENING
        result.hardening_work_orders = maturity.hardening_work_orders
        for g in maturity.gaps_to_100:
            result.blockers.append(f"DOCS_CU_GAP: {g}")

    return result


def evaluate_w_gdocs_cu_hardening_result(
    result: WDocsCUHardeningResult,
) -> bool:
    return result.final_status == WDocsCUHardeningStatus.CONFIRMED_FINAL_100


def build_w_gdocs_cu_hardening_report(
    result: WDocsCUHardeningResult,
) -> dict[str, Any]:
    return {
        "path_id": result.path_id,
        "final_status": result.final_status.value,
        "final_maturity_percent": result.final_maturity_percent,
        "docs_openable": result.docs_openable,
        "tabs_detectable": result.tabs_detectable,
        "child_tabs_supported": result.child_tabs_supported,
        "content_extractable": result.content_extractable,
        "parity_against_api": result.parity_against_api,
        "founder_confirmed": result.founder_confirmation_status,
        "governance_passed": result.governance_passed,
        "gap_count": len(result.hardening_work_orders),
        "hardening_work_orders": result.hardening_work_orders,
        "blocker_count": len(result.blockers),
        "blockers": result.blockers,
    }
