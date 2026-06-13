# UMH Broadcast Build Plan (Re-Derived from Full OBS Architecture)

> **Supersedes**: The ad-hoc Wave 1/2/3 list. This plan is grounded in the
> complete OBS architecture map, sequenced by leverage + dependency order.

> **Principle**: UMH wraps FFmpeg where OBS wraps GPU APIs. Every capability
> maps to FFmpeg filter_complex parameters, not in-process rendering. The
> differentiator is AI-operable broadcasting — agents and cells control the
> same API as humans. No other broadcast tool has this.

---

## What's Already Shipped

### Slice 0 — Single-Source Broadcast (COMPLETE)
- BroadcastEngine state machine (idle → starting → live → stopping)
- ProcessLifecycle (process group isolation, CPU gate, SIGTERM→SIGKILL)
- FFmpeg argument builder with SSRF-hardened URL validation
- Source types: test_pattern (8 lavfi), v4l2 camera, RTMP/SRT pull, file (loop)
- x264 encoding (High profile, level 4.1)
- Single RTMP/RTMPS/SRT output
- BroadcastHealth (fps, bitrate, dropped, speed, uptime, status tier)
- HTTP API: start, stop, status (Clerk auth)
- WebSocket health push (1s pulse with subprotocol auth)
- Cockpit BroadcastPanel (RTMP input, start/stop, health dashboard)
- CapabilityHandler integration (agent-cell operable)
- 7 process lifecycle tests

### Wave 2 Slice A — Multi-Source Compositing + Scene Switching (COMPLETE)
- filter_complex builder (canvas + scaled overlays + ZMQ named filters)
- Scene/SourceEntry/SourceLayout/CompositeConfig Pydantic models
- ZMQ client (per-command fresh socket, batch with abort semantics)
- Live scene switching via ZMQ overlay repositioning (~200ms, no FFmpeg restart)
- Composite start API + scene switch API + scene list API
- Cockpit scene switcher UI (conditional on composite + live)
- 25 filtergraph tests (overlays, z-order, scenes, injection prevention)
- nginx WS upgrade block for broadcast endpoint
- Frontend Clerk auth + backend subprotocol echo

---

## What's Missing (Mapped Against Full OBS Surface)

### Coverage Assessment

| OBS Subsystem | UMH Status | Priority |
|--------------|-----------|----------|
| Graphics/Compositor | N/A (FFmpeg wraps) | — |
| Source primitive | Partial (SourceEntry, no capability flags) | HIGH |
| Scene/Scene-item | Partial (no crop/rotation/opacity/blend/nesting) | HIGH |
| Audio pipeline | ABSENT (silent anullsrc placeholder) | **CRITICAL** |
| Video pipeline | WRAPPED (FFmpeg handles) | — |
| Encoder abstraction | Partial (x264 only, no HW) | MEDIUM |
| Output abstraction | Partial (stream only, no record) | HIGH |
| Service abstraction | ABSENT | MEDIUM |
| Module/plugin system | N/A (CapabilityHandler serves this role) | — |
| Capture sources | 4 of 16 types | MEDIUM |
| Video filters | ABSENT | HIGH |
| Audio filters | ABSENT | HIGH |
| Transitions | ABSENT (instant cut only) | MEDIUM |
| Studio mode | ABSENT | LOW |
| Properties/settings | Partial (Pydantic, no dynamic) | LOW |
| Profiles/collections | ABSENT | MEDIUM |
| Stats/performance | Partial (health monitor, no separate counters) | LOW |
| Projectors | N/A (cockpit serves this role) | — |
| Hotkeys | N/A (API serves this role) | — |
| Auto-config | ABSENT | LOW |
| Remote control | Partial (HTTP + WS health, no bidirectional WS) | MEDIUM |

---

## Re-Derived Critical Path

Sequenced by dependency order. Each phase builds on the previous.
Estimated scope in parentheses.

### Phase 1: Audio Pipeline (CRITICAL — blocks everything after it)

