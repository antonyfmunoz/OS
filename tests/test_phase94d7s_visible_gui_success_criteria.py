"""Tests for Phase 94D.7S — Visible GUI Success Criteria."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from eos_ai.substrate.interactive_gui_worker_contracts import (
    build_action_attempted_outbox,
    build_interactive_chrome_launch_command,
    build_interactive_launch_intent,
    build_visible_confirmed_outbox,
    classify_current_ssh_path,
    get_recommended_mvp_path,
)
from eos_ai.substrate.visible_gui_success_criteria import (
    LaunchContext,
    VisibleGuiStatus,
    build_action_attempted_status,
    build_waiting_for_confirmation_message,
    demote_ssh_launch_to_attempted,
    evaluate_founder_confirmation,
    is_context_reliable_for_gui,
    is_exit_code_sufficient_for_visible_success,
)


class TestExitCodeNotSufficient:
    def test_exit_code_not_sufficient_for_visible(self) -> None:
        assert is_exit_code_sufficient_for_visible_success() is False

    def test_ssh_context_unreliable_for_gui(self) -> None:
        assert is_context_reliable_for_gui(LaunchContext.NON_INTERACTIVE_WINDOWS_SSH) is False

    def test_interactive_desktop_reliable_for_gui(self) -> None:
        assert is_context_reliable_for_gui(LaunchContext.INTERACTIVE_WINDOWS_DESKTOP) is True

    def test_action_attempted_does_not_claim_visible(self) -> None:
        status = build_action_attempted_status(
            action="OPEN_GOOGLE_DRIVE",
            backend="VISIBLE_CHROME_LAUNCH",
            command_exit_code=0,
            launch_context=LaunchContext.NON_INTERACTIVE_WINDOWS_SSH,
        )
        assert status["visible_confirmed"] is False
        assert status["requires_founder_confirmation"] is True
        assert status["exit_code_sufficient_for_visible"] is False


class TestFounderConfirmation:
    def test_confirmed_visible_marks_success(self) -> None:
        result = evaluate_founder_confirmation("CONFIRMED_VISIBLE")
        assert result["visible_success"] is True
        assert result["status"] == VisibleGuiStatus.CONFIRMED_VISIBLE

    def test_not_visible_marks_false_positive(self) -> None:
        result = evaluate_founder_confirmation("NOT_VISIBLE")
        assert result["visible_success"] is False
        assert result["status"] == VisibleGuiStatus.FALSE_POSITIVE
        assert result["blocks_automation"] is True

    def test_no_confirmation_leaves_pending(self) -> None:
        status = build_action_attempted_status(
            action="OPEN_GOOGLE_DRIVE",
            backend="VISIBLE_CHROME_LAUNCH",
            command_exit_code=0,
            launch_context=LaunchContext.INTERACTIVE_WINDOWS_DESKTOP,
        )
        assert status["status"] == VisibleGuiStatus.ACTION_ATTEMPTED
        assert status["visible_confirmed"] is False

    def test_login_required_pauses(self) -> None:
        result = evaluate_founder_confirmation("LOGIN_REQUIRED")
        assert result["status"] == VisibleGuiStatus.LOGIN_REQUIRED
        assert result["blocks_automation"] is True
        assert result["next_action"] == "LOGIN_REQUIRED_MANUAL_INTERVENTION"

    def test_wrong_account_pauses(self) -> None:
        result = evaluate_founder_confirmation("WRONG_ACCOUNT")
        assert result["status"] == VisibleGuiStatus.WRONG_ACCOUNT
        assert result["blocks_automation"] is True
        assert result["next_action"] == "WRONG_ACCOUNT_PAUSE"

    def test_cancel_stops(self) -> None:
        result = evaluate_founder_confirmation("CANCEL")
        assert result["status"] == VisibleGuiStatus.CANCEL
        assert result["blocks_automation"] is True


class TestCredentialSafety:
    def test_credential_capture_not_in_valid_responses(self) -> None:
        msg = build_waiting_for_confirmation_message(
            work_order_id="WO-001", action="OPEN_GOOGLE_DRIVE"
        )
        valid = msg["payload"]["valid_responses"]
        assert "CAPTURE_CREDENTIALS" not in valid
        assert "SCREENSHOT" not in valid

    def test_no_credential_field_in_confirmation_message(self) -> None:
        msg = build_waiting_for_confirmation_message(
            work_order_id="WO-001", action="OPEN_GOOGLE_DRIVE"
        )
        payload_str = str(msg)
        assert "password" not in payload_str.lower()
        assert "credential" not in payload_str.lower()
        assert "token" not in payload_str.lower()
        assert "cookie" not in payload_str.lower()


class TestSshDemotion:
    def test_ssh_classified_non_interactive(self) -> None:
        info = classify_current_ssh_path()
        assert info["classification"] == LaunchContext.NON_INTERACTIVE_WINDOWS_SSH
        assert info["reliable_for_gui"] is False

    def test_ssh_allowed_for_file_operations(self) -> None:
        info = classify_current_ssh_path()
        assert info["reliable_for_commands"] is True

    def test_demote_ssh_success_to_attempted(self) -> None:
        previous = {"success": True, "backend": "VISIBLE_CHROME_LAUNCH", "exit_code": 0}
        demoted = demote_ssh_launch_to_attempted(previous)
        assert demoted["corrected_status"] == VisibleGuiStatus.ACTION_ATTEMPTED
        assert demoted["visible_confirmed"] is False
        assert demoted["launch_context"] == LaunchContext.NON_INTERACTIVE_WINDOWS_SSH


class TestInteractiveWorkerContracts:
    def test_launch_intent_requires_interactive_context(self) -> None:
        intent = build_interactive_launch_intent()
        assert intent["launch_context_required"] == LaunchContext.INTERACTIVE_WINDOWS_DESKTOP

    def test_launch_intent_exit_code_not_sufficient(self) -> None:
        intent = build_interactive_launch_intent()
        assert intent["success_criteria"]["exit_code_sufficient"] is False
        assert intent["success_criteria"]["requires_founder_visual_confirmation"] is True

    def test_action_attempted_outbox_not_confirmed(self) -> None:
        msg = build_action_attempted_outbox()
        assert msg["message_type"] == "ACTION_ATTEMPTED"
        assert msg["payload"]["visible_confirmed"] is False

    def test_visible_confirmed_outbox_confirmed(self) -> None:
        msg = build_visible_confirmed_outbox()
        assert msg["message_type"] == "ACTION_EXECUTED_VISIBLE"
        assert msg["payload"]["visible_confirmed"] is True

    def test_chrome_command_uses_confirmed_path(self) -> None:
        cmd = build_interactive_chrome_launch_command()
        assert "chrome.exe" in cmd
        assert "Start-Process" in cmd
        assert "Program Files" in cmd

    def test_mvp_path_is_manual_terminal(self) -> None:
        mvp = get_recommended_mvp_path()
        assert mvp["recommended"] == "A"
        assert "terminal" in mvp["description"].lower()
