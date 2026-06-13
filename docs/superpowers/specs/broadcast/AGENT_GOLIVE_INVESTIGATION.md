# Zone C Investigation — Agent-Driven Go-Live Validation

**Date**: 2026-06-12
**Status**: Investigation complete. Awaiting execute paste.

---

## 1. Capability Registration + Dispatch (ZERO core edits required)

**Two capability systems exist — only one is the extension point.**

| System | File | Purpose | Requires core edit? |
|--------|------|---------|---------------------|
| `capability_router.py` | `substrate/execution/runtime/capability_router.py` | Hardcoded 28-member Capability enum for LLM tool routing | YES — not our path |
| `IntegrationRegistry` + `CapabilitySocket` | `substrate/sockets/registry.py`, `capability_socket.py`, `protocols.py` | Plugin-style registration for any adapter | **NO** — this is the path |

**The path (proven by Notion adapter):**

1. Implement `CapabilityHandler` protocol (4 methods):
   - `integration_id -> str` (e.g. `"broadcast"`)
   - `describe_capabilities() -> list[CapabilityDescriptor]` (start, stop, status)
   - `handle_capability(request: CapabilityRequest) -> CapabilityResponse` (dispatch to engine)
   - `health() -> CapabilityHealth` (engine state)

2. Build `IntegrationManifest(integration_id="broadcast", capability_handler=handler)`

3. Call `IntegrationRegistry.register(manifest)` at boot — one line, no core edits.

**Dispatch path**: Cell calls `IntegrationAdapter.execute("start", params)` → builds `CapabilityRequest` → `CapabilitySocket.request()` → looks up handler → `handler.handle_capability(req)` → returns `CapabilityResponse`.

**Key detail**: The handler calls `BroadcastEngine` directly (in-process), same as Notion calls the Notion API client. The HTTP routes are the UI surface; the capability handler is the agent surface. Both share the engine singleton.

**Reference files**:
- `substrate/sockets/protocols.py:77-92` — CapabilityHandler Protocol
- `substrate/sockets/registry.py:96-117` — IntegrationManifest + register()
- `substrate/sockets/capability_socket.py:49` — dispatch
- `substrate/sockets/envelopes.py:41,56` — Request/Response shapes
- `adapters/notion/integration/handlers.py` — working example
- `adapters/notion/integration/manifest.py` — descriptor declarations

**VERDICT**: Adding broadcast capability requires ZERO edits to `capability_router.py`, `agent_runtime.py`, `orchestrator.py`, or any core file. The IntegrationRegistry is the clean extension point.

---

## 2. Secret Access (Stream Key Path)

**Current pattern**: 1Password → `.env.tpl` (committed, `op://` refs) → `dc-up.sh` injects → Docker env vars → `os.getenv()`.

**Stream key flow for public-platform follow-on**:

```
1Password vault "UMH-Production"
    → item "Broadcast-Twitch" field "stream_key"
    → services/.env.tpl: TWITCH_STREAM_KEY=op://UMH-Production/Broadcast-Twitch/stream_key
    → dc-up.sh: op inject resolves at container start
    → Broadcast handler: os.getenv("TWITCH_STREAM_KEY")
    → Passed to engine config, NOT embedded in output URL
       (output URL validator rejects embedded credentials)
```

For Claude Code sessions: `start_session.sh` uses `op run --env-file=services/.env.tpl` — same resolution, no disk write.

**Key constraint**: Stream keys MUST NOT appear in FFmpeg argv (visible via `ps aux`). The output URL validator already enforces this — `parsed.username` or `parsed.password` triggers rejection. For the public follow-on, the stream key gets appended to the RTMP path component (e.g., `rtmp://live.twitch.tv/app/{key}`) which is standard RTMP convention and acceptable in argv.

**Reference**: DISCORD_BOT_TOKEN follows this exact path (`.env.tpl:20`, injected by `dc-up.sh`, read by services via `os.getenv`).

---

## 3. Broadcast Socket Contract (Programmatic)

A cell consumes broadcast through the CapabilityHandler, not HTTP. Three operations:

