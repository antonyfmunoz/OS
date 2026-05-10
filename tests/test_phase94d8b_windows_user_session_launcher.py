"""Tests for Phase 94D.8B — Windows User-Session Launcher."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from eos_ai.substrate.windows_user_session_launcher import (
    CHROME_PATH,
    DRIVE_URL,
    TASK_NAME,
    build_action_attempted_message,
    build_cleanup_command,
    build_create_scheduled_task_command,
    build_delete_scheduled_task_command,
    build_full_launch_sequence,
    build_run_scheduled_task_command,
    build_ssh_create_and_run_command,
    classify_launch_context,
    get_why_task_scheduler,
)


class TestScheduledTaskCommands:
    def test_create_uses_schtasks(self) -> None:
        cmd = build_create_scheduled_task_command()
        assert "schtasks /create" in cmd

    def test_create_uses_it_flag(self) -> None:
        cmd = build_create_scheduled_task_command()
        assert "/it" in cmd.lower()

    def test_create_includes_chrome_path(self) -> None:
        cmd = build_create_scheduled_task_command()
        assert "chrome.exe" in cmd

    def test_create_includes_drive_url(self) -> None:
        cmd = build_create_scheduled_task_command()
        assert DRIVE_URL in cmd

    def test_create_uses_force_flag(self) -> None:
        cmd = build_create_scheduled_task_command()
        assert "/f" in cmd

    def test_run_uses_task_name(self) -> None:
        cmd = build_run_scheduled_task_command()
        assert TASK_NAME in cmd
        assert "schtasks /run" in cmd

    def test_delete_uses_force(self) -> None:
        cmd = build_delete_scheduled_task_command()
        assert "/f" in cmd
        assert TASK_NAME in cmd

    def test_full_sequence_has_create_and_run(self) -> None:
        seq = build_full_launch_sequence()
        assert len(seq) == 2
        assert "create" in seq[0]
        assert "run" in seq[1]


class TestSSHCommand:
    def test_ssh_command_uses_key(self) -> None:
        cmd = build_ssh_create_and_run_command()
        assert "id_ed25519" in cmd

    def test_ssh_command_targets_local_pc(self) -> None:
        cmd = build_ssh_create_and_run_command()
        assert "100.74.199.102" in cmd

    def test_ssh_command_chains_create_and_run(self) -> None:
        cmd = build_ssh_create_and_run_command()
        assert "&&" in cmd
        assert "create" in cmd
        assert "run" in cmd

    def test_does_not_use_wsl(self) -> None:
        cmd = build_ssh_create_and_run_command()
        assert "wsl" not in cmd.lower()


class TestClassification:
    def test_context_is_task_scheduler(self) -> None:
        assert classify_launch_context() == "WINDOWS_TASK_SCHEDULER_INTERACTIVE"

    def test_not_ssh_service(self) -> None:
        assert "SSH" not in classify_launch_context()


class TestActionAttempted:
    def test_message_not_confirmed(self) -> None:
        msg = build_action_attempted_message(exit_code=0)
        assert msg["payload"]["visible_confirmed"] is False

    def test_message_records_demoted_paths(self) -> None:
        msg = build_action_attempted_message(exit_code=0)
        demoted = msg["payload"]["demoted_paths"]
        assert "NON_INTERACTIVE_WINDOWS_SSH_LAUNCH" in demoted
        assert "SSH_ORIGINATED_TMUX_LAUNCH" in demoted

    def test_message_uses_task_scheduler_method(self) -> None:
        msg = build_action_attempted_message(exit_code=0)
        assert msg["payload"]["launch_method"] == "WINDOWS_TASK_SCHEDULER_INTERACTIVE"

    def test_no_playwright_in_message(self) -> None:
        msg = build_action_attempted_message(exit_code=0)
        assert "playwright" not in str(msg).lower()

    def test_no_credential_in_message(self) -> None:
        msg = build_action_attempted_message(exit_code=0)
        assert "password" not in str(msg).lower()
        assert "credential" not in str(msg).lower()
