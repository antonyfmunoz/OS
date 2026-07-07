# Ambient Activation Runtime — Compile Artifact

Compiled 2026-07-07 as the compile-only artifact for the full **AmbientActivation**
voice-taxonomy category (`P4S-AMBIENT-ACTIVATION-001`). Data artifact:
`data/umh/voice/ambient_activation_compile.json`.

**Compile mode — no activation authorized by this document.** No detector, no
global-hotkey registration, no acoustic-gesture library, no runtime ships with
this artifact. It defines the target shape a later implementation packet builds
and is validated against. **Every activation mode is held.** `GRANTABLE_MODES`
in `substrate/workstation/voice_consent.py` stays `{push_to_talk}` — clap and
hotkey are declared **future-grantable**, not grantable now.

---

## What this extends (and does NOT restate)

A prior desktop-ambient-**wake** compile already merged:
`data/umh/voice/desktop_ambient_wake_compile.json` +
`docs/DESKTOP_AMBIENT_WAKE_COMPILE.md`.

This artifact **extends** that into the whole AmbientActivation category. The
**wake-word dimension** — the `WakeEvent` contract, the daemon state machine,
the `AmbientState` reuse, on-device wake detection, wake consent, the wake
resource budget, and the mobile wake verdicts — is **defined in the wake
artifact and is NOT restated here.** This document references it and adds the
two missing dimensions plus the one unifying contract:

1. **Double-clap acoustic gesture** (new).
2. **Hotkey / manual activation** (new).
3. **The unified activation contract**: wake | clap | hotkey | manual all
   OPEN a session; none executes by itself.

Reading this artifact without the wake artifact is intentionally incomplete for
the wake dimension. Style matches `docs/DESKTOP_AMBIENT_WAKE_COMPILE.md` and
`docs/VOICE_MESSAGE_CONTRACT.md`.

## Taxonomy binding (binding)

Per `docs/VOICE_MESSAGE_CONTRACT.md` (2026-07-07 owner correction),
**AmbientActivation is category 3** of the five voice categories, defined
verbatim as:

> Wake word / double-clap / hotkey opens a voice session; does not execute by
> itself.

This packet is that category, compile-only, held.

## The unified activation contract

**An activation OPENS a session; it NEVER executes by itself.** Every mode —
wake word, double-clap, hotkey, manual press — is a *trigger* that opens a
bounded, consented capture window. It produces no intent, no classification, no
dispatch, no governed mutation. It only brings a capture surface to
ready-to-capture. The human still speaks (or the surface still receives a
transcript), and that transcript travels the SAME proven Cockpit Chat rail:

```
on-device / surface-local activation (consented, any mode)
  -> ActivationEvent (metadata only, carries_audio=false)
  -> consent_ref validated ACTIVE (fail-closed)
  -> OPEN one capture surface:
       LiveVoiceSession   (future P4S-LIVE-VOICE-SESSION-001), or
       UserVoiceNote      (P4S-31D1-B shipped record->review->send rail)
  -> [human speaks / records]
  -> TranscriptEvent -> sendMessage(text,'voice',routing,voice_turn_id)
  -> POST /advisor/converse -> deterministic classify_intent -> intent loop
     -> held gate -> proof
```

Which surface an activation opens is a **per-surface configuration**, not a
property of the mode: a hotkey, a clap, or a wake word can each open either
surface. The activation contract is uniform; only the opened surface differs.

**An activation is NOT** an intent, NOT a command, NOT a dispatch, NOT an
execution decision. Nothing between the activation and the transcript is new
execution surface. The held gate and proof chain are downstream of the
**transcript**, never of the activation.

### ActivationEvent shape (reference, not redefinition)

The wake dimension's `ActivationEvent` is the canonical `WakeEvent` already
declared in `data/umh/voice/voice_intent_contract_types.json` — see the wake
artifact; **not redefined here.** Clap and hotkey emit the SAME event family
with the same invariants: metadata only, `carries_audio` const `false`,
`consent_ref` must resolve ACTIVE or the event is rejected fail-closed,
`source_device_id` is a registry id/role (never a hostname). Concrete
clap/hotkey field shapes belong to the implementation packet, bound to the
existing `WakeEvent` family rather than forking it.

