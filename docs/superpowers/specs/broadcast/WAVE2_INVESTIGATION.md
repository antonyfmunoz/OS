# Zone C Investigation — Wave 2: Multi-Source Compositing + Scene Switching

**Date**: 2026-06-13
**Status**: Slice A COMPLETE — multi-source composite + blip-free zmq scene switching proven.
**Supersedes**: Section 4 (scene switch = restart) corrected by zmq spike + Slice A proof.

---

## 1. Current Spine (Slice 0) — How Single-Source Works

### Arg builder (`adapters/broadcast/ffmpeg_args.py`)
`build_args()` produces a **flat CLI arg list** for a single-source invocation:
```
ffmpeg -y [-re] -f <input_fmt> -i <source> [-f lavfi -i anullsrc] \
  -c:v libx264 -b:v 4500k ... -c:a aac -b:a 128k \
  -f flv -progress pipe:1 -stats_period 1 <output_url>
```

Key structural facts:
- One `-i` (video) and one `-i` (audio) — always exactly two inputs.
- No `-filter_complex` flag. Encoding params applied directly to the single stream.
- Output URL validated and DNS-pinned by `_validate_output_url()`.
- The function returns `list[str]` passed directly to `ProcessLifecycle`.

### Engine (`adapters/broadcast/engine.py`)
- `BroadcastEngine._start_locked()` calls `build_args(**config)` → gets `list[str]` → passes to `ProcessLifecycle(cmd)`.
- Engine holds ONE `ProcessLifecycle` at a time. ONE FFmpeg process = one broadcast session.
- Health parsing via `-progress pipe:1` on stdout — key=value lines.
- State machine: `idle → starting → live → stopping → idle` (or `error`).

### ProcessLifecycle (`adapters/broadcast/process_lifecycle.py`)
- Subsystem-agnostic. Wraps any subprocess. CPU gate + SIGTERM→SIGKILL + monitor.
- No FFmpeg-specific knowledge. Pure process management.

---

## 2. What Changes for Multi-Source Compositing

### 2a. Arg Builder → `-filter_complex` Filtergraph

The single-source arg builder produces flat `-i` + codec flags. Multi-source requires FFmpeg's **complex filtergraph** (`-filter_complex`), which is the standard way to composite N inputs.

**Compositing pattern (N sources → single output):**
```
ffmpeg -y \
  -f lavfi -i testsrc2=size=640x480:rate=30 \        # [0:v] source A
  -f lavfi -i color=c=blue:s=320x240:rate=30 \       # [1:v] source B
  -f lavfi -i anullsrc=r=44100:cl=stereo \            # [2:a] silence
  -filter_complex "
    [0:v]scale=640:480[s0];
    [1:v]scale=320:240[s1];
    color=c=black:s=1920x1080:rate=30[canvas];
    [canvas][s0]overlay=x=0:y=0[c0];
    [c0][s1]overlay=x=640:y=0[out]
  " \
  -map "[out]" -map "2:a" \
  -c:v libx264 -b:v 4500k ... -c:a aac -b:a 128k \
  -f flv -progress pipe:1 -stats_period 1 <output_url>
```

**What this means for the arg builder:**
1. New function: `build_composite_args(scene, output_config)` alongside existing `build_args()`.
2. Each source in the scene produces an `-i` input.
3. A `-filter_complex` string is built from the scene's source entries (scale → overlay chain by z_order).
4. `-map "[out]"` selects the composited video. `-map` selects the mixed audio.
5. Encoding params stay the same — they apply to the single composited output.
6. `build_args()` remains untouched for single-source backward compatibility.

### 2b. Audio Mixing

FFmpeg's `amix` filter combines N audio inputs with per-source volume:

```
-filter_complex "
  [0:a]volume=0.8[a0];
  [1:a]volume=0.5[a1];
  [a0][a1]amix=inputs=2:duration=longest[aout]
"
-map "[aout]"
```

Per-source mute = `volume=0.0`. Per-source volume = `volume=<0.0-1.0>`.
This slots into the same `-filter_complex` string as the video compositing.

### 2c. Impact on Engine and ProcessLifecycle

**ProcessLifecycle**: ZERO changes. It manages a subprocess. Doesn't care what the command is.

**BroadcastEngine**: Minimal changes:
- `_start_locked()` currently calls `build_args()`. With multi-source, it calls `build_composite_args()` when the config contains a scene with multiple sources, or falls back to `build_args()` for single-source.
- The rest (health parsing, state machine, stop, health callback) is unchanged — FFmpeg's `-progress pipe:1` output format is identical regardless of filtergraph complexity.

