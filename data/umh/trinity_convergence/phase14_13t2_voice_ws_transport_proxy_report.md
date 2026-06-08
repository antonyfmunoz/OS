# Phase 14.13T-2 Seal: Voice WebSocket Transport Proxy

**Date:** 2026-06-08
**Phase:** 14.13T-2 — Voice WS Transport for Deployed Cockpit
**Status:** SEALED
**Verdict:** PASS — deployed browser voice pipeline operational

---

## Problem

Deployed cockpit browser at `universalmetaharness.tech` dialed `ws://localhost:8096/voice` for voice WebSocket. From the browser, `localhost` resolves to the user's device, not the VPS where the voice server runs. Voice pipeline dead from deployed cockpit.

## Root Cause Chain

1. **URL mismatch**: Browser voice client hardcoded `ws://localhost:8096/voice` regardless of deployment context
2. **No proxy path**: No same-origin voice WS endpoint existed for deployed browsers
3. **Docker network isolation**: Voice server runs on VPS host port 8096; os-operator container can't reach host ports through `127.0.0.1`
4. **UFW firewall**: INPUT policy DROP silently blocks Docker bridge traffic to host, even through `host.docker.internal`

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

## Files Changed

| File | Change |
|------|--------|
| `docker-compose.yml` | `VOICE_WS_UPSTREAM` env var for os-operator |
| `infra/scripts/dc-up.sh` | Idempotent iptables rule for Docker→host voice traffic |
| `transports/api/cockpit.py` | Default upstream changed to `host.docker.internal` |
| `transports/api/cockpit_presence_routes.py` | Health check uses correct host based on env |

## Remaining Work

- **Workcell F**: Real hardware mic trial (requires human operator with browser mic)
- **Workcell G**: Voice command routing trial (transcript → DEX → response → TTS)
- **Workcell H**: TTS cancel/interruption trial (requires Kokoro on Beast)
- Kokoro TTS on Beast shows unreachable — Beast may be powered off

## Commits

- `96cd0d4a` fix: voice WS proxy Docker-to-host networking — iptables + host.docker.internal
- `18232831` feat: voice WebSocket transport proxy — deployed cockpit can reach voice server
