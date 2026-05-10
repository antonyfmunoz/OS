"""Google Docs CU Maturity Gate (W-GDOCS-CU-001).

Evaluates whether the Docs Computer Use path has reached 100%
maturity based on proof of execution and parity validation.

Prior proof from Phase W0-001R:
- 8/8 tabs detected via ControlType.TreeItem (100% accuracy)
- Tab names matched API baseline 100%
- Content extraction FAILED (Windows foreground ownership issue)
- Root cause: Task Scheduler /IT process not foreground window owner
- Tab detection PROVEN, content reader NEEDS HARDENING

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DocsCUProof:
    gui_ownership_proven: bool = False
    browser_profile_proven: bool = False
    account_verified: bool = False
    docs_openable: bool = False
    tabs_detectable: bool = False
    tabs_detected_count: int = 0
    tabs_expected_count: int = 0
    child_tabs_supported: bool = False
    content_extractable: bool = False
    scrolling_complete: bool = False
    per_doc_provenance_complete: bool = False
    per_tab_provenance_complete: bool = False
    empty_tabs_marked: bool = False
    inaccessible_tabs_marked: bool = False
    parity_docs: int = 0
    parity_tabs: int = 0
    parity_child_tabs: int = 0
    parity_words: int = 0
    parity_against_api: bool = False
    no_mutation: bool = True
    no_credential_capture: bool = True
    no_screenshot_ocr: bool = True
    proof_source: str = ""
    proof_phase: str = ""
    content_extraction_blocker: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "gui_ownership_proven": self.gui_ownership_proven,
            "browser_profile_proven": self.browser_profile_proven,
            "account_verified": self.account_verified,
            "docs_openable": self.docs_openable,
            "tabs_detectable": self.tabs_detectable,
            "tabs_detected_count": self.tabs_detected_count,
            "tabs_expected_count": self.tabs_expected_count,
            "child_tabs_supported": self.child_tabs_supported,
            "content_extractable": self.content_extractable,
            "scrolling_complete": self.scrolling_complete,
            "per_doc_provenance_complete": self.per_doc_provenance_complete,
            "per_tab_provenance_complete": self.per_tab_provenance_complete,
            "empty_tabs_marked": self.empty_tabs_marked,
            "inaccessible_tabs_marked": self.inaccessible_tabs_marked,
            "parity_docs": self.parity_docs,
            "parity_tabs": self.parity_tabs,
            "parity_child_tabs": self.parity_child_tabs,
            "parity_words": self.parity_words,
            "parity_against_api": self.parity_against_api,
            "no_mutation": self.no_mutation,
            "no_credential_capture": self.no_credential_capture,
            "no_screenshot_ocr": self.no_screenshot_ocr,
            "proof_source": self.proof_source,
            "proof_phase": self.proof_phase,
            "content_extraction_blocker": self.content_extraction_blocker,
        }


@dataclass
class GoogleDocsCUMaturityDecision:
    package_id: str = "W-GDOCS-CU-001"
    path_id: str = "W-GDOCS-CU-001"
    target_maturity_percent: float = 100.0
    current_maturity_percent: float = 0.0
    current_status: str = "partial_needs_hardening"
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
    governance_passed: bool = True
    tool_mastery_passed: bool = False
    tests_present: bool = False
    blockers: list[str] = field(default_factory=list)
    gaps_to_100: list[str] = field(default_factory=list)
    hardening_work_orders: list[str] = field(default_factory=list)
    is_100_percent_mature: bool = False
    proof: DocsCUProof | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "path_id": self.path_id,
            "target_maturity_percent": self.target_maturity_percent,
            "current_maturity_percent": self.current_maturity_percent,
            "current_status": self.current_status,
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
            "governance_passed": self.governance_passed,
            "tool_mastery_passed": self.tool_mastery_passed,
            "tests_present": self.tests_present,
            "blockers": self.blockers,
            "gaps_to_100": self.gaps_to_100,
            "hardening_work_orders": self.hardening_work_orders,
            "is_100_percent_mature": self.is_100_percent_mature,
            "proof": self.proof.to_dict() if self.proof else None,
        }


_DOCS_CU_CHECKS = [
    "gui_ownership_proven",
    "browser_profile_proven",
    "account_verified",
    "docs_openable",
    "tabs_detectable",
    "child_tabs_supported",
    "content_extractable",
    "scrolling_complete",
    "per_doc_provenance_complete",
    "per_tab_provenance_complete",
    "empty_tabs_marked",
    "inaccessible_tabs_marked",
    "parity_against_api",
    "governance_passed",
    "tool_mastery_passed",
    "tests_present",
]


def _build_phase_w0_001r_proof() -> DocsCUProof:
    """Prior proof from Phase W0-001R — tab detection proven,
    content extraction blocked by foreground ownership."""
    return DocsCUProof(
        gui_ownership_proven=True,
        browser_profile_proven=True,
        account_verified=True,
        docs_openable=True,
        tabs_detectable=True,
        tabs_detected_count=8,
        tabs_expected_count=8,
        child_tabs_supported=False,
        content_extractable=False,
        scrolling_complete=False,
        per_doc_provenance_complete=True,
        per_tab_provenance_complete=False,
        empty_tabs_marked=False,
        inaccessible_tabs_marked=False,
        parity_docs=0,
        parity_tabs=0,
        parity_child_tabs=0,
        parity_words=0,
        parity_against_api=False,
        no_mutation=True,
        no_credential_capture=True,
        no_screenshot_ocr=True,
        proof_source="w0_001_computer_use_document_review_sample_report.md",
        proof_phase="Phase W0-001R",
        content_extraction_blocker=(
            "Windows foreground ownership: Task Scheduler /IT process "
            "does not own foreground window, SetForegroundWindow fails, "
            "SendKeys/clipboard extraction blocked"
        ),
    )


def evaluate_w_gdocs_cu_001_maturity(
    proof: DocsCUProof | None = None,
    has_tool_mastery: bool = True,
    has_tests: bool = True,
) -> GoogleDocsCUMaturityDecision:
    if proof is None:
        proof = _build_phase_w0_001r_proof()

    decision = GoogleDocsCUMaturityDecision(proof=proof)
    checks_passed = 0
    total = len(_DOCS_CU_CHECKS)
    gaps = []

    if proof.gui_ownership_proven:
        checks_passed += 1
    else:
        gaps.append("gui_ownership_proven")

    if proof.browser_profile_proven:
        checks_passed += 1
    else:
        gaps.append("browser_profile_proven")

    if proof.account_verified:
        checks_passed += 1
    else:
        gaps.append("account_verified")

    if proof.docs_openable:
        checks_passed += 1
        decision.docs_openable = True
    else:
        gaps.append("docs_openable")

    if proof.tabs_detectable:
        checks_passed += 1
        decision.tabs_detectable = True
    else:
        gaps.append("tabs_detectable")

    if proof.child_tabs_supported:
        checks_passed += 1
        decision.child_tabs_supported = True
    else:
        gaps.append("child_tabs_supported")

    if proof.content_extractable:
        checks_passed += 1
        decision.content_extractable = True
    else:
        gaps.append("content_extractable")

    if proof.scrolling_complete:
        checks_passed += 1
        decision.scrolling_complete = True
    else:
        gaps.append("scrolling_complete")

    if proof.per_doc_provenance_complete:
        checks_passed += 1
        decision.per_doc_provenance_complete = True
    else:
        gaps.append("per_doc_provenance_complete")

    if proof.per_tab_provenance_complete:
        checks_passed += 1
        decision.per_tab_provenance_complete = True
    else:
        gaps.append("per_tab_provenance_complete")

    if proof.empty_tabs_marked:
        checks_passed += 1
        decision.empty_tabs_marked = True
    else:
        gaps.append("empty_tabs_marked")

    if proof.inaccessible_tabs_marked:
        checks_passed += 1
        decision.inaccessible_tabs_marked = True
    else:
        gaps.append("inaccessible_tabs_marked")

    if proof.parity_against_api:
        checks_passed += 1
        decision.parity_against_api = True
    else:
        gaps.append("parity_against_api")

    gov_pass = (
        proof.no_mutation
        and proof.no_credential_capture
        and proof.no_screenshot_ocr
    )
    if gov_pass:
        checks_passed += 1
        decision.governance_passed = True
    else:
        gaps.append("governance_passed")
        decision.governance_passed = False

    if has_tool_mastery:
        checks_passed += 1
        decision.tool_mastery_passed = True
    else:
        gaps.append("tool_mastery_passed")

    if has_tests:
        checks_passed += 1
        decision.tests_present = True
    else:
        gaps.append("tests_present")

    decision.current_maturity_percent = round(
        (checks_passed / total) * 100.0, 1
    )
    decision.gaps_to_100 = gaps
    decision.is_100_percent_mature = checks_passed == total

    if decision.is_100_percent_mature:
        decision.current_status = "complete"
        decision.blockers = []
    else:
        decision.current_status = "partial_needs_hardening"
        decision.blockers = [f"gap: {g}" for g in gaps]
        if proof.content_extraction_blocker:
            decision.blockers.append(
                f"content_extraction: {proof.content_extraction_blocker}"
            )
        decision.hardening_work_orders = [
            f"WO-GDOCS-CU-{g.upper()}" for g in gaps
        ]

    return decision


def w_gdocs_cu_001_is_100_percent_mature(
    proof: DocsCUProof | None = None,
) -> bool:
    return evaluate_w_gdocs_cu_001_maturity(proof).is_100_percent_mature


def build_w_gdocs_cu_001_gap_report(
    proof: DocsCUProof | None = None,
) -> dict[str, Any]:
    decision = evaluate_w_gdocs_cu_001_maturity(proof)
    return {
        "package_id": decision.package_id,
        "is_100_percent": decision.is_100_percent_mature,
        "current_maturity": decision.current_maturity_percent,
        "gaps": decision.gaps_to_100,
        "blockers": decision.blockers,
    }


def build_w_gdocs_cu_001_hardening_work_orders(
    proof: DocsCUProof | None = None,
) -> list[str]:
    decision = evaluate_w_gdocs_cu_001_maturity(proof)
    return decision.hardening_work_orders