**Why first**: A broadcast tool without audio is a slideshow. Audio is the
single largest capability gap. Every subsequent phase (recording, filters,
transitions) needs audio to be meaningful.

**What to build**:
1. Per-source audio input in filter_complex (`-i` audio sources mapped to
   each video source, or `anullsrc` for sources without audio)
2. Audio mixing via FFmpeg `amix` or `amerge` filters
3. Per-source volume control via `volume` filter with ZMQ-addressable parameter
4. Per-source mute (volume=0 via ZMQ, or `enable` flag)
5. Audio sync offset via `adelay` filter per source
6. AAC encoding for output stream (already have `aac` in args, just need
   real audio input instead of anullsrc)
7. Cockpit audio mixer UI (per-source volume sliders, mute toggles, VU meters)
8. API endpoints: set volume, set mute, get audio levels

**Wraps**: FFmpeg `amix`, `volume`, `adelay`, `pan` filters.
**Scope**: Medium. Filter_complex changes + new API endpoints + cockpit UI.

**Dependency chain**: Audio → Filters → Recording → Transitions → Studio Mode

### Phase 2: Recording + Multi-Output

**Why second**: Recording is the second most-asked-for broadcast feature after
"go live." Users need to stream AND record simultaneously. This also establishes
the multi-output pattern needed for replay buffer and studio mode preview.

**What to build**:
1. Multi-output via FFmpeg `tee` muxer or multiple `-f` outputs
2. Recording to MKV/MP4 (configurable container)
3. Simultaneous stream + record from same encode
4. Recording start/stop/pause API (independent of stream)
5. Output directory configuration
6. File naming with timestamps
7. Cockpit recording controls (button, duration, file path display)
8. Multi-track audio recording (separate tracks per source to MKV)

**Wraps**: FFmpeg `-f tee`, segment muxer, container muxing.
**Scope**: Medium. New output management layer, API endpoints, cockpit UI.

### Phase 3: Source Transform Completeness

**Why third**: With audio and recording working, the compositing layer needs
to match OBS's transform model to be production-usable. Users expect crop,
rotation, opacity — not just position and scale.

**What to build**:
1. Crop per source (FFmpeg `crop` filter before overlay)
2. Rotation per source (FFmpeg `rotate` filter)
3. Opacity per source (overlay `format=rgba`, alpha parameter via ZMQ)
4. Blend modes (FFmpeg `blend` filter between overlay layers)
5. Bounds modes (fit, fill, stretch — compute scale from bounds rectangle)
6. Alignment/anchor points (compute overlay position from anchor)
7. Source grouping (logical, transform inheritance)
8. Nested scenes (scene-in-scene composition)
9. Update scene_model.py with new transform fields
10. Cockpit source transform UI (position/size/crop/rotation controls)

**Wraps**: FFmpeg `crop`, `rotate`, `blend`, `format` filters.
**Scope**: Medium-Large. Extends existing filtergraph builder significantly.

### Phase 4: Video + Audio Filters

**Why fourth**: Filters are what make raw sources look and sound professional.
Chroma key is table-stakes for any producer. Noise suppression is table-stakes
for any microphone.

**What to build (video)**:
1. Color correction (FFmpeg `eq` for brightness/contrast/gamma, `hue` for
   hue/saturation)
2. Chroma key (FFmpeg `chromakey` filter)
3. Color key (FFmpeg `colorkey` filter)
4. LUT (FFmpeg `lut3d` with .cube file support)
5. Blur (FFmpeg `gblur` or `boxblur`)
6. Sharpen (FFmpeg `unsharp`)
7. Image mask/blend overlay

**What to build (audio)**:
1. Noise suppression (FFmpeg `arnndn` with RNNoise model)
2. Noise gate (FFmpeg `agate`)
3. Compressor (FFmpeg `acompressor`)
4. Limiter (FFmpeg `alimiter`)
5. EQ (FFmpeg `equalizer`)
6. Gain (FFmpeg `volume` — already have, expose as filter)

**For each filter**:
- Per-source filter chain model (ordered list of filters per source)
- ZMQ-addressable parameters for live adjustment
- API: add/remove/reorder/configure filters per source
- Cockpit filter panel (per-source filter list with parameter controls)

