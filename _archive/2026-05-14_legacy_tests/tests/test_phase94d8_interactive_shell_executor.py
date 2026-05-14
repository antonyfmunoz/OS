"""Tests for Phase 94D.8 — Interactive Shell Executor."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.substrate.interactive_shell_executor import (
    CHROME_PATH_CONFIRMED,
    DRIVE_URL,
    build_founder_confirmation_prompt,
    build_next_gate_message,
    build_open_drive_in_chrome_script,
    build_send_open_drive_to_tmux_command,
    classify_visual_confirmation_response,
    visible_success_requires_confirmation,
)


class TestChromeCommand:
    def test_script_uses_chrome_exe(self) -> None:
        script = build_open_drive_in_chrome_script()
        assert "chrome.exe" in script

    def test_script_opens_drive_only(self) -> None:
        script = build_open_drive_in_chrome_script()
        assert DRIVE_URL in script
        assert "mail.google.com" not in script
        assert "gmail" not in script.lower()

    def test_script_does_not_use_playwright(self) -> None:
        script = build_open_drive_in_chrome_script()
        assert "playwright" not in script.lower()

    def test_script_does_not_use_explorer(self) -> None:
        script = build_open_drive_in_chrome_script()
        assert "explorer.exe" not in script.lower()

    def test_tmux_command_targets_pane(self) -> None:
        cmd = build_send_open_drive_to_tmux_command("gui_shell:0.0")
        assert "gui_shell:0.0" in cmd
        assert "send-keys" in cmd


class TestVisualConfirmation:
    def test_requires_confirmation(self) -> None:
        assert visible_success_requires_confirmation() is True

    def test_confirmed_visible_emits_verify_gate(self) -> None:
        result = classify_visual_confirmation_response("CONFIRMED_VISIBLE")
        assert result["visible_success"] is True
        assert result["next_gate"] == "VERIFY_ACTIVE_GOOGLE_ACCOUNT"

    def test_not_visible_marks_false_positive(self) -> None:
        result = classify_visual_confirmation_response("NOT_VISIBLE")
        assert result["visible_success"] is False
        assert result["status"] == "FALSE_POSITIVE"
        assert result["blocks_automation"] is True

    def test_login_required_pauses(self) -> None:
        result = classify_visual_confirmation_response("LOGIN_REQUIRED")
        assert result["visible_success"] is True
        assert result["next_gate"] == "LOGIN_REQUIRED_MANUAL_INTERVENTION"
        assert result["blocks_automation"] is True
        assert result.get("credential_capture_allowed") is False

    def test_wrong_account_pauses(self) -> None:
        result = classify_visual_confirmation_response("WRONG_ACCOUNT")
        assert result["visible_success"] is True
        assert result["next_gate"] == "WRONG_ACCOUNT_PAUSE"
        assert result["blocks_automation"] is True
        assert result.get("account_switching_allowed") is False

    def test_cancel_stops(self) -> None:
        result = classify_visual_confirmation_response("CANCEL")
        assert result["visible_success"] is False
        assert result["blocks_automation"] is True


class TestNextGateMessage:
    def test_confirmed_visible_builds_gate(self) -> None:
        msg = build_next_gate_message("CONFIRMED_VISIBLE")
        assert msg is not None
        assert msg["payload"]["action"] == "VERIFY_ACTIVE_GOOGLE_ACCOUNT"
        assert msg["payload"]["blocked_until_approved"] is True

    def test_not_visible_returns_none(self) -> None:
        msg = build_next_gate_message("NOT_VISIBLE")
        assert msg is None

    def test_login_required_builds_gate(self) -> None:
        msg = build_next_gate_message("LOGIN_REQUIRED")
        assert msg is not None
        assert msg["payload"]["action"] == "LOGIN_REQUIRED_MANUAL_INTERVENTION"

    def test_wrong_account_builds_gate(self) -> None:
        msg = build_next_gate_message("WRONG_ACCOUNT")
        assert msg is not None
        assert msg["payload"]["action"] == "WRONG_ACCOUNT_PAUSE"


class TestConfirmationPrompt:
    def test_prompt_asks_about_chrome(self) -> None:
        prompt = build_founder_confirmation_prompt()
        assert "Chrome" in prompt["question"]
        assert "Google Drive" in prompt["question"]

    def test_prompt_includes_do_not_rules(self) -> None:
        prompt = build_founder_confirmation_prompt()
        assert len(prompt["do_not"]) >= 3
        assert any("credential" in d.lower() for d in prompt["do_not"])
