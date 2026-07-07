# Mobile UserVoiceNote Rail Compile — P4S-MOBILE-VOICE-SURFACE-001

Compiled 2026-07-07. Data artifact:
`data/umh/voice/mobile_uservoicenote_compile.json`. Validation:
`tests/test_p4s_mobile_uservoicenote_compile_artifacts.py`.

**Compile mode — no activation authorized.** This document plans how the
**shipped desktop UserVoiceNote rail** (P4S-31D1-B) would ADAPT to mobile
Safari, mobile Chrome, native iOS, and native Android. It implements nothing,
wires nothing, and authorizes no rollout.

This artifact **deepens** — it does not restate — the already-merged
`data/umh/voice/mobile_voice_compile.json` /
`docs/MOBILE_VOICE_COMPILE.md`. That artifact covers the generic
capture→transcript→rail seam and the per-surface push-to-talk / ambient /
permission verdicts. **This one deepens exactly one thing:** the
UserVoiceNote **draft** rail — MediaRecorder capture → `VoiceMessageDraft` →
audio bubble + transcript-underneath → review (send/retry/edit/delete) →
explicit send → Cockpit Chat — as it maps onto each mobile surface. Where the
two overlap (verdicts, consent, ambient), this document repeats the merged
verdict verbatim and contradicts nothing in
`data/umh/voice/platform_voice_feasibility_matrix.json`.

---

## What the shipped desktop rail is (the thing we adapt)

The reference implementation, already shipping on desktop browser:

- **Store** — `cockpit/src/renderer/stores/voiceMessageStore.ts`:
  the `VoiceMessageDraft` type, the `RecordingSessionState` machine
  (`idle → requesting_consent → requesting_permission → recording →
  paused_speech_gap → finalizing → transcribing → review → sending → sent`),
  `VAD_CONFIG` (`auto_send: false`), and `sendDraft` / `retryDraft` /
  `deleteDraft`.
- **Controller** — `cockpit/src/renderer/api/voice-controller.ts`:
  the MediaRecorder lifecycle (`_pickRecorderMime`, `_startRecorder`,
  `_stopRecorder`), `_finalizeRecording`, the `_onAudioLevel` VAD,
  `retryDraftTranscription` (decode → resample → WS re-stream), and the
  `sendDraft` upload via the existing `/chat/upload` seam.
- **Contract** — `docs/VOICE_MESSAGE_CONTRACT.md`: partial-never-committed,
  pause ≠ send, draft-before-chat, audio-preserved, operator-send-is-the-
  confidence-gate, storage law, rail-unchanged.

The mobile adapter is **this store + controller plus mobile lifecycle and codec
handling**. No new draft model, no new state machine, no new send path is
invented for mobile.

---

## Central thesis — the draft model SUITS mobile

**Tap-to-talk-then-review is a strictly better fit for mobile than a live /
hands-free model would be.**

Live push-to-talk on mobile is CONSTRAINED (matrix: mobile browser drops the
mic on background/lock; the native app ends capture on backgrounding). The
UserVoiceNote rail is not live: the operator taps to record, the recording
**finalizes to a REVIEW draft** (never auto-sends — `auto_send` is `false` and
no mode permits `true`), and the operator reads the transcript and taps send.

Consequences that make this the right mobile fit:

- A dropped mic mid-capture is **not a lost turn** — it finalizes the
  captured-so-far audio into a recoverable draft (audio preserved, retry
  available), exactly the desktop failure path.
- Review-before-send **tolerates STT jitter over a mobile radio** — a bad
  transcript costs a retry, not a bad chat message.
- Review-before-send **tolerates a lock-screen interruption** — the interruption
  produces a saved draft, not an accidental send.
- Low-confidence transcripts are displayed, editable, and never auto-enter the
  intent loop.

**This thesis does not upgrade any verdict.** Mobile browser PTT stays
CONSTRAINED; native app PTT stays LIKELY; mobile ambient/background stays
NOT_FEASIBLE (iOS background) / CONSTRAINED (Android FGS). The draft model makes
the CONSTRAINED surface *pleasant to use inside its constraint* — it does not
remove the constraint.

---

## Owner observation, 2026-07-07 (recorded)

Per `data/audits/2026-07-07_p4s31d5_mobile_browser_evidence.md`: the owner
opened the deployed cockpit on a **mobile browser**, tapped the mic, and
received the typed `CONSENT_REQUIRED` refusal — the mic never opened, the UMH
consent layer refused **before** the browser permission prompt (correct
two-layer ordering).