**Wraps**: FFmpeg's extensive filter library.
**Scope**: Large. Many filters, but each is a thin wrapper over FFmpeg.

### Phase 5: Transitions

**Why fifth**: With scenes, audio, and filters working, transitions make scene
switching look professional instead of jarring instant cuts.

**What to build**:
1. Fade transition (ZMQ opacity crossfade over configurable duration)
2. Cut transition (already exists — instant switch)
3. Stinger transition (overlay pre-rendered video with alpha at cut point)
4. Configurable transition duration (global default + per-scene override)
5. Transition model in scene config
6. API: set transition type/duration, trigger transition
7. Cockpit transition controls (type selector, duration slider)

**Architecture choice**: Crossfade via ZMQ opacity animation (source A opacity
1→0, source B opacity 0→1 over N frames). Stinger: overlay a video source
with alpha channel, timed to cover the cut. No FFmpeg restart needed.

**Wraps**: ZMQ parameter animation + FFmpeg overlay alpha.
**Scope**: Medium. Animation timing logic + stinger video source.

### Phase 6: Service Registry + Encoder Expansion

**Why sixth**: Quality-of-life. Users shouldn't need to know RTMP ingest URLs.
Hardware encoding dramatically reduces CPU usage.

**What to build (services)**:
1. Service registry (JSON: platform → server URL pattern, stream key ref,
   recommended settings, bitrate caps)
2. Built-in templates: Twitch, YouTube, Kick, custom RTMP
3. Stream key storage integration (1Password vault reference)
4. API: list services, select service, validate connection
5. Cockpit service selector (platform dropdown, stream key input, test button)

**What to build (encoders)**:
1. Encoder detection (probe FFmpeg `-encoders` output)
2. Hardware encoder support: h264_nvenc, h264_qsv, h264_vaapi
3. Encoder selection in config (auto or manual)
4. Codec parameters exposed via API (preset, profile, bitrate, rate control)
5. Auto-config: detect best encoder for node, recommend settings

**Wraps**: FFmpeg encoder selection + platform knowledge.
**Scope**: Medium. JSON config + FFmpeg arg changes + cockpit UI.

### Phase 7: Additional Source Types

**Why seventh**: Expanding the source palette beyond test patterns, cameras,
files, and RTMP pulls.

**What to build**:
1. Image source (FFmpeg `image2` input, PNG/JPG with alpha)
2. Text source (FFmpeg `drawtext` filter — font, size, color, position)
3. Color source (FFmpeg `color` lavfi generator)
4. Screen capture (FFmpeg `x11grab` for X11, `pipewire` for Wayland)
5. Audio-only sources (FFmpeg ALSA/PulseAudio input without video)
6. NDI input (FFmpeg with libndi, if available on node)

**Wraps**: FFmpeg input types + lavfi generators.
**Scope**: Medium. Each source type is a new input builder in ffmpeg_args.py.

### Phase 8: Replay Buffer + Source CRUD While Live

**Why eighth**: Advanced features that differentiate a production tool from
a simple encoder wrapper.

**What to build (replay)**:
1. Circular buffer output (FFmpeg segment muxer with rolling window)
2. Save-on-demand (copy buffer to timestamped file)
3. Configurable duration (seconds)
4. API: start buffer, save clip, get last saved path
5. Cockpit replay button

**What to build (live source management)**:
1. Add source while live (new FFmpeg input + overlay in filter_complex —
   requires filter_complex reinit or ZMQ source injection)
2. Remove source while live (disable overlay, drop input)
3. Update source config while live (URL change, device change)
4. This is architecturally hard — may require filter_complex rebuild with
   seamless switchover (start new FFmpeg, crossfade, stop old)

**Scope**: Large. Replay is medium; live source CRUD is architecturally complex.

### Phase 9: Studio Mode (Preview/Program)

**Why ninth**: Professional workflow feature. Requires dual output (preview +
program) which depends on multi-output (Phase 2) and transitions (Phase 5).

