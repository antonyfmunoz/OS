"""Profile + preferences wrapper — wraps substrate WorkstationStateManager."""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import asdict, dataclass
from typing import Any

logger = logging.getLogger(__name__)

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

UMH_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
PREFERENCES_FILE = os.path.join(UMH_ROOT, "data", "sessions", "preferences.json")


@dataclass
class WorkstationPreferences:
    voice_mode: str = "text_only"
    webcam_enabled: bool = False
    default_profile: str = "developer"
    notification_level: str = "normal"
    auto_overnight_hour: int = 23
    auto_morning_hour: int = 7
    wake_phrase: str = ""
    personality_preset: str = "operator"
    auto_away_minutes: int = 5
    maintenance_window_start: int = 3
    maintenance_window_end: int = 4
    mode_stacking_enabled: bool = True
    voice_clone_attempted: bool = False
    custom_boot_sequence: list[str] | None = None


class ProfileManager:
    def __init__(self) -> None:
        self._manager: Any = None
        self._profile: Any = None
        self._snapshot: Any = None
        self._preferences: WorkstationPreferences | None = None

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
            # Check for onboarding result as fallback
            onboarding_path = os.path.join(UMH_ROOT, "data", "onboarding", "onboarding_result.json")
            return os.path.exists(onboarding_path)
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

    def get_preferences(self) -> WorkstationPreferences:
        """Load preferences from disk or return defaults."""
        if self._preferences is not None:
            return self._preferences

        self._preferences = WorkstationPreferences()

        if os.path.exists(PREFERENCES_FILE):
            try:
                with open(PREFERENCES_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                for key, value in data.items():
                    if hasattr(self._preferences, key):
                        setattr(self._preferences, key, value)
            except Exception as exc:
                logger.debug("Failed to load preferences: %s", exc)

        return self._preferences

    def save_preferences(self, prefs: WorkstationPreferences) -> None:
        """Save preferences to disk."""
        self._preferences = prefs
        os.makedirs(os.path.dirname(PREFERENCES_FILE), exist_ok=True)
        try:
            with open(PREFERENCES_FILE, "w", encoding="utf-8") as f:
                json.dump(asdict(prefs), f, indent=2)
        except Exception as exc:
            logger.debug("Failed to save preferences: %s", exc)

    @property
    def preferences(self) -> WorkstationPreferences:
        return self.get_preferences()

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
    prefs = pm.get_preferences()
    print()
    print("=" * 48)
    print("  UMH Workstation Settings")
    print("=" * 48)
    print(f"  Voice mode:       {prefs.voice_mode.replace('_', '-')}")
    print(f"  Webcam:           {'enabled' if prefs.webcam_enabled else 'disabled'}")
    print(f"  Default mode:     {prefs.default_profile}")
    print(f"  Notifications:    {prefs.notification_level}")
    print(f"  Overnight at:     {prefs.auto_overnight_hour:02d}:00")
    print(f"  Morning at:       {prefs.auto_morning_hour:02d}:00")
    print(f"  Wake phrase:      {prefs.wake_phrase or '(not set)'}")
    print(f"  Personality:      {prefs.personality_preset}")
    print(f"  Auto-away:        {prefs.auto_away_minutes} min")
    print(
        f"  Maintenance:      {prefs.maintenance_window_start:02d}:00-{prefs.maintenance_window_end:02d}:00"
    )
    print(f"  Mode stacking:    {'enabled' if prefs.mode_stacking_enabled else 'disabled'}")
    if prefs.custom_boot_sequence:
        print(f"  Custom boot:      {', '.join(prefs.custom_boot_sequence)}")

    try:
        from umh.personality import load_personality

        config = load_personality()
        traits = config.traits
        print()
        print("  Personality Details:")
        print(f"    Tone:           {traits.tone}")
        print(f"    Style:          {traits.style}")
        print(f"    Governance:     {traits.governance.value}")
        print(f"    Proactivity:    {traits.proactivity.value}")
        if config.is_multi_mode:
            for mode, preset in config.mode_overrides.items():
                print(f"    {mode}:  {preset}")
    except Exception as exc:
        logger.debug("Personality display failed: %s", exc)

    try:
        from substrate.sockets.sensing_port import sensing_summary

        summary = sensing_summary()
        if summary.get("total", 0) > 0:
            print()
            print(f"  Sensing adapters: {summary['total']} registered")
            for family in summary.get("families", []):
                print(f"    - {family}")
    except Exception as exc:
        logger.debug("Sensing summary failed: %s", exc)

    print("=" * 48)
    print()
    return 0
