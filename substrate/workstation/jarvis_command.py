"""Jarvis command router — natural language command classification and routing.

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
    "start night cycle",
    "night mode",
    "start overnight",
    "end of day",
    "closing out",
    "going to sleep",
    "going away",
    "stepping away",
    "be right back",
    "back to work",
    "focused mode",
    "focus mode",
    "switch to review",
    "switch to execute",
    "switch to plan",
    "review mode",
    "execute mode",
    "plan mode",
]

_WORK_PACKET_SIGNALS = [
    "prepare the next",
    "next safe step",
    "draft a work packet",
    "create a task",
    "inspect the repo",
    "what should we do next",
    "what should i do next",
    "suggest next step",
    "next action",
    "plan next",
    "what's next",
    "whats next",
    "start working on",
    "begin working on",
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
    "is this good enough",
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
class JarvisCommandResult:
    """Result of a Jarvis command classification and execution."""

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
    """Classify natural text into a command intent. Deterministic, no LLM."""
    t = text.lower().strip()

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

    for signal in _WORK_PACKET_SIGNALS:
        if signal in t:
            return CommandIntent.WORK_PACKET_DRAFT

    for signal in _AGENT_SIGNALS:
        if signal in t:
            return CommandIntent.AGENT_QUERY

    for signal in _BLOCKED_SIGNALS:
        if signal in t:
            return CommandIntent.BLOCKED_QUERY

    for signal in _PACKET_CONTROL_SIGNALS:
        if signal in t:
            return CommandIntent.PACKET_CONTROL

    for signal in _COMMAND_CENTER_SIGNALS:
        if signal in t:
            return CommandIntent.COMMAND_CENTER_QUERY

    for signal in _COUNCIL_REVIEW_SIGNALS:
        if signal in t:
            return CommandIntent.COUNCIL_REVIEW

    for signal in _CC_SEND_SIGNALS:
        if signal in t:
            return CommandIntent.CC_SEND

    for signal in _CC_CAPTURE_SIGNALS:
        if signal in t:
            return CommandIntent.CC_CAPTURE

    for signal in _DECOMPOSE_SIGNALS:
        if signal in t:
            return CommandIntent.DECOMPOSE_INTENT

    nav_prefix = ["show ", "go to ", "open ", "navigate to "]
    for prefix in nav_prefix:
        if t.startswith(prefix):
            remainder = t[len(prefix):]
            if remainder in _NAV_MAP:
                return CommandIntent.COCKPIT_NAVIGATION

    for nav_key in _NAV_MAP:
        if t == nav_key or t == f"show {nav_key}" or t == f"go to {nav_key}":
            return CommandIntent.COCKPIT_NAVIGATION

    return CommandIntent.UNKNOWN


def resolve_navigation_target(text: str) -> str:
    """Extract the cockpit panel target from navigation text."""
    t = text.lower().strip()
    for prefix in ["show ", "go to ", "open ", "navigate to "]:
        if t.startswith(prefix):
            remainder = t[len(prefix):]
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
        CommandIntent.UNKNOWN,
    ):
        return GovernanceRequirement.INFORMATIONAL

    if intent == CommandIntent.MODE_SWITCH:
        return GovernanceRequirement.INFORMATIONAL

    if intent in (
        CommandIntent.WORK_PACKET_DRAFT,
        CommandIntent.PACKET_CONTROL,
        CommandIntent.CC_SEND,
        CommandIntent.DECOMPOSE_INTENT,
    ):
        return GovernanceRequirement.REQUIRES_GOVERNANCE

    if intent in (
        CommandIntent.COUNCIL_REVIEW,
        CommandIntent.CC_CAPTURE,
    ):
        return GovernanceRequirement.INFORMATIONAL

    return GovernanceRequirement.NONE
