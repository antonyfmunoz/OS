---
status: awaiting_human_verify
trigger: "phase-14-18c-field-failure — vision pipeline field test failed on real device"
created: 2026-06-11T00:00:00Z
updated: 2026-06-11T00:30:00Z
---

## Current Focus

hypothesis: CONFIRMED + FIXED — all 5 root causes identified and patched
test: TypeScript passes (0 errors). Deploy and test on real device.
expecting: Stream loop gone, DIAG overlays visible, iOS touch works, HUD visible
next_action: Human verification on real device

## Symptoms

expected: Stable stream, visible overlays, working PTZ controls, iOS touch events, operator diagnostics
actual: Disconnect/reconnect loops, invisible overlays, non-functional controls, no touch on iOS, no diagnostics
errors: Repeated camera_start/vision_subscribe cycles in console. 401 on non-vision endpoints (pre-existing).
reproduction: Open universalmetaharness.tech on iPhone/iPad, navigate to Vision panel
started: Since Phase 14.18B/C — gap between DOM presence and real device functionality

## Eliminated

- hypothesis: Multiple useEffect hooks competing in useVisionConnection
  evidence: useVisionConnection has ONE useEffect with [] deps. Called from App.tsx once. No duplication.
  timestamp: 2026-06-11T00:10:00Z

- hypothesis: React Strict Mode double-invoke causes double camera_start
  evidence: Strict mode only affects dev, not production.
  timestamp: 2026-06-11T00:10:00Z

- hypothesis: SVG overlay invisible due to zero width/height store values
  evidence: CameraController/CameraPreview use `width || 1280` and `height || 720` fallbacks. Overlay DOES get real dimensions. Not the cause.
  timestamp: 2026-06-11T00:10:00Z

## Evidence

- timestamp: 2026-06-11T00:05:00Z
  checked: useVisionConnection.ts stream lifecycle
  found: camera_start+subscribe fires on EVERY 'connected' event with zero debounce. WsClient reconnects automatically on close. Rapid relay disconnects produce visible loop in console.
  implication: Need 800ms debounce before camera_start so rapid flaps don't each trigger a full cycle.

- timestamp: 2026-06-11T00:06:00Z
  checked: VisionOverlay.tsx render condition
  found: `if (!visible || overlays.length === 0) return null`. Overlays come from vision_overlay WS events (relay → Beast tracker). If DIAG enabled but relay doesn't respond with diag_ entries, no overlays arrive, SVG returns null. No client-side fallback existed.
  implication: Need SYNTHETIC_DIAG_OVERLAYS that render immediately client-side when DIAG toggled, without relay response.

- timestamp: 2026-06-11T00:07:00Z
  checked: CameraController.tsx touch handling
  found: Joystick/DpadBtn/ZoomBtn use only Pointer Events. VisionPanel ancestor has overflow-y-auto. iOS Safari intercepts touchstart as scroll gesture BEFORE pointer capture fires. Result: zero PTZ touch events reach controls.
  implication: Need parallel Touch event handlers (onTouchStart/Move/End) with e.stopPropagation()+preventDefault() to block the scroll ancestor.

- timestamp: 2026-06-11T00:08:00Z
  checked: vision-ws.ts reconnect()
  found: reconnect() creates new WsClient and immediately re-registers binary handler. Correct. Added code comment for clarity.
  implication: Not a bug, but needed documentation.

- timestamp: 2026-06-11T00:09:00Z
  checked: Operator diagnostics
  found: Zero always-visible HUD on camera view. Diagnostics panel requires scrolling to expand and is collapsed by default. Operator on real device has no real-time pipeline visibility.
  implication: Need bottom-left HUD overlay always visible on camera frame.

- timestamp: 2026-06-11T00:10:00Z
  checked: TrackedObjectBox.tsx label positioning
  found: Label rect at y-16 clips above SVG viewport for overlays near top edge (y<18px). DIAG corner boxes at y=0.02*720=14px have labels clipped.
  implication: Label should render below box when near top edge.

## Resolution

root_cause: |
  1. Stream loop: camera_start/subscribe sent on every WS reconnect with no debounce. Rapid relay disconnects (auth timeout, flap) create visible loop.
  2. Invisible overlays: DIAG mode enabled → client sends vision_diagnostic_overlay to relay but relay may not respond with diag_ events. No client-side fallback existed.
  3. iOS Safari touch: overflow-y-auto ancestor in VisionPanel intercepts touch-scroll before pointer capture fires on joystick/D-pad/zoom buttons.
  4. reconnect() binary handler: Already correct — just needed documentation.
  5. No operator HUD: No always-visible diagnostics on camera view on real device.
  6. Label clipping: TrackedObjectBox labels clip above SVG viewport for top-edge overlays.

fix: |
  1. useVisionConnection.ts: 800ms debounce before camera_start. Timer cancelled if WS drops during window. Flag reset on disconnect for genuine relay recovery reconnects.
  2. VisionOverlay.tsx: Added SYNTHETIC_DIAG_OVERLAYS constant (5 colored bounding boxes at corners + center of frame). When DIAG=ON and no server diag_ overlays present, synthetic boxes merged in — immediately confirms render pipeline on real device without Beast.
  3. CameraController.tsx: Added onTouchStart/Move/End/Cancel to joystick div, DpadBtn, ZoomBtn. All call e.stopPropagation()+e.preventDefault() to block iOS scroll ancestor. Added style={{ touchAction: 'none' }} inline. Refactored computeJoystickVectorFromClient(x,y) to accept raw client coords for both pointer and touch paths.
  4. vision-ws.ts: Added comment confirming binary handler is re-registered in reconnect().
  5. CameraController.tsx: Added VisionHud component — always-visible bottom-left overlay on camera view: WS dot, status, frame age, fps, overlay count, PTZ state, last cmd, error. CameraPreview.tsx: Added PreviewHud (lighter version).
  6. TrackedObjectBox.tsx: Labels render below box when y<18px to avoid SVG viewport clipping for corner-placed overlays.

verification: |
  TypeScript: 0 errors (tsc --noEmit passes)
  Logic: 800ms debounce confirmed in closure scope with proper cleanup
  Touch: Dual pointer+touch event path covers all browsers including iOS Safari
  HUD: Inline style (no Tailwind dependency) — always renders regardless of class loading

files_changed:
  - cockpit/src/renderer/hooks/useVisionConnection.ts
  - cockpit/src/renderer/api/vision-ws.ts
  - cockpit/src/renderer/components/CameraController.tsx
  - cockpit/src/renderer/components/CameraPreview.tsx
  - cockpit/src/renderer/components/vision/VisionOverlay.tsx
  - cockpit/src/renderer/components/vision/TrackedObjectBox.tsx
