"""Canonical voice error taxonomy — the ONE voice error enum, tree-wide.

P4S31 Voice Convergence. This is the single home for ``VoiceErrorCode``. Every
layer emits ONLY these codes: the canonical ``VoiceSession`` runtime returns a
``VoiceErrorCode``, the governed WS (``transports/api/voice.py``) relays it
verbatim, and the client renders ``error_payload(code)`` with NO remapping. The
TS mirror (``cockpit/src/renderer/api/voiceErrorCodes.ts``) is codegen-checked
against this enum so client and server can never disagree.

Home rationale (Architecture Layer Law): this enum must live in ``substrate/``,
not ``umh/``, because the canonical runtime (substrate) imports it and
``substrate/`` may never import from ``umh/``. ``umh/voice_preflight.py`` now
re-exports from here for backward compatibility; it is not a second definition.

Provenance: the first six codes (EMPTY_AUDIO_BLOB … STT_FAILED) were introduced
by P4S-31D1-C in ``umh/voice_preflight.py`` and are relocated here unchanged so
existing wire codes keep their exact string values. The convergence adds the
three codes the runtime boundary needs: CONSENT_DENIED, TTS_FAILED,
RUNTIME_UNAVAILABLE — for a 9-code canon. (There is deliberately no
CONSENT_EXPIRED: the consent grant has no expiry, so the state can never fire.)

Gate 14 (``scripts/check_voice_runtime_divergence.py``) enforces that no voice
error code is defined outside this enum (Python) or its TS mirror.

UMH substrate subsystem. Instance-agnostic. No transcript/audio content ever
enters a message built here.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class VoiceErrorCode(str, Enum):
    """Precise, distinct failure taxonomy for the voice pipeline.

    Each value is a stable wire code emitted as
    ``{"type":"error","code":<value>,"message":<bounded>}``. The audio-pipeline
    codes are ordered from earliest (no bytes) to latest (engine failed) point of
    failure and are mutually exclusive — a given utterance resolves to exactly
    one. The boundary codes (consent/runtime) fire before the pipeline runs.
    """

    # ── Audio pipeline (relocated from umh/voice_preflight.py, values unchanged) ──
    # No audio bytes arrived at all (empty buffer / empty blob).
    EMPTY_AUDIO_BLOB = "EMPTY_AUDIO_BLOB"
    # Bytes present but the mic was effectively silent (mean energy below floor).
    SILENT_AUDIO = "SILENT_AUDIO"
    # A container blob could not be decoded (corrupt / truncated / not audio).
    DECODE_FAILED = "DECODE_FAILED"
    # The declared/observed container format is not one we support.
    UNSUPPORTED_AUDIO_FORMAT = "UNSUPPORTED_AUDIO_FORMAT"
    # Audio had energy but the STT engine found no speech in it.
    VAD_NO_SPEECH = "VAD_NO_SPEECH"
    # The STT engine itself errored / crashed / timed out.
    STT_FAILED = "STT_FAILED"

    # ── Runtime boundary (added by P4S31 convergence) ──
    # Consent to capture/act was not granted for this session/surface.
    CONSENT_DENIED = "CONSENT_DENIED"
    # Text-to-speech synthesis failed producing the spoken response.
    TTS_FAILED = "TTS_FAILED"
    # The canonical voice runtime could not be reached / is not available.
    RUNTIME_UNAVAILABLE = "RUNTIME_UNAVAILABLE"
    #
    # NOTE: there is deliberately NO ``CONSENT_EXPIRED`` code. ``VoiceConsentGrant``
    # has only granted_at/revoked_at (no expires_at), so an "expired" state can
    # never arise — a revoked grant surfaces as CONSENT_DENIED. Adding a code that
    # can never fire would be dead taxonomy. The canon is 9 codes.


# Human-readable, BOUNDED default messages. Callers may override, but must keep
# them free of transcript/audio content. Never interpolate secret content.
_DEFAULT_MESSAGES: dict[VoiceErrorCode, str] = {
    VoiceErrorCode.EMPTY_AUDIO_BLOB: "No audio was received.",
    VoiceErrorCode.SILENT_AUDIO: "The microphone was silent — no audio energy detected.",
    VoiceErrorCode.DECODE_FAILED: "The audio could not be decoded.",
    VoiceErrorCode.UNSUPPORTED_AUDIO_FORMAT: "This audio format is not supported.",
    VoiceErrorCode.VAD_NO_SPEECH: "Audio was captured but no speech was detected.",
    VoiceErrorCode.STT_FAILED: "Speech recognition failed.",
    VoiceErrorCode.CONSENT_DENIED: "Voice consent was not granted.",
    VoiceErrorCode.TTS_FAILED: "The spoken response could not be generated.",
    VoiceErrorCode.RUNTIME_UNAVAILABLE: "The voice runtime is unavailable.",
}


def error_payload(code: VoiceErrorCode, message: str | None = None) -> dict[str, Any]:
    """Build the WS error payload for a typed failure.

    Shape is fixed: ``{"type":"error","code":<CODE>,"message":<bounded>}``.
    The message is always bounded to <=100 chars and never carries transcript
    or audio content.
    """
    msg = message if message is not None else _DEFAULT_MESSAGES[code]
    return {"type": "error", "code": code.value, "message": msg[:100]}
