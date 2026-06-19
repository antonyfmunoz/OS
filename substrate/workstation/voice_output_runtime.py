"""Voice Output Runtime — Campaign 20.3.

Routes responses to the correct output surface. Static mapping —
no intelligence. RIGHT_RAIL → SPOKEN_REPLY + RIGHT_RAIL_TEXT.
Conference → CONFERENCE_LOG. Ambient command → SPOKEN_REPLY + RIGHT_RAIL_TEXT + SILENT_LOG.

Composes: VoiceSessionManager + VoiceRouteResolver + VoiceIngressRuntime.

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


class VoiceOutputTarget(str, Enum):
    SPOKEN_REPLY = "spoken_reply"
    RIGHT_RAIL_TEXT = "right_rail_text"
    CONFERENCE_LOG = "conference_log"
    DISCORD_VOICE = "discord_voice"
    SILENT_LOG = "silent_log"
    NOTIFICATION = "notification"


@dataclass
class OutputRoutingDecision:
    targets: list[str] = field(default_factory=list)
    rationale: str = ""
    session_id: str = ""
    source_type: str = ""
    session_type: str = ""
    timestamp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "targets": self.targets,
            "rationale": self.rationale,
            "session_id": self.session_id,
            "source_type": self.source_type,
            "session_type": self.session_type,
            "timestamp": self.timestamp,
        }


@dataclass
class VoiceOutputSnapshot:
    recent_decisions: list[dict[str, Any]] = field(default_factory=list)
    outputs_by_target: dict[str, int] = field(default_factory=dict)
    health: str = "idle"
    total_routed: int = 0
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "recent_decisions": self.recent_decisions,
            "outputs_by_target": self.outputs_by_target,
            "health": self.health,
            "total_routed": self.total_routed,
            "generated_at": self.generated_at,
        }


# ── Static output routing map ─────────────────────────────────────────
# Source type → output targets. Deterministic. No intelligence.

_SOURCE_OUTPUT_MAP: dict[str, list[VoiceOutputTarget]] = {
    "right_rail": [
        VoiceOutputTarget.SPOKEN_REPLY,
        VoiceOutputTarget.RIGHT_RAIL_TEXT,
    ],
    "conference": [
        VoiceOutputTarget.CONFERENCE_LOG,
    ],
    "discord": [
        VoiceOutputTarget.DISCORD_VOICE,
        VoiceOutputTarget.SILENT_LOG,
    ],
    "system_audio": [
        VoiceOutputTarget.SILENT_LOG,
    ],
    "ambient": [
        VoiceOutputTarget.SPOKEN_REPLY,
        VoiceOutputTarget.RIGHT_RAIL_TEXT,
        VoiceOutputTarget.SILENT_LOG,
    ],
}

# Session type overrides (more specific than source type)
_SESSION_TYPE_OUTPUT_MAP: dict[str, list[VoiceOutputTarget]] = {
    "operator_chat": [
        VoiceOutputTarget.SPOKEN_REPLY,
        VoiceOutputTarget.RIGHT_RAIL_TEXT,
    ],
    "conference_transcription": [
        VoiceOutputTarget.CONFERENCE_LOG,
    ],
    "broadcast_capture": [
        VoiceOutputTarget.SILENT_LOG,
        VoiceOutputTarget.NOTIFICATION,
    ],
    "ambient_listening": [
        VoiceOutputTarget.SPOKEN_REPLY,
        VoiceOutputTarget.RIGHT_RAIL_TEXT,
        VoiceOutputTarget.SILENT_LOG,
    ],
    "system_monitor": [
        VoiceOutputTarget.SILENT_LOG,
    ],
}


# ── Runtime ──────────────────────────────────────────────────────────


class VoiceOutputRuntime:
    """Routes voice responses to correct output surfaces.

    Composes VoiceSessionManager (session type → output targets),
    VoiceRouteResolver (audio device routing), and VoiceIngressRuntime
    (source classification). All routing is deterministic.
    """

    def __init__(
        self,
        voice_session_manager: Any | None = None,
        voice_route_resolver: Any | None = None,
        voice_ingress_runtime: Any | None = None,
    ) -> None:
        self._voice_session_manager = voice_session_manager
        self._voice_route_resolver = voice_route_resolver
        self._voice_ingress_runtime = voice_ingress_runtime
        self._recent_decisions: list[OutputRoutingDecision] = []
        self._outputs_by_target: dict[str, int] = {}
        self._total_routed: int = 0
        self._max_recent = 50

    # ── Lazy accessors ─────────────────────────────────────────────

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

    # ── Public API ─────────────────────────────────────────────────

    def route_output(
        self,
        session_id: str,
        response_text: str,
        source_type: str = "",
    ) -> OutputRoutingDecision:
        """Route a response to the correct output targets.

        Priority: session type override → source type → default.
        """
        session_type = ""
        resolved_source = source_type

        if session_id and self.voice_session_manager is not None:
            try:
                session = self.voice_session_manager.get_session(session_id)
                if session is not None:
                    session_type = session.session_type
                    if not resolved_source:
                        resolved_source = session.source_type
            except Exception:
                logger.debug("Failed to get session for output routing")

        targets = self._resolve_targets(session_type, resolved_source)

        decision = OutputRoutingDecision(
            targets=[t.value for t in targets],
            rationale=self._build_rationale(session_type, resolved_source, targets),
            session_id=session_id,
            source_type=resolved_source,
            session_type=session_type,
            timestamp=time.time(),
        )

        self._record_decision(decision)
        return decision

    def output_targets_for_source(
        self, source_type: str,
    ) -> list[str]:
        """Static lookup: which output targets for a given source type."""
        targets = _SOURCE_OUTPUT_MAP.get(
            source_type,
            [VoiceOutputTarget.SILENT_LOG],
        )
        return [t.value for t in targets]

    def output_targets_for_session_type(
        self, session_type: str,
    ) -> list[str]:
        """Static lookup: which output targets for a given session type."""
        targets = _SESSION_TYPE_OUTPUT_MAP.get(
            session_type,
            [VoiceOutputTarget.SILENT_LOG],
        )
        return [t.value for t in targets]

    def snapshot(self) -> VoiceOutputSnapshot:
        """Current state snapshot."""
        health = "active" if self._total_routed > 0 else "idle"
        return VoiceOutputSnapshot(
            recent_decisions=[
                d.to_dict() for d in self._recent_decisions[-10:]
            ],
            outputs_by_target=dict(self._outputs_by_target),
            health=health,
            total_routed=self._total_routed,
            generated_at=time.time(),
        )

    # ── Internal ───────────────────────────────────────────────────

    def _resolve_targets(
        self, session_type: str, source_type: str,
    ) -> list[VoiceOutputTarget]:
        if session_type and session_type in _SESSION_TYPE_OUTPUT_MAP:
            return _SESSION_TYPE_OUTPUT_MAP[session_type]
        if source_type and source_type in _SOURCE_OUTPUT_MAP:
            return _SOURCE_OUTPUT_MAP[source_type]
        return [VoiceOutputTarget.SILENT_LOG]

    def _build_rationale(
        self,
        session_type: str,
        source_type: str,
        targets: list[VoiceOutputTarget],
    ) -> str:
        target_names = ", ".join(t.value for t in targets)
        if session_type and session_type in _SESSION_TYPE_OUTPUT_MAP:
            return f"session_type={session_type} → [{target_names}]"
        if source_type and source_type in _SOURCE_OUTPUT_MAP:
            return f"source_type={source_type} → [{target_names}]"
        return f"default → [{target_names}]"

    def _record_decision(self, decision: OutputRoutingDecision) -> None:
        self._recent_decisions.append(decision)
        if len(self._recent_decisions) > self._max_recent:
            self._recent_decisions = self._recent_decisions[-self._max_recent:]
        for target in decision.targets:
            self._outputs_by_target[target] = (
                self._outputs_by_target.get(target, 0) + 1
            )
        self._total_routed += 1