---

## 3. Scene/Source Model

### Current state
The route file (`cockpit_broadcast_routes.py`) has `BroadcastStartRequest` with a flat `source_type` + `source_config` + encoding params. No scene concept.

### Extension: Scene + SourceEntry model

New models (local to routes for Wave 2, graduate to substrate/ when stable):

```python
class SourceEntry(BaseModel):
    source_id: str = Field(description="Unique ID within the scene")
    source_type: SourceType
    source_config: dict[str, Any] = Field(default_factory=dict)
    x: int = Field(default=0, description="Position X on canvas")
    y: int = Field(default=0, description="Position Y on canvas")
    width: int = Field(default=1920, description="Rendered width")
    height: int = Field(default=1080, description="Rendered height")
    z_order: int = Field(default=0, description="Layer index, higher = front")
    visible: bool = Field(default=True)
    volume: float = Field(default=1.0, ge=0.0, le=1.0)
    muted: bool = Field(default=False)

class Scene(BaseModel):
    scene_id: str
    name: str
    canvas_width: int = Field(default=1920)
    canvas_height: int = Field(default=1080)
    sources: list[SourceEntry] = Field(default_factory=list)
    background_color: str = Field(default="black")

class BroadcastCompositeRequest(BaseModel):
    scene: Scene
    output_url: str
    video_codec: str = Field(default="libx264")
    video_bitrate: str = Field(default="4500k")
    audio_codec: str = Field(default="aac")
    audio_bitrate: str = Field(default="128k")
    fps: int = Field(default=30, ge=1, le=120)
    keyframe_interval: int = Field(default=2, ge=1, le=10)
    preset: str = Field(default="veryfast")
    container_format: str = Field(default="flv")
```

### Active-scene state

The engine holds:
- `_scenes: dict[str, Scene]` — all defined scenes.
- `_active_scene_id: str | None` — which scene is currently being composited.
- Scene CRUD via new API endpoints (`POST /scenes`, `PUT /scenes/{id}`, `DELETE /scenes/{id}`, `PUT /scenes/{id}/activate`).

---

## 4. THE HARD QUESTION — Live Scene Switching

### ~~The constraint (stated honestly)~~ SUPERSEDED BY ZMQ SPIKE (2026-06-13)

**OLD (investigation conclusion):** "Switching scenes = rebuilding the FFmpeg filtergraph = restarting the FFmpeg process." → 1-3s blip.

**NEW (proven by spike + Slice A):** Scene switching within a pre-declared source set is **BLIP-FREE** via FFmpeg's `zmq` filter. The filtergraph STRUCTURE is immutable, but filter PARAMETERS (x, y, enable) are live-controllable per frame via zmq commands. No restart, no reconnect, no blip.

### How it works (proven)

All sources are pre-declared at FFmpeg launch in a single filtergraph with:
- Named overlays: `overlay@src_{id}` for each source
- `eval=frame` on each overlay — re-evaluates position expressions every frame
- `zmq` filter on the video chain — receives commands via ZMQ REQ/REP socket

A "scene" is a **named parameter preset**: per-source x/y/enable values. Switching scenes = sending N zmq commands (one per parameter per source). Each command returns `"0 Success"` in ~34ms.

### Proof data

| Measurement | Value |
|-------------|-------|
| Switch latency (6 commands, 2 sources) | 198-212ms |
| Per-command latency | ~34ms |
| PID change during switch | NONE (stable throughout) |
| RTMP start_time behavior | Monotonically increasing (no reset/reconnect) |
| Frame gaps during switch | 33-34ms (perfect 30fps) |
| Rapid switching (5 cycles = 10 switches) | 100% success, zero errors |
| Orphan processes after stop | ZERO |

### Atomicity (honest)

