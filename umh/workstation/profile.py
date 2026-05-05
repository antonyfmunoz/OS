"""Workstation profile — models the operator's working environment.

A WorkstationProfile captures what capabilities are available in the
current environment (shell, browser, filesystem, display). BootSequence
defines what happens at startup. WorkMode selects operational constraints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.environments.detector import EnvironmentInfo, detect_environment


class WorkMode(str, Enum):
    FULL = "full"
    HEADLESS = "headless"
    RESTRICTED = "restricted"
    READONLY = "readonly"


@dataclass
class BootSequence:
    """Ordered steps to run at workstation initialization."""

    steps: list[str] = field(default_factory=list)
    completed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    @property
    def all_done(self) -> bool:
        return len(self.completed) + len(self.failed) == len(self.steps)

    @property
    def success(self) -> bool:
        return self.all_done and len(self.failed) == 0

    def mark_completed(self, step: str) -> None:
        if step in self.steps and step not in self.completed:
            self.completed.append(step)

    def mark_failed(self, step: str) -> None:
        if step in self.steps and step not in self.failed:
            self.failed.append(step)


@dataclass
class WorkstationProfile:
    """Describes the current workstation's capabilities and mode."""

    environment: EnvironmentInfo
    work_mode: WorkMode
    capabilities: dict[str, bool] = field(default_factory=dict)
    boot_sequence: BootSequence = field(default_factory=BootSequence)
    metadata: dict[str, Any] = field(default_factory=dict)

    def has_capability(self, name: str) -> bool:
        return self.capabilities.get(name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "environment": self.environment.to_dict(),
            "work_mode": self.work_mode.value,
            "capabilities": self.capabilities,
            "boot_completed": self.boot_sequence.all_done,
        }


def detect_workstation() -> WorkstationProfile:
    """Build a WorkstationProfile from the current environment."""
    env = detect_environment()

    if env.in_ci:
        mode = WorkMode.RESTRICTED
    elif not env.has_display:
        mode = WorkMode.HEADLESS
    else:
        mode = WorkMode.FULL

    capabilities = {
        "shell": True,
        "filesystem": True,
        "browser": env.has_display and not env.in_ci,
        "display": env.has_display,
        "docker": env.in_docker,
    }

    return WorkstationProfile(
        environment=env,
        work_mode=mode,
        capabilities=capabilities,
    )
