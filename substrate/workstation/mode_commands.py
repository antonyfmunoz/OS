"""Mode switching via natural typed commands.

Parses natural-language mode switch commands and returns structured
mode change instructions. Deterministic regex/keyword matching first,
no LLM dependency.

Phase 14.11B. Substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from substrate.workstation.continuity import ContinuityState
from substrate.workstation.lifecycle_modes import LifecycleMode
from substrate.workstation.profile_modes import ProfileMode


@dataclass
class ModeCommandResult:
    """Result of parsing a natural mode command."""

    recognized: bool = False
    command_type: str = ""  # "continuity", "lifecycle", "profile"
    target_value: str = ""
    raw_input: str = ""
    confidence: str = "none"  # "high", "medium", "low", "none"

    def to_dict(self) -> dict[str, Any]:
        return {
            "recognized": self.recognized,
            "command_type": self.command_type,
            "target_value": self.target_value,
            "raw_input": self.raw_input,
            "confidence": self.confidence,
        }


_CONTINUITY_PATTERNS: list[tuple[str, ContinuityState]] = [
    (r"\b(?:i'?m\s+back|i\s+am\s+back|back\s+now|returning)\b", ContinuityState.RETURNING),
    (r"\b(?:mark\s+(?:me\s+)?away|i'?m\s+away|going\s+away|leaving|stepping\s+out)\b", ContinuityState.AWAY),
    (r"\b(?:going\s+remote|work(?:ing)?\s+remote(?:ly)?|remote\s+mode)\b", ContinuityState.REMOTE),
    (r"\b(?:good\s*night|going\s+to\s+(?:sleep|bed))\b", ContinuityState.NIGHT_SLEEPING),
    (r"\b(?:going\s+idle|mark\s+(?:me\s+)?idle|idle\s+mode)\b", ContinuityState.IDLE),
    (r"\b(?:extended\s+absence|vacation|going\s+on\s+leave)\b", ContinuityState.EXTENDED_ABSENCE),
]

_LIFECYCLE_PATTERNS: list[tuple[str, LifecycleMode]] = [
    (r"\b(?:start\s+)?night\s+cycle\b", LifecycleMode.NIGHT_CYCLE),
    (r"\b(?:start\s+)?day\s+cycle\b", LifecycleMode.DAY_CYCLE),
    (r"\b(?:start\s+)?overnight\s+mode\b", LifecycleMode.OVERNIGHT),
    (r"\b(?:start\s+)?maintenance\s+mode\b", LifecycleMode.MAINTENANCE),
    (r"\b(?:start\s+)?end[\s-]of[\s-]workday\b", LifecycleMode.END_OF_WORKDAY),
    (r"\b(?:start\s+)?emergency\s+mode\b", LifecycleMode.EMERGENCY),
    (r"\b(?:start\s+)?idle\s+mode\b", LifecycleMode.IDLE),
    (r"\b(?:start\s+)?away\s+mode\b", LifecycleMode.AWAY),
    (r"\b(?:start\s+)?remote\s+(?:work\s+)?mode\b", LifecycleMode.REMOTE_WORK),
]

_PROFILE_PATTERNS: list[tuple[str, ProfileMode]] = [
    (r"\b(?:switch\s+to\s+|enter\s+|start\s+)?developer\s+mode\b", ProfileMode.DEVELOPER),
    (r"\b(?:switch\s+to\s+|enter\s+|start\s+)?research\s+mode\b", ProfileMode.RESEARCH),
    (r"\b(?:switch\s+to\s+|enter\s+|start\s+)?music\s+mode\b", ProfileMode.MUSIC),
    (r"\b(?:switch\s+to\s+|enter\s+|start\s+)?design\s+mode\b", ProfileMode.DESIGN),
    (r"\b(?:switch\s+to\s+|enter\s+|start\s+)?content\s+mode\b", ProfileMode.CONTENT),
    (r"\b(?:switch\s+to\s+|enter\s+|start\s+)?command\s+center\b", ProfileMode.COMMAND_CENTER),
    (r"\b(?:switch\s+to\s+|enter\s+|start\s+)?finance\s+mode\b", ProfileMode.FINANCE),
    (r"\b(?:switch\s+to\s+|enter\s+|start\s+)?learning\s+mode\b", ProfileMode.LEARNING),
]


def parse_mode_command(text: str) -> ModeCommandResult:
    """Parse a natural-language mode switch command.

    Returns a ModeCommandResult with recognized=True if a pattern matched.
    Deterministic — no LLM dependency.
    """
    normalized = text.strip().lower()
    if not normalized:
        return ModeCommandResult(raw_input=text)

    for pattern, mode in _LIFECYCLE_PATTERNS:
        if re.search(pattern, normalized, re.IGNORECASE):
            return ModeCommandResult(
                recognized=True,
                command_type="lifecycle",
                target_value=mode.value,
                raw_input=text,
                confidence="high",
            )

    for pattern, mode in _PROFILE_PATTERNS:
        if re.search(pattern, normalized, re.IGNORECASE):
            return ModeCommandResult(
                recognized=True,
                command_type="profile",
                target_value=mode.value,
                raw_input=text,
                confidence="high",
            )

    for pattern, state in _CONTINUITY_PATTERNS:
        if re.search(pattern, normalized, re.IGNORECASE):
            return ModeCommandResult(
                recognized=True,
                command_type="continuity",
                target_value=state.value,
                raw_input=text,
                confidence="high",
            )

    return ModeCommandResult(raw_input=text)
