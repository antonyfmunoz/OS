"""Mode switching — deterministic command table, no LLM required."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class SystemMode(Enum):
    ACTIVE = "active"
    AWAY = "away"
    OVERNIGHT = "overnight"
    REMOTE = "remote"


class ProfileMode(Enum):
    DEVELOPER = "developer"
    RESEARCH = "research"
    COMMAND_CENTER = "command_center"
    OUTREACH = "outreach"
    CONTENT = "content"
    OVERNIGHT = "overnight"
    MAINTENANCE = "maintenance"
    SIMULATION = "simulation"
    EMERGENCY = "emergency"
    CUSTOM = "custom"


@dataclass
class ModeState:
    system: SystemMode = SystemMode.ACTIVE
    profiles: list[ProfileMode] = field(default_factory=lambda: [ProfileMode.DEVELOPER])

    @property
    def primary_profile(self) -> ProfileMode:
        return self.profiles[0] if self.profiles else ProfileMode.DEVELOPER

    def set_profile(self, mode: ProfileMode) -> str:
        self.profiles = [mode]
        return f"Switched to {mode.value} mode"

    def stack_profile(self, mode: ProfileMode) -> str:
        if mode not in self.profiles:
            self.profiles.append(mode)
            return f"Stacked {mode.value} mode"
        return f"{mode.value} mode already active"

    def unstack_profile(self, mode: ProfileMode) -> str:
        if mode in self.profiles and len(self.profiles) > 1:
            self.profiles.remove(mode)
            return f"Unstacked {mode.value} mode"
        if len(self.profiles) <= 1:
            return "Cannot unstack the last active mode"
        return f"{mode.value} mode not in stack"

    def display(self) -> str:
        profiles = " + ".join(p.value for p in self.profiles)
        return f"System: {self.system.value} | Profiles: {profiles}"


_PROFILE_ALIASES: dict[str, ProfileMode] = {
    "developer": ProfileMode.DEVELOPER,
    "dev": ProfileMode.DEVELOPER,
    "research": ProfileMode.RESEARCH,
    "command center": ProfileMode.COMMAND_CENTER,
    "command": ProfileMode.COMMAND_CENTER,
    "outreach": ProfileMode.OUTREACH,
    "content": ProfileMode.CONTENT,
    "overnight": ProfileMode.OVERNIGHT,
    "maintenance": ProfileMode.MAINTENANCE,
    "simulation": ProfileMode.SIMULATION,
    "sandbox": ProfileMode.SIMULATION,
    "emergency": ProfileMode.EMERGENCY,
}

_MODE_SWITCH_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^(?:switch to |go )?([\w\s]+?) mode$", re.IGNORECASE), "switch"),
    (re.compile(r"^go ([\w\s]+)$", re.IGNORECASE), "switch"),
    (re.compile(r"^([\w\s]+?) mode$", re.IGNORECASE), "switch"),
    (re.compile(r"^stack ([\w\s]+)$", re.IGNORECASE), "stack"),
    (re.compile(r"^unstack ([\w\s]+)$", re.IGNORECASE), "unstack"),
    (re.compile(r"^lock it down$", re.IGNORECASE), "emergency"),
    (re.compile(r"^good night$", re.IGNORECASE), "overnight"),
]

_SYSTEM_COMMANDS: dict[str, str] = {
    "status": "status",
    "show pending": "pending",
    "voice setup": "voice_setup",
    "push to talk": "push_to_talk",
    "always on": "always_on",
    "webcam on": "webcam_on",
    "webcam off": "webcam_off",
    "exit": "exit",
    "bye": "exit",
    "shut down": "exit",
    "help": "help",
    "settings": "settings",
    "mesh status": "mesh_status",
    "mode info": "mode_info",
    "personality": "personality",
    "governance": "governance",
    "review": "review",
    "profile inference": "profile_inference",
    "awakening": "awakening",
    "the awakening": "awakening",
    "reality brief": "awakening",
    "continuity": "continuity",
    "transport": "transport",
    "transport status": "transport",
    "triggers": "triggers",
    "trigger history": "triggers",
    "scheduler": "scheduler",
    "scheduler status": "scheduler",
    "approvals": "approvals",
    "approval queue": "approvals",
    "outcomes": "outcomes",
    "pipeline outcomes": "outcomes",
    "operator": "operator",
    "operator state": "operator",
    "capabilities": "local_capabilities",
    "local capabilities": "local_capabilities",
    "sysinfo": "local_capabilities",
    "health": "health",
    "health check": "health",
    "full status": "full_status",
    "dashboard": "full_status",
    "view": "view",
    "pipeline": "view",
    "view frames": "view",
}


@dataclass
class CommandResult:
    handled: bool
    command: str = ""
    response: str = ""


def parse_command(text: str, mode_state: ModeState) -> CommandResult:
    text_clean = text.strip().lower()

    for key, cmd in _SYSTEM_COMMANDS.items():
        if text_clean == key:
            return CommandResult(handled=True, command=cmd)

    if text_clean.startswith(("approve ", "reject ")):
        parts = text_clean.split(maxsplit=1)
        return CommandResult(
            handled=True, command=parts[0], response=parts[1] if len(parts) > 1 else ""
        )

    for pattern, action in _MODE_SWITCH_PATTERNS:
        m = pattern.match(text_clean)
        if not m:
            continue

        if action == "emergency":
            resp = mode_state.set_profile(ProfileMode.EMERGENCY)
            return CommandResult(handled=True, command="mode_switch", response=resp)

        if action == "overnight":
            resp = mode_state.set_profile(ProfileMode.OVERNIGHT)
            return CommandResult(handled=True, command="mode_switch", response=resp)

        mode_name = m.group(1).strip() if m.lastindex else ""
        target = _PROFILE_ALIASES.get(mode_name)
        if not target:
            continue

        if action == "switch":
            resp = mode_state.set_profile(target)
        elif action == "stack":
            resp = mode_state.stack_profile(target)
        elif action == "unstack":
            resp = mode_state.unstack_profile(target)
        else:
            continue

        return CommandResult(handled=True, command="mode_switch", response=resp)

    return CommandResult(handled=False)
