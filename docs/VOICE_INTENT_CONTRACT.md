# VoiceIntentContract

Compiled 2026-07-06 as part of **P4S-31D-VOICE-CAPABILITY-MATRIX-001** (compile
mode). Data artifacts:
`data/umh/voice/platform_voice_feasibility_matrix.json`,
`data/umh/voice/voice_intent_contract_types.json`.

**Compile mode — no voice implementation is authorized by this document.** It
defines the contract, the adapter matrix, and the ordered implementation packets
that come after. Style matches `docs/PROJECTION_CONNECTION_STANDARD.md` and
`docs/REALITY_TEMPLATE_GRAPH.md`.

---

## Owner doctrine (binding)

Voice is a **first-class adapter into Cockpit Chat**, not a second way to reach
the runtime. Voice must never bypass Chat, IntentSpec, WorkPacket, governance,
proof, tenant identity, or server truth.

The proven rail it feeds (P4S-31B/C, merged + browser-proven):

```
Cockpit Chat message
  -> deterministic classify_intent            (substrate/workstation/command_router.py)
  -> governed intent_loop_submit              (registered MutationSpec)
  -> held gate (AWAITING_APPROVAL)            (no auto-advance)
  -> governed approve                         (intent_loop_approval_decision)
  -> PROOF_RECORDED (proof_id, envelope, decided_by = Clerk principal)
```

Voice's ENTIRE job is to put a **transcript** into that chat channel. The entry
seam already exists:
`chatStore.sendMessage(text, 'voice', routing, voiceTurnId)` →
`POST /advisor/converse`.

---

## What already exists (ground truth — the contract binds to this, it does not invent)

| Seam | Location | State today |
|---|---|---|
| Chat voice entry | `cockpit/src/renderer/stores/chatStore.ts::sendMessage(content, source='voice', viewContext, voiceTurnId)` and `addVoiceTranscript(text, voiceTurnId)` | **Exists.** Voice attaches `routing` + `voice_turn_id`, posts the SAME `/advisor/converse` body as text. |
| Wire body | `POST /advisor/converse` `{content, view_context, conversation_id, source, routing?, voice_turn_id?}` | **Exists.** `source` is `'text'|'voice'`; `routing` voice-only. |
| Deterministic gate | `substrate/workstation/command_router.py::classify_intent(text) -> CommandIntent` | **Exists.** Keyword substring scan, **no LLM**. Ignores `source` — a voice message is classified identically to a typed one. |
| Rail dispatch | `transports/api/cockpit_chat_routes.py::try_chat_intent_rail` → `governed_intent_submit` → `IntentLoop.submit` | **Exists, proven.** Held at `AWAITING_APPROVAL`; advances only via `IntentLoop.decide`. |
| Proof chain | `substrate/execution/intent/loop.py` (`submit`/`decide`/`ProofRecord`); MutationSpecs `intent_loop_submit`, `intent_loop_approval_decision` | **Exists, browser-proven** (`docs/audits/2026-07-06_p4s31c_browser_proof.md`). |
| Transcript backend | `umh/voice_server.py` on `ws://:8096/voice`; nginx `/api/umh/voice/ws` → `127.0.0.1:8096/voice` | **Exists** (real STT+TTS bridge, transcript-only). STT = Groq Whisper + faster-whisper fallback; TTS = Kokoro (instance GPU node) + espeak fallback. **NOT** compose/systemd-managed — runs as a host process; lifecycle is a known gap (see below). |
| Routing metadata | `cockpit/src/renderer/stores/deviceSessionStore.ts::getRoutingMetadata()` → `{source_device_id, source_session_id, control_surface, audio_return_route}` | **Exists.** No tenant/principal fields — identity is resolved server-side. |
| Device binding | `substrate/workstation/device_presence.py::DeviceSession`; `substrate/workstation/voice_route_resolver.py::VoiceRoute` | **Exists.** VoiceRoute is a governance-NEUTRAL routing hint (execution_target/audio), not an authority. |
| Voice UI state | `cockpit/src/renderer/stores/voiceStore.ts` (`micState`, `ttsState`, `voicePresentationStatus`, `activationMode` = `manual|wake_word|clap|always_on`); rendered in `RightRail.tsx`, `VoiceRouteHud.tsx`, `VoiceCommandBar.tsx` | **Exists.** The mic affordances, HUD, and TTS status are already built. |
| Correlation id | `voice-turn-assembler.ts::voiceTurnId` (`vt-<uuid>`) | **Exists.** Threads capture → transcript → chat → loop. |

