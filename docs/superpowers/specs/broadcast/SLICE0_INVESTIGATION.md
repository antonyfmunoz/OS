# Slice 0 — Zone C Investigation Report

> Zone C artifact. No GPL/OBS/fork/Zone-B-source accessed.
> Inspected ONLY existing /opt/OS patterns.

---

## 1. Subprocess Lifecycle Pattern (adapters/)

**Finding: No unified subprocess wrapper exists.** The codebase has several
partial patterns but no single reusable class for spawn + monitor + health +
teardown + orphan-kill.

What exists:
- **CPU gate** (`substrate/execution/cpu_gate.py`): `gated_subprocess_run()` and
  `gated_popen()` — load-based gating (1.8/core ceiling). Returns None when CPU
  overloaded. All adapters use this. Broadcast engine MUST use it too.
- **Harness pattern** (e.g., `adapters/capabilities/goose_harness.py`): init resolves
  binary path → `health_check()` calls `--version` → `invoke()` wraps subprocess.run
  via `asyncio.to_thread()`. No long-lived process management.
- **Daemon pattern** (`substrate/organism/workcell_daemon.py`): threading.Event stop
  signal, heartbeat, exponential backoff on idle. For internal loops, not external
  process wrapping.
- **Circuit breaker** (`adapters/google_workspace/gws_connector.py`): file-based
  cooldown (`/tmp/gws_cooldown`, 300s). Stateless per call.

**Decision for broadcast engine:** Build a new `ProcessLifecycle` class in
`adapters/broadcast/engine.py` that combines:
- `gated_popen()` for spawn (CPU gate compliance)
- Asyncio subprocess monitoring (poll + stderr capture)
- Health heartbeat (process alive + stdout/stderr parse for metrics)
- Graceful teardown (SIGTERM → wait → SIGKILL)
- Orphan tracking (PID file or in-memory registry, cleanup on API shutdown)

This is new but follows existing harness + daemon patterns. No existing class to reuse.

---

## 2. HTTP Routes + WebSocket Pattern (transports/api/)

**Framework:** FastAPI. Two router instances per feature.

**Router pattern (mirroring cockpit_rooms_routes.py):**
```
broadcast_router = APIRouter(prefix="/broadcast", tags=["broadcast"])
broadcast_ws_router = APIRouter(prefix="/broadcast", tags=["broadcast-ws"])
```

**Mount pattern (lazy-load in cockpit.py, after line ~3408):**
```
def _mount_broadcast_router() -> None:
    from transports.api.cockpit_broadcast_routes import (
        broadcast_router, broadcast_ws_router
    )
    router.include_router(broadcast_router)
    ws_router.include_router(broadcast_ws_router)

_mount_broadcast_router()
```

**Auth:** `require_clerk_auth` dependency on main router (auto-applied).
WS auth via `validate_ws_clerk_token()` — checks Bearer header, then
Sec-WebSocket-Protocol subprotocol, then dev-bypass from private IP.

**Error shape:** `HTTPException(status_code=N, detail="message")` for errors.
Plain dict return for success. FastAPI auto-serializes.

**WS status-push pattern:** The cockpit uses a pulse loop (2s interval) that
sends a JSON snapshot to all connected clients. Subsystem events are injected
via `push_organism_event()` into a shared pending queue.

**Decision for broadcast:** Use the SAME push mechanism. Define a
`push_broadcast_event()` helper that calls `push_organism_event()` with
`type: "broadcast_event"`. Health metrics (bitrate, dropped frames, uptime)
pushed every 2s via this channel. OR: dedicated broadcast WS endpoint at
`/api/umh/broadcast/ws` with its own pulse loop (higher frequency, 1s,
since health metrics are time-sensitive). **Recommend dedicated WS** to
avoid polluting the main cockpit pulse with high-frequency broadcast data.

---

## 3. Pydantic Model Conventions (substrate/)

**Base:** Vanilla `BaseModel` from Pydantic v2. No custom base.
**Enums:** `class MyEnum(str, Enum)` — always str+Enum.
**Fields:** `Field(default_factory=uuid4)`, `Field(ge=0.0, le=1.0)`,
`Field(max_length=255)`. No decorators (@validator/@field_validator).
**Optionals:** `field: Type | None = None`
**Collections:** `field: list[T] = Field(default_factory=list)`
**Timestamps:** `Field(default_factory=lambda: datetime.now(timezone.utc))`

