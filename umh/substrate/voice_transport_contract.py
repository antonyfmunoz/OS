"""
umh.substrate.voice_transport_contract — Harness-side contract for
live voice interaction without implementing product UX.

Defines transport-agnostic data types and a minimal Protocol that
future voice transports (Discord voice, Google Meet, local mic) can
implement. No audio I/O, no Whisper/Voicebox integration — contract only.

Public API:
    TRANSPORT_DISCORD_VOICE  — transport constant
    TRANSPORT_MEET           — transport constant
    TRANSPORT_LOCAL_MIC      — transport constant
    VoiceIngressFrame        — inbound transcript frame
    VoiceEgressFrame         — outbound speech frame
    VoiceTransport           — Protocol interface
    compute_voice_frame_id   — deterministic frame ID
    build_voice_ingress_frame — construct ingress frame
    build_voice_egress_frame  — construct egress frame

Separation note:
    This module is contract-only. No network I/O, no audio processing,
    no product-specific rendering. Reusable by any future transport.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

_LOG_PREFIX = "[substrate.voice_transport_contract]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Transport constants
# ---------------------------------------------------------------------------
TRANSPORT_DISCORD_VOICE: str = "discord_voice"
TRANSPORT_MEET: str = "meet"
TRANSPORT_LOCAL_MIC: str = "local_mic"


# ---------------------------------------------------------------------------
# VoiceIngressFrame — inbound transcript
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class VoiceIngressFrame:
    """Immutable inbound voice transcript frame.

    Fields:
        frame_id:        deterministic frame identifier
        session_id:      owning session
        transport:       source transport (discord_voice, meet, local_mic)
        operator_id:     who spoke
        transcript:      transcribed text
        received_at:     ISO timestamp
        correlation_id:  links frame to upstream event chain
    """

    frame_id: str
    session_id: str
    transport: str
    operator_id: str
    transcript: str
    received_at: str
    correlation_id: str = ""

    def __post_init__(self) -> None:
        if not self.received_at:
            object.__setattr__(self, "received_at", _utcnow())

    def to_dict(self) -> dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "frame_id": self.frame_id,
            "operator_id": self.operator_id,
            "received_at": self.received_at,
            "session_id": self.session_id,
            "transcript": self.transcript,
            "transport": self.transport,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> VoiceIngressFrame:
        return VoiceIngressFrame(
            frame_id=str(d.get("frame_id", "")),
            session_id=str(d.get("session_id", "")),
            transport=str(d.get("transport", "")),
            operator_id=str(d.get("operator_id", "")),
            transcript=str(d.get("transcript", "")),
            received_at=str(d.get("received_at", "")),
            correlation_id=str(d.get("correlation_id", "")),
        )


# ---------------------------------------------------------------------------
# VoiceEgressFrame — outbound speech
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class VoiceEgressFrame:
    """Immutable outbound voice/speech frame.

    Fields:
        frame_id:        deterministic frame identifier
        session_id:      owning session
        transport:       target transport
        text:            text to be spoken / synthesized
        created_at:      ISO timestamp
        correlation_id:  links frame to upstream event chain
        artifact_id:     optional associated artifact
    """

    frame_id: str
    session_id: str
    transport: str
    text: str
    created_at: str
    correlation_id: str = ""
    artifact_id: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            object.__setattr__(self, "created_at", _utcnow())

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "correlation_id": self.correlation_id,
            "created_at": self.created_at,
            "frame_id": self.frame_id,
            "session_id": self.session_id,
            "text": self.text,
            "transport": self.transport,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> VoiceEgressFrame:
        return VoiceEgressFrame(
            frame_id=str(d.get("frame_id", "")),
            session_id=str(d.get("session_id", "")),
            transport=str(d.get("transport", "")),
            text=str(d.get("text", "")),
            created_at=str(d.get("created_at", "")),
            correlation_id=str(d.get("correlation_id", "")),
            artifact_id=str(d.get("artifact_id", "")),
        )


# ---------------------------------------------------------------------------
# Protocol — minimal interface for voice transports
# ---------------------------------------------------------------------------
@runtime_checkable
class VoiceTransport(Protocol):
    """Minimal contract that any voice transport implementation must satisfy.

    This is a structural protocol — implementations do not need to inherit.
    They just need to provide these two methods.
    """

    def ingest_transcript(self, frame: VoiceIngressFrame) -> Any:
        """Process an inbound transcript frame."""
        ...

    def emit_voice(self, frame: VoiceEgressFrame) -> Any:
        """Emit an outbound speech frame."""
        ...


# ---------------------------------------------------------------------------
# Deterministic ID
# ---------------------------------------------------------------------------


def compute_voice_frame_id(
    session_id: str,
    transport: str,
    timestamp: str,
    direction: str = "ingress",
) -> str:
    """Deterministic frame ID: same inputs → same ID.

    Uses SHA-256 of canonical JSON. Prefix: ``vfi_`` (ingress) or
    ``vfo_`` (egress).
    """
    canonical = json.dumps(
        {
            "direction": direction,
            "session_id": session_id,
            "timestamp": timestamp,
            "transport": transport,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    prefix = "vfi_" if direction == "ingress" else "vfo_"
    return f"{prefix}{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


# ---------------------------------------------------------------------------
# Builder helpers
# ---------------------------------------------------------------------------


def build_voice_ingress_frame(
    *,
    session_id: str,
    transport: str,
    operator_id: str,
    transcript: str,
    correlation_id: str = "",
    received_at: str = "",
    frame_id: str | None = None,
) -> VoiceIngressFrame:
    """Construct a VoiceIngressFrame with deterministic ID."""
    ts = received_at or _utcnow()
    fid = frame_id or compute_voice_frame_id(
        session_id,
        transport,
        ts,
        "ingress",
    )
    return VoiceIngressFrame(
        frame_id=fid,
        session_id=session_id,
        transport=transport,
        operator_id=operator_id,
        transcript=transcript,
        received_at=ts,
        correlation_id=correlation_id,
    )


def build_voice_egress_frame(
    *,
    session_id: str,
    transport: str,
    text: str,
    correlation_id: str = "",
    artifact_id: str = "",
    created_at: str = "",
    frame_id: str | None = None,
) -> VoiceEgressFrame:
    """Construct a VoiceEgressFrame with deterministic ID."""
    ts = created_at or _utcnow()
    fid = frame_id or compute_voice_frame_id(
        session_id,
        transport,
        ts,
        "egress",
    )
    return VoiceEgressFrame(
        frame_id=fid,
        session_id=session_id,
        transport=transport,
        text=text,
        created_at=ts,
        correlation_id=correlation_id,
        artifact_id=artifact_id,
    )
