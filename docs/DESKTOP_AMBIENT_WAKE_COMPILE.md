# Desktop Ambient Wake-Word Runtime — Compile Artifact

Compiled 2026-07-06 as the compile-only artifact for the wake portion of
**P4S-31D-3** and the ambient portion of **P4S-31D-6**. Data artifact:
`data/umh/voice/desktop_ambient_wake_compile.json`.

**Compile mode — no activation authorized by this document.** No daemon, no
wake runtime, no wake-word library dependency ships with this artifact. It
defines the target shape a later implementation packet builds and is validated
against. Both packets remain hard-held; P4S-31D-6 is owner-gated and ships
LAST. Style matches `docs/VOICE_INTENT_CONTRACT.md`.

---

## Owner doctrine (binding)

The wake daemon exists ONLY to emit `WakeEvent`s that open a consented capture
window feeding the SAME Cockpit Chat intent rail:

```
on-device wake detection (Electron main process, consented)
  -> WakeEvent (metadata only, carries_audio=false)
  -> consent_ref validated ACTIVE (fail-closed)
  -> bounded capture window
  -> TranscriptEvent -> sendMessage(text, 'voice', routing, voice_turn_id)
  -> POST /advisor/converse -> classify_intent -> intent loop -> held gate -> proof
```

The daemon never classifies intent, never dispatches work, never carries audio
off-device. Everything downstream of the transcript is the P4S-31B/C proven
rail, unchanged.

## Scope

- **Target:** `desktop_app` (Electron cockpit shell) only — the feasibility
  matrix's ONLY clean ambient-wake host (`wake_word: LIKELY` on desktop_app;
  `CONSTRAINED` in-tab on desktop_browser).
- **Device roles:** `controller` / `executor` per `infra/device_registry.json`.
  The orchestrator-role node NEVER runs a microphone, wake runtime, or capture.
- **Device binding:** registry role/id only — never hostnames.

## WakeEvent contract (reference, not redefinition)

The daemon emits **exactly** the `WakeEvent` shape already declared in
`data/umh/voice/voice_intent_contract_types.json` — `keyword`, `confidence`,
`detected_at`, `source_device_id`, `consent_ref`, `wake_runtime`,
`carries_audio` (const `false`). This artifact binds to that shape; it does not
redefine it. Inherited invariants:

1. `carries_audio` is always `false` — a WakeEvent reports a keyword event,
   never audio.
2. `consent_ref` must resolve to an ACTIVE `VoiceConsentGrant` for this
   device + mode, or the event is rejected fail-closed.
3. Sub-threshold detections are discarded on-device before emission.
4. The wake keyword is instance-configured at runtime, never a substrate
   literal.

## Daemon lifecycle

**Owner process:** the Electron MAIN process hosts the daemon (real background
thread, no tab throttling). The renderer only displays state and affordances —
it never owns the mic. The daemon is NOT a system service; it dies with the
app.

**Starts only when ALL of:** feature flag ON (default OFF), an ACTIVE
`VoiceConsentGrant` for the mode in effect, OS mic permission granted, and the
device's `DeviceCapabilityProfile` has `has_microphone=true` with
`wake_word_runtime != 'none'`.

**Stops on ANY of:** consent revocation, flag OFF, operator mute, app quit, or
resource-budget breach (self-disarm).

**States:**

```
disabled -> consent_granted -> armed -> wake_detected -> capture_window -> rearm -> armed
(any state) -> disabled   on revoke / flag off / mute / quit / budget breach
```

| State | Meaning |
|---|---|
| `disabled` | daemon not listening; no mic handle, no model loaded |
| `consent_granted` | preconditions satisfied; runtime not yet armed |
| `armed` | on-device detector listening locally |
| `wake_detected` | detector fired at/above threshold; WakeEvent emitted |
| `capture_window` | consent validated; bounded capture open, feeding the existing transcript seam |
| `rearm` | cooldown after a window closes; then back to `armed` |

**Vocabulary reuse (no parallel state machine).** These states map onto the
EXISTING `AmbientState` machine in
`substrate/workstation/ambient_wake_runtime.py`:
`disabled↔DORMANT`, `armed↔PASSIVE_LISTENING`, `wake_detected↔WAKE_DETECTED`,
`capture_window↔COMMAND_ACTIVE`, `rearm↔COOLDOWN`. `consent_granted` is the
consent precondition layer `VoiceSession` already models
(`consent_pending → consent_granted`) — it gates entry into the AmbientState
machine, it does not duplicate it. Transitions are recorded as
`WakeTransition`-shaped entries.

## Consent model (per-mode, strict)

- **Consent is PER-MODE and per-device.** `VoiceConsentGrant(wake_word)`
  authorizes wake-word listening ONLY. `VoiceConsentGrant(always_on)` is a
  SEPARATE grant required for ambient continuous operation. Neither implies the
  other; a `push_to_talk` grant authorizes neither.
