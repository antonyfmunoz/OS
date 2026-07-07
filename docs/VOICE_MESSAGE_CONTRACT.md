# VoiceMessage Contract — P4S-31D1-B

Compiled 2026-07-07. Canonical artifact: `data/umh/voice/voice_message_contract.json`.
Owner product correction: **P4S-31D-1 is reclassified P4S-31D1-A — the low-level
voice pipe (capture → WS STT → consent gate → chat rail → held gate) is proved,
but the shipped UX is dictation-into-chat and is NOT the product.**

## Voice taxonomy — what this packet IS and IS NOT (2026-07-07 owner correction)

"VoiceMessage" must not ambiguously mean every voice feature. The canonical
categories:

| Category | Meaning | Status in P4S-31D1-B |
|---|---|---|
| **UserVoiceNote** | User records audio into Cockpit → audio bubble + transcript underneath → retry/edit/delete/send → only after send does the transcript enter Cockpit Chat / IntentSpec / gate / proof | **THIS PACKET.** The `VoiceMessageDraft` type and the whole recording→review→send rail below ARE the UserVoiceNote rail. (`VoiceMessageDraft` is the internal type name; the product concept is UserVoiceNote / voice input draft.) |
| **LiveVoiceSession** | Real-time conversation with DEX; voice default response in live mode; transcript+events still in the Cockpit Chat ledger; actions still governed | NOT this packet — future `P4S-LIVE-VOICE-SESSION-001` |
| **AmbientActivation** | Wake word / double-clap / hotkey opens a voice session; does not execute by itself | NOT this packet — held; `P4S-AMBIENT-ACTIVATION-001` |
| **AIOutboundVoiceMessage** | AI renders a voice message in Antony's authorized voice for sending to another person; requires Antony approval; proof/audit; no covert impersonation, no third-party cloning | **NOT this packet, NOT built.** `P4S-AI-OUTBOUND-VOICE-MESSAGE-001` (compile only). Nothing here renders or sends AI voice. |
| **ManualCockpitControl** | approve / reject / execute / retry / cancel / inspect / open-proof | Execution controls, NOT intent ingress |

**Intent ingress law.** User intent enters ONLY through (1) Cockpit Chat text and
(2) voice-first control (the UserVoiceNote rail here). Manual cockpit buttons
control execution *after* intent exists — they are not primary user intent.

**This packet implements the user-recorded input rail (UserVoiceNote) only.** It
does not implement, and its docs must not imply, outbound AI voice messages,
voice cloning, live voice sessions, or ambient activation.

## The product

Voice is a governed **voice-message rail**:

```
tap mic (consent-gated)
  -> record real audio           (bubble/card: recording indicator + duration)
  -> partial transcript          (provisional display ONLY — never committed)
  -> pause-aware finalization    (VadConfig; sentence-internal pauses ignored;
                                  finalize = move draft to REVIEW, never send)
  -> VoiceMessageDraft           (audio artifact ref + transcript + duration +
                                  confidence + device/session + consent grant id
                                  + transcript status + created_at)
  -> transcript under the bubble; operator: send / retry / edit / delete
  -> ONLY on explicit send: Cockpit Chat -> IntentSpec -> WorkPacket/gate/proof
```

The intent loop receives the **finalized** transcript plus a pointer to the
audio artifact. Proof records that voice did not bypass Chat.

## Binding rules (implementation MUST satisfy — see JSON for full shapes)

1. **Partial transcript is never committed.** It renders as provisional text in
   the bubble only. No partial ever becomes a chat message or the input value.
2. **Pause ≠ send.** Silences shorter than `intra_utterance_pause_ms` (default
   1500ms) are ignored. Continuous silence ≥ `min_silence_before_finalize_ms`
   (default 2500ms) FINALIZES the draft into review — it does not send.
   `auto_send` defaults false and no current mode permits it.
3. **Draft before chat.** No chat message exists until the operator sends.
   Delete leaves no chat trace. No-speech leaves a recoverable draft / retry —
   never a chat message.
4. **Audio is preserved.** STT failure keeps the artifact; retry re-runs STT on
   the stored audio. Audio is never discarded on failure.
5. **Operator send is the confidence gate.** Low-confidence transcripts are
   displayed, editable, and never auto-enter the intent loop.
6. **Storage law.** Artifact is tenant/user/session scoped behind the
   authenticated session; audio bytes never logged, never leave the storage +
   STT seams; transcript never logged at INFO (≤40-char DEBUG previews only).
7. **Rail unchanged.** Send goes through `sendMessage(text,'voice',…)` →
   `POST /advisor/converse` → deterministic classify → governed submit → held
   gate. No separate voice execution path.

## Reuse (build on, don't duplicate)

- Capture transport: `voice-ws.ts` PCM16 → `umh/voice_server.py` (WS protocol unchanged)
- Consent: `VoiceConsentGrant(push_to_talk)` + inline enable control (shipped)
- Chat entry: `chatStore.sendMessage(text,'voice',routing,voice_turn_id)`
- Artifact upload candidate: existing `/chat/upload` media seam (Lane F decides)
- Turn correlation: `voice_turn_id` from the existing assembler

## Lanes

A LifeOS recon (report precedes implementation lock) · B this contract ·
C recording UI · D VAD state machine · E STT quality/retry · F storage/privacy ·
G Class-A proof (plan in the JSON `lane_g_proof_plan`).

Hard constraints and stop conditions: see the JSON `hard_constraints` — voice
never bypasses Cockpit Chat; no ambient/always-on/mobile activation; no
provider execution; P4S-21/40/22 held; stop only the affected lane on
contradiction.