**The doctrine is already the design of the shipping code.** `umh/voice_server.py`'s
own header states: *"This server handles ONLY audio I/O … All intelligence
(intent classification, conversation routing, governance) flows through
DEXConversation via the browser's POST … endpoint."* P4S-31D formalizes that
into a testable contract and extends it across platforms.

---

## VoiceIntentContract — how a voice utterance becomes a canonical Chat intent

```
capture (local, consented)
  -> [wake]  (optional; on-device; consent-gated)
  -> transcribe (STT; on-device preferred, server fallback)
  -> TranscriptEvent (text + provenance, NO audio, final=true)
  -> chat channel entry:  sendMessage(text, source='voice', routing, voice_turn_id)
  -> POST /advisor/converse  (SAME endpoint text uses)
  -> try_chat_intent_rail -> classify_intent(text)   (deterministic; source ignored)
  -> [if INTENT_CAPTURE] governed_intent_submit -> IntentLoop.submit
  -> held gate AWAITING_APPROVAL
  -> operator approves in the SAME thread/panel
  -> IntentLoop.decide -> PROOF_RECORDED
  -> server-truth status returns into the SAME cockpit thread
```

### Non-bypass invariants (testable statements)

1. **Same endpoint.** A voice utterance reaches the runtime ONLY through
   `POST /advisor/converse` with `source='voice'`. There is no voice-specific
   submit route. *(Test: no `/intent-loop/submit` or provider call in any voice
   adapter path; voice transcript hits `/advisor/converse`.)*
2. **Same classifier.** `classify_intent` receives `text` only; `source` is never
   passed to it. Voice and text produce identical classification for identical
   text. *(Test: `classify_intent(t)` deterministic and source-independent — the
   existing `test_chat_rail_classification_is_deterministic` already pins this.)*
3. **Same gate.** A voice-originated `INTENT_CAPTURE` holds at `AWAITING_APPROVAL`
   exactly like a typed one; no voice path auto-advances or auto-executes.
   *(Test: submit-from-voice-shaped payload → `stage == AWAITING_APPROVAL`,
   `proof is None`.)*
4. **Same proof.** Approval of a voice-origin loop produces a `ProofRecord` under
   the registered `intent_loop_approval_decision` MutationSpec with
   `governed_success=True`. *(Test: extend the P4S-31C chain by one hop — see
   Tests/proof section.)*
5. **Same identity.** `decided_by` is the authenticated Clerk operator principal
   resolved server-side, never client input, never re-minted by voice. *(Test:
   decided_by equals the session principal; a voice payload cannot set it.)*
6. **Verbatim entry.** The chat message `content` equals the final transcript
   text, unmodified. Voice does not pre-interpret. *(Test: transcript text ==
   chat message content.)*
7. **Transcript-only transit.** No audio bytes cross the chat seam; the
   `/advisor/converse` body carries text, not audio. *(Test: request body has no
   audio field.)*

---

## Typed contract shapes

Full machine-readable field lists:
`data/umh/voice/voice_intent_contract_types.json`. Summaries:

### TranscriptEvent
One STT result before it enters Chat. Carries: `text`, `final` (partials update
draft only; only `final=true` submits), `confidence`, `language` (BCP-47),
`voice_turn_id` (`vt-<uuid>`), `started_at`/`emitted_at` (ISO-8601 UTC),
`source_device_id`/`source_session_id` (opaque, not hostnames), `control_surface`,
`stt_engine`. **Invariant: `carries_audio = false` always.**

