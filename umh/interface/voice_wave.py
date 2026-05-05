"""Phase 84 six-line voice-wave state model — representational only.

State/metadata for the minimized voice-wave glyph concept.
No animation implementation. No audio implementation.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.core.clock import iso_now as _iso_now

DEFAULT_LINE_COUNT = 6


class VoiceWaveState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    MUTED = "muted"
    ERROR = "error"
    ATTENTION_REQUIRED = "attention_required"
    EXECUTING = "executing"
    UNKNOWN = "unknown"


class VoiceWaveLineState(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PULSE = "pulse"
    OFF = "off"
    UNKNOWN = "unknown"


def normalize_voice_wave_state(value: str) -> VoiceWaveState:
    try:
        return VoiceWaveState(value.lower().strip())
    except (ValueError, AttributeError):
        return VoiceWaveState.UNKNOWN


def normalize_line_state(value: str) -> VoiceWaveLineState:
    try:
        return VoiceWaveLineState(value.lower().strip())
    except (ValueError, AttributeError):
        return VoiceWaveLineState.UNKNOWN


_DEFAULT_LINE_PATTERNS: dict[VoiceWaveState, list[VoiceWaveLineState]] = {
    VoiceWaveState.IDLE: [
        VoiceWaveLineState.LOW,
        VoiceWaveLineState.MEDIUM,
        VoiceWaveLineState.LOW,
        VoiceWaveLineState.LOW,
        VoiceWaveLineState.MEDIUM,
        VoiceWaveLineState.LOW,
    ],
    VoiceWaveState.LISTENING: [
        VoiceWaveLineState.MEDIUM,
        VoiceWaveLineState.PULSE,
        VoiceWaveLineState.MEDIUM,
        VoiceWaveLineState.PULSE,
        VoiceWaveLineState.MEDIUM,
        VoiceWaveLineState.PULSE,
    ],
    VoiceWaveState.THINKING: [
        VoiceWaveLineState.PULSE,
        VoiceWaveLineState.LOW,
        VoiceWaveLineState.PULSE,
        VoiceWaveLineState.LOW,
        VoiceWaveLineState.PULSE,
        VoiceWaveLineState.LOW,
    ],
    VoiceWaveState.SPEAKING: [
        VoiceWaveLineState.HIGH,
        VoiceWaveLineState.MEDIUM,
        VoiceWaveLineState.HIGH,
        VoiceWaveLineState.MEDIUM,
        VoiceWaveLineState.HIGH,
        VoiceWaveLineState.MEDIUM,
    ],
    VoiceWaveState.MUTED: [
        VoiceWaveLineState.OFF,
        VoiceWaveLineState.LOW,
        VoiceWaveLineState.OFF,
        VoiceWaveLineState.OFF,
        VoiceWaveLineState.LOW,
        VoiceWaveLineState.OFF,
    ],
    VoiceWaveState.ERROR: [
        VoiceWaveLineState.PULSE,
        VoiceWaveLineState.OFF,
        VoiceWaveLineState.PULSE,
        VoiceWaveLineState.OFF,
        VoiceWaveLineState.PULSE,
        VoiceWaveLineState.OFF,
    ],
    VoiceWaveState.ATTENTION_REQUIRED: [
        VoiceWaveLineState.PULSE,
        VoiceWaveLineState.PULSE,
        VoiceWaveLineState.HIGH,
        VoiceWaveLineState.HIGH,
        VoiceWaveLineState.PULSE,
        VoiceWaveLineState.PULSE,
    ],
    VoiceWaveState.EXECUTING: [
        VoiceWaveLineState.MEDIUM,
        VoiceWaveLineState.HIGH,
        VoiceWaveLineState.PULSE,
        VoiceWaveLineState.PULSE,
        VoiceWaveLineState.HIGH,
        VoiceWaveLineState.MEDIUM,
    ],
}

_ACCESSIBLE_LABELS: dict[VoiceWaveState, str] = {
    VoiceWaveState.IDLE: "System idle",
    VoiceWaveState.LISTENING: "Listening for input",
    VoiceWaveState.THINKING: "Processing request",
    VoiceWaveState.SPEAKING: "Speaking response",
    VoiceWaveState.MUTED: "Microphone muted",
    VoiceWaveState.ERROR: "Error occurred",
    VoiceWaveState.ATTENTION_REQUIRED: "Attention required",
    VoiceWaveState.EXECUTING: "Executing action",
    VoiceWaveState.UNKNOWN: "Unknown state",
}


@dataclass
class VoiceWaveGlyph:
    glyph_id: str
    line_count: int = DEFAULT_LINE_COUNT
    state: VoiceWaveState = VoiceWaveState.IDLE
    line_states: list[str] = field(default_factory=list)
    animation_hint: str = ""
    accessible_label: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "glyph_id": self.glyph_id,
            "line_count": self.line_count,
            "state": self.state.value if isinstance(self.state, Enum) else self.state,
            "line_states": self.line_states,
            "animation_hint": self.animation_hint,
            "accessible_label": self.accessible_label,
            "metadata": self.metadata,
        }


@dataclass
class VoiceWaveTransition:
    from_state: VoiceWaveState = VoiceWaveState.UNKNOWN
    to_state: VoiceWaveState = VoiceWaveState.UNKNOWN
    allowed: bool = False
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_state": self.from_state.value
            if isinstance(self.from_state, Enum)
            else self.from_state,
            "to_state": self.to_state.value if isinstance(self.to_state, Enum) else self.to_state,
            "allowed": self.allowed,
            "reason": self.reason,
            "metadata": self.metadata,
        }


def create_voice_wave_glyph(state: VoiceWaveState = VoiceWaveState.IDLE) -> VoiceWaveGlyph:
    gid = f"vwg_{hashlib.sha256(f'{state.value}{_iso_now()}'.encode()).hexdigest()[:10]}"
    line_pattern = _DEFAULT_LINE_PATTERNS.get(state, _DEFAULT_LINE_PATTERNS[VoiceWaveState.IDLE])
    label = _ACCESSIBLE_LABELS.get(state, "Unknown state")
    return VoiceWaveGlyph(
        glyph_id=gid,
        line_count=DEFAULT_LINE_COUNT,
        state=state,
        line_states=[ls.value for ls in line_pattern],
        animation_hint=state.value,
        accessible_label=label,
    )


def get_default_six_line_wave(state: VoiceWaveState = VoiceWaveState.IDLE) -> VoiceWaveGlyph:
    return create_voice_wave_glyph(state)


def transition_voice_wave(
    glyph: VoiceWaveGlyph,
    target_state: VoiceWaveState,
) -> VoiceWaveTransition:
    if glyph.state == target_state:
        return VoiceWaveTransition(
            from_state=glyph.state,
            to_state=target_state,
            allowed=True,
            reason="Already in target state",
        )
    if target_state == VoiceWaveState.UNKNOWN:
        return VoiceWaveTransition(
            from_state=glyph.state,
            to_state=target_state,
            allowed=False,
            reason="Cannot transition to unknown state",
        )
    return VoiceWaveTransition(
        from_state=glyph.state,
        to_state=target_state,
        allowed=True,
        reason=f"Transition from {glyph.state.value} to {target_state.value}",
    )
