"""Activation signal and presence session for Jarvis workstation.

Defines the typed ActivationSignal contract and PresenceSession model.
Activation sources include manual, hotkey, typed command, push-to-talk,
Discord, and planned-but-unavailable sources (wake word, clap, mobile).
"""

from __future__ import annotations

import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ActivationSource(str, Enum):
    MANUAL_COCKPIT_OPEN = "manual_cockpit_open"
    HOTKEY = "hotkey"
    TYPED_COMMAND = "typed_command"
    PUSH_TO_TALK_VOICE = "push_to_talk_voice"
    DISCORD_REMOTE_COMMAND = "discord_remote_command"
    WAKE_WORD_UNAVAILABLE = "wake_word_unavailable"
    CLAP_UNAVAILABLE = "clap_unavailable"
    MOBILE_REMOTE_UNAVAILABLE = "mobile_remote_command_unavailable"


class ActivationCapabilityStatus(str, Enum):
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    NOT_IMPLEMENTED = "not_implemented"


@dataclass
class ActivationSignal:
    """Typed activation event for Jarvis workstation."""

    source: str
    activation_id: str = ""
    device: str = ""
    node: str = ""
    timestamp: str = ""
    user_id: str = ""
    session_id: str = ""
    lifecycle_mode: str = ""
    profile_mode: str = ""
    continuity_state: str = ""
    raw_payload: str = ""
    confidence: float = 1.0
    degraded_reason: str = ""

    def __post_init__(self) -> None:
        if not self.activation_id:
            self.activation_id = f"act_{uuid.uuid4().hex[:12]}"
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.node:
            self.node = os.uname().nodename
        if not self.device:
            self.device = os.uname().sysname

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActivationSignal:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class PresenceCapability:
    """Single activation capability with status and blocker info."""

    name: str
    source: str
    status: str = ActivationCapabilityStatus.AVAILABLE.value
    blocker: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def get_activation_capabilities() -> list[PresenceCapability]:
    """Return truthful capability status for all activation methods."""
    caps = [
        PresenceCapability(
            name="Manual Cockpit Open",
            source=ActivationSource.MANUAL_COCKPIT_OPEN.value,
            status=ActivationCapabilityStatus.AVAILABLE.value,
        ),
        PresenceCapability(
            name="Hotkey (Ctrl+Alt+J)",
            source=ActivationSource.HOTKEY.value,
            status=ActivationCapabilityStatus.AVAILABLE.value
            if os.environ.get("ELECTRON_RUN_AS_NODE") or os.environ.get("DISPLAY")
            else ActivationCapabilityStatus.DEGRADED.value,
            blocker="" if os.environ.get("ELECTRON_RUN_AS_NODE") or os.environ.get("DISPLAY")
            else "Global shortcut requires Electron desktop runtime or display server",
        ),
        PresenceCapability(
            name="Typed Command",
            source=ActivationSource.TYPED_COMMAND.value,
            status=ActivationCapabilityStatus.AVAILABLE.value,
        ),
        PresenceCapability(
            name="Push-to-Talk Voice",
            source=ActivationSource.PUSH_TO_TALK_VOICE.value,
            status=_detect_stt_status(),
            blocker=_detect_stt_blocker(),
        ),
        PresenceCapability(
            name="Discord Remote Command",
            source=ActivationSource.DISCORD_REMOTE_COMMAND.value,
            status=ActivationCapabilityStatus.AVAILABLE.value
            if os.environ.get("DISCORD_TOKEN")
            else ActivationCapabilityStatus.DEGRADED.value,
            blocker="" if os.environ.get("DISCORD_TOKEN")
            else "DISCORD_TOKEN not configured",
        ),
        PresenceCapability(
            name="Wake Word",
            source=ActivationSource.WAKE_WORD_UNAVAILABLE.value,
            status=ActivationCapabilityStatus.NOT_IMPLEMENTED.value,
            blocker="Wake word detection requires trained model — not implemented in this phase",
        ),
        PresenceCapability(
            name="Clap Detection",
            source=ActivationSource.CLAP_UNAVAILABLE.value,
            status=ActivationCapabilityStatus.NOT_IMPLEMENTED.value,
            blocker="Clap detection model not trained — not implemented in this phase",
        ),
        PresenceCapability(
            name="Mobile Remote Command",
            source=ActivationSource.MOBILE_REMOTE_UNAVAILABLE.value,
            status=ActivationCapabilityStatus.NOT_IMPLEMENTED.value,
            blocker="Dedicated mobile app not built — use Discord mobile as workaround",
        ),
    ]
    return caps


def _detect_stt_status() -> str:
    try:
        import importlib
        importlib.import_module("groq")
        if os.environ.get("GROQ_API_KEY"):
            return ActivationCapabilityStatus.AVAILABLE.value
    except ImportError:
        pass
    try:
        import importlib
        importlib.import_module("faster_whisper")
        return ActivationCapabilityStatus.DEGRADED.value
    except ImportError:
        pass
    return ActivationCapabilityStatus.UNAVAILABLE.value


def _detect_stt_blocker() -> str:
    try:
        import importlib
        importlib.import_module("groq")
        if os.environ.get("GROQ_API_KEY"):
            return ""
    except ImportError:
        pass
    try:
        import importlib
        importlib.import_module("faster_whisper")
        return "Groq STT unavailable — using local faster-whisper fallback"
    except ImportError:
        pass
    return "No STT engine available — install groq SDK or faster-whisper"


@dataclass
class PresenceSession:
    """Active presence session representing a Jarvis activation."""

    session_id: str = ""
    activation: ActivationSignal | None = None
    profile: dict[str, Any] = field(default_factory=dict)
    continuity_state: str = ""
    lifecycle_mode: str = ""
    profile_modes: list[str] = field(default_factory=list)
    pending_approvals: list[dict[str, Any]] = field(default_factory=list)
    resume_summary: str = ""
    next_actions: list[str] = field(default_factory=list)
    active_node: str = ""
    active_environment: str = ""
    capabilities: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.session_id:
            self.session_id = f"ps_{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.activation:
            d["activation"] = self.activation.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PresenceSession:
        act_data = data.pop("activation", None)
        session = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        if act_data and isinstance(act_data, dict):
            session.activation = ActivationSignal.from_dict(act_data)
        return session
