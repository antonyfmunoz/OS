"""Tests for Phase 94D.5 GUI backend healthcheck."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import json

import pytest

from eos_ai.substrate.gui_backend_healthcheck import (
    BackendCandidate,
    BackendCheck,
    BackendStatus,
    GUIHealthcheckReport,
    build_gui_missing_approval_request,
    build_healthcheck_report_from_results,
    generate_healthcheck_commands,
)


class TestHealthcheckGeneration:
    def test_gui_backend_is_preferred(self):
        checks = generate_healthcheck_commands()
        preferred = [c for c in checks if c.is_preferred]
        assert len(preferred) >= 1
        names = [c.candidate for c in preferred]
        assert BackendCandidate.PYAUTOGUI.value in names

    def test_playwright_is_not_default(self):
        checks = generate_healthcheck_commands()
        pw = next(c for c in checks if c.candidate == BackendCandidate.PLAYWRIGHT_VISIBLE.value)
        assert pw.requires_founder_approval is True
        assert pw.is_preferred is False

    def test_manual_fallback_always_available(self):
        checks = generate_healthcheck_commands()
        manual = next(c for c in checks if c.candidate == BackendCandidate.MANUAL_FALLBACK.value)
        assert manual.status == BackendStatus.AVAILABLE

    def test_no_mouse_keyboard_browser_in_commands(self):
        checks = generate_healthcheck_commands()
        for check in checks:
            cmd = check.check_command.lower()
            assert "click" not in cmd
            assert "move" not in cmd
            assert "type(" not in cmd
            assert "press(" not in cmd
            assert "open(" not in cmd or "open(" in "import"
            assert "launch" not in cmd


class TestHealthcheckReport:
    def test_missing_gui_creates_advisor_question(self):
        results = {
            "visible_display": "DISPLAY",
            BackendCandidate.PYAUTOGUI.value: "",
            BackendCandidate.ANTHROPIC_COMPUTER_USE.value: "",
            BackendCandidate.PLAYWRIGHT_VISIBLE.value: "",
            BackendCandidate.MANUAL_FALLBACK.value: "always available",
        }
        report = build_healthcheck_report_from_results(results)
        assert report.overall_status == BackendStatus.MISSING
        assert report.advisor_question_needed is True
        assert len(report.advisor_options) > 0

    def test_available_gui_no_advisor_question(self):
        results = {
            "visible_display": "DISPLAY",
            BackendCandidate.PYAUTOGUI.value: "pyautogui OK",
            BackendCandidate.ANTHROPIC_COMPUTER_USE.value: "anthropic SDK OK",
            BackendCandidate.MANUAL_FALLBACK.value: "always available",
        }
        report = build_healthcheck_report_from_results(results)
        assert report.overall_status == BackendStatus.AVAILABLE
        assert report.advisor_question_needed is False

    def test_report_serializes(self):
        report = GUIHealthcheckReport(
            node_id="test_node",
            overall_status=BackendStatus.AVAILABLE,
        )
        json_str = report.to_json()
        data = json.loads(json_str)
        assert data["node_id"] == "test_node"
        assert data["overall_status"] == "available"


class TestAdvisorApprovalRequest:
    def test_gui_missing_builds_approval(self):
        report = GUIHealthcheckReport(
            node_id="local_pc_worker",
            overall_status=BackendStatus.MISSING,
            advisor_question_needed=True,
            advisor_question="GUI not available",
            advisor_options=["A. Install", "B. Playwright", "C. Manual", "D. Cancel"],
        )
        payload = build_gui_missing_approval_request("WO-TEST-001", report)
        assert payload["work_order_id"] == "WO-TEST-001"
        assert payload["action"] == "GUI_BACKEND_DECISION"
        assert payload["blocked_until_approved"] is True
        assert len(payload["options"]) == 4
