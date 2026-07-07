# P4S-31D1-C — STT Fixtures, Deployed-STT Identification & LifeOS Capture/STT Recon

Date: 2026-07-07. Worktree-only work (`agent-aeb698f11720c6f92`); `/opt/OS` main
untouched; no live services restarted. Read-only against the running config.

---

## Part A — STT fixtures (what they prove)

Fixtures generated programmatically (stdlib `wave`+`struct`+`math`, no downloads,
no models) in `tests/fixtures/voice/generate_fixtures.py`; asserted by
`tests/test_p4s31d1c_stt_fixtures.py`. Every WAV is mono / 16-bit / 16 kHz — the
exact shape `save_wav()` writes and STT must receive.

| Fixture | Size | What it proves | Test |
|---|---|---|---|
| `known_good_tone.wav` | 19,244 B | Pipeline feeds ONE **decodable mono-16k-PCM WAV** to STT (not a raw blob); returned transcript delivered as a final `TranscriptEvent`; temp WAV unlinked after (no-persist invariant) | `test_known_good_feeds_decoded_mono16k_pcm_to_stt` |
| `mid_sentence_pause.wav` | 64,044 B | A 1.0 s intra-utterance gap (< 1.8 s `SILENCE_END_UTTERANCE_S`) yields **ONE** utterance / one STT call, not an early finalize into two | `test_mid_sentence_pause_is_one_utterance_not_two` |
| `silence.wav` | 25,644 B | **SILENT/NO-SPEECH typed path**: STT never invoked, empty final transcript emitted, session completes (no hang) | `test_silence_yields_no_speech_path_without_calling_stt`, `test_silence_does_not_hang` |
| `ios_audio_mp4.marker.json` | 1,094 B | Honest placeholder — documents that `audio/mp4` (AAC) must be decoded to PCM16-16k before STT; no valid AAC can be synthesized in-stdlib | `test_ios_mp4_marker_documents_decode_requirement` (pass) + `test_ios_mp4_blob_is_decoded_before_stt` (**xfail, strict**) |

Measured fixture audio levels vs the server's own thresholds (grounds the
assertions): known-good level **0.428** (> 0.02 threshold), silence level
**0.0**, pause gap **1.0 s** (< 1.8 s finalize window). `MIN_AUDIO_BYTES` = 9,600.

**Test approach.** `process_utterance` is a closure inside `handle_voice`, so the
tests drive the REAL `handle_voice` VAD + buffering + `save_wav` path via a fake
websocket that replays `mic_start → PCM chunks → mic_stop`. The network STT call
(`transcribe`) is mocked; the mock reads and captures the WAV bytes the pipeline
handed it, and the tests assert channels==1, sampwidth==2 (16-bit),
framerate==16000. We assert on **what STT receives**, never on a transcript
string (real Whisper on a synth tone is unreliable — hence the mock).

Result: **8 passed, 1 xfailed** (the iOS mp4 decode-seam gap, strict xfail).

### Why the iOS mp4 test is xfail, not fake-green

iOS Safari `MediaRecorder` emits `audio/mp4` (AAC in an MP4/M4A container). That
is NOT raw PCM. `voice_server.py`'s WS transport already delivers PCM16 @16 kHz,
so there is **no container-decode seam** in the server today. Handing an
un-decoded mp4 blob to `save_wav()` → local `faster-whisper` would be invalid.
(Groq's `whisper-large-v3-turbo` *does* accept m4a/mp4 as an uploaded file, so
for the Groq path decode can be delegated to Groq — but the local fallback needs
real decode-to-PCM first.) The strict-xfail test asserts the DESIRED end-state (a
`decode_container_to_pcm16` seam on the server) so it flips to a failure the day
someone claims mobile support without building the seam. This is a documented
gap, not a passed claim.

---

## Part B — Deployed STT identification (read from running config)

**Deployed STT engine: Groq `whisper-large-v3-turbo`** (network path, the
default), with **`faster-whisper` local fallback** available.

Evidence (no secret printed — presence only):

- `GROQ_API_KEY` present: **True** (loaded from `/opt/OS/services/.env` /
  `/opt/OS/.env`).
- Live `GET http://127.0.0.1:8096/health` on the running `umh-voice-server`:
  `{"status":"ok","stt_engine":"groq","tts_provider":"kokoro","active_sessions":0,...}`.
