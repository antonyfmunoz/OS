"""
Environment contracts for Phase 94D.8.

Defines the environment model: nodes contain environments, environments
host workers, workers execute capabilities.

Core doctrine:
- Shells, tmux sessions, containers, browser profiles are all environments.
- The system manages them as part of the organism.
- GUI-visible execution requires an environment bound to the interactive
  user session, not just any execution context.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EnvironmentType(Enum):
    SSH_SESSION = "SSH_SESSION"
    WSL_SHELL = "WSL_SHELL"
    TMUX_SESSION = "TMUX_SESSION"
    TMUX_PANE = "TMUX_PANE"
    WINDOWS_DESKTOP_SESSION = "WINDOWS_DESKTOP_SESSION"
    PYTHON_VENV = "PYTHON_VENV"
    DOCKER_CONTAINER = "DOCKER_CONTAINER"
    BROWSER_PROFILE = "BROWSER_PROFILE"
    LOCAL_DAEMON = "LOCAL_DAEMON"


class EnvironmentCapability(Enum):
    SHELL_EXECUTION = "SHELL_EXECUTION"
    FILE_ACCESS = "FILE_ACCESS"
    GUI_LAUNCH = "GUI_LAUNCH"
    GUI_OBSERVATION = "GUI_OBSERVATION"
    BROWSER_VISIBLE_LAUNCH = "BROWSER_VISIBLE_LAUNCH"
    BROWSER_CONTROL = "BROWSER_CONTROL"
    COMPUTER_USE = "COMPUTER_USE"
    LONG_RUNNING_WORKER = "LONG_RUNNING_WORKER"
    ADVISOR_RELAY = "ADVISOR_RELAY"


class EnvironmentBinding(Enum):
    HEADLESS = "HEADLESS"
    SSH_SERVICE = "SSH_SERVICE"
    INTERACTIVE_USER_SESSION = "INTERACTIVE_USER_SESSION"
    UNKNOWN = "UNKNOWN"


@dataclass
class EnvironmentProfile:
    """Profile of a single environment within a node."""

    environment_id: str
    node_id: str
    environment_type: EnvironmentType
    binding: EnvironmentBinding
    capabilities: list[EnvironmentCapability] = field(default_factory=list)
    session_name: str = ""
    pane_id: str = ""
    current_command: str = ""
    current_path: str = ""
    is_available: bool = True
    is_safe_for_gui: bool = False
    gui_confirmed_by_founder: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "environment_id": self.environment_id,
            "node_id": self.node_id,
            "environment_type": self.environment_type.value,
            "binding": self.binding.value,
            "capabilities": [c.value for c in self.capabilities],
            "session_name": self.session_name,
            "pane_id": self.pane_id,
            "current_command": self.current_command,
            "current_path": self.current_path,
            "is_available": self.is_available,
            "is_safe_for_gui": self.is_safe_for_gui,
            "gui_confirmed_by_founder": self.gui_confirmed_by_founder,
            "notes": self.notes,
        }


def is_ssh_service_gui_safe() -> bool:
    """SSH service binding is NOT automatically safe for visible GUI."""
    return False


def is_interactive_session_gui_safe(confirmed: bool = False) -> bool:
    """Interactive user session CAN be GUI-safe after founder confirms."""
    return confirmed


def gui_success_requires_confirmation() -> bool:
    """Visible GUI success always requires founder confirmation or observation backend."""
    return True


def build_environment_from_tmux_pane(
    session_name: str,
    window_index: str,
    pane_index: str,
    current_command: str,
    current_path: str,
    node_id: str = "local_pc",
) -> EnvironmentProfile:
    """Build an EnvironmentProfile from a tmux pane."""
    pane_id = f"{session_name}:{window_index}.{pane_index}"
    env_id = f"tmux_{pane_id}"

    capabilities = [EnvironmentCapability.SHELL_EXECUTION, EnvironmentCapability.FILE_ACCESS]

    shell_commands = {"bash", "zsh", "sh", "fish", "pwsh", "powershell"}
    is_shell = current_command.lower() in shell_commands

    if is_shell:
        capabilities.append(EnvironmentCapability.LONG_RUNNING_WORKER)

    return EnvironmentProfile(
        environment_id=env_id,
        node_id=node_id,
        environment_type=EnvironmentType.TMUX_PANE,
        binding=EnvironmentBinding.INTERACTIVE_USER_SESSION,
        capabilities=capabilities,
        session_name=session_name,
        pane_id=pane_id,
        current_command=current_command,
        current_path=current_path,
        is_available=is_shell,
        is_safe_for_gui=False,
        gui_confirmed_by_founder=False,
        notes="GUI safety unverified until founder confirms visible launch",
    )
