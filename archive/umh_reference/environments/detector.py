"""Environment detector — classifies the current execution context.

Detects whether UMH is running locally, in Docker, in CI, on a
server, etc. Used by adapters and the workstation subsystem to
adjust behavior based on available capabilities.
"""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from enum import Enum


class EnvironmentType(str, Enum):
    LOCAL = "local"
    DOCKER = "docker"
    CI = "ci"
    SERVER = "server"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class EnvironmentInfo:
    """Detected environment characteristics."""

    environment_type: EnvironmentType
    platform: str
    python_version: str
    hostname: str
    in_docker: bool
    in_ci: bool
    has_display: bool

    def to_dict(self) -> dict[str, str | bool]:
        return {
            "environment_type": self.environment_type.value,
            "platform": self.platform,
            "python_version": self.python_version,
            "hostname": self.hostname,
            "in_docker": self.in_docker,
            "in_ci": self.in_ci,
            "has_display": self.has_display,
        }


def detect_environment() -> EnvironmentInfo:
    """Detect and classify the current execution environment."""
    in_docker = os.path.exists("/.dockerenv") or os.environ.get("container") == "docker"
    ci_vars = ("CI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL", "CIRCLECI")
    in_ci = any(os.environ.get(v) for v in ci_vars)
    has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

    if in_ci:
        env_type = EnvironmentType.CI
    elif in_docker:
        env_type = EnvironmentType.DOCKER
    elif has_display:
        env_type = EnvironmentType.LOCAL
    else:
        env_type = EnvironmentType.SERVER

    return EnvironmentInfo(
        environment_type=env_type,
        platform=platform.system(),
        python_version=platform.python_version(),
        hostname=platform.node(),
        in_docker=in_docker,
        in_ci=in_ci,
        has_display=has_display,
    )
