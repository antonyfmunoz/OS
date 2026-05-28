# Phase 6.9 — Cockpit Panel Truth Matrix

Date: 2026-05-28
Build: `index-DakA7xec.js` / `index-DCEn9RGg.css`
Backend: os-operator on VPS (Caddy :8088 → :8091)
Browser: Playwright Chromium (headless)

## Panel Status Matrix

| # | Panel | Route ID | Status | Live Data | Endpoint(s) | Issue | Fix Applied | Remaining Blocker |
|---|-------|----------|--------|-----------|-------------|-------|-------------|-------------------|
| 1 | Command Center | dashboard | **PASS** | Yes | /pulse, /approvals, /models, /mesh/nodes, /infra, /tasks, /organism/* | — | — | — |
| 2 | Agents | agents | **PASS** | Yes | /agents (Neon) | — | — | — |
| 3 | Tasks | tasks | **PASS** | Yes | /tasks | "Invalid Date" on some tasks with missing timestamps | — | Minor: date fallback |
| 4 | Workflows | workflows | **PASS** | Yes | /organism/spine/*, /organism/workloads | — | — | — |
| 5 | Activity | activity | **PASS** | Yes | /organism/events?limit=50 | — | — | — |
| 6 | Approvals | approvals | **PASS** | Yes | /approvals, /organism/spine-guard, /organism/autonomous-gateway | — | — | — |
| 7 | Organism | organism | **PASS** | Yes | /organism/spine, /organism/leverage, /organism/bottlenecks, /organism/mutations, /organism/status, /organism/workloads, /organism/execution-mode | Crashed: `Object.values(undefined)` — API returns `specs` not `mutations` | Fixed: handle both field names | — |
| 8 | Execution | execution | **PASS** | Yes | /organism/spine/*, /organism/journal/*, /organism/leverage, /organism/execution-mode, /organism/workloads | — | — | — |
| 9 | Tracking | tracking | **PARTIAL** | No | — | Intentional: "Not wired — See Knowledge panel" | — | Pending tracking backend |
| 10 | Infrastructure | infrastructure | **PASS** | Yes | /infra, /mesh/nodes, /models, /organism/workloads | Build hash in footer | — | — |
| 11 | Portfolio | portfolio | **PASS** | Yes | /ventures (BIS) | — | — | — |
| 12 | Company | company | **PARTIAL** | No | /entities/companies, /entities/departments, /entities/roles, /entities/workflows | 404 on /entities/workflows (endpoint missing) | — | Endpoint not implemented; panel shows correct empty state |
| 13 | Knowledge | knowledge | **PASS** | Yes | /knowledge/observations, /knowledge/memory, /knowledge/skills | — | — | — |
| 14 | Analytics | analytics | **PASS** | Yes | /analytics (computed) | — | — | — |
| 15 | Skills | skills | **PASS** | Yes | /skills (Neon) | — | — | — |
| 16 | IDE (Editor) | editor | **PARTIAL** | No | — | Intentional: layout placeholder, file tree not loaded, terminal pending Phase 5 | — | xterm.js + node-pty integration |
| 17 | Experiments | experiments | **PARTIAL** | No | — | Intentional: "Not wired — Pending experiment framework" | — | Experiment framework not built |
| 18 | Messages (Comms) | comms | **PARTIAL** | No | — | Intentional: "Not wired — Pending transport integration" | — | Transport integration not built |
| 19 | Profile | profile | **PARTIAL** | No | — | Intentional: "Not wired — Pending identity integration" | — | Identity integration not built |
| 20 | Settings | settings | **PASS** | Yes | /settings, /governance | Crashed: `.map()` on undefined when governance API returns error object | Fixed: guard against missing arrays + validate API response shape | — |

## Summary

| Category | Count | Panels |
|----------|-------|--------|
| PASS (live data) | 13 | Dashboard, Agents, Tasks, Workflows, Activity, Approvals, Organism, Execution, Infrastructure, Portfolio, Analytics, Skills, Settings |
| PARTIAL (intentional placeholder) | 5 | Tracking, Company, IDE, Experiments, Messages, Profile |
| FAIL (crash/broken) | 0 | — (both were fixed: Organism, Settings) |

## Defects Fixed

1. **Organism panel crash** — `Object.values(mutations.mutations)` failed because API returns `{specs: {...}}` not `{mutations: {...}}`. Fixed in `OrganismPanel.tsx` and `organismStore.ts` to handle both field names.

2. **Settings panel crash** — `governance.safe_roots.map(...)` crashed when `/governance` API returned `{error: "policy engine not available"}` instead of expected shape. Fixed in `SettingsPanel.tsx` (optional chaining on arrays) and `settingsStore.ts` (validate response shape before storing).

3. **Clerk auth bypass** — `useAuth()` called unconditionally in `AuthenticatedApp`, crashing when no `ClerkProvider` in tree (no-Clerk builds). Fixed by extracting `ClerkTokenBridge` component, mounted only inside `ClerkProvider`.

4. **Vite envDir** — `.env.production` not loaded because Vite `root` was `src/renderer` but env files were in `cockpit/`. Fixed by adding `envDir: resolve(__dirname)` to `vite.web.config.ts`.

5. **Build hash mismatch** — `_compute_build_info()` used directory iteration (last-wins) with multiple stale JS files. Fixed to parse `index.html` for actual referenced hashes.

## Critical Finding: DNS

`universalmetaharness.tech` DNS (66.241.125.191) resolves to **Fly.io**, NOT the VPS. The VPS Caddy is correctly configured on :443 and :8088 but unreachable from the public domain. The Fly.io app serves a stale build with Clerk dev keys baked in. This must be fixed by updating DNS to point to the VPS public IP.
