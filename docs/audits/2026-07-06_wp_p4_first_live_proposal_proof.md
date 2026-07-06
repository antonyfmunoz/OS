# WP-P4-FIRST-LIVE-PROPOSAL-PROOF-001 — First Live Organic Proposal (2026-07-06)

Session C (EOS live proposal producer). Mission: produce ONE real pending
proposal in the EntrepreneurOS `agent_actions` table via the ORGANIC path,
then drive approve → execute → proof through the governed loop.

**Outcome in one line:** the organic proposal was produced end-to-end with
Class-A evidence and is verified PENDING through the UMH read seam; the
governed approve step fail-closed on a real platform defect (both EOS seam
mutation names were never registered in the canonical MutationRegistry),
the fix + regression tests ship in this PR, and the deploy of the fix to the
live operator was denied by the permission classifier and deliberately NOT
worked around. The proposal remains PENDING awaiting merge + authorized
deploy; approve → execute → proof is NOT claimed.

---

## 1. What was proven (Class A — real app, real DB, real model, real auth)

### 1.1 Organic proposal creation

| Field | Value |
|---|---|
| proposal_id | `action_1783367421127_b0ztpntev` |
| agent | `agent_executive` (Executive Agent) |
| user | `user_1776306380825` (Clerk-linked operator account) |
| action_type | `create_task` (executor allowlist member) |
| parameters.title | "Follow up with Demo Lead" |
| status | `pending`, requires_approval=true, priority=medium |
| created_at | 2026-07-06T19:50:21.127Z |
| insert path | app's own `storage.createAction` (server/routes/agents.ts ACTION-tag parser) |

Path (fully organic, zero manual DB writes):

1. EntrepreneurOS app (Beast source @ `9c8725f`, repo `C:\dev\dev\EntrepreneurOS`)
   started on Beast under the projection secret runtime:
   one-shot Scheduled Task `UMH_EOS_DEV` → `C:\dev\dev\run-eos.cmd` →
   `op run --env-file=.env.op.tpl -- npm run dev` (port 5000, log
   `C:\dev\dev\eos-server.log`). `.env.op.tpl` references
   `op://EntrepreneurOS/Development/DATABASE_URL` — the SAME item the UMH
   operator's EOS read seam uses (reference names verified; no values read
   into any output).
2. Authenticated `POST /api/agents/agent_executive/chat` (HTTP 200) asking the
   agent to create a follow-up task.
