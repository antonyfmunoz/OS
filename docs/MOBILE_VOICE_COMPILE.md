# Mobile Voice Compile — P4S-31D-4 (app) + P4S-31D-5 (browser)

Compiled 2026-07-06, Lane F of the voice wave. Data artifact:
`data/umh/voice/mobile_voice_compile.json`. Validation:
`tests/test_p4s31d_mobile_compile_artifacts.py`.

**Compile mode — no activation authorized.** This document plans the mobile-app
push-to-talk packet (P4S-31D-4) and the mobile-browser tap-to-talk packet
(P4S-31D-5). It implements nothing and authorizes nothing. Both packets remain
hard-held behind P4S-31D-1..3 per the implementation sequence in
`docs/VOICE_INTENT_CONTRACT.md`. Style and doctrine match that contract; this
plan **deepens** the verdicts in
`data/umh/voice/platform_voice_feasibility_matrix.json` and contradicts none of
them.

---

## Doctrine (unchanged, restated)

Voice is a thin adapter into Cockpit Chat. A mobile utterance becomes a
transcript that enters the SAME rail as typed text:

```
capture (local, consented, foreground)
  -> transcribe (on-device STT preferred; server fallback over authenticated WS)
  -> TranscriptEvent (text only, carries_audio = false)
  -> sendMessage(text, source='voice', routing, voice_turn_id)
  -> POST /advisor/converse                    (SAME endpoint text uses)
  -> classify_intent (deterministic, source-ignored)
  -> governed intent loop -> held gate -> approve -> PROOF_RECORDED
```

Mobile adds **no** new execution path, **no** new auth surface, **no** new
classifier. Everything below is lifecycle and permission engineering around
that one seam.

---

## Owner observation, 2026-07-06 (recorded)

The owner pressed push-to-talk on a **mobile browser** and received the
consent-required refusal (typed `CONSENT_REQUIRED`; the mic never opened).

- **The refusal was correct.** Capture without an active
  `VoiceConsentGrant(push_to_talk)` for that device must fail closed. This is
  the contract working, not a bug.
- **The gap was UX, not contract.** The grant path was not reachable from the
  refusal on a small viewport. Lane A is closing that consent UX gap.
- **Binding implication for this plan:** every mobile surface must render the
  resolution inside the refusal itself — an inline, thumb-reachable
  "enable push-to-talk on this device" affordance on the `CONSENT_REQUIRED`
  outcome. No desktop settings rail required to recover.
- Mobile browser PTT remains **CONSTRAINED** per the matrix — iOS Safari drops
  the mic on tab background / screen lock. The observation confirms the
  matrix; it does not soften it.

---

## Push-to-talk feasibility per surface

| Surface | Verdict (matrix row) | Tap-to-talk semantics | What breaks on background / lock |
|---|---|---|---|
| **Native iOS** | LIKELY (`mobile_app.push_to_talk`) | Explicit mic button, toggle: tap opens capture (consent + TCC gated), tap/VAD-end stops. Foreground only. | Background/lock interrupts `AVAudioSession` and capture ends — no `audio` UIBackgroundMode is claimed. Adapter emits typed `CAPTURE_ENDED`, discards buffers; resume needs a fresh tap. |
| **Native Android** | LIKELY (`mobile_app.push_to_talk`) | Same toggle tap-to-talk behind `RECORD_AUDIO` runtime grant. Foreground activity only. | Activity pause / lock stops capture. Android 10+ blocks background mic without a mic-type FGS — and P4S-31D-4 ships **no** foreground service. Typed `CAPTURE_ENDED`; fresh tap to resume. |
| **Mobile Safari** (all iOS browsers — WebKit) | CONSTRAINED (`mobile_browser.push_to_talk`) | Tap-to-talk **toggle**, not press-and-hold: `getUserMedia` + `AudioContext.resume()` must run inside a direct user gesture; long-press collides with iOS selection callouts. First tap also unlocks TTS audio output in the same gesture chain. | Tab background or screen lock ends the mic track immediately and freezes timers; the WS may drop. Track `ended` = session end: typed refusal, no buffered audio, no auto-reacquire — new gesture required. This is P4S-31D-5's graceful-refusal requirement. |
| **Mobile Chrome** (Android) | CONSTRAINED (`mobile_browser.push_to_talk`) | Same toggle semantics for parity. Per-origin mic permission persists better than iOS. | Backgrounded tab throttled, capture suspended; lock stops capture. Policy is identical to mobile Safari: visibility-hidden or track end = clean session end. No background capture attempted on any mobile browser. |

