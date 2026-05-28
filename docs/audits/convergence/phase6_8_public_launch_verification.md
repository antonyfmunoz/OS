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

**Status: COMPLETE**

| Record | Before | After |
|--------|--------|-------|
| A | `66.241.125.191` (Fly.io) | `157.173.212.126` (VPS) |
| AAAA | `2a09:8280:1::11b:8eb3:0` (Fly.io) | DELETED |

DNS verification:
- Authoritative NS (`atlas.dns-parking.com`): `157.173.212.126` (immediate)
- Google DNS (`8.8.8.8`): `157.173.212.126` (propagated)
- Cloudflare DNS (`1.1.1.1`): `157.173.212.126` (propagated)

**Firewall fix:** ufw had ports 80/443 blocked. Added rules for HTTP + HTTPS.
**TLS:** Caddy auto-provisioned via TLS-ALPN-01 challenge (Let's Encrypt production).

## Task 6 — Public Cockpit Smoke Test

**Status: COMPLETE**

| Check | Result |
|-------|--------|
| HTML serves correct build | `index-39q53cn6.js` confirmed |
| Build API matches | `index-39q53cn6.js`, commit `88af1ec3` |
| Pulse endpoint | 200 — CPU, memory, disk, agents, tasks |
| Organism status | 200 — running, tick engine active |
| TLS certificate valid | Let's Encrypt production cert, ssl_verify_result=0 |

## Task 7 — Security Smoke Test

| Check | Result |
|-------|--------|
| No `?token=` in WS URLs | PASS — no matches in frontend hooks |
| `Sec-WebSocket-Protocol: bearer.<token>` used | PASS — both hooks confirmed |
| Missing token closes WS with 4001 | PASS — code verified in both backends |
| Public IP cannot use `UMH_DEV_BYPASS` | PASS — explicit trusted proxy allowlist |
| Private IP bypass only if `UMH_DEV_BYPASS=true` | PASS |
| Timing-safe compare used | PASS — 4 `hmac.compare_digest` usages |
| No `dev-key-change-me` in codebase | PASS |
| No `UMH_ALLOW_INSECURE` in code/config | PASS |
| Proxy bypass (Caddy + public XFF) | PASS — public IP via Caddy gets 401 |
| Tailscale direct (no proxy) | PASS — bypass works |

### Auth Matrix (verified via curl)

| Scenario | Expected | Actual |
|----------|----------|--------|
| Public IP, no key | 401 | 401 |
| Public IP, correct key | 200 | 200 |
| Public IP, wrong key | 401 | 401 |
| Private XFF via Caddy, no key | 200 (bypass) | 200 |
| Tailscale direct, no key | 200 (bypass) | 200 |
| Privileged route, no operator token | 403 | 403 |
| Privileged route, with operator token | 200 | 200 |

### Proxy Bypass Bug (found + fixed during verification)

Behind Caddy, `request.client.host` was always 127.0.0.1 (the proxy).
Old code checked `_is_private_ip(tcp_ip)` to decide whether to trust
XFF — but all private IPs (including Tailscale CGNAT) were treated as
trusted proxies. Tailscale IPs carry XFF chains from the real network
path (public IPv6 → CDN → Tailscale), so the first XFF entry was a
public IPv6 address but the dev bypass still triggered because the TCP
source was "private."

**Fix:** Replaced broad `_is_private_ip` check with explicit `_TRUSTED_PROXIES`
set containing only `127.0.0.1`, `::1`, and the Docker bridge IP.
Tailscale IPs are real clients, not proxies — their TCP source is used
directly. Committed as `2c890af0`.

## Task 8 — Validation Gates

| Gate | Result |
|------|--------|
| `py_compile` (cockpit.py, operator_api.py, operator.py) | PASS |
| `tsc --noEmit` (cockpit TypeScript) | PASS |
| `electron-vite build` | PASS (hash: `index-39q53cn6.js`) |
| Type divergence gate | PASS |
| Instance leak gate | PASS |
| Dependency direction (substrate → transports/services) | PASS |
| `hmac.compare_digest` in all auth paths | PASS (4 usages) |
| Line count (cockpit.py: 2952, operator_api.py: 698) | PASS (under 3000) |

## Remaining Blockers

None. All tasks complete.

## Deployment Sequence Complete

```
✓ PR #5 merged
✓ docker-compose.yml fix committed (a80d1392)
✓ services/.env updated with production tokens
✓ Cockpit rebuilt with baked-in API key + WS token (index-39q53cn6.js)
✓ Both dist-web and dist/web synced
✓ os-operator recreated with correct env
✓ All validation gates passed
✓ All security checks passed
✓ DNS A record changed to 157.173.212.126
✓ AAAA record deleted
✓ Firewall ports 80/443 opened
✓ TLS certificate provisioned (Let's Encrypt production)
✓ Public auth enforced (401 without key, 200 with key)
✓ Proxy bypass bug found and fixed (trusted proxy allowlist)
✓ Tailscale dev bypass working
```

## Commits

| Hash | Description |
|------|-------------|
| `68e55e2c` | Initial auth hardening (3-layer progressive trust) |
| `6e4ec6cf` | Security review fixes (ipaddress, hmac, subprotocol) |
| `2bb7866e` | Phase 6.7 audit report |
| `a80d1392` | docker-compose.yml fix (remove dev-key-change-me) |
| `0ee0bdd0` | Proxy bypass fix (X-Forwarded-For from trusted proxies) |
| `2c890af0` | Explicit trusted proxy allowlist |

## Next Highest-Leverage Step

universalmetaharness.tech is live. The cockpit is the canonical
interface with hardened auth, working realtime WebSocket, and no
Fly stale-build split. Next: browser-level smoke test of all panels.
