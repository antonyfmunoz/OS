# Phase 14.18C / 14.19B — True PTZ Joystick + Discord-Grade Video + Overlay Rendering

## NO-GO Field Failure Summary

Operator field-tested deployed cockpit and reported NO-GO on 5 failures:

1. Joystick not functioning like a real joystick
2. Camera not continuously moving with finger drag
3. Controller feels like click/nudge instead of live PTZ
4. Stream quality not equal to Discord-level realtime video
5. Tracking overlays not visible on live stream

## Root Cause Analysis

### Joystick Failure Root Cause

The joystick was architecturally correct (continuous motion loop, velocity updates, guard timeout) but had **UX and mobile reliability gaps**:

1. **No visual thumbstick feedback** — the joystick circle showed a tiny dot at the velocity position but no draggable thumbstick that follows the finger
2. **No pointer capture release** — on pointerUp, the pointer capture was never explicitly released, causing stale capture state on mobile Safari
3. **Guard timeout too aggressive** — 500ms minimum on relay, 2000ms from cockpit. Mobile network jitter (Wi-Fi to LTE handoff) can easily exceed 500ms, causing guard timeout kills mid-drag
4. **`touch-action: none` via Tailwind class** — the `touch-none` Tailwind class is less reliable than inline `style={{ touchAction: 'none' }}` on iOS Safari, where the browser can still steal touch events for scroll/zoom gestures
5. **Small touch target** — 64px (w-16) joystick on mobile is below the recommended 44px minimum but at the edge; increased to 80px (w-20)

The PTZ motion loop itself (20Hz relay loop, relative position commands to Beast) was correctly implemented and functional.

### Stream Quality Gap Analysis

**Current architecture**: Beast captures camera via OpenCV -> base64 JPEG -> HTTP mesh dispatch -> Vision Relay (Python asyncio WebSocket) -> Cockpit (binary WebSocket frames -> Blob URL -> `<img>` element)

**Measured performance** (from previous Phase 14.18B deployment):
- Display FPS: 9.0 fps (balanced mode)
- Frame size: ~96 KB
- Transport: WebSocket binary frames
- Decode: browser JPEG decode via `<img>` element
- Buffer: RAF-gated single-frame buffer (no jitter buffer)

