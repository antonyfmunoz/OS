"""Tests for Phase 94D.9 — Chrome Profile Launch Backend."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.substrate.chrome_profile_launch_backend import (
    BACKEND_CLASS,
    BLOCKED_DOMAINS,
    CHROME_PATH,
    DRIVE_URL,
    build_action_attempted_message,
    build_chrome_profile_drive_launch_command,
    build_task_scheduler_profile_launch,
    classify_backend,
    validate_drive_url,
    validate_profile_directory,
)


class TestClassifyBackend:
    def test_backend_is_chrome_profile_launch(self) -> None:
        assert classify_backend() == "VISIBLE_CHROME_PROFILE_LAUNCH"

    def test_not_playwright(self) -> None:
        assert "playwright" not in classify_backend().lower()

    def test_not_explorer(self) -> None:
        assert "explorer" not in classify_backend().lower()


class TestBuildCommand:
    def test_command_includes_chrome_exe(self) -> None:
        cmd = build_chrome_profile_drive_launch_command()
        assert "chrome.exe" in cmd

    def test_command_includes_profile_directory(self) -> None:
        cmd = build_chrome_profile_drive_launch_command(profile_directory="Profile 1")
        assert '--profile-directory="Profile 1"' in cmd

    def test_command_opens_drive_google_com(self) -> None:
        cmd = build_chrome_profile_drive_launch_command()
        assert DRIVE_URL in cmd

    def test_does_not_use_explorer(self) -> None:
        cmd = build_chrome_profile_drive_launch_command()
        assert "explorer" not in cmd.lower()

    def test_does_not_use_playwright(self) -> None:
        cmd = build_chrome_profile_drive_launch_command()
        assert "playwright" not in cmd.lower()

    def test_custom_profile(self) -> None:
        cmd = build_chrome_profile_drive_launch_command(profile_directory="Profile 3")
        assert "Profile 3" in cmd


class TestValidateUrl:
    def test_drive_allowed(self) -> None:
        errors = validate_drive_url(DRIVE_URL)
        assert errors == []

    def test_mail_blocked(self) -> None:
        errors = validate_drive_url("https://mail.google.com/")
        assert any("blocked" in e.lower() for e in errors)

    def test_accounts_blocked(self) -> None:
        errors = validate_drive_url("https://accounts.google.com/")
        assert any("blocked" in e.lower() for e in errors)

    def test_http_blocked(self) -> None:
        errors = validate_drive_url("http://drive.google.com/")
        assert any("HTTPS" in e for e in errors)


class TestValidateProfileDirectory:
    def test_default_valid(self) -> None:
        assert validate_profile_directory("Default") == []

    def test_profile_1_valid(self) -> None:
        assert validate_profile_directory("Profile 1") == []

    def test_profile_2_valid(self) -> None:
        assert validate_profile_directory("Profile 2") == []

    def test_empty_rejected(self) -> None:
        errors = validate_profile_directory("")
        assert len(errors) > 0

    def test_path_traversal_rejected(self) -> None:
        errors = validate_profile_directory("../etc/passwd")
        assert any("traversal" in e.lower() for e in errors)

    def test_backslash_rejected(self) -> None:
        errors = validate_profile_directory("Profile\\..\\secret")
        assert len(errors) > 0

    def test_too_long_rejected(self) -> None:
        errors = validate_profile_directory("A" * 100)
        assert any("too long" in e.lower() for e in errors)


class TestTaskScheduler:
    def test_creates_with_it_flag(self) -> None:
        cmds = build_task_scheduler_profile_launch(profile_directory="Profile 1")
        assert "/it" in cmds["create"].lower()

    def test_includes_profile_directory_in_task(self) -> None:
        cmds = build_task_scheduler_profile_launch(profile_directory="Profile 1")
        assert "Profile 1" in cmds["create"]

    def test_run_command_targets_task(self) -> None:
        cmds = build_task_scheduler_profile_launch()
        assert "schtasks /run" in cmds["run"]

    def test_delete_uses_force(self) -> None:
        cmds = build_task_scheduler_profile_launch()
        assert "/f" in cmds["delete"]


class TestActionAttempted:
    def test_not_confirmed(self) -> None:
        msg = build_action_attempted_message("Profile 1")
        assert msg["payload"]["visible_confirmed"] is False

    def test_no_credentials_used(self) -> None:
        msg = build_action_attempted_message("Profile 1")
        assert msg["payload"]["credentials_used"] is False
        assert msg["payload"]["cookies_read"] is False
        assert msg["payload"]["account_switched_via_ui"] is False

    def test_includes_profile_directory(self) -> None:
        msg = build_action_attempted_message("Profile 1")
        assert msg["payload"]["profile_directory"] == "Profile 1"
