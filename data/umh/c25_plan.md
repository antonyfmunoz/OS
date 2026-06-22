# Campaign 25 — Parallel Projection Production Trial

## Context

C24 proved one projection (LyfeOS) can be produced through governed sessions on Beast, but bypassed the Meta IDE pipeline with direct dispatch scripts. C25 runs the full loop as designed: operator types engineering intent in cockpit chat → system classifies → plans → operator approves → dispatches to Beast → proof assembled → operator reviews → next task.

**Pipeline audit (2026-06-22)**: All 6 stages of the Meta IDE loop work individually. Method name bug fixed, planner singleton fixed, fully deterministic (no LLM hangs). Never tested end-to-end through cockpit UI — that's the first thing to verify.

**Ground truth from audits:**
- **EOS**: Firebase Auth → Clerk. Beast at `C:\dev\dev\EntrepreneurOS`. 6 Firebase files. No deploy infra.
- **COS**: Broken Passport.js → Clerk. Beast at `C:\dev\dev\CreatorOS`. No Firebase. God files (53KB, 105KB). No deploy infra.
- **Asymmetry**: EOS = Firebase→Clerk (identical to LyfeOS). COS = Passport→Clerk (different removal, same Clerk target).

---

## Execution Model

**Everything goes through the cockpit chat.** The operator (or this autonomous session acting as operator) pastes engineering intents into the Meta IDE conversation interface. The system:

1. Classifies intent as `ENGINEERING_BUILD` via `command_router.py`
2. Routes to `_handle_engineering_build()` in `advisor_conversation.py`
3. Creates plan via `engineering_planner.create_plan()` (deterministic, no LLM)
4. Returns plan with approve/reject buttons in chat response
5. Operator approves → `POST /engineering/plans/{plan_id}/approve`
6. Operator dispatches → `POST /engineering/plans/{plan_id}/dispatch`
7. Beast executes Claude Code session in project directory
8. Proof assembled via `review_package_builder.py`
9. Review presented → operator approves/rejects
10. Next intent

**This session orchestrates by calling the cockpit API endpoints directly** — same as what the cockpit UI does when an operator clicks buttons. The API is the interface, not scripts.

---

## Domains

EOS: `eos.universalmetaharness.tech` (CNAME → `eos-app.fly.dev`)
COS: `creatoros.universalmetaharness.tech` (CNAME → `creatoros-app.fly.dev`)

---

## Phase 0 — Pipeline Verification (gate)

Before any C25 work, verify the Meta IDE loop end-to-end with a trivial task:

1. **Send engineering intent** via `POST /api/umh/advisor/converse`:
   `"Create a health check endpoint at /api/health in LyfeOS that returns {status: ok}"`
2. **Verify** response contains a plan with approve action
3. **Approve** the plan via `POST /engineering/plans/{plan_id}/approve`
4. **Dispatch** via `POST /engineering/plans/{plan_id}/dispatch` with `node_id: windows-desktop`, `cwd: C:\dev\dev\LYFEOS`
5. **Verify** Beast executes and returns result
6. **Check** proof appears in `GET /engineering/reviews` or `GET /ide/reviews`
7. **Approve** review via `POST /engineering/reviews/{proof_id}/approve`

If any step fails → fix it before proceeding. This is the quality gate.

