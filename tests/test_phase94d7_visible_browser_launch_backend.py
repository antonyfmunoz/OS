"""Tests for Phase 94D.7R — Visible Chrome Launch Backend."""

from __future__ import annotations

import sys
from unittest.mock import patch

sys.path.insert(0, "/opt/OS")

from eos_ai.substrate.visible_browser_launch_backend import (
    ALLOWED_DOMAINS,
    BACKEND_CLASS,
    BLOCKED_DOMAINS,
    CHROME_WINDOWS_PATHS,
    DRIVE_URL,
    build_backend_missing_message,
    build_chrome_detection_command,
    build_drive_open_action,
    build_open_url_in_chrome_command,
    classify_backend,
    execute_chrome_launch,
    find_chrome_candidates,
    parse_launch_result,
    validate_url_allowed,
)


class TestClassifyBackend:
    def test_backend_is_visible_chrome_launch(self) -> None:
        assert classify_backend() == "VISIBLE_CHROME_LAUNCH"

    def test_backend_is_not_playwright(self) -> None:
        assert classify_backend() != "PLAYWRIGHT"
        assert "playwright" not in classify_backend().lower()

    def test_backend_is_not_default_browser(self) -> None:
        assert classify_backend() != "VISIBLE_DEFAULT_BROWSER_LAUNCH"
        assert "default" not in classify_backend().lower()


class TestChromeDetection:
    def test_chrome_path_includes_program_files(self) -> None:
        candidates = find_chrome_candidates()
        assert any("Program Files" in p and "x86" not in p for p in candidates)

    def test_chrome_path_includes_program_files_x86(self) -> None:
        candidates = find_chrome_candidates()
        assert any("Program Files (x86)" in p for p in candidates)

    def test_chrome_path_includes_localappdata(self) -> None:
        candidates = find_chrome_candidates()
        assert any("LOCALAPPDATA" in p or "Local" in p for p in candidates)

    def test_detection_command_uses_powershell(self) -> None:
        cmd = build_chrome_detection_command()
        assert "powershell.exe" in cmd

    def test_detection_command_checks_chrome_exe(self) -> None:
        cmd = build_chrome_detection_command()
        assert "chrome.exe" in cmd

    def test_detection_command_reports_not_found(self) -> None:
        cmd = build_chrome_detection_command()
        assert "CHROME_NOT_FOUND" in cmd


class TestBuildOpenUrlInChrome:
    def test_command_uses_chrome_exe(self) -> None:
        cmd = build_open_url_in_chrome_command(DRIVE_URL)
        assert "chrome.exe" in cmd

    def test_command_does_not_use_explorer(self) -> None:
        cmd = build_open_url_in_chrome_command(DRIVE_URL)
        assert "explorer" not in cmd.lower()

    def test_command_does_not_use_playwright(self) -> None:
        cmd = build_open_url_in_chrome_command(DRIVE_URL)
        assert "playwright" not in cmd.lower()

    def test_command_contains_url(self) -> None:
        cmd = build_open_url_in_chrome_command(DRIVE_URL)
        assert DRIVE_URL in cmd

    def test_command_uses_start_process(self) -> None:
        cmd = build_open_url_in_chrome_command(DRIVE_URL)
        assert "Start-Process" in cmd

    def test_command_uses_filepath_argument(self) -> None:
        cmd = build_open_url_in_chrome_command(DRIVE_URL)
        assert "-FilePath" in cmd


class TestValidateUrlAllowed:
    def test_drive_google_com_allowed(self) -> None:
        errors = validate_url_allowed("https://drive.google.com/")
        assert errors == []

    def test_drive_google_com_subpath_allowed(self) -> None:
        errors = validate_url_allowed("https://drive.google.com/drive/my-drive")
        assert errors == []

    def test_mail_google_com_blocked(self) -> None:
        errors = validate_url_allowed("https://mail.google.com/")
        assert any("blocked" in e.lower() for e in errors)

    def test_accounts_google_com_blocked(self) -> None:
        errors = validate_url_allowed("https://accounts.google.com/")
        assert any("blocked" in e.lower() for e in errors)

    def test_youtube_blocked(self) -> None:
        errors = validate_url_allowed("https://youtube.com/")
        assert any("blocked" in e.lower() or "not in allowed" in e.lower() for e in errors)

    def test_http_not_https_blocked(self) -> None:
        errors = validate_url_allowed("http://drive.google.com/")
        assert any("HTTPS" in e for e in errors)

    def test_unknown_domain_blocked(self) -> None:
        errors = validate_url_allowed("https://example.com/")
        assert any("not in allowed" in e.lower() for e in errors)

    def test_custom_allowed_domains(self) -> None:
        errors = validate_url_allowed(
            "https://example.com/", allowed_domains=frozenset({"example.com"})
        )
        assert errors == []


