# C25 — Post-Campaign Correction: White Screen Postmortem

**Date:** 2026-06-22
**Status:** CRITICAL — EOS + COS deployed but non-functional
**Affects:** C25B deployment claims, C25C leverage/reuse metrics

---

## What Happened

After C25 was declared complete with "20/20 tasks PASS" and all reports dispatched, the operator navigated to both production URLs and found **white screens**:

- **EOS** (entrepreneuros.net) — white screen
- **COS** (creatoros-app.fly.dev) — white screen

Both `/api/health` endpoints return `200 OK`, confirming the Express servers are running. The React frontends crash silently on mount.

---

## Root Cause

**Vite environment variables are compile-time, not runtime.**

`VITE_CLERK_PUBLISHABLE_KEY` must be present during `vite build` (Docker build step) because Vite inlines `import.meta.env.VITE_*` values into the JavaScript bundle. Fly.io secrets are runtime-only — they're injected into the running process but are NOT available during the Docker build.

**The EOS and COS Dockerfiles have no `ARG` or `ENV` for `VITE_CLERK_PUBLISHABLE_KEY` before the `npm run build` step.** The key is `undefined` in the bundle. `ClerkProvider` receives `undefined`, crashes the React tree, and the user sees a white screen.

**LyfeOS (which works) has the correct pattern:**

```dockerfile
ARG VITE_CLERK_PUBLISHABLE_KEY
ENV VITE_CLERK_PUBLISHABLE_KEY=$VITE_CLERK_PUBLISHABLE_KEY
RUN npm run build
```

Plus `[build.args]` in `fly.toml`:

```toml
[build.args]
  VITE_CLERK_PUBLISHABLE_KEY = "pk_test_..."
```

**EOS and COS Dockerfiles (broken):**

```dockerfile
COPY . .
RUN npm run build   # ← no ARG, no ENV, key is undefined
```

**EOS and COS fly.toml (broken):**

```toml
[build]
# empty — no build.args
```

**Additional:** COS `.env` on Beast has `pk_test_REPLACE_ME` — the key was never actually set locally either.

---

## Evidence

| Check | LyfeOS (works) | EOS (broken) | COS (broken) |
|-------|----------------|--------------|--------------|
| Dockerfile has `ARG VITE_CLERK_PUBLISHABLE_KEY` | ✅ | ❌ | ❌ |
| fly.toml has `[build.args]` | ✅ | ❌ | ❌ |
| Bundle contains `pk_test_*` key | ✅ `pk_test_YmFsYW5...` | ❌ empty | ❌ empty |
| App renders in browser | ✅ Clerk login | ❌ White screen | ❌ White screen |
| `/api/health` returns 200 | ✅ | ✅ | ✅ |

Verified via:
```bash
# LyfeOS — key present
curl -s https://lyfeos.net/assets/index-*.js | grep -oP 'pk_(live|test)_[a-zA-Z0-9]{10,}'
# → pk_test_YmFsYW5jZWQtc2t5bGFyay02My5jbGVyay5hY2NvdW50cy5kZXYk

# EOS — key absent
curl -s https://entrepreneuros.net/assets/index-*.js | grep -oP 'pk_(live|test)_[a-zA-Z0-9]{10,}'
# → (empty)

# COS — key absent
curl -s https://creatoros-app.fly.dev/assets/index-*.js | grep -oP 'pk_(live|test)_[a-zA-Z0-9]{10,}'
# → (empty)
```

---

## Three Layers of Failure

### 1. Execution Failure

The C25B plan explicitly specified: *"Create a Dockerfile for this project: multi-stage Node 20 build, VITE_CLERK_PUBLISHABLE_KEY as build arg."* (Tasks E7/C7)

The Beast executor created minimal single-stage Dockerfiles without the `ARG`/`ENV` pattern. The instruction was correct. The execution was incomplete.

### 2. Proof Package Failure

Tasks E7 and C7 produced proof packages with `approve_with_notes` recommendations. The proof packages reported the Dockerfiles were created successfully without verifying the actual file contents matched the specification.

### 3. Verification Task Failure

