# LiveVoiceSession Runtime — P4S-LIVE-VOICE-SESSION-001

Compiled 2026-07-07. Canonical artifact: `data/umh/voice/live_voice_session_compile.json`.

**Compile mode — no activation authorized.** This document defines the target
shape of the LiveVoiceSession runtime and nothing more. No live-session runtime,
no live-mode default-voice response, no auto-execute path, and no new consent
mode ships with this artifact. Style matches `docs/VOICE_MESSAGE_CONTRACT.md`.

## Voice taxonomy — what this packet IS and IS NOT

LiveVoiceSession is **category 2** of the canonical voice taxonomy in
`docs/VOICE_MESSAGE_CONTRACT.md` / `data/umh/voice/voice_message_contract.json`.

| Category | Meaning | Status here |
|---|---|---|
| UserVoiceNote | record audio → review draft → send | **NOT this packet** — shipped as P4S-31D1-B |
| **LiveVoiceSession** | **real-time conversation with DEX; voice is the DEFAULT response in live mode; transcript AND events STILL hit the Cockpit Chat ledger; actions STILL require governance (hold-at-AWAITING_APPROVAL, proof)** | **THIS ARTIFACT — compile only, no activation.** |
| AmbientActivation | wake word / hotkey opens a session | NOT this packet — held (`P4S-AMBIENT-ACTIVATION-001`) |
| AIOutboundVoiceMessage | AI renders the operator's authorized voice for external send | NOT this packet, NOT built (`P4S-AI-OUTBOUND-VOICE-MESSAGE-001`) |
| ManualCockpitControl | approve / reject / execute / retry / inspect | execution controls, not intent ingress |

**LiveVoiceSession is a live real-time conversation with DEX/Jarvis.** It is NOT
dictation, NOT ambient, and NOT outbound AI voice. It remains a first-class
adapter into Cockpit Chat — never a second way to reach the runtime.

## The product

A live session is a **loop of governed turns**:

```
engage live mode (consent-gated: VoiceConsentGrant(live_session) — FUTURE mode)
  -> listening              (mic open, VAD watching)
  -> capturing / transcribing (server STT: Groq whisper -> faster-whisper)
  -> operator transcript enters chat VERBATIM
       via sendMessage(text,'voice',routing,voice_turn_id) -> POST /advisor/converse
  -> responding             (voice is the DEFAULT response in live mode: text turn + TTS)
  -> ledger write           (BOTH operator + assistant turns via converse()/_save_turn)
  -> back to listening      (next turn; barge-in may interrupt DEX at any time)
  -> close                  (operator ends live mode / revoke / flag off / WS lost)
```

Voice does its entire job by putting a transcript into the SAME chat channel the
typed rail uses. The response is spoken by default while live mode is engaged,
but the ledger record is always the text.

## Binding rules (a future implementation MUST satisfy — see JSON for full shapes)

1. **Voice-default response, text always recorded.** While live mode is engaged
   DEX responds by voice (TTS via the existing `tts_request` seam) by default.
   Voice is the presentation, not a replacement: every DEX response still writes
   a text turn to the Cockpit Chat ledger, and voice is rendered from that text.
   If TTS fails, the text turn still commits — voice-default degrades to text,
   never to a lost turn (Deterministic-First Principle).
2. **Everything hits the ledger.** Each operator transcript and each DEX response
   is persisted through `DEXConversation.converse()` → `_save_turn()` — the same
   path a typed conversation uses. There is no private, unlogged live channel and
   no second store. Operator messages carry `source='voice'` and the
   `voice_turn_id`; content equals the final `TranscriptEvent.text`, unmodified.
3. **Governance is never bypassed. A live session NEVER auto-executes.**
   Conversational turns are chat. Any ACTION a live turn implies takes the SAME
   path a typed action takes: `try_chat_intent_rail` → deterministic
   `classify_intent(text)` → `governed_intent_submit` → `IntentLoop.submit`
   **held at AWAITING_APPROVAL**. The live session surfaces the held item
   in-thread and waits for an explicit governed approve; only `IntentLoop.decide`
   advances it to `PROOF_RECORDED`. Being in voice/live mode grants no extra
   authority — `classify_intent` ignores `source`, so a spoken action is
   classified and gated identically to a typed one.
4. **Barge-in is reused, not reinvented.** Turn-taking is half-duplex with a
   barge-in override: the operator can interrupt DEX at any time. This REUSES the
   existing barge-in in `cockpit/src/renderer/api/voice-controller.ts` — when VAD
   goes active while `ttsState === 'speaking'`, the client calls `cancelTts()` +
   `cancelPlayback()` and sets `micState = 'interrupted'`. No new barge-in
   mechanism is defined.