Capture format on every surface that reaches the server: PCM16 mono 16 kHz —
the exact protocol `cockpit/src/renderer/api/voice-ws.ts` already speaks.

---

## Mobile browser limitations (P4S-31D-5 design envelope)

- **Autoplay policy.** TTS playback needs a prior user gesture. The first PTT
  tap doubles as the unlock; TTS arriving before unlock is queued or dropped
  with a typed `TTS_BLOCKED` state — never a silent failure.
- **Mic policy.** Per-origin permission; iOS grants are effectively ephemeral
  (frequent re-prompts). Every session start may need a fresh browser prompt
  IN ADDITION to the UMH `VoiceConsentGrant`. Two layers, both required,
  either missing = fail-closed refusal.
- **WS keepalive.** A backgrounded tab freezes timers → ping/pong stops → the
  nginx proxy (`/api/umh/voice/ws` → `127.0.0.1:8096/voice`) idle-times the
  socket. Policy: don't fight it. End the capture session on visibility loss
  (`mic_stop`), reconnect lazily on the next foreground user gesture, never
  buffer or replay audio across a reconnect.
- **PWA constraints.** Installing the cockpit as a PWA upgrades nothing on
  iOS: no background execution, no service-worker microphone, capture only in
  the active window, dies on lock. PWA install is icon-and-chrome UX only.
  Wake word and ambient stay **NOT_FEASIBLE** on mobile browser, exactly as
  the matrix records.
- **Consent UX on a small viewport.** Per the owner observation: the
  `CONSENT_REQUIRED` refusal carries its own inline grant affordance,
  round-tripping the same `/voice/consent` surface the desktop adapter uses
  (`GET /voice/consent`, `POST /voice/consent/grant|revoke`). Lane A owns the
  fix; this plan consumes it.

---

## Native app permissions (P4S-31D-4 design envelope)

**iOS**

- `Info.plist`: `NSMicrophoneUsageDescription` (mandatory) and
  `NSSpeechRecognitionUsageDescription` (mandatory when `SFSpeechRecognizer`
  is used).
- TCC: microphone and speech recognition are **separate** prompts; both
  required for on-device STT. Either denied → typed refusal with a Settings
  deep link. No silent retries.
- Background modes: **none claimed.** No `audio` UIBackgroundMode — claiming
  it to keep the mic alive in a non-audio utility app is an App Review
  rejection risk and would contradict the matrix `ios_background`
  NOT_FEASIBLE verdict.

**Android**

- Manifest: `RECORD_AUDIO` (dangerous, runtime-requested), `INTERNET`.
- Runtime flow: request `RECORD_AUDIO` on the FIRST push-to-talk tap, never at
  install/launch. Denial → typed refusal; permanent denial → refusal with a
  Settings deep link.
- Foreground service types: **not shipped in P4S-31D-4.** PTT is strictly
  foreground. If the owner ever approves the CONSTRAINED Android-background
  slice (separate, owner-gated, post-privacy-review), it would require
  `FOREGROUND_SERVICE` + `FOREGROUND_SERVICE_MICROPHONE`,
  `android:foregroundServiceType="microphone"` (mandatory Android 14+), and a
  persistent user-visible notification. Recording the requirement is
  documentation of the constraint, not a plan to build it.

---

## Background / ambient feasibility (matrix verdicts, restated verbatim)

**No mobile ambient or background listening is promised by this plan.**

| Slice | Verdict |
|---|---|
| iOS background mic | **NOT_FEASIBLE** — no compliant continuous-background-mic path for a non-audio utility app; App Review blocks it |
| iOS foreground ambient | CONSTRAINED — screen-on, consented; not scheduled by these packets |
| Android background mic | **CONSTRAINED** — mic-type foreground service only (persistent notification, Android 14 FGS declaration), battery-costly; deferred, owner-gated |
| Android foreground ambient | CONSTRAINED — not scheduled by these packets |
| Mobile browser wake word | **NOT_FEASIBLE** — no background execution, tab suspension releases mic |
| Mobile browser ambient | **NOT_FEASIBLE** — same; explicitly not promised |

Any mobile ambient work requires a platform spike + privacy review + explicit
owner sign-off, and belongs to P4S-31D-6 scope (desktop-first), not to these
packets.

