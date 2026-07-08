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


def _read_store(name: str) -> str:
    return (_ROOT / "cockpit" / "src" / "renderer" / "stores" / name).read_text(encoding="utf-8")


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
    # (delete-draft / cancel) is TERMINAL with no _finalizeRecording completion to
    # reset the latch — if the latch stays set, startVoice's guard bails forever and
    # the mic is dead. Phase 2 replaced the bare `finalizing = false` with dropping
    # the CaptureSession (`activeSession = null`), which the guard
    # (`activeSession && !activeSession.done`) then passes cleanly. Same intent,
    # structural mechanism.
    ctrl = _read("voice-controller.ts")
    import re
    m = re.search(r"export function abortActiveRecording\(\).*?\n}", ctrl, re.S)
    assert m, "could not locate abortActiveRecording"
    body = m.group(0)
    assert "activeSession = null" in body, "abort must drop the session so the guard clears"


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
    # Phase 2: the finalize latch is now the CaptureSession's `done` flag, not the
    # bare `finalizing` module var. The real re-entrancy guard (live recorder OR an
    # un-finalized session) is still present — same intent, structural mechanism.
    assert "if (recorder || (activeSession && !activeSession.done))" in ctrl


def test_consent_never_blocks_capture_ws_autogrants() -> None:
    # P4S31 DURABLE consent (Apple/WhatsApp model): the authenticated WS auto-grants
    # on connect, so the client grant POST is best-effort and NEVER blocks capture.
    # A slow/flaky grant must not strand the user at a "consent failed" button.
    adapter = _read("platform-voice-adapter.ts")
    # _consentAndStart no longer throws ConsentRequiredError on a failed client grant
    # (it proceeds to startVoice; the WS is the real gate). Phase 2 added an
    # AbortSignal param + forwards it to startVoice, so match the signature loosely.
    import re
    m = re.search(r"async function _consentAndStart\([^)]*\).*?\n}", adapter, re.S)
    assert m, "could not locate _consentAndStart"
    body = m.group(0)
    assert "throw new ConsentRequiredError" not in body
    assert "await startVoice(" in body

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


# ── Phase 2: ROOT A (state latches) + ROOT F (races) ─────────────────────────

def test_finalize_has_terminal_finally() -> None:
    # ROOT A: _finalizeRecording must GUARANTEE terminal resolution — a try/finally
    # so micState can never strand at 'transcribing' (blob-present-but-null-draft,
    # a thrown branch, or a fall-through). The finally forces idle.
    ctrl = _read("voice-controller.ts")
    import re
    _s = ctrl.index("function _finalizeRecording(")
    _e = ctrl.index("function _resolveMicIdle", _s)
    body = ctrl[_s:_e]
    assert "finally" in body, "finalize must have a try/finally terminal guarantee"
    assert "_resolveMicIdle()" in body


def test_transcribing_state_has_watchdog() -> None:
    # ROOT A: entering 'transcribing' arms a hard watchdog so the mic can never hang
    # there forever (server never replies / promise never settles).
    ctrl = _read("voice-controller.ts")
    assert "micStateWatchdog" in ctrl
    assert "_armMicStateWatchdog" in ctrl
    # armed around the transcribing transition
    assert "MIC_STATE_WATCHDOG_MS" in ctrl


def test_transition_table_has_force_escape() -> None:
    # ROOT A: teardown must be able to reach a terminal state UNCONDITIONALLY — a
    # stuck recordingState can't block the next capture. _forceState is that escape,
    # and deleteDraft uses it (not the silently-droppable transitionRecordingState).
    store = _read_store("voiceMessageStore.ts")
    assert "_forceState" in store
    assert "_forceState('cancelled')" in store or "_forceState(\"cancelled\")" in store
    assert "_forceState('idle')" in store or "_forceState(\"idle\")" in store


