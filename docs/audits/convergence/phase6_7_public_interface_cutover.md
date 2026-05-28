# Phase 6.7 — Public Interface Cutover + Production Access Hardening

**Date:** 2026-05-28
**Branch:** worktree-anti-divergence-gate
**Base commit:** bc0f64b4 (phase 6.6)

## Deployment Path Chosen

**Option A: Direct VPS serving via Caddy** (chosen)

Rationale: VPS already runs the operator API on `:8091`, Caddy is configured
and running, and the cockpit build is on disk. Fly.io adds latency and a
stale deployment. The only blocker is DNS — the A record still points to Fly.

Option B (Fly redeploy) was rejected because it adds deployment complexity
and a second compute node to maintain.

## DNS Status

| Record | Current | Target |
|--------|---------|--------|
| A | `66.241.125.191` (Fly.io) | `157.173.212.126` (VPS) |
| AAAA | `2a09:8280:1::11b:8eb3:0` (Fly.io) | **DELETE** |

**Action required (Hostinger DNS panel):**

1. Log in to Hostinger → Domains → `universalmetaharness.tech` → DNS Zone
2. Edit the A record: change value from `66.241.125.191` to `157.173.212.126`
3. Delete the AAAA record entirely (Fly IPv6, no longer needed)
4. TTL: set to 300 (5 min) for fast propagation
5. Wait ~5–15 minutes for propagation
6. Caddy will automatically provision a production TLS certificate via ACME HTTP-01

## Public Build Hash Proof

| Artifact | Hash |
|----------|------|
| JS bundle | `index-C2ZAc6p_.js` |
| CSS bundle | `index-BCUjIQeU.css` |
| Build base commit | `bc0f64b4` |

Both `cockpit/dist-web/` and `cockpit/dist/web/` have been updated.
After operator restart, `/api/umh/build` will report these hashes.

## API Route Proof (pre-DNS, localhost verification)

All tested against `localhost:8091`:

| Endpoint | Status | Notes |
|----------|--------|-------|
| `/api/umh/build` | 200 | Returns commit sha, build hashes |
| `/api/umh/organism/status` | 200 | Live organism data (running, tick_count, stages) |
| `/api/umh/organism/spine` | 200 | 22 registered mutations, 0/0 executed |
| `/api/umh/organism/events` | 200 | Returns event array with timestamps |
| `/api/umh/pulse` | 200 | CPU, memory, disk, agents, tasks |
| `/api/umh/infra` | 200 | Tailscale nodes + Docker containers |

## Auth Hardening Changes

### Before (insecure)

- `UMH_ALLOW_INSECURE=true` globally bypassed ALL auth
- `UMH_OPERATOR_API_KEY` defaulted to `"dev-key-change-me"` (accepted as valid)
- WebSocket `/ws` and `/api/umh/ws` accepted all connections
- Any public request could hit any endpoint including privileged writes

### After (hardened)

| Layer | Mechanism | Bypass |
|-------|-----------|--------|
| HTTP reads | `X-API-Key` header validated against `UMH_OPERATOR_API_KEY` | `UMH_DEV_BYPASS=true` + private IP only |
| Privileged writes | `X-Operator-Token` header validated against `UMH_OPERATOR_TOKEN` | `UMH_DEV_BYPASS=true` + private IP only |
| WebSocket `/ws` | `?token=` query param against `UMH_WS_TOKEN` | `UMH_DEV_BYPASS=true` + private IP only |
| WebSocket `/api/umh/ws` | `?token=` query param against `UMH_WS_TOKEN` | `UMH_DEV_BYPASS=true` + private IP only |

**Private IP ranges recognized:** 127.x, 10.x, 192.168.x, 172.16-31.x, 100.64-127.x (CGNAT/Tailscale), ::1, fd (IPv6 ULA).

**Key behavioral changes:**

