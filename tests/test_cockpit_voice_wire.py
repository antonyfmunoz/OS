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


def test_mic_single_acquisition_no_double_getusermedia() -> None:
    # P4S31 PERMANENT mobile fix: the mic is opened with getUserMedia EXACTLY ONCE
    # per capture and reused. The old double-acquire (probe + startMic) is what
    # hung iOS Safari. The regression guard: there is a single real getUserMedia
    # call site (inside _acquireMicOnce), and startMic reuses the gesture stream.
    ws = _read("voice-ws.ts")
    # exactly ONE literal getUserMedia( invocation in the whole capture module
    assert ws.count("navigator.mediaDevices.getUserMedia(") == 1, (
        "voice-ws.ts must call getUserMedia exactly once (single-acquisition)"
    )
    assert "_gestureStream" in ws  # the reused single stream
    assert "_acquireMicOnce" in ws  # the one bounded acquisition helper
    assert "releaseGestureStream" in ws  # abort-path cleanup
    # bounded so a stalled acquisition degrades instead of dead-hanging
    assert "MicAcquireTimeout" in ws and "MIC_ACQUIRE_TIMEOUT_MS" in ws

    # The adapter releases the gesture stream on abort paths (no leaked mic) and
    # maps the timeout to a typed, fast outcome (not a dead button).
    adapter = _read("platform-voice-adapter.ts")
    assert "releaseGestureStream" in adapter
    assert "MicAcquireTimeout" in adapter
    assert "MIC_ACQUIRE_TIMEOUT" in adapter


def test_ios_blob_falls_back_to_server_decode() -> None:
    # P4S31 mobile decode fix: iOS Safari's AudioContext.decodeAudioData can't
    # decode the audio/mp4 blob its OWN MediaRecorder produced. When the client
    # PCM resample fails, _transcribeBlob must fall back to sending the RAW
    # container blob with its real content_type so the server ffmpeg-decodes it —
    # never a dead DECODE_FAILED while a playable blob exists.
    ctrl = _read("voice-controller.ts")
    # the client-decode failure now becomes a server-decode fallback, not a
    # terminal DECODE_FAILED return.
    assert "fallback_server" in ctrl
    assert "blob.arrayBuffer()" in ctrl  # sends raw container bytes
    assert "contentType" in ctrl  # real content_type drives the server ffmpeg lane
    # transcribeUtterance accepts a content_type override for the server lane
    ws = _read("voice-ws.ts")
    assert "contentType?" in ws
    assert "control.contentType ?? RAW_PCM_CONTENT_TYPE" in ws


def test_startvoice_guard_does_not_deadlock_on_startup_states() -> None:
    # P4S31 DEADLOCK FIX: startVoice()'s re-entrancy guard must only bail on a LIVE
    # recording ('listening'/'recording'), NOT on the startup states
    # 'requesting_permission'/'connecting_voice_ws'. startCapture() sets
    # 'requesting_permission' then calls startVoice() (active-consent path); if the
    # guard also matched those, startVoice returned immediately and the button
    # stranded forever at "Requesting mic…".
    ctrl = _read("voice-controller.ts")
    # the guard branch that early-returns must not list the startup states
    assert "activeState === 'listening' || activeState === 'recording'" in ctrl
    # and must NOT bail on requesting_permission / connecting_voice_ws
    assert "activeState === 'requesting_permission'" not in ctrl
    assert "activeState === 'connecting_voice_ws'" not in ctrl
    # the real re-entrancy guard (live recorder) is still present
    assert "if (recorder || finalizing)" in ctrl


def test_consent_auto_grants_no_second_gesture() -> None:
    # The browser mic approval IS the authorizing gesture: after it succeeds the
    # UMH push_to_talk grant is auto-requested in the same flow (retried once on a
    # transient failure) and a stale 'required' state never lingers — so the
    # separate "Enable Push-to-Talk" button never appears on the happy path.
    adapter = _read("platform-voice-adapter.ts")
    # auto-grant with a single automatic retry before the manual fallback
    assert adapter.count("await grantPushToTalk()") >= 2
    # a stale 'required' is cleared to 'granting' when a fresh capture starts
    assert "if (vs.consentState === 'required') vs.setConsentState('granting')" in adapter
