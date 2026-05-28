# Phase 6.8 — Public Launch Verification + Production Control Baseline

**Date:** 2026-05-28
**Merged PR:** #5 (commit `2ae39404`, merge commit on main)
**Compose fix:** `a80d1392` (removed `dev-key-change-me` default from docker-compose.yml)

## Task 1 — PR #5 Merge Status

PR #5 merged to main at `2026-05-28T16:53:51Z`. Contains:

| Hardening feature | Verified |
|-------------------|----------|
| WS subprotocol auth (`Sec-WebSocket-Protocol: bearer.<token>`) | YES |
| `ipaddress`-based private IP validation | YES |
| `hmac.compare_digest` timing-safe token comparison (4 usages) | YES |
| `dev-key-change-me` default removed | YES |
| `UMH_ALLOW_INSECURE` removed entirely | YES |
| Frontend `VITE_UMH_API_KEY` / `VITE_UMH_WS_TOKEN` support | YES |

## Task 2 — Environment Verification

Container env verified via `docker exec os-operator env`:

| Variable | Present | Value correct |
|----------|---------|---------------|
| `UMH_OPERATOR_API_KEY` | YES | Real token (not dev-key) |
| `UMH_OPERATOR_TOKEN` | YES | Set |
| `UMH_WS_TOKEN` | YES | Set |
| `UMH_DEV_BYPASS` | YES | `true` |
| `UMH_ALLOW_INSECURE` | NO (correct) | — |

**Bug found + fixed:** docker-compose.yml `environment:` block had
`UMH_OPERATOR_API_KEY=${UMH_OPERATOR_API_KEY:-dev-key-change-me}` which
always overrode the `env_file` value because the host shell didn't export it.
Fixed by removing the line entirely (`a80d1392`).

## Task 3 — Cockpit Build with Public Tokens

| Artifact | Hash |
|----------|------|
| JS bundle (production) | `index-39q53cn6.js` |
| CSS bundle | `index-BCUjIQeU.css` |
| Previous JS hash (no tokens) | `index-9qBg6yvr.js` |

Tokens verified baked into bundle:
- `Qd_vgBjj...` (API key prefix) found in JS
- `1ZSuF8Mz...` (WS token prefix) found in JS

Both build directories synced:
- `cockpit/dist-web/` — updated
- `cockpit/dist/web/` — updated

## Task 4 — Production Operator Verification

| Check | Result |
|-------|--------|
| Operator startup | Clean — Uvicorn on 0.0.0.0:8091 |
| `/api/umh/build` | 200 — returns `index-39q53cn6.js`, commit `a80d1392` |
| `/api/umh/pulse` | 200 from private IP |
| `/api/umh/organism/status` | 200 with correct API key |
| WS `/api/umh/ws` no token (localhost) | Connected (dev bypass — expected) |
| WS `/api/umh/ws` bearer subprotocol | Connected, subprotocol echoed back |
| Privileged POST without operator token | 403 Forbidden |
| Privileged POST with operator token | 200 OK |
| Tailscale IP (100.100.155.111) requests | All 200 (dev bypass working) |

## Task 5 — DNS Cutover

**Status: PENDING — manual action required**

| Record | Current | Target |
|--------|---------|--------|
| A | `66.241.125.191` (Fly.io) | `157.173.212.126` (VPS) |
| AAAA | `2a09:8280:1::11b:8eb3:0` (Fly.io) | **DELETE** |

**Action:** Hostinger → Domains → universalmetaharness.tech → DNS Zone
- Edit A record → `157.173.212.126`
- Delete AAAA record
- TTL: 300

After propagation:
- Caddy will auto-provision TLS certificate via ACME HTTP-01
- Cockpit becomes publicly accessible with hardened auth

## Task 6 — Public Cockpit Smoke Test

**Status: BLOCKED on DNS cutover**

Cannot verify public access until DNS points to VPS. Local/Tailscale
access verified via Task 4 — all endpoints functional, build correct,
auth gates enforced.

## Task 7 — Security Smoke Test

| Check | Result |
|-------|--------|
| No `?token=` in WS URLs | PASS — no matches in frontend hooks |
| `Sec-WebSocket-Protocol: bearer.<token>` used | PASS — both hooks confirmed |
| Missing token closes WS with 4001 | PASS — code verified in both backends |
| Public IP cannot use `UMH_DEV_BYPASS` | PASS — `_is_private_ip()` uses `ipaddress` module |
| Private IP bypass only if `UMH_DEV_BYPASS=true` | PASS — checked in `_dev_bypass_allowed()` |
| Timing-safe compare used | PASS — 4 `hmac.compare_digest` usages |
| No `dev-key-change-me` in codebase | PASS — grep found 0 matches |
| No `UMH_ALLOW_INSECURE` in code/config | PASS — grep found 0 matches |

## Task 8 — Validation Gates

| Gate | Result |
|------|--------|
| `py_compile` (cockpit.py, operator_api.py, operator.py) | PASS |
| `tsc --noEmit` (cockpit TypeScript) | PASS |
| `electron-vite build` | PASS (new hash: `index-39q53cn6.js`) |
| Type divergence gate | PASS |
| Instance leak gate | PASS |
| Dependency direction (substrate → transports/services) | PASS |
| `hmac.compare_digest` in all auth paths | PASS (4 usages) |
| Line count (cockpit.py: 2952, operator_api.py: 698) | PASS (under 3000) |

## Remaining Blockers

1. **DNS A record** — must be changed at Hostinger (the only remaining step)
2. **Public smoke test** — requires DNS to point to VPS
3. **TLS certificate** — Caddy will auto-provision after DNS change

## Deployment Sequence Complete

```
✓ PR #5 merged
✓ docker-compose.yml fix committed (a80d1392)
✓ services/.env updated with production tokens
✓ Cockpit rebuilt with baked-in API key + WS token
✓ Both dist-web and dist/web synced
✓ os-operator recreated with correct env
✓ All validation gates passed
✓ All security checks passed
⧖ DNS change pending (manual step)
⧖ Public smoke test pending (DNS dependent)
⧖ TLS certificate pending (DNS dependent)
```

## Next Highest-Leverage Step

Change DNS A record at Hostinger. Once it propagates (~5-15 min),
Caddy auto-provisions TLS and universalmetaharness.tech is live with
the hardened cockpit — no Fly stale-build split.