- `systemctl is-active umh-voice-server` → **active**.
- SDKs present on the host: `groq` installed; `faster_whisper` **1.2.1**
  installed (fallback is real, not theoretical).

Dispatch (`umh/voice_server.py`):

```
transcribe(audio_path)
  → _transcribe_groq(audio_path)        # model="whisper-large-v3-turbo", language="en"
      returns text on success
  → if empty: _transcribe_local(audio_path)   # substrate VoiceEngine.transcribe_fast (faster-whisper)
```

STT does **not** route through `adapters/models/model_router.py` — the voice
server calls Groq directly (`from groq import Groq`). `model_router.py` only
*mentions* `groq_whisper` in a comment near its `GROQ_API_KEY` provider config; the
active STT call path is the voice server. The `stt_engine` reported by `/health`
is a static `"groq" if GROQ_API_KEY else "faster-whisper"` selector — so on this
host, with the key present and the service live, **the deployed path is Groq**;
faster-whisper only takes over per-call when a Groq call returns empty/raises.

---

## Part C — LifeOS capture / DECODE / STT deep recon

Extends `data/audits/2026-07-07_p4s31d1b_lifeos_voice_recon.md` (Lane A) with the
CAPTURE → DECODE → STT angle specifically. Prior verdict (browser-native
`webkitSpeechRecognition`, no audio bytes, no server STT, no storage) is
CONFIRMED and deepened below.