### WakeEvent
A wake-word detection. Carries: `keyword`, `confidence`, `detected_at`,
`source_device_id`, `consent_ref` (the `VoiceConsentGrant` that authorizes
wake-listening), `wake_runtime`. **Invariant: `carries_audio = false` always** —
a WakeEvent reports a keyword event, never audio.

### VoiceSession
One operator voice interaction on one surface. Lifecycle `state`:
`consent_pending → consent_granted → mic_opening → capturing → transcribing →
closed` (plus `denied`, `revoked`). Binds `operator_principal` (Clerk
`clerk:user_<id>` — the SAME identity that stamps `decided_by`),
`device_session_id` (→ `DeviceSession.session_id`), `activation_mode`
(`push_to_talk|wake_word|always_on`), `consent_ref`, `device_capability_ref`.
Capture is refused fail-closed without an active consent grant or when
`can_capture_audio=false`.

### DeviceCapabilityProfile
Per-device voice capabilities, keyed by `device_registry_id` from
`infra/device_registry.json` — **never a hardcoded device name.** Fields:
`device_role` (`orchestrator|executor|controller`), `has_microphone` (**false for
orchestrator role always**), `can_play_audio`, `push_to_talk`,
`wake_word_runtime` (`none|on_device|platform_native`), `on_device_stt`,
`ambient_capable` (false unless the feasibility matrix PROVES it), `capture_api`.

### PlatformVoiceAdapter (the ONE adapter interface)
Every platform implements this and nothing more. Methods: `requestConsent`,
`openSession`, `startCapture`, `stopCapture`, `closeSession`. Events:
`onTranscript(TranscriptEvent)` → `chat.sendMessage(text,'voice',routing,
voice_turn_id)`; `onWake(WakeEvent)` (only when mode ∈ {wake_word, always_on});
`onError`; `onStateChange`. Error semantics: **fail-closed** — missing consent,
mic denied, STT down, or WS unavailable → typed refusal (mirrors `voiceStore`
`VoiceOutcome`), never a degraded ungoverned path. Invariants: adapter output is
ALWAYS a chat message via `source='voice'` — never a direct call to
`classify_intent`, `intent_loop_submit`, or `governed_mutation`; adapter never
persists audio; adapter stamps no identity (server resolves the Clerk principal).

### VoiceConsentGrant
Stored, revocable record that an operator authorized capture on a specific device
in a specific mode. `active = granted AND NOT revoked`. **Consent is PER-MODE:** a
`push_to_talk` grant does NOT authorize `always_on`. Wake/ambient capture is
IMPOSSIBLE without an active grant — this is the hard constraint against
always-on mic.

---

## Permission / consent model

- **Explicit consent per device per mode.** `VoiceConsentGrant(operator_principal,
  device_registry_id, activation_mode)`. A grant for one mode never implies
  another.
- **Consent is stored state and revocable.** `revoked_at` set → `active=false` →
  all capture in that mode refused fail-closed.
- **No always-on mic without explicit consent (hard constraint).** `wake_word`
  and `always_on` sessions require an active grant for that exact mode; absent it,
  the adapter refuses to open capture.
- **Two layers.** OS/browser mic permission (per-origin browser prompt, iOS/Android
  TCC/runtime permission) AND the UMH `VoiceConsentGrant`. Both required; either
  missing = refusal.

---

## Privacy / security model

- **Audio lives and dies on-device by default.** Capture buffers stay in the
  `PlatformVoiceAdapter`; only a `TranscriptEvent` (text) crosses the seam.
- **Transcript-only transit.** `/advisor/converse` carries text, never audio.
- **No audio persistence by default.** Transcripts are operator data (they already
  enter chat history); audio is not stored.
- **On-device STT preferred.** `on_device_stt` is the privacy-preferred path where
  the platform supports it (iOS `SFSpeechRecognizer`, Android `SpeechRecognizer`,
  desktop `whisper.cpp`/WebGPU). The existing `voice_server.py` server STT
  (Groq/faster-whisper) is the fallback for surfaces without on-device STT.
