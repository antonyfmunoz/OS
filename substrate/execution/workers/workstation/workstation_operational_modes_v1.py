"""Workstation Operational Modes v1.

Defines operational modes that constrain what the workstation can do.
Each mode specifies allowed commands, execution boundaries, governance
thresholds, continuity expectations, and adapter access.

Modes:
  developer_mode      — full safe command access, governed shell + tmux
  research_mode       — read-only inspection, no mutations
  audit_mode          — logging-only, no execution
  overnight_safe_mode — minimal safe operations, heightened governance

UMH substrate subsystem.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .workstation_contracts_v1 import OperationalMode


@dataclass
class ModeDefinition:
    """Complete definition of an operational mode."""

    mode: OperationalMode
    display_name: str
    description: str
    allowed_shell_commands: frozenset[str] = field(default_factory=frozenset)
    allowed_tmux_operations: frozenset[str] = field(default_factory=frozenset)
    allowed_adapters: frozenset[str] = field(default_factory=frozenset)
    max_command_timeout: int = 30
    allow_filesystem_write: bool = False
    allow_service_restart: bool = False
    allow_git_operations: bool = False
    governance_threshold: str = "standard"
    require_explicit_approval_above: str = "medium"

    def allows_command(self, command_prefix: str) -> bool:
        return command_prefix in self.allowed_shell_commands

    def allows_tmux(self, operation: str) -> bool:
        return operation in self.allowed_tmux_operations

    def allows_adapter(self, adapter_type: str) -> bool:
        return adapter_type in self.allowed_adapters

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "display_name": self.display_name,
            "description": self.description,
            "allowed_shell_commands": sorted(self.allowed_shell_commands),
            "allowed_tmux_operations": sorted(self.allowed_tmux_operations),
            "allowed_adapters": sorted(self.allowed_adapters),
            "max_command_timeout": self.max_command_timeout,
            "allow_filesystem_write": self.allow_filesystem_write,
            "allow_service_restart": self.allow_service_restart,
            "allow_git_operations": self.allow_git_operations,
            "governance_threshold": self.governance_threshold,
            "require_explicit_approval_above": self.require_explicit_approval_above,
        }


# ---------------------------------------------------------------------------
# Shell command prefixes allowed per mode
# ---------------------------------------------------------------------------

_INSPECTION_COMMANDS = frozenset(
    {
        "pwd",
        "ls",
        "find",
        "cat",
        "head",
        "tail",
        "wc",
        "grep",
        "which",
        "whoami",
        "hostname",
        "uname",
        "uptime",
        "df",
        "free",
        "ps",
        "docker",
        "date",
        "env",
        "echo",
        "file",
        "stat",
    }
)

_GIT_COMMANDS = frozenset(
    {
        "git status",
        "git diff",
        "git log",
        "git branch",
        "git show",
        "git rev-parse",
        "git remote",
        "git stash list",
        "git tag",
    }
)

_TEST_COMMANDS = frozenset(
    {
        "pytest",
        "python3 -m pytest",
        "python3 -m py_compile",
        "python3 -c",
        "ruff check",
        "ruff format --check",
    }
)

_DEVELOPER_COMMANDS = _INSPECTION_COMMANDS | _GIT_COMMANDS | _TEST_COMMANDS | frozenset(
    {
        "ruff format",
        "tmux",
    }
)

_TMUX_INSPECT = frozenset({"list-sessions", "list-panes", "list-windows", "display-message", "show-options"})
_TMUX_CONTROLLED = _TMUX_INSPECT | frozenset({"send-keys", "new-session", "new-window"})

# ---------------------------------------------------------------------------
# Mode definitions
# ---------------------------------------------------------------------------

DEVELOPER_MODE = ModeDefinition(
    mode=OperationalMode.DEVELOPER,
    display_name="Developer Mode",
    description="Full safe command access with governed shell and tmux",
    allowed_shell_commands=_DEVELOPER_COMMANDS,
    allowed_tmux_operations=_TMUX_CONTROLLED,
    allowed_adapters=frozenset({"shell", "tmux", "filesystem"}),
    max_command_timeout=60,
    allow_filesystem_write=False,
    allow_service_restart=False,
    allow_git_operations=True,
    governance_threshold="standard",
    require_explicit_approval_above="medium",
)

RESEARCH_MODE = ModeDefinition(
    mode=OperationalMode.RESEARCH,
    display_name="Research Mode",
    description="Read-only inspection, no mutations",
    allowed_shell_commands=_INSPECTION_COMMANDS | _GIT_COMMANDS,
    allowed_tmux_operations=_TMUX_INSPECT,
    allowed_adapters=frozenset({"shell", "tmux"}),
    max_command_timeout=30,
    allow_filesystem_write=False,
    allow_service_restart=False,
    allow_git_operations=False,
    governance_threshold="strict",
    require_explicit_approval_above="low",
)

AUDIT_MODE = ModeDefinition(
    mode=OperationalMode.AUDIT,
    display_name="Audit Mode",
    description="Logging-only observation, no execution",
    allowed_shell_commands=frozenset({"pwd", "whoami", "hostname", "date", "uptime"}),
    allowed_tmux_operations=frozenset({"list-sessions"}),
    allowed_adapters=frozenset(),
    max_command_timeout=10,
    allow_filesystem_write=False,
    allow_service_restart=False,
    allow_git_operations=False,
    governance_threshold="maximum",
    require_explicit_approval_above="safe",
)

OVERNIGHT_SAFE_MODE = ModeDefinition(
    mode=OperationalMode.OVERNIGHT_SAFE,
    display_name="Overnight Safe Mode",
    description="Minimal safe operations with heightened governance",
    allowed_shell_commands=_INSPECTION_COMMANDS | frozenset({"docker"}),
    allowed_tmux_operations=_TMUX_INSPECT,
    allowed_adapters=frozenset({"shell"}),
    max_command_timeout=15,
    allow_filesystem_write=False,
    allow_service_restart=False,
    allow_git_operations=False,
    governance_threshold="strict",
    require_explicit_approval_above="safe",
)

MODE_REGISTRY: dict[OperationalMode, ModeDefinition] = {
    OperationalMode.DEVELOPER: DEVELOPER_MODE,
    OperationalMode.RESEARCH: RESEARCH_MODE,
    OperationalMode.AUDIT: AUDIT_MODE,
    OperationalMode.OVERNIGHT_SAFE: OVERNIGHT_SAFE_MODE,
}


def get_mode_definition(mode: OperationalMode) -> ModeDefinition:
    return MODE_REGISTRY[mode]


def get_all_modes() -> list[ModeDefinition]:
    return list(MODE_REGISTRY.values())
