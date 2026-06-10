# Phase 14.18B — Live PTZ + Overlay Field Fix Report

**Date**: 2026-06-10
**Status**: DEPLOYED — awaiting live field trial
**Verdict standard**: "When I move my finger, the camera moves with it. When UMH tracks something, I see it on the stream."

---

## Root Cause Analysis

### Joystick "single click" behavior
D-pad buttons called `startDirectionMotion()` which sent `ptzStartMotion` but never
created the 50ms update timer. The relay's server-side guard killed motion after the
guard timeout (previously 500ms) because no `ptzUpdateMotion` messages arrived.
Additionally, the relay's `_dispatch_to_beast()` used blocking `urllib.request.urlopen`
inside the async event loop, starving frame delivery at 20Hz motion ticks. Step deltas
used `int()` truncation with a scale of 3, producing zero-pixel moves at low velocities.

### Overlay invisibility
Complete 5-layer break:
1. VisionOverlay component existed but was never mounted in CameraController
2. visionStore had no `overlays` field
3. vision-ws had no `vision_overlay` event type
4. useVisionConnection had no overlay event handler
5. Relay extracted overlays from frame metadata but never broadcast them

---

## Fixes Applied (6 files, 461 insertions)

### Track 1 — Continuous PTZ (CameraController.tsx + vision_relay.py)

| Fix | Before | After |
|-----|--------|-------|
| D-pad update timer | Missing — motion dies on guard timeout | `ensureUpdateTimer()` creates 50ms setInterval for all motion |
| Zoom update timer | Missing | `startZoomMotion` creates own update interval |
| Guard timeout | 500ms | 2000ms (client sends `durationGuardMs: 2000`) |
| Relay dispatch | Blocking urllib in async loop | `run_in_executor(None, sync_fn)` — non-blocking |
| Step delta | `int()` truncation, scale=3 | `round()`, scale=8 (zoom scale=10) |
| Motion stop | `pass` (noop) | Sends zero-delta command to Beast |
| Combined dispatch | Separate pan/tilt and zoom per tick | Single combined dispatch per tick |

### Track 2 — Overlay Pipeline (6 layers wired)

| Layer | File | Change |
|-------|------|--------|
| 1. Mount | CameraController.tsx | `<VisionOverlay>` mounted as sibling to `<img>` |
| 2. Store | visionStore.ts | `overlays`, `overlayVisible`, `diagnosticOverlay` fields |
| 3. WS event | vision-ws.ts | `vision_overlay` event type + `setDiagnosticOverlay()` method |
| 4. Handler | useVisionConnection.ts | `vision_overlay` → `setOverlays()` + chain health update |
| 5. Relay broadcast | vision_relay.py | `broadcast_frame()` sends `vision_overlay` JSON alongside binary JPEG |
| 6. Diagnostic mode | vision_relay.py | 4Hz synthetic overlay loop with sweeping boxes |

### Track 3 — Controller Diagnostics (CameraController.tsx)

Diagnostic panel visible during active motion showing: motion_id, state, velocity
vector (pan/tilt/zoom), speed, update interval, joystick state, last command age,
guard kills.

### Track 4 — UI Toggles (CameraController.tsx)

- **OVR** button: toggle overlay visibility (green when active)
- **DIAG** button: toggle diagnostic overlay mode (warning/orange when active)

---

## Security Regression Check (Workcell K)

| Constraint | Status |
|-----------|--------|
| No camera frames without auth | PASS — `_check_auth()` at line 405 enforced before WS session |
| No overlay events without auth | PASS — same authenticated WS connection |
| No PTZ without allowed operator | PASS — Clerk JWT + `ALLOWED_CLERK_USER_IDS` enforced at API layer |
| No public ports reopened | PASS — relay on 0.0.0.0:8097 behind Tailscale, auth-gated |
| No secret token in URL | PASS — auth via WS subprotocol header, not URL |
| No hidden recording | PASS — no frame-to-disk writes in relay |
| No runaway PTZ | PASS — guard timeout kills motion, emergency stop on blur/visibility |
| Stop/off always available | PASS — E-Stop button, window blur handler |
| Diagnostic overlay distinguishable | PASS — DIAG button shows warning color, synthetic boxes labeled |
| Unauthenticated users blocked | PASS — 4001 close + "authentication required" on invalid auth |

---

## Test Coverage

85 tests pass across 6 test classes:
- `TestMotionLoopFixes` (7): non-blocking dispatch, round vs int, step scale, guard timeout, combined dispatch
- `TestOverlayChain` (7): component mount, toggle buttons, relay forwarding, store fields, WS events
- `TestControllerContinuousMotion` (6): D-pad timer, zoom timer, guard timeout, pointer capture, touch-none, blur stop
- Plus 65 existing Phase 14.18 tests: zero regression

---

## Deployment

- Cockpit: deployed to Fly.io (`umh-cockpit`) — machine e826d04fd69568 healthy
- Operator: `docker restart os-operator` — clean startup, 8 runtimes registered
- Branch: merged `worktree-phase-14-14b-vision` → main

---

## Remaining for Live Field Trial (Workcell M)

The operator needs to verify on a real device:
1. Touch joystick, hold finger — camera moves continuously
2. Release finger — camera stops immediately
3. D-pad: press and hold Up — camera tilts continuously
4. Zoom: hold In — camera zooms continuously
5. E-Stop: camera halts from any motion state
6. DIAG button: synthetic boxes appear and sweep
7. OVR button: toggles overlay visibility
8. Diagnostics panel: shows live motion_id, velocity, state during motion
9. Tab away / window blur: motion stops automatically