## Activation modes at a glance

| Mode | Consent mode | Grantable now | Future-grantable | On-device | Dimension |
|---|---|---|---|---|---|
| Wake word | `wake_word` | **no** | yes | yes | **wake artifact** (referenced) |
| Double-clap | `clap_activation` | **no** | yes | yes | **new here** |
| Hotkey | `hotkey_activation` | **no** | yes | yes (no detection audio) | **new here** |
| Manual | `push_to_talk` | **yes** | yes | yes | shipped push-to-talk |

Only `push_to_talk` (manual) is grantable today. Manual is listed for taxonomy
completeness; it is not new work.

## Double-clap acoustic-gesture detection (new)

A double-clap OPENS a capture surface. It is **not** a command vocabulary — a
gesture never maps to an action, only to opening capture.

**On-device requirement.** All acoustic-gesture detection runs on-device
(Electron main process on `desktop_app`; surface-local elsewhere). No audio
frame streams off-device. Only `ActivationEvent` metadata crosses the device
boundary; the rolling audio buffer lives in main-process memory only, bounded to
a few hundred ms–seconds, never persisted, never transmitted — identical
privacy posture to the wake dimension.

**Detection approach — deterministic DSP, not a neural model.** A clap is a
short broadband percussive transient: fast attack, high crest factor
(peak-to-RMS), broadband energy, rapid decay. Detection is an on-device
amplitude-envelope + onset detector:

1. Compute a short-window energy/peak envelope.
2. Flag an onset when a transient exceeds an **adaptive** noise-floor-relative
   threshold with a high crest factor.
3. A **double**-clap is two qualifying onsets separated by an inter-clap
   interval inside a bounded window.

Per the **Deterministic-First Principle** (CLAUDE.md), the DSP rule is the
spine; any future ML refinement is enhancement only, with the DSP detector as
the always-works fallback.

| Parameter | Default | Meaning |
|---|---|---|
| `inter_clap_min_ms` | 80 | closer than this = one event / echo |
| `inter_clap_max_ms` | 600 | farther than this = unrelated impacts |
| `onset_crest_factor_min` | 6.0 | peak-to-RMS floor separating clap from speech/music |
| `onset_threshold_above_noise_floor_db` | 12.0 | adaptive to ambient level |
| `post_activation_cooldown_seconds` | 5.0 | reuses `COOLDOWN_SECONDS` — no new constant |

All values are compile-time planning defaults; the implementation packet MUST
re-measure and tune against real rooms before any threshold is finalized.

**False-positive handling.** Everyday sounds are clap-like (door slams, dropped
objects, keyboard bangs, applause). Mitigations:

- **Double-clap, not single** — a bounded-interval PAIR rejects most
  single-impact noises.
- **Crest-factor gate** — sustained loud sounds (music, speech, engines) have
  low crest factor and are rejected; only sharp transients qualify.
- **Adaptive noise-floor threshold** — scales with ambient level.
- **Inter-clap interval window** — rejects echoes (too close) and unrelated
  impacts (too far).
- **Refractory / cooldown** — reuses `COOLDOWN_SECONDS` to prevent burst
  retriggering (applause, repeated bangs).
- **Operator-visible activation log** — every emitted event and every rejected
  candidate is logged (mode, timestamp, accepted/rejected, reason). No
  invisible activations; the log is the tuning input.
- **Confirm-open, not confirm-execute** — the safety keystone. Because an
  activation opens-but-does-not-execute, even an imperfect detector cannot cause
  a wrong action. A false clap opens a mic that hears nothing and closes on
  timeout (reuses `COMMAND_TIMEOUT_SECONDS` = 120.0s). The cost of a false
  positive is a harmless empty window, never a wrong action.

**Resource budget (CPU Gate Law).** A DSP transient detector is cheaper than a
neural wake model — no model to load:

| Bound | Value |
|---|---|
| Sustained CPU (single core) | max **3%**, target **1.5%** |
| Detection burst | max **8%** for ≤ **1s** |
| Resident memory | max **30 MB** |
| Breach behavior | **self-disarm** → activation-log entry; never degrade the host |

## Hotkey model (new)