**What to build**:
1. Dual filter_complex output pads (preview + program)
2. Preview output via HLS or WebRTC to cockpit
3. Program output to RTMP (existing)
4. Scene changes affect preview only; transition fires to swap
5. Cockpit dual-panel UI (preview left, program right, transition controls)

**Wraps**: FFmpeg tee/split output + cockpit UI.
**Scope**: Large. Dual output + cockpit redesign + state management.

### Phase 10: Profiles + Scene Collections + Bidirectional WS

**Why last**: Polish features. Save/load configurations, advanced remote control.

**What to build (profiles/collections)**:
1. Profile model (encoding, output, service settings as named JSON)
2. Scene collection model (scenes, sources, filters as named JSON)
3. Save/load/switch API
4. Cockpit profile/collection selector

**What to build (WS expansion)**:
1. Bidirectional WS commands (not just health push)
2. Source/filter/scene CRUD via WS
3. Event subscriptions (scene changed, source added, health update)
4. Batch commands

**Scope**: Medium. Data modeling + API expansion.

---

## Dependency Graph

```
Phase 1: Audio Pipeline
    ↓
Phase 2: Recording + Multi-Output
    ↓
Phase 3: Source Transforms ←── (can parallel with Phase 2)
    ↓
Phase 4: Video + Audio Filters ←── (depends on Phase 1 for audio filters)
    ↓
Phase 5: Transitions ←── (depends on Phase 3 for opacity, Phase 1 for audio crossfade)
    ↓
Phase 6: Services + Encoders ←── (independent, can parallel with 4-5)
    ↓
Phase 7: Source Types ←── (independent, can parallel with 4-6)
    ↓
Phase 8: Replay Buffer + Live CRUD ←── (depends on Phase 2 for multi-output)
    ↓
Phase 9: Studio Mode ←── (depends on Phase 2 + Phase 5)
    ↓
Phase 10: Profiles + Collections + WS
```

### Parallelization Opportunities
- Phases 3 + 2 can run in parallel (independent)
- Phase 6 can run any time after Phase 1 (encoder/service are independent)
- Phase 7 can run any time (source types are additive)
- Phases 4 + 5 have partial overlap but audio filters need Phase 1

---

## Leverage Summary

| Verdict | Count | What |
|---------|-------|------|
| **WRAP (FFmpeg)** | 18 | Graphics, video pipeline, frame timing, encoders, most sources, all filters, transitions, audio mixing, recording |
| **INTERNALIZE** | 8 | Source primitive, scene model, output management, service registry, stats, studio mode, profiles, remote control |
| **DEFER** | 5 | Plugin system, virtual camera, game capture, browser source, VST, hotkeys, projectors |

**The fundamental insight**: OBS built a custom real-time GPU compositor because
it's a desktop application rendering in-process. UMH wraps FFmpeg because it's a
headless server orchestrating subprocesses. The capability surface is the same;
the implementation strategy is completely different. Every OBS capability maps to
FFmpeg filter parameters, codec flags, or muxer options — none require adopting
OBS's in-process rendering architecture.

**The differentiator**: OBS has no AI integration. UMH's CapabilityHandler protocol
means every broadcast action (start, stop, switch scene, adjust volume, apply
filter) is agent-operable via the same API humans use. An AI agent can direct a
broadcast, respond to health metrics, trigger scene switches based on content
analysis, and manage multi-destination streaming autonomously. This is the
capability that no existing broadcast tool provides.

---

## Acceptance Criteria Per Phase

Each phase is complete when:
1. Unit tests cover the new filter_complex constructs
2. Integration test: start composite, verify FFmpeg runs with new capabilities
3. API endpoints documented and Clerk-authed
4. Cockpit UI renders the new controls
5. Agent-cell operable (CapabilityHandler updated)
6. Health monitoring covers the new state
7. Zero regression on existing Slice 0 / Wave 2 capabilities

---

*Document produced 2026-06-13. Re-derived from complete OBS architecture study.*
*Supersedes ad-hoc Wave 1/2/3 list.*
