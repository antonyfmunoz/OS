"""Voice Operations Runtime — Campaign 20.4 (composition root).

Unified operational view of all voice subsystems. Composes all C20
runtimes into one snapshot. Provides process_utterance() — the full
pipeline from raw event to output routing decision.

Voice is not just query — it operates the organism. Action intents
route through CommandRuntime → existing governed execution path.

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


class VoiceOperationsHealth(str, Enum):
    OPTIMAL = "optimal"
    ACTIVE = "active"
    DEGRADED = "degraded"
    OFFLINE = "offline"


@dataclass
class VoiceCapabilityStatus:
    stt_available: bool = False
    tts_available: bool = False
    wake_word_available: bool = False
    conference_available: bool = False
    ambient_available: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "stt_available": self.stt_available,
            "tts_available": self.tts_available,
            "wake_word_available": self.wake_word_available,
            "conference_available": self.conference_available,
            "ambient_available": self.ambient_available,
        }


@dataclass
class VoiceOperationsSnapshot:
    health: str = VoiceOperationsHealth.OFFLINE.value
    ingress_status: dict[str, Any] = field(default_factory=dict)
    active_sessions: list[dict[str, Any]] = field(default_factory=list)
    ambient_state: str = "dormant"
    output_status: dict[str, Any] = field(default_factory=dict)
    query_engine_domains: list[str] = field(default_factory=list)
    capabilities: dict[str, Any] = field(default_factory=dict)
    stt_available: bool = False
    tts_available: bool = False
    devices_listening: list[str] = field(default_factory=list)
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "health": self.health,
            "ingress_status": self.ingress_status,
            "active_sessions": self.active_sessions,
            "ambient_state": self.ambient_state,
            "output_status": self.output_status,
            "query_engine_domains": self.query_engine_domains,
            "capabilities": self.capabilities,
            "stt_available": self.stt_available,
            "tts_available": self.tts_available,
            "devices_listening": self.devices_listening,
            "generated_at": self.generated_at,
        }


# ── Intent classification patterns ───────────────────────────────────

_ACTION_KEYWORDS = {
    "build", "create", "deploy", "run", "execute", "start",
    "stop", "restart", "cancel", "approve", "reject",
    "submit", "dispatch", "schedule",
}


def _is_action_intent(text: str) -> bool:
    """Deterministic check: is this an action intent or a query?"""
    lower = text.lower().strip()
    first_word = lower.split()[0] if lower.split() else ""
    return first_word in _ACTION_KEYWORDS


# ── Runtime ──────────────────────────────────────────────────────────


class VoiceOperationsRuntime:
    """Unified voice operations — composes all C20 runtimes.

    Provides process_utterance() for the full voice pipeline:
    raw event → classify → session → query/intent → output routing.

    Action intents route through CommandRuntime for governed execution.
    Query intents route through VoiceQueryEngine for organism queries.
    """

    def __init__(
        self,
        voice_ingress_runtime: Any | None = None,
        voice_session_manager: Any | None = None,
        ambient_wake_runtime: Any | None = None,
        voice_output_runtime: Any | None = None,
        voice_query_engine: Any | None = None,
        command_runtime: Any | None = None,
    ) -> None:
        self._voice_ingress_runtime = voice_ingress_runtime
        self._voice_session_manager = voice_session_manager
        self._ambient_wake_runtime = ambient_wake_runtime
        self._voice_output_runtime = voice_output_runtime
        self._voice_query_engine = voice_query_engine
        self._command_runtime = command_runtime

    # ── Lazy accessors ─────────────────────────────────────────────

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
    def ambient_wake_runtime(self) -> Any | None:
        if self._ambient_wake_runtime is None:
            try:
                from substrate.workstation.ambient_wake_runtime import (
                    AmbientWakeRuntime,
                )
                self._ambient_wake_runtime = AmbientWakeRuntime()
            except Exception:
                logger.debug("AmbientWakeRuntime unavailable")
        return self._ambient_wake_runtime

    @property
    def voice_output_runtime(self) -> Any | None:
        if self._voice_output_runtime is None:
            try:
                from substrate.workstation.voice_output_runtime import (
                    VoiceOutputRuntime,
                )
                self._voice_output_runtime = VoiceOutputRuntime()
            except Exception:
                logger.debug("VoiceOutputRuntime unavailable")
        return self._voice_output_runtime

    @property
    def voice_query_engine(self) -> Any | None:
        if self._voice_query_engine is None:
            try:
                from substrate.operator.voice_query_engine import (
                    VoiceQueryEngine,
                )
                self._voice_query_engine = VoiceQueryEngine()
            except Exception:
                logger.debug("VoiceQueryEngine unavailable")
        return self._voice_query_engine

    @property
    def command_runtime(self) -> Any | None:
        if self._command_runtime is None:
            try:
                from substrate.organism.command_runtime import CommandRuntime
                self._command_runtime = CommandRuntime()
            except Exception:
                logger.debug("CommandRuntime unavailable")
        return self._command_runtime

    # ── Core pipeline ──────────────────────────────────────────────

    def process_utterance(
        self,
        source_event: dict[str, Any],
        text: str = "",
    ) -> dict[str, Any]:
        """Full voice pipeline: ingest → session → query/intent → output.

        1. Classify source via VoiceIngressRuntime
        2. Start/route through VoiceSessionManager
        3. Determine if action intent or query
        4. Action → CommandRuntime (governed execution)
           Query → VoiceQueryEngine (organism queries)
        5. Route output via VoiceOutputRuntime
        """
        result: dict[str, Any] = {
            "status": "processed",
            "text": text or source_event.get("text", ""),
            "timestamp": time.time(),
        }

        # 1. Classify ingress
        ingress_event = None
        if self.voice_ingress_runtime is not None:
            try:
                if not text:
                    text = str(source_event.get("text", source_event.get("transcript", "")))
                    source_event["text"] = text
                ingress_event = self.voice_ingress_runtime.classify(source_event)
                result["ingress"] = ingress_event.to_dict()
            except Exception as exc:
                logger.debug("Ingress classification failed: %s", exc)
                result["ingress_error"] = str(exc)
        else:
            result["ingress_error"] = "VoiceIngressRuntime unavailable"

        # 2. Session management
        session_id = ""
        if ingress_event is not None and self.voice_session_manager is not None:
            try:
                session = self.voice_session_manager.start_session(ingress_event)
                session_id = session.session_id
                result["session"] = session.to_dict()
            except Exception as exc:
                logger.debug("Session management failed: %s", exc)
                result["session_error"] = str(exc)

        # 3. Route: action intent or query
        utterance = text or result.get("text", "")
        if _is_action_intent(utterance):
            result["intent_type"] = "action"
            result["resolution"] = self._handle_action_intent(utterance)
        else:
            result["intent_type"] = "query"
            result["resolution"] = self._handle_query_intent(utterance)

        # 4. Output routing
        if self.voice_output_runtime is not None:
            try:
                source_type = ""
                if ingress_event is not None:
                    source_type = ingress_event.source_type
                decision = self.voice_output_runtime.route_output(
                    session_id=session_id,
                    response_text=result.get("resolution", {}).get("answer_text", ""),
                    source_type=source_type,
                )
                result["output_routing"] = decision.to_dict()
            except Exception as exc:
                logger.debug("Output routing failed: %s", exc)
                result["output_error"] = str(exc)

        return result

    # ── Snapshot & health ──────────────────────────────────────────

    def snapshot(self) -> VoiceOperationsSnapshot:
        """Unified operational snapshot across all voice subsystems."""
        ingress_status: dict[str, Any] = {}
        if self.voice_ingress_runtime is not None:
            try:
                ingress_status = self.voice_ingress_runtime.snapshot().to_dict()
            except Exception:
                ingress_status = {"error": "unavailable"}

        active_sessions: list[dict[str, Any]] = []
        if self.voice_session_manager is not None:
            try:
                snap = self.voice_session_manager.snapshot()
                active_sessions = snap.active_sessions
            except Exception:
                pass

        ambient_state = "dormant"
        devices_listening: list[str] = []
        if self.ambient_wake_runtime is not None:
            try:
                ambient_state = self.ambient_wake_runtime.current_state().value
                devices_listening = self.ambient_wake_runtime.listening_devices()
            except Exception:
                pass

        output_status: dict[str, Any] = {}
        if self.voice_output_runtime is not None:
            try:
                output_status = self.voice_output_runtime.snapshot().to_dict()
            except Exception:
                output_status = {"error": "unavailable"}

        query_domains: list[str] = []
        if self.voice_query_engine is not None:
            try:
                from substrate.operator.voice_query_engine import QueryDomain
                query_domains = [d.value for d in QueryDomain]
            except Exception:
                pass

        caps = self.capabilities()

        health = self._derive_health(
            ingress_status, active_sessions, ambient_state,
        )

        return VoiceOperationsSnapshot(
            health=health.value,
            ingress_status=ingress_status,
            active_sessions=active_sessions,
            ambient_state=ambient_state,
            output_status=output_status,
            query_engine_domains=query_domains,
            capabilities=caps.to_dict(),
            stt_available=caps.stt_available,
            tts_available=caps.tts_available,
            devices_listening=devices_listening,
            generated_at=time.time(),
        )

    def health(self) -> VoiceOperationsHealth:
        """Derive overall voice operations health."""
        snap = self.snapshot()
        return VoiceOperationsHealth(snap.health)

    def capabilities(self) -> VoiceCapabilityStatus:
        """Check which voice capabilities are currently available."""
        stt = False
        tts = False
        wake_word = False
        conference = False
        ambient = False

        if self.voice_ingress_runtime is not None:
            stt = True

        if self.voice_output_runtime is not None:
            tts = True

        if self.ambient_wake_runtime is not None:
            try:
                state = self.ambient_wake_runtime.current_state()
                wake_word = state.value != "dormant"
                ambient = True
            except Exception:
                pass

        if self.voice_session_manager is not None:
            conference = True

        return VoiceCapabilityStatus(
            stt_available=stt,
            tts_available=tts,
            wake_word_available=wake_word,
            conference_available=conference,
            ambient_available=ambient,
        )

    def summary(self) -> dict[str, Any]:
        """Compact summary for API/cockpit."""
        snap = self.snapshot()
        return {
            "health": snap.health,
            "active_sessions": len(snap.active_sessions),
            "ambient_state": snap.ambient_state,
            "query_domains": len(snap.query_engine_domains),
            "capabilities": snap.capabilities,
            "devices_listening": len(snap.devices_listening),
        }

    # ── Internal ───────────────────────────────────────────────────

    def _handle_action_intent(self, text: str) -> dict[str, Any]:
        """Route action intent through CommandRuntime for governed execution."""
        if self.command_runtime is not None:
            try:
                cmd = self.command_runtime.process(text, source="voice")
                if hasattr(cmd, "to_dict"):
                    return cmd.to_dict()
                if isinstance(cmd, dict):
                    return cmd
                return {"action": "delegated", "text": text}
            except Exception as exc:
                logger.debug("CommandRuntime processing failed: %s", exc)
                return {
                    "action": "delegation_failed",
                    "error": str(exc),
                    "text": text,
                }

        return {
            "action": "not_delegated",
            "reason": "CommandRuntime unavailable",
            "text": text,
        }

    def _handle_query_intent(self, text: str) -> dict[str, Any]:
        """Route query intent through VoiceQueryEngine."""
        if self.voice_query_engine is not None:
            try:
                resolution = self.voice_query_engine.resolve(text)
                if hasattr(resolution, "to_dict"):
                    return resolution.to_dict()
                if isinstance(resolution, dict):
                    return resolution
                return {"answer_text": str(resolution)}
            except Exception as exc:
                logger.debug("VoiceQueryEngine resolution failed: %s", exc)
                return {
                    "domain": "error",
                    "answer_text": f"Query resolution failed: {exc}",
                }

        return {
            "domain": "unavailable",
            "answer_text": "Voice query engine is not available.",
        }

    def _derive_health(
        self,
        ingress_status: dict[str, Any],
        active_sessions: list[dict[str, Any]],
        ambient_state: str,
    ) -> VoiceOperationsHealth:
        """Deterministic health derivation from subsystem states."""
        subsystems_up = 0
        total_subsystems = 4

        if self.voice_ingress_runtime is not None:
            subsystems_up += 1
        if self.voice_session_manager is not None:
            subsystems_up += 1
        if self.voice_output_runtime is not None:
            subsystems_up += 1
        if self.voice_query_engine is not None:
            subsystems_up += 1

        if subsystems_up == 0:
            return VoiceOperationsHealth.OFFLINE
        if subsystems_up < total_subsystems:
            return VoiceOperationsHealth.DEGRADED
        if active_sessions or ambient_state != "dormant":
            return VoiceOperationsHealth.ACTIVE
        return VoiceOperationsHealth.OPTIMAL
