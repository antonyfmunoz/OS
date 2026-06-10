# Phase 14.16 — Realtime Vision Overlay + Tracker Stack + Vision Preset Studio + Trigger Chain Engine

**Status:** COMPLETE
**Date:** 2026-06-10
**Branch:** worktree-phase-14-14b-vision

## Summary

Phase 14.16 transforms the cockpit vision system from "camera preview" into a full visual operating system with realtime tracking overlays, stackable independent trackers, a vision preset studio, a deterministic trigger chain engine, and governed security harden mode.

## Workcell Delivery Matrix

| Workcell | Title | Status | Files |
|----------|-------|--------|-------|
| A | Overlay Rendering | DONE | `cockpit/src/renderer/components/vision/{VisionOverlay,TrackedObjectBox,FaceTrackingOverlay,HandLandmarkOverlay,PoseSkeletonOverlay}.tsx` |
| B | Tracker Stack | DONE | `substrate/workstation/tracker_stack.py` |
| C | Beast CV Runtime | DONE | `nodes/windows/umh_node/adapters/vision_runtime.py` |
| D | Voice Commands — Overlay/Tracker | DONE | `substrate/workstation/camera_commands.py` (extended) |
| E | Voice Commands — Preset/Chain/Security | DONE | `substrate/workstation/camera_commands.py` (extended) |
| F | Command Router Integration | DONE | `substrate/workstation/command_router.py` (extended) |
| G | Vision Preset Studio (backend) | DONE | `substrate/workstation/vision_presets.py` |
| H | Trigger Chain Engine | DONE | `substrate/workstation/trigger_chains.py` |
| I | Privacy Governance Extension | DONE | `substrate/workstation/vision_privacy.py` (extended) |
| J | Security Harden Mode | DONE | `substrate/workstation/security_mode.py` |
| K | Cockpit TypeScript — Types + Store | DONE | `cockpit/src/renderer/api/vision-ws.ts`, `cockpit/src/renderer/stores/visionStore.ts` |
| L | Cockpit TypeScript — Event Handlers | DONE | `cockpit/src/renderer/hooks/useVisionConnection.ts` |
| M | Voice Route Resolver Extension | DONE | `substrate/workstation/voice_route_resolver.py` (extended) |
| N | Vision Relay Handlers | DONE | `umh/vision_relay.py` (~21 handler functions added) |
| O | Tests | DONE | `tests/test_vision_14_16.py` (82 tests) |

## Architecture Decisions

1. **Client-side overlay rendering**: Beast sends tracking metadata as JSON (normalized 0.0-1.0 coordinates). Cockpit renders SVG overlays on top of `<img>` feed. No server-side frame annotation.

2. **Deterministic chain evaluation**: No LLM in the trigger chain path. Chains fire based on event match → zone filter → confidence gate → condition evaluation → debounce → governance check.

3. **Governed security mode**: Security harden activates/deactivates through governed paths only. Saves previous state for restoration. Forbidden actions are structurally blocked (weapon targeting, doxxing, continuous recording, identity recognition of strangers).

4. **Capability-detected Beast CV runtime**: `detect_capabilities()` probes for OpenCV, MediaPipe, and ONNX Runtime. `map_capabilities_to_trackers()` determines which tracker categories are available. Missing backends gracefully degrade.

## New Substrate Modules

### `substrate/workstation/tracker_stack.py` (~244 lines)
- 11 tracker categories, 3 sensitive (face, operator_presence, unknown_person)
- TrackerStackManager: create/delete/activate stacks, enable/disable individual trackers
- MAX_ACTIVE_TRACKERS=12, capability gating, cost tracking (CPU/GPU)

### `substrate/workstation/vision_presets.py` (~328 lines)
- Full CRUD: create, rename, delete, duplicate, activate
- PTZ + ROI positioning, tracker stack association, named zones, trigger chain refs
- MAX_PRESETS=50, MAX_ZONES_PER_PRESET=20, optional JSON persistence

### `substrate/workstation/trigger_chains.py` (~395 lines)
- 12 vision events, 7 action types, auto-calculated risk from action composition
- ChainCondition with 6 operators (eq, neq, in, not_in, gt, lt)
- Debounce, confidence gate, zone filter, requires_approval gate
- Full audit trail: ChainFireRecord with timestamp, confidence, frame_id, explanation
- MAX_CHAINS=50, MAX_CHAIN_HISTORY=100

### `substrate/workstation/security_mode.py` (~219 lines)
- 9 allowed actions, 8 structurally forbidden actions
- Activate saves previous profile_mode + preset_id for restoration
- Event history with resolved/resolved_by tracking
- MAX_EVENT_HISTORY=50

## Privacy Governance

- Face tracking = bounding box + landmarks only. No identity recognition.
- Unknown persons = "unknown_person". Never identified by name.
- Operator enrollment = explicit opt-in, local-only storage.
- Gesture control = explicit opt-in, high-risk blocked.
- Trigger chain actions = validated against FORBIDDEN_SECURITY_ACTIONS.
- All chain fires = auditable with event, confidence, frame_id.
- Continuous video recording = forbidden in all modes.

## Voice Commands Added (~15 new patterns)

- Overlay: "show/hide tracking overlay", "overlays on/off"
- Trackers: "enable/disable {face|hand|pose|object|person|motion} tracking", "stop all tracking", "what are you tracking"
- Presets: "create/delete/rename preset"
- Chains: "why did that trigger fire", "disable chain"
- Security: "go security harden", "exit security mode"

## Test Coverage

82 tests across 9 test classes:
- TestTrackerStack (10 tests)
- TestVisionPresets (12 tests)
- TestTriggerChains (17 tests)
- TestSecurityMode (10 tests)
- TestOverlayPrivacy (10 tests)
- TestOverlayVoiceCommands (11 tests)
- TestOverlayCommandRouter (5 tests)
- TestOverlayVoiceRouting (5 tests)
- ChainCondition operator coverage (6 operators verified)

Zero regressions in existing tests (152 pass in test_vision.py + test_vision_14e.py).

## Verification

- All Python files: `py_compile` clean
- All TypeScript: `tsc --noEmit` clean (zero errors)
- All 82 new tests: PASS
- All 152 existing vision tests: PASS (zero regressions)
- Dependency direction: substrate modules import only from substrate
- Type coherence: no parallel types created (all new dataclasses are self-contained within their modules)
- Privacy governance: forbidden actions lists match between vision_privacy.py and security_mode.py