**Key API details from audit:**
- Advisor converse: `POST /api/umh/advisor/converse` → `AdvisorConversation.converse()`
- Plan creation: `POST /engineering/plan` or `POST /ide/plan`
- Plan approval: `POST /engineering/plans/{plan_id}/approve`
- Plan dispatch: `POST /engineering/plans/{plan_id}/dispatch` (returns 202, background task)
- Reviews list: `GET /ide/reviews` (merges both review sources)
- Review approve: `POST /ide/reviews/{review_id}/approve`
- Mesh dispatch: `_mesh_dispatch.py` → `POST http://localhost:8095/dispatch`
- Beast allowlist: `windows-desktop` only, cwd must start with `C:\dev\dev\`

---

## Phase 1 — Pre-flight Setup

1. Create 2 Clerk applications (EntrepreneurOS, CreatorOS) — **needs operator input once**
2. Store Clerk keys in 1Password vault `UMH-Production`
3. Create 2 PostHog projects
4. Create Fly.io apps: `eos-app`, `creatoros-app`
5. Set Fly.io secrets (CLERK_SECRET_KEY, DATABASE_URL)
6. Create `data/umh/c25_metrics.json`

---

## Phase 2 — Parallel Auth Migration via Cockpit Chat

Each intent is sent through the Meta IDE pipeline. The system plans it, operator approves, Beast executes, proof reviewed.

### EOS Intents (paste into cockpit chat, one at a time)

| # | Intent to send | Reuse |
|---|---------------|-------|
| E1 | "Audit all Firebase and Passport auth files in this project. Map every import, every usage, every env var. List every file that needs modification for a Clerk migration." | MODIFIED |
| E2 | "Install @clerk/express and @clerk/clerk-react. Create server/clerkAdmin.ts that initializes createClerkClient with CLERK_SECRET_KEY from env. Create client/src/lib/clerk.ts that exports ClerkProvider setup." | DIRECT |
| E3 | "Rewrite server/auth.ts: remove all Passport and Firebase auth. Replace with Clerk middleware — clerkMiddleware(), requireAuth(), getAuth(). Rewrite the /api/user endpoint to use Clerk session." | MODIFIED |
| E4 | "Rewrite client/src/hooks/use-auth.tsx: remove all Firebase imports (signInWithPopup, MFA, onAuthStateChanged). Replace with Clerk hooks (useUser, useAuth, useClerk). Add ClerkProvider to App.tsx. Update protected-route.tsx." | MODIFIED |
| E5 | "Delete server/firebase.ts and client/src/lib/firebase.ts. Run npm uninstall firebase firebase-admin. Remove all VITE_FIREBASE_* references from env files and code." | DIRECT |
| E6 | "Add a clerkId text column to the users table in shared/schema.ts. Update server/storage.ts to use clerkId instead of firebaseUid. Create a Drizzle migration." | MODIFIED |
| E7 | "Create a Dockerfile for this project: multi-stage Node 20 build, VITE_CLERK_PUBLISHABLE_KEY as build arg, npm ci --omit=dev in production stage. Create fly.toml for app name eos-app, region sjc, shared-cpu-1x, 512MB, internal port 8080, health check at /api/health. Add /api/health endpoint if it doesn't exist." | DIRECT |
| E8 | "Run npm run build. Fix any TypeScript errors. Run npx tsc --noEmit. Verify zero imports from firebase.ts, firebaseAuth.ts, or firebase-admin remain. Commit all fixes." | DIRECT |
| E9 | "Install posthog-js. Add PostHog client-side initialization in the app entry point. Add server-side PostHog events for: user_signed_up, user_signed_in, user_signed_out, and core feature usage." | DIRECT |
| E10 | "Final verification: run npm run build, npx tsc --noEmit. Grep the entire codebase for any remaining firebase or passport imports. Report the build output size and any warnings." | DIRECT |

### COS Intents (paste into cockpit chat, one at a time)

| # | Intent to send | Reuse |
|---|---------------|-------|
| C1 | "Audit all Passport.js auth files in this project. Map the session middleware, local strategy, serialize/deserialize, comparePasswords function. Confirm whether comparePasswords is broken (returns true for all). List every file that needs modification for a Clerk migration." | NET NEW |
| C2 | "Install @clerk/express and @clerk/clerk-react. Create server/clerkAdmin.ts that initializes createClerkClient with CLERK_SECRET_KEY from env. Create client/src/lib/clerk.ts that exports ClerkProvider setup." | DIRECT |
| C3 | "Remove all Passport.js auth from the server: delete the local strategy, remove session middleware, remove serialize/deserialize, remove the broken comparePasswords function. Add Clerk middleware — clerkMiddleware(), requireAuth(), getAuth(). Rewrite auth-related routes to use Clerk." | NET NEW |
| C4 | "Remove Passport login/register forms from the client. Add ClerkProvider to App.tsx or main.tsx. Replace any auth state management with Clerk hooks (useUser, useAuth). Update protected routes." | MODIFIED |
| C5 | "Run npm uninstall passport passport-local express-session connect-pg-simple memorystore. Remove @types/passport and @types/express-session if present. Clean package.json of all session/passport references." | NET NEW |
| C6 | "Add a clerkId text column to the users table in shared/schema.ts. Remove the password column. Update storage.ts user queries to use clerkId. Create a Drizzle migration." | MODIFIED |
| C7 | "Create a Dockerfile for this project: multi-stage Node 20 build, VITE_CLERK_PUBLISHABLE_KEY as build arg, npm ci --omit=dev in production stage. Create fly.toml for app name creatoros-app, region sjc, shared-cpu-1x, 512MB, internal port 8080, health check at /api/health. Add /api/health endpoint if it doesn't exist." | DIRECT |
| C8 | "Run npm run build. Fix any TypeScript errors. Run npx tsc --noEmit. Verify zero passport or express-session imports remain. Commit all fixes." | DIRECT |
| C9 | "Install posthog-js. Add PostHog client-side initialization. Add server-side events for: user_signed_up, user_signed_in, user_signed_out, and core feature usage." | DIRECT |
| C10 | "Final verification: run npm run build, npx tsc --noEmit. Grep for any remaining passport, express-session, or comparePasswords references. Report build output and warnings." | DIRECT |

### Dispatch Strategy

Staggered parallel through the pipeline — send E(N) and C(N-1) intents through the cockpit API simultaneously when possible:

```
T1:  E1
T2:  E2 + C1
T3:  E3 + C2
...
T10: E10 + C9
T11: C10
```

If the pipeline can't handle parallel plans for different projects, fall back to alternating: E1, C1, E2, C2...

### Reuse Projections

| Category | EOS | COS | Total |
|----------|-----|-----|-------|
| DIRECT | 6 | 5 | 11 (55%) |
| MODIFIED | 4 | 2 | 6 (30%) |
| NET NEW | 0 | 3 | 3 (15%) |
| **Total** | 10 | 10 | **20** |

**Projected reuse: 85%**

---

## Phase 3 — Deploy Both Apps

After all 20 intents processed and reviewed:

1. Send deploy intent for EOS: "Deploy this project to Fly.io using flyctl deploy --remote-only. The Fly API token is set as FLY_API_TOKEN env var. Report full output."
2. Send deploy intent for COS: same pattern
3. Verify health checks: `curl https://eos-app.fly.dev/api/health`, `curl https://creatoros-app.fly.dev/api/health`

