"""
umh.substrate.stream_transport_contract — Adapter seam for live
streaming text transports (distinct from audio-frame voice transport).

Defines transport-agnostic data types and minimal Protocols for streaming
text ingress/egress. No audio I/O, no Discord/Meet APIs, no STT/TTS —
contract only.

Public API:
    TRANSPORT_DISCORD_VOICE         — transport constant
    TRANSPORT_MEET                  — transport constant
    TRANSPORT_LOCAL_MIC             — transport constant
    StreamIngressChunk              — inbound text chunk
    StreamEgressChunk               — outbound text chunk
    StreamingIngressAdapter         — Protocol for ingress adapters
    StreamingEgressAdapter          — Protocol for egress adapters
    compute_stream_chunk_id         — deterministic chunk ID
    build_stream_ingress_chunk      — construct ingress chunk
    build_stream_egress_chunk       — construct egress chunk

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

_LOG_PREFIX = "[substrate.stream_transport_contract]"


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
# StreamIngressChunk — inbound text chunk
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class StreamIngressChunk:
    """Immutable inbound streaming text chunk.

    Fields:
        chunk_id:        deterministic chunk identifier
        session_id:      owning live session
        transport:       source transport
        operator_id:     who sent this chunk
        text:            chunk text content
        is_partial:      True if this is a partial/streaming update
        received_at:     ISO timestamp
        correlation_id:  links chunk to upstream event chain
    """

    chunk_id: str
    session_id: str
    transport: str
    operator_id: str
    text: str
    is_partial: bool
    received_at: str
    correlation_id: str = ""

    def __post_init__(self) -> None:
        if not self.received_at:
            object.__setattr__(self, "received_at", _utcnow())

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict — deterministic key order."""
        return {
            "chunk_id": self.chunk_id,
            "correlation_id": self.correlation_id,
            "is_partial": self.is_partial,
            "operator_id": self.operator_id,
            "received_at": self.received_at,
            "session_id": self.session_id,
            "text": self.text,
            "transport": self.transport,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> StreamIngressChunk:
        """Reconstruct from plain dict."""
        return StreamIngressChunk(
            chunk_id=str(d.get("chunk_id", "")),
            session_id=str(d.get("session_id", "")),
            transport=str(d.get("transport", "")),
            operator_id=str(d.get("operator_id", "")),
            text=str(d.get("text", "")),
            is_partial=bool(d.get("is_partial", False)),
            received_at=str(d.get("received_at", "")),
            correlation_id=str(d.get("correlation_id", "")),
        )


# ---------------------------------------------------------------------------
# StreamEgressChunk — outbound text chunk
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class StreamEgressChunk:
    """Immutable outbound streaming text chunk.

    Fields:
        chunk_id:        deterministic chunk identifier
        session_id:      owning live session
        transport:       target transport
        text:            chunk text content
        is_partial:      True if this is a partial/streaming update
        created_at:      ISO timestamp
        correlation_id:  links chunk to upstream event chain
        artifact_id:     optional associated artifact
    """

    chunk_id: str
    session_id: str
    transport: str
    text: str
    is_partial: bool
    created_at: str
    correlation_id: str = ""
    artifact_id: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            object.__setattr__(self, "created_at", _utcnow())

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict — deterministic key order."""
        return {
            "artifact_id": self.artifact_id,
            "chunk_id": self.chunk_id,
            "correlation_id": self.correlation_id,
            "created_at": self.created_at,
            "is_partial": self.is_partial,
            "session_id": self.session_id,
            "text": self.text,
            "transport": self.transport,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> StreamEgressChunk:
        """Reconstruct from plain dict."""
        return StreamEgressChunk(
            chunk_id=str(d.get("chunk_id", "")),
            session_id=str(d.get("session_id", "")),
            transport=str(d.get("transport", "")),
            text=str(d.get("text", "")),
            is_partial=bool(d.get("is_partial", False)),
            created_at=str(d.get("created_at", "")),
            correlation_id=str(d.get("correlation_id", "")),
            artifact_id=str(d.get("artifact_id", "")),
        )


# ---------------------------------------------------------------------------
# Protocols — minimal interface for streaming text transports
# ---------------------------------------------------------------------------
@runtime_checkable
class StreamingIngressAdapter(Protocol):
    """Minimal contract for inbound text stream adapters.

    Structural protocol — implementations do not need to inherit.
    """

    def ingest_chunk(self, chunk: StreamIngressChunk) -> Any:
        """Process an inbound text chunk."""
        ...


@runtime_checkable
class StreamingEgressAdapter(Protocol):
    """Minimal contract for outbound text stream adapters.

    Structural protocol — implementations do not need to inherit.
    """

    def emit_chunk(self, chunk: StreamEgressChunk) -> Any:
        """Emit an outbound text chunk."""
        ...


# ---------------------------------------------------------------------------
# Deterministic ID
# ---------------------------------------------------------------------------


def compute_stream_chunk_id(
    session_id: str,
    transport: str,
    timestamp: str,
    direction: str = "ingress",
) -> str:
    """Deterministic chunk ID: same inputs → same ID.

    Uses SHA-256 of canonical JSON. Prefix: ``sci_`` (ingress) or
    ``sco_`` (egress).
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
    prefix = "sci_" if direction == "ingress" else "sco_"
    return f"{prefix}{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


# ---------------------------------------------------------------------------
# Builder helpers
# ---------------------------------------------------------------------------


def build_stream_ingress_chunk(
    *,
    session_id: str,
    transport: str,
    operator_id: str,
    text: str,
    is_partial: bool = False,
    correlation_id: str = "",
    received_at: str = "",
    chunk_id: str | None = None,
) -> StreamIngressChunk:
    """Construct a StreamIngressChunk with deterministic ID."""
    ts = received_at or _utcnow()
    cid = chunk_id or compute_stream_chunk_id(session_id, transport, ts, "ingress")
    return StreamIngressChunk(
        chunk_id=cid,
        session_id=session_id,
        transport=transport,
        operator_id=operator_id,
        text=text,
        is_partial=is_partial,
        received_at=ts,
        correlation_id=correlation_id,
    )


def build_stream_egress_chunk(
    *,
    session_id: str,
    transport: str,
    text: str,
    is_partial: bool = False,
    correlation_id: str = "",
    artifact_id: str = "",
    created_at: str = "",
    chunk_id: str | None = None,
) -> StreamEgressChunk:
    """Construct a StreamEgressChunk with deterministic ID."""
    ts = created_at or _utcnow()
    cid = chunk_id or compute_stream_chunk_id(session_id, transport, ts, "egress")
    return StreamEgressChunk(
        chunk_id=cid,
        session_id=session_id,
        transport=transport,
        text=text,
        is_partial=is_partial,
        created_at=ts,
        correlation_id=correlation_id,
        artifact_id=artifact_id,
    )
