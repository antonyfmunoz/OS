"""Voice Ingress Runtime — Campaign 20.0.

Classifies and tags every audio event with source, device, speaker,
channel context, and activation mode before it reaches processing.

Composes: PresenceRuntime + VoiceRouteResolver + SessionRuntime.
All classification is deterministic — regex + source metadata.

C20 substrate workstation subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────


class VoiceSourceType(str, Enum):
    RIGHT_RAIL = "right_rail"
    CONFERENCE = "conference"
    DISCORD = "discord"
    SYSTEM_AUDIO = "system_audio"
    AMBIENT = "ambient"


class ActivationMode(str, Enum):
    PUSH_TO_TALK = "push_to_talk"
    WAKE_WORD = "wake_word"
    ALWAYS_LISTEN_PASSIVE = "always_listen_passive"
    CONFERENCE_LISTENING = "conference_listening"
    BROADCAST_TRANSCRIPTION = "broadcast_transcription"
    COMMAND_MODE = "command_mode"


class VoiceChannelContext(str, Enum):
    OPERATOR_DIRECT = "operator_direct"
    MEETING = "meeting"
    BROADCAST = "broadcast"
    BACKGROUND = "background"
    SYSTEM = "system"


class VoicePermissionScope(str, Enum):
    FULL = "full"
    QUERY_ONLY = "query_only"
    TRANSCRIBE_ONLY = "transcribe_only"
    MONITOR_ONLY = "monitor_only"


@dataclass
class VoiceIngressEvent:
    source_type: str = VoiceSourceType.RIGHT_RAIL.value
    device_id: str = ""
    session_id: str = ""
    speaker_id: str = ""
    channel_context: str = VoiceChannelContext.OPERATOR_DIRECT.value
    activation_mode: str = ""
    permission_scope: str = VoicePermissionScope.FULL.value
    raw_text: str = ""
    confidence: float = 1.0
    timestamp: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "device_id": self.device_id,
            "session_id": self.session_id,
            "speaker_id": self.speaker_id,
            "channel_context": self.channel_context,
            "activation_mode": self.activation_mode,
            "permission_scope": self.permission_scope,
            "raw_text": self.raw_text,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class VoiceIngressSnapshot:
    active_sources: list[dict[str, Any]] = field(default_factory=list)
    event_counts_by_type: dict[str, int] = field(default_factory=dict)
    recent_events: list[dict[str, Any]] = field(default_factory=list)
    health: str = "idle"
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_sources": self.active_sources,
            "event_counts_by_type": self.event_counts_by_type,
            "recent_events": self.recent_events,
            "health": self.health,
            "generated_at": self.generated_at,
        }


# ── Source detection patterns ──────────────────────────────────────────

_DISCORD_PATTERNS = re.compile(
    r"\b(discord|guild|channel_id|voice_channel)\b", re.IGNORECASE,
)
_CONFERENCE_PATTERNS = re.compile(
    r"\b(conference|meeting|livekit|room|call)\b", re.IGNORECASE,
)
_SYSTEM_AUDIO_PATTERNS = re.compile(
    r"\b(system_audio|loopback|stream_capture|desktop_audio)\b", re.IGNORECASE,
)
_AMBIENT_PATTERNS = re.compile(
    r"\b(ambient|wake_word|always_listen|background_mic)\b", re.IGNORECASE,
)

# Channel context detection
_MEETING_PATTERNS = re.compile(
    r"\b(meeting|standup|sync|call|conference)\b", re.IGNORECASE,
)
_BROADCAST_PATTERNS = re.compile(
    r"\b(broadcast|announcement|stream|live)\b", re.IGNORECASE,
)


# ── Runtime ──────────────────────────────────────────────────────────


class VoiceIngressRuntime:
    """Classifies raw audio events into structured VoiceIngressEvent.

    Composes PresenceRuntime (device binding), VoiceRouteResolver
    (target node + audio device), and SessionRuntime (operator context).
    All classification is deterministic — regex + source metadata.
    """

    def __init__(
        self,
        presence_runtime: Any | None = None,
        voice_route_resolver: Any | None = None,
        session_runtime: Any | None = None,
    ) -> None:
        self._presence_runtime = presence_runtime
        self._voice_route_resolver = voice_route_resolver
        self._session_runtime = session_runtime
        self._recent_events: list[VoiceIngressEvent] = []
        self._event_counts: dict[str, int] = {}
        self._max_recent = 50

    # ── Lazy accessors ─────────────────────────────────────────────

    @property
    def presence_runtime(self) -> Any | None:
        if self._presence_runtime is None:
            try:
                from substrate.organism.presence_runtime import PresenceRuntime
                self._presence_runtime = PresenceRuntime()
            except Exception:
                logger.debug("PresenceRuntime unavailable")
        return self._presence_runtime

    @property
    def session_runtime(self) -> Any | None:
        if self._session_runtime is None:
            try:
                from substrate.organism.session_runtime import SessionRuntime
                self._session_runtime = SessionRuntime()
            except Exception:
                logger.debug("SessionRuntime unavailable")
        return self._session_runtime

    # ── Public API ─────────────────────────────────────────────────

    def classify(self, raw_event: dict[str, Any]) -> VoiceIngressEvent:
        """Classify a raw audio event into a structured VoiceIngressEvent.

        Classification is deterministic:
        1. Source type from explicit field or regex on metadata
        2. Activation mode from source type + metadata
        3. Channel context from metadata patterns
        4. Device binding from PresenceRuntime
        5. Permission scope from source type
        """
        source_type = self._detect_source_type(raw_event)
        activation_mode = self._detect_activation_mode(raw_event, source_type)
        channel_context = self._detect_channel_context(raw_event, source_type)
        permission_scope = self._detect_permission_scope(source_type)

        device_id = str(raw_event.get("device_id", ""))
        if not device_id and self.presence_runtime is not None:
            device_id = self._safe_call(
                lambda: self.presence_runtime.current_device_id(),
                "",
            )

        event = VoiceIngressEvent(
            source_type=source_type.value,
            device_id=device_id,
            session_id=str(raw_event.get("session_id", "")),
            speaker_id=str(raw_event.get("speaker_id", raw_event.get("user_id", ""))),
            channel_context=channel_context.value,
            activation_mode=activation_mode.value,
            permission_scope=permission_scope.value,
            raw_text=str(raw_event.get("text", raw_event.get("transcript", ""))),
            confidence=float(raw_event.get("confidence", 1.0)),
            timestamp=float(raw_event.get("timestamp", time.time())),
            metadata={
                k: v for k, v in raw_event.items()
                if k not in {
                    "text", "transcript", "device_id", "session_id",
                    "speaker_id", "user_id", "confidence", "timestamp",
                    "source", "source_type",
                }
            },
        )

        self._record_event(event)
        return event

    def active_sources(self) -> list[dict[str, Any]]:
        """Return currently active voice source types with counts."""
        sources: dict[str, int] = {}
        cutoff = time.time() - 300
        for ev in self._recent_events:
            if ev.timestamp >= cutoff:
                sources[ev.source_type] = sources.get(ev.source_type, 0) + 1
        return [
            {"source_type": st, "active_count": c}
            for st, c in sorted(sources.items())
        ]

    def snapshot(self) -> VoiceIngressSnapshot:
        """Current state snapshot for cockpit/API consumption."""
        active = self.active_sources()
        health = "active" if active else "idle"
        return VoiceIngressSnapshot(
            active_sources=active,
            event_counts_by_type=dict(self._event_counts),
            recent_events=[e.to_dict() for e in self._recent_events[-10:]],
            health=health,
            generated_at=time.time(),
        )

    def summary(self) -> dict[str, Any]:
        snap = self.snapshot()
        return {
            "health": snap.health,
            "active_source_count": len(snap.active_sources),
            "total_events": sum(self._event_counts.values()),
            "event_counts_by_type": snap.event_counts_by_type,
        }

    # ── Classification helpers ─────────────────────────────────────

    def _detect_source_type(self, raw: dict[str, Any]) -> VoiceSourceType:
        explicit = str(raw.get("source_type", raw.get("source", ""))).lower()
        if explicit:
            for st in VoiceSourceType:
                if st.value == explicit:
                    return st

        meta_str = str(raw)
        if _DISCORD_PATTERNS.search(meta_str):
            return VoiceSourceType.DISCORD
        if _CONFERENCE_PATTERNS.search(meta_str):
            return VoiceSourceType.CONFERENCE
        if _SYSTEM_AUDIO_PATTERNS.search(meta_str):
            return VoiceSourceType.SYSTEM_AUDIO
        if _AMBIENT_PATTERNS.search(meta_str):
            return VoiceSourceType.AMBIENT
        return VoiceSourceType.RIGHT_RAIL

    def _detect_activation_mode(
        self, raw: dict[str, Any], source: VoiceSourceType,
    ) -> ActivationMode:
        explicit = str(raw.get("activation_mode", "")).lower()
        if explicit:
            for am in ActivationMode:
                if am.value == explicit:
                    return am

        mode_map: dict[VoiceSourceType, ActivationMode] = {
            VoiceSourceType.RIGHT_RAIL: ActivationMode.PUSH_TO_TALK,
            VoiceSourceType.CONFERENCE: ActivationMode.CONFERENCE_LISTENING,
            VoiceSourceType.DISCORD: ActivationMode.BROADCAST_TRANSCRIPTION,
            VoiceSourceType.SYSTEM_AUDIO: ActivationMode.ALWAYS_LISTEN_PASSIVE,
            VoiceSourceType.AMBIENT: ActivationMode.WAKE_WORD,
        }

        if raw.get("wake_word") or raw.get("wake_event_id"):
            return ActivationMode.WAKE_WORD
        if raw.get("command_mode"):
            return ActivationMode.COMMAND_MODE

        return mode_map.get(source, ActivationMode.PUSH_TO_TALK)

    def _detect_channel_context(
        self, raw: dict[str, Any], source: VoiceSourceType,
    ) -> VoiceChannelContext:
        explicit = str(raw.get("channel_context", "")).lower()
        if explicit:
            for cc in VoiceChannelContext:
                if cc.value == explicit:
                    return cc

        if source == VoiceSourceType.CONFERENCE:
            return VoiceChannelContext.MEETING
        if source == VoiceSourceType.DISCORD:
            meta_str = str(raw)
            if _BROADCAST_PATTERNS.search(meta_str):
                return VoiceChannelContext.BROADCAST
            return VoiceChannelContext.MEETING
        if source == VoiceSourceType.SYSTEM_AUDIO:
            return VoiceChannelContext.BACKGROUND
        if source == VoiceSourceType.AMBIENT:
            return VoiceChannelContext.BACKGROUND
        return VoiceChannelContext.OPERATOR_DIRECT

    def _detect_permission_scope(
        self, source: VoiceSourceType,
    ) -> VoicePermissionScope:
        scope_map: dict[VoiceSourceType, VoicePermissionScope] = {
            VoiceSourceType.RIGHT_RAIL: VoicePermissionScope.FULL,
            VoiceSourceType.CONFERENCE: VoicePermissionScope.TRANSCRIBE_ONLY,
            VoiceSourceType.DISCORD: VoicePermissionScope.TRANSCRIBE_ONLY,
            VoiceSourceType.SYSTEM_AUDIO: VoicePermissionScope.MONITOR_ONLY,
            VoiceSourceType.AMBIENT: VoicePermissionScope.QUERY_ONLY,
        }
        return scope_map.get(source, VoicePermissionScope.FULL)

    # ── Internal ───────────────────────────────────────────────────

    def _record_event(self, event: VoiceIngressEvent) -> None:
        self._recent_events.append(event)
        if len(self._recent_events) > self._max_recent:
            self._recent_events = self._recent_events[-self._max_recent:]
        self._event_counts[event.source_type] = (
            self._event_counts.get(event.source_type, 0) + 1
        )

    @staticmethod
    def _safe_call(fn: Any, default: Any = None) -> Any:
        try:
            return fn()
        except Exception:
            return default
