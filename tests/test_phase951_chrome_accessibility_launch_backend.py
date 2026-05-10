"""Tests for Phase 95.1 — Chrome Accessibility Launch Backend."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from eos_ai.substrate.chrome_accessibility_launch_backend import (
    BACKEND_CLASS,
    build_chrome_accessibility_launch_command,
    build_task_scheduler_accessibility_launch,
    classify_backend,
    validate_accessibility_flags,
)


class TestClassifyBackend:
    def test_backend_class(self) -> None:
        assert classify_backend() == "VISIBLE_CHROME_ACCESSIBILITY_LAUNCH"

    def test_not_playwright(self) -> None:
        assert "playwright" not in classify_backend().lower()

    def test_not_cdp(self) -> None:
        assert "cdp" not in classify_backend().lower()
        assert "devtools" not in classify_backend().lower()


class TestBuildCommand:
    def test_includes_chrome_exe(self) -> None:
        cmd = build_chrome_accessibility_launch_command()
        assert "chrome.exe" in cmd

    def test_includes_profile_directory(self) -> None:
        cmd = build_chrome_accessibility_launch_command(profile_directory="Profile 5")
        assert '--profile-directory="Profile 5"' in cmd

    def test_includes_force_renderer_accessibility(self) -> None:
        cmd = build_chrome_accessibility_launch_command()
        assert "--force-renderer-accessibility" in cmd

    def test_does_not_include_remote_debugging_port(self) -> None:
        cmd = build_chrome_accessibility_launch_command()
        assert "--remote-debugging-port" not in cmd

    def test_does_not_include_headless(self) -> None:
        cmd = build_chrome_accessibility_launch_command()
        assert "--headless" not in cmd

    def test_includes_url(self) -> None:
        cmd = build_chrome_accessibility_launch_command()
        assert "drive.google.com" in cmd


class TestValidateFlags:
    def test_allowed_flags_pass(self) -> None:
        errors = validate_accessibility_flags([
            "--force-renderer-accessibility",
            "--profile-directory=Profile 5",
        ])
        assert errors == []

    def test_remote_debugging_blocked(self) -> None:
        errors = validate_accessibility_flags(["--remote-debugging-port=9222"])
        assert any("Blocked" in e for e in errors)

    def test_headless_blocked(self) -> None:
        errors = validate_accessibility_flags(["--headless"])
        assert any("Blocked" in e for e in errors)

    def test_enable_automation_blocked(self) -> None:
        errors = validate_accessibility_flags(["--enable-automation"])
        assert any("Blocked" in e for e in errors)

    def test_url_allowed(self) -> None:
        errors = validate_accessibility_flags(["https://drive.google.com/"])
        assert errors == []


class TestTaskSchedulerCommand:
    def test_create_includes_it(self) -> None:
        cmds = build_task_scheduler_accessibility_launch()
        assert "/it" in cmds["create"].lower()

    def test_create_includes_accessibility_flag(self) -> None:
        cmds = build_task_scheduler_accessibility_launch()
        assert "force-renderer-accessibility" in cmds["create"]

    def test_create_includes_profile(self) -> None:
        cmds = build_task_scheduler_accessibility_launch(profile_directory="Profile 5")
        assert "Profile 5" in cmds["create"]

    def test_run_command(self) -> None:
        cmds = build_task_scheduler_accessibility_launch()
        assert "schtasks /run" in cmds["run"]

    def test_delete_command(self) -> None:
        cmds = build_task_scheduler_accessibility_launch()
        assert "/f" in cmds["delete"]
