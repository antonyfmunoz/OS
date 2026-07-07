# P4S-31D-1 Proof — Desktop Browser Push-to-Talk Voice Into Cockpit Chat

Date: 2026-07-07 (05:30–05:45 UTC)
Packet: `P4S-31D-1-DESKTOP-BROWSER-PTT-001` (hard-hold released by owner
2026-07-07). Contract: `docs/VOICE_INTENT_CONTRACT.md`.

## What shipped

| Deliverable (packet spec) | Artifact |
|---|---|
| PlatformVoiceAdapter (desktop browser) over the existing chat seam | `cockpit/src/renderer/api/platform-voice-adapter.ts` — contract interface (`getConsent/requestConsent/revokeConsent/startCapture/stopCapture/closeSession`) delegating capture to the shipping `voice-controller.ts`; consent gate in front of capture, fail-closed |
| VoiceConsentGrant stored state + consent gate | `substrate/workstation/voice_consent.py` (store at `data/umh/voice/consent_grants.json`; per-mode, per-device, per-principal; `active = granted AND NOT revoked`); routes `transports/api/cockpit_voice_consent_routes.py` (`GET /voice/consent`, `POST /voice/consent/grant`, `POST /voice/consent/revoke`, operator-auth'd, principal resolved server-side) |
| Governed writes | `voice_consent_grant` / `voice_consent_revoke` MutationSpecs registered in `substrate/organism/mutation_registry.py` (low / LOCAL_FILE / fully reversible / degraded-opt-in — revocation always executable) |
| voice_server managed lifecycle unit | `infra/systemd/umh-voice-server.service` (Restart=on-failure, Nice=10, CPUQuota=150%, MemoryMax=1G per CPU Gate Law). NOTE: at proof time voice_server was NOT running (pgrep empty) — the lifecycle gap was live, the seam silently dead. Activation post-merge: `cp infra/systemd/umh-voice-server.service /etc/systemd/system/ && systemctl daemon-reload && systemctl enable --now umh-voice-server` |
| Tests | `tests/test_p4s31d1_voice_ptt.py` — 22 tests, all four packet-required proofs |

Scope guards honored: only `push_to_talk` is grantable (`GRANTABLE_MODES`);
wake_word / always_on / clap grants are refused typed (`MODE_NOT_GRANTABLE`)
until P4S-31D-3/6. No mobile, no desktop app, no cloud-STT decision.

## Packet-required tests (all pass — 22/22)

1. **TranscriptEvent.text == chat message content (verbatim)** —
   `test_voice_payload_enters_rail_verbatim_and_gate_holds` (server-truth
   `raw_text` equality) + `test_voice_exit_is_the_chat_seam_verbatim` (the
   controller dispatches `turn.assembledText` unmodified into
   `addVoiceTranscript` → `sendMessage(text, 'voice', …)`).
2. **Voice path contains no `/intent-loop/submit`, no `governed_mutation`, no
   provider call, no `classify_intent` call** —
   `test_voice_path_has_no_bypass_tokens` (static scan of
   `platform-voice-adapter.ts`, `voice-controller.ts`, `voice-ws.ts`).
3. **Consent gate refuses capture fail-closed without an active grant** —
   `test_no_grant_means_refusal_fail_closed`, per-mode/per-device/per-principal
   isolation tests, `test_consent_read_is_fail_closed_on_error` (unreadable
   store = no consent), rejected-governed-runner-persists-nothing.
4. **Gate holds at AWAITING_APPROVAL for a voice-origin INTENT_CAPTURE** —
   `test_voice_payload_enters_rail_verbatim_and_gate_holds` (`proof is None`,
   stage `awaiting_approval`) + `test_classification_is_source_independent`.

## Server-truth proof run (real ids, live store)

Voice-origin transcript submitted through the REAL `/advisor/converse`
handler (source='voice', voice_turn_id `vt-p4s31d1-proof-20260707`) against
the LIVE intent-loop store:

```
transcript : "Fix this p4s31d1-voice-proof-20260707 rail verification packet"
loop_id    : loop_37b05359b215
intent_id  : intent_f56baf8f17c9
draft_id   : draft_ea95c03f3c74
stage      : awaiting_approval   (gate HELD, proof None — no auto-advance)
governed   : degraded-mode audit record led-e23b0c4ddfe8
             (control plane down at proof time; intent_loop_submit is
             degraded-opt-in — the write stayed governed)
```

Independent verification: `read_intent_loop_surface()` executed INSIDE the
live `os-operator` container (the exact runtime `GET /intent-loop` reads)
returned the loop with `raw_text` VERBATIM equal to the transcript and stage
`awaiting_approval`. The held loop is visible in the cockpit Intent Loop
panel; the operator may reject it (it is the proof artifact, not real work).

## Verification summary

- 22/22 packet tests; 116/116 adjacent suites (p4s31b, p4s31c hardening,
  p4s31d artifacts, intent loop, voice turn assembly, voice identity)
- `tsc --noEmit`: 0 errors across the cockpit renderer
- Import check: consent routes + core-routes registration chain import clean
- All 13 pre-push gates pass (type coherence, instance context, projection
  boundary, dependency direction, CPU gate, ungoverned mutations, credential
  injection, secrets, mesh firewall, pytest collection, ontology layers,
  projection registry reads, ontology homes)

Evidence class: B (real handler + live-store run with container-side
independent read; not yet browser-proven). Class-A browser proof — real
Chrome on the executor node, spoken utterance end-to-end — is the next
packet, **P4S-31D-2**, per the contract's implementation sequence.
