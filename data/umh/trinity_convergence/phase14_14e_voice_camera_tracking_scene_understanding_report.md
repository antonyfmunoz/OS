# Phase 14.14E — Voice Camera Control, Object Tracking & Scene Understanding

**Date:** 2026-06-09
**Baseline:** Phase 14.14D (cockpit camera controller, PTZ, quality modes, stream metrics)
**Status:** SHIPPED

---

## Summary

Phase 14.14E upgrades DEX Vision from a camera control surface into a
voice-controlled, grounded visual perception system. DEX can now control
the camera through natural voice, detect and track objects, maintain a
scene model, answer visual queries with confidence scores, and watch
items for changes — all governed by strict privacy rules that prevent
hallucinated visual claims.

---

## Workcell Results

### A — Voice Camera PTZ Control
**Result:** PASS
- Voice commands: move camera left/right/up/down, pan left, tilt up
- Modifier support: "a little" (half step), "more" (double step)
- Zoom in/out with modifiers
- Center camera / stop moving
- All commands route deterministically (no LLM) via regex patterns
- 14 PTZ voice tests pass

### B — Voice Preset Control
**Result:** PASS
- "look at me/keyboard/desk/room/hands/monitor" → preset apply
- "save this preset as X" → save current PTZ position
- "update the desk preset" → update existing preset
- "what preset am I on" / "show my camera presets" → status query
- 6 preset voice tests pass

### C — Visual Scene Model
**Result:** PASS
- `vision_scene.py` — canonical scene state with frame ID, timestamp, detected objects, regions, summary
- Scene expiry after 5 minutes (SCENE_EXPIRY_S = 300)
- Object lookup by label or track_id
- Visible object filtering
- Scene serialization (to_dict/from_dict)
- 5 scene state tests pass

### D — Object/Item Detection
**Result:** PASS
- 15 initial object classes: person, face, hands, keyboard, mouse, phone, notebook, pen, cup/bottle, headphones, monitor, laptop, paper/document, camera/tripod, unknown
- Detection from VLM analysis (deterministic keyword extraction from VLM output)
- Confidence scores on every detection
- "Unknown means unknown" principle enforced
- 3 detection tests pass

### E — Object Tracking
**Result:** PASS
- Tracking states: visible, likely_visible, lost, occluded, moved, stationary, unknown
- Start/stop tracking by label
- Track undetected items (starts as "unknown" status)
- Lost detection after 30 seconds without visibility
- Max 50 tracked objects
- 5 tracking tests pass

### F — Operator-Labeled Items
**Result:** PASS
- "this is my notebook" / "remember this as my work phone" → label_item
- Operator confirmation required (operator_confirmed=True)
- Labels persist in memory for session duration
- 3 labeling tests pass

### G — Visual Query Handler
**Result:** PASS
- `vision_query.py` — grounded visual question answering
- No visual answer without frame/scene data
- Camera off → explicit blocker ("Camera is not active")
- Found object → confidence and timestamp included
- Not found → "I haven't seen X in the current scene"
- VLM analysis for "what do you see?" with deterministic fallback
- 6 visual query tests pass

### H — Vision Model Dispatch
**Result:** PASS
- VLM called only for semantic analysis ("what do you see?", "what is on my desk?")
- Deterministic object extraction from VLM output text
- Scene state updated after VLM analysis
- Fallback: "Frame captured but analysis unavailable"
- 2 dispatch tests pass

### I — Item Watch Mode
**Result:** PASS
- Explicit opt-in required (privacy gate)
- Watch conditions: moved, disappeared, appeared, activity_changed
- Auto-expiry after 60 minutes
- Max 10 concurrent watches
- Voice commands: "watch my phone", "tell me if my notebook disappears", "keep an eye on this"
- Stop: "stop watching my phone"
- 9 watch mode tests pass

### J — Auto-Framing / Follow Mode
**Result:** PASS
- Explicit activation required ("follow me" / "keep me centered")
- Target tracking by label or "operator" default
- Stop command: "stop following"
- Active state visible in cockpit UI
- 8 follow mode tests pass

### K — Visual Memory Boundaries
**Result:** PASS
- Scene state ephemeral (in-memory only, expires in 5 minutes)
- No persistent frame storage (latest-frame buffer only)
- No face recognition, emotion detection, health diagnosis
- No biometric memory storage
- Forbidden claims list enforced: identity, emotion, health, age, gender, ethnicity, biometric
- 12 tracking privacy rules defined
- 11 privacy tests pass

### L — Cockpit Tracking UI
**Result:** PASS
- `TrackingPanel.tsx` component integrated into CameraController
- Scene summary display with age indicator
- Follow mode toggle button
- "What Do You See?" analysis button
- Detected objects list with confidence percentages
- Tracked items list with status colors and stop buttons
- Label item input
- Watch mode list with stop buttons
- Visual query input ("Where is my...?")
- All state synced via 5-second scene polling

