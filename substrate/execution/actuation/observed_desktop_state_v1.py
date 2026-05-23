"""Observed Desktop State v1.

Captures the REAL observed state of the Windows desktop at actuation
time. Every field must come from actual observation — never from
intended or simulated state.

Composes with the existing ObservedDesktopState in
windows_foreground_actuator_v1.py but adds maturity-aware
classification and proof evidence extraction.

UMH substrate subsystem. Phase 96.8AN.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .actuator_maturity_v1 import (
    ActuatorMaturityLevel,
    compute_maturity_level,
    maturity_ceiling,
)


@dataclass
class ObservedDesktopStateV1:
    """Observed state of the Windows desktop with maturity classification."""

    chrome_pid: int = 0
    window_handle: int = 0
    window_title: str = ""
    visible: bool = False
    focused: bool = False
    monitor_detected: bool = False
    desktop_unlocked: bool = False
    active_user_session: bool = False
    navigation_url: str = ""
    navigation_detected: bool = False
    screenshot_path: str = ""
    screenshot_hash: str = ""
    founder_confirmed: bool = False
    replay_hash: str = ""
    backend_used: str = ""
    is_dry_run: bool = False
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    @property
    def evidence(self) -> dict[str, Any]:
        return {
            "chrome_pid": self.chrome_pid,
            "window_handle": self.window_handle,
            "focused": self.focused,
            "navigation_detected": self.navigation_detected,
            "screenshot_path": self.screenshot_path,
            "founder_confirmed": self.founder_confirmed,
            "replay_hash": self.replay_hash,
        }

    @property
    def maturity_level(self) -> ActuatorMaturityLevel:
        if self.is_dry_run:
            return ActuatorMaturityLevel.L0_SIMULATED
        ceiling = maturity_ceiling(
            has_window_handle=self.window_handle != 0,
            has_screenshot=bool(self.screenshot_path),
            has_founder_confirmation=self.founder_confirmed,
        )
        computed = compute_maturity_level(self.evidence)
        return min(computed, ceiling)

    @property
    def maturity_label(self) -> str:
        from .actuator_maturity_v1 import MATURITY_LABELS

        return MATURITY_LABELS[self.maturity_level]

    def to_dict(self) -> dict[str, Any]:
        return {
            "chrome_pid": self.chrome_pid,
            "window_handle": self.window_handle,
            "window_title": self.window_title,
            "visible": self.visible,
            "focused": self.focused,
            "monitor_detected": self.monitor_detected,
            "desktop_unlocked": self.desktop_unlocked,
            "active_user_session": self.active_user_session,
            "navigation_url": self.navigation_url,
            "navigation_detected": self.navigation_detected,
            "screenshot_path": self.screenshot_path,
            "screenshot_hash": self.screenshot_hash,
            "founder_confirmed": self.founder_confirmed,
            "replay_hash": self.replay_hash,
            "backend_used": self.backend_used,
            "is_dry_run": self.is_dry_run,
            "maturity_level": self.maturity_level.value,
            "maturity_label": self.maturity_label,
            "timestamp": self.timestamp,
        }


def from_relay_result(
    relay_result: dict[str, Any],
    backend: str = "windows_interactive_desktop_relay",
) -> ObservedDesktopStateV1:
    """Parse a PowerShell relay result into an ObservedDesktopStateV1."""
    obs = relay_result.get("observed_desktop_state", {})
    window_meta = relay_result.get("window_metadata", {})
    is_dry = relay_result.get("dry_run", False)

    return ObservedDesktopStateV1(
        chrome_pid=obs.get("chrome_pid", relay_result.get("process_id", 0)),
        window_handle=obs.get("window_handle", window_meta.get("main_window_handle", 0)),
        window_title=obs.get("window_title", window_meta.get("main_window_title", "")),
        visible=obs.get("visible", relay_result.get("process_detected", False)),
        focused=obs.get("focused", False),
        monitor_detected=obs.get("monitor_detected", False),
        desktop_unlocked=obs.get("desktop_unlocked", False),
        active_user_session=obs.get("active_user_session", False),
        navigation_url=obs.get("navigation_url", ""),
        navigation_detected=obs.get("navigation_detected", False),
        screenshot_path=obs.get("screenshot_path", relay_result.get("screenshot_path", "")),
        screenshot_hash=obs.get("screenshot_hash", relay_result.get("screenshot_hash", "")),
        founder_confirmed=False,
        backend_used=backend,
        is_dry_run=is_dry,
    )
