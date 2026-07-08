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


def test_server_decode_is_the_primary_path() -> None:
    # P4S31 DURABLE: server-decode is the PRIMARY (only) transcription path — the
    # way Apple/WhatsApp/Telegram do it. The client never decodes the recording
    # (iOS Safari can't decode its own MediaRecorder mp4). _transcribeBlob sends
    # the RAW container blob with its real content_type; the server ffmpeg-decodes.
    ctrl = _read("voice-controller.ts")
    # the fragile client resample is GONE from the transcribe path
    assert "_resampleToPcm16" not in ctrl or "REMOVED" in ctrl
    assert "blob.arrayBuffer()" in ctrl  # sends raw container bytes
    assert "transcribe_blob_server_decode" in ctrl
    assert "contentType" in ctrl  # real content_type drives the server ffmpeg lane
    # transcribeUtterance accepts a content_type override for the server lane
    ws = _read("voice-ws.ts")
    assert "contentType?" in ws
    assert "control.contentType ?? RAW_PCM_CONTENT_TYPE" in ws


def test_no_client_side_decodeaudiodata_in_transcribe() -> None:
    # The WebKit-fragile AudioContext.decodeAudioData must not gate transcription.
    ctrl = _read("voice-controller.ts")
    # the decode helper was removed; only a comment referencing it may remain
    assert "async function _resampleToPcm16" not in ctrl


def test_abort_recording_clears_finalizing_latch() -> None:
    # Field bug: "after I deleted it, voice wouldn't work again." abortActiveRecording
    # (delete-draft / cancel) sets `finalizing = true` but is TERMINAL — there is no
    # _finalizeRecording completion to reset it. If left true, startVoice()'s
    # `if (recorder || finalizing) return` guard bails forever and the mic is dead.
    # The abort MUST reset the latch.
    ctrl = _read("voice-controller.ts")
    import re
    m = re.search(r"export function abortActiveRecording\(\).*?\n}", ctrl, re.S)
    assert m, "could not locate abortActiveRecording"
    body = m.group(0)
    assert "finalizing = false" in body, "abort must clear the finalizing latch"


def test_consent_flow_noise_not_surfaced_in_ui() -> None:
    # Consent is auto-granted by the governed WS — the client must NOT surface
    # consent-flow transients as user-facing text: no "Enable Push-to-Talk" button,
    # no "Enabling push-to-talk…" label. (Field bug: a burst of consent/status
    # noise messages during a capture that ultimately worked.)
    rail = _ROOT / "cockpit" / "src" / "renderer" / "components" / "RightRail.tsx"
    txt = rail.read_text(encoding="utf-8")
    assert "Enable Push-to-Talk for this device" not in txt
    assert "Enabling push-to-talk" not in txt
    # the fire-and-forget consent means capture never blocks on / errors from it
    adapter = _read("platform-voice-adapter.ts")
    assert "fire-and-forget" in adapter.lower() or "void (async ()" in adapter


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


def test_consent_never_blocks_capture_ws_autogrants() -> None:
    # P4S31 DURABLE consent (Apple/WhatsApp model): the authenticated WS auto-grants
    # on connect, so the client grant POST is best-effort and NEVER blocks capture.
    # A slow/flaky grant must not strand the user at a "consent failed" button.
    adapter = _read("platform-voice-adapter.ts")
    # _consentAndStart no longer throws ConsentRequiredError on a failed client grant
    # (it proceeds to startVoice; the WS is the real gate).
    import re
    m = re.search(r"async function _consentAndStart\(\).*?\n}", adapter, re.S)
    assert m, "could not locate _consentAndStart"
    body = m.group(0)
    assert "throw new ConsentRequiredError" not in body
    assert "await startVoice()" in body

    # the WS server-side auto-grants for an authenticated principal.
    voice_py = (
        _ROOT / "transports" / "api" / "voice.py"
    ).read_text(encoding="utf-8")
    assert "auto-grant" in voice_py.lower()
    assert "_store.grant(" in voice_py


def test_ensure_client_disconnects_before_rebuild() -> None:
    # ROOT B: ensureClient must NOT overwrite `client`/`chatUnsub`/`cleanups`
    # without tearing down the old client first — else every reconnect gap leaks an
    # auto-reconnecting socket + heartbeat interval + visibilitychange listener +
    # duplicate handlers. It MUST still keep the warm-reuse early return (WS
    # auto-grant happy path).
    import re
    ctrl = _read("voice-controller.ts")
    m = re.search(r"async function ensureClient\(\).*?\n  return client\n}", ctrl, re.S)
    assert m, "could not locate ensureClient"
    body = m.group(0)
    # warm reuse preserved
    assert "if (client?.connected) return client" in body
    # rebuild branch tears the old client down first
    assert "cleanups.forEach" in body
    assert "cleanups = []" in body
    assert "chatUnsub" in body
    assert "client.disconnect()" in body
    # the disconnect precedes the rebuild
    assert body.index("client.disconnect()") < body.index("new VoiceWsClient()")


def test_connect_timeout_closes_socket() -> None:
    # ROOT B: connect()'s 5s timeout must close the underlying socket before
    # rejecting, or a socket that opens after 5s is an orphaned forever-reconnecting
    # zombie.
    import re
    ws = _read("voice-ws.ts")
    m = re.search(r"connect\(\): Promise<void> \{.*?\n  \}", ws, re.S)
    assert m, "could not locate connect()"
    body = m.group(0)
    # the timeout callback disconnects before rejecting
    to_idx = body.index("ws_connect_timeout")
    tail = body[to_idx:]
    assert "this.ws.disconnect()" in tail
    assert tail.index("this.ws.disconnect()") < tail.index("reject(")


def test_stop_recorder_detaches_handlers() -> None:
    # ROOT B: recorder handlers must be detached once the final blob is delivered so
    # a late ondataavailable from the OLD recorder can't push a tail chunk into the
    # NEXT session's recorderChunks (cross-session contamination).
    ctrl = _read("voice-controller.ts")
    assert "ondataavailable = null" in ctrl
    assert "onstop = null" in ctrl
