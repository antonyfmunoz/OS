"""Tmux execution surface for the Environment Bridge.

Models tmux as a persistent local execution environment. Builds
commands and policies without executing them. Dangerous commands
are blocked at the model layer.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

_DEFAULT_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"


class TmuxSurfaceStatus(str, Enum):
    AVAILABLE = "available"
    SESSION_MISSING = "session_missing"
    TMUX_NOT_INSTALLED = "tmux_not_installed"
    COMMAND_BLOCKED = "command_blocked"
    UNKNOWN = "unknown"


DANGEROUS_COMMANDS = frozenset(
    {
        "rm -rf /",
        "rm -rf ~",
        "rm -rf /*",
        "mkfs",
        "dd if=/dev/zero",
        ":(){:|:&};:",
        "chmod -R 777 /",
        "shutdown",
        "reboot",
        "halt",
        "poweroff",
        "init 0",
        "init 6",
    }
)

DANGEROUS_PREFIXES = (
    "rm -rf /",
    "mkfs ",
    "dd if=/dev/zero",
    "chmod -R 777 /",
    "curl | bash",
    "wget | bash",
    "curl | sh",
    "wget | sh",
)


@dataclass
class TmuxSurface:
    host: str = ""
    session_name: str = "eos-worker"
    window_name: str = "main"
    working_directory: str = ""
    allowed_commands: list[str] = field(default_factory=list)
    blocked_commands: list[str] = field(default_factory=list)
    status: TmuxSurfaceStatus = TmuxSurfaceStatus.UNKNOWN
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "session_name": self.session_name,
            "window_name": self.window_name,
            "working_directory": self.working_directory,
            "allowed_commands": self.allowed_commands,
            "blocked_commands": self.blocked_commands,
            "status": self.status.value,
            "notes": self.notes,
        }


def build_tmux_surface(
    host: str = "DESKTOP-LVGUIQ9",
    session_name: str = "eos-worker",
    window_name: str = "main",
    working_directory: str = _DEFAULT_ROOT,
    allowed_commands: list[str] | None = None,
    blocked_commands: list[str] | None = None,
) -> TmuxSurface:
    return TmuxSurface(
        host=host,
        session_name=session_name,
        window_name=window_name,
        working_directory=working_directory,
        allowed_commands=allowed_commands
        or [
            "python3",
            "pip",
            "git",
            "ls",
            "cat",
            "echo",
            "mkdir",
            "cp",
        ],
        blocked_commands=blocked_commands or list(DANGEROUS_COMMANDS),
        status=TmuxSurfaceStatus.AVAILABLE,
    )


def tmux_command_is_allowed(surface: TmuxSurface, command: str) -> bool:
    cmd_lower = command.strip().lower()
    if cmd_lower in {c.lower() for c in surface.blocked_commands}:
        return False
    for prefix in DANGEROUS_PREFIXES:
        if cmd_lower.startswith(prefix.lower()):
            return False
    return True


def build_tmux_send_command(surface: TmuxSurface, command: str) -> str:
    session = surface.session_name
    window = surface.window_name
    safe_cmd = command.replace("'", "'\\''")
    return f"tmux send-keys -t {session}:{window} '{safe_cmd}' Enter"


def tmux_surface_blocks_command(surface: TmuxSurface, command: str) -> bool:
    return not tmux_command_is_allowed(surface, command)


def summarize_tmux_surface(surface: TmuxSurface) -> dict[str, Any]:
    return {
        "host": surface.host,
        "session_name": surface.session_name,
        "status": surface.status.value,
        "allowed_command_count": len(surface.allowed_commands),
        "blocked_command_count": len(surface.blocked_commands),
    }
