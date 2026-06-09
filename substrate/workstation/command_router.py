"""Command router — natural language command classification and routing.

Classifies operator natural language into command intents and routes them
to the appropriate handler. Deterministic keyword matching with no LLM
dependency. Integrates with governance for executable/risky commands.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CommandIntent(str, Enum):
    STATUS_QUERY = "status_query"
    RESUME_QUERY = "resume_query"
    APPROVAL_QUERY = "approval_query"
    MODE_SWITCH = "mode_switch"
    WORK_PACKET_DRAFT = "work_packet_draft"
    COCKPIT_NAVIGATION = "cockpit_navigation"
    AGENT_QUERY = "agent_query"
    BLOCKED_QUERY = "blocked_query"
    PACKET_CONTROL = "packet_control"
    COMMAND_CENTER_QUERY = "command_center_query"
    COUNCIL_REVIEW = "council_review"
    CC_SEND = "cc_send"
    CC_CAPTURE = "cc_capture"
    DECOMPOSE_INTENT = "decompose_intent"
    EXPLAIN_CURRENT_VIEW = "explain_current_view"
    WORKSTATION_CONTROL = "workstation_control"
    VPS_CONTROL = "vps_control"
    CONTINUITY_TRANSITION = "continuity_transition"
    STARTUP_SEQUENCE = "startup_sequence"
    UNKNOWN = "unknown"


class GovernanceRequirement(str, Enum):
    NONE = "none"
    INFORMATIONAL = "informational"
    REQUIRES_GOVERNANCE = "requires_governance"


_STATUS_SIGNALS = [
    "what is happening",
    "what's happening",
    "what's going on",
    "whats happening",
    "whats going on",
    "current status",
    "system status",
    "status report",
    "give me status",
    "show me status",
    "how are things",
    "sitrep",
    "how is everything",
    "what are you working on",
    "what are we working on",
]

_RESUME_SIGNALS = [
    "what happened while i was gone",
    "what happened while i was away",
    "what did i miss",
    "catch me up",
    "morning brief",
    "resume brief",
    "what happened overnight",
    "what happened since",
    "bring me up to speed",
    "i'm back",
    "im back",
    "good morning",
    "i just got back",
]

_APPROVAL_SIGNALS = [
    "what needs approval",
    "pending approval",
    "what's pending",
    "whats pending",
    "anything to approve",
    "approvals",
    "show approvals",
    "what needs my sign-off",
    "what needs review",
    "waiting for me",
]

_MODE_SWITCH_SIGNALS = [
    "switch to developer",
    "switch to dev mode",
    "developer mode",
    "focused mode",
    "focus mode",
    "switch to review",
    "switch to execute",
    "switch to plan",
    "review mode",
    "execute mode",
    "plan mode",
    "back to work",
    "be right back",
]

_WORK_PACKET_SIGNALS = [
    "draft a work packet",
    "create a work packet",
    "create a task",
    "prepare the next work packet",
    "prepare the next safe step",
    "start working on",
    "begin working on",
    "start this task",
    "begin this task",
]

_AGENT_SIGNALS = [
    "show active agents",
    "show agents",
    "what are the agents doing",
    "agent status",
    "who is working",
    "which agents are running",
    "list agents",
    "agent list",
    "what agents exist",
    "fleet status",
]

_BLOCKED_SIGNALS = [
    "what is blocked",
    "show blocked",
    "blocked work",
    "blocked tasks",
    "blocked packets",
    "what's stuck",
    "whats stuck",
    "show blockers",
    "any blockers",
]

_PACKET_CONTROL_SIGNALS = [
    "pause this work packet",
    "pause the work packet",
    "pause work packet",
    "resume this work packet",
    "resume the work packet",
    "resume work packet",
    "stop this work packet",
    "stop the work packet",
    "stop work packet",
    "route this to",
    "assign this to",
    "delegate this to",
]

_COMMAND_CENTER_SIGNALS = [
    "command center",
    "full status",
    "full report",
    "everything report",
    "system overview",
    "operational summary",
    "give me the full picture",
    "what is the state of everything",
    "overall status",
]

_COUNCIL_REVIEW_SIGNALS = [
    "run council review",
    "council review",
    "council this",
    "review this like an expert",
    "review this like a world-class expert",
    "give me the final verdict",
    "final verdict",
    "what would the council say",
    "expert review",
    "multi-perspective review",
]

_CC_SEND_SIGNALS = [
    "send to claude code",
    "send this to claude code",
    "send this to cc",
    "delegate to claude",
    "have claude work on this",
    "send to claude",
    "delegate to cc",
    "claude code this",
]

_CC_CAPTURE_SIGNALS = [
    "capture output",
    "capture claude output",
    "what did claude do",
    "show claude output",
    "capture claude session",
    "get claude output",
    "what did cc do",
]

_DECOMPOSE_SIGNALS = [
    "turn this into work packets",
    "break this into packets",
    "decompose this",
    "make work packets from this",
    "create work packets",
    "decompose into packets",
    "split into tasks",
    "break this down",
]

_EXPLAIN_VIEW_SIGNALS = [
    "what am i looking at",
    "what is this",
    "explain this",
    "what should i do next",
    "what should we do next",
    "what does this page mean",
    "what is selected",
    "what can you see",
    "look at this",
    "analyze this page",
    "review this screen",
    "what's next",
    "whats next",
]

_VPS_CONTROL_SIGNALS = [
    "vps status",
    "server status",
    "show vps",
    "docker containers",
    "show containers",
    "docker ps",
    "list containers",
    "running containers",
    "provider health",
    "check provider",
    "provider status",
    "llm health",
    "model health",
    "operator logs",
    "discord logs",
    "restart operator",
    "restart discord",
    "restart the operator",
    "restart the bot",
    "git status",
    "show git",
    "tmux sessions",
    "tmux list",
    "capture tmux",
    "capture the claude",
    "capture session",
    "capture the session",
    "capture claude code",
    "service status",
    "show services",
    "cockpit build",
    "build cockpit",
    "cockpit typecheck",
    "type check",
    "python compile",
    "compile check",
    "cpu usage",
    "cpu load",
    "memory usage",
    "ram usage",
    "disk usage",
    "disk space",
    "show disk",
    "show cpu",
    "show memory",
    "show ram",
    "voice health",
    "voice status",
    "stt status",
    "tts status",
    "run the test suite",
    "run tests",
    "deploy the cockpit",
]

_WORKSTATION_CONTROL_SIGNALS = [
    "play music",
    "pause music",
    "next song",
    "previous song",
    "skip song",
    "take a screenshot",
    "screenshot",
    "what windows are open",
    "list windows",
    "show windows",
]

_WORKSTATION_VERB_PREFIXES = ["open ", "pull up ", "launch ", "focus ", "switch to "]

_CONTINUITY_TRANSITION_SIGNALS = [
    "start day cycle",
    "go into night cycle",
    "go into night mode",
    "start night cycle",
    "night mode",
    "start overnight",
    "i'm stepping away",
    "im stepping away",
    "stepping away",
    "going away",
    "going to sleep",
    "i'll be away",
    "i need to step out",
    "going on vacation",
    "extended absence",
    "i'm going remote",
    "im going remote",
    "working remote today",
    "end my day",
    "end of day",
    "closing out",
    "wrap up for the night",
    "shut down for the night",
    "prepare overnight work",
]

_STARTUP_SEQUENCE_SIGNALS = [
    "start my workday",
    "start my day",
    "morning sequence",
    "boot everything up",
    "wake up the system",
    "wake everything up",
    "initialize workstation",
    "begin day cycle",
]


def _get_known_app_keys() -> set[str]:
    """Load app keys from environment mapping engine at runtime."""
    try:
        from substrate.execution.workers.workstation.environment_mapping_engine_v1 import (
            PLATFORM_PROCESS_MAP,
        )

        keys = set(PLATFORM_PROCESS_MAP.keys())
        for entry in PLATFORM_PROCESS_MAP.values():
            keys.add(entry.get("name", "").lower())
        return keys
    except Exception:
        return set()


def _is_workstation_app_target(text: str) -> bool:
    """Check if text names a known app (from environment mapping engine)."""
    known = _get_known_app_keys()
    return text in known


_NAV_MAP: dict[str, str] = {
    "dashboard": "dashboard",
    "command center": "commandcenter",
    "agents": "agents",
    "tasks": "tasks",
    "approvals": "approvals",
    "activity": "activity",
    "knowledge": "knowledge",
    "analytics": "analytics",
    "workspace": "workspace",
    "editor": "editor",
    "ide": "editor",
    "meta ide": "editor",
    "settings": "settings",
    "execution": "execution",
    "portfolio": "portfolio",
    "company": "company",
    "organism": "organism",
    "runtime": "runtime",
    "tmux": "tmux",
    "infrastructure": "infrastructure",
    "intelligence": "intelligence",
    "world model": "worldmodel",
    "self-build": "selfbuild",
    "self build": "selfbuild",
    "tracking": "tracking",
    "workflows": "workflows",
    "skills": "skills",
    "experiments": "experiments",
    "messages": "comms",
    "comms": "comms",
    "profile": "profile",
    "operator": "operator",
}


@dataclass
class CommandResult:
    """Result of a command classification and execution."""

    command_id: str = ""
    intent: str = CommandIntent.UNKNOWN.value
    raw_text: str = ""
    governance: str = GovernanceRequirement.NONE.value
    response_text: str = ""
    panel_target: str = ""
    mode_target: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.command_id:
            self.command_id = f"jcmd_{uuid.uuid4().hex[:12]}"
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_intent(text: str) -> CommandIntent:
    """Classify natural text into a command intent. Deterministic, no LLM.

    Order matters — first match wins. Explicit action commands scan before
    informational queries, which scan before advisory/view-context phrases.
    """
    t = text.lower().strip()

    # ── Explicit action commands (mutating / high-specificity) ────────
    for signal in _CC_SEND_SIGNALS:
        if signal in t:
            return CommandIntent.CC_SEND

    for signal in _CC_CAPTURE_SIGNALS:
        if signal in t:
            return CommandIntent.CC_CAPTURE

    for signal in _DECOMPOSE_SIGNALS:
        if signal in t:
            return CommandIntent.DECOMPOSE_INTENT

    for signal in _WORK_PACKET_SIGNALS:
        if signal in t:
            return CommandIntent.WORK_PACKET_DRAFT

    for signal in _COUNCIL_REVIEW_SIGNALS:
        if signal in t:
            return CommandIntent.COUNCIL_REVIEW

    for signal in _PACKET_CONTROL_SIGNALS:
        if signal in t:
            return CommandIntent.PACKET_CONTROL

    # ── Startup / continuity (high-specificity lifecycle commands) ───
    for signal in _STARTUP_SEQUENCE_SIGNALS:
        if signal in t:
            return CommandIntent.STARTUP_SEQUENCE

    for signal in _CONTINUITY_TRANSITION_SIGNALS:
        if signal in t:
            return CommandIntent.CONTINUITY_TRANSITION

    # ── VPS control (server/infrastructure commands) ────────────────
    for signal in _VPS_CONTROL_SIGNALS:
        if signal in t:
            return CommandIntent.VPS_CONTROL

    # ── VPS blocked patterns (secrets, destructive) ───────────────
    from substrate.workstation.vps_control_catalog import check_blocked

    if check_blocked(t):
        return CommandIntent.VPS_CONTROL

    # ── Workstation control (app/desktop commands) ──────────────────
    for signal in _WORKSTATION_CONTROL_SIGNALS:
        if signal in t:
            return CommandIntent.WORKSTATION_CONTROL

    # ── Informational queries (read-only, specific) ──────────────────
    for signal in _RESUME_SIGNALS:
        if signal in t:
            return CommandIntent.RESUME_QUERY

    for signal in _APPROVAL_SIGNALS:
        if signal in t:
            return CommandIntent.APPROVAL_QUERY

    for signal in _STATUS_SIGNALS:
        if signal in t:
            return CommandIntent.STATUS_QUERY

    for signal in _MODE_SWITCH_SIGNALS:
        if signal in t:
            return CommandIntent.MODE_SWITCH

    for signal in _COMMAND_CENTER_SIGNALS:
        if signal in t:
            return CommandIntent.COMMAND_CENTER_QUERY

    for signal in _AGENT_SIGNALS:
        if signal in t:
            return CommandIntent.AGENT_QUERY

    for signal in _BLOCKED_SIGNALS:
        if signal in t:
            return CommandIntent.BLOCKED_QUERY

    # ── View-context / advisory (broad phrases, conversational) ──────
    for signal in _EXPLAIN_VIEW_SIGNALS:
        if signal in t:
            return CommandIntent.EXPLAIN_CURRENT_VIEW

    # ── Navigation ───────────────────────────────────────────────────
    nav_prefix = ["show ", "go to ", "open ", "navigate to "]
    for prefix in nav_prefix:
        if t.startswith(prefix):
            remainder = t[len(prefix) :]
            if remainder in _NAV_MAP:
                return CommandIntent.COCKPIT_NAVIGATION

    for nav_key in _NAV_MAP:
        if t == nav_key or t == f"show {nav_key}" or t == f"go to {nav_key}":
            return CommandIntent.COCKPIT_NAVIGATION

    # ── Fallback: "verb [target]" not in NAV_MAP → workstation control ─
    for prefix in _WORKSTATION_VERB_PREFIXES:
        if t.startswith(prefix):
            remainder = t[len(prefix) :]
            if remainder:
                return CommandIntent.WORKSTATION_CONTROL

    # ── External communication intent → workstation control (governed) ─
    _EXTERNAL_ACTION_VERBS = ["message ", "dm ", "send ", "post ", "comment ", "like ", "follow "]
    for verb in _EXTERNAL_ACTION_VERBS:
        if verb in t:
            return CommandIntent.WORKSTATION_CONTROL

    return CommandIntent.UNKNOWN


def resolve_navigation_target(text: str) -> str:
    """Extract the cockpit panel target from navigation text."""
    t = text.lower().strip()
    for prefix in ["show ", "go to ", "open ", "navigate to "]:
        if t.startswith(prefix):
            remainder = t[len(prefix) :]
            if remainder in _NAV_MAP:
                return _NAV_MAP[remainder]

    for nav_key, panel in _NAV_MAP.items():
        if t == nav_key:
            return panel

    return ""


def resolve_mode_target(text: str) -> str:
    """Extract the target mode from mode switch text."""
    t = text.lower().strip()

    if any(s in t for s in ["developer mode", "dev mode", "switch to developer", "switch to dev"]):
        return "developer"
    if any(s in t for s in ["night cycle", "night mode", "overnight", "going to sleep"]):
        return "night_sleeping"
    if any(s in t for s in ["end of day", "closing out"]):
        return "night_sleeping"
    if any(s in t for s in ["going away", "stepping away", "be right back"]):
        return "away"
    if any(s in t for s in ["i'm back", "im back", "back to work"]):
        return "returning"
    if any(s in t for s in ["focused mode", "focus mode"]):
        return "focused"
    if any(s in t for s in ["switch to review", "review mode"]):
        return "REVIEW"
    if any(s in t for s in ["switch to execute", "execute mode"]):
        return "EXECUTE"
    if any(s in t for s in ["switch to plan", "plan mode"]):
        return "PLAN"
    return ""


def _lookup_app(name: str) -> dict[str, str]:
    """Runtime lookup of app info from environment mapping engine."""
    try:
        from substrate.execution.workers.workstation.environment_mapping_engine_v1 import (
            PLATFORM_PROCESS_MAP,
        )
    except Exception:
        return {}
    entry = PLATFORM_PROCESS_MAP.get(name)
    if entry:
        return {
            "process": entry.get("process", ""),
            "domain": entry.get("domain", ""),
            "name": entry.get("name", name),
        }
    for key, val in PLATFORM_PROCESS_MAP.items():
        if val.get("name", "").lower() == name:
            return {
                "process": val.get("process", ""),
                "domain": val.get("domain", ""),
                "name": val.get("name", key),
            }
    return {}


def _enrich_with_lane_info(result: dict[str, Any], text: str) -> dict[str, Any]:
    """Enrich a workstation target result with lane routing and app resolution.

    Adds is_native, launch_cmd, browser, lane_type, lane_metadata, and
    foreground guard approval.  Mutates and returns the result dict.
    """
    from substrate.workstation.app_resolver import (
        resolve_app_target,
        resolve_search_url,
    )
    from substrate.workstation.work_lane import (
        ForegroundGuard,
        lane_hud_metadata,
        route_to_lane,
    )

    # App resolution: if target_app is set, resolve it
    if result.get("target_app"):
        app_target = resolve_app_target(result["target_app"])
        result["is_native"] = app_target.is_native
        result["launch_cmd"] = app_target.launch_cmd
        result["browser"] = app_target.browser
        if app_target.is_native:
            # Native apps: clear target_url (don't open website)
            result["target_url"] = ""
        elif app_target.open_url and not result.get("target_url"):
            result["target_url"] = app_target.open_url

    # Search URL override
    search_url = resolve_search_url(text)
    if search_url:
        result["target_url"] = search_url
        result["browser"] = "chrome"

    # Lane routing
    lane = route_to_lane(text, "command_router")
    result["lane_type"] = lane.lane_type.value
    result["lane_metadata"] = lane_hud_metadata(lane)

    # Foreground guard (merge with existing requires_approval via OR)
    guard_result = ForegroundGuard().check(text, lane)
    result["requires_approval"] = (
        result.get("requires_approval", False) or guard_result.requires_approval
    )

    return result


def resolve_workstation_target(text: str) -> dict[str, Any]:
    """Extract app target, action type, and risk from workstation control text.

    Uses runtime app registry from environment_mapping_engine_v1 — no hardcoded
    app names, URLs, or process names.  Enriched with work lane routing, native
    app resolution, and foreground guard.
    """
    t = text.lower().strip()
    result: dict[str, Any] = {
        "action": "open",
        "target_app": "",
        "target_url": "",
        "process_name": "",
        "risk": "low",
        "requires_approval": False,
    }

    if any(s in t for s in ["screenshot", "take a screenshot"]):
        result["action"] = "screenshot"
        return _enrich_with_lane_info(result, text)

    if any(s in t for s in ["list windows", "what windows are open", "show windows"]):
        result["action"] = "list_windows"
        return _enrich_with_lane_info(result, text)

    if any(
        s in t for s in ["play music", "pause music", "next song", "previous song", "skip song"]
    ):
        if "pause" in t:
            result["action"] = "media_pause"
        elif "next" in t or "skip" in t:
            result["action"] = "media_next"
        elif "previous" in t:
            result["action"] = "media_previous"
        else:
            result["action"] = "media_play"
        result["risk"] = "low"
        return _enrich_with_lane_info(result, text)

    for prefix in _WORKSTATION_VERB_PREFIXES:
        if t.startswith(prefix):
            remainder = t[len(prefix) :]
            if not remainder:
                continue
            if prefix.strip() in ("focus", "switch to"):
                result["action"] = "focus"
            app_info = _lookup_app(remainder)
            if app_info:
                result["target_app"] = remainder
                result["process_name"] = app_info.get("process", "")
                if app_info.get("domain"):
                    result["target_url"] = f"https://{app_info['domain']}"
                return _enrich_with_lane_info(result, text)
            result["target_app"] = remainder
            if remainder.isalpha() and len(remainder) <= 30:
                result["target_url"] = f"https://{remainder}.com"
            return _enrich_with_lane_info(result, text)

    if any(s in t for s in ["message", "dm", "send", "post", "comment", "like", "follow"]):
        result["risk"] = "high"
        result["requires_approval"] = True

    return _enrich_with_lane_info(result, text)


def resolve_continuity_target(text: str) -> str:
    """Extract target continuity state from transition text."""
    t = text.lower().strip()

    if any(s in t for s in ["day cycle", "start my day", "begin day"]):
        return "active"
    if any(
        s in t
        for s in ["night cycle", "night mode", "shut down for the night", "wrap up for the night"]
    ):
        return "night_sleeping"
    if any(s in t for s in ["stepping away", "step out", "i'll be away", "i need to step"]):
        return "away"
    if any(s in t for s in ["going remote", "working remote", "remote today"]):
        return "remote"
    if any(s in t for s in ["vacation", "extended absence"]):
        return "extended_absence"
    if any(s in t for s in ["end my day", "end of day", "closing out"]):
        return "night_sleeping"
    if any(s in t for s in ["prepare overnight", "overnight work"]):
        return "night_sleeping"
    return ""


def resolve_packet_control_action(text: str) -> str:
    """Extract the control action from packet control text."""
    t = text.lower().strip()
    if any(s in t for s in ["pause this", "pause the", "pause work"]):
        return "pause"
    if any(s in t for s in ["resume this", "resume the", "resume work"]):
        return "resume"
    if any(s in t for s in ["stop this", "stop the", "stop work"]):
        return "stop"
    if any(s in t for s in ["route this", "assign this", "delegate this"]):
        return "route"
    return ""


def governance_requirement(intent: CommandIntent) -> GovernanceRequirement:
    """Determine governance requirement for an intent."""
    if intent in (
        CommandIntent.STATUS_QUERY,
        CommandIntent.RESUME_QUERY,
        CommandIntent.APPROVAL_QUERY,
        CommandIntent.COCKPIT_NAVIGATION,
        CommandIntent.AGENT_QUERY,
        CommandIntent.BLOCKED_QUERY,
        CommandIntent.COMMAND_CENTER_QUERY,
        CommandIntent.EXPLAIN_CURRENT_VIEW,
        CommandIntent.UNKNOWN,
    ):
        return GovernanceRequirement.INFORMATIONAL

    if intent in (
        CommandIntent.MODE_SWITCH,
        CommandIntent.CONTINUITY_TRANSITION,
        CommandIntent.STARTUP_SEQUENCE,
    ):
        return GovernanceRequirement.INFORMATIONAL

    if intent in (
        CommandIntent.WORK_PACKET_DRAFT,
        CommandIntent.PACKET_CONTROL,
        CommandIntent.CC_SEND,
        CommandIntent.DECOMPOSE_INTENT,
        CommandIntent.WORKSTATION_CONTROL,
        CommandIntent.VPS_CONTROL,
    ):
        return GovernanceRequirement.REQUIRES_GOVERNANCE

    if intent in (
        CommandIntent.COUNCIL_REVIEW,
        CommandIntent.CC_CAPTURE,
    ):
        return GovernanceRequirement.INFORMATIONAL

    return GovernanceRequirement.NONE