Method: live SSH to the executor node (`antonys beast pc@100.74.199.102`),
recursive `Select-String` over `client\src` and `server` on the real
`C:\dev\dev\LyfeOS\` tree (not the VPS mirror). Read-only. The whole feature is
three files: `client/src/hooks/use-voice-control.ts` (STT engine),
`client/src/components/VoiceOverlay.tsx` (UI), and
`server/replit_integrations/chat/routes.ts` (`/api/voice-command`).

**1. Audio blob handling — NO raw audio bytes (confirmed).**
`MediaRecorder|getUserMedia|createMediaStreamSource|MediaStream` over `client\src`
→ **0 hits**. The only `AudioContext`/`Blob`/`ArrayBuffer`/`FileReader`/`base64`
hits in the whole client are decoys unrelated to capture: `lib/sounds.ts`
(output UI tones), `lib/theta-beats.ts` (synthesizes a binaural-beat WAV —
output), and `pages/ProfilePage.tsx:2003-2008` (profile **photo** upload). The
app never touches the mic audio stream; the browser opens the mic implicitly for
SpeechRecognition only. → **LIFEOS-SPECIFIC** (absence of a capture layer is the
design; nothing to reuse).

**2. STT path — browser Web Speech API only, zero server STT (confirmed).**
`use-voice-control.ts:90` `window.SpeechRecognition || window.webkitSpeechRecognition`;
instantiated `:95`. Flags: `continuous=false` (`:103`), `interimResults=true`
(`:104`), `lang='en-US'` hardcoded (`:105`), `maxAlternatives=1` (`:106`).
`whisper|transcribe|/stt|groq.*audio|deepgram|assemblyai` → **0 hits** in both
client and server. The `/api/voice-command` route (`routes.ts:1740`) accepts only
`{ transcript, conversationId }` and **rejects any non-string transcript**
(`:1745`) — no audio field, no multipart, no file. Audio never leaves the
browser. → **LIFEOS-SPECIFIC** (browser-produced text only; cannot satisfy the
D1-B audio-preservation/retry contract).

**3. Transcript display — interim streamed, only final committed (confirmed).**
`onresult` splits by `isFinal` (`use-voice-control.ts:117-124`). Interim →
`setLastTranscript(interim)`/`onTranscript(interim)` (`:126-129`), live-updates UI,
never committed. Final → additionally `parseVoiceCommand(final)` + `onCommand`
(`:131-136`). `VoiceOverlay.tsx:227-228` renders the live transcript in quotes;
swaps to server feedback once processed (`:231-233`). → **REUSABLE-COCKPIT
(concept)** — clean interim-in-quotes / commit-on-`isFinal` render pattern;
validates the `TranscriptEvent.final` split.

**4. Pause behavior — NO re-arm, NO VAD, NO debounce (the sharp finding).**
`continuous=false` (`:103`) and `onend` does ONLY
`isActiveRef=false; setIsListening(false)` (`:145-148`) — no restart, no re-arm,
no debounce, no `onend→start()` loop. There is **no VAD and no silence threshold
anywhere in the app**. Consequence: on a mid-sentence pause the browser's own
silence heuristic ends the utterance, `onend` fires, LyfeOS flips to "Paused" and
stops; the user must manually re-tap the mic (`VoiceOverlay.tsx:109-117`) to start
a NEW session. `onerror` (`:139-143`) also just stops — no retry. → **UNSAFE-STALE**
— a natural speaking pause silently terminates dictation with no recovery. This is
exactly the failure the D1-B server-side VAD (`SILENCE_END_UTTERANCE_S=1.8`,
intra-utterance gaps kept as one utterance — see Part A) is designed to avoid;
LyfeOS offers no reusable pause mechanic.

**4b. Mobile / iOS — support-gated, no fallback (confirmed).**
`isSupported = !!SpeechRecognition` (`:89-92`); `VoiceOverlay.tsx:127`
`if (!isSupported || !showOverlay) return null`. No iOS/Safari branch, no
polyfill, no MediaRecorder fallback. Where `webkitSpeechRecognition` is undefined
(unreliable on iOS Safari) the feature is invisible with no alternative path —
silent no-op, not graceful degradation. → **UNSAFE-STALE** — cannot assume voice
works cross-device.

**5. Storage path — transcript text persisted, no audio (confirmed).**
`routes.ts:1777` `chatStorage.createMessage(dbConversationId, "user", `[Voice] ${transcript}`)`
— stored as a plain user chat row prefixed `[Voice] `; the LLM sees
`[Voice Command] ${transcript}` (`:1797`). No audio stored, uploaded, or
referenced; rate-limited (`index.ts:109`, `routes.ts:1740`). → **REUSABLE-COCKPIT
(concept)** — "store transcript as a tagged text message, never audio" is a clean
privacy-preserving pattern (aligns with the D1-B chat seam carrying an artifact
*reference*, not bytes).

**Recon verdict.** Prior Lane-A verdict confirmed at file:line and deepened:
LyfeOS's voice path captures no audio, runs STT entirely in the browser, has no
VAD / no re-arm (a pause kills the session), no iOS fallback, and persists only
tagged text. For the P4S-31D1-B/C governed voice-MESSAGE rail it offers reusable
UX *concepts* only (interim/final split, tagged-text persistence) — the STT
engine decision stays with the confirmed **MediaRecorder/PCM16 → `voice_server.py`
Groq-turbo + faster-whisper** path, which is the only one that preserves audio
bytes for retry.

---

## Classification summary

| Mechanic | Origin | Class | Reason |
|---|---|---|---|
| PCM16 @16 kHz WS capture transport (`voice-ws.ts` → `voice_server.py`) | Cockpit/substrate | **REUSABLE-COCKPIT** | Real audio bytes; the confirmed engine for the governed voice-MESSAGE rail |
| Server STT (Groq turbo + faster-whisper fallback) | substrate/`umh` | **REUSABLE-SUBSTRATE** | Deployed, health-verified; satisfies audio-preservation/retry (LifeOS's browser API cannot) |
| interim-vs-final transcript split | LifeOS (Web Speech) | **REUSABLE (concept only)** | Validates the `TranscriptEvent.final` pattern; no audio bytes so cannot BE the engine |
| Listening/Thinking/Paused status vocab + pause/resume | LifeOS HUD | **REUSABLE-COCKPIT (concept)** | UX vocabulary maps cleanly onto `RecordingSessionState` |
| `webkitSpeechRecognition` as the STT engine | LifeOS | **UNSAFE-STALE for this contract** | Emits no audio bytes → violates audio-preservation/retry; iOS Safari support is unreliable |
| ungoverned auto-execute on final transcript | LifeOS `/api/voice-command` | **UNSAFE-STALE** | Violates hold-at-`AWAITING_APPROVAL`; the D1-B rail requires explicit operator send |
| iOS `audio/mp4` decode-to-PCM seam | (not built) | **GAP** | No container-decode seam in `voice_server.py`; tracked by the strict-xfail test |

---

## Verification

- `python3 -m py_compile umh/voice_server.py tests/fixtures/voice/generate_fixtures.py tests/test_p4s31d1c_stt_fixtures.py` → clean.
- `python3 -m pytest tests/test_p4s31d1c_stt_fixtures.py -q` → **8 passed, 1 xfailed**.
- Fixtures all < 100 KB; all valid mono/16-bit/16 kHz WAV.
- No secret printed anywhere; `GROQ_API_KEY` reported as presence bool only.