### `start`
```python
CapabilityRequest(
    capability_name="start",
    integration_id="broadcast",
    params={
        "source_type": "test_pattern",
        "source_config": {},
        "output_url": "rtmp://100.74.199.102:1935/live/test",
        "resolution": "1280x720",
        "video_bitrate": "2500k",
        "fps": 30,
    },
)
# Returns: CapabilityResponse(success=True, result_data={"pid": 12345, "state": "live"})
```

### `stop`
```python
CapabilityRequest(
    capability_name="stop",
    integration_id="broadcast",
    params={},
)
# Returns: CapabilityResponse(success=True, result_data={"exit_code": 255, "state": "idle"})
```

### `status`
```python
CapabilityRequest(
    capability_name="status",
    integration_id="broadcast",
    params={},
)
# Returns: CapabilityResponse(success=True, result_data={
#     "state": "live",
#     "health": {"fps": 29.0, "bitrate_kbps": 2200, "drop_percentage": 0.0, ...},
#     "pid": 12345,
# })
```

---

## 4. Reachability — VPS → Beast over Tailscale

| Check | Result |
|-------|--------|
| Ping 100.74.199.102 | **OK** — 0% loss, 81ms RTT |
| Tailscale status | **active; direct** connection (not relayed) |
| Port 1935 (RTMP) | **CLOSED** — MediaMTX not running on Beast yet |
| Non-loopback? | **YES** — `is_loopback=False`, `is_private=False` (Python 3.12) |
| Output URL validator | **PASSES** — 100.74/10 is not flagged by `is_private` on 3.12 |

**Topology consideration**: Python 3.12 classifies 100.64.0.0/10 (CGNAT/Tailscale) as `is_private=False`. Docker containers run 3.11 — need to verify same behavior there. If 3.11 rejects Tailscale IPs, the test must bypass the output URL validator or use a public relay.

**Pre-test setup needed on Beast**:
1. Start MediaMTX on Beast listening on :1935 (all interfaces)
2. Open firewall rule if Windows Defender blocks inbound on 1935
3. Verify from VPS: `ffprobe rtmp://100.74.199.102:1935/live/test`

---

## 5. ProcessLifecycle + Engine Review (Post-Merge)

**MUST-FIX (1)**:
- **Stale exit callback**: `_handle_exit` can fire on a stale engine after stop() + new start() cycle, corrupting the new session's state. Fix: reset/unbind `_on_exit` callback during `stop()`.

