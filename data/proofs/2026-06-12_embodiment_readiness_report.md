# Vision Productionization — Embodiment Readiness Report

**Date:** 2026-06-12
**Beast:** Insta360 Link 2 on GTX 1080 Ti (windows-desktop)
**Relay:** umh-vision-relay.service on VPS (srv1500858)
**Cockpit:** umh-cockpit.fly.dev v228

---

## Phase Results

### Phase 1: Vision Truth Model Audit
**Status: WORKING — REAL HARDWARE VERIFIED**

StatusHud 8-chip display verified on live cockpit:
VIDEO, CONTROL, PTZ, DETECTOR, TRACKER, GPU, DEVICE, PRESETS.
Detector shows `yolov8n` model, `cuda-infer/cpu-nms` device, NMS fallback visible.
Active tracks and total tracks displayed. Consecutive errors counter at 0.

### Phase 2: Tracking Foundation
**Status: WORKING — REAL HARDWARE VERIFIED**

IoU tracker running on Beast with greedy matching (threshold 0.25).
Live verification: `active_tracks=1, total_tracks=2` (person detected and tracked).
Velocity tracking, max 30 lost frames, first_seen/last_seen in overlay data.
SceneInventory shows detected objects as tappable chips.

### Phase 3: Autonomous Camera Foundation
**Status: WORKING — CODE VERIFIED ONLY**

Authority stack implemented: operator > voice > ai > autonomous.
CameraModeSelector with Manual | Follow | Watch modes.
AI Assist defaults OFF, operator always overrides.
Authority audit log in DiagnosticsPanel shows from→to transitions.
**Not hardware-verified:** Follow/Watch modes require manual cockpit interaction.

### Phase 4: Detection Pipeline Hardening
**Status: WORKING — REAL HARDWARE VERIFIED**

- OpenCV 4.13 imencode regression fixed: explicit `int()` cast on encode params (commit `393a5449`)
- DirectShow probe crash fixed: WMI-only enumeration for default `list_devices`, DirectShow only on `validate=true` (commit `dec89d3f`)
- Beast daemon stable through 10+ device-poll cycles (30s interval) without crashing
- `detect_interval=5.0s`, `avg_inference_ms=455.1ms`, `consecutive_errors=0`

### Phase 5: Frame Pipeline Observability
**Status: WORKING — REAL HARDWARE VERIFIED**

Pipeline latency measurement: capture_timestamp → relay_receive → cockpit_render.
DiagnosticsPanel shows capture→relay, relay→render, end-to-end with color coding.
Clock-skew between Beast/VPS detected and handled: negative values clamped to 0 (commit `f331b771`).
Frame count climbing steadily: 2fps verified (8 frames per 4s window).

### Phase 6: Camera Command Validation
**Status: WORKING — REAL HARDWARE VERIFIED**

Command telemetry recording: rolling 100-entry log with id, operation, sent_at, rtt_ms, success/error.
WS endpoint `command_log` + HTTP `/commands` both verified.
Live data: 440+ total commands, camera.status RTT 350-760ms.
DiagnosticsPanel shows last 8 commands with color-coded RTT.
Dispatch counters in health: dispatch_total, dispatch_ok_count, dispatch_fail_count.

### Phase 7: Object-Centric Control Foundation
**Status: WORKING — CODE VERIFIED ONLY**

SceneInventory component renders detected objects as chips.
Long-press-to-look-at planned for Follow mode.
**Not hardware-verified:** Requires manual cockpit interaction to test tap→PTZ flow.

### Phase 8: Vision Memory Foundation
**Status: WORKING — REAL HARDWARE VERIFIED**

Vision event stream: rolling 500-event history.
WS endpoint `vision_events` + HTTP `/events` both verified.
38 events recorded: viewer_connected, viewer_disconnected, fault_inject, etc.
DiagnosticsPanel shows last 8 events with timestamps and type coloring.
Events include detail payloads (e.g., `{"viewers": 1}`).

### Phase 9: Failure Injection
**Status: WORKING — REAL HARDWARE VERIFIED**

4 injectable faults verified on live hardware:
- `drop_frames`: Stops all frame delivery. Verified: 8 frames/4s → 0 frames/4s → 9 frames/4s after clear.
- `block_commands`: Blocks relay→Beast dispatch. Returns None with `fault_injected` error.
- `fake_detector_offline`: Nulls detector_status in frame broadcast.
- `high_latency`: Adds 500ms sleep to broadcast_frame.

WS control: `fault_inject` message toggles, `fault_status` queries.
Health payload: `active_faults` dict shows currently active faults.
All faults inject and clear cleanly. Recovery is immediate.

### Phase 10: Embodiment Readiness Report
**Status: THIS DOCUMENT**

---

## Hardware Verification Summary

| Phase | Status | Verified On |
|-------|--------|-------------|
| 1. Truth Model | REAL HARDWARE | Live cockpit + relay health |
| 2. Tracking | REAL HARDWARE | 1 active track, 2 total |
| 3. Authority Stack | CODE ONLY | Needs manual UI test |
| 4. Detection Hardening | REAL HARDWARE | Daemon stable 10+ cycles |
| 5. Pipeline Observability | REAL HARDWARE | Frames flowing, latency measured |
| 6. Command Telemetry | REAL HARDWARE | 440+ commands, RTT recorded |
| 7. Object Control | CODE ONLY | Needs manual tap test |
| 8. Event Stream | REAL HARDWARE | 38 events, WS+HTTP verified |
| 9. Failure Injection | REAL HARDWARE | 4/4 faults tested on live pipeline |
| 10. Readiness Report | COMPLETE | This document |

**8/10 phases REAL HARDWARE VERIFIED. 2/10 CODE VERIFIED ONLY (require manual cockpit interaction).**

---

## Commits

| Hash | Description |
|------|-------------|
| `3b02cf10` | vision pipeline observability + event stream + enhanced diagnostics |
| `c045514f` | command telemetry + failure injection |
| `393a5449` | cast imencode params to int for OpenCV 4.13 compat |
| `dec89d3f` | skip DirectShow probe in list_devices unless validate=true |
| `f331b771` | clamp negative pipeline latency from cross-machine clock skew |

---

## Known Issues

1. **Clock skew:** Beast system clock ~300ms ahead of VPS. capture_to_relay_ms clamped to 0. Fix: NTP sync both machines, or use relative frame-to-frame timing.
2. **Dispatch fail ratio:** 50% of dispatches fail during daemon startup (before camera module initializes). Steady-state ratio is 100% OK.
3. **DirectShow still crashes on validate=true:** WMI-only is the safe path. Full device validation with DirectShow should only be used manually.

## Embodiment Readiness

The vision pipeline is production-ready as a foundation for embodied operation:

- **Perception:** YOLOv8n running on CUDA with IoU tracking
- **Telemetry:** Every command logged, every event recorded, pipeline latency measured
- **Resilience:** Fault injection proves graceful degradation
- **Authority:** Stack exists for operator→AI handoff
- **Observability:** DiagnosticsPanel provides full operator visibility

**Next steps for embodiment:**
1. Follow/Watch mode live testing on cockpit
2. Object-centric PTZ (tap object → camera follows)
3. AI-initiated camera movements (detection → autonomous PTZ)
4. Voice command integration for camera control