**Why this is not Discord-grade**:
- Discord uses WebRTC with H.264/VP8 hardware encoding, adaptive bitrate, jitter buffer, congestion control
- JPEG-over-WebSocket has no temporal compression (each frame is independent), no hardware encoder engagement, no congestion feedback
- At 15fps balanced mode, each 96KB frame = ~11.5 Mbps bandwidth (vs Discord's ~2-4 Mbps for similar quality with temporal compression)
- No frame pacing — frames arrive at network speed, not display speed
- No adaptive quality — if network degrades, frames just get stale rather than reducing quality

**Verdict**: JPEG-over-WebSocket is fundamentally limited to "good diagnostic/office monitor" quality. Discord-grade requires WebRTC or equivalent.

### Overlay Failure Root Cause

**Critical bug found**: `VisionOverlay.tsx` line 61 checked `enabledCategories.has(cat)` — but `enabledCategories` was built from `trackerStack.enabled_trackers.filter(t => t.enabled)`. When no trackers are explicitly enabled (the default state), `enabledCategories` is an **empty set**, causing ALL overlays to be filtered out, including diagnostic overlays.

This means:
- User enables DIAG overlay
- Relay sends diagnostic overlay data at 4Hz
- Cockpit receives overlay data (confirmed in store)
- VisionOverlay renders... nothing, because category filter blocks everything

Secondary issue: `CameraPreview.tsx` did not render `VisionOverlay` at all — overlays were only rendered in `CameraController.tsx`.

## Fixes Applied

### PTZ Joystick Fixes
- **True visual thumbstick**: draggable circle follows finger position with glow effect when active
- **Explicit pointer capture + release**: `setPointerCapture` on down, `releasePointerCapture` on up
- **Inline `touchAction: 'none'`**: more reliable than Tailwind class on iOS Safari
- **Larger touch target**: 80px (w-20) circle with crosshair guides
- **Vector clamping to unit circle**: prevents overdriving velocity when finger drags outside circle
- **Live vector readout**: shows x,y velocity values during drag
- **Guard timeout increased to 3000ms**: from 2000ms, giving mobile networks more headroom
- **Relay guard clamp widened to 500-5000ms**: from 200-2000ms, allowing operator to tune for their network
- **`e.preventDefault()` on all pointer events**: prevents default browser handling

### Overlay Visibility Fixes
- **Diagnostic overlays bypass category filter**: overlays with `track_id` starting with `diag_` are never filtered by tracker category
- **Real overlays pass when no trackers enabled**: `hasTrackerFilters` flag — only apply category filter when at least one tracker is explicitly enabled
- **`CameraPreview.tsx` now renders `VisionOverlay`**: overlays visible in all camera display surfaces
- **Overlay health diagnostics panel**: shows exactly why overlays are missing (no tracker runtime, no trackers enabled, DIAG mode active but no data, etc.)

### PTZ Diagnostics Panel
- **Collapsible diagnostics section**: shows joystick state, pointer capture, vector, speed, motion ID, relay loop Hz, stop latency, guard kills, coalesced commands, WebSocket state
- **Overlay diagnostics**: overlay visible toggle, diagnostic mode, overlay count, last overlay age, tracker runtime availability, enabled trackers, Beast connection, camera streaming state
- **Blocker explanation**: natural language explanation of why overlays are missing

### Relay Improvements
- **Coalesced commands broadcast**: relay now sends `coalesced_commands` in motion state broadcasts
- **Periodic motion state updates**: relay broadcasts motion state every ~1s (every 20 loops) during active motion
- **Health report includes `diagnostic_overlay_active`**: cockpit can distinguish diagnostic vs real overlay state

## Media Plane Analysis

### WebRTC vs JPEG-over-WebSocket

| Dimension | JPEG-over-WS (current) | WebRTC (target) |
|-----------|----------------------|-----------------|
| FPS | 9-15 practical | 24-30 typical |
| Latency | 100-300ms (network + decode) | 50-150ms (hardware path) |
| Bandwidth | ~12 Mbps at 15fps/96KB | ~2-4 Mbps (temporal compression) |
| Stutter | Possible on jitter | Jitter buffer smooths |
| Mobile | Works everywhere | Needs STUN/TURN for NAT |
| Encoding | CPU JPEG (OpenCV) | Hardware H.264/VP8 |
| Quality | Readable office view | Near-realtime video call |
| Complexity | Simple (we have it) | Significant (signaling, ICE, codecs) |

### WebRTC Migration Path

1. **Phase 14.20**: WebRTC signaling server on VPS (websocket-based SDP exchange)
2. **Beast publishes WebRTC stream**: using `aiortc` (Python) or native WebRTC
3. **VPS as TURN relay**: for NAT traversal (Beast behind home network)
4. **Cockpit consumes via `<video>` element**: native browser WebRTC support
5. **Keep JPEG-over-WS as fallback**: for diagnostics, snapshots, and when WebRTC unavailable
6. **Auth gate**: WebRTC offer/answer gated by same Clerk auth as current WebSocket

### Decision

WebRTC is **required** for Discord-grade quality. JPEG-over-WebSocket is a functional diagnostic/monitoring path but will not match realtime video call quality regardless of optimization.

## Real Tracker Overlay Status

Beast-side tracker runtime (`vision_runtime.py`) has a placeholder tracker loop that emits empty overlays. Real object detection requires:

1. OpenCV DNN module or YOLO model on Beast
2. Frame-to-overlay pipeline integration
3. Overlay data attached to frame metadata

**Current state**: Diagnostic overlays work (rendering proven). Real tracker overlays require CV model installation on Beast.

**Blocker displayed in UI**: "No tracker runtime available on Beast. Enable DIAG overlay to test rendering, or install CV dependencies on Beast node."

## Security Result

- Auth check (`_check_auth`) remains enforced on WebSocket connect
- Origin validation (`_ALLOWED_ORIGINS`) remains enforced
- Connection rejection on invalid auth returns 4001
- No public camera port exposed
- No token in URL
- Camera live indicator visible

## Test Results

- 112/112 tests pass (85 existing + 27 new)
- TypeScript compiles clean
- Python compiles clean
- No auth regression
- No grounding regression

## Verdict: PARTIAL

### What Ships
- Joystick now has true visual thumbstick with pointer capture and mobile-reliable touch handling
- Guard timeout increased for mobile network reliability
- Overlay rendering is now visible (diagnostic overlays work, real overlays display exact blocker)
- PTZ diagnostics panel provides full transparency into every layer
- CameraPreview renders overlays in all camera surfaces
- Overlay health explains exactly why boxes are missing

### What Requires Next Phase
- **WebRTC media plane** (Phase 14.20): required for Discord-grade streaming quality
- **Real tracker CV model** on Beast: required for real object/person overlays
- **Live field trial**: code changes need operator device confirmation before SHIPPED verdict

### Why Not SHIPPED
- Stream quality does not match Discord target (JPEG-over-WS ceiling confirmed)
- Real tracker overlays require CV model installation on Beast (exact blocker displayed)
- Live operator field trial has not been performed on this build
- Per phase rules: no SHIPPED without live field trial

### Why Not NO-GO
- Joystick architecture is now correct with visual feedback and mobile reliability
- Overlay rendering chain is proven (diagnostic overlays visible)
- Every failure has an exact diagnostic explanation
- Security remains intact
- Clear migration path to WebRTC defined