**Registration:** Broadcast models defined in route file or
`substrate/broadcast/models.py` do NOT need canonical_types.py registration.
The rooms subsystem defines its types locally in the route file — broadcast
should do the same. Only register in canonical_types.py if the types are
shared across multiple subsystems.

**Decision:** Define broadcast Pydantic models (SourceConfig, SceneConfig,
OutputProfile, BroadcastHealth) directly in `cockpit_broadcast_routes.py`
for Slice 0. Extract to `substrate/broadcast/models.py` only if they grow
complex enough to warrant a separate file. Follow the rooms pattern.

---

## 4. Cockpit Store / Panel / WS-Client Trio

**The vision subsystem trio is the canonical sibling. Mirror it 1:1.**

### broadcastStore.ts (mirror visionStore.ts)
- Exported types at top (BroadcastStatus, OutputState, HealthMetrics)
- `interface BroadcastState` with all state + setters
- INITIAL_* constants
- `export const useBroadcastStore = create<BroadcastState>((set, get) => ({...}))`

### BroadcastPanel.tsx (mirror VisionPanel.tsx)
- Import React + useViewContextStore + useBroadcastStore + sub-components
- `export function BroadcastPanel()`
- useEffect sets view context on mount
- Destructure selectors from store
- Return JSX with status + child controls

### broadcast-ws.ts (mirror vision-ws.ts)
- Import WsClient from `./websocket`
- URL resolver: `getBroadcastUrl()` (localhost:PORT or /api/umh/broadcast/ws)
- Exported event discriminated union: `type BroadcastEvent = ...`
- `export class BroadcastWsClient` with:
  - constructor (creates WsClient)
  - connect() / disconnect() / reconnect()
  - Command methods (startStream, stopStream, getHealth, etc.)
  - on(type, handler) for event subscription

### useBroadcastConnection.ts (mirror useVisionConnection.ts)
- Module-level singleton: `let _client: BroadcastWsClient | null = null`
- `export function useBroadcastConnection(): void`
- Single useEffect with empty deps []
- Create/reuse client singleton
- Subscription array: client.on('event_type', handler)
- Polling intervals (health every 1s)
- Cleanup: unsubscribe, clear timers, disconnect, reset store

### Integration touchpoints (NOT core files):
- `cockpitStore.ts`: add `| 'broadcast'` to Panel union
- `routes.ts`: add route entry with id 'broadcast'
- `Shell.tsx`: add `case 'broadcast': return <BroadcastPanel />`

---

## 5. Do-Not-Touch Confirmation

ALL core files are avoidable for Slice 0:

| Core File | Avoidable? | Reason |
|-----------|-----------|--------|
| substrate/types.py | YES | Define types locally in route file |
| substrate/__init__.py | YES | Broadcast lives in transports.api |
| substrate/control_plane/ | YES | Broadcast is transports-layer |
| substrate/execution/ | YES | No orchestration involvement |
| services/discord_bot.py | YES | Broadcast is adapter-agnostic |
| adapters/models/model_router.py | YES | Broadcast is event-driven, not LLM |
| Vision components | YES | Parallel subsystem, no coupling |
| Conference Room components | YES | Parallel subsystem, no coupling |

Files that WILL be edited (all permitted — not in the restricted list):
- `cockpitStore.ts` — add 'broadcast' to Panel union
- `routes.ts` — add broadcast route entry
- `Shell.tsx` — add BroadcastPanel case
- `cockpit.py` — add lazy-mount for broadcast router (~5 lines)

---

## Proof Topology

### Host: VPS (self-contained, no GUI dependency)
The engine wraps FFmpeg as a subprocess. FFmpeg runs headless. No X server,
no GPU, no webcam needed. The VPS is the correct host for Slice 0.

### Source: FFmpeg lavfi test pattern (testsrc2)
The VPS has no webcam. Use FFmpeg's built-in test signal generator:
`-f lavfi -i testsrc2=size=1920x1080:rate=30`
This produces a synthetic video source with color bars, timestamp, and frame
counter. Isolates pipeline mechanics with zero device dependency.

### Test Ingest: MediaMTX (local RTMP server)
MediaMTX (formerly rtsp-simple-server) is a single Go binary. No external
dependencies, no cloud accounts, sovereignty-aligned. Accepts RTMP ingest,
serves RTMP/HLS/WebRTC playback.

