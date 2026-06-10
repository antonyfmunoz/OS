# Phase 14.18 — Camera Default-On Experience + Realtime PTZ Control Loop + Smooth Vision UX

**Date:** 2026-06-10
**Status:** SHIPPED
**Phase:** 14.18 (builds on 14.17 reliability hardening)

## Executive Summary

Transforms the vision system from manual-start-per-session to a camera-default-on experience gated by Clerk authentication and profile policy. Replaces click-per-nudge PTZ with a realtime continuous motion protocol using a 20Hz server-side motion loop with guard timeouts and emergency stop. Adds smooth preset transitions via smoothstep interpolation.

## Verdict Criteria — All Met

| Criterion | Status |
|-----------|--------|
| Auth-gated default-on — camera starts on cockpit open | PASS |
| CAMERA LIVE indicator visible when active | PASS |
| One global stream (no duplicate sessions) | PASS |
| Continuous press-and-hold D-pad + joystick | PASS |
| Immediate stop on button release | PASS |
| No runaway motion (guard timeout + emergency stop) | PASS |
| DEX voice commands for continuous/stop/default-on | PASS |
| All 65 Phase 14.18 tests pass | PASS |

## Workcell Deliverables

### A: Camera Default-On Policy

- `validate_default_on_activation()` in `substrate/workstation/vision_privacy.py`
- Profile-based policy: `active_day=on, deep_work=off, creative_build=on, admin_ops=off, away/night/shutdown=off`
- Operator override allows enabling for blocked profiles
- Auth-gated: Clerk `<SignedIn>` wrapper means `useVisionConnection` only runs for authenticated operators
- `shouldAutoStartCamera()` in vision store checks policy before auto-start

### B: Single Global Session

- Singleton `_client` pattern in `useVisionConnection` — one WebSocket per cockpit
- `_broadcast_session_state()` in relay broadcasts viewer count
- Auto-stop when last viewer disconnects

### C+D: Realtime PTZ Motion Protocol + Beast Motion Loop

- Server-side 20Hz async motion loop in `umh/vision_relay.py`
- `_start_motion()` / `_update_motion()` / `_stop_motion()` functions
- Guard timeout (500ms default) auto-stops motion if no updates received
- Dispatches `camera.set_position_relative` to Beast at each tick
- Motion state broadcast to all connected viewers
- Motion ack with stop latency measurement

### E: Controller UI Upgrade

- Press-and-hold D-pad via pointer events (pointerdown/up/cancel/leave)
- 64px circular joystick with 0.15 deadzone, pointer capture, 50ms update interval
- Press-and-hold zoom buttons
- Emergency stop on window blur + visibilitychange
- Speed slider (0.2x to 3x)
- CAMERA LIVE indicator banner with motion state

### F+G: Smooth Preset Transitions + Zoom Smoothing

- `_smooth_preset_transition()` in relay uses smoothstep interpolation (`t^2 * (3-2t)`)
- Gets current position, computes delta to target, runs 20Hz interpolation loop
- Duration configurable (0.3s to 3s, default 1s)
- Falls back to instant jump if current position unavailable or delta is small
- Cancels any active motion before starting transition
- Frontend `setPreset()` passes `smooth=true` by default

### H: Latency and Smoothness Metrics

- Control metrics tracked in vision store: ptzLoopCadenceHz, stopLatencyMs, guardTimeouts
- `ptz_motion_state` events carry loop cadence and guard timeout count
- `ptz_motion_ack` events enable stop latency calculation
- Metrics displayed in CameraController UI

### I: Reconnect Safety

- Disconnect handler zeros all motion state, sets state to 'disconnected'
- Guard timeout (server-side) auto-stops motion if WebSocket drops silently
- Reconnect handler resets motion to 'idle'
- Emergency stop fires on window blur/visibilitychange

### J+K: Security Regression + DEX Voice Alignment

- 8 new regex patterns in `camera_commands.py`:
  - `_CONTINUOUS_MOTION_PATTERN` — "keep moving left", "keep panning right", "keep tilting up"
  - `_CONTINUOUS_ZOOM_PATTERN` — "keep zooming in", "continuously zoom out"
  - `_STOP_MOTION_PATTERN` — "stop moving", "stop camera motion"
  - `_STOP_ZOOM_PATTERN` — "stop zoom", "stop zooming"
  - `_DEFAULT_ON_ENABLE_PATTERN` — "keep camera on by default", "enable camera default-on"
  - `_DEFAULT_ON_DISABLE_PATTERN` — "disable camera default-on", "turn off camera default"
  - `_WHY_CHOPPY_PATTERN` — "why is the camera choppy", "camera is laggy"
  - `_WHY_NOT_LIVE_PATTERN` — "why isn't the camera live", "camera not on"
- `classify_camera_command()` updated with all 8 new handlers
- Priority ordering: security > stop_motion > stop_zoom > default_on > diagnostics > continuous_motion > continuous_zoom > existing commands
- Existing commands unaffected (all regression tests pass)

### L: Test Suite

- 65 tests in `tests/test_vision_14_18.py`
- 11 classes covering: default-on policy, privacy governance, continuous motion commands, stop motion commands, default-on toggle commands, diagnostic commands, existing command regression, motion state machine, smooth preset, relay message types, Beast camera relative position, pattern regex validation
- All pass

## Files Modified

| File | Changes |
|------|---------|
| `substrate/workstation/vision_privacy.py` | Default-on policy dict + validation function |
| `substrate/workstation/camera_commands.py` | 8 new patterns + classify routing for continuous/stop/default-on/diagnostic |
| `umh/vision_relay.py` | Motion loop (20Hz), smooth preset transition, session state broadcast |
| `nodes/windows/umh_node/adapters/camera.py` | `set_position_relative` for motion loop |
| `cockpit/src/renderer/stores/visionStore.ts` | Motion state, control metrics, default-on policy |
| `cockpit/src/renderer/api/vision-ws.ts` | 6 new motion methods + smooth preset flag |
| `cockpit/src/renderer/hooks/useVisionConnection.ts` | Default-on auto-start, motion/session event handlers |
| `cockpit/src/renderer/components/CameraController.tsx` | Full rewrite — press-and-hold, joystick, emergency stop, CAMERA LIVE |
| `cockpit/src/renderer/panels/VisionPanel.tsx` | Updated privacy text + voice command reference |
| `tests/test_vision_14_18.py` | 65 tests (new file) |

## Architecture Notes

- Motion protocol lives in the relay (server-side), not the frontend — decouples UI update rate from hardware command rate
- Guard timeout is the primary runaway prevention — server kills motion if client goes silent
- Smooth transitions use existing motion infrastructure (set_position), not a parallel mechanism
- Default-on is auth-gated by Clerk wrapper, not by additional token checks
