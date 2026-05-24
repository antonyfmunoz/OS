"""Signal emission — build and emit SignalEnvelopes from workstation inputs.

Creates properly typed SignalEnvelope objects from workstation events
(text input, voice transcription, perception events, mode transitions,
boot events) and emits them through the substrate SignalSocket.

Follows the discord signal_factory.py pattern: each input type has a
dedicated builder that produces a SignalEnvelope with the correct
content_type, payload, and metadata.

When SignalSocket is unavailable, signals are logged but not lost —
they can be replayed from the continuity bridge.

UMH workstation subsystem.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_INTEGRATION_ID = "workstation_local"

_signal_socket: Any = None


def set_signal_socket(socket: Any) -> None:
    """Register the SignalSocket instance for emission."""
    global _signal_socket
    _signal_socket = socket


def get_signal_socket() -> Any:
    """Return the registered SignalSocket, or None."""
    return _signal_socket


def _emit(envelope: Any) -> dict[str, Any]:
    """Emit a SignalEnvelope through the registered SignalSocket."""
    if _signal_socket is None:
        logger.debug("No SignalSocket registered — signal logged only")
        return {"emitted": False, "reason": "no_socket"}

    try:
        receipt = _signal_socket.emit(envelope)
        return {
            "emitted": True,
            "accepted": receipt.accepted,
            "signal_id": str(receipt.signal_id),
            "rejection_reason": receipt.rejection_reason,
        }
    except Exception as exc:
        logger.debug("Signal emission failed: %s", exc)
        return {"emitted": False, "reason": str(exc)}


def emit_text_input(text: str, source: str = "stdin") -> dict[str, Any]:
    """Emit a text input signal."""
    try:
        from substrate.sockets.envelopes import SignalEnvelope
        from substrate.types import SignalUrgency

        envelope = SignalEnvelope(
            integration_id=_INTEGRATION_ID,
            content_type="workstation.text.input",
            payload={"text": text, "source": source},
            raw_content=text,
            urgency=SignalUrgency.NORMAL,
            metadata={"input_source": source},
        )
        return _emit(envelope)
    except ImportError:
        return {"emitted": False, "reason": "substrate_unavailable"}


def emit_voice_transcription(
    text: str,
    confidence: float = 1.0,
    duration_ms: float = 0.0,
) -> dict[str, Any]:
    """Emit a voice transcription signal."""
    try:
        from substrate.sockets.envelopes import SignalEnvelope
        from substrate.types import SignalUrgency

        envelope = SignalEnvelope(
            integration_id=_INTEGRATION_ID,
            content_type="workstation.voice.transcription",
            payload={
                "text": text,
                "confidence": confidence,
                "duration_ms": duration_ms,
            },
            raw_content=text,
            urgency=SignalUrgency.NORMAL,
            metadata={"input_source": "voice"},
        )
        return _emit(envelope)
    except ImportError:
        return {"emitted": False, "reason": "substrate_unavailable"}


def emit_presence_change(
    present: bool,
    previous: bool | None = None,
) -> dict[str, Any]:
    """Emit a presence detection signal (webcam face detection)."""
    try:
        from substrate.sockets.envelopes import SignalEnvelope
        from substrate.types import SignalUrgency

        envelope = SignalEnvelope(
            integration_id=_INTEGRATION_ID,
            content_type="workstation.perception.presence",
            payload={
                "present": present,
                "previous": previous,
                "transition": "arrived" if present else "departed",
            },
            urgency=SignalUrgency.LOW,
        )
        return _emit(envelope)
    except ImportError:
        return {"emitted": False, "reason": "substrate_unavailable"}


def emit_workspace_change(
    window_title: str,
    app_name: str = "",
    category: str = "",
) -> dict[str, Any]:
    """Emit a workspace/active window change signal."""
    try:
        from substrate.sockets.envelopes import SignalEnvelope
        from substrate.types import SignalUrgency

        envelope = SignalEnvelope(
            integration_id=_INTEGRATION_ID,
            content_type="workstation.perception.workspace",
            payload={
                "window_title": window_title,
                "app_name": app_name,
                "category": category,
            },
            urgency=SignalUrgency.LOW,
        )
        return _emit(envelope)
    except ImportError:
        return {"emitted": False, "reason": "substrate_unavailable"}


def emit_system_metrics(
    cpu_percent: float = 0.0,
    memory_percent: float = 0.0,
    disk_percent: float = 0.0,
) -> dict[str, Any]:
    """Emit a system metrics signal."""
    try:
        from substrate.sockets.envelopes import SignalEnvelope
        from substrate.types import SignalUrgency

        envelope = SignalEnvelope(
            integration_id=_INTEGRATION_ID,
            content_type="workstation.perception.metrics",
            payload={
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_percent": disk_percent,
            },
            urgency=SignalUrgency.BACKGROUND,
        )
        return _emit(envelope)
    except ImportError:
        return {"emitted": False, "reason": "substrate_unavailable"}


def emit_mode_transition(
    old_mode: str,
    new_mode: str,
    reason: str = "",
) -> dict[str, Any]:
    """Emit a mode transition signal."""
    try:
        from substrate.sockets.envelopes import SignalEnvelope
        from substrate.types import SignalUrgency

        envelope = SignalEnvelope(
            integration_id=_INTEGRATION_ID,
            content_type="workstation.mode.transition",
            payload={
                "old_mode": old_mode,
                "new_mode": new_mode,
                "reason": reason,
            },
            urgency=SignalUrgency.NORMAL,
        )
        return _emit(envelope)
    except ImportError:
        return {"emitted": False, "reason": "substrate_unavailable"}


def emit_boot_event(
    boot_type: str = "daily",
    session_id: str = "",
) -> dict[str, Any]:
    """Emit a workstation boot signal."""
    try:
        from substrate.sockets.envelopes import SignalEnvelope
        from substrate.types import SignalUrgency

        envelope = SignalEnvelope(
            integration_id=_INTEGRATION_ID,
            content_type="workstation.boot",
            payload={
                "boot_type": boot_type,
                "session_id": session_id,
            },
            urgency=SignalUrgency.NORMAL,
        )
        return _emit(envelope)
    except ImportError:
        return {"emitted": False, "reason": "substrate_unavailable"}
