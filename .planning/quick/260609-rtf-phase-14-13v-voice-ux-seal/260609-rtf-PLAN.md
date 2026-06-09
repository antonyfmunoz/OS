# Phase 14.13V — Voice UX Seal Plan

## Task Description
Seal the voice UX so DEX feels like one coherent organism response. Three bugs to fix:
1. iPhone TTS not audible (iOS audio policy / format / session routing)
2. Text/audio feel separate (need organism response commit — text+TTS together)
3. STT pauses create duplicate turns (need voice turn assembly + grace window)

## Must-Haves
- truths:
  - iPhone TTS playback instrumented with [TTSPlayback] logs
  - Audio unlocked on mic tap gesture (iOS policy)
  - TTS jobs addressed to source session
  - WAV format verified playable on iOS (or transcode to MP3)
  - Organism response envelope type created
  - DEX text+audio committed together (not text-first)
  - Tap-to-play fallback for iOS autoplay blocks
  - spoken_text used for TTS, metadata visible but never spoken
  - voice_turn_id created per recording session
  - Voice turn assembler collects segments before dispatch
  - End-of-turn grace window (1600ms desktop, 2200ms mobile)
  - Tap-to-stop commits immediately
  - Live draft bubble during recording (no duplicate YOU messages)
  - Backend idempotency guard on voice_turn_id
  - Transcript deduplication (overlapping segments merged)
  - Barge-in creates new turn
  - Phase 14.13U routing preserved
  - All tests pass
  - TypeScript clean

## Tasks

### Task 1 — TTS Playback + iPhone Audio (Workcells A, B, C, D, H)
Files to modify:
- cockpit/src/renderer/api/voice-ws.ts
- cockpit/src/renderer/api/voice-controller.ts
- cockpit/src/renderer/stores/voiceStore.ts

New files:
- cockpit/src/renderer/api/tts-playback-controller.ts

Work:
1. Create tts-playback-controller.ts with TtsPlaybackState interface
2. Add [TTSPlayback] instrumentation to voice-ws.ts _playNext()
3. On mic tap (startVoice), create/unlock a persistent Audio element
4. Store unlock state in TtsPlaybackState
5. When TTS binary arrives, reuse unlocked audio element
6. Add session matching check (audio_output_session_id vs current)
7. Log all events per Workcell A spec
8. Add tap-to-play fallback UI state when playback rejected
9. Verify WAV playback on iOS — if audio/wav fails, test audio/mpeg path

### Task 2 — Organism Response Commit + Presentation (Workcells E, F, G, I)
Files to modify:
- cockpit/src/renderer/api/voice-controller.ts
- cockpit/src/renderer/stores/voiceStore.ts
- cockpit/src/renderer/stores/chatStore.ts
- cockpit/src/renderer/components/RightRail.tsx

Work:
1. Add OrganismResponseEnvelope interface to voiceStore
2. Add presentation state machine: thinking → preparing_response → preparing_voice → ready_to_commit → committing → presenting → complete
3. For voice responses: hold DEX message (don't show final text yet)
4. Show placeholder "DEX is thinking..." → "DEX is preparing voice..."
5. When TTS ready (or failed): commitOrganismResponse()
6. In one requestAnimationFrame: reveal DEX bubble + audio.play()
7. If audio.play() rejects: show text + exact blocker + tap-to-play
8. Ensure spoken_text used for TTS, metadata visible not spoken

### Task 3 — Voice Turn Assembly + Dedup (Workcells J, K, L, M, N, O, P, Q, R, S)
Files to modify:
- cockpit/src/renderer/api/voice-controller.ts
- cockpit/src/renderer/stores/voiceStore.ts
- cockpit/src/renderer/stores/chatStore.ts
- substrate/organism/advisor_conversation.py
- transports/api/cockpit.py
- umh/voice_server.py

New files:
- cockpit/src/renderer/api/voice-turn-assembler.ts

Work:
1. Create voice-turn-assembler.ts with VoiceTurnState, VoiceTranscriptSegment
2. On mic start: create voice_turn_id via crypto.randomUUID()
3. STT final segments append to current turn (don't dispatch immediately)
4. Start/restart end-of-turn silence timer (1600ms desktop, 2200ms mobile)
5. On silence timeout: assemble all segments, commit one YOU message
6. On tap-to-stop: immediate commit of assembled segments
7. Live draft bubble: show single updating "YOU is speaking..." bubble
8. Transcript dedup: normalize + merge overlapping segments
9. Barge-in: if DEX speaking and user speaks, cancel TTS + new turn
10. Send voice_turn_id in /dex/converse payload
11. Backend idempotency: advisor_conversation.py caches voice_turn_id → response
12. cockpit.py passes voice_turn_id through
13. Add [VoiceTurn] logs per Workcell S spec

### Task 4 — Tests + Report (Workcells T, U, V)
Files:
- tests/test_voice_turn_assembly.py
- tests/test_voice_idempotency.py
- tests/test_voice_identity.py (extend)
- data/umh/trinity_convergence/phase14_13v_voice_ux_seal_report.md

Work:
1. Write test_voice_turn_assembly.py: pause doesn't commit immediately, multiple segments commit one message, mobile silence longer, tap-stop commits, duplicate segments deduped, overlapping replaced, voice_turn_id sent, barge-in creates new turn, late segment after commit ignored
2. Write test_voice_idempotency.py: same voice_turn_id returns idempotent response, one turn one response, text chat path unchanged
3. Extend test_voice_identity.py: organism response envelope, commit timing, playback rejection, spoken_text usage, routing regression
4. Run all Python tests
5. Run TypeScript typecheck + build
6. Create final report
