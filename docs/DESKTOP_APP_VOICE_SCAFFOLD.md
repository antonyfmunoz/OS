# Desktop App (Electron) Voice Adapter — Scaffold (P4S-31D-3, flag-disabled)

Status: **SCAFFOLD ONLY — no activation path exists.** Compiled 2026-07-06 as
Lane D of the voice wave. The binding contract is
`docs/VOICE_INTENT_CONTRACT.md`; the feasibility source is the `desktop_app`
row of `data/umh/voice/platform_voice_feasibility_matrix.json`
(push_to_talk: LIKELY, wake_word: LIKELY — cleanest wake path, ambient:
CONSTRAINED by doctrine, ships last).

## What exists after this packet

| Artifact | State |
|---|---|
| `cockpit/src/main/desktop-voice-adapter.ts` | PlatformVoiceAdapter method surface (`requestConsent` / `openSession` / `startCapture` / `stopCapture` / `closeSession`); every method returns a typed `DESKTOP_VOICE_DISABLED` refusal |
| `DESKTOP_VOICE_ENABLED` | Hard build-time constant, `false`. NOT readable from env, config, IPC, or renderer input — enabling it requires a reviewed code change in the P4S-31D-3 implementation packet |
| Capture / wake / STT code | **None.** No media API, no wake runtime, no listener of any kind |
| IPC wiring | **None.** `cockpit/src/main/index.ts` does not import this module; nothing can activate it |
| Tests | `tests/test_p4s31d3_desktop_scaffold.py` (static contract checks) |

## Platform contract (binding, restated from VoiceIntentContract)

The desktop-app voice path, when implemented, has exactly ONE exit:

```
local capture (consented) -> transcript (text, final=true)
  -> chatStore.sendMessage(text, source='voice', routing, voice_turn_id)
  -> POST /advisor/converse          (the SAME endpoint text uses)
```

The voice path NEVER:

- calls the deterministic intent classifier directly (`command_router` is
  reached only server-side via `/advisor/converse`, identically for voice and
  text);
- posts to the intent-loop submit route or any voice-specific submit route;
- invokes a governed mutation from the adapter (consent writes are governed
  server-side by the transport layer, not by this module);
- calls any model provider (no LLM anywhere in capture → transcript → chat);
- ships audio across the chat seam (transcript-only transit) or persists audio;
- stamps identity (the Clerk operator principal is resolved server-side; the
  adapter sends only `device_registry_id` + `activation_mode`).

These are the §Non-bypass invariants; the scaffold's tests pin them statically
today, and the P4S-31D-3 proof pins them at runtime.

## Permission model — two mandatory layers, per mode

Both layers are required for capture. Either missing = typed fail-closed
refusal. This mirrors the shipped desktop-browser adapter
(`cockpit/src/renderer/api/platform-voice-adapter.ts`) with the browser
permission layer replaced by the OS layer.

### Layer 1 — OS microphone permission (Electron main process)

- **macOS**: the packaged app declares `NSMicrophoneUsageDescription`
  (Info.plist). Before any capture the main process checks
  `systemPreferences.getMediaAccessStatus('microphone')` and requests via
  `systemPreferences.askForMediaAccess('microphone')` (TCC prompt). Status
  `denied`/`restricted` → typed refusal, mic never opens; the operator is
  pointed at System Settings → Privacy & Security → Microphone.
- **Windows**: capture respects Settings → Privacy → Microphone. Chromium's
  `getUserMedia` in the renderer surfaces the OS state; a native main-process
  capture path checks the same privacy setting. Denied → typed refusal.
- **Linux**: no TCC equivalent; PulseAudio/PipeWire device availability is the
  gate. No device or no access → typed refusal.
- Capture host: push-to-talk may reuse Chromium `getUserMedia` in the renderer
  (same as desktop browser, PROVEN path via the `:8096` voice_server), with a
  global shortcut (`globalShortcut`) registered in main for press-to-talk. The
  on-device wake runtime (later) is main-process native and additionally
  gated by the same OS permission.

### Layer 2 — UMH VoiceConsentGrant (per device, per mode, revocable)

- Source of truth: `substrate/workstation/voice_consent.py` —
  `VoiceConsentGrant(operator_principal, device_registry_id, activation_mode)`,
  `active = granted AND NOT revoked`, exact-mode/exact-device/exact-principal
  lookup, `require_active_grant` raises typed `CONSENT_REQUIRED` refusal.
