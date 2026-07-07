# EntrepreneurOS Deep Seam Inventory — Unsafe Writes, Auth/Provider Seams, Ranked Import Candidates

**Work packet:** WP-P4-EOS-DEEP-SEAM-INVENTORY-001 (increment 2 of the Beast source map)
**Date:** 2026-07-06
**Source truth:** EntrepreneurOS on the Beast — `C:\dev\dev\EntrepreneurOS`,
branch `feature/company-system`, head `9c8725f`, working tree clean
(re-verified live over SSH this packet: `git log -1` = `9c8725f`,
`git status --porcelain` = 0 lines). All file:line references below are to the
Beast working tree at that head unless the path starts with `projections/` or
`transports/` (those are `/opt/OS`).
**Method:** read-only SSH (`findstr /n`, `powershell Get-Content` slices,
`type`). Zero writes to the Beast. No app code copied into `/opt/OS`.

**Builds on (read first, zero duplication):**
- `docs/audits/2026-07-06_wp_p4_eos_beast_module_map.md` (#191) — module→primitive
  map, 12-seam table (S1–S12), first import candidate (S6 `/eos/tasks`), mirror
  drift finding, owner-approval ledger.
- `docs/audits/2026-07-06_wp_p4_eos_beast_route_schema_inventory.md` (#191) —
  94-handler route census, 76-method IStorage census, 35+2+36 table census,
  action grammar, live/dead client map.

This packet answers the three questions those docs deliberately left open:
**(1)** which app write paths are unsafe alongside UMH's executor seam,
**(2)** the exact auth principal and credential material behind every surface,
**(3)** what to import/build after `/eos/tasks`, in what order.

---

## 1. Corrections to increment 1 (found by reading files it only sampled)

1. **`server/middleware/auth.ts` is dead code.** A repo-wide
   `findstr /s /c:"middleware/auth"` over `*.ts`/`*.tsx` returns **zero
   imports**. The wired auth chain is `server/auth.ts::setupAuth` (routes.ts:3,21),
   which contains its **own** copy of `attachClerkUser` (auth.ts:41-99) —
   without the debug logger. The `auth-debug.log` `appendFileSync` at
   middleware/auth.ts:57-64 therefore does **not** run on every request as
   increment 1 stated; it runs never. The committed 3.8 MB `auth-debug.log` is
   residue from when it was wired. Hygiene item stands (delete both), severity
   drops. The duplicate `attachClerkUser`/`requireAuth` definitions
   (auth.ts:26-99 vs middleware/auth.ts:48-133) are themselves a
   drift-of-two-copies hazard.
2. **`server/posthog.ts` is a console stub, not a posthog-node client**
   (posthog.ts:1-5: `capture()` → `console.log`). No server-side PostHog
   credential exists; only the client-side `VITE_POSTHOG_API_KEY` is real.
3. **`server/openai.ts` is no longer a legacy OpenAI path** — it routes through
   the Anthropic gateway (`callAI`, openai.ts:5,33-39, tier `fast`). The
   "legacy AgentBrain" label from #181/#191 is stale; the file is a misnamed
   gateway wrapper. `server/ai/index.ts` (5-provider fan-out) remains the
   second, parallel AI entry.

None of these change the built seams (S1–S5).

## 2. The safety baseline — UMH's atomic claim contract

Everything in §3 is judged against the UMH-side executor seam
(`/opt/OS/projections/eos/integration/action_execution.py` +
`tables.py`), which defines what "safe alongside UMH" means:

- **Atomic claim:** `claim_action_for_execution()` (tables.py:474-518) is a
  single `UPDATE agent_actions SET status='executing' ... WHERE id=%s AND
  status='approved' AND action_type=ANY(allowlist) RETURNING ...`
  (tables.py:489-501). A row that is pending/rejected/completed/failed/already-
  executing **cannot be claimed**; double execution is structurally impossible
  *from the UMH side*.
- **Allowlist in the SQL:** `EXECUTABLE_ACTION_TYPES = {create_task,
  create_document}` (tables.py:451) is enforced inside the claim WHERE clause —
  provider-coupled types (send_email) can never even be claimed.
- **Guarded outcome recording:** `record_action_execution_outcome()`
  (tables.py:588-639) transitions only `WHERE status='executing'`
  (tables.py:610,621) — only the claiming execution can record its outcome.
  Failure applies the EOS-faithful retry policy (retry_count+1, back to
  `pending` = human re-approval queue, else terminal `failed`).
- **Governed envelope:** the whole execution submits through
  `governed_mutation` (action_execution.py:281-300); governance down →
  fail-closed, nothing claimed (action_execution.py:301-313).
- **Fail-closed source gate:** readiness requires `source_build_safe` +
  `VERIFIED` + `runtime_ready` (action_execution.py:136-165).

A write path is **unsafe** to the degree it (a) touches tables UMH reads or
writes (`agent_actions`, `tasks`, `documents`, `crm_*` — per
`tables.py::VALID_SOURCE_TABLES` and the executor insert targets), (b) skips
authentication, and (c) transitions state without the guard/claim semantics
above.

## 3. Unsafe direct DB writes — exhaustive inventory, ranked

Census method: `findstr /s` for `db.insert(`/`db.update(`/`db.delete(` across
`server\*.ts` (84 hits: 47 in `server/storage.ts`, 9 direct-Drizzle sites in
`server/routes/{portfolios,companies,workflows}.ts`, 18 in dead
`server/generated/storage/*`, plus route-level `app.delete` matches), joined
with the 76-method IStorage census from #191 and a full read of every route
module. Every runtime write path in the server is listed below; dead and
out-of-band writers are in §3.6.

Auth legend: **ANON** = no `isAuthenticated()`/`requireAuth` check — any HTTP
client that can reach the port writes (the app deploys to Fly per `fly.toml`,
so "reach the port" can mean the public internet). **USER** = inline
`req.isAuthenticated()` check, principal = lazy-synced local `users` row (§4).

### 3.1 RISK 0 — unauthenticated or unguarded writes to UMH-coupled tables

| # | Write path | Table(s) | Trigger surface | Why unsafe alongside the claim contract |
|---|---|---|---|---|
| W1 | **Boot-time destructive re-seed**: `DatabaseStorage` constructor (storage.ts:161-164) fires `initSampleData()` (storage.ts:254-330); if no agent with `role='executive'` exists it **deletes every agent's tasks and messages** (storage.ts:276-281), **deletes ALL agents** (storage.ts:285), then inserts a seed executive agent + 3 seed tasks (storage.ts:293-311+) | tasks, messages, agents | **server process start** — no HTTP, no auth, no approval | The single most dangerous write in the app. A rename/removal of the executive agent row + a restart wipes `tasks` (UMH poll source + `/eos/tasks` candidate) and floods the UMH poller with seed inserts. Completely outside any governance; UMH's fail-closed gates don't help because the damage is to shared state, not to UMH's own writes. |
| W2 | **Approve→execute without claim**: `POST /api/actions/:id/approve` (actions.ts:43-62) does `storage.updateAction(id, {status:'approved',...})` (actions.ts:51) then `executeAction({...action, status:'approved'})` (actions.ts:57). `executeAction` (action-executor.ts:5-57) then does `updateAction(id,{status:'executing'})` (action-executor.ts:11-14), runs the effect, records completed (:32-36) or retry/failed (:48-53). **`storage.updateAction` (storage.ts:1363-1371) is an unconditional by-id UPDATE — no `WHERE status=`, no returning-guard.** | agent_actions (+ tasks/documents/Gmail side effects, agent_metrics via :38-41) | HTTP (USER, ownership-checked :49) | Three concrete races: **(a) double-approve double-execute** — the handler never checks `action.status`; approving an already-`completed` row re-runs the effect (for `send_email`: a second real email). **(b) cross-system double execution** — between actions.ts:51 (row becomes `approved`) and action-executor.ts:11, the UMH executor can legally claim the row (`approved→executing`); the app executor then blindly stomps `executing` and runs the effect anyway → each side executes once, effect lands twice. UMH's atomic claim protects only UMH. **(c) lifecycle clobber** — the app's unguarded failure path (action-executor.ts:48-53) can flip a row UMH already completed back to `pending`, re-queueing a done action for human approval. |
| W3 | **Unauthenticated task CRUD** — all 7 write handlers in tasks.ts have **no auth check**: POST /api/tasks (tasks.ts:21→storage.createTask storage.ts:578-604), PATCH /api/tasks/:id (tasks.ts:40→updateTask storage.ts:606), DELETE /api/tasks/:id (tasks.ts:74→deleteTask storage.ts:531-541), POST :id/collaborators (tasks.ts:98→addAgentCollaborator storage.ts:645-664), POST :id/assign (tasks.ts:136→assignTaskToAgent storage.ts:676-677), POST :id/subtask (tasks.ts:184→createSubtask storage.ts:694-700), POST :id/messages (tasks.ts:245→addCollaborativeMessage storage.ts:775-785) | tasks, messages | HTTP **ANON** | `tasks` is in UMH's `VALID_SOURCE_TABLES`: the poller turns inserts into SignalEnvelopes and S6 will surface rows to the operator. An anonymous client can therefore inject signals into the organism, mutate/delete the very rows the UMH executor created (`insert_task_from_action`), and corrupt the governed-effect audit trail — no user, no approval, no trace. DELETE has no ownership concept at all (tasks has no userId column). |
| W4 | **Unauthenticated agent mutation / prompt injection**: PATCH /api/agents/:id (agents.ts:82-103) passes **raw `req.body`** to `storage.updateAgent` (storage.ts:464); POST /api/agents (agents.ts:105-116, zod-validated but ANON); POST /api/agents/:id/clear-messages (agents.ts:140→clearAgentMessages storage.ts:746-748) | agents, messages | HTTP **ANON** | `agents.instructions`/`brainContent` are concatenated into every chat system prompt (agents.ts:247-248) **which also carries the `[ACTION:...]` grammar** (agents.ts:232-236). An anonymous PATCH is a stored prompt-injection that can steer a legitimately authenticated user's agent into proposing attacker-chosen actions (e.g. `SEND_EMAIL` with attacker text) — the human approval gate becomes the only remaining defense, presented with attacker-crafted descriptions. Mass-assignment (no zod on PATCH) also allows overwriting `roleLevel`, `parentAgentId`, `isActive`. |
| W5 | **Unauthenticated chat writes**: POST /api/agents/:id/chat (agents.ts:151) writes user + assistant messages with no auth (storage.addAgentMessage at agents.ts:170,191,212,315; storage.ts:752-758) and burns LLM spend (callAI agents.ts:181, generateAIResponse agents.ts:251). The action-extraction step alone is auth-gated: `if (!req.isAuthenticated()) continue;` (agents.ts:291) before `storage.createAction` (agents.ts:293-304) | messages, agent_actions (auth-gated leg), agents (updateAgentActivity agents.ts:322) | HTTP **ANON** (message legs), USER (action leg) | The one place the app almost got it right: anonymous chats cannot mint `agent_actions` rows (silent `continue` — proposals are dropped without error, a UX trap but fail-closed). Everything else is open: anonymous LLM spend, message-history poisoning of the context window (dbMessages replayed at agents.ts:220,240), and activity-log writes. |
| W6 | **`POST /api/keys/save` mutates `process.env` from an unauthenticated HTTP body** (ai.ts:61-92: `process.env[keyName] = value` at :83, allowlist of 5 provider key names at :66-72, **no auth check**) | none (process state, not DB) | HTTP **ANON** | Not a DB write, ranked here because it is the single worst credential surface: an anonymous request can overwrite `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`/etc. in the running process — swap in an attacker key (exfiltrate prompts via attacker's account/base URL for services that honor it) or a garbage key (denial of service to every provider call). Directly violates the credential-injection law's spirit; bypasses 1Password entirely. |

### 3.2 RISK 1 — authenticated but ungoverned writes to UMH-coupled tables

| # | Write path | Table(s) | Trigger surface | Assessment |
|---|---|---|---|---|
| W7 | Action proposal insert from chat: `storage.createAction` (storage.ts:1336-1361) ← agents.ts:293 | agent_actions | HTTP USER (sub-step of W5) | **Safe by shape** alongside the claim contract: insert-only, `status:'pending'`, `requiresApproval:true` (agents.ts:301-303) — UMH only claims `approved` rows, so a new pending row can't collide. Unsafe by *content*: parameters come from LLM output steered by W4-injectable prompts; `actionType` is unvalidated free text from the regex (agents.ts:274) — non-allowlisted types are still inserted and will sit unexecutable (app executor throws, action-executor.ts:29; UMH refuses, tables.py:489). |
| W8 | App-side executor effects: `executeCreateTask` (action-executor.ts:81-94→storage.createTask) and `executeCreateDocument` (action-executor.ts:96-107→storage.createDocument storage.ts:1258) | tasks, documents | approve flow (W2) | The effect inserts themselves are the same shape UMH's `insert_task_from_action`/`insert_document_from_action` produce (deliberately mirrored, tables.py:521-585). The unsafety is entirely the W2 dispatch race, not the inserts. |
| W9 | CRM writes: POST/PATCH contacts (crm.ts:49-93→storage.ts:999-1034), deals (crm.ts:133-177→storage.ts:1047-1087), activities (crm.ts:217-261→storage.ts:1100-1134) | crm_contacts, crm_deals, crm_activities | HTTP USER, ownership-checked | All three tables are UMH poll sources. Auth + user-scoping are correct; what's missing is governance on **agent attribution**: the client body can set `assignedAgentId` (deals) / `createdByAgentId` (activities) freely — an "agent did this" claim with no approval chain behind it. This is seam S9 (owner-gated app change); until then UMH must treat agent-attribution columns as unverified. |
| W10 | Documents/folders CRUD (documents.ts:45-114 folders, :155-224 documents → storage.ts:1160-1306; note `deleteFolder` also bulk-nulls `documents.folderId`, storage.ts:1202-1207) | folders, documents | HTTP USER, ownership-checked | `documents` is a UMH executor write target. App-side CRUD is authenticated and owner-scoped — acceptable app-native behavior; a UMH-created document is user-property once created. Only hazard: app DELETE of a document that a UMH `execution_result.document_id` references orphans the proof pointer (audit trail integrity, not correctness). |
| W11 | Notification read-mark without ownership: POST /api/notifications/:id/read (notifications.ts:70-77) → `storage.markNotificationAsRead(id)` (storage.ts:918-925) — updates **any** notification by id; contrast DELETE (notifications.ts:98-152) which does check ownership | notifications | HTTP USER | Cross-user write (IDOR): any authenticated user can mark any other user's notification read. Not UMH-coupled today; listed because notifications is a projection-read-surface candidate later. |

### 3.3 RISK 2 — authenticated writes to app-only tables (IStorage bypassed)

Direct Drizzle in route modules — the company-system tier never got IStorage
methods (#191 §2 note), so these bypass the app's own single-gateway
convention:

- portfolios: insert portfolios.ts:44, update :130, delete :175, plus
  company attach (update companies) :289 and company create :301 — all USER +
  owner-scoped (`ownerId`/`ownerUserId` in every WHERE).
- companies: insert companies.ts:158, update :224 — USER + owner-scoped;
  BIS-shaped fields (`stage`,`offer`,`targetCustomer`,`goals`) accepted as free
  text (matters for C6, §5).
- **workflows: POST /api/workflows (workflows.ts:16-33) is ANON** — Drizzle
  insert at :21, zod-validated but no auth and no ownership column at all;
  GET (workflows.ts:6) dumps every row to anyone. App-only table, so ranked
  RISK 2 despite ANON.
- **integrations: POST /api/integrations/connect (integrations.ts:11-36) is
  ANON** — `storage.connectIntegration(type)` (storage.ts:807-859) inserts a
  placeholder "connected" row with no user column; the follow-on notification
  insert (integrations.ts:21-30) is skipped for anon since `req.user` is
  undefined. Cosmetic table, anonymous state pollution.

### 3.4 RISK 2 — credential-material writes

- `storage.upsertOauthToken` (storage.ts:1382-1414) ← OAuth callback
  integrations.ts:61-68 and token refresh gmail.ts:62-69: **plaintext** Google
  access/refresh tokens into `oauth_tokens` (schema §4.4 of #191). USER-gated,
  correctly scoped — the unsafety is at-rest plaintext, which is exactly why
  `send_email` stays out of `EXECUTABLE_ACTION_TYPES` (S8 blocker).
- `storage.deleteOauthToken` (storage.ts:1416-1422) ← integrations.ts:93. Fine.

### 3.5 RISK 3 — housekeeping writes (authenticated, low blast radius)

- Lazy user create: `storage.createUser` (storage.ts:196-223) ←
  auth.ts:81-88 on first authenticated request. Note `id = \`user_${Date.now()}\``
  (storage.ts:198) — millisecond-collision risk on concurrent first-logins;
  also `integration_${Date.now()}` (storage.ts:845,863). UMH reads `users.id`
  for scoping (`user_ids` in the claim WHERE, tables.py:492), so duplicate-id
  pathology would confuse scoping — probability low, noted.
- `storage.updateUser` metadata merges ← notifications.ts:39-45,136-144. USER.
- `agent_metrics` counters: `incrementMetric` (storage.ts:1459-1477) ←
  action-executor.ts:38-41; read-modify-write without row lock (racy counters,
  cosmetic). Relevant to C5 (§5): app-side metrics count app-side executions
  only — UMH executions land in `umh_outcomes`, not here.
- `ai_messages`: addAiMessage (storage.ts:965) ← ai.ts:307,323,376,383;
  clearAiMessages (storage.ts:982) ← ai.ts:342 — all USER.
- Multi-agent collab messages: ai.ts:218-246 (3 inserts) + activity updates
  :249-260 — **ANON** (no auth check in /api/ai/multi-agent, ai.ts:119) but
  messages-table only; grouped with W5's exposure.
- `updateAgentActivity` (storage.ts:501) — 12 call sites across
  tasks.ts:28,59,113,120,161,168,197,266, agents.ts:322, ai.ts:249,256 —
  inherits each caller's (mostly ANON) auth posture; overwrites
  `agents.latestActivity` only.

### 3.6 Dead and out-of-band writers (census completeness)

- `server/generated/storage/*` — 18 Drizzle write sites (inserts/updates/
  deletes across capabilities, companies, conversations, departments, kpis,
  login, logout, me, onboarding, portfolios, preferences, read, readAll,
  register, roles, steps, tasks, workflows) — **unreachable**
  (`registerGeneratedRoutes()` is an empty stub, #191 §1.16). Deletion
  candidate; never a seam.
- `scripts/` — 38 ad-hoc setup/migration/pipeline scripts that write the DB
  directly when run by hand on the Beast; plus `npm run db:push`
  (drizzle-kit, package.json). Out-of-band, owner-operated; UMH must never
  invoke them (#191 §7).
- `session` table — connect-pg-simple leftover; no live writer found (Clerk
  owns sessions).

### 3.7 Summary counts (independently verifiable)

- 94 live handlers (#191 census, re-confirmed by module reads this packet).
- **32 handlers have no auth gate** (beyond the 3 by-design: 2 health +
  logout): agents 10/11, tasks 11/11, ai 5/10 (models, provider-status,
  keys/save, generate, multi-agent), analytics 1/2 (/api/stats), workflows 2/2,
  conversations 1/1, integrations 2/6. The other 59 check
  `req.isAuthenticated()` inline (or `requireAuth` for /api/user).
- **15 of those 32 are write endpoints**: tasks 7, agents 4 (PATCH, POST,
  clear-messages, chat message-legs), ai 2 (keys/save = process-env,
  multi-agent = messages), workflows 1, integrations 1.
- 47 live IStorage write call-sites in storage.ts + 9 direct-Drizzle route
  sites + 1 boot path (initSampleData) = every runtime DB write in the server;
  each appears in §3.1–3.5 exactly once.

## 4. Auth / provider seams

### 4.1 The wired Clerk boundary (one principal, one gap-mode)

Chain (auth.ts:118-126, registered first in routes.ts:21): `clerkMiddleware()`
**only if `CLERK_SECRET_KEY` is set** (auth.ts:121-123) → `extractClerkOrg`
(auth.ts:104-108: JWT `orgId` → `req.clerkOrg`) → `attachClerkUser`
(auth.ts:41-99: Clerk userId → local `users` row via
`storage.getUserByClerkId`, lazy-create via Clerk Admin API
`clerkClient.users.getUser` auth.ts:66, random-bytes password :84; installs the
`req.isAuthenticated()` polyfill).

Facts that define the boundary:

1. **Single principal.** Every authenticated route acts as the local `users`
   row of the caller. There is no service principal, no role check anywhere
   (`users.role` defaults `"user"`, storage.ts:214, never consulted), no
   admin tier. The "(admin)" comment on `/api/ai/stats` (ai.ts:425-431) is
   aspirational — it checks plain auth.
2. **Org is extracted, never enforced.** `req.clerkOrg` has **zero consumers**
   in any query; `companies.orgId` (schema line 508 region, nullable) is never
   filtered on. Multi-tenancy is user-id scoping only, and only on the routes
   that do it (§3).
3. **Fail-open configuration mode.** With `CLERK_SECRET_KEY` unset,
   `clerkMiddleware` is skipped and every `isAuthenticated()` returns false —
   the 59 gated routes all 401, but the **32 ungated surfaces (§3.7) keep
   serving and writing**. The app degrades to an anonymous-writable state
   rather than refusing to boot.
4. **Enumerated ownership gaps** inside the authenticated set:
   notifications :id/read (W11); companies departments/roles GETs
   (companies.ts:54-87) query by `companyId` without verifying company
   ownership (cross-tenant read); conversations GET (conversations.ts:5) and
   agent messages GET (agents.ts:119) are ANON reads of chat history —
   `messages` can contain business content from W5/W7 flows.

### 4.2 The two-Clerk-apps hazard (S12, sharpened)

Two **separate Clerk applications** now sit on the two sides of the shared DB:

| Side | Clerk app | Credential home | Principal model |
|---|---|---|---|
| EOS app (Beast/Fly) | EntrepreneurOS Clerk instance — `CLERK_SECRET_KEY`, `CLERK_PUBLISHABLE_KEY`, `VITE_CLERK_PUBLISHABLE_KEY` | 1Password `EntrepreneurOS/Development` (.env.op.tpl, verified this packet) | any signed-up user → lazy local `users` row |
| UMH cockpit | UMH Clerk instance, **locked to AFM's Clerk user id** (security lockdown, 4-layer) | 1Password `UMH-Production` | single operator |

Consequences to hold as law until S12 is decided: a Clerk identity in one app
means nothing in the other (same email ≠ same principal); the UMH integration
scopes DB access by **local** `users.id` values (`user_ids` in
`load_eos_config`, enforced in claim SQL tables.py:491-493), which are
app-Clerk-derived — so the operator's authority over EOS rows is *configured*,
not *proven* by identity. Any future crossover (cockpit deep-linking into the
app, app webhooks into UMH) must bridge at the identity layer, not by sharing
either secret. The `/eos/*` surfaces stay operator-only.

### 4.3 Provider / external-call census (every site, with credential material)

| # | Provider | Call sites (file:line) | Credential material | Where it lives today |
|---|---|---|---|---|
| P1 | **Clerk** (session parse + Admin API) | clerkMiddleware auth.ts:122; `clerkClient.users.getUser` auth.ts:66; client factory clerkAdmin.ts:5-7; frontend `lib/clerk.tsx` | `CLERK_SECRET_KEY`, `CLERK_PUBLISHABLE_KEY`, `VITE_CLERK_PUBLISHABLE_KEY` | **Vaulted** — 1P `EntrepreneurOS/Development` via `.env.op.tpl` |
| P2 | **Google OAuth / Gmail API** | OAuth2 client gmail.ts:10-20; authUrl :22-29; code exchange :31-46; token refresh :48-75 (writes back to DB :62); `gmail.users.messages.send` :102-105; kicked off by integrations.ts:39-75; consumed by action-executor.ts:65-76 | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` + per-user access/refresh tokens | **NOT in `.env.op.tpl`** — client id/secret are unvaulted (plain env on the host or absent); user tokens **plaintext in `oauth_tokens`** (storage.ts:1382-1414). Double S8 blocker: vault the client secret AND migrate token storage before UMH ever executes `send_email`. |
| P3 | **Anthropic (primary gateway)** | `new Anthropic({apiKey, baseURL})` ai/gateway.ts:63-71; models haiku-4-5 / sonnet-4-6 / opus-4-6 :33-37; callers: openai.ts:33 (all agent-brain traffic), agents.ts:181 (direct-claude), ai.ts:366 (/api/llm/chat) | `AI_INTEGRATIONS_ANTHROPIC_API_KEY` + `AI_INTEGRATIONS_ANTHROPIC_BASE_URL` (custom base URL — an AI-integrations proxy, not api.anthropic.com) | **NOT in `.env.op.tpl`.** The tpl vaults `ANTHROPIC_API_KEY`, but the gateway reads the `AI_INTEGRATIONS_*` pair — the vaulted key is dead config for the primary path. Unvaulted primary-provider credential. |
| P4 | **Anthropic (service layer)** | ai/anthropic-service.ts:44 availability = same `AI_INTEGRATIONS_*` pair; used by `generateAIResponse` fan-out (ai/index.ts) from agents.ts:251,395, ai.ts:107,197,214 | same as P3 | same as P3 |
| P5 | **OpenAI** | ai/openai-service.ts:8-11 | `OPENAI_API_KEY` | Vaulted |
| P6 | **Gemini** | ai/gemini-service.ts:9 | `GEMINI_API_KEY` | Vaulted |
| P7 | **Perplexity** | ai/perplexity-service.ts:8-11 | `PERPLEXITY_API_KEY` | **NOT in `.env.op.tpl`** |
| P8 | **xAI** | ai/xai-service.ts:8-11 | `XAI_API_KEY` | **NOT in `.env.op.tpl`** |
| P9 | **Neon Postgres** | db.ts:6-7 (`postgres(connectionString)`), whole app | `DATABASE_URL` | Vaulted. Same physical DB the UMH integration reads via its own `EOS_*` env (repointed in 977a09c71) — the DSN exists in two vaults/env-surfaces; rotation must hit both. |
| P10 | **PostHog** | server: stub only (posthog.ts:1-5, no network); client: pageview capture (App.tsx, #191 §6) | `VITE_POSTHOG_API_KEY` (client-side only) | Vaulted |
| P11 | Dormant vault entries | — | `SESSION_SECRET` (Clerk owns sessions), `STITCH_API_KEY`/`STITCH_PROJECT_ID` (no server call site found) | Vaulted, unused server-side — hygiene entries |

Cross-cutting credential findings: **(a)** the runtime mutation hole W6 can
overwrite P5–P8 keys (and the dead `ANTHROPIC_API_KEY`) in-process,
unauthenticated — 1Password injection is only as good as the process's refusal
to accept new secrets over HTTP; **(b)** four referenced credentials
(`AI_INTEGRATIONS_ANTHROPIC_API_KEY`, `AI_INTEGRATIONS_ANTHROPIC_BASE_URL`,
`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, plus P7/P8) are outside the vault
template — the WP-P4-SECRETS-001 migration (head commit's own subject) is
incomplete against actual code references.

## 5. Import/build candidates 2..N (after S6 `/eos/tasks`)

Candidate #1 remains S6 `/eos/tasks` exactly as specified in
`2026-07-06_wp_p4_eos_beast_module_map.md` §6 (contract, acceptance criteria,
hazards — not restated here). The ranked continuation, with dependency
ordering at the end:

### C2 — Governed action-proposal production (the agents.ts:151 pipeline, UMH-originated)

- **App-side reference:** the chat action-tag pipeline — grammar advertised at
  agents.ts:232-236, extraction regex at :268, insert at :293-304
  (`status:'pending'`, `requiresApproval:true`).
- **UMH primitive:** Signal → Operation boundary; **ApprovalRequest creation**
  through `governed_mutation`. Today UMH can read (S1), decide (S2), execute
  (S3) and record (S4) proposals — but only the app can *mint* them. C2 makes
  UMH a producer into the same human approval queue: a new
  `projections/eos/integration/` accessor (e.g. `proposal_production.py`)
  whose `_execute` is a **single INSERT into agent_actions** mirroring
  storage.ts:1336-1361 defaults, submitted through `governed_mutation` like
  action_execution.py:281-300.
- **Acceptance sketch:** (1) INSERT-only — never UPDATE/DELETE; created row is
  always `status='pending'`, `requires_approval=true`; (2) `action_type`
  restricted to `EXECUTABLE_ACTION_TYPES` in v1 (proposing what UMH cannot
  execute invites drift; send_email proposals wait for C7); (3) per-type
  parameter validation before insert (reuse `_require_str`, tables.py:642) —
  no free-text passthrough of LLM output beyond validated keys; (4) `user_id`
  ∈ configured `user_ids`, `agent_id` verified to exist (FK is cascade-delete,
  schema §4.4); (5) provenance stamped in `metadata` (source=`umh`,
  envelope_id) so the poller/correlation layer can distinguish UMH-minted rows;
  (6) fail-closed on `eos_readiness()` identically to the decision seam;
  (7) proof loop: minted row visible in cockpit `/eos/action-proposals` AND the
  app's `/api/actions/pending`, approved by human, executed by S3, outcome in
  `umh_outcomes`.
- **Hazards:** poller signal-loop (UMH inserts → poller emits a Signal about
  UMH's own act — dedupe on the provenance stamp, `correlation.py` is the
  hook); id-scheme coexistence (app uses `action_${Date.now()}_rand`,
  storage.ts:1337 — UMH should use uuid4, column is text, no collision);
  W2's app-side approve race applies to any row UMH mints (the app's inline
  execute can win); prompt-injection provenance — C2 must never mint from
  unvalidated LLM text without the parameter allowlist (W4/W7 lesson).
- **Ordering:** buildable now (all dependencies merged). Highest-value next
  write seam.

### C3 — `/eos/documents` read surface (second governed-effect visibility loop)

- **App-side reference:** documents CRUD documents.ts:116-224; UMH insert
  target `insert_document_from_action` tables.py:556-585.
- **UMH primitive:** Trace/Proof observability — same WorkPacket-effect
  pattern as S6, applied to the executor's other effect. `create_document` is
  one of two activated action types; UMH can create documents it cannot see.
- **Acceptance sketch:** clone the S6 criteria (module map §6) with one
  deliberate narrowing: the view exposes id, title, user_id, folder_id, tags,
  created_at — **never `content`** (free-text payload hygiene, same rule that
  excluded `instructions`/`metadata` from S6).
- **Hazards:** `documents` requires adding to `VALID_SOURCE_TABLES` or a
  parallel read gate (today only 5 tables are readable, tables.py) — extend
  the frozen set consciously, with the same head-match gate; W10's app-side
  deletes mean absence of a row is not evidence execution failed.
- **Ordering:** after S6 (reuses its test harness and route pattern
  verbatim); independent of C2.

### C4 — `/eos/agents` read surface → organism-role correspondence (S10 activation)

- **App-side reference:** agents table (schema line 36 region: `roleLevel`
  chief/manager/laborer, `parentAgentId`, `department`, `isActive`).
- **UMH primitive:** organism role registry correspondence — RuntimeNode /
  authority-tier **labels in the view**, exactly like S6's status-vocabulary
  rule (correspondence lives in the view layer, never pushed into either
  schema).
- **Acceptance sketch:** SELECT-only flat view (id, name, role, roleLevel,
  department, parentAgentId, isActive, latestActivity); **never**
  `instructions`/`brainContent`/`knowledgeBase` (prompt material — and per W4,
  attacker-writable prompt material); hierarchy expressed as parent id, not a
  built tree (read-surface discipline invariant 5).
- **Hazards:** W4 means every field of this table is untrusted input until
  the Beast hardens PATCH /api/agents — the view must be labeled as app-truth,
  not organism-truth; do not seed organism state from it.
- **Ordering:** any time after S6; pure read, no owner gate.

### C5 — agent_metrics → Trace/feedback importer

- **App-side reference:** agent_metrics counters (schema line 451 region),
  written by incrementMetric (storage.ts:1459-1477) from the app executor
  (action-executor.ts:38-41).
- **UMH primitive:** feedback/quality signals (`substrate/execution/feedback.py`).
- **Acceptance sketch:** read-only SELECT of per-agent per-day counters;
  mapped into feedback observations tagged `source=eos_app`; explicitly **not
  summed** with `umh_outcomes` (disjoint populations: app metrics count only
  app-executed actions — W2 path; UMH executions never touch agent_metrics).
- **Hazards:** racy counters (§3.5) make values approximate; `api_cost` is
  text; date is text — treat as strings end-to-end.
- **Ordering:** low urgency; after C3/C4.

### C6 — Company-system ↔ BIS bridge, read side (S7)

- **App-side reference:** portfolios/companies routes (§3.3), BIS-shaped
  columns `stage/offer/targetCustomer/goals/assistantName` (companies, schema
  line 508 region).
- **UMH primitive:** L4 bridge (`DomainBridge`) to the BIS/venture registry
  (`substrate/state/business/`).
- **Blocked on:** owner ontology decision (module map §7.5 — are `companies`
  rows ventures; which side is authoritative). A read-only
  `/eos/companies` view could ship before the decision, but it would freeze
  vocabulary prematurely — sequence the decision first.
- **Hazards:** actively churning schema region (mirror-drift epicenter, module
  map §5); free-text BIS-shaped fields (no enum discipline app-side).

### C7 — send_email execution via AdapterCall + credential gate (S8)

- **Blocked on (widened this packet):** not just the `oauth_tokens` plaintext
  migration — **`GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` are themselves
  unvaulted** (§4.3 P2), and W6 lets anonymous HTTP overwrite provider keys in
  the app process. Executing provider actions from UMH before the Beast
  credential surface is fixed would launder an unsafe credential posture
  through a governed pipeline.
- **UMH primitive:** AdapterCall through `adapters/` GWS +
  `validate_credential_source()` (`substrate/execution/credential_gate.py`);
  allowlist expansion is one frozen-set edit (tables.py:451) **after** the
  gate passes — the claim SQL picks it up automatically.

### C8 — CRM governed mutation (S9)

Owner-gated app behavior change (route agent-attributed CRM writes through an
approval flow). Unchanged from module map; W9 documents the exact columns and
call sites for the eventual packet.

### C9 — App-side write hardening (prerequisite gate, not an import)

Not a UMH build — a Beast change owner-approval item that this packet's
findings make **sequencing-critical**: before any deeper two-writer coupling
(C2 included, ideally), the app needs (1) auth gates on the 15 ANON write
endpoints (§3.7 list); (2) a status guard on approve (actions.ts:43: refuse
unless `action.status === 'pending'`) and ideally claim semantics in
`updateAction` (mirror tables.py:489 — one WHERE clause); (3) the
initSampleData destructive branch (storage.ts:272-286) removed or gated to
empty-DB-only; (4) `/api/keys/save` deleted or admin-gated (ai.ts:61); (5) the
four unvaulted credentials added to `.env.op.tpl`. Items already partly on the
module map's owner ledger (§7.6) — this list is the file:line-precise version.

### Dependency ordering

```
S6 /eos/tasks (candidate #1, spec'd in #191)
 ├─ C3 /eos/documents        (pattern reuse; + VALID_SOURCE_TABLES extension)
 ├─ C4 /eos/agents           (pattern reuse; app-truth labeling)
 └─ C5 metrics→feedback      (independent read; after C3/C4 by value)
C2 proposal production        (buildable now; SAFER after C9.2 approve-guard)
C6 companies↔BIS              (blocked: owner ontology decision)
C7 send_email AdapterCall     (blocked: oauth_tokens migration + P2/P3 vaulting + W6 removal)
C8 CRM governed mutation      (blocked: owner app-change approval)
C9 app hardening              (owner-gated; unblocks C7, de-risks C2/W2)
```

## 6. Additions to the owner-approval ledger (extends module map §7)

8. **W1**: disable/gate `initSampleData`'s destructive re-seed
   (storage.ts:272-286) — CRITICAL class; it can delete live `tasks` rows on
   boot.
9. **W6**: remove or admin-gate `POST /api/keys/save` (ai.ts:61-92).
10. **W2**: add `status==='pending'` precondition to approve (actions.ts:43-62)
    and a status-guarded `updateAction`; decide whether app-side inline
    execution should defer to the UMH claim contract when both are active.
11. Auth gates on the 15 anonymous write endpoints (§3.7) — especially
    tasks.ts (7) and agents.ts PATCH/POST.
12. Vault the four unvaulted credentials (`AI_INTEGRATIONS_ANTHROPIC_API_KEY`,
    `AI_INTEGRATIONS_ANTHROPIC_BASE_URL`, `GOOGLE_CLIENT_ID`,
    `GOOGLE_CLIENT_SECRET`; plus P7/P8 if those providers stay) and reconcile
    the dead `ANTHROPIC_API_KEY` tpl entry against the `AI_INTEGRATIONS_*`
    pair the code actually reads.
13. W11 ownership check on notification read-mark; companies
    departments/roles ownership verification.
14. Delete the dead duplicate `server/middleware/auth.ts` (+ its debug logger)
    and the committed `auth-debug.log` (supersedes ledger item 6's phrasing —
    the logger is dormant, not live).

## 7. Method + proof

- Access: `ssh "antonys beast pc@100.74.199.102"`, read-only commands only
  (`git log -1`, `git status --porcelain`, `git ls-files`, `findstr /n`,
  `findstr /s`, `type`, `powershell Get-Content` slices). Zero mutations.
- Beast files read **in full with line numbers** this packet (24):
  `server/routes.ts`, `server/index.ts`, `server/auth.ts`,
  `server/middleware/auth.ts`, `server/middleware/clerk-org.ts`,
  `server/clerkAdmin.ts`, `server/db.ts`, `server/posthog.ts`,
  all 13 `server/routes/*.ts`, `server/services/action-executor.ts`,
  `server/integrations/gmail.ts`, `.env.op.tpl`.
- Beast files read by targeted extraction: `server/storage.ts` (full
  76-method line census via `findstr /n /c:"async "` + four body slices:
  lines 161-330, 806-878, 1336-1372), `server/ai/gateway.ts` (lines 1-80 +
  env census), `server/openai.ts` (lines 1-50), `server/ai/*-service.ts`
  (`process.env` census).
- Repo-wide sweeps: `middleware/auth` import search (0 hits → §1.1),
  `db.insert/update/delete` + `.insert(/.update(/.delete(` write census
  (84 hits, all classified in §3), `process.env` census over `server/ai/` +
  `server/openai.ts` (12 hits → §4.3).
- `/opt/OS` files read: `projections/eos/integration/action_execution.py`
  (full), `tables.py` (lines 440-649 + function census), both #191 docs (full).
- Handler-count cross-check: 94 = 59 auth'd + 32 ungated + 3 by-design
  (§3.7 breakdown sums exactly; per-module counts re-verified against the
  #191 census during the full module reads).
- Fallback declaration: none needed — Beast SSH worked throughout; the
  `/opt/OS` mirror was not used as source truth for anything (it remains
  drifted per #191 §5, unresolved by design in this docs-only packet).
