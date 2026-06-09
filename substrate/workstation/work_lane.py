"""Work lane model — multi-session lane routing and foreground guard.

Routes workstation commands to the appropriate execution lane (foreground,
background browser, background shell, or native app).  Foreground guard
prevents accidental disruption of the operator's active session.

All routing is deterministic — no LLM dependency.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class LaneType(str, Enum):
    """Execution lane type for workstation commands."""

    foreground = "foreground"
    background_browser = "background_browser"
    background_shell = "background_shell"
    native_app = "native_app"


@dataclass
class WorkLane:
    """A work execution lane on the workstation.

    Attributes:
        lane_id: Auto-generated unique lane ID.
        lane_type: Execution lane category.
        session_id: Operator session that initiated the command.
        task_description: Human-readable description of the task.
        is_operator_foreground: Whether this lane occupies operator's foreground.
        created_at: ISO timestamp of lane creation.
        metadata: Additional lane metadata for cockpit display.
    """

    lane_type: LaneType
    session_id: str
    task_description: str = ""
    is_operator_foreground: bool = False
    lane_id: str = ""
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.lane_id:
            self.lane_id = f"lane-{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        # foreground and native_app operate in the operator's view
        if self.lane_type in (LaneType.foreground,):
            self.is_operator_foreground = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "lane_id": self.lane_id,
            "lane_type": self.lane_type.value,
            "session_id": self.session_id,
            "task_description": self.task_description,
            "is_operator_foreground": self.is_operator_foreground,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


# Patterns that indicate foreground interaction
_FOREGROUND_PATTERNS: list[str] = [
    "screenshot",
    "take a screenshot",
    "list windows",
    "list_windows",
    "what windows are open",
    "show windows",
    "focus ",
]

# Patterns that indicate browser/web intent
_BROWSER_PATTERNS: list[str] = [
    "search for ",
    "search ",
    "browse ",
    "look up ",
    "find on ",
    "go to ",
    "open http",
    "open www",
]

# Patterns that indicate shell/command intent
_SHELL_PATTERNS: list[str] = [
    "run command",
    "run shell",
    "execute command",
    "powershell",
    "terminal",
    "cmd ",
]

# Verb prefixes that indicate operator explicit request
_OPERATOR_REQUEST_PREFIXES: list[str] = [
    "open ",
    "launch ",
    "pull up ",
    "start ",
]

# Foreground GUI interaction patterns that need approval
_FOREGROUND_GUI_ACTIONS: list[str] = [
    "click ",
    "click on ",
    "type ",
    "type in ",
    "press ",
    "focus_window",
    "drag ",
    "scroll ",
    "right-click",
    "right click",
    "double-click",
    "double click",
]


@dataclass
class ForegroundCheckResult:
    """Result of a foreground guard check.

    Attributes:
        approved: Whether the action is approved without operator consent.
        requires_approval: Whether the action needs explicit approval.
        reason: Human-readable explanation.
    """

    approved: bool
    requires_approval: bool
    reason: str


class ForegroundGuard:
    """Guards foreground access to prevent disrupting the operator.

    Approved without question:
        - Native app launches (no foreground disruption)
        - Background browser / shell tasks
        - Screenshot / list_windows (read-only)

    Requires approval:
        - Foreground GUI interaction (click, type, focus_window)
        - UNLESS the operator explicitly requested it via verb prefix
    """

    def check(self, text: str, lane: WorkLane) -> ForegroundCheckResult:
        """Check whether a command is approved for foreground access.

        Args:
            text: The operator's command text.
            lane: The resolved work lane.

        Returns:
            ForegroundCheckResult with approval status.
        """
        t = text.lower().strip()

        # Background lanes are always approved — no foreground disruption
        if lane.lane_type in (LaneType.background_browser, LaneType.background_shell):
            return ForegroundCheckResult(
                approved=True,
                requires_approval=False,
                reason="background lane — no foreground disruption",
            )

        # Native app launches are approved — they open in their own window
        if lane.lane_type == LaneType.native_app:
            return ForegroundCheckResult(
                approved=True,
                requires_approval=False,
                reason="native app launch — opens in own window",
            )

        # Read-only foreground actions are approved
        read_only = ["screenshot", "list windows", "list_windows", "show windows", "what windows"]
        if any(ro in t for ro in read_only):
            return ForegroundCheckResult(
                approved=True,
                requires_approval=False,
                reason="read-only foreground action",
            )

        # Operator explicitly requested via verb prefix
        if any(t.startswith(p) for p in _OPERATOR_REQUEST_PREFIXES):
            return ForegroundCheckResult(
                approved=True,
                requires_approval=False,
                reason="operator explicitly requested foreground action",
            )

        # GUI interaction actions require approval
        if any(action in t for action in _FOREGROUND_GUI_ACTIONS):
            return ForegroundCheckResult(
                approved=False,
                requires_approval=True,
                reason="foreground GUI interaction requires approval",
            )

        # Default: foreground lane but no risky patterns — approved
        return ForegroundCheckResult(
            approved=True,
            requires_approval=False,
            reason="foreground action — no disruption risk detected",
        )


def route_to_lane(text: str, session_id: str) -> WorkLane:
    """Route operator text to the appropriate work lane.

    Deterministic routing — no LLM.  Order:
    1. Check if target is a native app -> native_app lane
    2. Check for screenshot/list_windows/focus -> foreground lane
    3. Check for browser/search/website -> background_browser lane
    4. Check for shell/command -> background_shell lane
    5. Default: foreground (safe default, operator sees what happens)

    Args:
        text: Operator's natural language command.
        session_id: Session that originated the command.

    Returns:
        WorkLane with routing decision.
    """
    from substrate.workstation.app_resolver import classify_app_vs_website

    t = text.lower().strip()

    # 1. Native app check
    classification = classify_app_vs_website(t)
    if classification == "native_app":
        return WorkLane(
            lane_type=LaneType.native_app,
            session_id=session_id,
            task_description=t,
        )

    # 2. Foreground patterns
    if any(pat in t for pat in _FOREGROUND_PATTERNS):
        return WorkLane(
            lane_type=LaneType.foreground,
            session_id=session_id,
            task_description=t,
        )

    # 3. Browser/web patterns
    if any(pat in t for pat in _BROWSER_PATTERNS):
        return WorkLane(
            lane_type=LaneType.background_browser,
            session_id=session_id,
            task_description=t,
        )

    # Also classify "website" results as background_browser
    if classification == "website":
        return WorkLane(
            lane_type=LaneType.background_browser,
            session_id=session_id,
            task_description=t,
        )

    # 4. Shell patterns
    if any(pat in t for pat in _SHELL_PATTERNS):
        return WorkLane(
            lane_type=LaneType.background_shell,
            session_id=session_id,
            task_description=t,
        )

    # 5. Default: foreground
    return WorkLane(
        lane_type=LaneType.foreground,
        session_id=session_id,
        task_description=t,
    )


def lane_hud_metadata(lane: WorkLane) -> dict[str, Any]:
    """Return HUD metadata for cockpit display.

    Args:
        lane: The resolved work lane.

    Returns:
        Dict with lane_type, is_background, disruption_risk for Workcell J.
    """
    is_background = lane.lane_type in (
        LaneType.background_browser,
        LaneType.background_shell,
    )
    disruption_risk = "none" if is_background else "low"
    if lane.lane_type == LaneType.foreground:
        disruption_risk = "medium"

    return {
        "lane_type": lane.lane_type.value,
        "is_background": is_background,
        "disruption_risk": disruption_risk,
        "session_id": lane.session_id,
        "lane_id": lane.lane_id,
    }