- **Cloud transcription is DEFERRED to a privacy review (hard constraint).** This
  document does NOT decide whether/when audio may transit to a cloud STT. Any such
  decision is a separate, owner-gated privacy review. Compile mode records the
  constraint; it does not resolve it.
- **Credential / identity flow.** Voice introduces NO new auth surface. The
  operator Clerk session that already authenticates `/advisor/converse` is the
  identity; `decided_by` is that principal. TTS/STT provider credentials (Groq,
  Kokoro node) flow through the existing secret runtime (1Password `op run`),
  never as plaintext.

---

## Wake-word runtime requirements

- **On-device requirement.** Wake detection runs on-device (openWakeWord /
  Porcupine-class, or platform-native). No audio streams off-device for wake
  detection.
- **Candidate runtimes.** Desktop app: `porcupine_native` / `openwakeword_onnx` /
  platform-native (macOS SpeechRecognizer). Browser: `porcupine_web_wasm` /
  `openwakeword_wasm` (foreground-active only). Mobile app:
  `porcupine_ios_android` / `openwakeword_mobile` (foreground; background is
  constrained — see matrix).
- **CPU / battery budget.** The on-device wake runtime MUST respect the CPU Gate
  Law — it may not saturate CPU on any host. On mobile it must respect a battery
  budget; always-on is battery-hostile and ships last, if at all.
- **What the orchestrator NEVER does.** The orchestrator-role node (per
  `infra/device_registry.json`) NEVER runs a microphone, capture, wake runtime, or
  STT. **No mic on the VPS.** `DeviceCapabilityProfile.has_microphone=false` for
  the orchestrator role, always.

---

## Platform voice adapter matrix (feasibility)

Full rows + per-platform reasoning:
`data/umh/voice/platform_voice_feasibility_matrix.json`. Verdict summary:

| Target | Push-to-talk | Wake-word | Ambient (always-on) |
|---|---|---|---|
| **desktop browser** | **PROVEN** (already shipping on `:8096`) | CONSTRAINED (in-tab WASM, foreground-active only) | CONSTRAINED (tab must stay active) |
| **desktop app** (Electron) | LIKELY | **LIKELY** (main-process on-device runtime — cleanest wake path) | CONSTRAINED (ships last, on-device, consented) |
| **mobile app** (native) | LIKELY | CONSTRAINED (foreground on-device OK; background = Android FGS only, iOS blocked) | Android: CONSTRAINED (foreground service). **iOS background: NOT_FEASIBLE** |
| **mobile browser** (PWA) | CONSTRAINED (tap-to-talk; iOS Safari drops mic on background/lock) | **NOT_FEASIBLE** (no background execution) | **NOT_FEASIBLE** |
| **desktop ambient wake word** | — | LIKELY on desktop app; CONSTRAINED on browser | CONSTRAINED (desktop app, on-device, consented, last) |
| **mobile ambient wake word** | — | CONSTRAINED (foreground app only); background NOT_FEASIBLE (iOS) / CONSTRAINED (Android FGS) | **NOT_FEASIBLE** (no compliant hands-free always-on) |

**Mobile ambient is NOT promised.** iOS App Review blocks continuous background
mic for a non-audio utility app; Android background wake is only a battery-hostile
foreground-service approximation. The matrix records these as CONSTRAINED /
NOT_FEASIBLE by defensible platform policy, not a roadmap commitment. Any mobile
ambient work requires a platform spike + privacy review + owner sign-off before it
may be scheduled.

---

## Implementation sequence (packets AFTER this compile — hard-held until owner calls)

Ordered so each packet proves before the next builds on it. Every packet extends
the P4S-31C browser-proof pattern by exactly one hop: **spoken word → transcript
in chat → same `loop_id` chain → same `proof_id` / `decided_by`.** All are
`hard_hold` until the owner explicitly starts P4S-31D-1.

