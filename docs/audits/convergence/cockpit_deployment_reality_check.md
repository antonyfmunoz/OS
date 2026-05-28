# Cockpit Deployment Reality Check

**Date:** 2026-05-28
**Auditor:** Developer Agent (background session)
**Status:** ROOT CAUSE IDENTIFIED — FIX APPLIED

---

## Root Cause

**Phase 1–4 organism code was never merged to main.** 8 commits exist
only on the worktree branch `worktree-anti-divergence-gate`. The
`os-operator` container bind-mounts `/opt/OS` (main branch). Main
branch stopped at `88722547` (P1-P5 production hardening). All organism
subsystems, cockpit API routes, and anti-divergence gates are
worktree-only.

### Secondary issues found

1. **`import os` bug in `services/operator_api.py`** — line 6 uses
   `os.environ.get()` before `os` is imported (line 12). The container
   was started 22 hours ago from a prior version; a restart would have
   crashed. **Fixed in main repo.**

2. **Missing `/execution/*` routes** — The frontend `ExecutionPanel`
   calls 7 execution routes (`/execution/status`, `/execution/log`,
   `/execution/authority`, `/execution/start`, `/execution/stop`,
   `/execution/pause`, `/execution/resume`). These never existed in the
   Python cockpit router (`transports/api/cockpit.py`). They only
   existed in `saas/api/routes/execution.ts` (TypeScript EOS backend,
   not running). **Added to worktree cockpit.py as stub endpoints.**

3. **Organism daemon not running** — `_get_organism()` returns `None`
   because the daemon lifecycle (`transports/api/app.py`) is not wired
   into `operator_api.py`. All organism routes return empty/false data.

---

## 1. DNS & Hosting

| Item | Value |
|------|-------|
| Domain | universalmetaharness.tech |
| DNS target | 66.241.125.191 |
| Fly.io app | umh-cockpit |
| Primary region | sjc |
| Server header | `Fly/b59e3505 (2026-05-27)` |

## 2. Frontend Bundle

| Item | Value |
|------|-------|
| HTML last-modified | Wed, 27 May 2026 02:11:56 GMT |
| JS bundle | `/assets/index-DQxsZjx-.js` |
| CSS bundle | `/assets/index-BCjaLMLN.css` |
| Contains organism routes | YES — `/organism/agents`, `/organism/control`, etc. |
| Contains execution routes | YES — `/execution/status`, `/execution/start`, etc. |
| API base | `/api/umh` (relative, proxied by nginx) |

The frontend was built from the worktree branch and deployed to Fly.io.
It calls routes that exist in the worktree's cockpit.py but NOT in main's.

## 3. Architecture

```
Browser → Fly.io (nginx:8080)
  → /api/*  → socat:8091 → Tailscale tunnel → VPS 100.77.233.50:8091
  → /ws     → same tunnel
  → /*      → static files (dist-web)
```

- `start.sh` runs: nginx → tailscaled → tailscale up → socat bridge
- VPS `os-operator` container: `python3 -m uvicorn services.operator_api:app --port 8091`
- Container bind-mounts `/opt/OS` → `/app`
- `operator_api.py` imports `transports.api.cockpit.router` at line 572

## 4. Backend API (VPS port 8091)

### Working endpoints (in main repo's cockpit.py)

| Endpoint | Response |
|----------|----------|
| `/api/umh/pulse` | ✅ Real data (uptime, CPU, memory, disk) |
| `/api/umh/organism/status` | ✅ `{"running":false,"agents":[]}` |
| `/api/umh/organism/agents` | ✅ `[]` |
| `/api/umh/organism/deliverables` | ✅ `[]` |
| `/api/umh/agents` | ✅ Lists agent .md files |
| `/api/umh/tasks` | ✅ Lists traces |
| `/api/umh/models` | ✅ Model routing config |
| `/api/umh/infra` | ✅ Compute/network/service nodes |
| `/api/umh/mesh/nodes` | ✅ Tailscale peers |

