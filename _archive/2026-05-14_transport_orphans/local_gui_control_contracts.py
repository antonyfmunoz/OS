"""
Local GUI control contracts for Phase 95.0.

Defines the abstraction layer for computer-use-only operations:
observation methods, action types, and policies for interacting
with visible desktop UI elements.

This is the fallback path when APIs/connectors are unavailable.
The system uses only what a human would use: eyes and hands.

No API. No Playwright. No CDP. No token/cookie access.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class GUIObservationMethod(str, Enum):
    WINDOWS_UI_AUTOMATION = "windows_ui_automation"
    ACCESSIBILITY_TREE = "accessibility_tree"
    TEMPORARY_SCREEN_OBSERVATION = "temporary_screen_observation"
    OCR_LAST_RESORT = "ocr_last_resort"
    HUMAN_VISUAL_CONFIRMATION = "human_visual_confirmation"


class GUIActionType(str, Enum):
    MOVE_MOUSE = "move_mouse"
    CLICK = "click"
    TYPE_TEXT = "type_text"
    HOTKEY = "hotkey"
    SCROLL = "scroll"
    WAIT = "wait"
    OBSERVE = "observe"


class GUIControlStatus(str, Enum):
    AVAILABLE = "available"
    PARTIAL = "partial"
    MISSING = "missing"
    BLOCKED = "blocked"
    NEEDS_APPROVAL = "needs_approval"


OBSERVATION_METHOD_PRIORITY: list[GUIObservationMethod] = [
    GUIObservationMethod.WINDOWS_UI_AUTOMATION,
    GUIObservationMethod.ACCESSIBILITY_TREE,
    GUIObservationMethod.TEMPORARY_SCREEN_OBSERVATION,
    GUIObservationMethod.OCR_LAST_RESORT,
    GUIObservationMethod.HUMAN_VISUAL_CONFIRMATION,
]

BLOCKED_OBSERVATION_TARGETS: frozenset[str] = frozenset(
    {
        "credential_field",
        "password_field",
        "login_form",
        "cookie_store",
        "token_display",
        "gmail_inbox",
        "document_body",
        "document_content",
        "file_download",
        "export_dialog",
    }
)

ALLOWED_OBSERVATION_TARGETS: frozenset[str] = frozenset(
    {
        "drive_file_list",
        "drive_folder_list",
        "drive_file_name",
        "drive_file_type_icon",
        "drive_modified_date",
        "drive_owner_label",
        "drive_location_label",
        "drive_view_mode",
        "drive_navigation_panel",
        "browser_tab_title",
        "browser_url_bar",
    }
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class GUIObservationPolicy:
    """Policy controlling what may be observed through the GUI."""

    allowed_targets: frozenset[str] = field(
        default_factory=lambda: ALLOWED_OBSERVATION_TARGETS
    )
    blocked_targets: frozenset[str] = field(
        default_factory=lambda: BLOCKED_OBSERVATION_TARGETS
    )
    temporary_observation_allowed: bool = True
    persistent_screenshot_allowed: bool = False
    credential_observation_blocked: bool = True
    document_opening_blocked: bool = True
    wrong_account_pauses: bool = True
    login_screen_pauses: bool = True

    def is_target_allowed(self, target: str) -> bool:
        """Check if an observation target is allowed."""
        if target in self.blocked_targets:
            return False
        return target in self.allowed_targets

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed_targets": sorted(self.allowed_targets),
            "blocked_targets": sorted(self.blocked_targets),
            "temporary_observation_allowed": self.temporary_observation_allowed,
            "persistent_screenshot_allowed": self.persistent_screenshot_allowed,
            "credential_observation_blocked": self.credential_observation_blocked,
            "document_opening_blocked": self.document_opening_blocked,
            "wrong_account_pauses": self.wrong_account_pauses,
            "login_screen_pauses": self.login_screen_pauses,
        }


@dataclass
class GUIAction:
    """A single GUI action to perform."""

    action_type: GUIActionType
    target: str = ""
    value: str = ""
    x: int | None = None
    y: int | None = None
    delay_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "action_type": self.action_type.value,
            "target": self.target,
        }
        if self.value:
            result["value"] = self.value
        if self.x is not None:
            result["x"] = self.x
        if self.y is not None:
            result["y"] = self.y
        if self.delay_ms:
            result["delay_ms"] = self.delay_ms
        return result


@dataclass
class GUIObservationResult:
    """Result of observing the GUI."""

    method: GUIObservationMethod
    target: str
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""
    observed_at: str = field(default_factory=_now_iso)
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method.value,
            "target": self.target,
            "success": self.success,
            "data": self.data,
            "observed_at": self.observed_at,
            "error": self.error,
        }


@dataclass
class GUIInventoryItem:
    """A single item discovered through GUI observation."""

    name: str
    item_type: str = ""
    modified_date: str = ""
    owner: str = ""
    location: str = ""
    row_index: int = 0
    observation_method: GUIObservationMethod = GUIObservationMethod.WINDOWS_UI_AUTOMATION
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "item_type": self.item_type,
            "modified_date": self.modified_date,
            "owner": self.owner,
            "location": self.location,
            "row_index": self.row_index,
            "observation_method": self.observation_method.value,
            "confidence": self.confidence,
        }


def is_observation_target_blocked(target: str) -> bool:
    """Check if an observation target is blocked by policy."""
    return target in BLOCKED_OBSERVATION_TARGETS


def is_observation_target_allowed(target: str) -> bool:
    """Check if an observation target is explicitly allowed."""
    return target in ALLOWED_OBSERVATION_TARGETS


def classify_gui_control_availability(
    has_ui_automation: bool = False,
    has_accessibility: bool = False,
    has_screen_capture: bool = False,
    has_ocr: bool = False,
) -> tuple[GUIControlStatus, GUIObservationMethod | None]:
    """Classify what GUI observation capability is available."""
    if has_ui_automation:
        return (GUIControlStatus.AVAILABLE, GUIObservationMethod.WINDOWS_UI_AUTOMATION)
    if has_accessibility:
        return (GUIControlStatus.AVAILABLE, GUIObservationMethod.ACCESSIBILITY_TREE)
    if has_screen_capture:
        return (GUIControlStatus.PARTIAL, GUIObservationMethod.TEMPORARY_SCREEN_OBSERVATION)
    if has_ocr:
        return (GUIControlStatus.PARTIAL, GUIObservationMethod.OCR_LAST_RESORT)
    return (GUIControlStatus.MISSING, None)


def build_gui_backend_missing_report(
    checked_methods: list[str],
) -> dict[str, Any]:
    """Build a report when no GUI observation backend is available."""
    return {
        "status": "GUI_OBSERVATION_BACKEND_MISSING",
        "checked_methods": checked_methods,
        "options": [
            {"option": "A", "action": "BUILD_UI_AUTOMATION_BACKEND", "description": "Install/build Windows UI Automation observation backend"},
            {"option": "B", "action": "APPROVE_TEMPORARY_SCREENSHOT_OCR", "description": "Approve temporary screen capture + OCR backend"},
            {"option": "C", "action": "HUMAN_VISUAL_INVENTORY", "description": "Founder provides inventory from visible screen"},
            {"option": "D", "action": "CANCEL", "description": "Cancel computer-use test"},
        ],
    }