5. **Consent is per-mode; `live_session` is future-grantable, not grantable now.**
   A live session requires a NEW `VoiceConsentGrant(live_session)` mode. A
   `push_to_talk` grant does NOT authorize a live session. This mode is DECLARED
   here as future-grantable only — no grant of it may be created and no UI to
   grant it may ship until the LiveVoiceSession packet is owner-authorized.
   Absent an active `live_session` grant, live mode refuses fail-closed
   (`CONSENT_REQUIRED`). Revoking the grant closes the session immediately. The
   orchestrator-role node never opens a live session (no mic on the orchestrator).
6. **Same identity, same proof.** `decided_by` on any resulting `ProofRecord` is
   the authenticated Clerk operator principal resolved server-side, never set by
   a voice payload. A live-origin `INTENT_CAPTURE` extends the P4S-31C proof
   chain by exactly one hop (spoken word instead of typed).
7. **Transcript-only transit.** `/advisor/converse` carries text, never audio.
   STT audio is written to a temp WAV for the STT call only and unlinked
   immediately; transcript text is never logged at INFO (≤40-char DEBUG previews).

## Session lifecycle (states)

`closed → opening → listening → capturing → transcribing → responding →
ledger_write → listening …` (loop of turns), with `→ closing → closed` on end,
and a `responding → listening` barge-in edge. Full transitions in the JSON
`session_lifecycle`. A turn ends on an utterance-boundary silence — **a silence
never triggers an action and never sends anything ungoverned.** Ending a turn
does not end the session; ending the session releases the mic.

## STT / TTS path

- **STT:** server STT via `umh/voice_server.py` — Groq `whisper-large-v3-turbo`,
  `faster-whisper` fallback. Transcript-only transit; audio never persisted.
- **TTS:** server TTS via `umh/voice_server.py` `tts_request` — Kokoro on the
  instance GPU node, espeak fallback. TTS renders DEX's response for the operator
  **inside the live session only**. It never renders the operator's authorized
  voice, never sends voice to a third party, and never clones any voice — that is
  `AIOutboundVoiceMessage`, not this artifact.
- The voice_server WS protocol is UNCHANGED — LiveVoiceSession composes existing
  messages, it does not add a wire protocol.

## State / store shape

The live session reuses the existing `voiceStore` (`micState`, `ttsState`,
`vadActive`, `heldEnvelope` / `OrganismResponseEnvelope`, `consentState`,
`lastOutcome`). It does NOT fork a parallel store. The future fields a real
implementation would add (`liveSessionState`, `liveSessionId`, `liveModeEngaged`,
`turnIndex`) are DECLARED in the JSON `state_store_shape.future_fields_declared_not_added`
— this compile artifact does not add them.

## CPU-gate budget

Bound by the existing `umh-voice-server.service` unit (`CPUQuota=150%` /
`MemoryMax=1G`, the measured worst case with the `faster-whisper` fallback).
LiveVoiceSession adds NO new server process and MUST NOT raise these bounds
without re-measuring (CPU Gate Law). On sustained breach the session degrades —
TTS dropped first (text-only turns still commit), then fail-closed session close
— rather than saturating the host. A live session is operator-engaged and
inactivity-bounded; it is not an always-on mic.

## Rollback

- **Flag off → no live mode.** The live-mode feature flag defaults OFF; with it
  OFF no live session can open. This is the primary rollback.
- **Revoke → immediate close.** Revoking `VoiceConsentGrant(live_session)` stops
  capture and closes any open session immediately.
- **Artifact rollback is a no-op on runtime.** This artifact activates nothing;
  reverting the compile commit removes documentation only.

## Reuse (build on, don't duplicate)

- Capture transport: `voice-ws.ts` PCM16 → `umh/voice_server.py` (WS unchanged)
- STT/TTS: `umh/voice_server.py` (Groq/faster-whisper + Kokoro/espeak)
- Chat entry + ledger: `chatStore.sendMessage(text,'voice',…)` →
  `POST /advisor/converse` → `DEXConversation.converse()` → `_save_turn()`
- Held gate: `try_chat_intent_rail` → `governed_intent_submit` → `IntentLoop`
- Barge-in: `voice-controller.ts` `vad_status` handler (existing)
- Presentation: `voiceStore` `OrganismResponseEnvelope` / `heldEnvelope`
- Turn correlation: `voice-turn-assembler.ts` `voice_turn_id`

## Hard constraints and stop conditions

See the JSON `forbidden_in_this_packet` — no implementation, no activation, no
auto-execute of voice-implied actions, no `live_session` grant now, no provider
execution, no outbound AI voice / cloning, no separate execution path, no
ambient activation, no new server process. Voice never bypasses Cockpit Chat or
the governed intent loop.