class TestBuildDriveOpenAction:
    def test_action_is_open_google_drive(self) -> None:
        action = build_drive_open_action()
        assert action["action"] == "OPEN_GOOGLE_DRIVE"

    def test_backend_is_visible_chrome_launch(self) -> None:
        action = build_drive_open_action()
        assert action["backend"] == "VISIBLE_CHROME_LAUNCH"

    def test_url_is_drive(self) -> None:
        action = build_drive_open_action()
        assert action["url"] == DRIVE_URL

    def test_chrome_command_present(self) -> None:
        action = build_drive_open_action()
        assert "chrome_command" in action
        assert "chrome.exe" in action["chrome_command"]

    def test_chrome_candidates_present(self) -> None:
        action = build_drive_open_action()
        assert "chrome_candidates" in action
        assert len(action["chrome_candidates"]) >= 3


class TestBackendMissing:
    def test_missing_chrome_emits_backend_missing(self) -> None:
        msg = build_backend_missing_message("Chrome not found")
        assert msg["message_type"] == "BACKEND_MISSING"
        assert msg["backend"] == "VISIBLE_CHROME_LAUNCH"

    def test_no_silent_fallback(self) -> None:
        msg = build_backend_missing_message("Chrome not found")
        assert msg["silent_fallback_allowed"] is False

    def test_fallback_options_present(self) -> None:
        msg = build_backend_missing_message("Chrome not found")
        assert len(msg["fallback_options"]) == 5

    def test_requires_advisor_decision(self) -> None:
        msg = build_backend_missing_message("Chrome not found")
        assert msg["next_action_required"] == "ADVISOR_DECISION"


class TestExecuteChromeLaunch:
    def test_blocked_url_fails_without_launching(self) -> None:
        result = execute_chrome_launch("https://mail.google.com/")
        assert result["success"] is False
        assert "blocked" in result["detail"].lower()
        assert result["command_used"] is None

    def test_chrome_found_launches(self) -> None:
        mock_result = type("R", (), {"returncode": 0, "stdout": r"C:\Program Files\Google\Chrome\Application\chrome.exe", "stderr": ""})()
        with patch("eos_ai.substrate.visible_browser_launch_backend.subprocess.run", return_value=mock_result):
            result = execute_chrome_launch(DRIVE_URL)
            assert result["success"] is True
            assert result["backend"] == "VISIBLE_CHROME_LAUNCH"
            assert result["chrome_path"] is not None

    def test_chrome_not_found_returns_backend_missing(self) -> None:
        mock_result = type("R", (), {"returncode": 1, "stdout": "CHROME_NOT_FOUND", "stderr": ""})()
        with patch("eos_ai.substrate.visible_browser_launch_backend.subprocess.run", return_value=mock_result):
            result = execute_chrome_launch(DRIVE_URL)
            assert result["success"] is False
            assert result["detail"] == "CHROME_NOT_FOUND"
            assert "backend_missing" in result

    def test_chrome_not_found_does_not_silently_fallback(self) -> None:
        mock_result = type("R", (), {"returncode": 1, "stdout": "CHROME_NOT_FOUND", "stderr": ""})()
        with patch("eos_ai.substrate.visible_browser_launch_backend.subprocess.run", return_value=mock_result):
            result = execute_chrome_launch(DRIVE_URL)
            assert result.get("backend_missing") is not None
            missing = result["backend_missing"]
            assert missing["silent_fallback_allowed"] is False


class TestParseLaunchResult:
    def test_success_message(self) -> None:
        result = {
            "success": True,
            "url": DRIVE_URL,
            "backend": BACKEND_CLASS,
            "chrome_path": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        }
        msg = parse_launch_result(result)
        assert "Chrome opened" in msg
        assert DRIVE_URL in msg

    def test_failure_message(self) -> None:
        result = {
            "success": False,
            "detail": "CHROME_NOT_FOUND",
        }
        msg = parse_launch_result(result)
        assert "not found" in msg.lower()
        assert "silent fallback" not in msg.lower() or "no silent fallback" in msg.lower()

    def test_generic_failure_message(self) -> None:
        result = {
            "success": False,
            "detail": "OS error: some issue",
        }
        msg = parse_launch_result(result)
        assert "failed" in msg.lower()