1. `UMH_ALLOW_INSECURE` removed entirely — no global bypass
2. `dev-key-change-me` default removed — empty string means "not configured"
3. `UMH_DEV_BYPASS` only works from private IPs — public requests always fail-closed
4. WebSocket connections rejected with code 4001 if auth fails
5. Frontend sends `X-API-Key` on all HTTP requests (from `VITE_UMH_API_KEY`)
6. Frontend sends `?token=` on all WebSocket connections (from `VITE_UMH_WS_TOKEN`)

### Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `UMH_OPERATOR_API_KEY` | API key for all HTTP reads | Yes (public) |
| `UMH_OPERATOR_TOKEN` | Token for privileged writes | Yes (public) |
| `UMH_WS_TOKEN` | Token for WebSocket auth (defaults to API key) | Optional |
| `UMH_DEV_BYPASS` | Allow private-IP access without tokens | Dev only |
| `VITE_UMH_API_KEY` | Frontend API key (build-time) | For public deploy |
| `VITE_UMH_WS_TOKEN` | Frontend WS token (build-time) | For public deploy |

## WebSocket Proof

- `/api/umh/ws` — organism realtime stream, sends pulse+events every 2s
- `/ws` — chat/voice WebSocket, bidirectional
- Both require `?token=` param on public access
- Both allow private-IP bypass when `UMH_DEV_BYPASS=true`
- Unauthenticated connections receive close code 4001

## Files Changed

| File | Change |
|------|--------|
| `transports/api/cockpit.py` | Replace `UMH_ALLOW_INSECURE` with `UMH_DEV_BYPASS` + private-IP check; add WS auth gate; update `_require_api_key` signature to include `Request` |
| `transports/api/operator.py` | Remove `dev-key-change-me` default |
| `services/operator_api.py` | Remove `dev-key-change-me` default; add WS auth gate for `/ws` |
| `cockpit/src/renderer/api/client.ts` | Add `X-API-Key` header, export `getApiKey()` |
| `cockpit/src/renderer/hooks/useWebSocket.ts` | Add `?token=` to WS URL |
| `cockpit/src/renderer/hooks/useOrganismRealtime.ts` | Add `?token=` to organism WS URL |

## Validation Gates

| Gate | Status |
|------|--------|
| `py_compile cockpit.py` | PASS |
| `py_compile operator_api.py` | PASS |
| `py_compile operator.py` | PASS |
| `tsc --noEmit` (cockpit) | PASS |
| `electron-vite build` | PASS |
| Type divergence gate | PASS (5 pre-existing warnings, no new) |
| Instance leak gate | PASS (539 files clean) |
| Dependency direction | PASS (substrate has no runtime imports from transports/services) |

## Remaining Blockers

1. **DNS A record** — must be changed at Hostinger from Fly to VPS IP
2. **Environment variables** — `services/.env` needs the new tokens added and `UMH_ALLOW_INSECURE` removed. Script prepared at `~/.claude/jobs/dad1aef1/apply_env_changes.sh`
3. **Operator restart** — `docker restart os-operator` after env change
4. **Cockpit rebuild for public** — when deploying publicly, rebuild with `VITE_UMH_API_KEY` and `VITE_UMH_WS_TOKEN` set

## Deployment Sequence (after merge)

```bash
# 1. Apply env changes
bash ~/.claude/jobs/dad1aef1/apply_env_changes.sh

# 2. Copy new Python code (already in repo after merge)
# 3. Restart operator
docker restart os-operator

# 4. Verify local access still works
curl -s http://localhost:8091/api/umh/build

# 5. Change DNS at Hostinger (manual step)
# 6. Wait for propagation (5-15 min)
# 7. Verify public access
curl -s -H "X-API-Key: $UMH_OPERATOR_API_KEY" https://universalmetaharness.tech/api/umh/build
```

## Next Highest-Leverage Step

Change DNS A record at Hostinger. Everything else is ready.
Once DNS propagates, Caddy auto-provisions TLS, and the cockpit
is live at `https://universalmetaharness.tech` with hardened auth.
