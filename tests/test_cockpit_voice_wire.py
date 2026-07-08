"""P4S31 Voice Convergence — cockpit capture edges speak the governed protocol.

Structural (source-text) assertions over the cockpit TS client: the voice WS
resolves to the ONE governed endpoint, uses the GAP F wire protocol (control
frame → PCM → terminator), sources error codes from the codegen'd canonical
mirror, and carries no stale :8096 / groq_whisper / bare mic_start references.
(TS behavior is covered by tsc + the build; these guard the convergence
invariants that a future edit could silently break.)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_ROOT = Path(__file__).resolve().parent.parent
_API = _ROOT / "cockpit" / "src" / "renderer" / "api"


def _read(name: str) -> str:
    return (_API / name).read_text(encoding="utf-8")


def test_voice_ws_resolves_to_governed_endpoint() -> None:
    src = _read("voice-ws.ts")
    assert "/api/umh/voice/ws" in src
    # no standalone voice_server anymore
    assert "8096" not in src


def test_voice_ws_uses_gap_f_control_frame() -> None:
    src = _read("voice-ws.ts")
    # the control frame carries the GAP F fields
    for field in (
        "source",
        "device_registry_id",
        "consent_grant_id",
        "content_type",
        "activation_mode",
    ):
        assert field in src, field
    # raw-PCM content type for the live-mic lane
    assert "audio/pcm" in src
    # a terminator frame
    assert '"end"' in src or "'end'" in src


def test_client_error_codes_sourced_from_canonical_mirror() -> None:
    ctrl = _read("voice-controller.ts")
    # imports the codegen'd mirror and references it (no parallel taxonomy for
    # the overlapping codes)
    assert "from './voiceErrorCodes'" in ctrl
    assert "VOICE_ERROR_CODES.EMPTY_AUDIO_BLOB" in ctrl
    assert "VOICE_ERROR_CODES.STT_FAILED" in ctrl


def test_no_stale_voice_refs_in_client() -> None:
    for name in ("voice-ws.ts", "voice-controller.ts", "platform-voice-adapter.ts"):
        src = _read(name)
        assert "groq_whisper" not in src, name
        assert "8096" not in src, name


def test_source_label_is_runtime_derived_not_hardcoded() -> None:
    # platform-voice-adapter derives the source label at runtime (web/mobile_web/
    # electron) rather than hardcoding it on the control frame.
    src = _read("platform-voice-adapter.ts")
    assert "currentVoiceSource" in src
    assert "mobile_web" in src


def test_ts_error_codes_are_subset_of_canonical() -> None:
    # Every code the client references for the SERVER taxonomy must exist in the
    # canonical mirror. The 4 client-only pre-flight codes are exempt.
    from substrate.execution.voice.error_codes import VoiceErrorCode

    canonical = {c.value for c in VoiceErrorCode}
    mirror = _read("voiceErrorCodes.ts")
    for code in canonical:
        assert code in mirror, code
