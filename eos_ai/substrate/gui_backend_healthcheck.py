"""
GUI computer-use backend healthcheck for Phase 94D.5.

Generates safe healthcheck commands and parses reported capability.
Does NOT execute any commands, move mouse, click, type, or open browser.

The healthcheck produces a status report that the worker uses to decide
whether to proceed with GUI_COMPUTER_USE or ask the advisor for fallback.

No computer use. No Google Drive. No browser automation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BackendStatus(str, Enum):
    AVAILABLE = "available"
    MISSING = "missing"
    PARTIAL = "partial"
    NEEDS_INSTALL = "needs_install"
    NEEDS_FOUNDER_DECISION = "needs_founder_decision"


class BackendCandidate(str, Enum):
    ANTHROPIC_COMPUTER_USE = "anthropic_computer_use"
    PYAUTOGUI = "pyautogui"
    WINDOWS_UI_AUTOMATION = "windows_ui_automation"
    BROWSER_USE_ADAPTER = "browser_use_adapter"
    PLAYWRIGHT_VISIBLE = "playwright_visible"
    MANUAL_FALLBACK = "manual_fallback"


@dataclass
class BackendCheck:
    candidate: str
    status: BackendStatus
    check_command: str
    detail: str = ""
    is_preferred: bool = False
    requires_founder_approval: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate": self.candidate,
            "status": self.status.value,
            "check_command": self.check_command,
            "detail": self.detail,
            "is_preferred": self.is_preferred,
            "requires_founder_approval": self.requires_founder_approval,
        }


@dataclass
class GUIHealthcheckReport:
    node_id: str = "local_pc_worker"
    overall_status: BackendStatus = BackendStatus.MISSING
    preferred_backend: str = "GUI_COMPUTER_USE"
    checks: list[BackendCheck] = field(default_factory=list)
    has_visible_display: bool | None = None
    has_screen_control: bool | None = None
    has_screenshot_capability: bool | None = None
    advisor_question_needed: bool = False
    advisor_question: str = ""
    advisor_options: list[str] = field(default_factory=list)
    checked_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "overall_status": self.overall_status.value,
            "preferred_backend": self.preferred_backend,
            "checks": [c.to_dict() for c in self.checks],
            "has_visible_display": self.has_visible_display,
            "has_screen_control": self.has_screen_control,
            "has_screenshot_capability": self.has_screenshot_capability,
            "advisor_question_needed": self.advisor_question_needed,
            "advisor_question": self.advisor_question,
            "advisor_options": self.advisor_options,
            "checked_at": self.checked_at,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def generate_healthcheck_commands() -> list[BackendCheck]:
    """Generate safe healthcheck commands for the local worker.

    These commands detect presence of GUI backends without performing
    any mouse/keyboard/browser actions.
    """
    checks = [
        BackendCheck(
            candidate=BackendCandidate.PYAUTOGUI.value,
            status=BackendStatus.MISSING,
            check_command="python3 -c \"import pyautogui; print('pyautogui OK')\"",
            detail="Check if pyautogui is installed (screen control)",
            is_preferred=True,
        ),
        BackendCheck(
            candidate=BackendCandidate.ANTHROPIC_COMPUTER_USE.value,
            status=BackendStatus.MISSING,
            check_command="python3 -c \"import anthropic; print('anthropic SDK OK')\"",
            detail="Check if Anthropic SDK with computer-use is available",
            is_preferred=True,
        ),
        BackendCheck(
            candidate=BackendCandidate.WINDOWS_UI_AUTOMATION.value,
            status=BackendStatus.MISSING,
            check_command="python3 -c \"import subprocess; subprocess.run(['powershell', '-Command', 'Get-Process explorer'], capture_output=True); print('WinUI OK')\"",
            detail="Check if Windows UI automation is accessible (desktop running)",
        ),
        BackendCheck(
            candidate=BackendCandidate.PLAYWRIGHT_VISIBLE.value,
            status=BackendStatus.MISSING,
            check_command="python3 -c \"import playwright; print('playwright installed')\"",
            detail="Check if Playwright is installed (NOT default, requires approval)",
            requires_founder_approval=True,
        ),
        BackendCheck(
            candidate=BackendCandidate.MANUAL_FALLBACK.value,
            status=BackendStatus.AVAILABLE,
            check_command="echo 'manual fallback always available'",
            detail="Human operator fallback — always available",
        ),
    ]

    display_check = BackendCheck(
        candidate="visible_display",
        status=BackendStatus.MISSING,
        check_command="python3 -c \"import os; print('DISPLAY' if os.environ.get('DISPLAY') or os.name == 'nt' else 'NO_DISPLAY')\"",
        detail="Check if a visible display is available",
    )
    checks.insert(0, display_check)

    return checks


def build_healthcheck_report_from_results(
    results: dict[str, str],
    node_id: str = "local_pc_worker",
) -> GUIHealthcheckReport:
    """Build a healthcheck report from command execution results.

    `results` maps candidate name → stdout output from running the check command.
    """
    checks = generate_healthcheck_commands()
    gui_available = False
    display_available = False

    for check in checks:
        output = results.get(check.candidate, "")
        if (
            "OK" in output
            or "installed" in output
            or "available" in output
            or (
                check.candidate == "visible_display"
                and "DISPLAY" in output
                and "NO_DISPLAY" not in output
            )
        ):
            check.status = BackendStatus.AVAILABLE
            if check.candidate == "visible_display":
                display_available = True
            elif check.is_preferred:
                gui_available = True
        elif output:
            check.status = BackendStatus.PARTIAL
        else:
            check.status = BackendStatus.MISSING

    if gui_available and display_available:
        overall = BackendStatus.AVAILABLE
        advisor_needed = False
        advisor_q = ""
        advisor_opts: list[str] = []
    elif gui_available and not display_available:
        overall = BackendStatus.PARTIAL
        advisor_needed = True
        advisor_q = "GUI backend installed but no visible display detected. Options?"
        advisor_opts = [
            "A. Verify display is active and retry",
            "B. Use Playwright visible-browser fallback (requires approval)",
            "C. Use manual fallback",
            "D. Cancel work order",
        ]
    else:
        overall = BackendStatus.MISSING
        advisor_needed = True
        advisor_q = (
            "GUI computer-use backend is not available on this machine. "
            "The work order requires visible screen control for supervised execution."
        )
        advisor_opts = [
            "A. Install GUI computer-use backend (pyautogui + anthropic SDK)",
            "B. Switch to Playwright browser automation (not recommended for pilot)",
            "C. Use manual fallback (founder performs steps, worker records)",
            "D. Cancel this work order",
        ]

    return GUIHealthcheckReport(
        node_id=node_id,
        overall_status=overall,
        checks=checks,
        has_visible_display=display_available,
        has_screen_control=gui_available,
        has_screenshot_capability=gui_available and display_available,
        advisor_question_needed=advisor_needed,
        advisor_question=advisor_q,
        advisor_options=advisor_opts,
    )


def build_gui_missing_approval_request(
    work_order_id: str,
    report: GUIHealthcheckReport,
) -> dict[str, Any]:
    """Build the advisor approval request payload when GUI backend is missing."""
    return {
        "approval_request_id": f"apr_gui_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "work_order_id": work_order_id,
        "node_id": report.node_id,
        "action": "GUI_BACKEND_DECISION",
        "target": "local_pc_worker",
        "description": report.advisor_question,
        "risk_level": "MEDIUM",
        "backend": "GUI_COMPUTER_USE",
        "options": report.advisor_options,
        "healthcheck_summary": {
            "overall_status": report.overall_status.value,
            "has_visible_display": report.has_visible_display,
            "has_screen_control": report.has_screen_control,
        },
        "blocked_until_approved": True,
    }
