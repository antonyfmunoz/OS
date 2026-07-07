# Voice Capture-Signal Contract (P4S-31D1-C)

**Packet:** `P4S-31D1-C-VOICE-CAPTURE-SIGNAL-001`
**Binds:** `data/umh/voice/voice_capture_signal_contract.json`
**Extends:** `data/umh/voice/voice_message_contract.json` (VoiceMessageDraft, RecordingSessionState, VadConfig, VoiceDiagnostics)

## Doctrine

Capture must be **VISIBLE** and failure must be **LEGIBLE**.

The recording card shows a live, client-computed RMS meter so the operator can
see the mic is actually delivering samples. When a draft fails, the card shows
the **specific** cause. A mic-silent, empty-blob, or decode failure is **never**
reported as a bare "No speech detected" — that mis-diagnosis is the exact bug
this contract closes.

## Root cause this closes

- **Symptom:** every voice note failed with "No speech detected".
- **True cause:** the capture-side `AudioContext` was **suspended**, so
  `ScriptProcessor.onaudioprocess` never fired. Zero PCM reached the server. The
  server's VAD **correctly** reported no speech. The UI then collapsed *all*
  failures to "No speech detected", hiding the real (silent-capture) cause.
- **Fix:** the capture `AudioContext` resume is fixed elsewhere (the capture
  fix). This packet's UI guarantee is that (1) the live RMS meter makes a silent
  capture immediately visible, and (2) the failure taxonomy names the real cause.

## Acceptance criteria — the ordered signal chain

1. **non-zero energy** — client-computed capture RMS rises above the silence
   floor while the user speaks (proves mic + AudioContext deliver samples).
2. **valid blob** — MediaRecorder produces a non-empty blob on stop
   (`EMPTY_AUDIO_BLOB` if zero bytes).
3. **server decode** — the server decodes the audio (`DECODE_FAILED` /
   `UNSUPPORTED_AUDIO_FORMAT` otherwise).
4. **VAD speech** — server VAD finds speech (`VAD_NO_SPEECH` otherwise, draft
   recoverable).
5. **STT transcript** — STT returns a transcript (`STT_FAILED` otherwise, audio
   preserved for retry).
6. **preserved artifact** — audio is preserved on **every** failure path; only
   an explicit delete discards it.
7. **transcript under card** — the finalized transcript renders **underneath**
   the voice bubble, never in the message input.
8. **pause doesn't send** — a sentence-internal pause never finalizes; a
   finalize is not a send.
9. **explicit send** — a draft becomes a chat message **only** on the operator's
   explicit Send (`auto_send=false`, no exceptions).
10. **chat only after send** — no chat message / IntentSpec / loop entry exists
    for a draft whose `status != 'sent'`.
11. **delete leaves no trace** — delete discards the draft + audio artifact and
    revokes the blob URL; no chat trace, no loop entry.

## Client diagnostics

Source: `cockpit/src/renderer/api/voice-ws.ts` (`VoiceWsClient`) +
`voice-controller.ts` meter poll.

| Field | Meaning |
|---|---|
| `clientRms` | RMS (0..1) of the most recent capture buffer, computed client-side from the same PCM the WS ships. The visible proof of capture. Polled at ~10Hz into `voiceMessageStore.captureRms`. |
| `captureRmsPeak` | Highest `clientRms` seen this session; a peak that stays ~0 during live recording is the silent-capture signature. |
| `captureSilentMs` | ms the session has run flat-at-0 past the grace window (`MIC_SILENT_HINT_MS=2000`); `> 0` arms the "mic appears silent" hint. |
| `chunksSent` | PCM16 buffers pushed to the server (0 during a silent/suspended capture). |
| `lastCaptureMsAgo` | ms since the last processed buffer (capture liveness). |
| `capturing` | AudioContext + ScriptProcessor are live. |

**Meter law:** the meter reads a store field the controller writes; it runs
**no** audio loop of its own and performs **no** FFT — one getter read + one
shallow store write per tick (`METER_POLL_MS=100`, `MIC_SILENT_RMS_FLOOR=0.005`).

## Server diagnostics — error taxonomy

Source: `umh/voice_server.py`.

| Code | Meaning | UI string |
|---|---|---|
| `EMPTY_AUDIO_BLOB` | zero bytes captured | No audio captured — mic sent no bytes |
| `SILENT_AUDIO` | below the energy floor | Mic appears silent — no audio energy detected |
| `UNSUPPORTED_AUDIO_FORMAT` | container/codec not decodable | Unsupported audio format for this browser |
| `DECODE_FAILED` | corrupt/truncated container | Audio could not be decoded |
| `VAD_NO_SPEECH` | decoded but no speech segment | No speech found in the recording |
| `STT_FAILED` | engine returned no transcript | Transcription failed — try again |

Client / retry / send codes (`NO_SPEECH`, `RETRY_*`, `AUDIO_UPLOAD_FAILED`,
`CHAT_SEND_FAILED`) each map to their own distinct string. UI source:
`RightRail.tsx` `VOICE_FAILURE_REASON`.

**Taxonomy law:** every code maps to a distinct operator-facing string; **none**
collapses to "No speech detected". Mic-silent, empty-blob, and decode failures
are visibly different from a genuine no-speech.

## Platform matrix — for THIS bug

> A mobile-platform capture failure must **not** reject the `desktop_chrome`
> verdict. Each row stands alone.

| Platform | Capture status | Root cause / note | MIME | Verdict |
|---|---|---|---|---|
| **desktop_chrome** | **FIXED** | suspended capture AudioContext → zero PCM → server VAD saw no speech → UI mislabeled "No speech detected". Resolved by AudioContext resume + live RMS meter + precise taxonomy. | `audio/webm;codecs=opus` | **PASS** (primary target) |
| **mobile_chrome** | SUPPORTED | Android Chrome supports the shipped webm/opus path | `audio/webm;codecs=opus` | PASS (path supported; e2e proof deferred) |
| **mobile_safari** | **BLOCKED** | iOS Safari supports none of the shipped MediaRecorder MIMEs (webm/ogg/wav); iOS needs `audio/mp4` (AAC), absent from `_pickRecorderMime()`. Needs an mp4 recorder candidate + server AAC decode. | none supported | **DOCUMENTED FAILURE** — tracked `P4S-31D-5`; does not reject desktop |
| **desktop_safari** | DEFERRED | not yet evaluated | — | LATER (out of scope) |

## Hard constraints

- The meter reads client-computed RMS, never server transcript content.
- No transcript (partial or final) is ever pasted into the message input.
- Send is explicit-only; a pause/finalize is never a send.
- A silent-capture / empty-blob / decode failure is never reported as
  "No speech detected".
- Mobile capture failure does not reject the desktop capture verdict.
