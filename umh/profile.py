"""Profile + preferences wrapper — wraps substrate WorkstationStateManager."""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


@dataclass
class WorkstationPreferences:
    voice_mode: str = "text-only"
    webcam_enabled: bool = False
    default_profile: str = "developer"
    notification_level: str = "normal"
    auto_overnight_hour: int = 23
    auto_morning_hour: int = 7
    wake_phrase: str = ""
    personality_preset: str = "operator"


class ProfileManager:
    def __init__(self) -> None:
        self._manager: Any = None
        self._profile: Any = None
        self._snapshot: Any = None
        self._preferences = WorkstationPreferences()

    def _ensure_manager(self) -> Any:
        if self._manager is None:
            try:
                from substrate.workstation.state import WorkstationStateManager

                self._manager = WorkstationStateManager()
            except ImportError:
                logger.debug("WorkstationStateManager not available")
        return self._manager

    def has_snapshot(self) -> bool:
        mgr = self._ensure_manager()
        if mgr is None:
            return False
        snapshot = mgr.load_snapshot()
        return snapshot is not None

    def load_snapshot(self) -> Any:
        mgr = self._ensure_manager()
        if mgr is None:
            return None
        self._snapshot = mgr.load_snapshot()
        return self._snapshot

    def detect_profile(self) -> Any:
        try:
            from substrate.workstation.state import WorkstationProfile

            self._profile = WorkstationProfile.detect()
            return self._profile
        except (ImportError, Exception) as exc:
            logger.debug("Profile detection failed: %s", exc)
            return None

    def save_snapshot(self, profile: Any, session: Any) -> None:
        mgr = self._ensure_manager()
        if mgr is None:
            return
        try:
            snapshot = mgr.build_snapshot(profile, session)
            mgr.save_snapshot(snapshot)
        except Exception as exc:
            logger.debug("Snapshot save failed: %s", exc)

    @property
    def preferences(self) -> WorkstationPreferences:
        return self._preferences

    @property
    def resume_summary(self) -> str:
        if self._snapshot and hasattr(self._snapshot, "resume"):
            return self._snapshot.resume.resume_summary
        return "No previous session"

    @property
    def next_actions(self) -> list[str]:
        if self._snapshot and hasattr(self._snapshot, "resume"):
            return self._snapshot.resume.next_suggested_actions
        return []


def show_settings() -> int:
    pm = ProfileManager()
    prefs = pm.preferences
    print()
    print("╔══════════════════════════════════════╗")
    print("║  UMH Workstation Settings            ║")
    print("╠══════════════════════════════════════╣")
    print(f"║  Voice mode:     {prefs.voice_mode:<20s}║")
    print(f"║  Webcam:         {'enabled' if prefs.webcam_enabled else 'disabled':<20s}║")
    print(f"║  Default mode:   {prefs.default_profile:<20s}║")
    print(f"║  Notifications:  {prefs.notification_level:<20s}║")
    print(f"║  Overnight at:   {prefs.auto_overnight_hour:02d}:00{' ' * 15}║")
    print(f"║  Morning at:     {prefs.auto_morning_hour:02d}:00{' ' * 15}║")
    print(f"║  Wake phrase:    {prefs.wake_phrase or '(not set)':<20s}║")
    print(f"║  Personality:    {prefs.personality_preset:<20s}║")
    print("╚══════════════════════════════════════╝")
    print()
    return 0