An OS-level global hotkey (or in-surface accelerator) is a **deterministic**
activation trigger: the keypress OPENS a capture surface; it never executes.

**Which surface owns it.** The `desktop_app` (Electron cockpit shell) **main
process** owns the OS-level global hotkey via Electron's `globalShortcut` API. A
global hotkey must survive window blur and work when the cockpit is backgrounded
— only the main process can register it. The renderer may own an **in-window
accelerator** only (active while the window is focused). This mirrors the wake
artifact's rule that the main process owns the mic/daemon and the renderer only
displays state.

- **`desktop_browser`:** a tab cannot register an OS-level global hotkey; the
  best it can do is an in-tab shortcut active only while focused —
  **CONSTRAINED** relative to `desktop_app`, consistent with the feasibility
  matrix. No global hotkey is promised for the browser surface.
- **Orchestrator role:** registers no hotkey and opens no capture — no mic, no
  interactive capture desktop (`has_microphone=false`).

**Trigger semantics.**

- **Deterministic** — the keypress IS the trigger; no audio detection, no
  probabilistic model, so there is no acoustic false-positive class. The only
  misfire is an accidental keypress, mitigated by a non-conflicting chord and by
  opens-not-executes (an accidental hotkey opens an empty window that times
  out).
- **On activation** — on a registered-hotkey press, under an ACTIVE
  `hotkey_activation` grant, the main process emits an `ActivationEvent`
  (metadata only, `carries_audio=false`, `consent_ref`) and OPENS the configured
  capture surface. It classifies nothing and executes nothing.
- **Conflict handling** — the implementation packet must detect OS-level
  registration conflicts (`globalShortcut.register` returns false / throws) and
  surface an operator-visible "hotkey unavailable" state rather than silently
  failing — fail-closed and visible, never a silent dead key.
- **No-audio privacy** — the hotkey trigger captures NO audio and needs NO
  microphone to fire; the mic only opens AFTER the hotkey opens the capture
  surface, exactly as a manual press does. The on-device requirement is
  trivially satisfied.

**Resource budget (CPU Gate Law).** Trivially satisfied — a registered global
hotkey is an OS event callback with near-zero steady-state CPU (≤ 0.1% single
core, ≤ 5 MB). Post-activation mic/capture cost belongs to the capture surface,
not the hotkey.

## Consent model (per-mode, strict) — `GRANTABLE_MODES` unchanged

Consent is PER-MODE and per-device, exactly as the wake artifact and
`substrate/workstation/voice_consent.py` enforce. A grant for one mode
authorizes ONLY that mode; no grant implies another.

| Activation mode | Grant | Grantable now |
|---|---|---|
| `push_to_talk` | `VoiceConsentGrant(push_to_talk)` | **yes** |
| `wake_word` | `VoiceConsentGrant(wake_word)` | no (future) — wake artifact |
| `clap_activation` | `VoiceConsentGrant(clap_activation)` | no (future) — **new here** |
| `hotkey_activation` | `VoiceConsentGrant(hotkey_activation)` | no (future) — **new here** |
| `always_on` | `VoiceConsentGrant(always_on)` | no (future) — wake artifact |

**The invariant this packet must not break.** `GRANTABLE_MODES` in
`substrate/workstation/voice_consent.py` MUST remain exactly `{push_to_talk}`
after this artifact merges. This artifact adds NO mode to `GRANTABLE_MODES`;
`clap_activation` and `hotkey_activation` are **future-grantable** (their own
implementation packets), not grantable now. Because this compile packet touches
no code, `VoiceConsentStore.grant()` still raises
`VoiceConsentRefused(code='MODE_NOT_GRANTABLE')` for every mode except
`push_to_talk` — the mechanical proof this compile packet activates nothing.

- **Two layers.** OS-level permission (mic for wake/clap; global-hotkey
  registration for hotkey) AND the UMH grant — either missing means refusal,
  fail-closed.
- **Revocation kills the mode immediately.** `revoked_at` set → gesture detector
  stopped, global hotkey unregistered, any open capture window aborted; partial
  transcripts discarded, not submitted — identical to the wake rule, applied to
  clap and hotkey.
