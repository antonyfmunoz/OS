# EOS App-Body → Substrate Module Map

**Work packet:** WP-P4-EOS-APP-MODULE-MAP-001
**Date:** 2026-07-06
**Source truth:** EntrepreneurOS on the Beast — branch `feature/company-system`, head `9c8725f`, probe 2026-07-05, `beast_verification=VERIFIED`, `source_build_safe=True`
**Machine-readable map:** `data/umh/projection_reconciliation/eos_app_module_map.json`
**Accessor:** `projections/eos/integration/module_map.py` (`load_eos_app_module_map()`, `build_mappable_modules()`)

This is a read-first map. No code was copied, no schemas migrated, no Beast
writes performed. It answers one question: **what does EntrepreneurOS actually
contain, and where does each piece belong in UMH terms** — before anything is
imported or built.

CreatorOS and LyfeOS are excluded (both `source_dirty`, not build-safe).
`data/repos/entrepreneuros` was used as the read-only inspection mirror
(`mirror_fidelity=full` per the #179 harness) — it is **not** source authority.

---

## 1. What exists on the Beast

A single Vite+Express monorepo (`rest-express` in package.json), Replit-origin,
141 source/config files:

| Area | Files | Content |
|---|---|---|
| `server/` | 21 | Express entrypoint (:5000), monolithic `routes.ts` (~2,360 lines, ~60 endpoints), passport+Firebase auth, Drizzle storage layer, 5-provider AI router, Gmail OAuth, approval-gated action executor, Replit leftovers |
| `client/` | 97 | React 18 + wouter + TanStack Query; 17 pages (dashboard, task board, agent chat/programming, CRM, documents, analytics, integrations, notifications, settings, auth…), 21 app components, 48 shadcn/ui components |
| `shared/` | 2 | `schema.ts` — 15 Drizzle tables (the one file already mirrored to the VPS) + `models/chat.ts` (Replit chat schema, **collides** with the main `messages` table) |
| `scripts/` | 12 | Ad-hoc table setup/migration scripts (pre-drizzle-kit era) |
| root | 14 | Build config, Replit artifacts |

The product is an **agent-workforce app**: users create AI agents (chief/manager/
laborer hierarchy, departments), chat with them, assign tasks, agents propose
actions (send email / create task / create document) that the user approves
before execution, with per-agent metrics, CRM, and documents around it.

**Domain schema (15 tables):** users, agents, tasks, messages, integrations,
notifications, ai_messages, crm_contacts, crm_deals, crm_activities, folders,
documents, agent_actions, oauth_tokens, agent_metrics.

**Env keys (names only — values in 1Password vault `EntrepreneurOS`, loaded via
`op run --env-file=.env.op.tpl`; plaintext .env retired):**
server — DATABASE_URL, SESSION_SECRET, NODE_ENV, AI_INTEGRATIONS_ANTHROPIC_API_KEY,
AI_INTEGRATIONS_ANTHROPIC_BASE_URL, OPENAI_API_KEY, PERPLEXITY_API_KEY,
XAI_API_KEY, GEMINI_API_KEY, FIREBASE_SERVICE_ACCOUNT_KEY, FIREBASE_CLIENT_EMAIL,
FIREBASE_PRIVATE_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI;
client — VITE_FIREBASE_API_KEY, VITE_FIREBASE_AUTH_DOMAIN, VITE_FIREBASE_PROJECT_ID,
VITE_FIREBASE_APP_ID.

---

## 2. What maps to substrate

These EOS mechanisms are hand-rolled versions of things UMH already owns.
Import the **semantics**, never the code:

- **`agent_actions` + `action-executor.ts`** — the strongest match in the whole
  app. It is a homemade `governed_mutation`: propose → approve → execute →
  record result, with retries and status lifecycle. Maps directly onto
  `governed_mutation → MutationRouter → GovernedExecutionSpine` with authority-
  engine approval gates. This is the natural first semantic import.
- **`server/ai/` provider router** — duplicate of
  `adapters/models/model_router.py::call_with_fallback`. When EOS runs over the
  substrate, all LLM calls route through the canonical router; the app-local
  registry exists only while EOS runs standalone on the Beast.
- **agents / tasks / messages** — EOS "agents" are L3 vocabulary over UMH
  organism roles; tasks carry WorkPacket semantics; agent chat/execution
  belongs on the canonical spine.

## 3. What maps to projections/eos

- **`shared/schema.ts` domain model** — CRM (contacts/deals/activities),
  documents/folders, agent metrics, notifications: EOS L3 domain objects.
  Already mirrored to `/opt/OS` (node-role discipline keeps exactly this file).
- **`server/storage.ts` IStorage seam** — one interface gates every DB access
  in the app. This is where a governed adapter attaches later: reads become
  projection read surfaces, writes become governed mutations.
- **Read surfaces** — future `/eos/*` endpoints (tasks, CRM, metrics) follow
  the projection read-surface discipline: projection-owned accessor + thin
  transport wrapper, like `eos_readiness()`.

## 4. What maps to transports/cockpit

- Nothing as file copies. Overlapping operator views (agents, tasks, analytics,
  notifications) may later be re-expressed as cockpit projection views backed
  by `/eos/*` read surfaces. The EOS client remains the customer-facing product
  UI and stays on the Beast; the cockpit remains the UMH operator surface.

## 5. What should NOT be copied

- **Any app code at all, in this phase.** The packet sanctions mapping only.
- `server/ai/` (duplicate router), `server/openai.ts` (misnamed legacy fallback).
- `server/replit_integrations/`, `.replit`, `replit.nix`, `replit.md`,
  root `llmApi.ts` — Replit-hosting dead weight.
- `shared/models/chat.ts` — defines a **second `messages` pgTable** (serial PK)
  colliding with `shared/schema.ts` `messages` (text PK). Type-coherence hazard;
  resolve on the Beast first.
- `client/src/components/ui/` — regenerable shadcn kit.
- `scripts/` — ad-hoc schema mutators; never run from `/opt/OS`.
- Secrets, `.env*`, session material — nothing secret appears in the map
  (key names only), and nothing secret ever lands in this repo.
- `/api/keys/save` semantics — the route mutates `process.env` from an HTTP
  body; the UMH replacement is the 1Password credential-injection law.

## 6. What requires owner approval before mutation

1. Any schema migration / `drizzle-kit push` against the EOS Neon database
   (CRITICAL risk class — row counts first).
2. **Auth model decision:** EOS uses passport-local + Firebase/Google; UMH
   cockpit is Clerk-locked. Must be reconciled before any user-facing build-out.
3. Any copy of Beast app-body code into `/opt/OS` (VPS node role keeps
   `shared/schema.ts` only).
4. Resolution of the `messages` table collision (`shared/models/chat.ts`).
5. Deleting Replit artifacts on the Beast.
6. Any write to the Beast working tree (branch `feature/company-system`,
   head `9c8725f`).

---

## Build-safety gate (enforced in code)

`build_mappable_modules()` returns rows **only** while
`eos_readiness()['source_build_safe']` is True *and* the map's recorded head
matches the live VERIFIED Beast head. If the Beast drifts (dirty tree, stale
mirror, lost backup, unverified probe), the mappable set collapses to `[]` —
a build orchestrator can never plan a slice from stale truth.

Regression tests: `tests/test_eos_app_module_map.py`.

## Next-packet candidates (evidence-based)

1. **One governed read slice:** a single `/eos/*` read surface backed by a real
   EOS table (tasks or crm_contacts), discipline-conformant, read-only.
2. **Action-executor semantics import:** express the `agent_actions` approval
   flow as governed_mutation contracts (no code copy).
3. **Beast hygiene packet (owner-approved):** retire Replit artifacts, resolve
   the messages-table collision.
