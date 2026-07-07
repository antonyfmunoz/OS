# P4S-31C — Deployed Cockpit Chat Intent Loop: Browser Proof

Recorded 2026-07-06. Acceptance: the deployed Cockpit browser UI proves
`Cockpit Chat → IntentSpec/intent loop → awaiting approval → governed approval
→ proof_recorded → server-truth status visible in the same Cockpit thread`.

**Result: PASSED** — all ten stages green, exit 0, confirmed by independent
server-truth read. Evidence class A (real deployed UI, real Chrome on the
executor node, real Clerk principal, zero synthetic data).

## The proven run

| Field | Value |
|---|---|
| Intent (typed in Cockpit Chat) | `Fix this stale probe path run-1783392904` |
| Loop | `loop_c63aea43a17c` (id taken from our own `/advisor/converse` 200 response on the wire) |
| Gate | HELD at `awaiting_approval` — in-thread reply + panel row, proof absent pre-decision |
| Decision | Approve clicked on the loop's own panel row (row anchored by unique run tag + Approve control) |
| Proof | `proof_1eafcfdc72f3` |
| Envelope | `ac0dd375c8ce4776` |
| Decided by | `clerk:user_3EHDsQSiGJUVF5FdLVkGflrwFlu` — the browser session's authenticated Clerk principal |
| Governance | `completed`, `degraded: False` — full GovernedExecutionSpine, live daemon |
| Mutation | `intent_loop_approval_decision` (registered MutationSpec) |
| In-thread status | DEX turn: "Intent loop `loop_c63aea43a17c` approve by clerk:… — stage proof_recorded, proof `proof_1eafcfdc72f3` (governed_success=True)" |

## Stage chain (collector output, exit 0)

```
[OK] clerk_auth                    auth state ready
[OK] chat_input_found
[OK] chat_submit                   Fix this stale probe path run-1783392904
[OK] gate_held_in_thread           loop_c63aea43a17c
[OK] panel_opened_from_thread      suggested action clicked
[OK] panel_window_added_from_palette
[OK] governed_approve_clicked      run-1783392904 -> loop_c63aea43a17c
[OK] proof_recorded_server_truth   proof_id=proof_1eafcfdc72f3 envelope=ac0dd375c8ce4776
                                   decided_by=clerk:user_3EHDsQSiGJUVF5FdLVkGflrwFlu
[OK] proof_badge_on_own_row
[OK] status_visible_in_cockpit     loop id present in thread/panel
```

## Evidence artifacts

- Screenshots (executor-captured, shipped to orchestrator):
  `data/audits/proof/2026-07-06_p4s31c_browser/01_cockpit_loaded.png`,
  `01b_chat_rail_opened.png`, `02_intent_captured_held.png`,
  `03_intent_loop_panel.png`, `04_proof_recorded.png`
- Raw staged JSON + network log: `data/audits/proof/p4s31c_browser_evidence_raw.json`
- Network route evidence: `POST /api/umh/advisor/converse` 200 (live reply carried
  the loop id); `GET /api/umh/intent-loop` 200s (panel truth); post-approve
  server-truth fetch from the browser origin returned the loop at `proof_recorded`.
- Independent verification: orchestrator-side read of the deployed
  `/api/umh/intent-loop` confirmed identical proof fields.
- Secret scan: evidence JSON contains zero credential patterns; Clerk creds flowed
  vault → `op run` env on the executor only (Credential Injection Law).
- Deploy evidence: cockpit deployed via `cockpit/deploy.sh` gate (merge #217-era
  bundle); `/healthz` 200; verifier path fixed in #218.

## How it ran (Browser Verification Law honored)

Real Chrome on the executor node (`windows-desktop`, interactive Session 1),
dispatched through the governed mesh port (signed verdict + relay bearer);
collector `scripts/browser_intent_loop_proof.py`; credentials injected executor-side
via `op run --env-file=scripts/.env.beast.tpl` — never CLI args, never printed.

## Runtime context (what unblocked this)

- PR #225: os-operator CPU cap 0.50 → 1.00 (owner Option 1 decision) — took
  `GET /intent-loop` from 22.6s/504-storms to 0.3–0.4s on fresh memory.
- Residual defect (unchanged by this packet): memory RES growth still degrades the
  runtime to unhealthy within ~20–30 min under sustained cockpit load — the proof
  ran inside a fresh-restart window. Durable fix is the queued
  `P4S-31C-RUNTIME-READ-PATH-HARDENING-001` (lane E) which must ALSO cover the
  RES-growth dimension, per PR #212's diagnosis.

## False-positive audit trail (kept deliberately)

An earlier run reported `proof_confirmed: true` falsely: panel cards render
`raw_text` (never the loop id), so a `div:has-text(loop_id)` selector matched outer
containers and approved a DIFFERENT row (`loop_42aaf9907e05`, envelope
`706b68d2cca14016` — itself a valid governed UI approve, wrong target). Caught by
independent server-truth audit; fixed by unique-run-tag row anchoring and
server-truth-only completion. No fake completion stands.
