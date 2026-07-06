# EntrepreneurOS Beast Route / Action / Schema Inventory (Raw)

**Work packet:** WP-P4-EOS-BEAST-MODULE-MAP-001 (companion raw inventory)
**Date:** 2026-07-06
**Source truth:** EntrepreneurOS on the Beast — `C:\dev\dev\EntrepreneurOS`,
branch `feature/company-system`, head `9c8725f`
("chore(secrets): standardize 1Password runtime references"), working tree
clean (`git status --porcelain` = 0 lines), read live over SSH this packet.
**Method:** read-only SSH (`git ls-files`, `type`, `findstr`, `more`,
`git hash-object`). Zero writes to the Beast. No code copied into `/opt/OS`.
**Companion doc:** `docs/audits/2026-07-06_wp_p4_eos_beast_module_map.md`
(module map, seam map, first-seam candidate, hazards).

Ground-truth file counts (from `git ls-files` on Beast, this probe):
`server/` 59 files · `client/src/pages/` 32 · `client/src/components/` 79
(47 of which are the shadcn `ui/` kit) · `client/src/hooks/` 9 ·
`client/src/lib/` 9 · `shared/` 4 · `scripts/` 38 · `migrations/` 6.

---

## 1. Server HTTP route inventory — 94 endpoints

Registrar: `server/routes.ts` (thin — imports 13 `register*Routes` modules
from `server/routes/`, plus `setupAuth` and the dead generated registrar).
Entrypoint: `server/index.ts` (Express on `PORT` env, default :5000).

