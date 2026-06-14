# OBS Architecture Map (Concept-Only)

> **Firewall**: This document contains architectural concepts, design rationale,
> and capability descriptions only. Zero GPL expression — no copied code,
> no reproduced structures, no identifiers beyond unavoidable domain nouns.
> Produced via ephemeral quarantine read; quarantine destroyed on exit.

> **Purpose**: Complete concept-level understanding of every OBS subsystem,
> how they relate, why each exists, and what design decisions make OBS
> effective as a producer tool. Each subsystem includes a LEVERAGE VERDICT
> for UMH's clean-room broadcast implementation.

---

## Table of Contents

1. [Design Philosophy](#1-design-philosophy)
2. [Core Engine: Graphics/Compositor](#2-core-engine-graphicscompositor)
3. [Core Engine: Universal Source Primitive](#3-core-engine-universal-source-primitive)
4. [Core Engine: Scene/Scene-Item Model](#4-core-engine-scenescene-item-model)
5. [Core Engine: Audio Pipeline](#5-core-engine-audio-pipeline)
6. [Core Engine: Video Pipeline + Frame Timing](#6-core-engine-video-pipeline--frame-timing)
7. [Core Engine: Encoder Abstraction](#7-core-engine-encoder-abstraction)
8. [Core Engine: Output Abstraction](#8-core-engine-output-abstraction)
9. [Core Engine: Service Abstraction](#9-core-engine-service-abstraction)
10. [Core Engine: Module/Plugin System](#10-core-engine-moduleplugin-system)
11. [Capability Surface: Capture Sources](#11-capability-surface-capture-sources)
12. [Capability Surface: Filter Catalog](#12-capability-surface-filter-catalog)
13. [Capability Surface: Transition System](#13-capability-surface-transition-system)
14. [Capability Surface: Studio Mode](#14-capability-surface-studio-mode)
15. [Capability Surface: Properties/Settings](#15-capability-surface-propertiessettings)
16. [Capability Surface: Profiles & Scene Collections](#16-capability-surface-profiles--scene-collections)
17. [Capability Surface: Stats/Performance](#17-capability-surface-statsperformance)
18. [Capability Surface: Projectors](#18-capability-surface-projectors)
19. [Capability Surface: Hotkeys](#19-capability-surface-hotkeys)
20. [Capability Surface: Auto-Config](#20-capability-surface-auto-config)
21. [Capability Surface: Remote Control Protocol](#21-capability-surface-remote-control-protocol)
22. [Data Flow: Threading Model](#22-data-flow-threading-model)
23. [Data Flow: Video Frame Path](#23-data-flow-video-frame-path)
24. [Data Flow: Audio Signal Path](#24-data-flow-audio-signal-path)
25. [Data Flow: Scene Rendering Pipeline](#25-data-flow-scene-rendering-pipeline)
26. [Cross-Cutting Design Principles](#26-cross-cutting-design-principles)

---

## 1. Design Philosophy

OBS was rewritten from OBS Classic in 2013 with three explicit goals: multi-platform,
separation of core from frontend, and extensibility. The resulting design embodies
several non-obvious architectural choices:

**Everything is a source.** Cameras, text, colors, scenes, transitions, filters —
all share one universal primitive with one lifecycle. No type hierarchy. Behavioral
variation comes from capability flags and registered callbacks. This eliminates
special-casing and enables uniform composition.

**Callback-table polymorphism.** All extensibility uses C function pointer structs
filled out by plugins and registered with the core. No class hierarchies, no
templates. The simplest possible abstraction with maximum ABI stability.

**Self-describing configuration.** Every plugin declares its own settings schema.
The UI renders generically from the schema. No plugin-specific UI code in the core.
This means new capabilities added via plugins get automatic UI without core changes.

**Timestamp-based synchronization.** Audio and video threads run independently.
All synchronization is through nanosecond timestamps, not locks or barriers.
An interleave queue at the output ensures monotonic delivery. This eliminates
the most common source of A/V desync.

**GPU-first rendering.** All composition, scaling, color conversion, and filter
effects happen on the GPU. CPU involvement is minimized to staging surface readback
— and eliminated entirely for hardware encoders that accept GPU textures directly.

**Plugin equality.** Built-in and third-party plugins are architecturally
indistinguishable. The four registration categories (source, output, encoder,
service) cover every extensibility point.

**Stability over modernity.** The core targets a D3D11-class mental model. Newer
backends (Metal) simulate this rather than requiring core rewrites.

---

## 2. Core Engine: Graphics/Compositor

### Responsibility
Abstracts platform GPU APIs (D3D11, OpenGL, Metal) behind a single unified C
function-pointer interface. Provides render targets, textures, shaders, vertex
buffers, blend states, and staging surfaces. All higher-level code dispatches
through cached function pointers — no rendering code above this layer touches
a GPU API directly.

### Design Decision + Why
OBS needed platform-specific capture integration (shared textures for game capture,
platform screen capture APIs) that no existing abstraction (SDL, ANGLE) provided.
A custom layer gives full control over resource sharing, texture interop, and
capture hooks. The function-pointer dispatch (rather than compile-time abstraction)
enables runtime backend selection from the same binary.

### Key Data Flow
Startup: load platform backend as dynamic library → resolve ~150 function pointers
→ create graphics context. Per-frame: clear render target → set orthographic
projection → traverse scene graph calling source render callbacks → apply filters
via effect shaders → scale to output resolution → convert RGB→YUV via GPU shaders
→ stage to CPU via double-buffered async copy.

### Effect/Shader System
OBS has its own shading language (HLSL-like "effect files") bundling vertex/pixel
shaders with uniforms, samplers, techniques, and passes. Two universal parameters
expected: view/projection matrix and main source texture. Filters use a begin/end
pattern: capture parent output to texture, set effect parameters, draw fullscreen
quad through custom effect. The OpenGL backend includes a transpiler that converts
the HLSL-like syntax to GLSL at load time. Metal transpiles to MSL at runtime.

### Inputs/Outputs
- In: source render callbacks, filter effects, scene transform matrices
- Out: final composited texture → GPU format conversion → staging surface → CPU frame

### LEVERAGE VERDICT: **WRAP (FFmpeg + GStreamer)**
UMH runs headless on servers. No need for a custom GPU abstraction or real-time
GPU compositing. FFmpeg's filter_complex already handles compositing, scaling,
and format conversion. For future GPU acceleration: GStreamer's pipeline model
with hardware-accelerated elements. The OBS approach (custom GPU abstraction for
desktop rendering) solves a problem UMH doesn't have.

---

## 3. Core Engine: Universal Source Primitive

### Responsibility
The single universal media entity. Every object that produces, transforms, or
composes video and/or audio is a source: cameras, screen captures, text, color,
filters, transitions, and scenes themselves. Provides a uniform lifecycle, reference
counting, and capability declaration via flags.

### Lifecycle
create → activate (on-air, first reference) → show (visible on any display) →
tick (per-frame update) → render/output (produce frames) → hide → deactivate →
destroy. The two-tier visibility (show/hide vs activate/deactivate) gives sources
fine-grained resource management: "someone might be looking" vs "this is going
to air." Both are reference-counted — fires on first/last reference only.

### Sync vs Async Sources
**Sync**: render callback called by graphics thread during scene traversal. Frame
rate tied to output FPS. For generated content (text, colors, images).
**Async**: push frames from any thread at any rate with timestamps. Core maintains
a frame queue, selects best-matching frame during rendering. Handles rate mismatches
(24fps camera on 60fps output reuses frames; 120fps drops intermediates). For
hardware capture sources.

### Four Source Types
- **Input**: primary media producers (cameras, media files, browser)
- **Filter**: transformers attached to a parent source's chain
- **Transition**: interpolators blending two child sources over time
- **Scene**: composite containers holding ordered items with transforms

### Capability Flags (Composition Over Inheritance)
Flags like "produces video," "produces audio," "async video," "accepts interaction,"
"composites children," "unique hardware (do not duplicate)" — combined freely.
No class hierarchy. One struct, one lifecycle. All variation from flags + callbacks.

### Reference Counting
Dual-tier: strong references (prevent destruction, atomic) and weak references
(check existence without preventing cleanup, breaks circular references in scene
nesting). Destruction posted to a dedicated thread to avoid blocking render/audio.

### Design Decision + Why
Making everything a source eliminates type hierarchies and special-casing. Scenes
compose with transitions compose with filters — all through the same interface.
The flag-based capability system avoids the combinatorial explosion of inheritance
trees for "video source," "audio source," "video+audio source," "interactive
video source," etc.

### LEVERAGE VERDICT: **INTERNALIZE (own abstraction)**
UMH needs its own source primitive. The concept of a universal media entity with
lifecycle, capability flags, and uniform composition is the right pattern. But
UMH's implementation is fundamentally different: Python/async, headless, FFmpeg
subprocess-based rather than in-process GPU rendering. Internalize the design
pattern, not the implementation.

---

## 4. Core Engine: Scene/Scene-Item Model

### Responsibility
Scenes compose sources into layered visual layouts. A scene IS a source (enabling
nesting). Scene items are wrappers pairing a source reference with per-instance
transform, crop, blend, and visibility properties. The same source can appear in
multiple scenes with independent transforms.

### Transform Model
Full per-item state: position (x, y), rotation (degrees), scale (independent x/y),
alignment (anchor point — 9 positions from corners/edges/center), bounds type
(none, stretch, scale-inner/outer, match-width/height, max-only), crop (left/top/
right/bottom pixels, applied before scaling), scale filter (nearest/bilinear/
bicubic/lanczos/area), blend mode (normal, additive, subtract, screen, multiply,
lighten, darken).

### Z-Order
Items stored in an ordered list. Bottom-to-top rendering: index 0 drawn first
(furthest back), last index in front. No z-index numbers — purely positional
in the list.

### Nesting
Because scenes are sources, any scene can contain other scenes as items. Unlimited
depth with cycle detection at insertion time (graph walk, not depth limit). Nested
scenes act as reusable templates — changes propagate everywhere they appear.

### Grouping
Groups are special items containing other items within a single scene. Unlike
nested scenes: cannot exist independently, cannot be shared across scenes, cannot
nest inside other groups (one level only). Organizational sugar with transform
inheritance.

### Design Decision + Why
Separating scene items from sources is the key insight: a source is a content
provider (one webcam), a scene item is a rendering instance with transform state.
One webcam source can appear in five scenes at five different positions without
duplicating the capture. The scene-item is the rendering unit; the source is the
content unit.

### LEVERAGE VERDICT: **INTERNALIZE (own model)**
UMH already has Scene and SourceEntry models. The concepts map directly. Key
gaps to close: crop, rotation, opacity, blend modes, nested scenes, alignment/
anchor points, bounds modes. All implementable via FFmpeg filter parameters
without adopting OBS's in-process rendering.

---

## 5. Core Engine: Audio Pipeline

### Responsibility
Multi-track audio mixing with per-source volume, mute, sync offset, monitoring,
filters, and hierarchical scene-based mixing. Produces mixed audio for encoding
and separate monitoring output.

### Architecture: Pull-Based
Unlike video (push/render-driven), audio is pull-based. The audio thread fires
every 1024 samples (~21.3ms at 48kHz) and pulls mixed audio from the source tree.
This asymmetry matches reality: audio hardware drivers pull on their own clock,
while video rendering is application-driven.

### Signal Path
Source capture → resampling (if rates differ, via swresample with drift
compensation) → per-source circular buffer → audio filter chain (forward order:
noise suppress → gate → compressor → EQ → limiter → gain) → audio tree build
(snapshot to prevent concurrent modification) → hierarchical mixing (leaf→parent,
scenes mix children, transitions crossfade) → volume/balance/mute application →
final mix per track → distribution to encoders + monitoring.

### Multi-Track (Up to 6 Buses)
Each track is an independent mix bus with its own encoder. Sources assigned to
tracks via bitmask. Streaming uses one track; recording can write all six
simultaneously (MKV/MOV containers). Enables separate audio tracks per source
category (game, mic, Discord, music, alerts, spare).

### Per-Source Controls
Volume (linear multiplier, UI shows dB), mute (binary gate), sync offset
(per-source ms delay, positive or negative, output only — doesn't affect
monitoring), balance (sine/square/linear panning law for stereo).

### Monitoring Modes (Per-Source)
Monitor Off (encode only), Monitor Only (local playback, muted from output),
Monitor and Output (duplicated to both). Monitoring taps audio earlier in the
pipeline, so sync offsets don't affect monitored audio.

### A/V Sync
Timestamp-based, not lock-based. Both media types carry nanosecond timestamps.
Audio and video threads run independently. An interleave queue at the output
orders packets by timestamp. Per-source sync offset adds additional timestamp
shift for hardware latency correction. Audio buffers up to ~1 second for
timestamp alignment; sources drifting beyond this are isolated (their audio
drops, not everyone's).

### Design Decision + Why
The pull model and timestamp-based sync avoid the biggest failure modes of real-time
audio: thread starvation (push model can miss deadlines), global dropout from one
bad source (isolation), and A/V drift (timestamps, not frame-counting).

### LEVERAGE VERDICT: **WRAP (FFmpeg audio filters)**
UMH's subprocess FFmpeg model handles audio mixing via the `amix`, `amerge`,
`volume`, `adelay` filters and per-stream mapping. Per-source volume, mute, sync
offset, and multi-track output are all filter_complex capabilities.
Audio filters (compressor, gate, EQ) available as FFmpeg `acompressor`, `agate`,
`equalizer` filters. No need to build a custom pull-based audio subsystem.

---

## 6. Core Engine: Video Pipeline + Frame Timing

### Responsibility
Drives the render loop, manages frame timing at nanosecond precision, handles
resolution scaling, color space conversion, and GPU-to-CPU frame transfer.

### Two-Thread Architecture
Graphics thread: owns GPU context, runs tick→render loop at configured FPS.
Video output thread: waits on semaphore, maps staged frames, distributes to
encoders and raw callbacks. Separating these prevents slow encoders from stalling
the render pipeline.

### Per-Frame Stages
1. Tick: traverse all sources, call per-frame update with elapsed time
2. Render: enter GPU context, traverse scene graph, invoke source render callbacks
3. Scale: GPU-based scaling if output differs from canvas (bilinear/bicubic/lanczos/area)
4. Color convert: RGB→YUV via GPU shaders, each plane to dedicated texture
5. Stage: double-buffered async GPU→CPU transfer (frame N copies to surface A while
   frame N-1 reads from surface B — prevents pipeline stalls)
6. Distribute: post semaphore to wake encoding thread, pass to raw callbacks

### Two-Resolution Model
Base canvas (virtual workspace for positioning) vs output resolution (what gets
encoded). Independent — canvas can be 1920x1080 for layout, output 1280x720 for
bandwidth. Per-source scale filtering is independent of global output scaling.

### Frame Timing
Nanosecond precision: interval = 1,000,000,000 * denominator / numerator. Supports
fractional rates (29.97 = 30000/1001). After each frame, sleep to next target time.
No catch-up on overload — late frames tracked in stats, cadence continues.

### GPU Texture Pass-Through
When an encoder declares GPU texture capability, staging is bypassed entirely.
GPU texture handle passed directly to encoder — zero CPU copy. Eliminates the
single biggest latency bottleneck for hardware encoding.

### Frame Duplication Strategy
When encoder can't keep up, duplicate last frame rather than drop.
Duplicate frames compress to almost nothing via temporal prediction (encoder
finds zero motion), reducing CPU load rather than increasing it. Trades minor
visual stutter for encoding stability.

### LEVERAGE VERDICT: **WRAP (FFmpeg)**
FFmpeg handles frame timing, scaling, color conversion, and encoding internally.
UMH's subprocess model delegates all of this. For GPU-accelerated encoding:
FFmpeg's `-hwaccel` flags and hardware codec selections.
The double-buffered staging concept is irrelevant — FFmpeg manages its own
internal pipeline.

---

## 7. Core Engine: Encoder Abstraction

### Responsibility
Uniform interface between raw media and the output layer. The core never talks
to x264, NVENC, or any vendor SDK directly — only through the encoder abstraction
via function pointer callbacks.

### Dual Input Paths
Raw frame path: planar YUV in system memory. Used by software encoders and some
HW encoders. GPU texture path: direct GPU texture handles, zero CPU copy. Declared
via capability flag. Used by NVENC, QSV, AMF, VideoToolbox when available.

### Codec vs Encoder Identity
"codec = h264" is separate from "encoder id." Multiple encoder implementations
produce the same codec. Output layer cares about codec; core cares about encoder
instance. This enables transparent swapping.

### Self-Describing Settings
Each encoder declares its own configuration via the properties system. No hardcoded
settings panels. New encoders added as plugins get automatic UI. Settings include
codec-specific parameters (preset, profile, level, rate control, bitrate,
quality target).

### Encoder-Output Relationship
One encoder can connect to multiple outputs simultaneously. Encoded packets carry
PTS/DTS, keyframe markers, priority, and track index. This enables stream + record
from the same encoder without double-encoding.

### Hardware Detection
External probe executables detect GPU encoder availability without loading vendor
libraries into the main process. Failed detection = encoder type not registered.
No automatic runtime fallback from hardware to software — explicit user choice,
with the auto-config wizard making the initial recommendation.

### Supported Encoders
Video: x264 (H.264), x265 (H.265), NVENC (NVIDIA), QSV (Intel), AMF (AMD),
VAAPI (Linux HW), Apple VideoToolbox, SVT-AV1.
Audio: FFmpeg AAC, CoreAudio AAC, libfdk_aac, Opus.

### LEVERAGE VERDICT: **WRAP (FFmpeg)**
FFmpeg already abstracts every encoder OBS supports and more. `-c:v libx264`,
`h264_nvenc`, `h264_qsv`, `h264_vaapi`, `h264_videotoolbox`
are direct FFmpeg codec selections. UMH's model of building FFmpeg CLI arguments
already handles this. Gap: UMH currently hardcodes libx264. Expanding to hardware
encoders is a configuration change, not an architectural one.

---

## 8. Core Engine: Output Abstraction

### Responsibility
Final delivery of encoded (or raw) media to destinations: streaming servers,
files, replay buffers, virtual cameras. Manages the interleave queue that orders
audio and video packets by timestamp for monotonic delivery.

### Output Types
**Encoded outputs**: receive compressed packets from encoders. Examples: RTMP
streaming, MP4/MKV/FLV recording. **Raw outputs**: receive uncompressed frames
directly. Example: virtual camera. Outputs can be video-only, audio-only, or both.
Multi-track outputs support multiple audio encoders.

### Reconnection
Streaming outputs implement automatic reconnection with configurable delay and
retry count. During reconnection, encoding continues but packets are discarded
until connection re-establishes and a new keyframe arrives. This means the encoder
never stops — reconnection is seamless from the encoding perspective.

### Replay Buffer
Circular buffer of the most recent N seconds of encoded data in memory. On trigger,
writes buffer to file. Buffer size configured in seconds; actual memory depends on
bitrate. Enables "clip that" functionality without continuous recording.

### Virtual Camera
Creates a virtual video device that other applications see as a camera. Receives
raw frames, not encoded. Platform-specific device creation.

### Multi-Output
Multiple outputs can run simultaneously: stream to platform + record to file + feed
virtual camera. Each output independently connects to encoders (can share or have
dedicated ones).

### LEVERAGE VERDICT: **INTERNALIZE (own output management)**
UMH already manages FFmpeg subprocess outputs. Key gaps to close: simultaneous
multi-output (stream + record), replay buffer (FFmpeg segment muxer + buffer),
reconnection logic (FFmpeg's `-reconnect` flags plus UMH-level process recovery).
Virtual camera is DEFER — requires platform-specific kernel modules and is
irrelevant for server-side operation.

---

## 9. Core Engine: Service Abstraction

### Responsibility
Decouples "where to send" from "how to send." An output knows the protocol
(RTMP/SRT); a service knows the specific server URL, stream key, and platform
requirements. Provides connection information to outputs.

### What a Service Provides
Server URL, stream key, platform-specific requirements (recommended encoders,
bitrate limits, audio track count), authentication tokens for OAuth-based
platforms. A built-in service database includes known streaming platforms with
their ingest servers and recommended settings.

### Service-Output Binding
A service binds to an output. When the output starts, it queries the service for
connection details. The service can apply platform constraints (required encoder
settings, maximum bitrate).

### Design Decision + Why
Separating service from output enables the same RTMP output to work with any
platform. Platform-specific knowledge (ingest server selection, bitrate caps,
required encoder settings) lives in the service, not the output. New platforms
added by creating service plugins without modifying output code.

### LEVERAGE VERDICT: **INTERNALIZE (own service registry)**
UMH needs a service/destination registry mapping platform names to connection
parameters. Much simpler than OBS's plugin model — a JSON configuration file
with platform templates (Twitch, YouTube, custom RTMP) containing server URL
patterns, recommended settings, and key storage references. The separation of
"where" from "how" is the right pattern.

---

## 10. Core Engine: Module/Plugin System

### Responsibility
Discovery, loading, version validation, and registration of plugins that provide
sources, outputs, encoders, and services. Most "built-in" functionality ships
as plugins through this system.

### Loading Lifecycle
Search configured directories → load shared library → give module its handle →
call module load function → module registers types (sources, outputs, encoders,
services) with the core → types stored in global arrays indistinguishable from
built-in ones. Version check (major.minor comparison) rejects plugins built
against newer core versions.

### Plugin Equality
Registered types stored in the same arrays regardless of origin. Third-party
plugins indistinguishable from built-in ones in API and UI. Full extensibility
without core modification.

### LEVERAGE VERDICT: **DEFER**
UMH's extensibility model is the capability handler protocol + integration
registry, not dynamic library loading. The OBS plugin system solves desktop
application extensibility. UMH solves server-side AI-operable broadcasting.
Different problem space. UMH's existing CapabilityHandler + IntegrationManifest
pattern is the right abstraction for this system.

---

## 11. Capability Surface: Capture Sources

### All Source Types

| Source | What It Captures | Key Capability |
|--------|-----------------|----------------|
| Window Capture | Single app window | Isolates one app; GDI/WGC/ScreenCaptureKit/PipeWire/XComposite |
| Display Capture | Entire monitor | Desktop Duplication/ScreenCaptureKit/PipeWire — captures everything |
| Game Capture | Game render pipeline | DLL injection, hooks Present, GPU shared texture (zero CPU copy). Windows only. |
| Video Capture Device | Cameras, capture cards | DirectShow/AVFoundation/V4L2, resolution/FPS negotiation, embedded audio |
| Image | Static image file | PNG/JPG/BMP/GIF/TIFF, alpha, file-change monitoring |
| Image Slideshow | Image rotation | Transitions, duration, loop/random, hotkey advance |
| Media Source | File/network playback | FFmpeg-based, any format, HW decode, transport controls, loop, speed |
| Browser Source | Web content | Full Chromium (CEF), custom CSS, JS bridge, interaction |
| Text Source | Rendered text | GDI+/FreeType2, read-from-file auto-update |
| Color Source | Solid color | RGBA with alpha, layout building block |
| Audio Input | Microphones | WASAPI/CoreAudio/PulseAudio, full filter chain |
| Audio Output | Desktop/app audio | WASAPI loopback, per-app capture (Win), PulseAudio monitor |
| VLC Source | Media + playlists | Playlist, subtitles, multi-track audio selection |
| NDI Source | Network video (plugin) | mDNS discovery, bandwidth modes, alpha, PTZ control |
| Scene Source | Nested scene | Hierarchical composition, reusable templates |
| Group Source | Item container | Organizational, transform inheritance, single-scene only |

### LEVERAGE VERDICT (per source type)

| Source | Verdict | Notes |
|--------|---------|-------|
| Test Pattern | WRAP (FFmpeg lavfi) | Already shipped (Slice 0) |
| Camera (V4L2) | WRAP (FFmpeg v4l2) | Already shipped (Slice 0, Linux only) |
| RTMP/SRT Pull | WRAP (FFmpeg) | Already shipped (Slice 0) |
| File Playback | WRAP (FFmpeg) | Already shipped (Slice 0) |
| Display/Window Capture | WRAP (FFmpeg x11grab/pipewire/gdigrab) | Requires X11/PipeWire on server |
| NDI | WRAP (FFmpeg + libndi) | NDI SDK required |
| Browser Source | DEFER | Requires CEF/headless Chrome — heavy for server |
| Image Source | WRAP (FFmpeg image2) | Simple, high value for overlays |
| Text Source | WRAP (FFmpeg drawtext) | Requires font rendering, moderate complexity |
| Color Source | WRAP (FFmpeg color lavfi) | Trivial — already possible via test patterns |
| Audio Input/Output | WRAP (FFmpeg ALSA/PulseAudio) | Needed for audio pipeline |
| Image Slideshow | INTERNALIZE | Build on image source + timer logic |
| Media playlist | WRAP (FFmpeg concat) | FFmpeg concat demuxer handles playlists |
| Game Capture | DEFER | Windows DLL injection — irrelevant for server |

---

## 12. Capability Surface: Filter Catalog

### Video/Effect Filters

| Filter | What It Does | Design Rationale |
|--------|-------------|-----------------|
| Color Correction | Brightness, contrast, gamma, hue, saturation, opacity | Five matrices → single GPU pass |
| LUT | 3D color mapping from .cube files | Arbitrary nonlinear transforms impossible with manual correction |
| Chroma Key | Green/blue screen removal | YCbCr chrominance space — tolerant of lighting variation |
| Color Key | RGB-space color removal | Simpler than chroma — best for digitally precise colors |
| Crop/Pad | Edge cropping or padding | Global (all scenes), vs scene-item crop (per-instance) |
| Scaling/Aspect Ratio | Resolution/aspect forcing | Five algorithms from nearest neighbor to lanczos |
| Sharpen | Unsharp mask | Single parameter, GPU convolution |
| Scroll | Continuous motion | Ticker text, moving backgrounds |
| Image Mask/Blend | Alpha mask or blend layer | Vignettes, shaped overlays |
| Render Delay | Video delay in ms | A/V sync correction for high-latency cameras |
| Luma Key | Luminance-based keying | Key out white/black backgrounds |
| HDR Tonemap | HDR→SDR conversion | BT.2408 mapping |

### Audio Filters

| Filter | What It Does | Design Rationale |
|--------|-------------|-----------------|
| Gain | Volume adjustment (dB) | Before other processors in chain |
| Noise Suppression | ML noise removal | RNNoise (ML), Speex (DSP), NVIDIA (GPU AI) |
| Noise Gate | Binary mute below threshold | Three-state with hysteresis prevents flutter |
| Compressor | Dynamic range compression | Ratio/threshold/attack/release/makeup + sidechain ducking |
| Limiter | Hard level ceiling | Infinite ratio compressor, always last |
| Expander | Graduated level reduction | Inverse of compressor, more nuanced than gate |
| 3-Band EQ | Low/mid/high shelf | Intentionally simple — VST for detailed work |
| VST 2.x | Third-party audio plugins | Opens pro-audio ecosystem |

### Filter Chain Order
Video: reverse order (bottom-to-top) for GPU texture chaining.
Audio: forward order (top-to-bottom), signal processing convention.
Recommended audio: noise suppress → gate → compressor → EQ → limiter → gain.

### Async vs Sync Filter Distinction
Async: timestamped frames from hardware (variable timing). Sync (effect): within
GPU render pipeline at fixed framerate. Camera inputs inherently async; rendering
inherently sync.

### LEVERAGE VERDICT

| Filter Category | Verdict | FFmpeg Equivalent |
|-----------------|---------|-------------------|
| Color correction | WRAP | eq, colorbalance, hue |
| LUT | WRAP | lut3d (.cube native) |
| Chroma/Color/Luma key | WRAP | chromakey, colorkey, lumakey |
| Crop | WRAP | crop filter |
| Scale | WRAP | scale filter (already used) |
| Blur | WRAP | boxblur, gblur |
| Audio gain/volume | WRAP | volume filter |
| Noise suppression | WRAP | arnndn or afftdn |
| Compressor/Gate/Limiter | WRAP | acompressor, agate, alimiter |
| EQ | WRAP | equalizer |
| VST | DEFER | Desktop-only, irrelevant for server |

---

## 13. Capability Surface: Transition System

### Responsibility
Animates the visual (and audio) switch between two scenes. A transition takes
ownership of both scenes and composites them over a configurable duration.

### How Transitions Work
Transitions ARE sources. When triggered, the transition source takes scenes A and B
as children. During the transition period, it composites both (blend, slide, wipe)
and crossfades audio. The output encoder reads the transition output during switch.

### Transition Types
**Cut**: instantaneous, zero intermediate frames.
**Fade**: opacity crossfade (default 300ms).
**Stinger**: video with alpha over a cut — at the "transition point" (full cover
frame), cuts A→B underneath. Broadcast-industry standard for branded transitions.
**Swipe**: B enters from a direction, sliding over A.
**Slide**: both scenes move together like a conveyor belt.
**Fade to Color**: A fades to solid, solid reveals B.
**Luma Wipe**: grayscale image controls per-pixel reveal order.
**Custom Shader**: arbitrary GPU compositing.

### Configuration Layers
Global default → per-transition instances → per-scene overrides (fires when
switching TO that scene) → per-quick-transition in Studio Mode → source show/hide
transitions (per-source, independent of scene switching).

### Design Decision + Why
Making transitions sources means they use the standard rendering pipeline.
Can have filters, emit signals, compose with everything else. No special-casing.

### LEVERAGE VERDICT: **WRAP (FFmpeg xfade + ZMQ opacity)**
FFmpeg's `xfade` filter for pre-built transitions. For live use: ZMQ-based
opacity animation over ~300ms for crossfades. Stinger transitions: overlay
a pre-rendered video with alpha over the cut point. UMH currently does instant
cuts only. Adding transitions = ZMQ opacity control + timing logic.

---

## 14. Capability Surface: Studio Mode

### Responsibility
Two-panel preview/program model. Preview = staging (viewers can't see). Program =
live output. Non-destructive editing.

### Workflow
Click scene → Preview only. Edit freely. Click Transition → Preview goes to
Program. Scene hotkeys change Preview; separate hotkey fires transition.

### Controls
Main transition button, quick transitions (each with own type/duration/hotkey),
T-bar slider for manual fade control.

### Design Decision + Why
PVW/PGM model from professional broadcast switchers. The key insight: live
production requires a staging area where mistakes don't go to air.

### LEVERAGE VERDICT: **INTERNALIZE (cockpit UI + dual output)**
Engine needs dual output: one for preview (to cockpit via HLS/WebRTC), one for
program (to RTMP). In FFmpeg: filter_complex with two output pads, or tee muxer.
Lower priority than core pipeline capabilities.

---

## 15. Capability Surface: Properties/Settings

### Responsibility
Self-describing configuration. Plugins declare settings schema; UI renders
automatically; settings persisted as JSON-like key-value data.

### Two Objects
**Properties** (schema): types, constraints, UI behavior. Ephemeral.
**Data** (values): three-tier — user values, defaults, auto-select suggestions.
Persisted as JSON.

### Property Types
Bool, Int (spinbox/slider), Float, Text (single/password/multiline/info),
Path (file/save/directory), List (dropdown/editable/radio), Color (with/without
alpha), Font, Button, Editable List, Frame Rate, Group (normal/checkable).

### Dynamic Properties
Modification callbacks: changing one value shows/hides others, modifies lists,
changes constraints. Enables conditional configuration forms.

### LEVERAGE VERDICT: **INTERNALIZE (Pydantic models + cockpit forms)**
UMH already uses Pydantic for config. Cockpit renders forms from models.
Gap: no dynamic property system. Pydantic discriminated unions handle
conditional fields for now.

---

## 16. Capability Surface: Profiles & Scene Collections

### Profiles
Encoding/output/service settings ("how"). Video resolution, FPS, audio sample
rate, service config, encoder settings. Lightweight switching.

### Scene Collections
Visual content ("what"). All scenes, sources, transforms, filters. Single JSON.
Heavyweight switching (full teardown/rebuild).

### Design Decision + Why
Independent axes. Same scenes to different platforms (switch profile). Different
layouts to same platform (switch collection). No unnecessary duplication.

### LEVERAGE VERDICT: **INTERNALIZE (own config model)**
CompositeConfig already contains output params (profile) + scene definitions
(collection). Making them independently storable/switchable is a data modeling
task. High value, low complexity.

---

## 17. Capability Surface: Stats/Performance

### Three-Stage Drop Detection
**Rendering lag**: GPU compositing exceeded frame interval.
**Encoding lag**: encoder can't keep up.
**Network drops**: send buffer overflow.
Three independent counters for precise diagnosis.

### Metrics
CPU, memory, disk, active FPS, render time (ms), missed/skipped/dropped counts,
actual bitrate, total bytes, stream duration, congestion.

### Adaptive Behavior
Dynamic bitrate (opt-in): reads congestion, lowers bitrate instead of dropping.
Only adaptive behavior — no auto resolution/preset/FPS.

### LEVERAGE VERDICT: **INTERNALIZE (already partially built)**
BroadcastHealth already parses FFmpeg progress (fps, bitrate, dropped, speed,
uptime, tier). Gaps: separate render/encode/network counters (FFmpeg lumps
together), dynamic bitrate adaptation, CPU/memory monitoring.

---

## 18. Capability Surface: Projectors

### Responsibility
Auxiliary output displays — fullscreen, multiview (grid of scenes with live/preview
color borders), windowed. Reuses rendered textures (lightweight).

### LEVERAGE VERDICT: **DEFER**
Desktop concept. UMH equivalent: cockpit broadcast panel (already exists). Preview
stream via HLS/WebRTC would serve the same purpose. Lower priority.

---

## 19. Capability Surface: Hotkeys

### Responsibility
Focus-independent keyboard shortcuts. 40Hz polling thread with platform-specific
key state queries.

### Categories
Per-source (show/hide, mute, push-to-talk), global (start/stop stream/record),
scene switching, transition triggers.

### LEVERAGE VERDICT: **DEFER**
Desktop interaction model. UMH equivalent: WebSocket commands from cockpit, API
calls from agents. Already covered by existing HTTP + WS API.

---

## 20. Capability Surface: Auto-Config

### Responsibility
First-run wizard: test bandwidth, detect HW encoders, recommend resolution/FPS/
bitrate/encoder.

### Tests
Bandwidth: dummy stream to ingest, 10s measurement, 30% safety haircut.
Encoder: probe executables detect GPU (NVENC > QSV > VT > AMF > x264).
Resolution: descending ladder with actual encoding.
FPS: prefer 60fps if achievable at >= 960x540.

### LEVERAGE VERDICT: **INTERNALIZE (simplified)**
Detect FFmpeg encoders (`-encoders`), test RTMP connectivity, select optimal
config based on node resources. Simpler than OBS because UMH controls the
hardware (VPS/Beast, not unknown user machines).

---

## 21. Capability Surface: Remote Control Protocol

### Responsibility
WebSocket RPC for programmatic control of all broadcast functions.

### Protocol
WebSocket, JSON or MessagePack, SHA256 challenge-response auth, multiple
simultaneous clients, sub-10ms localhost latency.

### Request Surface (133+ requests)
General (8), Config (17), Sources (3), Scenes (11), Inputs (28), Filters (10),
Scene Items (20), Outputs (17), Stream (5), Record (9), Media (4), UI (8),
Transitions (9). Every user-facing action available programmatically.

### Event Surface (61+ events)
All categories. Subscription via bitmask. High-volume events require explicit
opt-in.

### Batch Requests
Serial realtime, serial frame-synced (one per render frame), parallel.

### Key Integrations
Stream Deck, Touch Portal, Bitfocus Companion, Streamer.bot, tally lights,
web dashboards, automation systems.

### LEVERAGE VERDICT: **INTERNALIZE (already partially built)**
UMH has HTTP REST + WS health push + ZMQ scene control. Gaps vs full remote
control: bidirectional WS commands, source CRUD while live, filter management,
recording control, batch commands, event subscriptions. Target: equivalent
programmatic control via UMH's existing API pattern, not obs-websocket replication.

---

## 22. Data Flow: Threading Model

### Four Threads (OBS)
**Graphics/Render**: owns GPU context, tick→render at FPS.
**Video encoding/output**: waits on semaphore, routes to encoders.
**Audio**: fires every ~21.3ms, pulls from source buffers.
**UI**: Qt event loop, never touches GPU.

### UMH Equivalent
FFmpeg subprocess collapses these into one (internally threaded). Python asyncio
handles API/WS/health concurrently. No explicit thread management needed.

---

## 23. Data Flow: Video Frame Path

### Pipeline
Source → (async: queued; sync: rendered) → scene composites with transforms →
filter chain → output scale → color convert → stage to CPU (or GPU texture to
HW encoder) → encoder → interleave queue → output.

### Key Mechanisms
Async frame selection, double-buffered staging, GPU texture pass-through,
frame duplication on overload.

### UMH Equivalent
FFmpeg filter_complex IS the scene graph. Scaling, color conversion, encoding,
muxing are FFmpeg-internal. UMH's role: build filter_complex, start FFmpeg,
modify via ZMQ.

---

## 24. Data Flow: Audio Signal Path

### Pipeline
Source → resample → circular buffer → filter chain → tree snapshot → hierarchical
mix → volume/balance/mute → final mix per track → encoders + monitoring.

### Key Mechanisms
Pull model (~21.3ms), multi-track mixing (6 buses), monitoring tap before sync
offset, timestamp alignment with ~1s buffer, lagging source isolation.

### UMH Equivalent
FFmpeg audio pipeline via filter_complex: `amix` for mixing, `volume` for
per-source gain, `adelay` for sync offset, dynamics filters for processing.
Multi-track via multiple `-map` outputs.

---

## 25. Data Flow: Scene Rendering Pipeline

### Traversal
Enumerate items → per item: visibility check → crop (before scale) → transform
matrix (position × rotation × scale × alignment) → bounds → render source →
blend mode → composite onto buffer → next item.

### Filter Application
Video: reverse order (texture chain). Audio: forward order (signal chain).

### UMH Equivalent
FFmpeg overlay filter chain. Scale → overlay at position, enable/disable via ZMQ.
Z-order = overlay chain order. Crop, rotation, blend modes available as FFmpeg
parameters but not yet wired in UMH.

---

## 26. Cross-Cutting Design Principles

| Principle | OBS | UMH Equivalent |
|-----------|-----|----------------|
| Everything is a source | Universal primitive, flags | SourceEntry model — needs capability flags |
| Callback-table polymorphism | C function pointer structs | Python Protocol + CapabilityHandler |
| Self-describing config | Properties schema + data | Pydantic models (already) |
| Timestamp-based A/V sync | Nanosecond timestamps | FFmpeg handles internally |
| GPU-first rendering | Custom GPU abstraction | N/A — FFmpeg handles rendering |
| Plugin equality | Same registration arrays | CapabilityHandler + IntegrationManifest |
| Frontend/backend separation | libobs + any frontend | Engine (Python) + Cockpit (React) |
| Conveyor belt pipeline | Double-buffered staging | FFmpeg's internal pipeline |
| Scene-item/source separation | Rendering unit vs content unit | Scene/SourceEntry (already) |

---

*Document produced 2026-06-13. Ephemeral quarantine read. Zero GPL expression.*
*Concepts, design rationale, and capability descriptions only.*
