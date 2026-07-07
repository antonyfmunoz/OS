# LifeOS Voice Recon — P4S-31D1-B Lane A

Date: 2026-07-07. Read-only recon (VPS mirror + full repo on the executor node
at `C:\dev\dev\LyfeOS\`). Nothing modified anywhere.

## Verdict

LyfeOS HAS a working voice feature, but it is a **voice-COMMAND overlay**, not
a voice-MESSAGE rail — architecturally the opposite of P4S-31D1-B. It captures
NO audio bytes (browser-native Web Speech API returns text directly), has no
recording bubble, no waveform, no pause-aware finalization, no review/edit, no
consent model, and no governance. Reuse is conceptual only.

## Feature map (key files, all on the executor node)

| Concern | Location | Reality |
|---|---|---|
| STT | `client/src/hooks/use-voice-control.ts` | `webkitSpeechRecognition` (Web Speech API): `continuous=false`, `interimResults=true`; interim/final split; final → deterministic regex `parseVoiceCommand()` (nav/mission/timer aliases, no LLM) |
| UX | `client/src/components/VoiceOverlay.tsx` | Floating draggable HUD (Listening/Thinking/Paused, pause-resume, stop); transcript transient, never persisted as a voice object |
| Message shape | server + `shared/models/chat.ts` | No voice-message object — user turn stored as plain text prefixed `[Voice] ${transcript}`; schema has zero audio/transcript/duration fields |
| Server | `server/replit_integrations/chat/routes.ts` `POST /api/voice-command` | Anthropic tool-use loop (max 3 iter), executes toolActions IMMEDIATELY — no approval gate, no proof |
| TTS | `client/src/hooks/use-nova-actions.ts` | Browser `speechSynthesis` only |
| Absent (grep-verified) | — | MediaRecorder, getUserMedia audio recording, VAD thresholds, audio upload/storage, server STT, review-before-send |

## Consequences for P4S-31D1-B

1. **STT engine decision settled**: browser Web Speech API yields no audio
   bytes, so it CANNOT satisfy the contract's audio-preservation/retry
   requirement. MediaRecorder + the existing server Whisper path
   (`umh/voice_server.py`) is the confirmed engine. LyfeOS offers no better path.
2. **Reusable conceptually**: interim-vs-final transcript split (validates the
   TranscriptEvent `final` pattern); deterministic no-LLM classifier (mirrors
   `classify_intent` doctrine); Listening/Thinking/Paused status vocabulary +
   pause/resume mic; `isSupported` capability gate (→ DeviceCapabilityProfile).
3. **Substrate/cockpit capability**: already correctly homed —
   PlatformVoiceAdapter, TranscriptEvent, VoiceConsentGrant, the governed chat
   rail. Nothing to port.
4. **Projection-specific (stays in LyfeOS)**: NAV_ALIASES/mission/timer verbs,
   `/api/voice-command` handler + prompts, affirmation TTS loop, HUD branding.
5. **Unsafe/stale — explicitly rejected**: ungoverned auto-execute on final
   transcript (violates the hold-at-AWAITING_APPROVAL invariant); no consent
   layer beyond the browser prompt; `replit_integrations/` scaffold lineage;
   client-assembled context with client-supplied conversation id (identity must
   resolve server-side).