---

## Battery / privacy constraints

- **On-device STT preferred.** iOS `SFSpeechRecognizer`
  (`requiresOnDeviceRecognition` where the locale supports it); Android
  `SpeechRecognizer` (`EXTRA_PREFER_OFFLINE` where supported). On this path,
  audio never leaves the device.
- **Server STT fallback — authenticated channel only.** For surfaces/locales
  without on-device STT (including the whole mobile-browser surface today):
  the existing voice_server (Groq Whisper + faster-whisper fallback) over
  `wss://` through the nginx proxy under the operator's session. No
  unauthenticated audio endpoint, ever.
- **Cloud transcription remains DEFERRED to a privacy review** — unchanged
  from the contract. This plan does not decide it.
- **No audio persistence.** Buffers live inside the adapter; only
  `TranscriptEvent` text crosses the seam (`carries_audio = false`, always).
- **Battery.** No wake runtime on mobile in these packets. The audio pipeline
  exists only between capture start and stop and is fully torn down on stop.
- **Secrets.** STT/TTS provider credentials stay in the existing server-side
  secret runtime (1Password `op run`). No provider key ships in a mobile
  client or in any artifact of this compile.

---

## Adapter into Cockpit Chat

- **Same interface.** The ONE `PlatformVoiceAdapter` from the contract —
  `requestConsent`, `openSession`, `startCapture`, `stopCapture`,
  `closeSession`; events `onTranscript`, `onWake` (unused on mobile — no wake
  mode), `onError`, `onStateChange`. Reference implementation:
  `cockpit/src/renderer/api/platform-voice-adapter.ts` (desktop browser,
  P4S-31D-1).
- **Same output, only output.** `sendMessage(text, source='voice', routing,
  voice_turn_id)` → `POST /advisor/converse`. The adapter never calls
  `classify_intent`, `intent_loop_submit`, `governed_mutation`, any provider,
  or `/intent-loop/submit`.
- **Transport reuse (browser).** P4S-31D-5 reuses the existing PCM16 16 kHz
  WS protocol from `voice-ws.ts` verbatim (`mic_start`/`mic_stop` control
  frames, binary PCM16 up, transcript/TTS events down). The mobile-browser
  adapter is the desktop-browser adapter plus mobile lifecycle handling.
- **Transport (native app).** On-device STT preferred (no audio off-device);
  the server-STT fallback speaks the same PCM16 WS protocol over the
  authenticated `wss://` channel.
- **Identity.** The mobile Clerk session principal, resolved server-side at
  `/advisor/converse` — the same principal that stamps `decided_by`. The
  adapter stamps no identity and cannot spoof one.
- **Consent.** `VoiceConsentGrant` per-mode per-device:
  `(operator_principal, device_registry_id, activation_mode='push_to_talk')`.
  Mobile devices register in `infra/device_registry.json` as controller-role
  entries. The grant is read fail-closed before any capture; missing, revoked,
  or unreadable → typed `CONSENT_REQUIRED` refusal with the inline grant
  affordance. A `push_to_talk` grant never authorizes `wake_word` or
  `always_on`.
- **Device role.** Mobile surfaces are controller role only — never executor,
  never orchestrator. The orchestrator-role node never has a microphone.

---

## Proof requirements (when the packets are eventually authorized)

Both packets extend the P4S-31C server-truth chain by one hop; UI rendering
alone is not proof.

- **P4S-31D-4 (mobile app):** foreground capture → transcript enters chat
  verbatim (`source='voice'`, `voice_turn_id`) → deterministic classification
  → held gate → governed approve → `PROOF_RECORDED` with `decided_by` = the
  mobile Clerk principal. Consent fail-closed test: no grant → typed refusal,
  mic never opens.
- **P4S-31D-5 (mobile browser):** tap → transcript → same rail, PLUS the
  graceful-refusal proof: background/lock mid-capture → typed `CAPTURE_ENDED`,
  no audio replay, fresh gesture required to resume.

---

## Stop conditions (inherited + mobile-specific)

- Any voice implementation code shipped under this compile → stop.
- Any promise of mobile ambient/background listening → stop (contradicts the
  matrix).
- Any audio path that bypasses the authenticated channel or persists audio →
  stop.
- Any consent bypass, or a `push_to_talk` grant treated as authorizing another
  mode → stop.
- Any plaintext secret in an artifact → stop.
