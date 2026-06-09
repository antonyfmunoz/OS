# Phase 14.13V — Voice UX Seal Report

**Date:** 2026-06-09
**Branch:** worktree-voice-ws-proxy-fix
**Status:** COMPLETE

## Summary

Sealed the voice UX so DEX feels like one coherent organism response.
Three bugs addressed:
1. iPhone TTS not audible (iOS audio policy)
2. Text/audio feel separate (organism response commit)
3. STT pauses create duplicate turns (voice turn assembly)

## Task 1: TTS Playback + iPhone Audio

**New file:** `cockpit/src/renderer/api/tts-playback-controller.ts`

- TtsPlaybackState interface with audioUnlocked, unlockAttempted, unlockError, playbackStatus
- unlockAudioForIOS() creates silent WAV, calls play() to satisfy iOS autoplay policy
- Called from startVoice() on mic tap (user gesture context)
- playTtsAudio(buffer) reuses unlocked Audio element or creates new one
- Sequential chunk playback via internal queue with _drainQueue()
- cancelPlayback() and resetPlayback() for cleanup
- All [TTSPlayback] log events instrumented
- Playback rejection callback surfaces iOS blocks to UI

**Modified:** `voice-ws.ts` — imports tts-playback-controller for _playNext()
**Modified:** `voice-controller.ts` — calls unlockAudioForIOS on mic tap, wires playback callbacks
**Modified:** `voiceStore.ts` — added OrganismResponseEnvelope, PresentationStatus types

## Task 2: Organism Response Commit

**Modified:** `voiceStore.ts`
- OrganismResponseEnvelope interface (messageId, content, spokenText, metadata, ttsReady, ttsError, voiceTurnId)
- PresentationStatus type (idle -> thinking -> preparing_response -> preparing_voice -> ready_to_commit -> committing -> presenting -> complete)
- New state fields: voicePresentationStatus, activeTtsJobId, heldEnvelope

**Modified:** `chatStore.ts`
- draftMessage and placeholderMessage state fields
- setDraftMessage(), commitDraftMessage() for live "YOU is speaking..." bubble
- setPlaceholderMessage(), clearPlaceholderMessage() for "DEX is thinking..."
- sendMessage() now accepts voiceTurnId parameter
- addVoiceTranscript() forwards voiceTurnId

**Modified:** `RightRail.tsx`
- Renders draft bubble during recording with mic icon + "speaking..." badge
- Renders "thinking..." placeholder during voice flow
- Renders "preparing voice..." during TTS generation
- Renders tap-to-play button when iOS blocks audio

## Task 3: Voice Turn Assembly + Dedup

**New file:** `cockpit/src/renderer/api/voice-turn-assembler.ts`

- VoiceTurnState interface (voiceTurnId, status, partialText, finalSegments, assembledText)
- VoiceTranscriptSegment interface (text, timestamp, index)
- createTurn() generates crypto.randomUUID-based voice_turn_id
- appendSegment() adds final segments, deduplicates
- updatePartial() updates live partial text for draft bubble
- commitTurn() assembles all segments into final text
- normalizeTranscript() trims and collapses whitespace
- deduplicateSegments() handles subset, superset, and overlapping segments
- getSilenceTimeoutMs() returns 1600ms desktop / 2200ms mobile
- startSilenceTimer() with configurable callback

**Modified:** `voice-controller.ts`
- Creates turn on mic start
- Appends segments on final transcript (does NOT dispatch immediately)
- Starts/restarts silence timer on each segment
- Silence timeout triggers _dispatchCommittedTurn()
- Tap-to-stop commits immediately via commitTurn()
- Barge-in (VAD while DEX speaking) cancels TTS and creates new turn
- Draft bubble updates on every segment and partial
- _pendingVoiceTurnId tracked for response correlation
- voicePresentationStatus transitions through lifecycle

**Modified:** `chatStore.ts` — passes voice_turn_id to /advisor/converse

**Modified:** `transports/api/cockpit.py` — extracts voice_turn_id from payload, passes to converse()

**Modified:** `substrate/organism/advisor_conversation.py`
- converse() accepts voice_turn_id parameter
- _voice_turn_cache: dict mapping voice_turn_id -> (AdvisorResponse, timestamp)
- Cache hit returns stored response without LLM call
- Cache TTL: 10 minutes, cleaned on access via _clean_voice_turn_cache()

## Task 4: Tests

**New file:** `tests/test_voice_turn_assembly.py` — 23 tests
- File existence and export verification
- Controller integration (imports assembler, dispatches via it)
- Barge-in and tap-to-stop patterns
- Silence timer values (1600ms/2200ms)
- Deduplication logic (overlap, subset, superset, merge)
- Draft bubble support in chatStore and RightRail

**New file:** `tests/test_voice_idempotency.py` — 8 tests
- Same voice_turn_id returns cached response (LLM called once)
- Different voice_turn_id creates new response
- No voice_turn_id skips cache
- Text chat path unchanged
- Cache expiry after TTL
- One turn = one response (3x calls, 1 LLM)
- converse() signature includes voice_turn_id
- cockpit.py passes voice_turn_id through

**Extended:** `tests/test_voice_identity.py` — 14 new tests (29 total)
- OrganismResponseEnvelope structure verification
- PresentationStatus all states present
- voiceStore presentation fields
- spoken_text used for TTS
- Metadata visible not spoken
- Routing preserved in response
- TTS playback controller existence and exports
- Controller uses tts-playback-controller

## Verification

```
tests/test_voice_turn_assembly.py    23 passed
tests/test_voice_idempotency.py       8 passed
tests/test_voice_identity.py         29 passed
tests/test_device_presence.py        25 passed (regression)
tests/test_voice_route_resolver.py   32 passed (regression)
                                    117 total, 0 failed
TypeScript typecheck:                clean (0 errors)
Python py_compile:                   all modified files pass
```

## Files Changed

### New (4)
- cockpit/src/renderer/api/tts-playback-controller.ts
- cockpit/src/renderer/api/voice-turn-assembler.ts
- tests/test_voice_turn_assembly.py
- tests/test_voice_idempotency.py

### Modified (7)
- cockpit/src/renderer/api/voice-ws.ts
- cockpit/src/renderer/api/voice-controller.ts
- cockpit/src/renderer/stores/voiceStore.ts
- cockpit/src/renderer/stores/chatStore.ts
- cockpit/src/renderer/components/RightRail.tsx
- substrate/organism/advisor_conversation.py
- transports/api/cockpit.py

### Extended (1)
- tests/test_voice_identity.py

## Architecture Compliance
- No new dependencies added
- substrate/ does not import from transports/ or services/
- All Python is 3.11 compatible (no match statements)
- All exceptions logged (no silent except-pass)
- Type coherence: no new types in substrate/canonical_types.py needed
- Deterministic-first: routing, assembly, dedup all use rules/logic, no LLM