3. The live model (`gemini-2.5-flash` via the app's unified AI service)
   emitted `[ACTION:CREATE_TASK|title:...|description:...|priority:medium]`;
   the route parsed it and inserted the `agent_actions` row with
   `status=pending` (`actionsCreated: 1` in the HTTP response).

### 1.2 UMH read-seam verification (Class A)

`docker exec os-operator` → `GET http://localhost:8091/api/umh/eos/action-proposals`
(HTTP 200):

- `proposal_count: 1`
- `proposals[0].proposal_id = action_1783367421127_b0ztpntev`
- `status: pending`, `approval_state: PENDING`, `execute_enabled: false`
- envelope: `connection_status: connected`, `source_build_safe: true`,
  `beast_head: 9c8725f`, `allowed_action_types: create_document,create_task`

### 1.3 DB ground truth (read-only SELECT via `op run` injection)

- `agent_actions`: exactly one row — the organic proposal, all
  approval/execution fields NULL (`approved_by/approved_at/executed_at/
  completed_at/execution_result` all NULL).
- `tasks`: total 5, **0 created in the last 2 hours** — execution never ran,
  as required (nothing executed without approval).

## 2. What fail-closed (the defect this run surfaced)

`POST /api/umh/eos/action-proposals/{id}/approve` (operator-role headers from
the container's own env; never printed) returned HTTP 200 with:

```
"governance_status": "rejected",
"decision_applied": false,
"error": "unregistered mutation: eos_action_proposal_decision"
```

Root cause: the WP #186 seams submit `eos_action_proposal_decision`
(`projections/eos/integration/action_decisions.py`) and
`eos_action_proposal_execute` (`projections/eos/integration/action_execution.py`)
through `governed_mutation`, but NEITHER name was ever registered in
`substrate/organism/mutation_registry.py`. Every test used a fake
`mutation_runner`, so the suite stayed green while every live decision
fail-closed. The governed spine did exactly what it is designed to do:
reject unregistered mutations, execute_fn never invoked, zero state change.

### Fix shipped in this PR

- `substrate/organism/mutation_registry.py`: `EOS_ACTION_PROPOSAL_DECISION`
  and `EOS_ACTION_PROPOSAL_EXECUTE` MutationSpecs (medium risk, EXTERNAL
  blast radius, `require_approval=False` — the human approval is the cockpit
  operator decision itself; modeled on `APPROVAL_DECIDE`), registered in
  `_register_builtins`.
- `tests/test_eos_action_decisions.py`: three live-run regression tests that
  pin the REAL `MutationRegistry` (not a fake) — lookup of both names + a
  call-site literal ↔ registry match test. This closes the exact gap that
  masked the defect.
- Verification: 21/21 decision tests, 91/91 across execution/read/seam/router
  suites, import + `py_compile` clean.

## 3. What was NOT done (honest boundary)

- **Approve → execute → completed lifecycle: NOT performed.** The registry fix
  exists only on this branch. Deploying the self-authored governance change to
  the live os-operator (`cp` into /opt/OS + restart) was **denied by the
  permission classifier** ("Production Deploy ... deploying a self-authored
  change to a running shared service the user did not authorize"). Per the
  mission's hard rule, this was documented, not laundered around. After this
  PR merges and an authorized deploy restarts os-operator, the pending
  proposal can be driven through approve → execute and the task row verified.
- No seed INSERTs, no manual DB writes of any kind. The only DB writes this
  session were the app's own organic inserts (chat messages + the action row).
- No Beast source/git mutation. Files placed on Beast: `C:\dev\dev\run-eos.cmd`
  and `C:\dev\dev\eos-server.log` (both OUTSIDE the repo; launcher + log only).

## 4. Auth path used (documented honestly)

Clerk Backend API server-side session (the mission's sanctioned shortcut):
with `CLERK_SECRET_KEY` injected via `op run` (VPS side, value never printed),
`GET /v1/users?email_address=<operator email>` → `POST /v1/sessions` (session
`sess_3G8yJYWb4058NBZVgoG5KyFdqjM`) → `POST /v1/sessions/{id}/tokens`
(300s JWT) → `Authorization: Bearer` on the chat request. The app's REAL
Clerk middleware chain (`clerkMiddleware` → `attachClerkUser` →
`req.isAuthenticated()`) validated the token and attached the real local user
row (`user_1776306380825`). This bypasses interactive login, not auth
verification — the UI-driven browser login path was not used for proposal
creation. Classification: Class A for "authenticated user produced the
proposal"; Class B for "operator drove it through the app UI".

## 5. Coordinator hazard acknowledgements (Lane E deep inventory, PR #196)

1. **`initSampleData()` destructive re-seed**: verified BEFORE any launch
   attempt via read-only SELECT that an executive-role agent row existed
   (`agent_executive`, role=`executive` — the exact value storage.ts:264
   tests). Re-verified immediately before the successful launch:
   `executive_role_agents: 1`. Post-start SELECT confirmed agents intact.
   Case found: app was NOT running; started it with the guard row present —
   the destructive branch could not trigger.
2. **Double-execution race in the app's own approve endpoint**: the app-side
   `POST /api/actions/:id/approve` was deliberately NEVER called. All
   decision traffic went exclusively through the UMH governed cockpit routes
   (`/api/umh/eos/action-proposals/...`), which carry the atomic claim.
3. **Auth fail-open when CLERK_SECRET_KEY unset**: not applicable-safe — the
   app was started WITH the full Clerk env via `op run`; `clerkMiddleware`
   was active and the action insert required `req.isAuthenticated()`
   (verified: unauthenticated chat attempts create NO action rows —
   the two earlier failed-model chats with valid auth created 0 actions,
   and the insert is behind the authenticated-user guard at agents.ts:291).

## 6. Runtime notes / additional findings

- **os-operator threadpool starvation**: mid-run, os-operator went
  `unhealthy` (all requests timing out, `{"error":"request timeout"}`,
  504s on heavy routes). Restarted (verified zero code changes present in
  /opt/OS before restart — pure health remediation); recovered cleanly.
  Worth a follow-on: the sync route threadpool can be exhausted by slow
  workstation/snapshot endpoints.
- **Provider reality on Beast app**: Anthropic API → 400 credit balance too
  low; `gemini-2.5-pro` → 429 free-tier quota 0. `gemini-2.5-flash` works.
  The two failed-model chat attempts (HTTP 200, `actionsCreated: 0`) left
  only chat-message rows, no action rows.
- Clerk API via urllib requires a non-default User-Agent (Cloudflare error
  1010 otherwise).

## 7. Browser verification (honest classification)

Executor-grade collection DID run: mesh daemon dispatch (governed default
dispatcher, signed verdict, relay bearer — secrets via `op run` on both ends)
→ Beast interactive Session 1 → `browser_gate_collector.py`, chromium,
1 pass × 3 viewports (desktop/tablet/mobile) against production
`https://universalmetaharness.tech`. Per WP-P4-COCKPIT-BROWSER-VERIFY-001 §3
this executor path was previously a governed blocker — this run is the first
executor-grade browser pass against production in this workstream.

- Production surface reachable and rendering at all 3 viewports; os-operator
  log layer during collection: 0 tracebacks, 0 auth failures, 0 timeouts.
- The collector's DOM gate expects the Meta IDE button and reports
  "Meta IDE button not found" — the unauthenticated production cockpit
  correctly shows the Clerk sign-in gate, so app-internal elements are not
  reachable. **The PENDING queue row was therefore NOT verified in pixels.**
- Authenticated executor-browser verification of the approvals panel remains
  the same open blocker #187 documented (Clerk-authenticated Session 1
  browser session). Queue-row truth is verified Class A at the API seam
  (§1.2), Class B at the UI layer (jsdom suite from #186/#187 + production
  reachability only).
- An earlier collection attempt without mesh secrets fell back to SSH
  (Session 0, no display) and was DISCARDED as invalid evidence per the
  Browser Verification Law; only the mesh Session 1 evidence is recorded.

## 8. Evidence

- JSON envelope: `data/audits/proof/2026-07-06_wp_p4_first_live_proposal_proof.json`
  (includes the full `browser_evidence` block from the Session 1 run).
- No secret values, no DSNs, no tokens appear in this document or the
  envelope (regex secret-scan run over the envelope before commit: clean).
  Identifiers shown (Clerk user id, session id, proposal id, row ids) are
  non-secret identifiers.