- **No silent activation.** No detector runs, no hotkey stays registered, and no
  capture window opens without an active grant for the exact mode in effect.
  Events with a missing/revoked `consent_ref` are rejected fail-closed and
  logged.

## On-device requirement & privacy boundary

No audio leaves the device for ANY activation detection, across all modes. Wake
(wake artifact), clap (this artifact), and hotkey (no detection audio) are all
on-device. Only `ActivationEvent` metadata crosses the boundary — and, after a
consented capture window, the existing transcript-only path. Never audio bytes.
Cloud STT remains DEFERRED to the same separate owner-gated privacy review.
No detector, mic, hotkey, or capture ever runs on the orchestrator role. A
one-action cockpit **mute** suspends all activation detection and disarms the
hotkey without revoking consent; an operator-visible **activation log** records
every activation and rejection across all modes — no invisible activations.

## Resource budget summary (CPU Gate Law)

| Mode | Sustained CPU (1 core) | Resident memory |
|---|---|---|
| Wake word | wake artifact (≤ 5%) | wake artifact (≤ 200 MB) |
| Double-clap | ≤ 3% (target 1.5%) | ≤ 30 MB |
| Hotkey | ≤ 0.1% (event-driven) | ≤ 5 MB |
| Manual | no standing detector | — |

Any standing detector that breaches its budget **self-disarms** and logs the
reason; it never degrades the host. All numbers are compile-time planning
estimates; each implementation packet must measure and prove the bounds on
target hardware before its mode may be offered.

## Rollback plan

- **Flag off → runtime never starts.** Each mode has its own feature flag, all
  default OFF; no detector thread, no registered hotkey, no mic handle. Turning
  a flag off on a running app stops that mode immediately.
- **Revoke → immediate stop** of that mode (detector stopped / hotkey
  unregistered), independent of the flag.
- **Mute → instant suspension** of all detection + hotkey without touching
  consent.
- **Uninstall** removes all detectors, hotkey registrations, and local
  activation state; no persisted audio to purge; consent grants remain
  server-side as revocable state.
- **This artifact** is additive (docs + data + one test, zero code); revert the
  commit and nothing at runtime changes. `GRANTABLE_MODES` is untouched, so no
  mode became grantable.

## Mobile activation — honest verdicts (unchanged)

Desktop activation work implies NO mobile activation promise.

| Slice | Verdict |
|---|---|
| Mobile wake / ambient | see wake artifact + matrix — CONSTRAINED (fg) / **NOT_FEASIBLE** (bg) wake; **NOT_FEASIBLE** ambient |
| Mobile double-clap | **NOT_FEASIBLE** background; CONSTRAINED foreground-only, under consent |
| Mobile hotkey | **NOT_FEASIBLE** as OS-global hotkey; in-app buttons are ManualCockpitControl, not a global hotkey |

Any mobile activation work requires a platform spike + privacy review + owner
sign-off before it may even be scheduled.

## Forbidden in this packet

- Any runtime code (detector, hotkey registration, adapter, route, cockpit
  component, service, daemon).
- Any acoustic-gesture or wake-word library dependency in any manifest.
- Any global-hotkey or OS shortcut registration.
- Adding `clap_activation`, `hotkey_activation`, `wake_word`, or `always_on` to
  `GRANTABLE_MODES` — it MUST stay `{push_to_talk}`.
- Any activation, scheduling, or start of any implementation packet.
- Any provider execution, intent classification, or `governed_mutation`
  triggered by an activation.
- Any mobile activation promise beyond the verdicts above.
- Any cloud-STT decision.
- Any tenant or device-hostname literal as global truth.

## Validation

`tests/test_p4s_ambient_activation_compile_artifacts.py` mechanically validates
the JSON artifact: compile-only flag, required sections, the unified
"activation opens a session, does not execute by itself" language, the
double-clap detection approach + false-positive handling, the hotkey
surface-ownership model, per-mode consent strictness, on-device requirement,
numeric CPU-gate bounds, honest mobile verdicts, absence of
activation-authorizing language and tenant/device literals — and, by importing
`substrate.workstation.voice_consent`, asserts `GRANTABLE_MODES` is still
exactly `{push_to_talk}`.