- **P4S-31D-3 scope** requires the `wake_word` grant. **P4S-31D-6 scope**
  requires BOTH `wake_word` AND `always_on` grants active simultaneously.
- **Two layers.** OS mic permission (macOS TCC / Windows privacy) AND the UMH
  grant — either missing means the daemon refuses to arm, fail-closed.
- **Revocation kills listening immediately.** `revoked_at` set → wake thread
  stopped, mic released, state → `disabled`, within 1 second (acceptance-test
  bound for the implementation packet). Revocation mid-capture aborts the
  window; partial transcripts are discarded, not submitted.
- **No silent listening.** There is no state in which the daemon listens
  without an active grant for the exact mode in effect.

## Privacy boundary

- ALL wake detection runs on-device in the Electron main process. No audio
  frame ever streams off-device for wake detection.
- Only `WakeEvent` **metadata** crosses the device boundary — and, after a
  consented capture window, the existing transcript-only path. Never audio
  bytes.
- The detector's rolling audio buffer lives in main-process memory, bounded to
  a few seconds, never persisted, never transmitted.
- Cloud STT remains DEFERRED to the separate owner-gated privacy review.
- The daemon stamps no identity; the Clerk principal is resolved server-side.

## False-positive handling

- **Confidence threshold:** default `0.6` (0.0–1.0), operator-tunable; below
  threshold is discarded on-device.
- **Cooldown:** `5.0s` after a capture window closes (reuses
  `COOLDOWN_SECONDS` from `ambient_wake_runtime.py`) — prevents retrigger
  loops.
- **Capture-window timeout:** `120.0s` (reuses `COMMAND_TIMEOUT_SECONDS`).
- **Operator-visible wake log:** every emitted WakeEvent AND every
  consent-rejected wake is appended to a wake log surfaced in the cockpit
  (keyword, confidence, timestamp, accepted/rejected). No invisible wakes.
- **Mute affordance:** one-action mute in the cockpit HUD/tray suspends
  listening instantly WITHOUT revoking consent; visibly indicated;
  hardware/OS mic mute respected as an outer layer.

## Resource budget (CPU Gate Law)

The daemon is bound by the CPU Gate Law: never saturate CPU on any host.

| Bound | Value |
|---|---|
| Sustained CPU (single core) | max **5%**, target **3%** |
| Detection burst | max **15%** for ≤ **2s** |
| Resident memory | max **200 MB** including models + runtime |
| Breach behavior | **self-disarm** → `disabled` + wake-log entry; never degrade the host |

Candidate runtimes (compile-time estimates — MUST be re-measured on target
hardware in the P4S-31D-3 spike; **no dependency is added by this artifact**):

| Runtime | Est. CPU (1 core) | Est. RSS | Notes |
|---|---|---|---|
| `openwakeword_onnx` | 1–3% | 50–150 MB | open-source ONNX models, on-device |
| `porcupine_native` | 0.5–1% | 2–10 MB | smallest footprint; Picovoice access key + commercial licensing review belongs to the implementation packet |

## Rollback plan

- **Flag off → daemon never starts.** Default OFF; no thread, no mic handle,
  no model load. Turning it off on a running app stops the daemon immediately.
- **Revoke → immediate stop**, independent of the flag.
- **Mute → instant suspension** without touching consent state.
- **Uninstall** removes daemon, models, and all local wake state; there is no
  persisted audio to purge because audio is never persisted; consent grants
  remain server-side as revocable stored state.
- **This artifact** is additive (docs + data + one test); revert the commit and
  nothing at runtime changes.

## Mobile ambient — honest verdicts (unchanged)

Desktop ambient work implies NO mobile ambient promise. Verbatim from the
feasibility matrix:

| Slice | Verdict |
|---|---|
| mobile ambient wake-word | CONSTRAINED (foreground) / **NOT_FEASIBLE** (background) |
| mobile ambient always-on | **NOT_FEASIBLE** |
| iOS background mic (non-audio app) | **NOT_FEASIBLE** — App Review policy blocks it |
| Android background wake | CONSTRAINED — foreground-service approximation, battery-costly |
| mobile browser | **NOT_FEASIBLE** — no background execution |

Any mobile ambient work requires a platform spike + privacy review + owner
sign-off before it may even be scheduled.

## Forbidden in this packet

- Any runtime code (daemon, adapter, route, cockpit component, service).
- Any wake-word library dependency added to any manifest.
- Any activation, scheduling, or start of P4S-31D-3 / P4S-31D-6.
- Any mobile ambient promise beyond the matrix verdicts above.
- Any cloud-STT decision.
- Any tenant or device-hostname literal as global truth.

## Validation

`tests/test_p4s31d_ambient_compile_artifacts.py` mechanically validates the
JSON artifact: compile-only flag, required sections, consent per-mode
strictness, numeric resource bounds, WakeEvent reference (not redefinition),
lifecycle states, honest mobile verdicts, and absence of activation-authorizing
language and tenant/device literals.