- **The refusal was correct.** Capture without an active
  `VoiceConsentGrant(push_to_talk)` for that device must fail closed. This is
  the P4S-31D-1 security contract behaving correctly on an unproven surface,
  not a bug.
- **The gap was UX, not contract.** The refusal was a small-viewport dead-end
  with no inline grant path. Lane A closes it with an inline "Enable
  Push-to-Talk for this device" control that renders on any served surface.
  Granting consent does **not** make mobile browser PTT a proven surface.
- **Binding implication for this rail:** the `CONSENT_REQUIRED` outcome must
  render its inline grant affordance in the **same thumb-reachable column** the
  draft bubble and review controls occupy. The refusal, the enable control, the
  recording indicator, the draft bubble, the transcript, and the
  send/retry/edit/delete controls all live in **one vertical, thumb-reachable
  stack** — no desktop settings rail.
- **Open item, not a claim:** browser mic-permission behavior was not reached
  (consent refused first). Per-origin / HTTPS-only / iOS-Safari-ephemeral
  re-prompt semantics are recorded as open, to be characterized when the rail
  is actually exercised on the surface.

---

## The rail per surface

### native iOS — LIKELY (`mobile_app.push_to_talk`)

Capture via `AVAudioEngine` tap on `inputNode` (PCM16 16 kHz mono) under an
`AVAudioSession .playAndRecord`. The captured audio is retained as the draft's
audio artifact (the native analog of the desktop MediaRecorder blob), so the
audio-preserved and retry laws hold. On-device `SFSpeechRecognizer` produces the
transcript from the same buffer where the locale supports
`requiresOnDeviceRecognition`.

- **Draft-model fit:** tap-to-talk toggle → REVIEW draft. The desktop
  `RecordingSessionState` machine maps 1:1; only the capture/STT primitives
  change.
- **No codec problem:** on-device capture is raw PCM; the retained artifact is
  encoded (m4a/AAC is the natural iOS container) only for the `/chat/upload`
  artifact, and `content_type` is set from the actual encoder, never assumed.
- **Background/lock:** app backgrounded or device locked → `AVAudioSession`
  interruption → capture ends. **No** `audio` `UIBackgroundMode` is claimed
  (that would be an App Review rejection risk for a non-audio utility app and
  would contradict the matrix `ios_background` NOT_FEASIBLE verdict). The
  interruption is treated like a desktop manual-stop-mid-record: finalize
  captured-so-far audio into a REVIEW draft, never discard, never auto-send.
  Resume = a fresh foreground tap. The draft survives; the turn is not lost.

### native Android — LIKELY (`mobile_app.push_to_talk`)

Capture via `AudioRecord` (PCM16 16 kHz mono) retained as the draft artifact, or
`android.speech.SpeechRecognizer` for the transcript. Foreground activity only,
behind consent + a `RECORD_AUDIO` runtime grant requested on the **first tap**
(never at install/launch).

- **Draft-model fit / codec / review controls:** same tap-to-talk → REVIEW draft
  and same send gate as iOS. Retained artifact encoded to whatever the platform
  encoder gives (m4a/AAC or ogg/opus); `content_type` set from the encoder.
- **Background/lock:** Activity pause / screen lock → capture stops. Android 10+
  blocks background mic without a microphone-type foreground service, and this
  rail ships **no** foreground service — capture is strictly foreground. Stop-by-
  background finalizes captured-so-far audio into a recoverable REVIEW draft;
  it never auto-sends and never loses the turn.

### mobile Safari — CONSTRAINED (`mobile_browser.push_to_talk`)

Capture via `getUserMedia` → `MediaRecorder` for the audio artifact **plus**
PCM16 16 kHz over the **existing authenticated voice WS**
(`cockpit/src/renderer/api/voice-ws.ts`, `mic_start`/`mic_stop` frames, binary
PCM16 up, transcript events down) for STT. This is the shipped desktop
controller path; the mobile-Safari adapter is that controller **plus** mobile
lifecycle + codec handling.

- **Why usable despite CONSTRAINED:** the draft rail is why mobile Safari is
  usable inside the constraint. Tap-to-talk **toggle** (never press-and-hold —
  long-press fires iOS text-selection/callout; `getUserMedia` and
  `AudioContext.resume()` must run inside the direct user gesture). Recording
  finalizes to a REVIEW draft; nothing enters chat until send, so a dropped mic
  or a jittery transcript costs a retry, not a lost turn.