The zmq filter processes commands sequentially. For 2 sources × 3 params = 6 commands, the switch spans ~200ms (~6 frames at 30fps). This is **near-atomic** — the viewer sees source changes ripple across ~6 frames, not a single-frame cut. True single-frame atomicity would require:
- `sendcmd` with timestamp-aligned commands (possible but complex)
- OR zmq batch protocol (not supported by FFmpeg's zmq filter)

200ms is well below perceptual threshold for a cut transition and far better than the 1-3s restart blip. For comparison, OBS defaults to 300ms fade transitions.

### Limits of zmq approach

| Limit | Reality | Trigger for upgrade |
|-------|---------|---------------------|
| Cannot add/remove inputs at runtime | Graph structure fixed at launch | Need source type not in pre-declared set |
| Cannot change encoder settings live | Codec/bitrate/resolution fixed at launch | Need adaptive bitrate |
| No animated transitions | Cut only — no fade/wipe/slide | Need production-quality transitions |
| Source ceiling | Fixed at launch-time max | Need truly dynamic source count |

### Architecture decision (settled)

**Build on zmq parameter control. Defer GPU compositor.**

The GPU compositor (Wave 8) is justified ONLY when zmq's limits are hit: animated transitions, dynamic source addition, or per-frame interpolation. Until then, zmq delivers blip-free scene switching at negligible complexity.

---

## 5. Audio Mixing Basics

For Wave 2, basic audio mixing via FFmpeg `amix`:

**Per-source controls:**
- `volume: float` (0.0–1.0) → FFmpeg `volume` filter
- `muted: bool` → `volume=0.0`

**Filtergraph audio section:**
```
[0:a]volume=0.8[a0]; [1:a]volume=0.5[a1]; [a0][a1]amix=inputs=2:duration=longest[aout]
```

**Sources without audio** (e.g., test_pattern, image, color source): the arg builder generates `anullsrc` (silence) for that input so the `amix` filter always gets the expected number of audio streams.

**NOT in Wave 2 scope** (per spec, these are Wave 5):
- Per-source audio filters (compressor, noise gate, EQ)
- Audio ducking
- Monitor mode (local-only playback)
- Master volume (applied client-side or as a final gain stage)

---

## 6. Cockpit UI Extension

### Current BroadcastPanel
176 lines. Single RTMP URL input + Start/Stop + health grid. No scene or source controls.

### Wave 2 UI additions

**Option A — Scene editor as BroadcastPanel expansion:**
Add a scene/source section above the controls:
- Scene list (sidebar tabs or dropdown) with active indicator
- Source list per scene with drag-reorder (z_order)
- Per-source: type selector, position (x/y/w/h), volume slider, mute toggle, visible toggle
- "Add Source" button with source type picker (test_pattern, camera, file, rtmp_pull)
- "Switch Scene" button (with "will cause brief interruption" warning)

**Option B — Separate SceneEditor panel:**
New panel accessible from Broadcast panel. Handles scene CRUD, source layout, and previews. BroadcastPanel stays focused on stream control + health.

**Recommended: Option A.** The BroadcastPanel already owns the broadcast context. A separate panel would fragment the workflow. The scene/source section slides in above the controls — same pattern as VisionPanel's tracking config section.

### API endpoints to add

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/broadcast/scenes` | GET | List all scenes |
| `/broadcast/scenes` | POST | Create scene |
| `/broadcast/scenes/{id}` | PUT | Update scene (sources, layout) |
| `/broadcast/scenes/{id}` | DELETE | Delete scene |
| `/broadcast/scenes/{id}/activate` | POST | Switch to this scene (restarts FFmpeg) |
| `/broadcast/start` | POST | Modified: accepts `scene_id` OR legacy flat config |

---

## 7. Dependency Check: Wave 2 vs Wave 1

**Canonical plan says:** Wave 2 depends on Wave 1 (recording + multi-output).

**Actual analysis: NO real coupling.** They are independent.

| Concern | Wave 1 (Recording) | Wave 2 (Multi-Source) | Shared? |
|---------|--------------------|-----------------------|---------|
| FFmpeg arg builder | Adds `-f segment` or tee muxer for file output | Adds `-filter_complex` for compositing | **No** — different sections of the arg list |
| Engine state machine | Adds `recording` state alongside `live` | Scene state, active scene tracking | **No** — orthogonal state |
| ProcessLifecycle | No changes | No changes | N/A |
| Output URL handling | Adds file:// validation for recording path | No changes | **No** |
| API routes | Adds `/broadcast/record/start`, `/record/stop` | Adds `/broadcast/scenes/*` | **No** — separate endpoints |
| Cockpit UI | Recording controls + file size | Scene editor + source controls | **No** — separate UI sections |

**Verdict: Wave 2 can proceed independently of Wave 1.** The canonical plan's dependency arrow (`Wave 1 → Wave 2`) was based on the assumption that multi-output (stream + record simultaneously) needs to be proven before multi-source, but architecturally they touch different parts of the FFmpeg command (output muxing vs input compositing) and different engine state (recording flag vs scene state).

**Recommendation:** Update the canonical plan's dependency graph to show Wave 1 and Wave 2 as parallel branches from Slice 0, not sequential.

---

## 8. Build Plan — Wave 2

### Files to create/modify (ZERO core edits):

| File | Action | Purpose |
|------|--------|---------|
| `adapters/broadcast/scene_model.py` | **CREATE** | Scene, SourceEntry Pydantic models |
| `adapters/broadcast/filtergraph.py` | **CREATE** | `build_filtergraph(scene, output_config) -> list[str]` — scene → FFmpeg complex filtergraph args |
| `adapters/broadcast/ffmpeg_args.py` | **MODIFY** | Add `build_composite_args()` that delegates to filtergraph.py; preserve `build_args()` for single-source |
| `adapters/broadcast/engine.py` | **MODIFY** | Add `_scenes`, `_active_scene_id`, `switch_scene()`, scene CRUD methods; routing logic in `_start_locked()` |
| `transports/api/cockpit_broadcast_routes.py` | **MODIFY** | Add scene CRUD endpoints, modify `/start` to accept `scene_id` |
| `cockpit/.../panels/BroadcastPanel.tsx` | **MODIFY** | Scene list, source editor, z-order controls, volume/mute per source |
| `cockpit/.../stores/broadcastStore.ts` | **MODIFY** | Scene state, source state, active scene tracking |
| `tests/adapters/broadcast/test_filtergraph.py` | **CREATE** | Unit tests for filtergraph generation (edge cases: empty scene, single source fallback, z_order sorting, audio mixing with muted sources) |

### Proof topology (local RTMP — same as Slice 0):

```
┌─────────────────────────────────────────────────────────────────┐
│  VPS (srv1500858)                                               │
│                                                                 │
│  Scene A: [testsrc2 640x480 @ (0,0)] + [color:blue 320x240     │
│            @ (640,0)] → 1920x1080 canvas                        │
│  Scene B: [testsrc 1920x1080 @ (0,0)] (single fullscreen)      │
│                                                                 │
│  Proof steps:                                                   │
│  1. Create Scene A (2 sources)                                  │
│  2. Start broadcast with Scene A → RTMP to MediaMTX :1935       │
│  3. ffprobe → confirm 1920x1080 H.264 composited output         │
│  4. Health metrics → fps, bitrate, drop% for composited stream  │
│  5. Create Scene B (1 source)                                   │
│  6. Switch to Scene B → confirm FFmpeg restart + RTMP reconnect │
│  7. ffprobe → confirm new scene rendering                       │
│  8. Stop → ZERO orphan ffmpeg                                   │
│                                                                 │
│  MediaMTX :1935 (same host)                                     │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation order:

1. **Scene model** (`scene_model.py`) — pure data, no dependencies.
2. **Filtergraph builder** (`filtergraph.py`) — pure function, unit-testable in isolation.
3. **Tests** (`test_filtergraph.py`) — prove filtergraph generation before wiring.
4. **Engine integration** — scene CRUD + `switch_scene()` + routing in `_start_locked()`.
5. **API routes** — scene CRUD endpoints.
6. **Cockpit UI** — scene editor in BroadcastPanel.
7. **End-to-end proof** — local RTMP compositing + scene switch.

---

## 9. Honest Constraint Summary

| Constraint | Reality | Mitigation |
|------------|---------|------------|
| ~~Scene switch = FFmpeg restart~~ | **SUPERSEDED** — zmq parameter control, no restart, ~200ms switch | N/A |
| Source set fixed at launch | Cannot add new input types after FFmpeg starts | Declare max sources at launch; rare "add source" = restart |
| Switch is near-atomic, not single-frame | ~200ms for 6 zmq commands (2 sources) | Below perceptual threshold; OBS default is 300ms |
| Filtergraph complexity scales O(sources) | CPU cost per source: ~5-15% for scale+overlay | Limit to 8-10 sources per scene for VPS (software encoding) |
| No animated transitions | Cut only — fade/wipe requires dual-pipeline (Wave 4) | Document as known limitation, not a defect |
| Audio mixing via amix | Basic volume/mute only — no compressor/EQ | Sufficient for Wave 2; Wave 5 adds per-source filters |
| `-re` flag interaction with compositing | `-re` paces *each input* independently — may cause sync issues with mixed input types | Use `-re` only on lavfi/file inputs, not on live inputs (camera, rtmp_pull) |

---

## STOP. Slice A delivered. Wave 2 architecture settled: zmq preset switching.