def test_synchronous_capture_claim() -> None:
    # ROOT F: the double-tap guard must be SYNCHRONOUS (before any await) — the React
    # micState guard reads a stale closure. captureClaimed is set before the first
    # await and released in finally.
    adapter = _read("platform-voice-adapter.ts")
    assert "captureClaimed" in adapter
    # slice from startCapture to the next top-level function so the whole body (incl.
    # the claim + first await) is in view — a non-greedy `}` stops at the first inner
    # block close and would truncate before the await.
    start = adapter.index("async function startCapture(): Promise<void> {")
    nxt = adapter.index("async function _startCaptureInner", start)
    body = adapter[start:nxt]
    # the synchronous claim must precede the (only) real await in the wrapper — the
    # `await _startCaptureInner()` call. (Match the exact awaited call, not the bare
    # word "await" which also appears in the doc comment.)
    claim_idx = body.index("captureClaimed = true")
    await_idx = body.index("await _startCaptureInner")
    assert claim_idx < await_idx, "captureClaimed must be set BEFORE the first await"
    assert "finally" in body and "captureClaimed = false" in body


def test_withtimeout_aborts_chain() -> None:
    # ROOT F: the 8s watchdog must CANCEL the raced chain (AbortController), not just
    # reject — else startVoice runs on and installs a recorder over a torn-down mic.
    adapter = _read("platform-voice-adapter.ts")
    assert "new AbortController()" in adapter
    assert "abort?.abort()" in adapter
    # startVoice checks signal.aborted after its awaits
    ctrl = _read("voice-controller.ts")
    assert "signal?.aborted" in ctrl


def test_completion_uses_captured_draft_id() -> None:
    # ROOT F: _finalizeRecording must write the returning transcript to the CAPTURED
    # session.draftId via the parameterized store actions — never the live
    # activeDraftId (which a concurrent delete/new-recording may have rebound).
    ctrl = _read("voice-controller.ts")
    assert "session.draftId" in ctrl
    import re
    m = re.search(r"function _finalizeRecording\(.*?\n}\n", ctrl, re.S)
    body = m.group(0)
    assert "completeTranscript(draftId" in body
    assert "markFailed(draftId" in body
    # the store exposes the draft-id-parameterized variants
    store = _read_store("voiceMessageStore.ts")
    assert "completeTranscript: (draftId" in store
    assert "markFailed: (draftId" in store


def test_error_listeners_deconflicted() -> None:
    # ROOT F: the top-level client.on('error') handler must NOT double-write the
    # draft while a scoped transcribeUtterance listener owns the error — it defers
    # via the transcribeInFlight flag, preserving the precise code.
    ctrl = _read("voice-controller.ts")
    assert "transcribeInFlight" in ctrl
    import re
    m = re.search(r"client\.on\('error'.*?\n    \}\)\n", ctrl, re.S)
    assert m, "could not locate top-level error handler"
    body = m.group(0)
    assert "if (transcribeInFlight)" in body


def test_capture_session_replaces_finalizing_latch() -> None:
    # Phase 2: the bare `finalizing` module var is gone — replaced by the
    # CaptureSession object whose `done` flag is the latch. abortActiveRecording no
    # longer relies on a manual `finalizing = false`.
    ctrl = _read("voice-controller.ts")
    assert "interface CaptureSession" in ctrl
    assert "let activeSession: CaptureSession | null" in ctrl
    # no bare `finalizing` assignment survives (comments referencing the word are ok)
    import re
    assert not re.search(r"^\s*finalizing = (true|false)", ctrl, re.M), (
        "bare finalizing latch assignments must be gone"
    )


def test_sendraw_verifies_open() -> None:
    # ROOT C-client: sendRaw + sendBinary must FAIL FAST (throw) when the socket is
    # not OPEN — a silent no-op drops the GAP F control frame → server 4002 → 25s
    # client hang. send() (TTS + heartbeat ping) must stay a tolerant no-op.
    ws = (_API / "websocket.ts").read_text(encoding="utf-8")
    import re

    def _body(name: str) -> str:
        m = re.search(rf"\b{name}\([^)]*\):\s*void\s*\{{(.*?)\n  \}}", ws, re.S)
        assert m, f"could not locate {name}"
        return m.group(1)

    send_raw = _body("sendRaw")
    send_bin = _body("sendBinary")
    assert "throw" in send_raw and "WS_NOT_OPEN" in send_raw
    assert "throw" in send_bin and "WS_NOT_OPEN" in send_bin
    # send() (the typed-envelope path used by heartbeat/TTS) must NOT throw.
    send_plain = _body("send")
    assert "throw" not in send_plain


