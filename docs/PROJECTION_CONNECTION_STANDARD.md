# Projection Connection Standard

Compiled 2026-07-06 as part of P4-SYNC (compile mode). Data:
`data/umh/projections/projection_connection_matrix.json`.

Defines the ONE way a projection app plugs into UMH. The standard is the 17 slots;
tenant values bind at runtime (Instance Context Law). EOS is the reference
implementation — the only projection with a live loop; the standard is generalized
from it and frozen as universal only when a second projection ships the loop
(same N≥2 rule as templates).

## The 17 connection slots

| # | Slot | Contract | Canonical mechanism (proven home) |
|---|---|---|---|
| 1 | `tenant_id` | Every connection is tenant-scoped; no global tenant literals in code | BIS / `UMH_ORG_ID` runtime lookup |
| 2 | `projection_id` | Registered identity in the projection seed | `substrate/sockets/projection_port.py` + `data/umh/projection_registry.json` |
| 3 | `source_node` | Where source-of-truth code lives (role, not hostname) | `infra/device_registry.json` role lookup |
| 4 | `runtime_node` | Where the app runs (fly app, container, node) | projection seed `app_name`/`public_url` |
| 5 | `secret_runtime` | vault → op:// manifest → `op run`; plaintext never canonical | `scripts/op_run.sh` + per-app `.env.op.tpl` (RT-SECRET-RUNTIME-BINDING) |
| 6 | `identity_auth` | App principal (Clerk per-app) + UMH operator principal — NEVER conflated; two-Clerk-apps law | app `server/auth.ts` + `_require_operator_role` |
| 7 | `database` | Per-projection DB bound via `<PROJ>_DATABASE_URL` op:// ref; UMH reads read-only by default | `EOS_DATABASE_URL` pattern (compose passthrough, empty=fail-closed) |
| 8 | `readiness` | Projection-owned accessor → thin route, env-disabled-safe, never 500 | `eos_readiness()` → `/eos/activation` (rules/projection-read-surfaces.md) |
| 9 | `action_proposal` | App-native signal becomes a pending, requires-approval row; insert-only; authenticated principal | EOS `agent_actions` via `[ACTION:]` grammar |
| 10 | `approval_decision` | pending→approved/rejected ONLY, atomic status-claim, registered MutationSpec, FK-safe app-principal stamping, UMH decider in envelope only | `update_action_decision` + governed_mutation (#197/#198 lessons are REQUIREMENTS) |
| 11 | `execution` | Server-truth `execute_enabled` gate; atomic approved→executing claim; typed allowlist; provider actions separately enabled | `execute_action_proposal` non_provider_allowlist |
| 12 | `proof_trace` | Decision + execution envelopes, result_ref, server-truth verification; no completion without proof | governance envelopes + read-only row verification (PR #201 shape) |
| 13 | `memory_context_sync` | Projection context flows into substrate memory (Trace/feedback/Cognee); one memory, projection surfaces over it | `substrate/execution/trace.py` + feedback (LifeOS journal = surface, not a second memory) |
| 14 | `native_ux` | The projection keeps its own product UX; UMH never absorbs it | standalone app clients |
| 15 | `cockpit_mirror` | Cockpit renders read-surface truth + approval commands; mirror, not reimplementation | cockpit approvals panel over `/eos/*` |
| 16 | `capability_registry` | Projection action types + capabilities declared in the substrate manifest | `capability_router.py` + (P4S-11 manifest) |
| 17 | `template_registry` | Repeatable projection patterns recorded as RealityTemplates with proof pointers | (P4S-12) `substrate/templates/` |

## Conformance requirements (non-negotiable, learned live)

1. **Registered mutations only** — every decision/execution surface registers its
   MutationSpec; suites must include a real-registry regression test (#197).
2. **FK-safe principal stamping** — app rows carry app principals; UMH identities
   live in governance envelopes only (#198).
3. **Atomic claims everywhere** — `WHERE status='pending'` doctrine on both UMH and
   app sides (W2/EntrepreneurOS#4).
4. **Boot safety** — an app boot may never destructively mutate shared state
   (W1/EntrepreneurOS#3).
5. **Fail-closed defaults** — missing env/secret/daemon = refusal with typed error,
   never degradation.
6. **No secret transit** — values move vault→process env only; manifests are
   committable references.

## Onboarding runbook for a new projection (executable)

1. Register in projection seed (slot 2); bind tenant (slot 1).
2. Bind secret runtime: vault + `.env.op.tpl` + op run launch (slot 5). Verify: child
   env booleans, zero plaintext.
3. Bind DB: `<PROJ>_DATABASE_URL` op:// ref + compose passthrough (slot 7). Verify:
   read-only schema check.
4. Ship readiness accessor + route (slot 8) per RT-PROJECTION-READ-SURFACE. Verify:
   shape test + live 200 + env-unset dict.
5. Ship proposal read surface (slot 9 read side); cockpit mirror panel (slot 15).
6. Ship decision + execution seams (slots 10–11) per RT-GOVERNED-PROPOSAL-LOOP with
   conformance requirements 1–5. Verify: one organic PENDING→APPROVED→EXECUTED with
   proof (slot 12) — this is the projection's activation certificate.
7. Register capabilities + templates (slots 16–17); wire memory sync (slot 13).
