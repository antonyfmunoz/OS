"""Tests for Phase 94D.8 — Tmux Environment Manager."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from eos_ai.substrate.tmux_environment_manager import (
    TmuxPane,
    build_tmux_list_panes_command,
    build_tmux_new_shell_session_command,
    build_tmux_send_keys_command,
    choose_best_shell_pane,
    classify_tmux_pane,
    is_busy_pane,
    is_shell_pane,
    parse_tmux_list_panes_output,
)

SAMPLE_OUTPUT = """\
main:0.0 | cmd=bash | path=/home/user
work:0.0 | cmd=claude | path=/opt/OS
dev:1.0 | cmd=python3 | path=/home/user/project
gui_shell:0.0 | cmd=zsh | path=/home/user
bridge:0.0 | cmd=node | path=/home/user/bridge
"""


class TestParsePanes:
    def test_parses_multiple_panes(self) -> None:
        panes = parse_tmux_list_panes_output(SAMPLE_OUTPUT)
        assert len(panes) == 5

    def test_extracts_session_name(self) -> None:
        panes = parse_tmux_list_panes_output(SAMPLE_OUTPUT)
        assert panes[0].session_name == "main"
        assert panes[1].session_name == "work"

    def test_extracts_command(self) -> None:
        panes = parse_tmux_list_panes_output(SAMPLE_OUTPUT)
        assert panes[0].current_command == "bash"
        assert panes[1].current_command == "claude"

    def test_extracts_path(self) -> None:
        panes = parse_tmux_list_panes_output(SAMPLE_OUTPUT)
        assert panes[0].current_path == "/home/user"

    def test_target_format(self) -> None:
        panes = parse_tmux_list_panes_output(SAMPLE_OUTPUT)
        assert panes[0].target == "main:0.0"
        assert panes[3].target == "gui_shell:0.0"


class TestClassifyPane:
    def test_bash_is_shell(self) -> None:
        pane = TmuxPane("s", "0", "0", "bash", "/")
        assert classify_tmux_pane(pane) == "shell"

    def test_zsh_is_shell(self) -> None:
        pane = TmuxPane("s", "0", "0", "zsh", "/")
        assert classify_tmux_pane(pane) == "shell"

    def test_claude_is_busy(self) -> None:
        pane = TmuxPane("s", "0", "0", "claude", "/")
        assert classify_tmux_pane(pane) == "busy"

    def test_python_is_busy(self) -> None:
        pane = TmuxPane("s", "0", "0", "python3", "/")
        assert classify_tmux_pane(pane) == "busy"

    def test_vim_is_busy(self) -> None:
        pane = TmuxPane("s", "0", "0", "vim", "/")
        assert classify_tmux_pane(pane) == "busy"

    def test_is_shell_pane_true(self) -> None:
        pane = TmuxPane("s", "0", "0", "bash", "/")
        assert is_shell_pane(pane) is True

    def test_is_busy_pane_true(self) -> None:
        pane = TmuxPane("s", "0", "0", "claude", "/")
        assert is_busy_pane(pane) is True


class TestChooseBestPane:
    def test_chooses_shell_pane(self) -> None:
        panes = parse_tmux_list_panes_output(SAMPLE_OUTPUT)
        best = choose_best_shell_pane(panes)
        assert best is not None
        assert is_shell_pane(best)

    def test_prefers_gui_named_session(self) -> None:
        panes = parse_tmux_list_panes_output(SAMPLE_OUTPUT)
        best = choose_best_shell_pane(panes)
        assert best is not None
        assert best.session_name == "gui_shell"

    def test_returns_none_if_no_shell(self) -> None:
        busy_output = "work:0.0 | cmd=claude | path=/opt/OS\ndev:0.0 | cmd=python3 | path=/home\n"
        panes = parse_tmux_list_panes_output(busy_output)
        best = choose_best_shell_pane(panes)
        assert best is None


class TestBuildCommands:
    def test_send_keys_targets_exact_pane(self) -> None:
        cmd = build_tmux_send_keys_command("main:0.0", "echo hello")
        assert "main:0.0" in cmd
        assert "send-keys" in cmd
        assert "echo hello" in cmd

    def test_new_session_command_names_session(self) -> None:
        cmd = build_tmux_new_shell_session_command("umh_gui_shell")
        assert "umh_gui_shell" in cmd
        assert "new-session" in cmd

    def test_list_panes_command_uses_ssh(self) -> None:
        cmd = build_tmux_list_panes_command()
        assert "ssh" in cmd
        assert "list-panes" in cmd