---

## Phase 4 — DNS + TLS

Add 2 CNAME records on Squarespace (via Playwright on Beast or operator manual):
- `eos` → `eos-app.fly.dev`
- `creatoros` → `creatoros-app.fly.dev`

Create TLS certs: `flyctl certs create eos.universalmetaharness.tech`, `flyctl certs create creatoros.universalmetaharness.tech`

Verify with `dig` and `curl -sI`.

---

## Phase 5 — Production Verification

- Both URLs load with valid TLS
- Clerk auth flow works (register, login, logout)
- PostHog receiving events
- Health checks passing
- Zero Firebase/Passport dependencies remaining

---

## Phase 6 — Measurement & Reports

Generate all deliverables from session data:

1. `C25_EOS_AUDIT.md` — from E1 results
2. `C25_COS_AUDIT.md` — from C1 results
3. `C25_CAPABILITY_REUSE_REPORT.md` — reuse % with evidence per session
4. `C25_PARALLEL_PRODUCTION_REPORT.md` — parallelization metrics
5. `C25_OPERATOR_LEVERAGE_REPORT.md` — touches per projection vs C24
6. `C25_FINAL_VERDICT.md` — answers all 10 hypothesis questions with numerical evidence

Dispatch all to Discord Founders Office via ReportDispatcher.

---

## Risk Register

| Risk | Mitigation |
|------|------------|
| Pipeline verification (Phase 0) fails | Fix broken stage before proceeding — this is the gate |
| Beast can't handle parallel dispatches | Fall back to alternating E/C sessions |
| COS god files exceed Claude context | Scope C3 intent to auth routes only, not full file rewrite |
| Plans lost on process restart | Keep this session alive through the entire campaign; plans are in-memory |
| Clerk apps don't exist | Single operator input at Phase 1, then fully autonomous |

---

## Done Criteria

1. `eos.universalmetaharness.tech` loads with Clerk auth
2. `creatoros.universalmetaharness.tech` loads with Clerk auth
3. Zero Firebase deps in EOS, zero Passport deps in either
4. Both PostHog projects receiving events
5. All secrets in 1Password
6. `C25_FINAL_VERDICT.md` answers all 10 questions with evidence
7. All 6 reports dispatched to Discord
