"""Phase 84 interface state machine — deterministic UI state transitions.

No UI rendering. No OS calls. Transitions are typed and deterministic.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.core.clock import iso_now as _iso_now


class InterfaceMode(str, Enum):
    FULL_SCREEN = "full_screen"
    WINDOWED = "windowed"
    EXPANDED_OVERLAY = "expanded_overlay"
    MINIMIZED_WAVE = "minimized_wave"
    GHOST = "ghost"
    HIDDEN = "hidden"
    VOICE_ONLY = "voice_only"
    MOBILE = "mobile"
    TERMINAL = "terminal"
    UNKNOWN = "unknown"


class InterfaceVisibility(str, Enum):
    VISIBLE = "visible"
    PARTIAL = "partial"
    MINIMIZED = "minimized"
    HIDDEN = "hidden"
    GHOST = "ghost"
    UNKNOWN = "unknown"


class InterfaceFocusState(str, Enum):
    ACTIVE = "active"
    PASSIVE = "passive"
    BACKGROUND = "background"
    INTERRUPTIVE = "interruptive"
    DO_NOT_DISTURB = "do_not_disturb"
    UNKNOWN = "unknown"


class InterfaceTransitionStatus(str, Enum):
    ALLOWED = "allowed"
    DENIED = "denied"
    NOOP = "noop"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


def normalize_interface_mode(value: str) -> InterfaceMode:
    try:
        return InterfaceMode(value.lower().strip())
    except (ValueError, AttributeError):
        return InterfaceMode.UNKNOWN


def normalize_visibility(value: str) -> InterfaceVisibility:
    try:
        return InterfaceVisibility(value.lower().strip())
    except (ValueError, AttributeError):
        return InterfaceVisibility.UNKNOWN


def normalize_focus_state(value: str) -> InterfaceFocusState:
    try:
        return InterfaceFocusState(value.lower().strip())
    except (ValueError, AttributeError):
        return InterfaceFocusState.UNKNOWN


def normalize_transition_status(value: str) -> InterfaceTransitionStatus:
    try:
        return InterfaceTransitionStatus(value.lower().strip())
    except (ValueError, AttributeError):
        return InterfaceTransitionStatus.UNKNOWN


_ALLOWED_TRANSITIONS: frozenset[tuple[InterfaceMode, InterfaceMode]] = frozenset(
    {
        (InterfaceMode.FULL_SCREEN, InterfaceMode.WINDOWED),
        (InterfaceMode.WINDOWED, InterfaceMode.FULL_SCREEN),
        (InterfaceMode.WINDOWED, InterfaceMode.EXPANDED_OVERLAY),
        (InterfaceMode.EXPANDED_OVERLAY, InterfaceMode.WINDOWED),
        (InterfaceMode.EXPANDED_OVERLAY, InterfaceMode.MINIMIZED_WAVE),
        (InterfaceMode.MINIMIZED_WAVE, InterfaceMode.EXPANDED_OVERLAY),
        (InterfaceMode.EXPANDED_OVERLAY, InterfaceMode.GHOST),
        (InterfaceMode.GHOST, InterfaceMode.EXPANDED_OVERLAY),
        (InterfaceMode.FULL_SCREEN, InterfaceMode.HIDDEN),
        (InterfaceMode.WINDOWED, InterfaceMode.HIDDEN),
        (InterfaceMode.EXPANDED_OVERLAY, InterfaceMode.HIDDEN),
        (InterfaceMode.MINIMIZED_WAVE, InterfaceMode.HIDDEN),
        (InterfaceMode.GHOST, InterfaceMode.HIDDEN),
        (InterfaceMode.VOICE_ONLY, InterfaceMode.HIDDEN),
        (InterfaceMode.MOBILE, InterfaceMode.HIDDEN),
    }
)

_MODE_VISIBILITY: dict[InterfaceMode, InterfaceVisibility] = {
    InterfaceMode.FULL_SCREEN: InterfaceVisibility.VISIBLE,
    InterfaceMode.WINDOWED: InterfaceVisibility.VISIBLE,
    InterfaceMode.EXPANDED_OVERLAY: InterfaceVisibility.VISIBLE,
    InterfaceMode.MINIMIZED_WAVE: InterfaceVisibility.MINIMIZED,
    InterfaceMode.GHOST: InterfaceVisibility.GHOST,
    InterfaceMode.HIDDEN: InterfaceVisibility.HIDDEN,
    InterfaceMode.VOICE_ONLY: InterfaceVisibility.PARTIAL,
    InterfaceMode.MOBILE: InterfaceVisibility.VISIBLE,
    InterfaceMode.TERMINAL: InterfaceVisibility.VISIBLE,
    InterfaceMode.UNKNOWN: InterfaceVisibility.UNKNOWN,
}


@dataclass
class InterfaceState:
    state_id: str
    surface_id: str = ""
    mode: InterfaceMode = InterfaceMode.UNKNOWN
    visibility: InterfaceVisibility = InterfaceVisibility.UNKNOWN
    focus_state: InterfaceFocusState = InterfaceFocusState.UNKNOWN
    voice_state: str | None = None
    position: dict[str, Any] | None = None
    size: dict[str, Any] | None = None
    active_view: str | None = None
    last_event_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "surface_id": self.surface_id,
            "mode": self.mode.value if isinstance(self.mode, Enum) else self.mode,
            "visibility": self.visibility.value
            if isinstance(self.visibility, Enum)
            else self.visibility,
            "focus_state": self.focus_state.value
            if isinstance(self.focus_state, Enum)
            else self.focus_state,
            "voice_state": self.voice_state,
            "position": self.position,
            "size": self.size,
            "active_view": self.active_view,
            "last_event_id": self.last_event_id,
            "metadata": self.metadata,
        }


@dataclass
class InterfaceTransition:
    transition_id: str
    surface_id: str = ""
    from_mode: InterfaceMode = InterfaceMode.UNKNOWN
    to_mode: InterfaceMode = InterfaceMode.UNKNOWN
    status: InterfaceTransitionStatus = InterfaceTransitionStatus.UNKNOWN
    reason: str = ""
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "surface_id": self.surface_id,
            "from_mode": self.from_mode.value
            if isinstance(self.from_mode, Enum)
            else self.from_mode,
            "to_mode": self.to_mode.value if isinstance(self.to_mode, Enum) else self.to_mode,
            "status": self.status.value if isinstance(self.status, Enum) else self.status,
            "reason": self.reason,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def create_interface_state(
    surface_id: str = "",
    mode: InterfaceMode = InterfaceMode.UNKNOWN,
    focus_state: InterfaceFocusState = InterfaceFocusState.UNKNOWN,
    voice_state: str | None = None,
    active_view: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> InterfaceState:
    sid = f"ist_{hashlib.sha256(f'{surface_id}{_iso_now()}'.encode()).hexdigest()[:10]}"
    vis = _MODE_VISIBILITY.get(mode, InterfaceVisibility.UNKNOWN)
    return InterfaceState(
        state_id=sid,
        surface_id=surface_id,
        mode=mode,
        visibility=vis,
        focus_state=focus_state,
        voice_state=voice_state,
        active_view=active_view,
        metadata=metadata or {},
    )


def is_transition_supported(
    from_mode: InterfaceMode,
    to_mode: InterfaceMode,
    surface: Any | None = None,
) -> bool:
    if from_mode == to_mode:
        return True
    if from_mode == InterfaceMode.UNKNOWN or to_mode == InterfaceMode.UNKNOWN:
        return False
    if (from_mode, to_mode) in _ALLOWED_TRANSITIONS:
        return True
    if to_mode == InterfaceMode.HIDDEN:
        return True
    return False


def transition_interface_state(
    state: InterfaceState,
    target_mode: InterfaceMode,
    surface: Any | None = None,
) -> InterfaceTransition:
    tid = f"trn_{hashlib.sha256(f'{state.state_id}{target_mode.value}{_iso_now()}'.encode()).hexdigest()[:10]}"

    if state.mode == target_mode:
        return InterfaceTransition(
            transition_id=tid,
            surface_id=state.surface_id,
            from_mode=state.mode,
            to_mode=target_mode,
            status=InterfaceTransitionStatus.NOOP,
            reason="Already in target mode",
        )

    if not is_transition_supported(state.mode, target_mode, surface):
        return InterfaceTransition(
            transition_id=tid,
            surface_id=state.surface_id,
            from_mode=state.mode,
            to_mode=target_mode,
            status=InterfaceTransitionStatus.UNSUPPORTED,
            reason=f"Transition from {state.mode.value} to {target_mode.value} not supported",
        )

    return InterfaceTransition(
        transition_id=tid,
        surface_id=state.surface_id,
        from_mode=state.mode,
        to_mode=target_mode,
        status=InterfaceTransitionStatus.ALLOWED,
        reason=f"Transition from {state.mode.value} to {target_mode.value}",
    )