Install: download binary, run `./mediamtx`. Accepts RTMP at rtmp://localhost/live.
The engine streams to `rtmp://localhost/live/test`.

### Verify Path
```
testsrc2 (lavfi) --> Engine (FFmpeg subprocess) --> RTMP out
                                                      |
                                                      v
                                              MediaMTX (localhost)
                                                      |
                                           +----------+----------+
                                           |                     |
                                     ffprobe/ffplay          cockpit WS
                                     (pull RTMP back)     (health metrics)
```

Verification steps:
1. `ffprobe rtmp://localhost/live/test` — confirms stream exists, shows codec/resolution/fps
2. `ffplay rtmp://localhost/live/test` — visual confirm (if display available; skip on VPS)
3. Cockpit WS health endpoint — confirms bitrate, frame count, uptime arrive
4. Stop API call — confirms FFmpeg process terminates cleanly, no orphans

---

## Concrete File Plan

### New files (each annotated with sibling it mirrors)

| New File | Mirrors | Purpose |
|----------|---------|---------|
| `adapters/broadcast/__init__.py` | — | Package marker |
| `adapters/broadcast/engine.py` | `adapters/capabilities/goose_harness.py` (harness pattern) + `substrate/organism/workcell_daemon.py` (lifecycle pattern) | FFmpeg subprocess lifecycle: spawn via gated_popen, monitor, health parse, teardown, orphan kill |
| `adapters/broadcast/ffmpeg_args.py` | — (new, no sibling) | Translate SourceConfig + OutputProfile into FFmpeg CLI args list. Pure function, no side effects. |
| `transports/api/cockpit_broadcast_routes.py` | `transports/api/cockpit_rooms_routes.py` | FastAPI router: HTTP endpoints (start/stop/configure/status) + WS endpoint (health push). Pydantic models defined locally. |
| `cockpit/src/renderer/stores/broadcastStore.ts` | `cockpit/src/renderer/stores/visionStore.ts` | Zustand store: BroadcastState interface, initial constants, setters |
| `cockpit/src/renderer/panels/BroadcastPanel.tsx` | `cockpit/src/renderer/panels/VisionPanel.tsx` | Panel component: status display, start/stop controls, health metrics |
| `cockpit/src/renderer/api/broadcast-ws.ts` | `cockpit/src/renderer/api/vision-ws.ts` | WS client: BroadcastWsClient class, event types, command methods |
| `cockpit/src/renderer/hooks/useBroadcastConnection.ts` | `cockpit/src/renderer/hooks/useVisionConnection.ts` | Connection hook: singleton client, event subscriptions, polling, cleanup |
| `cockpit/src/renderer/components/broadcast/BroadcastControls.tsx` | `cockpit/src/renderer/components/vision/CameraController.tsx` | Control sub-component: source picker, output config, start/stop buttons |
| `cockpit/src/renderer/components/broadcast/HealthDisplay.tsx` | — (new, health-specific) | Real-time health metrics: bitrate bar, dropped frames, uptime, status tier |

### Edited files (minimal, all permitted)

| Existing File | Edit | Lines Added |
|---------------|------|-------------|
| `cockpit/src/renderer/stores/cockpitStore.ts` | Add `'broadcast'` to Panel union | 1 |
| `cockpit/src/renderer/types/routes.ts` | Add broadcast route entry + union member | 2 |
| `cockpit/src/renderer/components/Shell.tsx` | Import BroadcastPanel + add case | 3 |
| `transports/api/cockpit.py` | Add `_mount_broadcast_router()` lazy-load | ~6 |

### Plan path adjustments

The original plan listed `substrate/broadcast/models.py` for Pydantic models.
**Adjustment:** For Slice 0, define models locally in `cockpit_broadcast_routes.py`
(matching the rooms pattern). Extract to substrate/broadcast/ only if models grow
complex in later waves. This avoids touching the substrate layer entirely for Slice 0.

---

## Proof Topology Summary

```
SOURCE:  FFmpeg lavfi testsrc2 (synthetic, no device needed)
ENGINE:  adapters/broadcast/engine.py (FFmpeg subprocess on VPS)
INGEST:  MediaMTX binary (local RTMP server, single binary, no cloud)
VERIFY:  ffprobe pull + cockpit WS health metrics
```

STOPPED. Awaiting execute instruction.