- **The codec break (the central mobile-browser problem for this rail):** the
  desktop `_pickRecorderMime()` tries
  `['audio/webm;codecs=opus','audio/webm','audio/ogg;codecs=opus','audio/wav']`
  in order. iOS WebKit `MediaRecorder` supports **none** of these — it produces
  `audio/mp4` (AAC). On iOS every candidate fails `isTypeSupported`,
  `_pickRecorderMime()` returns `''`, and the recorder is built with the WebKit
  default (`audio/mp4`). The adapter MUST:
  1. add `'audio/mp4'` to the candidate list so `isTypeSupported` succeeds
     explicitly on iOS;
  2. stop assuming `audio/webm` — `voiceMessageStore.ts::_normalizeAudioContentType()`
     defaults unknown types to `audio/webm` and `sendDraft` picks only `.wav`
     or `.webm`; an `audio/mp4` blob would be mislabeled. Derive `content_type`
     and extension from the **actual** `recorder.mimeType` / `blob.type`
     (`audio/mp4` → `.m4a`), never from a webm assumption, so the `/chat/upload`
     seam and `AudioArtifactRef.content_type` carry the true container and the
     audio bubble plays back correctly.

  The retry decode path (`AudioContext.decodeAudioData` in
  `retryDraftTranscription`) must also decode `audio/mp4` on iOS — no webm
  assumption there either.
- **Background/lock:** tab background or screen lock → WebKit ends the
  `MediaStreamTrack` immediately, freezes timers, and the WS may be dropped by
  proxy idle timeout. For this rail: treat track `'ended'` (and
  `visibilitychange`-to-hidden) as a manual-stop-equivalent that **finalizes**
  the in-flight recording into a REVIEW draft — attach whatever audio flushed,
  mark recoverable, run STT (or mark `NO_SPEECH`/`STT_FAILED` and keep the audio
  for retry). **Never** auto-send on background; **never** auto-reacquire the
  mic — a fresh gesture is required on return to foreground. This is the
  graceful-refusal requirement expressed for the draft rail: a background/lock
  event produces a **saved draft**, not a dropped turn and not an accidental
  send.
- **STT:** no on-device STT in the browser today (no usable-quality on-device
  WebGPU Whisper on mobile Safari). STT is server-side over the authenticated
  `wss` channel only — the same `voice_server` the desktop rail uses. This is
  the one surface with no on-device option.
- **All iOS browsers are WebKit** — the codec and background/lock constraints
  apply to Chrome/Firefox/Edge on iOS too, not just Safari-branded.

### mobile Chrome — CONSTRAINED (`mobile_browser.push_to_talk`)

Same capture path as mobile Safari.

- **Codec:** Android Chrome `MediaRecorder` **does** support
  `audio/webm;codecs=opus`, so `_pickRecorderMime()` returns the first desktop
  candidate and the existing path works unchanged. The adapter still derives
  `content_type` from the actual `recorder.mimeType` (never a hardcode), so the
  same code is correct on both Android-Chrome-webm and iOS-mp4 without branching
  on user-agent.
- **Draft-model fit:** same toggle → REVIEW draft for cross-surface parity. Mic
  permission is per-origin and persistable on Android Chrome, so re-prompts are
  rarer than iOS — but the draft model and send gate are identical.
- **Background/lock:** backgrounded tab throttled and suspended; screen lock
  stops capture. Android Chrome is more permissive than WebKit, but the adapter
  applies the **same** policy: track `'ended'` or `visibilitychange`-to-hidden
  finalizes to a REVIEW draft; no background capture attempted, no auto-send.
- **STT:** none reliably in the browser today; server STT over the authenticated
  `wss` channel only.

---

## Shipped-rail adaptation deltas (documented, not authorized)

Concrete deltas between the shipped desktop rail and a conforming mobile
adapter. Each is a documented **adaptation requirement**, not a code change
authorized by this compile.

