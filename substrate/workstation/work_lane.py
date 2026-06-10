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
    background_browser_profile = "background_browser_profile"
    background_shell = "background_shell"
    native_app = "native_app"
    headless_browser = "headless_browser"


class IsolationLevel(str, Enum):
    """How strongly a lane is isolated from the operator session."""

    session_isolated = "session_isolated"
    profile_isolated = "profile_isolated"
    headless = "headless"
    none = "none"


class TransportType(str, Enum):
    """How commands reach the target node."""

    mesh_relay = "mesh_relay"
    ssh = "ssh"


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

    isolation_level: str = IsolationLevel.none.value
    chrome_profile: str = ""

    def __post_init__(self) -> None:
        if not self.lane_id:
            self.lane_id = f"lane-{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if self.lane_type in (LaneType.foreground,):
            self.is_operator_foreground = True
        if self.lane_type == LaneType.background_browser_profile:
            self.isolation_level = IsolationLevel.profile_isolated.value
        elif self.lane_type == LaneType.headless_browser:
            self.isolation_level = IsolationLevel.headless.value

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "lane_id": self.lane_id,
            "lane_type": self.lane_type.value,
            "session_id": self.session_id,
            "task_description": self.task_description,
            "is_operator_foreground": self.is_operator_foreground,
            "isolation_level": self.isolation_level,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }
        if self.chrome_profile:
            d["chrome_profile"] = self.chrome_profile
        return d


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
        if lane.lane_type in (
            LaneType.background_browser,
            LaneType.background_browser_profile,
            LaneType.background_shell,
            LaneType.headless_browser,
        ):
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
    1. Native app -> native_app lane
    2. GUI interaction (click/type/drag) -> foreground (before browser check)
    3. Screenshot/list_windows/focus -> foreground lane
    4. Browser/search/website patterns -> background_browser lane
    5. Unknown apps with "open" prefix that resolve as web -> background_browser
    6. Shell/command patterns -> background_shell lane
    7. Default: foreground (safe default, operator sees what happens)
    """
    from substrate.workstation.app_resolver import classify_app_vs_website, resolve_app_target

    t = text.lower().strip()

    # 1. Native app check
    classification = classify_app_vs_website(t)
    if classification == "native_app":
        return WorkLane(
            lane_type=LaneType.native_app,
            session_id=session_id,
            task_description=t,
        )

    # 2. GUI interaction routes to foreground BEFORE browser pattern check
    if any(action in t for action in _FOREGROUND_GUI_ACTIONS):
        return WorkLane(
            lane_type=LaneType.foreground,
            session_id=session_id,
            task_description=t,
        )

    # 3. Foreground patterns (screenshot, list windows, focus)
    if any(pat in t for pat in _FOREGROUND_PATTERNS):
        return WorkLane(
            lane_type=LaneType.foreground,
            session_id=session_id,
            task_description=t,
        )

    # 4. Browser/web patterns
    if any(pat in t for pat in _BROWSER_PATTERNS):
        return WorkLane(
            lane_type=LaneType.background_browser,
            session_id=session_id,
            task_description=t,
        )

    if classification == "website":
        return WorkLane(
            lane_type=LaneType.background_browser,
            session_id=session_id,
            task_description=t,
        )

    # 5. Unknown apps with "open/launch" prefix — check if they resolve as web
    if classification == "unknown":
        for prefix in _OPERATOR_REQUEST_PREFIXES:
            if t.startswith(prefix):
                remainder = t[len(prefix) :].strip()
                if remainder:
                    target = resolve_app_target(remainder)
                    if not target.is_native and target.open_url:
                        return WorkLane(
                            lane_type=LaneType.background_browser,
                            session_id=session_id,
                            task_description=t,
                        )
                break

    # 6. Shell patterns
    if any(pat in t for pat in _SHELL_PATTERNS):
        return WorkLane(
            lane_type=LaneType.background_shell,
            session_id=session_id,
            task_description=t,
        )

    # 7. Default: foreground
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
        Dict with lane_type, is_background, disruption_risk, isolation_level.
    """
    is_background = lane.lane_type in (
        LaneType.background_browser,
        LaneType.background_browser_profile,
        LaneType.background_shell,
        LaneType.headless_browser,
    )
    disruption_risk = "none" if is_background else "low"
    if lane.lane_type == LaneType.foreground:
        disruption_risk = "medium"
    if lane.lane_type == LaneType.background_browser_profile:
        disruption_risk = "low"

    hud: dict[str, Any] = {
        "lane_type": lane.lane_type.value,
        "is_background": is_background,
        "disruption_risk": disruption_risk,
        "isolation_level": lane.isolation_level,
        "session_id": lane.session_id,
        "lane_id": lane.lane_id,
    }
    if lane.chrome_profile:
        hud["chrome_profile"] = lane.chrome_profile
    return hud