| Packet | Objective | Proof requirement |
|---|---|---|
| **P4S-31D-1** | Desktop-browser **push-to-talk** into the Chat intent rail: formalize the `PlatformVoiceAdapter` over the existing `:8096` `voice_server` + `sendMessage('voice')`; add `VoiceConsentGrant(push_to_talk)`. Also close the voice_server **lifecycle gap** (compose/systemd unit) so the seam is managed, not hand-started. | Unit + shape tests: TranscriptEvent → chat message verbatim; consent gate fail-closed; no `/intent-loop/submit` in the voice path. |
| **P4S-31D-2** | **Browser proof** (extend P4S-31C): real Chrome on the executor node — spoken utterance → transcript in chat → held gate → governed approve → `proof_recorded`, all ids from the real run, `decided_by` = Clerk principal. | Class-A browser evidence; server-truth read confirms the loop at `proof_recorded`; secret scan clean. |
| **P4S-31D-3** | **Desktop app** (Electron) push-to-talk + **on-device wake-word** (main-process runtime, `VoiceConsentGrant(wake_word)`), CPU-budgeted. | Wake → capture only under active grant; revoke → capture refused; same rail/proof chain. |
| **P4S-31D-4** | **Mobile app** push-to-talk (on-device STT), controller role. | Foreground capture → transcript → same rail; identity = mobile Clerk principal. |
| **P4S-31D-5** | **Mobile browser** tap-to-talk (constrained; no wake). | Tap → transcript → same rail; graceful refusal on background/lock. |
| **P4S-31D-6** (LAST, owner-gated) | **Ambient / always-on** — desktop app only, on-device wake, `VoiceConsentGrant(always_on)`, CPU/battery budget. Mobile ambient only if a platform spike + privacy review clears it. | Consent revocation kills capture immediately; no cloud STT without the privacy review; same rail/proof chain. |

Sequencing rules: push-to-talk before wake; wake before ambient; a proof packet
follows every capability packet; ambient is last and owner-gated; the cloud-STT
decision is never taken inside any of these — it is a separate privacy review.

---

## Tests / proof requirements (what ANY voice implementation packet must prove)

Every voice packet's acceptance is the **P4S-31C server-truth chain extended by
one hop**:

1. **Transcript enters chat verbatim as a canonical event.** The chat message
   `content` equals the final `TranscriptEvent.text`; the message carries
   `source='voice'` and the `voice_turn_id`.
2. **No separate execution path.** The utterance reaches the runtime ONLY via
   `POST /advisor/converse`. Static check: the voice adapter contains no
   `/intent-loop/submit`, no `governed_mutation`, no provider call, no
   `classify_intent` call — output is always `sendMessage('voice')`.
3. **Deterministic classification, source-independent.** `classify_intent(text)`
   yields the same result for voice and text; no LLM in the path.
4. **Gate holds.** A voice-origin `INTENT_CAPTURE` lands at `AWAITING_APPROVAL`
   with `proof is None`; no auto-advance, no auto-execution.
5. **Consent gates enforced fail-closed.** Wake/ambient capture without an active
   `VoiceConsentGrant(mode)` is refused with a typed error; revoking a grant
   mid-session stops capture.
6. **Identity stamped correctly.** `decided_by` on the resulting `ProofRecord`
   equals the authenticated Clerk operator principal; a voice payload cannot set
   or spoof it.
7. **Server-truth proof.** Independent read of `/api/umh/intent-loop` confirms the
   loop at `proof_recorded` with matching `proof_id` / `envelope_id` — the same
   verification P4S-31C used, one hop further back (spoken word instead of typed).
8. **No audio leaves the device by default; no audio persisted.** Request body
   carries text only; secret/audio scan on evidence is clean.
9. **Browser proof runs on an executor-role node** with a real interactive Chrome
   session (Browser Verification Law) — never on the orchestrator.

An implementation packet that cannot produce items 1–7 as server-truth from a real
run is not complete, regardless of what the UI appears to do (the P4S-31C
false-positive audit is the precedent: panel rendering is not proof).