| Delta | What changes |
|---|---|
| **Codec candidate list** | `_pickRecorderMime()` must include `'audio/mp4'` for iOS WebKit, else `MediaRecorder` falls to an implicit default and the known-mime path is bypassed. |
| **Content-type normalization** | `_normalizeAudioContentType()` defaults unknown → `audio/webm`, and `sendDraft` picks `.wav`/`.webm` only. Mobile maps `audio/mp4` → `.m4a` and derives `content_type` from the real `blob.type`. `AudioArtifactRef.content_type` must be the true container for iOS playback. |
| **Finalize on lifecycle event** | Desktop finalizes on manual tap-stop, VAD silence, or max-duration. Mobile **adds** lifecycle finalize: `MediaStreamTrack 'ended'` and `visibilitychange`-to-hidden both call the finalize path (≈ `_finalizeRecording('manual_stop')`). Additive — no new state. |
| **No auto-reacquire** | On foreground return, do not auto-reacquire the mic or auto-resume the WS. A fresh user gesture is required (iOS `getUserMedia` + `AudioContext.resume()` rule). "Sending is only ever explicit" extends to "capturing is only ever an explicit gesture". |
| **Lazy WS reconnect** | A backgrounded tab freezes timers → ping/pong stops → the nginx proxy idle-times the socket. Do not fight it: end capture cleanly on visibility loss, reconnect lazily on the next gesture, **never** buffer or replay audio across a reconnect. Retry re-streams the **preserved blob**, not a live session. |
| **Audio-unlock gesture** | The existing `unlockAudioForIOS()` mic gesture must double as the `getUserMedia` capture gesture and `AudioContext.resume()` for STT decode — one gesture chain. |
| **`crypto.subtle` availability** | `_sha256Hex()` needs a secure context. Mobile cockpit is HTTPS-only, so `crypto.subtle` is available; the empty-string fallback stays as defensive code but should not trigger. |
| **Review UI on small viewport** | The desktop review controls (send/retry/edit/delete under the bubble) reflow to a single thumb-reachable column, co-located with the Lane A inline consent-enable control, so `CONSENT_REQUIRED → enable → record → review → send` is one continuous thumb column. |

---

## Draft lifecycle on mobile interruptions

Every path preserves audio and produces a recoverable draft — **none** produces
a chat message and **none** produces an auto-send.

- **Background / lock mid-record** → track `'ended'` / `visibilitychange`-hidden
  (browser) or `AVAudioSession` interruption / Activity pause (native): finalize
  captured-so-far audio into a REVIEW draft; attach audio; run STT or mark
  `STT_FAILED`/`NO_SPEECH` keeping the audio. Never auto-send. Resume = fresh
  gesture.
- **No speech** → under-threshold/too-short capture: `markNoSpeech()` — recoverable
  draft with retry, never a chat message (identical to desktop).
- **STT failed over radio** → `markTranscriptFailed('STT_FAILED')`: draft kept,
  audio kept (no revoke, no discard); retry re-runs STT over the preserved blob.
- **WS dropped by proxy** → backgrounded-tab idle timeout: in-flight capture
  finalizes to a draft (audio preserved); a later retry lazily reconnects and
  re-streams the preserved blob. No live-session replay across the reconnect.
- **Upload failed on send** → `/chat/upload` fails over a flaky radio: draft
  marked failed, audio preserved for retry (desktop `send_upload_failed` path).
  No chat trace.
- **Delete** → the ONLY path that discards audio (revokes the object URL, removes
  the draft, no chat trace). Every failure path above preserves it.

---

## Audio upload over mobile radio

- **Seam:** the existing `/chat/upload` media seam (`sendDraft`) — no new upload
  endpoint. `content_type` carried truthfully (`audio/mp4` on iOS,
  `audio/webm` on Android Chrome, `audio/wav` fallback).
- **Timing:** upload happens **only on explicit send**, not during capture, so a
  flaky radio never corrupts an in-progress recording — it can only fail a send,
  which preserves the audio for retry. No chunked-during-capture upload, no
  background upload. Draft artifacts are short (max 120 s hard cap).
- **Retry:** STT retry re-streams the preserved PCM16 blob over the authenticated
  WS; upload retry re-POSTs the preserved blob. Both operate on stored audio,
  never a live session.
- **Persistence:** audio bytes cross only the storage + STT seams behind the
  authenticated session; transcript never logged at INFO (≤40-char DEBUG
  previews); no audio persisted on device/server by default beyond the
  tenant/user/session-scoped artifact (storage law, `docs/VOICE_MESSAGE_CONTRACT.md`).

---

## On-device vs server STT

- **native iOS** — `SFSpeechRecognizer` on-device preferred
  (`requiresOnDeviceRecognition` where the locale supports it); audio never
  leaves the device. `NSSpeechRecognitionUsageDescription` mandatory; Microphone
  and Speech Recognition are **separate** TCC prompts, both required for the
  on-device path; either denied → typed refusal + Settings deep link, no silent
  retry.