### 404 endpoints (only in worktree cockpit.py, never merged)

| Endpoint | Why missing |
|----------|------------|
| `/api/umh/organism/snapshot` | Added in commit c76c28bf (Phase 4), worktree only |
| `/api/umh/organism/topology` | Same |
| `/api/umh/organism/economy` | Added in commit 251747dc (Phase 3), worktree only |
| `/api/umh/organism/recursion` | Same |
| `/api/umh/organism/advisors` | Same |
| `/api/umh/organism/leverage` | Added in commit b2943c2a (Phase 2), worktree only |
| `/api/umh/execution/status` | Never existed in Python — only in saas/api TS |
| `/api/umh/execution/log` | Same |

## 5. Unmerged Commits (worktree → main)

```
f3ea10c2 feat(organism): continuous objective queue
2ce9401d feat(organism): autonomous tick engine
af3c4838 feat(organism): unified event spine
c76c28bf feat: phase 4 — cockpit operationalization, organism API bridge
251747dc feat: organism phase 3 — governed recursive execution economy
b2943c2a feat: organism phase 2 — integrated DEX orchestration runtime
09cb937f feat: persistent distributed organism runtime — 5 new subsystems
14076692 feat: anti-divergence gate — permanent type coherence enforcement
```

## 6. Auth / CORS / Proxy

| Check | Result |
|-------|--------|
| Clerk auth | Publishable key baked into Fly build args |
| API auth | `X-API-Key` header, defaults to `dev-key-change-me` (dev mode pass-through) |
| CORS | Configured for localhost:5173/5174, NOT for universalmetaharness.tech |
| Tailscale tunnel | Working (VPS reachable from Fly container) |
| 401/403 errors | None — dev-key bypass active |
| 502 errors | None — socat bridge healthy |

**CORS note:** CORS is configured for local dev origins only. The Fly.io
deployment works because nginx proxies `/api/` as same-origin — the
browser never makes a cross-origin request.

## 7. Fix Applied

1. **`import os` bug fixed** in main repo `services/operator_api.py`
   (moved `import os` before `sys.path.insert` that uses `os.environ`)

2. **Execution routes added** to worktree `transports/api/cockpit.py`
   (`/execution/status`, `/execution/log`, `/execution/authority`,
   `/execution/start`, `/execution/stop`, `/execution/pause`,
   `/execution/resume`) as stub endpoints matching the TypeScript
   saas/api behavior

## 8. Remaining Blocker

**The worktree branch must be merged to main.** Until then:
- Container runs against main (no Phase 1-4 routes)
- Container restart will work now (import bug fixed) but still won't have organism routes

### To deploy Phase 4 to production:

```bash
# 1. Merge worktree branch to main
cd /opt/OS
git merge worktree-anti-divergence-gate

# 2. Restart container (picks up new code via bind mount)
docker restart os-operator

# 3. Verify routes
curl -s http://localhost:8091/api/umh/organism/snapshot
curl -s http://localhost:8091/api/umh/execution/status

# 4. Optionally rebuild Fly.io image (if frontend needs update)
cd cockpit && fly deploy
```

### Organism daemon still won't show data until:
- `_get_organism()` is wired to actually start the organism daemon
- Currently it tries to import from `transports.api.app._organism` which
  is only set when `transports/api/app.py` runs as the entrypoint (not
  when `services/operator_api.py` is the entrypoint)

## 9. Success Criteria Assessment

| Criterion | Status |
|-----------|--------|
| universalmetaharness.tech displays Phase 4 organism data | ❌ BLOCKED — merge required |
| Root cause proven | ✅ 8 commits never merged to main |
| Exact deployed frontend commit/build | ✅ Built 2026-05-27T02:11:56Z from worktree branch |
| Exact backend being hit | ✅ os-operator container, main branch code via bind mount |
| Endpoint results documented | ✅ See section 4 |
| Fix applied | ✅ Import bug fixed, execution routes added |
| Remaining blockers documented | ✅ Merge + container restart + daemon wiring |
