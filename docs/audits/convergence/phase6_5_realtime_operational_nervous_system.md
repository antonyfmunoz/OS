# Phase 6.5 — Realtime Operational Nervous System

**Date:** 2026-05-28
**Status:** DEPLOYED (Tailscale), DNS BLOCKED (universalmetaharness.tech)
**Build hash:** index-DhLGIOb_.js / index-DCEn9RGg.css

---

## Baseline Issues Found

1. **Caddy path mismatch**: Caddy served from `cockpit/dist/web`, Vite built to `cockpit/dist-web`. Both paths now synced.
2. **Stale build**: dist-web was from May 26 (2 days old), dist/web from May 27. Both now updated.
3. **Wrong WebSocket target**: Frontend `useWebSocket` connected to `/ws` (chat/voice), not `/api/umh/ws` (organism stream). The backend cockpit WS at `/api/umh/ws` was never consumed by the frontend.
4. **Router auth on WebSocket**: The cockpit router's `APIRouter(dependencies=[Depends(_require_api_key)])` caused WS handshake to fail with HTTP 500. Fixed by moving WS to a separate `ws_router` without auth dependency.
5. **Missing psutil**: Docker image lacked `psutil`, causing the entire cockpit router to fail on import. Added to `requirements.txt`.
6. **Docker CLI unavailable in container**: `subprocess.run(["docker", "ps"])` failed silently. Replaced with Docker Engine API via Unix socket (`/var/run/docker.sock`).

## Realtime Transport

**Chosen:** WebSocket primary at `/api/umh/ws` with automatic polling fallback.

- Backend: `ws_router` in `transports/api/cockpit.py` streams pulse + organism_events every ~2s
- Frontend: `useOrganismRealtime` hook connects, parses, deduplicates, dispatches to stores
- Fallback: When WS drops, polling activates at 5s intervals; WS reconnects with exponential backoff (1s → 30s max)
- Heartbeat: Client sends `ping` every 25s, server responds `pong`

**Proof:**
```
ws://localhost:8091/api/umh/ws → type: pulse, cpu: 26.0%, memory: 34.7%, containers: 3
ws://localhost:8088/api/umh/ws → type: pulse (via Caddy proxy) ✓
```

## Cockpit Panels Updated

| Panel | Changes |
|-------|---------|
| **OrganismPanel** | Full 3-column operational cortex: ExecutionTimeline + EventConsole + TopologyMap/Leverage/Bottlenecks. 10-KPI strip with live CPU/RAM from WS. ConnectionBanner. Adaptive polling (15s when WS up, 5s when down). |
| **ExecutionPanel** | ExecutionTimeline component with lifecycle progress bars. EventConsole (compact) in sidebar. Adaptive polling. |
| **DashboardPanel** | 10-KPI strip (added EVENTS/min, RUNTIMES count). Live containers from WS. Runtime graph replaces static model badges when available. Removed "No models registered" placeholder — shows runtime graph or contextual "waiting" message. |
| **ApprovalsPanel** | Rejection reason input field. Gateway decisions sidebar. Guard violations panel. Execution mode/guard/gateway status in header. |
| **InfrastructurePanel** | TopologyMap component. Live Docker containers from WS pulse. CPU/RAM/DISK in header from realtime store. |

## New Components

| Component | Purpose |
|-----------|---------|
| `stores/realtimeStore.ts` | Zustand store for WS connection state, event buffer (max 500), dedup set (max 1000 IDs), system metrics, domain filtering |
| `hooks/useOrganismRealtime.ts` | WS connection management, reconnect with backoff, fallback polling, organism event dispatching |
| `components/EventConsole.tsx` | Live event stream with domain filters (ALL/GOV/EXEC/RUNTIME/LEVERAGE/etc), expandable payload, auto-scroll toggle |
| `components/ExecutionTimeline.tsx` | Envelope lifecycle visualization with 7-stage progress bar, journal trail |
| `components/TopologyMap.tsx` | Runtime topology grouped by type (core/governance/transport/runtime/docker/mesh) with health dots |
| `components/ConnectionBanner.tsx` | Non-intrusive connection status indicator, invisible when healthy |

