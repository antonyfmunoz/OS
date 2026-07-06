# EntrepreneurOS Beast Module / Seam Map

**Work packet:** WP-P4-EOS-BEAST-MODULE-MAP-001
**Date:** 2026-07-06
**Source truth:** EntrepreneurOS on the Beast — `C:\dev\dev\EntrepreneurOS`,
branch `feature/company-system`, head `9c8725f`, working tree clean, read
**live over SSH this packet** (not from the `/opt/OS` mirror — see §5 for why
that matters).
**Raw inventory companion:**
`docs/audits/2026-07-06_wp_p4_eos_beast_route_schema_inventory.md`
(every endpoint, every table, every storage method, action grammar, live/dead
client pages — all counts are there; this doc carries the mapping and the
seam decisions).

**Prior work this builds on (does not duplicate):**
- `docs/EOS_APP_MODULE_MAP.md` + `data/umh/projection_reconciliation/eos_app_module_map.json`
  (#181 — 20-module map, build-safety gate in
  `projections/eos/integration/module_map.py`)
- `docs/EOS_ACTION_EXECUTOR_SEAM.md` + `eos_action_executor_seam_map.json`
  (#182 — 13-seam map of the action executor)
- Built seams since: #183 ActionProposal read (`action_proposals.py`),
  #184 approve/reject command (`action_decisions.py`), executor-activate
  (`action_execution.py`, non-provider types only), #186/#188 cockpit
  approval queue (`transports/api/cockpit_core_eos_routes.py`
  `/eos/action-proposals*`), #187 browser verification, and the runtime
  unblock repointing the EOS integration at the app database (977a09c71).

This packet is pure comprehension: no code imported, no code copied, no
schema migrated, zero writes to the Beast.

---

## 1. Corrections to the prior map (ground-truth drift found this probe)

The prior map (#181, probe 2026-07-05) is right about the product shape but
stale on four load-bearing facts. Same head (`9c8725f`), but #181 read the
`/opt/OS` inspection mirror, which had **silently drifted** from the Beast
working tree:

1. **Routes are modular, not monolithic.** `server/routes.ts` is a thin
   registrar; the 94 endpoints live in 14 modules under `server/routes/`
   (actions, agents, ai, analytics, companies, conversations, crm,
   documents, integrations, notifications, portfolios, tasks, workflows +
   auth.ts). Any seam plan that assumed "one 2,360-line file" is planning
   against a repo that no longer exists.
2. **Auth is Clerk, not passport+Firebase.** `server/auth.ts` wires
   `clerkMiddleware() → extractClerkOrg → attachClerkUser` globally;
   `users.clerkUserId` replaced `users.firebaseUid`; local user rows are
   lazy-created from Clerk identities. The prior map's owner-decision item
   "EOS passport/Firebase vs UMH Clerk must be reconciled" is **half
   resolved on the Beast already** — both sides are Clerk (different Clerk
   applications; see hazards §7.3).
3. **The schema is 35 tables, not 15.** `feature/company-system` added
   portfolios, companies, session, workflows + 16 generator-scaffold tables
   to `shared/schema.ts`. There is also a dead 36-table
   `server/generated/schema.ts`. Full census in the inventory doc §4.
4. **The live client is the company-system UI.** `App.tsx` routes
   portfolios → company command center → org/chat/workflows/tasks. The
   17-page dashboard universe (CRM, documents, analytics, notifications,
   integrations pages) is dead code — roughly half of the 94 server endpoints currently
   have **no live UI consumer** in the app itself.

Nothing in the drift invalidates the built seams: the columns UMH actually
reads (`agent_actions`, `agent_metrics`, `crm_*`, `tasks`, `users.id` — see
`projections/eos/integration/tables.py`) are byte-identical between mirror
and Beast. The drift is in `users` auth columns and the appended
company-system tables.

## 2. Module map — app modules → UMH substrate primitives

Layer legend: L2 = substrate primitive · L3 = projection domain ·
L4 = semantic bridge. "Import" always means *semantics*, never code.

### 2.1 Server modules

| App module (Beast path) | What it is | UMH primitive / target | Disposition |
|---|---|---|---|
| `server/index.ts` | Express entrypoint, :5000, health probes | deployment entrypoint (`services/`-class concern) | stays app-side; UMH health = `/eos/activation` readiness |
| `server/routes.ts` + `server/routes/actions.ts` | action queue + approve/reject over `agent_actions` | **Approval** + `governed_mutation` lifecycle | **seam BUILT** (#183/#184/#186) — app routes remain for the app; UMH is the governed twin |
| `server/services/action-executor.ts` | approve→execute→record→retry dispatcher | **Operation** on canonical runtime (`governed_mutation → MutationRouter → GovernedExecutionSpine`) | semantics imported (#185 executor-activate, non-provider subset); `send_email` deferred (credential law) |
| `server/routes/agents.ts` (chat + `[ACTION:...]` extraction) | agent persona chat; bracket-grammar proposal creation | **Signal → Operation** boundary; grammar itself is L3 prompt protocol | map-only; proposal *creation* from UMH side is a future seam (§6 alternatives) |
| `server/routes/tasks.ts` + tasks storage ops | task CRUD, subtasks, collaborators, assignment | **WorkPacket** semantics (L3 vocabulary over `substrate/types.py::WorkPacket`) | **first-seam candidate** (§6) |
| `server/routes/crm.ts` | CRM contacts/deals/activities CRUD | L3 domain objects; agent-attributed writes must become **governed_mutation** | read side already polled (`tables.py`, `poller.py`); write side owner-gated |
| `server/routes/documents.ts` | folders/documents CRUD | L3 domain; `create_document` effect already governed via executor seam | map-only |
| `server/routes/notifications.ts` | user notification feed | projection read surface later; overlaps organism state broadcast | map-only |
| `server/routes/portfolios.ts` + `companies.ts` | **company-system**: portfolio → companies with stage/offer/targetCustomer/goals | **L4 bridge to BIS/venture registry** — `companies` rows are BIS-shaped venture records | NEW since #181; second-seam candidate (§6.4) |
| `server/routes/workflows.ts` + `conversations.ts` | workflow shells (active/paused), conversation shells | WorkPacket/workflow primitives eventually; schema is scaffold-thin | too thin to seam; map-only |
| `server/routes/ai.ts` + `server/ai/*` (7 files) | 5-provider gateway, model registry, `/api/keys/save` | duplicate of `adapters/models/model_router.py::call_with_fallback` | **import-never**; app-local only while EOS runs standalone |
| `server/routes/analytics.ts` + `agent_metrics` ops | per-agent per-day counters | **Trace → feedback** (`substrate/execution/feedback.py`) | outcome writeback already lands via `outcomes.py`; metrics import later |
| `server/routes/integrations.ts` + `server/integrations/gmail.ts` | Gmail OAuth + send, `oauth_tokens` persistence | **AdapterCall** (`adapters/` GWS) + `credential_gate.py` | blocked on plaintext-token migration (owner-gated) |
| `server/auth.ts` + `middleware/auth.ts`, `clerk-org.ts` | Clerk auth, lazy local-user sync, org extraction | transports auth boundary (`transports/api/http/middleware/`) | stays app-side; identity-bridge decision owner-gated (§7.3) |
| `server/storage.ts` (IStorage, 76 methods) | single DB gateway for the original 15-table universe | the app-side seam surface where a governed adapter would attach | map-only; note: company-system routes **bypass** IStorage |
| `server/generated/**` (23 files incl. 21 storage stubs) | dead generator output, empty registrar | none | delete-candidate on Beast (owner call); never import |
| `server/openai.ts`, `server/gateway-era files`, `llmApi.ts` (root) | legacy AgentBrain / Replit leftovers | none | import-never |
| `server/posthog.ts`, `client posthog` | product analytics | instance config | stays app-side |

### 2.2 Client modules

| App module | What it is | UMH mapping | Disposition |
|---|---|---|---|
| `client/src/App.tsx` + live pages (14) | company-system product UI (portfolios/command-center/org/chat/workflows/tasks) | customer-facing projection UI — stays on Beast/Fly | never copied; cockpit is the operator surface, not a replacement |
| `client/src/components/action-approval-panel.tsx` | app-side approval queue widget (currently unrouted) | superseded operationally by cockpit `/eos/action-proposals` queue (#186) | map-only |
| 18 dead pages + 47 shadcn `ui/` files | unrouted legacy dashboard + regenerable kit | none | import-never |
| `client/src/lib/queryClient.ts` + `clerk.tsx` | Clerk token injection into fetch | auth boundary reference for any future UMH→app API call | map-only |

### 2.3 Schema domains (35 live tables → 5 domains)

| Domain | Tables | UMH primitive |
|---|---|---|
| Agent workforce | agents, tasks, messages, ai_messages, agent_metrics | organism roles (RuntimeNode tiers), WorkPacket, Signal, Trace/feedback |
| Governed actions | agent_actions, oauth_tokens | ApprovalRequest/Operation (BUILT), AdapterCall+credential_gate (blocked) |
| CRM | crm_contacts, crm_deals, crm_activities | L3 domain; agent-attributed writes → governed_mutation (gap) |
| Documents | folders, documents | L3 domain; create effect governed via executor seam |
| Company system | portfolios, companies, workflows, departments, roles, steps, conversations (+ session) | **L4 → BIS/venture registry** (companies.stage/offer/targetCustomer are BIS vocabulary) |
| Scaffold/noise | login, signup, forgotPassword, resetPassword, metrics, recentActivity, profile, security, config, register, logout, me (+ dead `server/generated/schema.ts`, + `shared/models/chat.ts` collision) | none — hygiene debt |

## 3. Seam map — where the app boundary meets UMH governed contracts

Ordered by maturity. "App side" = Beast/Fly Express app; "UMH side" =
`/opt/OS` substrate + projection integration.

| # | Seam | App-side surface | UMH-side surface | Status |
|---|---|---|---|---|
| S1 | **Action proposals (read)** | `agent_actions` rows (pending) | `action_proposals.py` → `/eos/action-proposals` (GET) | **BUILT** #183/#186, browser-verified #187 |
| S2 | **Action decisions (write)** | approve/reject semantics of `/api/actions/:id/*` | `action_decisions.py` via `governed_mutation` → `/eos/action-proposals/{id}/approve|reject` | **BUILT** #184 |
| S3 | **Action execution (non-provider)** | `executeAction()` create_task/create_document branches | `action_execution.py`, `EXECUTABLE_ACTION_TYPES={create_task,create_document}`, fail-closed guard | **BUILT** (executor-activate) |
| S4 | **Outcome writeback** | `agent_actions.execution_result` / status | `outcomes.py` dual writeback (source row umh_status + `umh_outcomes` audit table) | **BUILT** |
| S5 | **DB polling → Signals** | crm_contacts/crm_deals/crm_activities/tasks/agent_actions inserts | `poller.py` + `signals.py` → SignalEnvelope | **BUILT** (read spine) |
| S6 | **Tasks ↔ WorkPacket read surface** | `tasks` table (WorkPacket-shaped: status/priority/assignee/subtask/collaborators) | none yet — no `/eos/tasks` | **FIRST CANDIDATE** (§6) |
| S7 | **Company system ↔ BIS/venture registry** | `portfolios`/`companies` (stage, offer, targetCustomer, goals, orgId) | none yet — BIS lives in `substrate/state/business/` | candidate #2 |
| S8 | **send_email execution** | `executeAction()` gmail branch over plaintext `oauth_tokens` | blocked: credential-injection law requires 1Password migration first | **BLOCKED** (owner-gated) |
| S9 | **CRM governed mutation** | `crm_deals.assignedAgentId` / `crm_activities.createdByAgentId` writes bypass approval | must route through `governed_mutation` | owner-gated (app behavior change) |
| S10 | **Agent hierarchy ↔ organism roles** | agents.roleLevel chief/manager/laborer, parentAgentId | RuntimeNode / authority tiers | map-only |
| S11 | **AI routing** | `server/ai/` gateway | `model_router.call_with_fallback` | convergence-on-rebuild only, never a code seam |
| S12 | **Identity bridge** | Clerk app users (`users.clerkUserId`) | cockpit Clerk lock (AFM's Clerk ID) | decision seam — must be settled before any user-facing crossover (§7.3) |

Boundary invariant that holds everywhere: **UMH never calls the app's HTTP
API and the app never calls UMH** — the sanctioned meeting point today is
the shared Neon database, read/written UMH-side only through
`projections/eos/integration/tables.py` (SELECT + bounded UPDATE on
`agent_actions`, plus `umh_outcomes`), surfaced only through
discipline-conformant `/eos/*` routes
(`.claude/rules/projection-read-surfaces.md`).

## 4. Already-built seam contract (for orientation, verified in-tree)

`projections/eos/integration/` today: `readiness.py` (build-safety gate),
`module_map.py` (#181 accessor), `action_seam.py` (#182), `tables.py`
(typed read/bounded-write layer; `VALID_SOURCE_TABLES = {crm_contacts,
crm_deals, crm_activities, tasks, agent_actions}`), `action_proposals.py`,
`action_decisions.py`, `action_execution.py`, `poller.py`, `signals.py`,
`handlers.py`, `outcomes.py`, `correlation.py`, `manifest.py`.
Transport: `transports/api/cockpit_core_eos_routes.py` (6 read routes + 3
action-proposal command routes). Every accessor fails closed on
`eos_readiness()['source_build_safe']` + live-head match.

## 5. Mirror drift finding (must be handled before the next column-level packet)

Measured this packet via `git hash-object` on Beast vs the mirror:

- `shared/schema.ts`: Beast `ff64b01d` ≠ mirror `d6f2d5d6` — mirror is
  pre-Clerk (`firebaseUid`) and missing all 20 company-system/scaffold
  tables (358 diff lines).
- `server/storage.ts`: Beast `d5d8283a` ≠ mirror `76e75cd6`.
- `shared/models/chat.ts`: identical.

`projection_source_sync.json` records `mirror_fidelity: "full"` at the same
head — **that flag is stale at file level**. Consequences:

1. Anything that reads the mirror for column truth (as #181 did) can emit a
   wrong map. This packet read the Beast live; the inventory doc is the
   corrected census.
2. The built runtime is safe: every column `tables.py` touches sits in the
   byte-identical region (verified by full-file diff — divergence is
   confined to `users.clerkUserId`/`firebaseUid` and lines 482+).
3. **Deferred debt:** re-run the #179 sync harness (or refresh
   `data/repos/entrepreneuros` from Beast) and make `mirror_fidelity`
   computed from file hashes, not directory presence. Not done in this
   packet — docs-only scope, and the mirror refresh is a governed sync
   operation, not a mapping step.

## 6. FIRST sanctioned importable/buildable seam candidate

### Decision: S6 — **EOS Tasks ↔ WorkPacket read surface** (`/eos/tasks`)

One projection-owned accessor translating EOS `tasks` rows into a flat
WorkPacket-shaped governance view, exposed through one
discipline-conformant read route. Pattern: exactly what
`action_proposals.py` + `/eos/action-proposals` did for Approval — applied
to the WorkPacket correspondence.

Why this one (and not the alternatives):

- **The Approval seam is finished** (S1-S4 read/decide/execute/writeback +
  cockpit UI). The packet question "first importable seam" now means the
  *next* primitive, and WorkPacket is the highest-value unproven mapping:
  the executor already *creates* tasks (`create_task` is one of the two
  activated action types) — but UMH cannot yet *see* the tasks it creates.
  This seam closes that loop: governed effect → observable state, no new
  write path.
- **Infrastructure is already in place:** `tables.py` already SELECTs the
  `tasks` table for the poller (agent-linked task query, WP-P0-010) and
  `TASKS_TABLE` is in `VALID_SOURCE_TABLES`. The accessor is a reshape of
  an existing read, not a new DB capability.
- **Zero drift exposure:** the `tasks` table definition is byte-identical
  between mirror and Beast head (verified §5) and is in the original stable
  15-table universe, not the churning company-system region.
- Alternatives ranked out: S7 company-system↔BIS is the strategically
  biggest seam but sits on scaffold-thin, actively-churning schema plus an
  ontology decision (companies↔ventures) that needs an owner call first;
  S8 send_email is blocked by the credential law; S9 CRM mutation changes
  app behavior (owner-gated); S11 AI routing is convergence-only.

### Shape (contract, not implementation)

- `projections/eos/integration/task_views.py` (or extend `tables.py` within
  its size budget): `fetch_task_views(...) -> list[TaskView]` — SELECT-only
  over `tasks` (id, title, status, priority, task_type, agent_id,
  assigned_by_id, parent_task_id, due_date, created_at; **never**
  `metadata`/`instructions` free-text payloads in v1), plus a
  WorkPacket-correspondence mapping (`status todo/in-progress/done →
  EnvironmentEnvironmentPacketStatus` names) as *labels in the view*, not new types.
- Route: `GET /eos/tasks` in `cockpit_core_eos_routes.py`, thin wrapper,
  lazy import, try/except → stable error dict, per
  `.claude/rules/projection-read-surfaces.md` (all six invariants; it does
  NOT go on the legacy allowlist).

### Acceptance criteria

1. **Read-only:** accessor issues SELECTs only; no INSERT/UPDATE/DELETE; no
   new tables; no `drizzle-kit push`; zero Beast writes.
2. **Fail-closed on source truth:** returns `[]`/not-ready dict unless
   `eos_readiness()['source_build_safe']` is True and the recorded head
   matches the live VERIFIED Beast head (same gate contract as
   `build_mappable_modules()` / `mappable_seams()`).
3. **Read-surface discipline:** projection-owned accessor; thin transport
   wrapper; lazy projection import; never raises a 500; no domain-object
   expansion in the route; no direct registry/file reads. Covered by
   extending `tests/test_projection_read_surface_discipline.py` — the new
   route must conform, not be allowlisted.
4. **Type coherence:** no new Enum/BaseModel duplicating `WorkPacket` /
   `EnvironmentEnvironmentPacketStatus` — check `substrate/canonical_types.py` first; the
   view is a flat dict with correspondence labels. Gate:
   `scripts/check_type_divergence.py` clean.
5. **Payload hygiene:** no secrets, no free-text `instructions`/`metadata`
   blobs, no email addresses in the default view; column list pinned and
   asserted in a shape test against head `9c8725f`.
6. **Env-disabled-safe:** with EOS DB env unset, the accessor returns a
   stable disconnected dict (parity with `eos_readiness()` behavior).
7. **Verification pass:** unit tests (gate closed / gate open / shape /
   empty DB), plus a live read against the real EOS Neon DB showing at
   least the tasks created by the activated executor, plus cockpit fetch of
   `/eos/tasks` returning 200 through auth.

### Hazards (specific to this seam)

- **Duplicate types:** `WorkPacket` already exists in `substrate/types.py`
  and `EnvironmentWorkPacket` in `nodes/environments/work_packet.py`; a third
  "EosTaskPacket" model would trip the type-coherence law. Return dicts.
- **Schema drift:** `tasks` is stable today, but the company-system branch
  is active development; the head-match gate (criterion 2) is the
  mechanical defense, and the shape test turns silent column drift into a
  loud failure.
- **Auth boundary:** `/eos/tasks` is behind the cockpit's Clerk lock
  (operator surface). It must NOT be conflated with app-user visibility —
  EOS app users authenticate against a different Clerk application; this
  read surface is operator-only until S12 (identity bridge) is decided.
- **Status-vocabulary temptation:** do not "normalize" EOS statuses into
  UMH enums in the DB or push UMH vocabulary into the app; the
  correspondence lives in the view layer only.
- **Mirror staleness:** any implementer verifying columns must verify
  against the Beast (or a refreshed mirror), not
  `data/repos/entrepreneuros` as it stands (§5).

## 7. Owner approvals required before any mutation (consolidated, updated)

1. Schema migration of any kind against the EOS Neon DB (CRITICAL class,
   row counts first) — includes resolving the `shared/models/chat.ts`
   `messages`/`conversations` collisions and dropping the 16 scaffold
   tables + dead `server/generated/` universe.
2. `oauth_tokens` plaintext → 1Password migration (prerequisite for S8
   send_email execution).
3. **Identity bridge (S12):** app Clerk application ↔ cockpit Clerk lock —
   whether/how an EOS app user maps to a UMH operator. Prior blocker
   "passport/Firebase vs Clerk" is resolved on the Beast (Clerk-only), but
   the two-Clerk-apps question replaces it.
4. Routing agent-attributed CRM mutations through `governed_mutation` (S9 —
   app behavior change).
5. Company-system ↔ BIS ontology decision (S7): are `companies` rows
   ventures in the BIS registry sense, and which side is authoritative.
6. Beast hygiene: delete dead `server/generated/**`, 18 dead client pages,
   Replit artifacts, the `middleware/auth.ts` hardcoded `auth-debug.log`
   append (it writes on every request), and the committed 3.8 MB
   `auth-debug.log`.
7. Any write to the Beast working tree, any copy of app-body code into
   `/opt/OS` (VPS node role: `shared/schema.ts` mirror only), any refresh
   of the inspection mirror (governed sync operation).

## 8. Method + proof

- Access: `ssh "antonys beast pc@100.74.199.102"`, read-only commands only
  (`git ls-files`, `git log -1`, `git status --porcelain`, `git hash-object`,
  `type`, `more +N`, `findstr /n`). Zero mutations: no writes, no resets,
  no stash, no clean, no checkout.
- Files read in full on Beast: `server/routes.ts`, `server/index.ts`,
  `server/auth.ts`, `server/middleware/auth.ts`,
  `server/middleware/clerk-org.ts`, `server/services/action-executor.ts`,
  `server/ai/index.ts`, `server/generated/index.ts`, `shared/schema.ts`
  (826 lines, all), `client/src/App.tsx`.
- Files read by targeted extraction: `server/routes/*.ts` (all 14, route
  signatures + action grammar sections), `server/storage.ts` (full IStorage
  interface, 76 methods), `shared/models/chat.ts` +
  `server/generated/schema.ts` (table defs), `package.json` (scripts/deps).
- Repo census: 236 tracked files across server/client-src/shared/scripts/
  migrations (breakdown in inventory doc header); 59 server files,
  94 live HTTP handlers, 35 + 2 + 36 table definitions across the three
  schema universes.
- Cross-checks on `/opt/OS`: `git hash-object` mirror comparison (§5),
  `projections/eos/integration/tables.py` column usage,
  `transports/api/cockpit_core_eos_routes.py` existing `/eos/*` routes,
  `projection_source_sync.json` recorded state.
- Fallback declaration: **not needed** — Beast SSH worked; the mirror was
  used only as a diff target, never as source truth.