# ── SSH Transport Guard ──────────────────────────────────────────────────

_GUI_CAPABILITIES: frozenset[str] = frozenset({
    "desktop.click",
    "desktop.type",
    "desktop.screenshot",
    "desktop.focus_window",
    "desktop.list_windows",
})

_GUI_SHELL_PATTERNS: list[str] = [
    "start ",
    "start-process ",
    "invoke-item ",
    "explorer ",
    "chrome ",
    "spotify ",
    "discord ",
]


@dataclass
class TransportCheckResult:
    """Result of a transport guard check."""

    allowed: bool
    reason: str


def check_transport_allowed(
    capability: str,
    command: str,
    transport: str,
) -> TransportCheckResult:
    """Block GUI actions through SSH — they land in Session 0.

    SSH is allowed for: file operations, process listing, health checks, logs.
    Mesh relay is required for: app launches, Chrome, screenshots, GUI actions.
    """
    if transport != "ssh":
        return TransportCheckResult(allowed=True, reason="mesh relay transport approved")

    if capability in _GUI_CAPABILITIES:
        return TransportCheckResult(
            allowed=False,
            reason=f"GUI action '{capability}' must route through Beast mesh relay; SSH lands in Session 0.",
        )

    cmd_lower = command.lower().strip()
    if any(cmd_lower.startswith(p) for p in _GUI_SHELL_PATTERNS):
        return TransportCheckResult(
            allowed=False,
            reason=f"GUI shell command must route through Beast mesh relay; SSH lands in Session 0.",
        )

    return TransportCheckResult(allowed=True, reason="non-GUI action allowed via SSH")


# ── Lane Inventory ───────────────────────────────────────────────────────

_DEFAULT_WORKER_PROFILE = "UMH_Worker_01"
_WORKER_PROFILE_DIR = r"C:\UMH\chrome-worker"


def get_lane_inventory(
    has_worker_profile: bool = False,
    has_headless: bool = False,
) -> list[dict[str, Any]]:
    """Return the truthful lane inventory for Beast.

    Does NOT fake Session 2+. Reports only lanes that actually exist.
    """
    lanes: list[dict[str, Any]] = [
        {
            "lane_id": "beast_service_session_0",
            "lane_type": "service",
            "windows_session_id": 0,
            "gui_capable": False,
            "description": "daemon/service only — no GUI automation",
        },
        {
            "lane_id": "beast_operator_foreground",
            "lane_type": LaneType.foreground.value,
            "windows_session_id": 1,
            "gui_capable": True,
            "visible_to_operator": True,
            "isolation_level": IsolationLevel.none.value,
            "description": "operator's visible desktop session",
        },
    ]

    if has_worker_profile:
        lanes.append({
            "lane_id": "beast_background_browser_01",
            "lane_type": LaneType.background_browser_profile.value,
            "windows_session_id": 1,
            "gui_capable": True,
            "visible_to_operator": "potentially",
            "isolation_level": IsolationLevel.profile_isolated.value,
            "browser": "chrome",
            "chrome_profile": _DEFAULT_WORKER_PROFILE,
            "profile_dir": _WORKER_PROFILE_DIR,
            "description": "Chrome worker profile — profile-isolated, not session-isolated",
        })

    if has_headless:
        lanes.append({
            "lane_id": "beast_headless_browser_01",
            "lane_type": LaneType.headless_browser.value,
            "windows_session_id": 1,
            "gui_capable": False,
            "visible_to_operator": False,
            "isolation_level": IsolationLevel.headless.value,
            "browser": "chromium",
            "best_for": ["research", "scraping", "page checks", "docs lookup"],
            "not_for": ["logged-in account workflows unless explicitly authorized"],
            "description": "headless browser — zero foreground disruption",
        })

    return lanes


_SHELL_UNSAFE = frozenset('&|^<>%`"\r\n')


def build_worker_chrome_launch_cmd(url: str = "") -> str:
    """Build the Chrome launch command for the UMH worker profile."""
    parts = [
        "start chrome",
        f'--user-data-dir="{_WORKER_PROFILE_DIR}"',
        "--profile-directory=Default",
        "--new-window",
    ]
    if url:
        if not url.startswith(("http://", "https://")):
            raise ValueError("only http/https URLs allowed")
        if any(c in url for c in _SHELL_UNSAFE):
            raise ValueError("URL contains shell-unsafe characters")
        parts.append(url)
    return " ".join(parts)