### M — Voice + Tracking Commands
**Result:** PASS
- 10 voice+tracking integration tests pass
- Commands route through command_router → camera_commands → vision relay → scene manager
- Deterministic classification — no LLM dependency in routing
- Beast target detection for all tracking commands

### N — Tests
**Result:** 106 tests pass, 0 fail
- TestVoiceCameraPTZ: 14 tests
- TestVoiceCameraRouting: 6 tests
- TestVoicePresetControl: 6 tests
- TestVoiceQualityMode: 6 tests
- TestSceneState: 5 tests
- TestObjectDetection: 3 tests
- TestObjectTracking: 5 tests
- TestOperatorLabeling: 3 tests
- TestVisualQueries: 6 tests
- TestVisionModelDispatch: 2 tests
- TestWatchMode: 9 tests
- TestFollowMode: 8 tests
- TestVisionPrivacy14E: 11 tests
- TestVoiceTrackingCommands: 10 tests
- TestSceneManagerState: 2 tests
- TestBackwardCompatibility: 10 tests

Original Phase 14.14B tests: 46/46 pass (zero regressions)

---

## Files Changed

### New Files (4)
- `substrate/workstation/vision_scene.py` — scene model, tracking, watch, follow (380 lines)
- `substrate/workstation/vision_query.py` — grounded visual query handler (210 lines)
- `cockpit/src/renderer/components/TrackingPanel.tsx` — tracking UI component (250 lines)
- `tests/test_vision_14e.py` — 106 tests

### Modified Files (8)
- `substrate/workstation/camera_commands.py` — extended with PTZ, zoom, quality, tracking, watch, follow, label commands
- `substrate/workstation/command_router.py` — 40+ new camera control signals
- `substrate/workstation/voice_route_resolver.py` — 18 new camera target patterns
- `substrate/workstation/vision_privacy.py` — tracking privacy rules, forbidden claims, new validation gates
- `umh/vision_relay.py` — 12 new message handlers + scene manager integration
- `cockpit/src/renderer/api/vision-ws.ts` — tracking types + 10 new client methods
- `cockpit/src/renderer/stores/visionStore.ts` — tracking state + scene state
- `cockpit/src/renderer/hooks/useVisionConnection.ts` — scene event handlers + 5s polling
- `cockpit/src/renderer/components/CameraController.tsx` — TrackingPanel integration
- `cockpit/src/renderer/panels/VisionPanel.tsx` — expanded voice commands reference + tracking status

---

## Privacy Governance

### Structural Constraints (code-enforced, not configurable)
1. Camera OFF by default
2. No face recognition / identity matching
3. No emotion / mood / health claims
4. No persistent frame storage
5. No hidden recording
6. Tracking requires explicit operator command
7. Watch mode requires explicit opt-in
8. Watch mode auto-expires (60 minutes)
9. Follow mode requires explicit activation
10. Scene state expires (5 minutes)
11. No biometric memory
12. Lost objects reported as "lost", never guessed

### Forbidden Claim Types
- identity_recognition
- emotion_detection
- health_diagnosis
- age_estimation
- gender_classification
- ethnicity_classification
- biometric_storage

---

## Remaining Limitations

1. **Object detection** depends on VLM keyword extraction — not a dedicated CV model.
   A local YOLO/SAM detector would significantly improve detection accuracy and speed.
2. **Follow mode** dispatches commands but actual camera movement depends on Beast
   PTZ hardware. No closed-loop visual servoing yet (requires WebRTC or faster frames).
3. **Watch mode notifications** are logged but not yet wired to Discord/cockpit push
   notifications. The event triggers exist; delivery is a transport concern.
4. **Scene graph regions** (keyboard area, desk area) are defined in the data model
   but not yet populated by the detector. Needs spatial reasoning from VLM.

---

## Recommended Next Phase

**Phase 14.14F — Local CV Model + WebRTC Upgrade**
- Deploy lightweight YOLO model on Beast for real-time object detection
- WebRTC upgrade for sub-second latency follow mode
- Spatial region mapping from detector bounding boxes
- Watch mode notification delivery via cockpit push + Discord

---

## Verdict

### SHIPPED

All acceptance criteria met:
- Voice camera movement works (14 tests)
- Voice zoom works (4 tests)
- Voice presets work (6 tests)
- "What do you see?" grounded in real frame (VLM analysis with deterministic fallback)
- Scene state exists (VisionScene with frame_id, timestamp, confidence)
- Detected items include confidence (0.0-1.0 scores)
- Item tracking works for visible objects (start/stop/status lifecycle)
- Lost items reported as lost (30s threshold, never guessed)
- Operator-labeled items require confirmation (operator_confirmed=True)
- Watch mode requires explicit opt-in (privacy gate)
- Follow mode requires explicit activation (privacy gate)
- Tracking UI shows detected/tracked items (TrackingPanel component)
- No hidden recording (structural privacy rules)
- No identity/emotion claims (forbidden claims list)
- Final report exists (this document)