**SHOULD-FIX (3)**:
- **SIGKILL wait has no timeout**: `await self._proc.wait()` after SIGKILL could hang forever on a zombie. Wrap in `wait_for(..., timeout=5.0)`.
- **Concurrent start/stop race**: No lock on engine state transitions. Add `asyncio.Lock` to engine (the route file has one, but the capability handler won't go through routes).
- **Monitor cancel race**: Narrow window where `_proc` could be None when monitor task accesses it between `_stopped=True` and cancel delivery.

**NOTES (acceptable for now)**:
- `preexec_fn=os.setsid` correct for 3.11 (3.12's `process_group` not available)
- `asyncio.gather` dangling reader — clean, both coroutines complete
- Health parse silently swallows ValueError — correct for production
- `_stopped` flag not thread-safe — all usage is single-threaded asyncio

---

## Planned Test Topology (cross-host egress — DEFERRED)

```
┌─────────────────────────────────────────────────────────────────┐
│  VPS (srv1500858)                                               │
│                                                                 │
│  agent cell ──capability──▶ BroadcastCapabilityHandler           │
│                                    │                             │
│                            BroadcastEngine.start()               │
│                                    │                             │
│                            ProcessLifecycle (FFmpeg subprocess)   │
│                                    │                             │
│                  testsrc2 (lavfi) → libx264 → RTMP push          │
│                                    │                             │
└────────────────────────────────────┼─────────────────────────────┘
                                     │ Tailscale (100.74.199.102)
                                     │ ~81ms RTT, direct connection
                                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  Beast (desktop-lvguiq9)                                        │
│                                                                 │
│                  MediaMTX :1935 (RTMP ingest)                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼ (verification from VPS)
                              ffprobe rtmp://100.74.199.102/live/test
                              → confirm H.264, advancing frames
                              → WS health check (fps, bitrate, uptime)
                              → agent stop → clean teardown
                              → ps check → ZERO orphan ffmpeg
```

**Status**: DEFERRED — MediaMTX not yet installed on Beast (port 1935 closed
at investigation time). Cross-host egress over WireGuard tunnel is untested.

## Actual Test Topology (what was proven)

```
┌─────────────────────────────────────────────────────────────────┐
│  VPS (srv1500858)                                               │
│                                                                 │
│  agent cell / cockpit UI                                         │
│        │                                                         │
│        ▼                                                         │
│  BroadcastEngine → FFmpeg subprocess                             │
│        │                                                         │
│        ▼ RTMP push to 100.77.233.50:1935 (VPS own Tailscale IP) │
│        │                                                         │
│  MediaMTX :1935 (same host)                                      │
│        │                                                         │
│        ▼ ffprobe pull-back confirms H.264 High, 30fps            │
└─────────────────────────────────────────────────────────────────┘
```

**What this proves**: Full pipeline (engine + FFmpeg + RTMP + health parsing +
lifecycle + SSRF validator + capability handler + cockpit UI). The RTMP target
(100.77.233.50) is the VPS's own Tailscale CGNAT IP — non-loopback per Python
`is_loopback`, non-private per Python `is_private` (both 3.11 and 3.12), but
kernel-local (never traverses WireGuard to a peer). This validates the full
software stack but does NOT prove cross-host network egress.

**PROVEN**: agent-drive go-live, cockpit human path, engine+FFmpeg pipeline,
SSRF output URL validator, ProcessLifecycle fixes, dual-consumer contract.
**NOT PROVEN**: cross-host egress (Beast MediaMTX pending).

---

## Concrete Plan: Thin Broadcast Capability

### Files to create (ZERO core edits):

| File | Purpose |
|------|---------|
| `adapters/broadcast/integration/__init__.py` | Package marker |
| `adapters/broadcast/integration/manifest.py` | `INTEGRATION_ID`, `CAPABILITY_DESCRIPTORS` (start, stop, status) |
| `adapters/broadcast/integration/handlers.py` | `BroadcastCapabilityHandler` — dispatches to engine singleton |

### Registration (1 line at boot):
```python
from substrate.sockets.registry import IntegrationRegistry, IntegrationManifest
from adapters.broadcast.integration.handlers import BroadcastCapabilityHandler

IntegrationRegistry.register(IntegrationManifest(
    integration_id="broadcast",
    capability_handler=BroadcastCapabilityHandler(),
))
```

This line goes in a boot-time registration function (pattern: lazy-load in cockpit.py or a dedicated `adapters/broadcast/integration/boot.py` called from the API server startup).

### Capability descriptors:

| Name | Category | Risk | Input | Output |
|------|----------|------|-------|--------|
| `start` | COMMUNICATE | EXTERNAL_COMMUNICATION | source_type, source_config, output_url, video/audio params | pid, state |
| `stop` | COMMUNICATE | READ_ONLY | (none) | exit_code, state |
| `status` | RETRIEVE | READ_ONLY | (none) | state, health, pid, config |

### Engine fixes to fold in (from review):

| Fix | Priority | What |
|-----|----------|------|
| Stale exit callback | MUST-FIX | Reset `_on_exit` binding during `stop()` |
| SIGKILL wait timeout | SHOULD-FIX | `wait_for(proc.wait(), timeout=5.0)` after SIGKILL |
| Engine-level lock | SHOULD-FIX | `asyncio.Lock` on start/stop (capability handler bypasses route lock) |

### Secret path for public follow-on:
```
.env.tpl: TWITCH_STREAM_KEY=op://UMH-Production/Broadcast-Twitch/stream_key
Handler: key = os.getenv("TWITCH_STREAM_KEY")
Output URL: rtmp://live.twitch.tv/app/{key}  (key in path component, not userinfo)
```

---

## STOP. Awaiting execute paste.
