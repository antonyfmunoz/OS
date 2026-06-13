# Broadcast Subsystem — Slice 0 Proof Report

**Date**: 2026-06-12
**Branch**: worktree-broadcast-subsystem
**Status**: ALL PASS

---

## Files Created (9 new)

### Python Engine (Zone C — adapters/broadcast/)
| File | Lines | Purpose |
|------|-------|---------|
| `adapters/broadcast/__init__.py` | 0 | Package marker |
| `adapters/broadcast/process_lifecycle.py` | 173 | Subsystem-agnostic subprocess lifecycle (process group isolation, SIGTERM→SIGKILL teardown, CPU gate) |
| `adapters/broadcast/ffmpeg_args.py` | 104 | Pure function: config → FFmpeg CLI args (test_pattern, camera, rtmp_pull, file sources) |
| `adapters/broadcast/engine.py` | 208 | BroadcastEngine: health parsing from `-progress pipe:1`, state machine (idle/starting/live/stopping/error) |

### API Route (Zone C — transports/api/)
| File | Lines | Purpose |
|------|-------|---------|
| `transports/api/cockpit_broadcast_routes.py` | ~150 | FastAPI routers: POST /start, POST /stop, GET /status, WS /ws (1s health push) |

### Cockpit Frontend (Zone C — cockpit/src/renderer/)
| File | Lines | Purpose |
|------|-------|---------|
| `cockpit/src/renderer/api/broadcast-ws.ts` | ~80 | BroadcastWsClient wrapping WsClient, health pulse types |
| `cockpit/src/renderer/stores/broadcastStore.ts` | ~60 | Zustand store: state, health metrics, connected flag |
| `cockpit/src/renderer/hooks/useBroadcastConnection.ts` | ~30 | Module-level singleton hook, auto-connect/cleanup |
| `cockpit/src/renderer/panels/BroadcastPanel.tsx` | 176 | Full panel: header, RTMP input, start/stop, health grid (9 metrics), idle/disconnected states |

---

## 4 Edits (OLD → NEW)

### 1. cockpitStore.ts — Panel union type
```
OLD: | 'rooms'
NEW: | 'rooms'
     | 'broadcast'
```

### 2. routes.ts — Lucide import + route entry
```
OLD: Radio,
     } from 'lucide-react'
NEW: Radio,
     Cast,
     } from 'lucide-react'

OLD: (after vision route)
NEW: { id: 'broadcast', label: 'Broadcast', icon: Cast, group: 'primary', visibility: 'primary', key: 'b' },
```

### 3. Shell.tsx — Import + case
```
OLD: import { VisionPanel } from '../panels/VisionPanel'
     import { ConferenceRoomsPanel } ...
NEW: import { VisionPanel } from '../panels/VisionPanel'
     import { BroadcastPanel } from '../panels/BroadcastPanel'
     import { ConferenceRoomsPanel } ...

OLD: case 'rooms':
       return <ErrorBoundary><ConferenceRoomsPanel /></ErrorBoundary>
     default:
NEW: case 'rooms':
       return <ErrorBoundary><ConferenceRoomsPanel /></ErrorBoundary>
     case 'broadcast':
       return <BroadcastPanel />
     default:
```

### 4. cockpit.py — Router mount (6 lines)
```
NEW (after _mount_rooms_router()):
def _mount_broadcast_router() -> None:
    from transports.api.cockpit_broadcast_routes import broadcast_router as _br
    from transports.api.cockpit_broadcast_routes import broadcast_ws_router as _bws
    router.include_router(_br)
    ws_router.include_router(_bws)
_mount_broadcast_router()
```

---

## Proof Execution

### Topology
```
testsrc2 (lavfi) → BroadcastEngine (FFmpeg subprocess) → MediaMTX (RTMP :1935, same host) → ffprobe verify
```

**Egress note**: RTMP target was `rtmp://localhost:1935/live/prooftest` —
same-host MediaMTX. Cross-host egress (VPS → Beast over Tailscale WireGuard)
is DEFERRED pending MediaMTX installation on Beast.

### Exact FFmpeg invocation
```
ffmpeg -y -re -f lavfi -i testsrc2=size=1280x720:rate=30 \
  -f lavfi -i anullsrc=r=44100:cl=stereo \
  -c:v libx264 -b:v 2500k -preset veryfast -g 60 -keyint_min 60 \
  -profile:v high -level 4.1 -pix_fmt yuv420p \
  -c:a aac -b:a 128k -ar 44100 \
  -f flv -progress pipe:1 -stats_period 1 \
  rtmp://localhost:1935/live/prooftest
```

### Results

