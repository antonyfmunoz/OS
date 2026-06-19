"""Ambient Wake Runtime — Campaign 20.2.

Governs passive→active mode transitions. Wake-word detection
triggers COMMAND priority session. State machine:
DORMANT → PASSIVE_LISTENING → WAKE_DETECTED → COMMAND_ACTIVE → COOLDOWN.

Composes: WakeProducerRuntime + VoiceSessionManager + PresenceRuntime.

C20 substrate workstation subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────


class AmbientState(str, Enum):
    DORMANT = "dormant"
    PASSIVE_LISTENING = "passive_listening"
    WAKE_DETECTED = "wake_detected"
    COMMAND_ACTIVE = "command_active"
    COOLDOWN = "cooldown"


# Valid state transitions
_VALID_TRANSITIONS: dict[AmbientState, set[AmbientState]] = {
    AmbientState.DORMANT: {AmbientState.PASSIVE_LISTENING},
    AmbientState.PASSIVE_LISTENING: {
        AmbientState.WAKE_DETECTED,
        AmbientState.DORMANT,
    },
    AmbientState.WAKE_DETECTED: {
        AmbientState.COMMAND_ACTIVE,
        AmbientState.COOLDOWN,
    },
    AmbientState.COMMAND_ACTIVE: {AmbientState.COOLDOWN},
    AmbientState.COOLDOWN: {
        AmbientState.PASSIVE_LISTENING,
        AmbientState.DORMANT,
        AmbientState.WAKE_DETECTED,
    },
}

COOLDOWN_SECONDS = 5.0
COMMAND_TIMEOUT_SECONDS = 120.0


@dataclass
class WakeTransition:
    from_state: str = ""
    to_state: str = ""
    trigger: str = ""
    device_id: str = ""
    timestamp: float = 0.0
    session_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_state": self.from_state,
            "to_state": self.to_state,
            "trigger": self.trigger,
            "device_id": self.device_id,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
        }


@dataclass
class AmbientWakeSnapshot:
    state: str = AmbientState.DORMANT.value
    transitions_today: int = 0
    last_wake: float = 0.0
    active_command_session: str = ""
    listening_devices: list[str] = field(default_factory=list)
    recent_transitions: list[dict[str, Any]] = field(default_factory=list)
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "transitions_today": self.transitions_today,
            "last_wake": self.last_wake,
            "active_command_session": self.active_command_session,
            "listening_devices": self.listening_devices,
            "recent_transitions": self.recent_transitions,
            "generated_at": self.generated_at,
        }


# ── Runtime ──────────────────────────────────────────────────────────


class AmbientWakeRuntime:
    """Governs passive→active mode transitions.

    Composes WakeProducerRuntime (wake-word event bridge),
    VoiceSessionManager (creates COMMAND session on wake),
    and PresenceRuntime (device awareness).
    """

    def __init__(
        self,
        wake_producer_runtime: Any | None = None,
        voice_session_manager: Any | None = None,
        presence_runtime: Any | None = None,
    ) -> None:
        self._wake_producer_runtime = wake_producer_runtime
        self._voice_session_manager = voice_session_manager
        self._presence_runtime = presence_runtime
        self._state: AmbientState = AmbientState.DORMANT
        self._active_command_session: str = ""
        self._last_wake: float = 0.0
        self._transitions: list[WakeTransition] = []
        self._transitions_today: int = 0
        self._listening_devices: set[str] = set()
        self._last_state_change: float = time.time()
        self._max_transitions = 100

    # ── Lazy accessors ─────────────────────────────────────────────

    @property
    def wake_producer_runtime(self) -> Any | None:
        if self._wake_producer_runtime is None:
            try:
                from substrate.execution.bridge.wake_producer import (
                    WakeProducerRuntime,
                )
                self._wake_producer_runtime = WakeProducerRuntime()
            except Exception:
                logger.debug("WakeProducerRuntime unavailable")
        return self._wake_producer_runtime

    @property
    def voice_session_manager(self) -> Any | None:
        if self._voice_session_manager is None:
            try:
                from substrate.workstation.voice_session_manager import (
                    VoiceSessionManager,
                )
                self._voice_session_manager = VoiceSessionManager()
            except Exception:
                logger.debug("VoiceSessionManager unavailable")
        return self._voice_session_manager

    @property
    def presence_runtime(self) -> Any | None:
        if self._presence_runtime is None:
            try:
                from substrate.organism.presence_runtime import PresenceRuntime
                self._presence_runtime = PresenceRuntime()
            except Exception:
                logger.debug("PresenceRuntime unavailable")
        return self._presence_runtime

    # ── Public API ─────────────────────────────────────────────────

    def current_state(self) -> AmbientState:
        """Current ambient state with automatic timeout handling."""
        now = time.time()
        elapsed = now - self._last_state_change

        if (
            self._state == AmbientState.COMMAND_ACTIVE
            and elapsed > COMMAND_TIMEOUT_SECONDS
        ):
            self._transition(
                AmbientState.COOLDOWN,
                trigger="command_timeout",
                device_id="",
            )

        if (
            self._state == AmbientState.COOLDOWN
            and elapsed > COOLDOWN_SECONDS
        ):
            self._transition(
                AmbientState.PASSIVE_LISTENING,
                trigger="cooldown_expired",
                device_id="",
            )

        return self._state

    def activate(self) -> WakeTransition:
        """Activate ambient listening (DORMANT → PASSIVE_LISTENING)."""
        return self._transition(
            AmbientState.PASSIVE_LISTENING,
            trigger="activate",
            device_id="",
        )

    def deactivate(self) -> WakeTransition:
        """Deactivate ambient listening (any → DORMANT)."""
        if self._active_command_session and self.voice_session_manager is not None:
            try:
                self.voice_session_manager.end_session(
                    self._active_command_session,
                )
            except Exception:
                logger.debug("Failed to end command session on deactivate")
            self._active_command_session = ""

        self._state = AmbientState.DORMANT
        return self._record_transition(
            AmbientState.DORMANT,
            trigger="deactivate",
            device_id="",
        )

    def on_wake_detected(
        self, device_id: str, phrase: str = "",
    ) -> WakeTransition:
        """Handle wake-word detection.

        PASSIVE_LISTENING → WAKE_DETECTED → COMMAND_ACTIVE.
        Creates a COMMAND priority session via VoiceSessionManager.
        """
        _ = self.current_state()

        if self._state not in (
            AmbientState.PASSIVE_LISTENING,
            AmbientState.COOLDOWN,
        ):
            return WakeTransition(
                from_state=self._state.value,
                to_state=self._state.value,
                trigger=f"wake_ignored_in_{self._state.value}",
                device_id=device_id,
                timestamp=time.time(),
            )

        self._transition(
            AmbientState.WAKE_DETECTED,
            trigger=f"wake_word:{phrase}" if phrase else "wake_word",
            device_id=device_id,
        )

        session_id = ""
        if self.voice_session_manager is not None:
            try:
                from substrate.workstation.voice_ingress_runtime import (
                    VoiceIngressEvent,
                )
                event = VoiceIngressEvent(
                    source_type="ambient",
                    device_id=device_id,
                    activation_mode="command_mode",
                    raw_text=phrase,
                    timestamp=time.time(),
                    metadata={"wake_phrase": phrase},
                )
                session = self.voice_session_manager.start_session(event)
                session_id = session.session_id
            except Exception:
                logger.debug("Failed to create command session on wake")

        self._active_command_session = session_id
        self._last_wake = time.time()
        self._transitions_today += 1

        return self._transition(
            AmbientState.COMMAND_ACTIVE,
            trigger="command_session_started",
            device_id=device_id,
            session_id=session_id,
        )

    def on_command_complete(self, session_id: str = "") -> WakeTransition:
        """Handle command completion — enter cooldown."""
        if self._state != AmbientState.COMMAND_ACTIVE:
            return WakeTransition(
                from_state=self._state.value,
                to_state=self._state.value,
                trigger="command_complete_ignored",
                device_id="",
                timestamp=time.time(),
                session_id=session_id,
            )

        if session_id and self.voice_session_manager is not None:
            try:
                self.voice_session_manager.end_session(session_id)
            except Exception:
                logger.debug("Failed to end command session")

        self._active_command_session = ""
        return self._transition(
            AmbientState.COOLDOWN,
            trigger="command_complete",
            device_id="",
            session_id=session_id,
        )

    def on_timeout(self) -> WakeTransition:
        """Handle timeout — move to appropriate next state."""
        _ = self.current_state()
        return WakeTransition(
            from_state=self._state.value,
            to_state=self._state.value,
            trigger="timeout_check",
            device_id="",
            timestamp=time.time(),
        )

    def listening_devices(self) -> list[str]:
        """Return devices currently in ambient listening mode."""
        if self._state in (
            AmbientState.PASSIVE_LISTENING,
            AmbientState.COMMAND_ACTIVE,
        ):
            if self.presence_runtime is not None:
                try:
                    snap = self.presence_runtime.snapshot()
                    if hasattr(snap, "online_devices"):
                        devices = snap.online_devices
                        return [
                            d.get("device_id", "") if isinstance(d, dict) else str(d)
                            for d in devices
                        ]
                except Exception:
                    logger.debug("Failed to get listening devices")
            return list(self._listening_devices) if self._listening_devices else ["local"]
        return []

    def add_listening_device(self, device_id: str) -> None:
        self._listening_devices.add(device_id)

    def remove_listening_device(self, device_id: str) -> None:
        self._listening_devices.discard(device_id)

    def snapshot(self) -> AmbientWakeSnapshot:
        """Current state snapshot."""
        _ = self.current_state()
        return AmbientWakeSnapshot(
            state=self._state.value,
            transitions_today=self._transitions_today,
            last_wake=self._last_wake,
            active_command_session=self._active_command_session,
            listening_devices=self.listening_devices(),
            recent_transitions=[
                t.to_dict() for t in self._transitions[-10:]
            ],
            generated_at=time.time(),
        )

    # ── Internal ───────────────────────────────────────────────────

    def _transition(
        self,
        to_state: AmbientState,
        trigger: str,
        device_id: str,
        session_id: str = "",
    ) -> WakeTransition:
        """Execute a state transition if valid."""
        valid_targets = _VALID_TRANSITIONS.get(self._state, set())
        if to_state not in valid_targets and to_state != self._state:
            logger.debug(
                "Invalid transition %s → %s (trigger: %s)",
                self._state.value, to_state.value, trigger,
            )
            return WakeTransition(
                from_state=self._state.value,
                to_state=self._state.value,
                trigger=f"blocked:{trigger}",
                device_id=device_id,
                timestamp=time.time(),
                session_id=session_id,
            )

        prev = self._state
        self._state = to_state
        self._last_state_change = time.time()
        return self._record_transition(
            to_state, trigger=trigger, device_id=device_id,
            session_id=session_id, from_state=prev,
        )

    def _record_transition(
        self,
        to_state: AmbientState,
        trigger: str,
        device_id: str,
        session_id: str = "",
        from_state: AmbientState | None = None,
    ) -> WakeTransition:
        t = WakeTransition(
            from_state=(from_state or self._state).value,
            to_state=to_state.value,
            trigger=trigger,
            device_id=device_id,
            timestamp=time.time(),
            session_id=session_id,
        )
        self._transitions.append(t)
        if len(self._transitions) > self._max_transitions:
            self._transitions = self._transitions[-self._max_transitions:]
        return t