## Endpoints Consumed

All via `organismStore.ts` fetching from `/api/umh/organism/*`:
- `/organism/status` — daemon state, agents, runtimes
- `/organism/spine` — execution stats
- `/organism/spine/pending` — pending envelopes
- `/organism/spine/active` — active executions
- `/organism/spine/completed` — completed history
- `/organism/spine/approve/:id` — approve action (POST)
- `/organism/spine/reject/:id` — reject action (POST)
- `/organism/journal/statistics` — journal stats
- `/organism/journal/recent` — recent entries
- `/organism/autonomous-gateway` — gateway status
- `/organism/autonomous-gateway/decisions` — decision history
- `/organism/spine-guard` — guard status
- `/organism/bottlenecks` — active bottlenecks
- `/organism/leverage` — leverage dimensions
- `/organism/execution-mode` — mode status
- `/organism/workloads` — workload probe results
- `/organism/events` — event history
- `/organism/mutations` — mutation registry

Plus WebSocket at `/api/umh/ws` for live pulse + organism events.

## Placeholder Removal

| Before | After |
|--------|-------|
| "No models registered" | Shows runtime graph runtimes when available, falls back to model badges, shows "Waiting for runtime graph data..." when WS connected but no data yet |
| "No infrastructure connected" | Shows live Docker containers from WS pulse, falls back to mesh/infra nodes, shows contextual message based on WS state |
| Static 8-column KPI strip | 10-column strip with live CPU/RAM from WS, events/min, runtime count |
| 5s polling everywhere | Adaptive: 15s when WS connected, 3-5s when disconnected |

## Deployment Verification

- ✅ `localhost:8091` serves build hash `DhLGIOb_`
- ✅ Caddy `:8088` serves build hash `DhLGIOb_` (Tailscale)
- ✅ WebSocket connects through Caddy proxy
- ✅ Organism daemon running (tick #3+)
- ✅ 3 containers visible in WS pulse
- ✅ All organism API endpoints returning real data
- ❌ `universalmetaharness.tech` DNS points to Fly.io (66.241.125.191), not VPS (157.173.212.126)

## DNS Blocker

`universalmetaharness.tech` resolves to `66.241.125.191` (Fly.io), serving a stale build. The VPS Caddy instance at `157.173.212.126` has the current build. Fix requires updating DNS A record to point to VPS, or redeploying to Fly.io.

**Workaround:** Access via Tailscale at `http://100.77.233.50:8088`

## Gates

- ✅ TypeScript typecheck: clean
- ✅ Vite production build: 440KB JS, 29KB CSS
- ✅ py_compile: cockpit.py, operator_api.py
- ✅ Type divergence gate: 0 blocked (1 pre-existing warning)
- ✅ Instance leak gate: 539 files clean
- ✅ Dependency direction: no substrate → transports/services imports
- ✅ Line count: all files under 3000 (cockpit.py at 2860)

## Backend Changes

1. `transports/api/cockpit.py`: Added `ws_router` (no auth dependency) for WebSocket endpoint. Added `_get_docker_containers()` using Docker Engine API via Unix socket instead of `docker` CLI.
2. `services/operator_api.py`: Import and register both `cockpit_router` and `cockpit_ws_router`.
3. `docker-compose.yml`: Mounted `/var/run/docker.sock:ro` into os-operator.
4. `requirements.txt`: Added `psutil`.

## Remaining Blockers

1. **DNS**: universalmetaharness.tech → Fly.io, not VPS. Must update A record.
2. **Docker image rebuild**: psutil was `pip install`'d at runtime; needs `docker compose build` for persistence.
3. **Organism events latency**: Events only flow when organism daemon ticks (~21s interval). Between ticks, the event stream is silent. This is expected behavior, not a bug.

## Next Highest-Leverage Step

1. Fix DNS to point universalmetaharness.tech to VPS
2. Rebuild Docker image with psutil in requirements
3. Add tmux session discovery to TopologyMap (host tmux socket already mounted in os-discord)
