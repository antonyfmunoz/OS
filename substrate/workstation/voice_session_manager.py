"""Voice Session Manager — Campaign 20.1.

Unified multi-surface session lifecycle. One operator can have multiple
simultaneous voice sessions (conference transcription + ambient Jarvis).
COMMAND > CONVERSATION > PASSIVE — deterministic conflict resolution.

Composes: VoiceSessionRuntime + VoiceIngressRuntime + SessionRuntime.

C20 substrate workstation subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────


class VoiceSessionType(str, Enum):
    OPERATOR_CHAT = "operator_chat"
    CONFERENCE_TRANSCRIPTION = "conference_transcription"
    BROADCAST_CAPTURE = "broadcast_capture"
    AMBIENT_LISTENING = "ambient_listening"
    SYSTEM_MONITOR = "system_monitor"


class VoiceSessionPriority(str, Enum):
    COMMAND = "command"
    CONVERSATION = "conversation"
    PASSIVE = "passive"

    @property
    def rank(self) -> int:
        return {"command": 3, "conversation": 2, "passive": 1}.get(self.value, 0)


@dataclass
class ManagedVoiceSession:
    session_id: str = ""
    session_type: str = VoiceSessionType.OPERATOR_CHAT.value
    source_type: str = ""
    activation_mode: str = ""
    priority: str = VoiceSessionPriority.CONVERSATION.value
    status: str = "active"
    device_id: str = ""
    speaker_ids: list[str] = field(default_factory=list)
    started_at: float = 0.0
    last_activity_at: float = 0.0
    turn_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "session_type": self.session_type,
            "source_type": self.source_type,
            "activation_mode": self.activation_mode,
            "priority": self.priority,
            "status": self.status,
            "device_id": self.device_id,
            "speaker_ids": self.speaker_ids,
            "started_at": self.started_at,
            "last_activity_at": self.last_activity_at,
            "turn_count": self.turn_count,
            "metadata": self.metadata,
        }


@dataclass
class SessionConflictResolution:
    conflicting_sessions: list[str] = field(default_factory=list)
    resolution: str = ""
    rationale: str = ""
    winner_id: str = ""
    demoted_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflicting_sessions": self.conflicting_sessions,
            "resolution": self.resolution,
            "rationale": self.rationale,
            "winner_id": self.winner_id,
            "demoted_ids": self.demoted_ids,
        }


@dataclass
class VoiceSessionManagerSnapshot:
    active_sessions: list[dict[str, Any]] = field(default_factory=list)
    total_sessions: int = 0
    sessions_by_type: dict[str, int] = field(default_factory=dict)
    sessions_by_priority: dict[str, int] = field(default_factory=dict)
    conflict_count: int = 0
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_sessions": self.active_sessions,
            "total_sessions": self.total_sessions,
            "sessions_by_type": self.sessions_by_type,
            "sessions_by_priority": self.sessions_by_priority,
            "conflict_count": self.conflict_count,
            "generated_at": self.generated_at,
        }


# ── Source → session type mapping ──────────────────────────────────────

_SOURCE_TO_SESSION_TYPE: dict[str, VoiceSessionType] = {
    "right_rail": VoiceSessionType.OPERATOR_CHAT,
    "conference": VoiceSessionType.CONFERENCE_TRANSCRIPTION,
    "discord": VoiceSessionType.BROADCAST_CAPTURE,
    "system_audio": VoiceSessionType.SYSTEM_MONITOR,
    "ambient": VoiceSessionType.AMBIENT_LISTENING,
}

_SESSION_TYPE_PRIORITY: dict[VoiceSessionType, VoiceSessionPriority] = {
    VoiceSessionType.OPERATOR_CHAT: VoiceSessionPriority.COMMAND,
    VoiceSessionType.CONFERENCE_TRANSCRIPTION: VoiceSessionPriority.CONVERSATION,
    VoiceSessionType.BROADCAST_CAPTURE: VoiceSessionPriority.PASSIVE,
    VoiceSessionType.AMBIENT_LISTENING: VoiceSessionPriority.PASSIVE,
    VoiceSessionType.SYSTEM_MONITOR: VoiceSessionPriority.PASSIVE,
}

# Command mode always gets COMMAND priority regardless of source
_COMMAND_ACTIVATION_MODES = {"command_mode", "push_to_talk"}


# ── Runtime ──────────────────────────────────────────────────────────


class VoiceSessionManager:
    """Unified multi-surface voice session lifecycle manager.

    Composes VoiceSessionRuntime (single-session lifecycle),
    VoiceIngressRuntime (source classification), and SessionRuntime
    (operator session binding).

    Multiple concurrent sessions are supported. Conflict resolution
    is deterministic: COMMAND > CONVERSATION > PASSIVE.
    """

    def __init__(
        self,
        voice_session_runtime: Any | None = None,
        voice_ingress_runtime: Any | None = None,
        session_runtime: Any | None = None,
    ) -> None:
        self._voice_session_runtime = voice_session_runtime
        self._voice_ingress_runtime = voice_ingress_runtime
        self._session_runtime = session_runtime
        self._managed_sessions: dict[str, ManagedVoiceSession] = {}
        self._conflict_count: int = 0

    # ── Lazy accessors ─────────────────────────────────────────────

    @property
    def voice_session_runtime(self) -> Any | None:
        if self._voice_session_runtime is None:
            try:
                from substrate.execution.bridge.voice_session import (
                    VoiceSessionRuntime,
                )
                self._voice_session_runtime = VoiceSessionRuntime()
            except Exception:
                logger.debug("VoiceSessionRuntime unavailable")
        return self._voice_session_runtime

    @property
    def voice_ingress_runtime(self) -> Any | None:
        if self._voice_ingress_runtime is None:
            try:
                from substrate.workstation.voice_ingress_runtime import (
                    VoiceIngressRuntime,
                )
                self._voice_ingress_runtime = VoiceIngressRuntime()
            except Exception:
                logger.debug("VoiceIngressRuntime unavailable")
        return self._voice_ingress_runtime

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

    def start_session(
        self, ingress_event: Any,
    ) -> ManagedVoiceSession:
        """Start a managed voice session from an ingress event.

        Determines session type from source, assigns priority,
        checks for conflicts with existing sessions.
        """
        if hasattr(ingress_event, "to_dict"):
            ev = ingress_event
        else:
            ev = type("Ev", (), ingress_event)()

        source_type = getattr(ev, "source_type", "right_rail")
        activation_mode = getattr(ev, "activation_mode", "")
        device_id = getattr(ev, "device_id", "")
        speaker_id = getattr(ev, "speaker_id", "")

        session_type = _SOURCE_TO_SESSION_TYPE.get(
            source_type, VoiceSessionType.OPERATOR_CHAT,
        )

        if activation_mode in _COMMAND_ACTIVATION_MODES:
            priority = VoiceSessionPriority.COMMAND
        else:
            priority = _SESSION_TYPE_PRIORITY.get(
                session_type, VoiceSessionPriority.CONVERSATION,
            )

        session_id = f"vms_{uuid.uuid4().hex[:12]}"
        now = time.time()

        managed = ManagedVoiceSession(
            session_id=session_id,
            session_type=session_type.value,
            source_type=source_type,
            activation_mode=activation_mode,
            priority=priority.value,
            status="active",
            device_id=device_id,
            speaker_ids=[speaker_id] if speaker_id else [],
            started_at=now,
            last_activity_at=now,
            turn_count=0,
            metadata=getattr(ev, "metadata", {}),
        )

        self._check_conflicts(managed)
        self._managed_sessions[session_id] = managed
        return managed

    def end_session(self, session_id: str) -> bool:
        """End a managed voice session."""
        session = self._managed_sessions.get(session_id)
        if session is None:
            return False
        session.status = "ended"
        return True

    def active_sessions(self) -> list[ManagedVoiceSession]:
        """Return all currently active managed sessions."""
        return [
            s for s in self._managed_sessions.values()
            if s.status == "active"
        ]

    def get_session(self, session_id: str) -> ManagedVoiceSession | None:
        return self._managed_sessions.get(session_id)

    def resolve_conflict(
        self, session_a_id: str, session_b_id: str,
    ) -> SessionConflictResolution:
        """Deterministic conflict resolution: COMMAND > CONVERSATION > PASSIVE."""
        a = self._managed_sessions.get(session_a_id)
        b = self._managed_sessions.get(session_b_id)

        if a is None or b is None:
            return SessionConflictResolution(
                conflicting_sessions=[session_a_id, session_b_id],
                resolution="no_conflict",
                rationale="One or both sessions not found",
            )

        a_priority = VoiceSessionPriority(a.priority)
        b_priority = VoiceSessionPriority(b.priority)

        if a_priority.rank > b_priority.rank:
            winner, loser = a, b
        elif b_priority.rank > a_priority.rank:
            winner, loser = b, a
        else:
            # Same priority: newer session wins
            winner = a if a.started_at >= b.started_at else b
            loser = b if winner is a else a

        return SessionConflictResolution(
            conflicting_sessions=[session_a_id, session_b_id],
            resolution="priority_override",
            rationale=f"{winner.priority} ({winner.session_type}) overrides {loser.priority} ({loser.session_type})",
            winner_id=winner.session_id,
            demoted_ids=[loser.session_id],
        )

    def route_utterance(
        self, session_id: str, text: str,
    ) -> dict[str, Any]:
        """Route an utterance through the appropriate session.

        Returns routing metadata: session type, priority, source type.
        Does not execute the query — that's VoiceOperationsRuntime.
        """
        session = self._managed_sessions.get(session_id)
        if session is None:
            return {"error": "session_not_found", "session_id": session_id}

        session.last_activity_at = time.time()
        session.turn_count += 1

        return {
            "session_id": session_id,
            "session_type": session.session_type,
            "priority": session.priority,
            "source_type": session.source_type,
            "activation_mode": session.activation_mode,
            "device_id": session.device_id,
            "turn_count": session.turn_count,
            "text": text,
        }

    def snapshot(self) -> VoiceSessionManagerSnapshot:
        """Current state snapshot."""
        active = self.active_sessions()
        by_type: dict[str, int] = {}
        by_priority: dict[str, int] = {}
        for s in active:
            by_type[s.session_type] = by_type.get(s.session_type, 0) + 1
            by_priority[s.priority] = by_priority.get(s.priority, 0) + 1

        return VoiceSessionManagerSnapshot(
            active_sessions=[s.to_dict() for s in active],
            total_sessions=len(self._managed_sessions),
            sessions_by_type=by_type,
            sessions_by_priority=by_priority,
            conflict_count=self._conflict_count,
            generated_at=time.time(),
        )

    # ── Internal ───────────────────────────────────────────────────

    def _check_conflicts(self, new_session: ManagedVoiceSession) -> None:
        """Check for and resolve conflicts with existing active sessions.

        Same-device, same-source conflicts are resolved by priority.
        Different-source sessions coexist (conference + ambient is valid).
        """
        active = self.active_sessions()
        for existing in active:
            if (
                existing.device_id == new_session.device_id
                and existing.source_type == new_session.source_type
                and existing.status == "active"
            ):
                new_priority = VoiceSessionPriority(new_session.priority)
                existing_priority = VoiceSessionPriority(existing.priority)
                if new_priority.rank >= existing_priority.rank:
                    existing.status = "superseded"
                    self._conflict_count += 1
