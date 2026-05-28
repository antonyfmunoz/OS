# Phase 5.6 — Production Activation + Cockpit Proof

**Date:** 2026-05-28
**Deployed commit:** `dfeca995` (Merge branch 'worktree-anti-divergence-gate')
**Key commits:**
- `92d4d054` — Phase 5.5 production activation: instance context cleanup + metabolism integration
- `3816be2e` — Wire RuntimeGraph into daemon + add organism API routes + centralize CORS
- `6dd9fb88` — Run organism tick in thread pool to prevent event loop blocking

---

## 1. Phase 5.5 Code on Main

- All Phase 5.5 commits merged to main via 3 merge cycles
- 3 merge conflicts resolved (portfolio_advisor, user_model, human_intelligence — all import path changes)
- PrimitiveType → LeveragePrimitiveType rename confirmed on main
- Type divergence gate: **PASS** (warnings only, no BLOCKED)
- Instance leak gate: **PASS** (521 files scanned, clean)
- Dependency direction: **PASS** (substrate/ has zero imports from transports/ or services/)

## 2. os-operator Restart

- `docker restart os-operator` → clean FastAPI startup
- Organism daemon startup log:
  ```
  organism daemon started: 3 agents, graph=True, supervisor=True,
    tick_stages=7, events_recovered=5
  ```
- All 7 tick stages registered:
  1. advisor
  2. homeostasis
  3. supervisor_reconcile
  4. allocation
  5. async_objectives
  6. leverage_rebalance
  7. projection_broadcast

## 3. Metabolism Running

- Tick cycle count: **3** (and incrementing)
- Total stages executed: **14** (7 per complete cycle × 2)
- Total stages failed: **0**
- Adaptive interval: 21.68s (started at 30s base, adjusted down due to activity)
- System mode: **healthy**
- All 7 homeostasis dimensions: healthy
- EventSpine events: **11** persisted to JSONL

### Production blocker fixed: event loop blocking
`daemon.tick()` is synchronous and was called directly in the async `_tick_loop`,
blocking all HTTP request handling during each ~42s tick. Fixed by wrapping in
`asyncio.to_thread()`. API now responds during tick execution.

## 4. EventSpine Persistence + Recovery

- JSONL file: `data/umh/organism/events.jsonl` — exists, growing
- Recovery proven across restarts:
  - First restart: `recovered 2 events`
  - Second restart: `recovered 5 events`
  - Third restart: `recovered 5 events` (from prior session)
- Events include: `tick_completed`, `allocation_cycle_completed`, `leverage_rebalanced`

## 5. Cockpit API — Local Verification

All endpoints return valid JSON:

| Endpoint | Status | Data |
|----------|--------|------|
| `/api/umh/pulse` | 200 | uptime, cpu, memory, agents |
| `/api/umh/organism/tick` | 200 | 7 stages, cycle count, metrics |
| `/api/umh/organism/status` | 200 | full daemon status with tick_engine, event_spine, governor |
| `/api/umh/organism/snapshot` | 200 | system_mode=healthy, objectives, work_units, runtimes, supervision |
| `/api/umh/organism/runtimes` | 200 | `[]` (no external runtimes registered yet) |
| `/api/umh/organism/governor` | 200 | limits, state, kill_switch=false, approval_map |
| `/api/umh/organism/workcells` | 200 | `[]` (workcell daemon not wired) |
| `/api/umh/organism/events` | 200 | events array with domain, type, source, data, timestamp |
| `/api/umh/execution/status` | 200 | execution slots with status |

## 6. Cockpit Frontend

- Built via `npx vite build src/renderer --outDir dist/web`
- Output: `/opt/OS/cockpit/dist/web/` (index.html + JS/CSS bundles)
- JS bundle contains organism API calls: agents, control, delegations, deliverables, handoff, parallel
- API client defaults to `/api/umh` (relative path — works with Caddy proxy)
- Frontend panels: Dashboard, Execution, Infrastructure, Approvals, Knowledge, Agents, Settings + more

### Caddy Reverse Proxy

Configured at `/etc/caddy/Caddyfile`:
- `universalmetaharness.tech` → HTTPS with auto-TLS
- `/api/*` → reverse_proxy localhost:8091
- `/ws` → reverse_proxy localhost:8091
- `/*` → static files from cockpit/dist/web with SPA fallback
- Port 8088 → HTTP fallback for testing

### Cockpit Panel Status

| Panel | Data Source | Status |
|-------|------------|--------|
| Dashboard | /pulse, /tasks, /approvals | Real data |
| Execution | /execution/status | Real data |
| Infrastructure | /infra, /mesh/nodes | Real data |
| Approvals | /approvals | Real data |
| Knowledge/Skills | /skills, /memory | Real data |
| Agents | /agents, /organism/agents | Real data |
| Settings | /settings, /governance | Real data |

## 7. Public Domain — universalmetaharness.tech

**BLOCKER: DNS A record points to wrong IP.**

- Domain resolves to: `66.241.125.191` (Hostinger web hosting default)
- VPS actual IP: `157.173.212.126`
- Fix required: Update DNS A record in Hostinger DNS panel to `157.173.212.126`
- Once DNS propagates, Caddy will auto-provision TLS cert via Let's Encrypt

**Workaround:** Access via Tailscale at `http://100.77.233.50:8088/`
- Verified: pulse, organism endpoints, frontend all serve correctly

## 8. WebSocket

- Direct connection to `ws://127.0.0.1:8091/ws`: **CONNECTED**
- Via Caddy at `ws://127.0.0.1:8088/ws`: **CONNECTED**
- EventSpine → cockpit WS bridge: **WIRED**
- Subscribers: `state_port_bridge`, `cockpit_ws_bridge`
- Events push on tick completion (not true realtime — push on ~25s tick interval)
- **Status: Connected WebSocket with event push on tick cycle. Not sub-second realtime.**

## 9. Validation Gates

| Gate | Result |
|------|--------|
| Type divergence (`check_type_divergence.py --all`) | PASS (warnings only) |
| Instance leak (`check_instance_leak.py --all`) | PASS (521 files clean) |
| Dependency direction (manual grep) | PASS |
| Organism tests (336 tests) | PASS (0 failures) |
| Import verification | PASS |
| Frontend build | PASS |

## 10. Remaining Blockers

1. **DNS A record** — `universalmetaharness.tech` must point to `157.173.212.126`. User action required in Hostinger DNS panel.
2. **Runtimes empty** — no external runtimes (Beast, Tmux, Docker) registered at startup. The RuntimeGraph starts empty; adapters need registration calls.
3. **Workcells empty** — WorkcellDaemon not wired into OrganismDaemon.
4. **Tick duration** — avg 222s per cycle due to advisor's LLM calls via cc_sdk (~42s each). Not a blocker but impacts event push frequency.
5. **Clerk auth on cockpit** — frontend uses Clerk for auth; VITE_CLERK_PUBLISHABLE_KEY must be set for the web build. Without it, app skips auth and renders directly.

## 11. Next Highest-Leverage Sprint

1. **DNS fix** — point universalmetaharness.tech A record to 157.173.212.126 (5 min, user action)
2. **Runtime registration** — register VPS runtime adapters (Tmux, Docker) at daemon startup for non-empty runtimes view
3. **Workcell wiring** — connect WorkcellDaemon into OrganismDaemon
4. **Tick optimization** — make advisor LLM calls async or skip when no signals pending
5. **Frontend organism panels** — add dedicated organism view panels to cockpit (tick, events, governor)