- Consent is **PER-MODE**: a `push_to_talk` grant never authorizes
  `wake_word` or `always_on`.
- **Sequencing**: `push_to_talk` first. `GRANTABLE_MODES` is push_to_talk-only
  today; the P4S-31D-3 implementation packet is what makes `wake_word`
  grantable (its own reviewed change to `GRANTABLE_MODES` + its own proof).
  `always_on` stays non-grantable until P4S-31D-6 (owner-gated, last).
- Writes are governed: grant/revoke flow through the registered
  `voice_consent_grant` / `voice_consent_revoke` MutationSpecs on the server —
  the adapter only calls the consent HTTP surface, exactly like the browser
  adapter (`GET /voice/consent`, `POST /voice/consent/grant|revoke`).
- Revocation is immediate: an active session re-checks the grant; revoke →
  capture stops and further capture refuses fail-closed.

### Wake-word (P4S-31D-3 implementation, later — NOT in this scaffold)

- Runs **on-device in the Electron main process** (porcupine_native /
  openwakeword_onnx / platform-native per the feasibility matrix) — the
  cleanest wake path because main has a real background thread, no
  tab-throttling.
- No audio ever leaves the device for wake detection; a WakeEvent carries a
  keyword + confidence, never audio (`carries_audio = false` always).
- Requires an active `VoiceConsentGrant(wake_word)` — absent it the wake
  runtime does not even start. Revoke → runtime stops.
- CPU Gate Law applies: the wake runtime runs under an explicit CPU budget and
  NEVER runs on the orchestrator-role node (per `infra/device_registry.json`;
  `has_microphone=false` for the orchestrator role, always — no mic on the
  VPS).
- Always-on/ambient is NOT part of P4S-31D-3. It is P4S-31D-6, owner-gated,
  desktop app only, and ships last if at all.

## Why the flag cannot be enabled from client input

`DESKTOP_VOICE_ENABLED` is a `const` in the main-process module, compiled into
the app bundle. There is no env read, no config read, no IPC handler, no
renderer message that can change it. The renderer cannot reach main-process
module constants through the `contextIsolation: true` preload boundary. The
only enable path is a code change that lands through review in the
P4S-31D-3 implementation packet — which is exactly the intended gate.

## Proof plan — what P4S-31D-3's Class-A proof will require

Per the contract's implementation sequence, P4S-31D-3's acceptance is the
P4S-31C server-truth chain extended by one hop (spoken word instead of typed),
on the desktop app shell:

1. **Push-to-talk chain, real run**: press global shortcut in the Electron
   cockpit → spoken utterance → verbatim transcript appears in chat with
   `source='voice'` + `voice_turn_id` → deterministic classification →
   `AWAITING_APPROVAL` held gate (`proof is None`) → operator approves in the
   same panel → `PROOF_RECORDED` with real `proof_id` / `envelope_id` /
   `decided_by` = Clerk principal. Server-truth confirmed by an independent
   read of `/api/umh/intent-loop` (the P4S-31C verification, one hop back).
2. **Consent fail-closed, both layers**: (a) no `VoiceConsentGrant(push_to_talk)`
   → typed `CONSENT_REQUIRED`, mic never opens; (b) OS mic permission denied
   (macOS TCC) → typed refusal; (c) grant revoked mid-session → capture stops
   immediately and further capture refuses.
3. **Wake under grant only**: wake runtime starts ONLY with an active
   `VoiceConsentGrant(wake_word)`; wake → capture → same rail; revoke kills the
   runtime; WakeEvent carries no audio. `GRANTABLE_MODES` grows to exactly
   {push_to_talk, wake_word} — always_on still refused `MODE_NOT_GRANTABLE`.
4. **Non-bypass, static + runtime**: the adapter and its capture path contain
   no intent-loop submit route, no governed-mutation call, no classifier call,
   no provider call; network trace of the run shows the only runtime-bound
   request is `POST /advisor/converse` with a text-only body (no audio field).
5. **CPU budget**: wake runtime CPU measured under budget on the executor node;
   nothing voice-related runs on the orchestrator node.
6. **Class-A evidence discipline**: the proof runs on an executor-role node
   with a real interactive session (Browser Verification Law analog for the
   desktop shell — real Electron app, visible, not headless), all ids from the
   real run, secret/audio scan on evidence clean. Panel rendering alone is not
   proof (P4S-31C false-positive precedent).

Until that packet is called by the owner, this scaffold stays flag-disabled
and inert.