- **native Android** — `android.speech.SpeechRecognizer` on-device preferred
  (`EXTRA_PREFER_OFFLINE` where supported).
- **mobile browser** — **no** on-device STT today (Safari or Chrome). Server STT
  over the authenticated `wss` channel only — the existing `voice_server`
  (Groq Whisper + faster-whisper fallback). No unauthenticated audio endpoint,
  ever.
- **Fallback channel** — where on-device STT is unavailable (unsupported locale
  on native; the entire mobile-browser surface), the server-STT fallback speaks
  the same PCM16 WS protocol over the authenticated `wss` channel under the
  operator's session. Provider credentials stay server-side in the existing
  secret runtime (1Password `op run`); no provider key ever ships in a mobile
  client or this artifact.
- **Cloud transcription** — DEFERRED to a privacy review, unchanged from
  `docs/VOICE_MESSAGE_CONTRACT.md`. This plan does not decide it.

---

## Adapter into Cockpit Chat (rail unchanged)

The mobile UserVoiceNote adapter is the desktop `voice-controller.ts` +
`voiceMessageStore.ts` rail plus mobile lifecycle/codec handling. **No new
interface, no new store, no new send path.**

- **Output seam:** on explicit send only — `sendDraft` →
  `chatStore.addVoiceTranscript` → `sendMessage(text, source='voice', routing,
  voice_turn_id)` → `POST /advisor/converse` — the same endpoint typed text
  uses. The draft carries the audio artifact ref + duration in message meta; the
  transcript text is the chat content.
- **Never calls** `classify_intent`, `intent_loop_submit`,
  `governed_mutation`, any LLM/provider call, or `/intent-loop/submit`.
- **Identity:** the mobile Clerk session principal, resolved **server-side** at
  `/advisor/converse` — identical to the principal that stamps `decided_by` on
  the ProofRecord. The adapter stamps no identity and cannot spoof one.
- **Consent:** `VoiceConsentGrant` per-mode per-device
  (`operator_principal`, `device_registry_id`, `activation_mode='push_to_talk'`),
  read fail-closed from the governed `/voice/consent` surface before any capture.
  Missing/revoked/unreadable → typed `CONSENT_REQUIRED` refusal with the inline
  grant affordance. A `push_to_talk` grant never authorizes `wake_word` or
  `always_on`.
- **Device role:** mobile surfaces are **controller role only** — never
  executor, never orchestrator. The orchestrator-role node never has a
  microphone.
- **Send is the only ingress:** per the intent-ingress law, the transcript enters
  Cockpit Chat / IntentSpec / gate / proof **only** on the explicit operator
  send. Partials are provisional display only; pause finalizes to review, never
  sends; delete leaves no chat trace.

**Class-A proof for this rail on a mobile surface** = tap → record → REVIEW
draft (audio bubble + transcript) → explicit send → transcript enters the same
rail → held gate → approve → `PROOF_RECORDED` with `decided_by` = the mobile
Clerk principal; **plus** the graceful-refusal proof: a background/lock event
during capture produces a recoverable REVIEW draft (audio preserved) and never
an auto-send or a lost turn. UI rendering alone is not proof; server-truth
confirmation of the chain is required.

---

## No mobile ambient / background (restated, verbatim with the matrix)

This rail promises **no** mobile ambient or background listening. It is
foreground-only, tap-initiated, review-before-send.

| Verdict | Value | Why |
|---|---|---|
| `ios_background` | **NOT_FEASIBLE** | iOS forbids continuous background mic for a non-audio utility app; App Review policy blocks it. Capture ends on background and finalizes to a draft. |
| `android_background` | **CONSTRAINED** | Only via a microphone-type foreground service (persistent notification, Android 14 FGS type), user-visible and battery-costly. This rail ships no such service; deferred and owner-gated. |
| `mobile_browser_wake_word` | **NOT_FEASIBLE** | No background execution; tabs suspended, mic released; WebKit has no service-worker background audio and no wake-word API. |
| `mobile_browser_ambient` | **NOT_FEASIBLE** | Same as wake word. Explicitly not promised. |

Any mobile ambient work is deferred behind a platform spike + privacy review +
explicit owner sign-off. These verdicts are identical to
`data/umh/voice/platform_voice_feasibility_matrix.json` and are cross-checked by
the validation test.
