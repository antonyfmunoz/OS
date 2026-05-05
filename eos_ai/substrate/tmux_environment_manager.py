"""
Tmux environment manager for Phase 94D.8.

Manages tmux sessions/panes as environments within the UMH organism.
Provides pane discovery, classification, selection, and command dispatch.

Key rules:
- Never send commands into Claude sessions.
- Never send commands into Python worker loops or bridge sessions.
- Only dispatch to confirmed shell panes (bash, zsh, sh, fish, pwsh).
- GUI-visible launch via tmux is unverified until founder confirms.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from eos_ai.substrate.environment_contracts import (
    EnvironmentBinding,
    EnvironmentCapability,
    EnvironmentProfile,
    EnvironmentType,
    build_environment_from_tmux_pane,
)


SSH_KEY = "/root/.ssh/id_ed25519"
SSH_USER = r"DESKTOP-LVGUIQ9\antonys beast pc"
SSH_HOST = "100.74.199.102"

SHELL_COMMANDS: frozenset[str] = frozenset({"bash", "zsh", "sh", "fish", "pwsh", "powershell"})

BUSY_COMMANDS: frozenset[str] = frozenset(
    {
        "claude",
        "python",
        "python3",
        "node",
        "npm",
        "vim",
        "nvim",
        "nano",
        "ssh",
        "tmux",
        "less",
        "man",
        "top",
        "htop",
    }
)


@dataclass
class TmuxPane:
    """Parsed representation of a tmux pane."""

    session_name: str
    window_index: str
    pane_index: str
    current_command: str
    current_path: str

    @property
    def target(self) -> str:
        return f"{self.session_name}:{self.window_index}.{self.pane_index}"


def parse_tmux_list_panes_output(output: str) -> list[TmuxPane]:
    """Parse output from tmux list-panes -a with custom format.

    Expected format per line:
    session_name:window_index.pane_index | cmd=command | path=/some/path
    """
    panes: list[TmuxPane] = []
    for line in output.strip().splitlines():
        line = line.strip()
        if not line or "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2:
            continue

        target_part = parts[0]
        cmd_part = ""
        path_part = ""

        for part in parts[1:]:
            if part.startswith("cmd="):
                cmd_part = part[4:]
            elif part.startswith("path="):
                path_part = part[5:]

        if ":" not in target_part or "." not in target_part:
            continue

        session_window, pane_idx = target_part.rsplit(".", 1)
        session_name, window_idx = session_window.split(":", 1)

        panes.append(
            TmuxPane(
                session_name=session_name,
                window_index=window_idx,
                pane_index=pane_idx,
                current_command=cmd_part,
                current_path=path_part,
            )
        )
    return panes


def classify_tmux_pane(pane: TmuxPane) -> str:
    """Classify a tmux pane: 'shell', 'busy', or 'unknown'."""
    cmd = pane.current_command.lower().split("/")[-1]
    if cmd in SHELL_COMMANDS:
        return "shell"
    if cmd in BUSY_COMMANDS:
        return "busy"
    return "unknown"


def is_shell_pane(pane: TmuxPane) -> bool:
    """Check if pane is running a shell (safe to send commands to)."""
    return classify_tmux_pane(pane) == "shell"


def is_busy_pane(pane: TmuxPane) -> bool:
    """Check if pane is busy (do NOT send commands)."""
    return classify_tmux_pane(pane) == "busy"


def choose_best_shell_pane(panes: list[TmuxPane]) -> TmuxPane | None:
    """Choose the best shell pane for command dispatch.

    Prefers:
    1. Panes with 'gui' or 'shell' in session name
    2. Regular shell panes
    Avoids all busy and unknown panes.
    """
    shell_panes = [p for p in panes if is_shell_pane(p)]
    if not shell_panes:
        return None

    for pane in shell_panes:
        name_lower = pane.session_name.lower()
        if "gui" in name_lower or "shell" in name_lower:
            return pane

    return shell_panes[0]


def build_tmux_list_panes_command() -> str:
    """Build the SSH command to list all tmux panes on the local PC."""
    format_str = '#{session_name}:#{window_index}.#{pane_index} | cmd=#{pane_current_command} | path=#{pane_current_path}'
    return (
        f"ssh -i {SSH_KEY} -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=8 "
        f"'{SSH_USER}'@{SSH_HOST} "
        f"'wsl -e bash -lc \"tmux list-panes -a -F \\\"{format_str}\\\"\"'"
    )


def build_tmux_send_keys_command(target: str, command: str) -> str:
    """Build the SSH command to send keys into a specific tmux pane.

    target: session:window.pane format (e.g., 'my_session:0.0')
    command: the shell command to execute
    """
    return (
        f"ssh -i {SSH_KEY} -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=8 "
        f"'{SSH_USER}'@{SSH_HOST} "
        f"'wsl -e bash -lc \"tmux send-keys -t {target} \\\"{command}\\\" Enter\"'"
    )


def build_tmux_new_shell_session_command(session_name: str = "umh_gui_shell") -> str:
    """Build SSH command to create a new tmux shell session."""
    return (
        f"ssh -i {SSH_KEY} -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=8 "
        f"'{SSH_USER}'@{SSH_HOST} "
        f"'wsl -e bash -lc \"tmux new-session -d -s {session_name}\"'"
    )


def build_tmux_capture_pane_command(target: str) -> str:
    """Build SSH command to capture output of a tmux pane."""
    return (
        f"ssh -i {SSH_KEY} -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=8 "
        f"'{SSH_USER}'@{SSH_HOST} "
        f"'wsl -e bash -lc \"tmux capture-pane -t {target} -p\"'"
    )


def panes_to_environment_profiles(panes: list[TmuxPane], node_id: str = "local_pc") -> list[EnvironmentProfile]:
    """Convert parsed tmux panes to EnvironmentProfile objects."""
    return [
        build_environment_from_tmux_pane(
            session_name=p.session_name,
            window_index=p.window_index,
            pane_index=p.pane_index,
            current_command=p.current_command,
            current_path=p.current_path,
            node_id=node_id,
        )
        for p in panes
    ]
