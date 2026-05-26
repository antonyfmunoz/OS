"""First Boot — detects whether the system needs onboarding.

Checks for the presence of onboarding result file and critical
configuration. If missing, the system is in "first boot" state
and should run the onboarding wizard before normal operation.

Environment detection is automatic — the system figures out
what hardware, OS, and services are available without asking.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_UMH_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or "/opt/OS"
_ONBOARDING_PATH = Path(_UMH_ROOT) / "data" / "onboarding" / "onboarding_result.json"
_FIRST_BOOT_MARKER = Path(_UMH_ROOT) / "data" / "umh" / ".first_boot_complete"


@dataclass
class EnvironmentProfile:
    """Auto-detected environment capabilities."""

    platform: str = ""
    hostname: str = ""
    has_docker: bool = False
    has_gpu: bool = False
    has_ollama: bool = False
    has_notion_token: bool = False
    has_anthropic_key: bool = False
    has_gemini_key: bool = False
    has_discord_token: bool = False
    has_telegram_token: bool = False
    python_version: str = ""
    detected_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class FirstBootStatus:
    """Status of the first-boot check."""

    needs_onboarding: bool = True
    needs_env_setup: bool = True
    onboarding_complete: bool = False
    environment: EnvironmentProfile | None = None
    missing_critical: list[str] = field(default_factory=list)
    missing_optional: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "needs_onboarding": self.needs_onboarding,
            "needs_env_setup": self.needs_env_setup,
            "onboarding_complete": self.onboarding_complete,
            "environment": self.environment.to_dict() if self.environment else None,
            "missing_critical": self.missing_critical,
            "missing_optional": self.missing_optional,
        }


def detect_environment() -> EnvironmentProfile:
    """Auto-detect environment capabilities."""
    import platform
    import shutil
    import sys

    profile = EnvironmentProfile(
        platform=platform.system(),
        hostname=platform.node(),
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        detected_at=datetime.now(timezone.utc).isoformat(),
    )

    profile.has_docker = shutil.which("docker") is not None
    profile.has_ollama = shutil.which("ollama") is not None
    profile.has_notion_token = bool(os.environ.get("NOTION_TOKEN"))
    profile.has_anthropic_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    profile.has_gemini_key = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    profile.has_discord_token = bool(os.environ.get("DISCORD_BOT_TOKEN"))
    profile.has_telegram_token = bool(os.environ.get("TELEGRAM_BOT_TOKEN"))

    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5,
        )
        profile.has_gpu = result.returncode == 0 and bool(result.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired):
        profile.has_gpu = False

    return profile


def check_first_boot() -> FirstBootStatus:
    """Check if the system needs first-boot setup."""
    status = FirstBootStatus()
    status.environment = detect_environment()

    if _ONBOARDING_PATH.exists():
        try:
            data = json.loads(_ONBOARDING_PATH.read_text())
            if data.get("operator_name"):
                status.onboarding_complete = True
                status.needs_onboarding = False
        except (json.JSONDecodeError, KeyError):
            pass

    if _FIRST_BOOT_MARKER.exists():
        status.needs_env_setup = False

    env = status.environment
    if not env.has_anthropic_key and not env.has_gemini_key:
        status.missing_critical.append("No LLM API key (ANTHROPIC_API_KEY or GEMINI_API_KEY)")
        status.needs_env_setup = True

    if not env.has_notion_token:
        status.missing_optional.append("NOTION_TOKEN — Notion integration disabled")
    if not env.has_discord_token:
        status.missing_optional.append("DISCORD_BOT_TOKEN — Discord channel disabled")
    if not env.has_docker:
        status.missing_optional.append("Docker not found — container execution disabled")
    if not env.has_ollama:
        status.missing_optional.append("Ollama not found — local inference disabled")

    return status


def mark_first_boot_complete() -> None:
    """Mark first boot as complete — won't prompt again."""
    _FIRST_BOOT_MARKER.parent.mkdir(parents=True, exist_ok=True)
    _FIRST_BOOT_MARKER.write_text(
        json.dumps({
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "environment": detect_environment().to_dict(),
        }, indent=2)
    )


def load_onboarding_result() -> dict[str, Any] | None:
    """Load saved onboarding result if it exists."""
    if not _ONBOARDING_PATH.exists():
        return None
    try:
        return json.loads(_ONBOARDING_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return None