The prior map (#181, `docs/EOS_APP_MODULE_MAP.md`) described `routes.ts` as
"monolithic ~2,360 lines". **That is stale**: at head `9c8725f` routes are
split into 14 modules. Counts below are from `findstr` over
`server/routes/*.ts` at the live head.

### 1.1 `server/index.ts` — 2

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | Dockerfile HEALTHCHECK / platform probes |
| GET | `/api/health` | `{status:"ok", app:"eos"}` |

### 1.2 `server/auth.ts` — 2 (Clerk-only auth)

| Method | Path | Notes |
|---|---|---|
| GET | `/api/user` | `requireAuth`; strips password; PostHog `user_logged_in` |
| POST | `/api/logout` | 200 no-op (Clerk owns sessions) |

Global middleware chain (every request): `clerkMiddleware()` →
`extractClerkOrg` (JWT orgId → `req.clerkOrg`) → `attachClerkUser`
(Clerk userId → local `users` row lookup, **lazy-create** with random
password bytes; installs `req.isAuthenticated()` polyfill for the old
Passport-era inline checks). Passport and Firebase are gone at this head.

### 1.3 `server/routes/actions.ts` — 5 (the governed-action seam)

| Method | Path |
|---|---|
| GET | `/api/actions` (filters: status, agentId) |
| GET | `/api/actions/pending` |
| GET | `/api/actions/:id` |
| POST | `/api/actions/:id/approve` (ownership check, then **executes inline**) |
| POST | `/api/actions/:id/reject` |

### 1.4 `server/routes/agents.ts` — 11

| Method | Path |
|---|---|
| GET | `/api/agents` |
| GET | `/api/agents/:id` |
| PATCH | `/api/agents/:id` |
| POST | `/api/agents` |
| GET | `/api/agents/:id/messages` |
| POST | `/api/agents/:id/clear-messages` |
| POST | `/api/agents/:id/chat` (bracket-grammar action proposal extraction — §3) |
| GET | `/api/agents/:id/tasks` |
| POST | `/api/agents/:id/generate-response` |
| GET | `/api/agents/:id/collaborative-tasks` |
| GET | `/api/agents/:id/metrics` |

### 1.5 `server/routes/ai.ts` — 10

| Method | Path |
|---|---|
| GET | `/api/ai/models` |
| GET | `/api/ai/provider-status` |
| POST | `/api/keys/save` (**mutates `process.env` from HTTP body** — hazard) |
| POST | `/api/ai/generate` |
| POST | `/api/ai/multi-agent` |
| GET | `/api/ai-assistant/messages` |
| POST | `/api/ai-assistant/messages` |
| DELETE | `/api/ai-assistant/messages` |
| POST | `/api/llm/chat` |
| GET | `/api/ai/stats` |

### 1.6 `server/routes/analytics.ts` — 2

GET `/api/stats` · GET `/api/analytics`

### 1.7 `server/routes/companies.ts` — 7

| Method | Path |
|---|---|
| GET | `/api/companies/:id` |
| GET | `/api/companies/:id/tasks` |
| GET | `/api/companies/:id/departments` |
| GET | `/api/companies/:id/roles` |
| GET | `/api/companies/:id/workflows` |
| GET | `/api/company` |
| POST | `/api/company` |
| PATCH | `/api/company/:id` |

(8 handlers listed; `/api/company` GET+POST counted separately = 7 paths, 8
handlers. Handler count is what the totals below use.)

### 1.8 `server/routes/conversations.ts` — 1

GET `/api/conversations/:id`

### 1.9 `server/routes/crm.ts` — 12

GET/POST/PATCH over three resources, plus by-id GETs:
`/api/crm/contacts` (GET list, GET :id, POST, PATCH :id),
`/api/crm/deals` (GET list, GET :id, POST, PATCH :id),
`/api/crm/activities` (GET list, GET :id, POST, PATCH :id).
No DELETE on any CRM resource.

### 1.10 `server/routes/documents.ts` — 10

`/api/folders` (GET list, GET :id, POST, PATCH :id, DELETE :id),
`/api/documents` (GET list, GET :id, POST, PATCH :id, DELETE :id).

### 1.11 `server/routes/integrations.ts` — 6

| Method | Path |
|---|---|
| GET | `/api/integrations` |
| POST | `/api/integrations/connect` |
| GET | `/api/integrations/gmail/auth` (OAuth kickoff) |
| GET | `/api/auth/google/callback` (OAuth redirect target) |
| GET | `/api/integrations/gmail/status` |
| POST | `/api/integrations/gmail/disconnect` |

### 1.12 `server/routes/notifications.ts` — 5

GET `/api/notifications` · GET `/api/notifications/count` ·
POST `/api/notifications/:id/read` · POST `/api/notifications/read-all` ·
DELETE `/api/notifications/:id`

### 1.13 `server/routes/portfolios.ts` — 7

GET `/api/portfolios` · POST `/api/portfolios` · GET `/api/portfolios/:id` ·
PUT `/api/portfolios/:id` · DELETE `/api/portfolios/:id` ·
GET `/api/portfolios/:id/companies` · POST `/api/portfolios/:id/companies`

### 1.14 `server/routes/tasks.ts` — 11

| Method | Path |
|---|---|
| GET | `/api/tasks` |
| GET | `/api/tasks/:id` |
| POST | `/api/tasks` |
| PATCH | `/api/tasks/:id` |
| DELETE | `/api/tasks/:id` |
| POST | `/api/tasks/:id/collaborators` |
| POST | `/api/tasks/:id/assign` |
| POST | `/api/tasks/:id/subtask` |
| GET | `/api/tasks/:id/subtasks` |
| GET | `/api/tasks/:id/messages` |
| POST | `/api/tasks/:id/messages` |

### 1.15 `server/routes/workflows.ts` — 2

GET `/api/workflows` · POST `/api/workflows`

### 1.16 `server/generated/index.ts` — 0 (dead)

`registerGeneratedRoutes()` is an **empty stub**. Its header comment states
all generated routes were removed because they called nonexistent storage
methods and returned 500s. The 21 files under `server/generated/storage/`
and the 36 table defs in `server/generated/schema.ts` are orphaned
generator output.

### Endpoint total

90 handlers in `server/routes/*.ts` + 2 in `auth.ts` + 2 in `index.ts`
= **94 live HTTP handlers**. Independent check: the `findstr` extraction over
`server/routes/*.ts` emitted exactly 90 `app.<method>(` handler lines
(actions 5, agents 11, ai 10, analytics 2, companies 8, conversations 1,
crm 12, documents 10, integrations 6, notifications 5, portfolios 7,
tasks 11, workflows 2 = 90), all listed above exhaustively.

---

## 2. Storage layer — `server/storage.ts` (51,003 bytes)

One `IStorage` interface gates every DB access; `DatabaseStorage` implements
it over Drizzle (`server/db.ts`, Neon). **76 interface methods** at head
`9c8725f`, grouped:

| Domain | Count | Methods |
|---|---|---|
| Users | 8 | getUsers, getUser, getUserByUsername, getUserByEmail, **getUserByClerkId**, createUser, createOrUpdateUser, updateUser |
| Agents | 5 | getAgents, getAgent, createAgent, updateAgent, updateAgentActivity |
| Tasks | 9 | getTasks, getTask, createTask, updateTask, deleteTask, getAgentTasks, getCollaborativeTasks, getTasksByType, getSubtasks |
| Messages | 7 | getAgentMessages, getTaskMessages, getConversationMessages, getAllMessages, clearAgentMessages, addAgentMessage, addCollaborativeMessage |
| Collaboration | 3 | addAgentCollaborator, assignTaskToAgent, createSubtask |
| Integrations | 2 | getIntegrations, connectIntegration |
| Notifications | 6 | getNotifications, getUnreadNotificationsCount, createNotification, markNotificationAsRead, markAllNotificationsAsRead, deleteNotification |
| AI assistant | 3 | getAiMessages, addAiMessage, clearAiMessages |
| CRM | 12 | get/getOne/create/update × contacts, deals, activities |
| Folders | 5 | getFolders, getFolder, createFolder, updateFolder, deleteFolder |
| Documents | 5 | getDocuments, getDocument, createDocument, updateDocument, deleteDocument |
| Agent actions | 5 | getActions, getAction, getPendingActions, createAction, updateAction |
| OAuth tokens | 3 | getOauthToken, upsertOauthToken, deleteOauthToken |
| Agent metrics | 3 | getAgentMetrics, upsertAgentMetric, incrementMetric |

Note: there is **no storage method for the company-system tables**
(portfolios/companies/departments/roles/workflows/conversations) —
`server/routes/portfolios.ts`, `companies.ts`, `workflows.ts`,
`conversations.ts` query Drizzle directly, bypassing `IStorage`. The
"one interface gates every DB access" claim in the prior map holds only for
the original 15-table universe.

---

## 3. Agent action types — the governed-action grammar

Proposal side (`server/routes/agents.ts`, chat handler ~line 268):
agent replies are scanned with `/\[ACTION:(\w+)\|([^\]]+)\]/g`; matched tags
are stripped from the visible reply and inserted as `agent_actions` rows
(`status=pending`, `requiresApproval=true`, `estimatedTimeSaved` 5 min for
send_email / 3 min otherwise).

Prompt grammar advertised to agents (agents.ts lines 233-235):

```
[ACTION:SEND_EMAIL|to:...|subject:...|body:...]
[ACTION:CREATE_TASK|title:...|description:...|priority:...]
[ACTION:CREATE_DOCUMENT|title:...|content:...]
```

Execution side (`server/services/action-executor.ts`, read in full):

| actionType | Effect | Adapter |
|---|---|---|
| `send_email` | Gmail send (requires to/subject/body; cc/bcc optional) | `server/integrations/gmail.ts` over `oauth_tokens` row (with refresh) |
| `create_task` | `storage.createTask` insert | EOS DB only |
| `create_document` | `storage.createDocument` insert | EOS DB only |
| anything else | `throw` — fail closed | — |

Status lifecycle (zod enum in `shared/schema.ts`):
`pending → approved → executing → completed | failed | rejected`, with
failure below `maxRetries` (default 3) returning the row to **`pending`**
(every retry is human-re-approved). Success increments `agent_metrics`
(`actionsExecuted`, `estimatedTimeSavedMinutes`) via
`storage.incrementMetric`.

UMH side (already merged, for cross-reference):
`projections/eos/integration/tables.py` pins
`EXECUTABLE_ACTION_TYPES = frozenset({"create_task", "create_document"})` —
`send_email` is deliberately **excluded** from UMH-side execution pending
the credential-injection migration.

---

## 4. Schema inventory — three overlapping table universes

### 4.1 `shared/schema.ts` — 35 pgTables (live universe)

Beast blob `ff64b01dbaf0b75525898c4ddd6ca1d6d124133a`, 826 lines.
Grouped by domain:

**Core agent-workforce (15 tables, the original universe):**

| Table | Line | Notes |
|---|---|---|
| `users` | 6 | text PK; **`clerkUserId`** unique (replaced `firebaseUid`); notNull `password` kept for legacy, filled with random bytes |
| `agents` | 36 | text PK; role, `roleLevel` (chief/manager/laborer), department, instructions, brainContent, knowledgeBase, kpis, behavioralStyle, isActive, simulationMode, `parentAgentId` (hierarchy) |
| `tasks` | 78 | text PK; status(todo…)/priority/startDate/dueDate, `agentId`, `assignedById`, `collaboratorIds` (comma-separated), `taskType` (standard/collaboration/delegated), `parentTaskId`, metadata (JSON string) |
| `messages` | 130 | text PK (collides with `shared/models/chat.ts` `messages`, serial PK) |
| `integrations` | 154 | |
| `notifications` | 189 | |
| `ai_messages` | 217 | floating AI assistant thread |
| `crm_contacts` | 237 | |
| `crm_deals` | 267 | **`assignedAgentId`** → agents.id (agent-attributed, ungoverned) |
| `crm_activities` | 297 | **`createdByAgentId`** → agents.id (agent-attributed, ungoverned) |
| `folders` | 335 | |
| `documents` | 354 | |
| `agent_actions` | 376 | full column list in §4.4 |
| `oauth_tokens` | 425 | **plaintext** accessToken/refreshToken columns |
| `agent_metrics` | 451 | per-agent per-day counters |

**Company-system (4 real tables, added by `feature/company-system`):**

| Table | Line | Notes |
|---|---|---|
| `portfolios` | 485 | serial PK; ownerId → users |
| `companies` | 508 | serial PK; ownerUserId, portfolioId, name, type, **stage, offer, targetCustomer, goals, assistantName** (BIS-shaped L3 fields), `orgId` (Clerk org, nullable) |
| `session` | 526 | connect-pg-simple leftover (Clerk owns sessions now) |
| `workflows` | 532 | text PK; companyId; status active/paused |

**Generator scaffold (16 tables, low-value — endpoint names materialized as
tables by the saas-dev backend generator; most have only
name/companyId/timestamps):**
`login` (554), `signup` (572), `forgotPassword` (594), `resetPassword` (610),
`metrics` (628), `recentActivity` (644), `profile` (660), `security` (676),
`config` (694), `register` (710), `logout` (732), `me` (748),
`departments` (764), `roles` (780), `steps` (796), `conversations` (812).
Note `departments`/`roles`/`steps`/`conversations` are real product concepts
but their columns are scaffold-thin (name + companyId only) — the org-chart
and workflow UIs run on these.

### 4.2 `shared/models/chat.ts` — 2 pgTables (COLLISION, unresolved)

Blob `54c94f4de66240941f13d568c78c3db2aec136ef` (identical on Beast and the
`/opt/OS` mirror). Defines `conversations` (serial PK) and `messages`
(serial PK) — **both names collide** with `shared/schema.ts` tables
(`messages` text PK at line 130, `conversations` text PK at line 812).
Known hazard since #181; still present at this head.

### 4.3 `server/generated/schema.ts` — 36 pgTables (DEAD)

Orphaned generator output; nothing imports it since
`registerGeneratedRoutes()` was emptied. Redefines 22 names that also exist
in `shared/schema.ts` (users, notifications, companies, portfolios, tasks,
workflows, messages, login, signup, …) plus 14 unique scaffold names
(`workflow_steps`, `activity_logs`, `user_preferences`,
`capability_manifests`, `kpis`, `onboarding_progress`, `read`, `readAll`,
`preferences`, `activity`, `capabilities`, `onboarding`, `auth`, plus a
second `metrics`). Treat as deletion candidate on the Beast (owner call) —
never as a schema source.

### 4.4 Seam-critical column detail (verified identical Beast↔mirror)

`agent_actions` (line 376): id (text PK), agent_id → agents (cascade),
user_id → users (cascade), action_type, action_name, description,
parameters (jsonb, notNull), status (default 'pending'), requires_approval
(bool default true), approved_by → users, approved_at, executed_at,
completed_at, failed_at, execution_result (jsonb), error_message,
retry_count (default 0), max_retries (default 3), task_id → tasks,
conversation_id, estimated_time_saved (int), priority (default 'medium'),
tags (text[]), metadata (jsonb), created_at, updated_at.

`oauth_tokens` (line 425): id (text PK), user_id → users (cascade),
provider, **access_token (text, notNull, plaintext)**,
**refresh_token (text, plaintext)**, token_type, expires_at, scope,
created_at, updated_at.

`agent_metrics` (line 451): id (text PK), agent_id, user_id, date (text),
messages_sent, messages_received, tasks_completed, actions_executed,
tokens_used, api_cost (text), estimated_time_saved_minutes, created_at,
updated_at.

### 4.5 Mirror drift (measured this packet)

| File | Beast blob @9c8725f | `/opt/OS/data/repos/entrepreneuros` blob | Verdict |
|---|---|---|---|
| `shared/schema.ts` | `ff64b01d` | `d6f2d5d6` | **DRIFTED** — mirror has `firebaseUid` (pre-Clerk) and stops at line 481 (missing all 20 company-system + scaffold tables; 358 diff lines) |
| `server/storage.ts` | `d5d8283a` | `76e75cd6` | **DRIFTED** |
| `shared/models/chat.ts` | `54c94f4d` | `54c94f4d` | identical |

The recorded `mirror_fidelity: "full"`
(`data/umh/projection_reconciliation/projection_source_sync.json`, probe
2026-07-05) is **no longer true at file level** even though the head hash
matches — the mirror was snapshotted before the Clerk/company-system files
landed in the working tree it copied, or copied selectively. Impact
assessment is in the companion doc §5.

---

## 5. AI provider layer — `server/ai/` (7 files)

`index.ts` is a hand-rolled provider gateway: 5 lazily-instantiated services
(`anthropic-service.ts`, `openai-service.ts`, `perplexity-service.ts`,
`xai-service.ts`, `gemini-service.ts`) behind `AIServiceInterface`
(isAvailable / generateResponse / generateImage? / analyzeImage?).
Default provider **anthropic / claude-haiku-4-5** (8192 tokens, temp 0.7).
`generateAgentResponse()` builds the agent persona system prompt from the
`agents` row (name, role, instructions, knowledgeBase). `gateway.ts` +
`server/openai.ts` (misnamed legacy `AgentBrain` module) predate it.
This entire layer is a duplicate of
`adapters/models/model_router.py::call_with_fallback` and is mapped
import-never in the module map.

## 6. Client inventory — live vs dead

Live routed pages (`client/src/App.tsx`, wouter `<Switch>`, 15 routes over
14 page components — the **company-system UI is what actually renders**):

| Route | Component |
|---|---|
| `/` | RootRedirect → `/portfolios` (signed in) or `/login` |
| `/login`, `/signup`, `/forgot-password`, `/reset-password` | Clerk-backed auth pages |
| `/company-setup` | company-setup-page |
| `/settings` | settings-page (inside CompanyGate) |
| `/portfolios` | portfolio-list-page |
| `/portfolios/:portfolioId` | portfolio-detail-page |
| `/company/:companyId` | command-center-page |
| `/company/:companyId/org` | org-chart-page |
| `/company/:companyId/chat` | agent-chat-page |
| `/company/:companyId/workflows` | workflows-page |
| `/company/:companyId/tasks` | task-board-page-new |
| `/*` | not-found-page |

Auth stack: `ClerkProviderWrapper` (`lib/clerk.tsx`) + `ClerkTokenProvider`
injects `getToken` into `lib/queryClient.ts`; `ProtectedRoute` +
`CompanyGate` (`lib/company-guard.tsx`) gate everything after login.
PostHog pageview capture on route change.

Dead page files (18, present but not imported by App.tsx):
admin-dashboard-page, agent-chat (old), agent-os-dashboard,
agent-programming, analytics-page, auth-page, crm-page, dashboard-page,
dashboard (old), documents-page, gpt4o-chat-page, integrations-page,
notifications-page, not-found (old), support-page, task-board-page (old),
tutorials-page, backup/documents-page.tsx.bak.

**Implication:** the server keeps full CRM/documents/notifications/
integrations/analytics APIs alive (roughly half of the 94 endpoints — all 12 CRM, 10 documents, 5 notifications, 6 integrations, 2 analytics, and the ai-assistant trio) with **no live
client page consuming them** — the old dashboard UI that used them is
unrouted. The approval-queue UI consumer of `/api/actions*` on the app side
is `client/src/components/action-approval-panel.tsx` (imported by dead
pages) — meaning at this head, **the UMH cockpit approval queue (#186) is
the only live UI over agent_actions**.

## 7. Integrations, middleware, ops

- `server/integrations/gmail.ts` — Gmail OAuth (env: GOOGLE_CLIENT_ID,
  GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI), token persist/refresh via
  `oauth_tokens`, `sendEmail`/`isConnected`.
- `server/middleware/` — `auth.ts` (attachClerkUser + requireAuth; contains
  a **hardcoded debug log path**
  `C:/Users/antonys beast pc/dev/EntrepreneurOS/auth-debug.log` writing on
  every request — Beast hygiene item), `clerk-org.ts`, `error-handler.ts`,
  `validation.ts`.
- `server/clerkAdmin.ts` — Clerk backend client (CLERK_SECRET_KEY).
- `server/posthog.ts` — posthog-node client.
- Ops: `Dockerfile` + `fly.toml` (fly deploy target), `.env.op.tpl`
  (1Password runtime injection; plaintext .env retired per #178),
  `drizzle.config.ts` (`db:push` via drizzle-kit), `package.json`
  (`rest-express`; dev=tsx, build=vite+esbuild, test=vitest).
- `migrations/` — 6 files inc. `0001_add_clerk_user_id.sql`,
  `0001_add_assistant_name.sql`; `scripts/` — 38 ad-hoc setup/migration/
  pipeline scripts (never to be run from `/opt/OS`).