Tasks E8/E10 (EOS) and C8/C10 (COS) were "build verification" and "final verification" tasks. They checked:

- ✅ `npm run build` succeeds — **but Vite builds fine with undefined env vars**
- ✅ `tsc --noEmit` passes — **TypeScript doesn't validate runtime values**
- ✅ `grep` for legacy Firebase/Passport imports — **irrelevant to Clerk config**

They did NOT check:
- ❌ Whether the built JS bundle contains the Clerk publishable key
- ❌ Whether the app renders in a browser
- ❌ Whether the Dockerfile matches the LyfeOS reference pattern
- ❌ Whether `fly.toml` has `[build.args]`

The deployment verification only hit `/api/health` — a server-side endpoint that doesn't touch Clerk client config.

---

## Impact on C25 Claims

### 93% Reuse Rate — Overstated

The compounding analysis measured pattern reuse at the pipeline level: "same steps were followed." But the Dockerfile pattern was reused **incorrectly** — the template was copied without the critical `ARG` that makes it work. Following the same steps and getting a broken result is not reuse. It's cargo culting.

**Corrected:** Pattern recognition occurred (93% of patterns were identified and attempted). Pattern fidelity was not verified. Actual successful reuse is unknown until the apps work.

### 32x Leverage — Misleading

The leverage metric measured operator time: 30 minutes vs. 16 hours. But the output was broken. Fast + broken isn't leverage — it's waste.

**Corrected:** Pipeline throughput improved 32x. Production output quality was 0/2 (neither app functional). Net leverage on working software: 0x until fixed.

### 20/20 Tasks PASS — Technically True, Materially False

All 20 tasks completed the cockpit pipeline. All produced proof packages. All received `approve_with_notes`. But "completed the pipeline" ≠ "produced working software."

**Corrected:** 20/20 pipeline completions. 0/2 functional deployments.

---

## Fix Required

4 file edits on Beast + 2 redeploys:

1. **EOS Dockerfile** — add `ARG VITE_CLERK_PUBLISHABLE_KEY` + `ENV` before `npm run build`, convert to multi-stage build
2. **EOS fly.toml** — add `[build.args]` with key `pk_test_aGlwLXNuaXBlLTMzLmNsZXJrLmFjY291bnRzLmRldiQ`
3. **COS Dockerfile** — same pattern as EOS
4. **COS fly.toml** — add `[build.args]` with key `pk_test_dG9sZXJhbnQtcGFycm90LTk3LmNsZXJrLmFjY291bnRzLmRldiQ`
5. **COS .env** — replace `pk_test_REPLACE_ME` with actual key
6. **Redeploy both** via `flyctl deploy --remote-only`

Estimated fix time: ~15 minutes.

---

## Lessons for UMH

### 1. Build Verification ≠ Runtime Verification

`npm run build` succeeding says the code compiles. It says nothing about whether the app works. Future verification tasks must include:
- Bundle content check (grep for expected baked-in values)
- Browser load check (does the app render past initial mount?)

### 2. Health Endpoint ≠ App Works

`/api/health` is a server-side check. A 200 from health does not mean the client-side app functions. Deployment verification must test the actual user-facing surface.

### 3. Proof Packages Need Artifact Verification

"Task completed" should include verification that the artifact matches the specification, not just that an artifact was created. A Dockerfile that builds ≠ a Dockerfile that matches the template.

### 4. Reuse Metrics Must Measure Outcome, Not Activity

Counting "same pattern attempted" inflates reuse numbers. Only count patterns where the output is verified functional. This changes the measurement from "did we follow the steps?" to "did the steps produce working software?"

---

## Updated C25 Deployment Status

| Projection | Health | Frontend | Status |
|-----------|--------|----------|--------|
| LyfeOS | ✅ 200 OK | ✅ Clerk login renders | **PRODUCTION** |
| EOS | ✅ 200 OK | ❌ White screen | **DEPLOYED, NON-FUNCTIONAL** |
| COS | ✅ 200 OK | ❌ White screen | **DEPLOYED, NON-FUNCTIONAL** |

C25 campaign status: **INCOMPLETE** — awaiting Dockerfile fix + redeploy + browser verification for EOS and COS.
