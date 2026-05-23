"""Browser and GUI Embodiment Contracts v1.

Data shapes for controlled browser and GUI embodiment:
  BrowserState, BrowserSession, BrowserCapabilityRequest,
  BrowserExecutionRequest, BrowserExecutionResult,
  GUIState, VisibleActuationEvent, BrowserOperationalSnapshot.

All contracts are immutable after creation. All carry provenance.
All serialize deterministically.

UMH substrate subsystem.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:16]}"


def _deterministic_id(namespace: str, content: str) -> str:
    h = hashlib.sha256(f"{namespace}:{content}".encode("utf-8")).hexdigest()[:16]
    return f"{namespace}-{h}"


def _content_hash(data: dict[str, Any]) -> str:
    payload = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class BrowserActionType(str, Enum):
    INSPECT_TABS = "inspect_tabs"
    INSPECT_URL = "inspect_url"
    INSPECT_DOM = "inspect_dom"
    NAVIGATE = "navigate"
    SCROLL = "scroll"
    SCREENSHOT = "screenshot"
    DOCUMENT_INSPECT = "document_inspect"
    WINDOW_INSPECT = "window_inspect"
    WINDOW_FOCUS = "window_focus"
    UI_STATE_INSPECT = "ui_state_inspect"


class BrowserActionVerdict(str, Enum):
    APPROVED = "approved"
    DENIED = "denied"
    REQUIRES_REVIEW = "requires_review"


class BrowserExecutionOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    DENIED = "denied"
    NOT_AVAILABLE = "not_available"


class BrowserOperationalMode(str, Enum):
    INSPECTION = "inspection_mode"
    RESEARCH = "research_mode"
    INTERNAL_NAVIGATION = "internal_navigation_mode"
    RESTRICTED_EXECUTION = "restricted_execution_mode"


class NavigationScope(str, Enum):
    NONE = "none"
    LOCAL_ONLY = "local_only"
    INTERNAL_ONLY = "internal_only"
    APPROVED_EXTERNAL = "approved_external"


class GUIWindowState(str, Enum):
    VISIBLE = "visible"
    MINIMIZED = "minimized"
    MAXIMIZED = "maximized"
    HIDDEN = "hidden"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Contract 1: BrowserState
# ---------------------------------------------------------------------------


@dataclass
class BrowserState:
    """Current browser operational state."""

    state_id: str = ""
    browser_type: str = ""
    is_running: bool = False
    active_tabs: int = 0
    current_url: str = ""
    current_title: str = ""
    pid: int = 0
    operational_mode: BrowserOperationalMode = BrowserOperationalMode.INSPECTION
    navigation_scope: NavigationScope = NavigationScope.NONE
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.state_id:
            self.state_id = _new_id("bstate")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash(
            {
                "browser_type": self.browser_type,
                "is_running": self.is_running,
                "current_url": self.current_url,
                "operational_mode": self.operational_mode.value,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "browser_type": self.browser_type,
            "is_running": self.is_running,
            "active_tabs": self.active_tabs,
            "current_url": self.current_url,
            "current_title": self.current_title,
            "pid": self.pid,
            "operational_mode": self.operational_mode.value,
            "navigation_scope": self.navigation_scope.value,
            "content_hash": self.content_hash(),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Contract 2: BrowserSession
# ---------------------------------------------------------------------------


@dataclass
class BrowserSession:
    """A single browser tab or window session."""

    session_id: str = ""
    tab_index: int = 0
    url: str = ""
    title: str = ""
    is_active: bool = False
    is_loading: bool = False
    domain: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.session_id:
            self.session_id = _deterministic_id("bsess", f"{self.tab_index}:{self.url}")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "tab_index": self.tab_index,
            "url": self.url,
            "title": self.title,
            "is_active": self.is_active,
            "is_loading": self.is_loading,
            "domain": self.domain,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Contract 3: BrowserCapabilityRequest
# ---------------------------------------------------------------------------


@dataclass
class BrowserCapabilityRequest:
    """A request for a browser capability."""

    request_id: str = ""
    action_type: BrowserActionType = BrowserActionType.INSPECT_TABS
    target_url: str = ""
    target_selector: str = ""
    operational_mode: BrowserOperationalMode = BrowserOperationalMode.INSPECTION
    correlation_id: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.request_id:
            self.request_id = _new_id("bcapreq")
        if not self.correlation_id:
            self.correlation_id = _new_id("bcorr")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash(
            {
                "action_type": self.action_type.value,
                "target_url": self.target_url,
                "operational_mode": self.operational_mode.value,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "action_type": self.action_type.value,
            "target_url": self.target_url,
            "target_selector": self.target_selector,
            "operational_mode": self.operational_mode.value,
            "correlation_id": self.correlation_id,
            "content_hash": self.content_hash(),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Contract 4: BrowserExecutionRequest
# ---------------------------------------------------------------------------


@dataclass
class BrowserExecutionRequest:
    """A request to execute a browser action."""

    request_id: str = ""
    action_type: BrowserActionType = BrowserActionType.INSPECT_TABS
    target_url: str = ""
    target_selector: str = ""
    scroll_direction: str = ""
    screenshot_path: str = ""
    adapter_type: str = "browser"
    operational_mode: BrowserOperationalMode = BrowserOperationalMode.INSPECTION
    risk_class: str = "safe"
    governance_verdict: BrowserActionVerdict = BrowserActionVerdict.APPROVED
    governance_rules: list[str] = field(default_factory=list)
    correlation_id: str = ""
    timeout_seconds: int = 30
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.request_id:
            self.request_id = _new_id("bexreq")
        if not self.correlation_id:
            self.correlation_id = _new_id("bcorr")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash(
            {
                "action_type": self.action_type.value,
                "target_url": self.target_url,
                "operational_mode": self.operational_mode.value,
                "risk_class": self.risk_class,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "action_type": self.action_type.value,
            "target_url": self.target_url,
            "target_selector": self.target_selector,
            "scroll_direction": self.scroll_direction,
            "screenshot_path": self.screenshot_path,
            "adapter_type": self.adapter_type,
            "operational_mode": self.operational_mode.value,
            "risk_class": self.risk_class,
            "governance_verdict": self.governance_verdict.value,
            "governance_rules": self.governance_rules,
            "correlation_id": self.correlation_id,
            "timeout_seconds": self.timeout_seconds,
            "content_hash": self.content_hash(),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Contract 5: BrowserExecutionResult
# ---------------------------------------------------------------------------


@dataclass
class BrowserExecutionResult:
    """Result of a browser execution."""

    result_id: str = ""
    request_id: str = ""
    action_type: BrowserActionType = BrowserActionType.INSPECT_TABS
    outcome: BrowserExecutionOutcome = BrowserExecutionOutcome.SUCCESS
    url_before: str = ""
    url_after: str = ""
    dom_summary: str = ""
    screenshot_path: str = ""
    screenshot_hash: str = ""
    adapter_used: str = ""
    duration_ms: float = 0.0
    governance_verdict: str = ""
    error_message: str = ""
    result_data: dict[str, Any] = field(default_factory=dict)
    correlation_id: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.result_id:
            self.result_id = _new_id("bexres")
        if not self.timestamp:
            self.timestamp = _now_iso()

    @property
    def succeeded(self) -> bool:
        return self.outcome == BrowserExecutionOutcome.SUCCESS

    def content_hash(self) -> str:
        return _content_hash(
            {
                "request_id": self.request_id,
                "action_type": self.action_type.value,
                "outcome": self.outcome.value,
                "url_after": self.url_after,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "request_id": self.request_id,
            "action_type": self.action_type.value,
            "outcome": self.outcome.value,
            "succeeded": self.succeeded,
            "url_before": self.url_before,
            "url_after": self.url_after,
            "dom_summary": self.dom_summary,
            "screenshot_path": self.screenshot_path,
            "screenshot_hash": self.screenshot_hash,
            "adapter_used": self.adapter_used,
            "duration_ms": self.duration_ms,
            "governance_verdict": self.governance_verdict,
            "error_message": self.error_message,
            "result_data": self.result_data,
            "correlation_id": self.correlation_id,
            "content_hash": self.content_hash(),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Contract 6: GUIState
# ---------------------------------------------------------------------------


@dataclass
class GUIState:
    """Current GUI/desktop operational state."""

    state_id: str = ""
    desktop_session_active: bool = False
    display_available: bool = False
    active_window_title: str = ""
    active_window_pid: int = 0
    window_state: GUIWindowState = GUIWindowState.UNKNOWN
    visible_windows: list[str] = field(default_factory=list)
    screenshot_available: bool = False
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.state_id:
            self.state_id = _new_id("guistate")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash(
            {
                "desktop_session_active": self.desktop_session_active,
                "display_available": self.display_available,
                "active_window_title": self.active_window_title,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "desktop_session_active": self.desktop_session_active,
            "display_available": self.display_available,
            "active_window_title": self.active_window_title,
            "active_window_pid": self.active_window_pid,
            "window_state": self.window_state.value,
            "visible_windows": self.visible_windows,
            "screenshot_available": self.screenshot_available,
            "content_hash": self.content_hash(),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Contract 7: VisibleActuationEvent
# ---------------------------------------------------------------------------


@dataclass
class VisibleActuationEvent:
    """A single visible actuation event in the browser/GUI."""

    event_id: str = ""
    action_type: BrowserActionType = BrowserActionType.INSPECT_TABS
    target: str = ""
    url: str = ""
    governance_verdict: str = ""
    governance_rules: list[str] = field(default_factory=list)
    outcome: str = ""
    adapter_used: str = ""
    visibility_confirmed: bool = False
    screenshot_path: str = ""
    duration_ms: float = 0.0
    correlation_id: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.event_id:
            self.event_id = _new_id("vactev")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "action_type": self.action_type.value,
            "target": self.target,
            "url": self.url,
            "governance_verdict": self.governance_verdict,
            "governance_rules": self.governance_rules,
            "outcome": self.outcome,
            "adapter_used": self.adapter_used,
            "visibility_confirmed": self.visibility_confirmed,
            "screenshot_path": self.screenshot_path,
            "duration_ms": self.duration_ms,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Contract 8: BrowserOperationalSnapshot
# ---------------------------------------------------------------------------


@dataclass
class BrowserOperationalSnapshot:
    """Complete snapshot of browser/GUI operational state."""

    snapshot_id: str = ""
    browser_state: BrowserState | None = None
    gui_state: GUIState | None = None
    sessions: list[BrowserSession] = field(default_factory=list)
    recent_events: list[VisibleActuationEvent] = field(default_factory=list)
    operational_mode: BrowserOperationalMode = BrowserOperationalMode.INSPECTION
    total_actions: int = 0
    total_denials: int = 0
    phase: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.snapshot_id:
            self.snapshot_id = _new_id("bsnap")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash(
            {
                "snapshot_id": self.snapshot_id,
                "mode": self.operational_mode.value,
                "sessions": len(self.sessions),
                "total_actions": self.total_actions,
                "phase": self.phase,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "browser_state": self.browser_state.to_dict() if self.browser_state else None,
            "gui_state": self.gui_state.to_dict() if self.gui_state else None,
            "sessions": [s.to_dict() for s in self.sessions],
            "recent_events": [e.to_dict() for e in self.recent_events],
            "operational_mode": self.operational_mode.value,
            "total_actions": self.total_actions,
            "total_denials": self.total_denials,
            "content_hash": self.content_hash(),
            "phase": self.phase,
            "timestamp": self.timestamp,
        }
