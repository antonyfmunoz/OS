# AI Outbound Voice Message — Compile (P4S-AI-OUTBOUND-VOICE-MESSAGE-001)

Compiled 2026-07-07. **Compile mode. No activation authorized. No rendering, no
send, no clone execution authorized.** Canonical artifact:
`data/umh/voice/ai_outbound_voice_compile.json`.

This is the governance-and-consent design for the **highest-risk** voice
category. It DESIGNS an authorization model, a held approval gate, an audit
trail, an anti-impersonation disclosure policy, and a governed mutation. It
BUILDS none of them. Nothing here renders audio, sends a message, calls a
provider, or clones a voice.

## Category (binding)

`AIOutboundVoiceMessage` — the AI drafts/renders a voice message in the
authorizing operator's own explicitly-authorized voice, intended for delivery to
another person. Defined in `docs/VOICE_MESSAGE_CONTRACT.md` voice_taxonomy and
`data/umh/voice/voice_message_contract.json`
(`voice_taxonomy.categories.AIOutboundVoiceMessage`), where it is listed as
**NOT this packet, NOT built**.

## The five hard requirements (BINDING — may never be weakened)

Each is phrased as a hard requirement. No downstream packet may remove, soften,
or make any of them optional.

1. **HR1 — Approval before send.** The authorizing operator's explicit approval
   is REQUIRED before ANY external send. Rendering produces a HELD artifact at
   `awaiting_approval`. It is a held gate, **never** an auto-send. There is no
   `auto_send` field, mode, or path — and one must never be added.
2. **HR2 — Full audit trail.** Every render and every send appends an immutable
   `AiOutboundVoiceProofRecord`: authorizing principal, approving principal,
   grant, rendered text, provider/voice model, recipient identity, disclosure
   applied, and timestamps. The record MUST exist before send.
3. **HR3 — No covert impersonation.** Every outbound AI-rendered voice message
   MUST carry a recipient-facing disclosure that the audio was AI-rendered in
   the operator's voice. No disclosure surface → no send.
4. **HR4 — No third-party voice cloning.** ONLY the authorizing operator's OWN
   voice may be modeled, and ONLY under a `VoiceAuthorizationGrant` with
   `self_voice_attestation = true`. No path renders any other person's voice.
5. **HR5 — External send is a high-risk governed mutation.** The send is a
   governed mutation: `high` risk, `external` blast radius,
   `require_approval = true`, `degraded_mode_allowed = false`. It routes through
   the canonical governed spine. There is no ungoverned send path.

## Voice authorization model

The authorizing operator authorizes use of **their own** voice via a
`VoiceAuthorizationGrant` — revocable, per-purpose, never blanket, with
`self_voice_attestation = true`. This grant licenses the voice model's use; it is
**not** a send approval. Each individual outbound message still passes the HR1
held gate. Revocation sets `revoked_at` and immediately refuses all render and
send, fail-closed. The authorizing principal is resolved server-side from the
authenticated session — never a hardcoded literal (Instance Context Law).

Third-party cloning is **prohibited**: render is preconditioned on
`self_voice_attestation = true` on a live (non-revoked, non-expired,
purpose-matching) grant; absence or falsity fails closed with no render.

## Approval gate (held → approve → proof → send)

```
authorize (VoiceAuthorizationGrant)
  -> render_requested -> rendering
  -> rendered_held (AWAITING_APPROVAL)        <- render NEVER sends (HR1)
  -> operator explicitly approves that artifact
  -> proof recorded (HR2)
  -> send  (governed mutation ai_outbound_voice_send, HR5)
  -> sent
```

Reject or revoke from any pre-sent state discards the rendered artifact and
produces no outbound send. Approval is per-message; approving one artifact never
pre-approves the next. The gate must never auto-advance past `awaiting_approval`.

## Audit / proof trail

`AiOutboundVoiceProofRecord` is append-only and immutable after write. Recipient
identity and the applied disclosure are required on any approved record. Audio
bytes and provider secrets are never written to the record or logs — references
only. Rendered text is never logged at INFO (≤40-char DEBUG previews only).

## Anti-impersonation / disclosure policy

Recipient-facing disclosure is mandatory (HR3). The disclosure — an in-audio
statement and/or accompanying text on the delivery surface — is part of the
message payload. The exact disclosure applied is recorded in the proof trail
before send. If the delivery surface cannot carry a disclosure, the send is
refused fail-closed.

## Governed mutation — DESIGN ONLY (not registered)

Design of the send mutation. **It is NOT registered in
`substrate/organism/mutation_registry.py` by this packet.** Registering, wiring,
or executing it is out of scope and forbidden here.

| Field | Value |
|---|---|
| name | `ai_outbound_voice_send` |
| action_type | `NETWORK` |
| risk_level | `high` |
| blast_radius | `external` |
| require_approval | `true` |
| reversibility | `irreversible` |
| degraded_mode_allowed | `false` (fail closed when control plane down) |
| allowed_modes (design) | `ASSISTED` only — never `AUTONOMOUS` |

`degraded_mode_allowed = false` is deliberate: an external, irreversible send
must never execute when the governed control plane is unavailable. The held
approval gate — not rollback — is the real protection, because an external send
cannot be recalled.

## Secret / credential handling

Any TTS/voice-provider credentials flow through 1Password
(`.claude/rules/credential-injection.md`): resolved via
`op run --env-file=<tpl>` with `op://` URIs — never hardcoded, never plaintext
CLI args, never committed, never logged, never inlined into any record or into
this design. `validate_credential_source()` is the substrate check to call
before authenticated provider use (design reference; not invoked here).

## Threat model (each threat → its gate)

- Covert impersonation → HR3 mandatory disclosure recorded before send.
- Third-party cloning → HR4 self-voice attestation precondition.
- Auto-send / accidental blast → HR1 held gate, no auto_send, HR5 spine approval.
- Ungoverned / degraded send → HR5 `degraded_mode_allowed = false`, fails closed.
- Credential leak → 1Password injection; secrets never logged or inlined.
- Repudiation → HR2 immutable proof record before send.
- Scope creep → per-purpose, revocable, expirable grant.

## Rollback

Compile rollback is a clean `git revert` of the three artifacts — nothing is
wired, so removal has zero runtime effect. A future implementation's rollback
design: grant revocation (immediate fail-closed) and a feature flag whose
off-state means no render, no send. Already-sent audio cannot be recalled, which
is why HR1's held gate is the protection.

## Forbidden in this packet

Rendering audio; sending to any recipient; executing/training any voice model or
clone; registering `ai_outbound_voice_send`; calling any provider; writing any
projection/live DB; weakening any of HR1–HR5; any activation- or
implementation-authorizing language.
