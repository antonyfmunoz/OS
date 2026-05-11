"""Tests for Phase 94D.8 — Environment Contracts."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.substrate.environment_contracts import (
    EnvironmentBinding,
    EnvironmentCapability,
    EnvironmentType,
    build_environment_from_tmux_pane,
    gui_success_requires_confirmation,
    is_interactive_session_gui_safe,
    is_ssh_service_gui_safe,
)


class TestEnvironmentModel:
    def test_tmux_pane_is_an_environment(self) -> None:
        env = build_environment_from_tmux_pane(
            session_name="test",
            window_index="0",
            pane_index="0",
            current_command="bash",
            current_path="/home/user",
        )
        assert env.environment_type == EnvironmentType.TMUX_PANE

    def test_shell_pane_has_shell_execution(self) -> None:
        env = build_environment_from_tmux_pane(
            session_name="test",
            window_index="0",
            pane_index="0",
            current_command="bash",
            current_path="/home/user",
        )
        assert EnvironmentCapability.SHELL_EXECUTION in env.capabilities

    def test_ssh_service_binding_not_gui_safe(self) -> None:
        assert is_ssh_service_gui_safe() is False

    def test_interactive_session_gui_safe_after_confirmation(self) -> None:
        assert is_interactive_session_gui_safe(confirmed=False) is False
        assert is_interactive_session_gui_safe(confirmed=True) is True

    def test_gui_success_requires_confirmation(self) -> None:
        assert gui_success_requires_confirmation() is True

    def test_shell_pane_is_available(self) -> None:
        env = build_environment_from_tmux_pane(
            session_name="work",
            window_index="0",
            pane_index="0",
            current_command="bash",
            current_path="/home/user",
        )
        assert env.is_available is True

    def test_busy_pane_not_available(self) -> None:
        env = build_environment_from_tmux_pane(
            session_name="work",
            window_index="0",
            pane_index="0",
            current_command="python3",
            current_path="/home/user",
        )
        assert env.is_available is False

    def test_environment_binding_is_interactive(self) -> None:
        env = build_environment_from_tmux_pane(
            session_name="test",
            window_index="0",
            pane_index="0",
            current_command="bash",
            current_path="/home/user",
        )
        assert env.binding == EnvironmentBinding.INTERACTIVE_USER_SESSION

    def test_gui_not_confirmed_by_default(self) -> None:
        env = build_environment_from_tmux_pane(
            session_name="test",
            window_index="0",
            pane_index="0",
            current_command="bash",
            current_path="/home/user",
        )
        assert env.is_safe_for_gui is False
        assert env.gui_confirmed_by_founder is False
