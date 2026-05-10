"""CU Execution Probe.

Evaluates whether the current runtime environment can execute
Computer Use hardening or production parity tests.

Pure contract functions — no live GUI execution.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CUExecutionProbeStatus(str, Enum):
    READY = "ready"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    NO_VISIBLE_SESSION = "no_visible_session"
    WRONG_ACCOUNT = "wrong_account"
    DRIVE_NOT_OPEN = "drive_not_open"
    DOC_NOT_OPEN = "doc_not_open"
    UI_ACCESS_BLOCKED = "ui_access_blocked"
    EXTRACTION_BLOCKED = "extraction_blocked"
    GOVERNANCE_BLOCKED = "governance_blocked"


@dataclass
class CUExecutionProbeResult:
    probe_id: str = ""
    target_package_id: str = ""
    source_system: str = ""
    browser_profile: str = ""
    account_expected: str = ""
    account_confirmed: bool = False
    visible_session_available: bool = False
    drive_visible: bool = False
    doc_visible: bool = False
    ui_access_available: bool = False
    extraction_available: bool = False
    governance_safe: bool = True
    can_run_hardening_test: bool = False
    can_run_production_parity: bool = False
    blockers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "probe_id": self.probe_id,
            "target_package_id": self.target_package_id,
            "source_system": self.source_system,
            "browser_profile": self.browser_profile,
            "account_expected": self.account_expected,
            "account_confirmed": self.account_confirmed,
            "visible_session_available": self.visible_session_available,
            "drive_visible": self.drive_visible,
            "doc_visible": self.doc_visible,
            "ui_access_available": self.ui_access_available,
            "extraction_available": self.extraction_available,
            "governance_safe": self.governance_safe,
            "can_run_hardening_test": self.can_run_hardening_test,
            "can_run_production_parity": self.can_run_production_parity,
            "blockers": self.blockers,
            "notes": self.notes,
        }


def build_cu_probe_result(
    probe_id: str = "",
    target_package_id: str = "",
    source_system: str = "",
    browser_profile: str = "",
    account_expected: str = "",
    account_confirmed: bool = False,
    visible_session_available: bool = False,
    drive_visible: bool = False,
    doc_visible: bool = False,
    ui_access_available: bool = False,
    extraction_available: bool = False,
    governance_safe: bool = True,
) -> CUExecutionProbeResult:
    result = CUExecutionProbeResult(
        probe_id=probe_id,
        target_package_id=target_package_id,
        source_system=source_system,
        browser_profile=browser_profile,
        account_expected=account_expected,
        account_confirmed=account_confirmed,
        visible_session_available=visible_session_available,
        drive_visible=drive_visible,
        doc_visible=doc_visible,
        ui_access_available=ui_access_available,
        extraction_available=extraction_available,
        governance_safe=governance_safe,
    )

    blockers = []
    if not visible_session_available:
        blockers.append("NO_VISIBLE_SESSION")
    if not account_confirmed:
        blockers.append("ACCOUNT_NOT_CONFIRMED")
    if not drive_visible:
        blockers.append("DRIVE_NOT_VISIBLE")
    if not ui_access_available:
        blockers.append("UI_ACCESS_BLOCKED")
    if not extraction_available:
        blockers.append("EXTRACTION_BLOCKED")
    if not governance_safe:
        blockers.append("GOVERNANCE_BLOCKED")
    result.blockers = blockers

    result.can_run_hardening_test = (
        visible_session_available
        and governance_safe
        and ui_access_available
    )
    result.can_run_production_parity = (
        result.can_run_hardening_test
        and account_confirmed
        and extraction_available
        and drive_visible
    )
    return result


def cu_probe_allows_hardening(result: CUExecutionProbeResult) -> bool:
    return result.can_run_hardening_test


def cu_probe_allows_production_parity(
    result: CUExecutionProbeResult,
) -> bool:
    return result.can_run_production_parity


def cu_probe_blocks_maturity(result: CUExecutionProbeResult) -> bool:
    return not result.can_run_production_parity


def summarize_cu_probe(result: CUExecutionProbeResult) -> dict[str, Any]:
    return {
        "probe_id": result.probe_id,
        "target_package_id": result.target_package_id,
        "can_harden": result.can_run_hardening_test,
        "can_parity": result.can_run_production_parity,
        "blocker_count": len(result.blockers),
        "blockers": result.blockers,
    }


def build_vps_environment_probe(
    target_package_id: str,
) -> CUExecutionProbeResult:
    """Probe for VPS/Linux headless environment — no visible session."""
    return build_cu_probe_result(
        probe_id="vps_headless_probe",
        target_package_id=target_package_id,
        source_system="linux_vps",
        browser_profile="none",
        account_expected="antonyfm@empyreanstudios.co",
        account_confirmed=False,
        visible_session_available=False,
        drive_visible=False,
        doc_visible=False,
        ui_access_available=False,
        extraction_available=False,
        governance_safe=True,
    )


def build_windows_local_probe(
    target_package_id: str,
    account_confirmed: bool = False,
    drive_visible: bool = False,
    doc_visible: bool = False,
    extraction_available: bool = False,
) -> CUExecutionProbeResult:
    """Probe for Windows local desktop with Chrome."""
    return build_cu_probe_result(
        probe_id="windows_local_probe",
        target_package_id=target_package_id,
        source_system="windows_desktop",
        browser_profile="default_chrome_profile",
        account_expected="antonyfm@empyreanstudios.co",
        account_confirmed=account_confirmed,
        visible_session_available=True,
        drive_visible=drive_visible,
        doc_visible=doc_visible,
        ui_access_available=True,
        extraction_available=extraction_available,
        governance_safe=True,
    )