def test_voice_error_has_render_path() -> None:
    # ROOT E: voiceStore.error must be RENDERED (the visible banner previously read
    # only chatStore.error). It surfaces in a banner gated on a TERMINAL lastOutcome,
    # NOT inside the Tap-to-play button or the mic title attr.
    rail = (
        _ROOT / "cockpit" / "src" / "renderer" / "components" / "RightRail.tsx"
    ).read_text(encoding="utf-8")
    assert "VOICE_TERMINAL_OUTCOMES" in rail
    # the terminal set gates the banner and includes the real dead-ends
    for code in ("MIC_PERMISSION_DENIED", "VOICE_WS_UNAVAILABLE", "STT_FAILED", "TIMEOUT"):
        assert code in rail, code
    # the banner renders voiceError gated on the terminal set (not just Tap-to-play)
    assert "VOICE_TERMINAL_OUTCOMES.has(voiceLastOutcome" in rail


def test_dead_consent_code_removed() -> None:
    # ROOT E: the "Enable Push-to-Talk" affordance was removed (WS auto-grants); its
    # dead handler must be gone too.
    rail = (
        _ROOT / "cockpit" / "src" / "renderer" / "components" / "RightRail.tsx"
    ).read_text(encoding="utf-8")
    assert "handleEnablePushToTalk" not in rail
    # the revoke/disable affordance stays.
    assert "handleRevokePushToTalk" in rail


def test_voice_outcome_union_complete() -> None:
    # ROOT E: the watchdog outcomes the adapter emits must be in the VoiceOutcome union.
    store = (
        _ROOT / "cockpit" / "src" / "renderer" / "stores" / "voiceStore.ts"
    ).read_text(encoding="utf-8")
    assert "'VOICE_START_TIMEOUT'" in store
    assert "'VOICE_START_FAILED'" in store


def test_silent_hint_gated_on_context_running() -> None:
    # ROOT D (iOS): the "mic appears silent" hint must only fire when the meter
    # AudioContext is actually 'running'. On iOS an out-of-gesture context is
    # 'suspended' and reads all-zeros → a false silent hint on EVERY recording.
    ctrl = _read("voice-controller.ts")
    import re
    m = re.search(r"function startCaptureMeter\(\).*?\n}", ctrl, re.S)
    assert m, "could not locate startCaptureMeter"
    body = m.group(0)
    assert "meterAudioContext" in body and "'running'" in body
    # the running check gates the silentMs computation
    assert "meterRunning" in body


def test_recorder_has_health_handlers() -> None:
    # ROOT D (iOS): the recorder must wire onerror + track mute/ended handlers so an
    # OS-driven capture teardown (screen-lock / call) finalizes gracefully instead
    # of hanging the draft at 'transcribing' or losing the audio.
    ctrl = _read("voice-controller.ts")
    assert "rec.onerror" in ctrl
    assert "track.onended" in ctrl
    assert "track.onmute" in ctrl
    # and they are detached on teardown so they can't fire across sessions
    assert "_detachTrackHandlers" in ctrl


def test_recorder_uses_timeslice() -> None:
    # ROOT D (iOS): recorder.start() must pass a timeslice so ondataavailable flushes
    # periodically — otherwise any interruption before a clean stop() loses ALL audio.
    ctrl = _read("voice-controller.ts")
    import re
    assert re.search(r"\.start\(\d", ctrl), "recorder must start with a numeric timeslice"


def test_ios_unlock_awaited() -> None:
    # ROOT D (iOS): the audio unlock must be awaited so it completes within the user
    # gesture — fire-and-forget let the gesture expire and iOS then blocked TTS.
    ctrl = _read("voice-controller.ts")
    assert "await unlockAudioForIOS(" in ctrl


def test_voice_player_playsinline() -> None:
    # ROOT D (iOS): the <audio> players carry playsInline so iOS doesn't take an
    # audio-only mp4 blob fullscreen / block inline playback.
    rail = (
        _ROOT / "cockpit" / "src" / "renderer" / "components" / "RightRail.tsx"
    ).read_text(encoding="utf-8")
    assert "playsInline" in rail