| Step | Description | Result |
|------|-------------|--------|
| 1 | Start MediaMTX (RTMP :1935) | **PASS** — pid=3875350 |
| 2 | Start BroadcastEngine | **PASS** — pid=3875371, state=live |
| 3 | Health metrics (5s collection) | **PASS** — 5 snapshots, fps=29.01, 2206kbps, 0 drops, tier=HEALTHY |
| 4 | ffprobe RTMP pull-back | **PASS** — codec=h264, 1280x720, 30/1 fps |
| 5 | Stop + orphan check | **PASS** — exit=255 (SIGTERM), 0 orphan ffmpeg |
| 6 | Restart + re-verify | **PASS** — new pid=3875508, frames=57, 0 orphans after 2nd stop |

### ffprobe output
```json
{
  "streams": [{
    "codec_name": "h264",
    "codec_type": "video",
    "width": 1280,
    "height": 720,
    "r_frame_rate": "30/1"
  }]
}
```

### Health snapshot at proof time
```json
{
  "frame": 118,
  "fps": 29.01,
  "bitrate_kbps": 2205.9,
  "drop_frames": 0,
  "out_time_ms": 4527891,
  "speed": "1.11x",
  "total_size_bytes": 1248535,
  "uptime_s": 5.0,
  "drop_percentage": 0.0,
  "status_tier": "HEALTHY"
}
```

---

## Compliance Verification

| Check | Result |
|-------|--------|
| No GPL expression in Zone C code | **CLEAN** — zero OBS/GPL references |
| No libav* linking | **CLEAN** — engine invokes `ffmpeg` CLI via subprocess only |
| CPU gate compliance | **CLEAN** — ProcessLifecycle calls cpu_gate_check() before spawn, uses asyncio.create_subprocess_exec |
| No raw subprocess in adapters/ | **CLEAN** — no subprocess.run/Popen/call/check_output |
| Core untouched | **CLEAN** — substrate/ has zero diffs |
| Architecture layer correct | **CLEAN** — engine in adapters/, routes in transports/, UI in cockpit/ |

---

## Known Limitation

- **Exit code 255**: FFmpeg returns 255 on SIGTERM (normal for interrupted streams). Engine handles this correctly — state is already "stopping" before kill, so on_exit does not transition to "error".
- **-re flag required**: Added to test_pattern source to pace lavfi output at real-time rate. Without it, FFmpeg blasts frames at CPU speed, causing RTMP disconnects.

---

---

## Post-Slice 0 Validation (2026-06-12)

### Agent-Drive Go-Live (CapabilityHandler path)
| Check | Result |
|-------|--------|
| BroadcastCapabilityHandler implements Protocol | **PASS** — 4 methods |
| IntegrationManifest registered (zero core edits) | **PASS** |
| CapabilityRequest → engine start → RTMP push | **PASS** |
| CapabilityRequest → engine stop → clean teardown | **PASS** |
| CapabilityRequest → status → health dict | **PASS** |
| ProcessLifecycle stale exit callback fix | **PASS** — 7/7 tests |
| ProcessLifecycle SIGKILL wait timeout | **PASS** |
| ProcessLifecycle concurrent lock | **PASS** |
| ProcessLifecycle monitor race fix | **PASS** |
| Engine-level asyncio.Lock | **PASS** |

### Cockpit Human Path (HTTP + WS)
| Check | Result |
|-------|--------|
| Panel renders (IDLE state) | **PASS** — Playwright snapshot |
| Start Stream → state flips to LIVE | **PASS** — WS pulse confirmed |
| Health metrics live (FPS 30.0, Bitrate 4503 kbps) | **PASS** |
| ffprobe confirms H.264 High, 1920x1080, 30fps | **PASS** |
| Stop Stream → state returns to IDLE | **PASS** |
| Zero orphan ffmpeg after stop | **PASS** |
| WS auth bug fixed (sync function was awaited) | **PASS** |

### Dual-Consumer Thesis
Same HTTP routes + WS health push consumed by both agent cells
(CapabilityHandler) and humans (cockpit panel). Both paths proven
independently through the same engine singleton.

### Egress Status
| What | Status |
|------|--------|
| Agent-drive pipeline (testsrc2 → H.264 → RTMP) | **PROVEN** |
| Cockpit human path (UI → API → engine → RTMP) | **PROVEN** |
| SSRF output URL validator | **PROVEN** |
| ProcessLifecycle fixes (4 fixes, 7 tests) | **PROVEN** |
| Cross-host egress (VPS → Beast WireGuard) | **DEFERRED** — Beast MediaMTX pending |

---

## OVERALL: PASS — Slice 0 proven end-to-end
