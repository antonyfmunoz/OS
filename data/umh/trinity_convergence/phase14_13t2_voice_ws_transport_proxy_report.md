# Phase 14.13T-2 Seal: Voice WebSocket Transport Proxy

**Date:** 2026-06-08 (initial), 2026-06-09 (final fix)
**Phase:** 14.13T-2 — Voice WS Transport for Deployed Cockpit
**Status:** SEALED
**Verdict:** PASS — deployed browser voice pipeline operational, verified end-to-end

---

## Problem

Deployed cockpit browser at `universalmetaharness.tech` could not reach the voice server. Multiple layers were broken.

## Root Cause Chain

1. **ws_router never mounted** (CRITICAL): `cockpit.py` defines a separate `ws_router` APIRouter for WebSocket endpoints (`/api/umh/ws` and `/api/umh/voice/ws`), but `app.py` only imported and included `router` (the HTTP router). The WebSocket endpoints existed in code but returned 404 at runtime.
2. **Missing Sec-WebSocket-Protocol forwarding**: nginx voice WS proxy block was missing the `Sec-WebSocket-Protocol` header forwarding that the main cockpit WS block had. Without it, subprotocol-based auth tokens would be silently dropped.
3. **URL mismatch** (fixed in prior session): Browser voice client had been hardcoded to `ws://localhost:8096/voice`
4. **Docker network isolation** (fixed in prior session): iptables rule needed for Docker→host traffic

## Fix Architecture

### Layer 1 — Frontend URL Resolver (`cockpit/src/renderer/api/voice-ws.ts`)
Detects environment at module load:
- Electron/localhost/Tailscale → `ws://localhost:8096/voice` (direct)
- Deployed browser → `wss://{window.location.host}/api/umh/voice/ws` (same-origin proxy)
- Env override → `VITE_VOICE_URL` takes precedence

### Layer 2 — Backend Voice WS Proxy (`transports/api/cockpit.py`)
FastAPI WebSocket endpoint at `/api/umh/voice/ws`:
- Auth: same as main cockpit WS (subprotocol bearer token or query param)
- Upstream: connects to `VOICE_WS_UPSTREAM` (default `ws://host.docker.internal:8096/voice`)
- Bidirectional forwarding: binary (PCM audio) and JSON control frames
- 4 MiB max message size, 5s upstream connect timeout

### Layer 3 — Nginx Voice Route (`cockpit/nginx.conf.template`)
```
location /api/umh/voice/ws {
    proxy_pass http://127.0.0.1:8091/api/umh/voice/ws?token=${UMH_WS_TOKEN};
    ...WebSocket upgrade headers...
}
```

### Layer 4 — Docker-to-Host Networking
- `docker-compose.yml`: Added `VOICE_WS_UPSTREAM=ws://host.docker.internal:8096/voice` to os-operator environment
- `infra/scripts/dc-up.sh`: Idempotent iptables rule allowing Docker bridge → host port 8096
- `cockpit_presence_routes.py`: Health check uses `host.docker.internal` when `VOICE_WS_UPSTREAM` indicates container environment

## Full Request Path (deployed browser)

```
Browser mic → PCM16 chunks
  → wss://universalmetaharness.tech/api/umh/voice/ws
  → nginx on Fly (proxy_pass to 127.0.0.1:8091)
  → SSH tunnel (Fly → VPS via Tailscale)
  → os-operator FastAPI proxy (inside Docker)
  → host.docker.internal:8096 (iptables rule)
  → voice_server.py on VPS host
  → Groq Whisper STT
  → transcript JSON back through same chain
```

## Verification

### Automated
- `docker exec os-operator python3 -c "socket.connect(('host.docker.internal', 8096))"` → CONNECTED
- Voice proxy WS test: connect → mic_start → silence → mic_stop → `{"type": "transcript", "text": "", "final": true}` — full round-trip confirmed
- Voice health endpoint: `"ok": true, "voice_server": "reachable"`

### Deployed Browser
- Console log: `[VoicePipeline] voice_ws_url_resolved wss://universalmetaharness.tech/api/umh/voice/ws`
- Direct WebSocket test from Playwright: `CONNECTED — voice WS proxy works from deployed browser`
- Cockpit deployed to Fly, health checks pass, WS proxy operational

## Files Changed (2026-06-09 final fix)

| File | Change |
|------|--------|
| `transports/api/app.py` | Import and include `ws_router` from cockpit.py — the actual root cause |
| `cockpit/nginx.conf.template` | Add `Sec-WebSocket-Protocol` header forwarding to voice WS block |
| `transports/api/cockpit_presence_routes.py` | Flatten health response to match spec |

### Previously changed (2026-06-08 partial fix)
| File | Change |
|------|--------|
| `docker-compose.yml` | `VOICE_WS_UPSTREAM` env var for os-operator |
| `infra/scripts/dc-up.sh` | Idempotent iptables rule for Docker→host voice traffic |
| `transports/api/cockpit.py` | Voice WS proxy handler + URL resolver |
| `cockpit/src/renderer/api/voice-ws.ts` | Environment-aware URL resolver |

## End-to-End Verification (2026-06-09)

1. **VPS direct**: `ws://127.0.0.1:8091/api/umh/voice/ws?token=...` → `{"type": "connected"}` ✅
2. **Deployed cockpit**: `wss://universalmetaharness.tech/api/umh/voice/ws` → `{"type": "connected"}` ✅
3. **Console log**: `[VoicePipeline] voice_ws_url_resolved wss://universalmetaharness.tech/api/umh/voice/ws` ✅
4. **Health endpoint**: `"ok": true, "voice_server": "reachable"` ✅
5. **Docker logs**: `[VoiceProxy] client_connected`, `upstream_connected`, `session_ended` ✅
6. **Cockpit WS also fixed**: `/api/umh/ws` now returns system metrics (was also broken by same ws_router issue) ✅

## Remaining Work

- **Real hardware mic trial**: Requires human operator with browser mic on deployed cockpit
- **Voice command routing**: transcript → DEX → response → TTS
- **TTS playback**: Kokoro on Beast must be reachable

## Commits

- `96cd0d4a` fix: voice WS proxy Docker-to-host networking — iptables + host.docker.internal
- `18232831` feat: voice WebSocket transport proxy — deployed cockpit can reach voice server
- `4bbe4055` fix: mount ws_router so voice/cockpit WebSocket endpoints are reachable
