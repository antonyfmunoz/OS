# UMH Broadcast Build Plan (Re-Derived from Full OBS Architecture + Organism Placement)

> **Supersedes**: The ad-hoc Wave 1/2/3 list AND the first re-derivation. This
> version corrects a silent assumption in the prior plan — that the engine lives
> on the VPS (Linux) — by encoding UMH's actual deployment reality: **VPS + Beast
> (local Windows workstation) + iPhone are one organism.** The engine is
> node-portable; capture and hardware encode are first-class organism capabilities,
> not deferred phases.

> **Principle**: UMH wraps FFmpeg where OBS wraps GPU APIs. Every capability maps
> to FFmpeg `filter_complex` parameters, codec flags, or muxer options — not
> in-process rendering. The differentiator is **AI-operable broadcasting across an
> organism**: agents and cells control the same socket as humans, and that socket
> drives the engine on whichever node holds the capability. No other broadcast tool
> has either property.

-----

## Organism Placement Model (read this first)

The control-plane socket (HTTP + WS) is **node-agnostic**. The engine is **node-portable**.
The same socket that makes the engine dual-*consumer* (human cockpit + agent cells) makes it
dual-*node* (VPS + Beast). The cockpit and agent cells address the engine over Tailscale
**without caring which box it runs on**.

### Node roles

|Node                           |Address            |Role                                                                      |Has                                                                                   |
|-------------------------------|-------------------|--------------------------------------------------------------------------|--------------------------------------------------------------------------------------|
|**Beast** (Windows workstation)|`100.74.199.102`   |**Production capture + encode engine**                                    |Real display/window/webcam capture, mic + system audio, **NVENC** hardware encode, GPU|
|**VPS** (Ubuntu, headless)     |`100.77.233.50`    |**Control plane + agent orchestration + always-on synthetic/relay engine**|No capture devices, no GPU, always-on                                                 |
|**iPhone**                     |(Termius/Tailscale)|Control surface                                                           |—                                                                                     |

### Node-aware capability resolution

A single uniform socket capability resolves to the right FFmpeg construct **per node**. The
caller (human or agent) asks for `"display capture"` or `"mic"`; the engine resolves it for the
node it's running on:

|Capability               |Beast (Windows)                                          |VPS (Linux)                        |
|-------------------------|---------------------------------------------------------|-----------------------------------|
|Display capture          |`ddagrab` (Desktop Duplication, GPU) / `gdigrab` fallback|`x11grab` (needs Xvfb)             |
|Window capture           |`gdigrab title=` / `ddagrab` output                      |`x11grab` window id                |
|Webcam                   |`-f dshow -i video="<name>"`                             |`-f v4l2 -i /dev/videoN`           |
|Mic / audio device       |`-f dshow -i audio="<name>"`                             |`pulse` / `alsa`                   |
|System (loopback) audio  |WASAPI loopback / loopback capture device                |pulse monitor source               |
|Hardware encode          |`h264_nvenc` / `hevc_nvenc`                              |`x264` (sw) or `vaapi`/`qsv` if GPU|
|Synthetic / relay sources|lavfi, file, RTMP/SRT pull (node-independent)            |lavfi, file, RTMP/SRT pull         |

**Windows system-audio capture is finicky** — it usually requires a loopback device. This is
a specific derisk item, not a given.

### Why NVENC on the Beast is also a license win

Hardware encoders (`h264_nvenc`/`hevc_nvenc`) sidestep the **x264 GPL flip** the LICENSE_FIREWALL
flagged: software x264 in an FFmpeg build pulls GPL, while NVENC keeps the FFmpeg dependency
cleanly **LGPL** (CLI subprocess, no `libav*` linking). Performance *and* license cleanliness in
one move — so the Beast's GPU encode is the preferred production path, not just the fast one.

-----

## What's Already Shipped (all VPS-hosted, synthetic sources)

### Slice 0 — Single-Source Broadcast (COMPLETE)

- BroadcastEngine state machine (idle -> starting -> live -> stopping)
- ProcessLifecycle (process group isolation, CPU gate, SIGTERM->SIGKILL)
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

- `filter_complex` builder (canvas + scaled overlays + ZMQ named filters)
- Scene/SourceEntry/SourceLayout/CompositeConfig Pydantic models
- ZMQ client (per-command fresh socket, batch with abort semantics)
- Live scene switching via ZMQ overlay repositioning (~200ms, no FFmpeg restart)
- Composite start API + scene switch API + scene list API
- Cockpit scene switcher UI (conditional on composite + live)
- 25 filtergraph tests (overlays, z-order, scenes, injection prevention)
- nginx WS upgrade block; frontend Clerk auth; backend subprotocol echo (deployed v239)

> **Reality check**: everything shipped runs on the VPS with synthetic/file/pull sources. No
> real capture, no real audio, no hardware encode, no Beast engine node yet. Against the full
> OBS surface this is **~15%** of capabilities — and all of it on the node that has none of the
> real hardware.

-----

## Coverage Assessment (against full OBS surface + organism placement)

|OBS Subsystem                                  |UMH Status                                      |Production Node|Priority        |
|-----------------------------------------------|------------------------------------------------|---------------|----------------|
|Graphics/Compositor                            |N/A (FFmpeg wraps)                              |either         |—               |
|Source primitive                               |Partial (SourceEntry, no capability flags)      |either         |HIGH            |
|Scene/Scene-item                               |Partial (no crop/rotation/opacity/blend/nesting)|either         |HIGH            |
|Audio pipeline                                 |**ABSENT** (silent `anullsrc` placeholder)      |either         |**CRITICAL**    |
|Real capture (display/window/webcam/mic/system)|**ABSENT**                                      |**Beast**      |**HIGH**        |
|Hardware encode (NVENC)                        |**ABSENT** (x264 only)                          |**Beast**      |**HIGH**        |
|Cross-node engine placement                    |**ABSENT** (VPS-only today)                     |organism       |**FOUNDATIONAL**|
|Video pipeline                                 |WRAPPED (FFmpeg)                                |either         |—               |
|Output abstraction                             |Partial (stream only, no record)                |either         |HIGH            |
|Service abstraction                            |ABSENT                                          |either         |MEDIUM          |
|Video filters                                  |ABSENT                                          |either         |HIGH            |
|Audio filters                                  |ABSENT                                          |either         |HIGH            |
|Transitions                                    |ABSENT (instant cut only)                       |either         |MEDIUM          |
|Studio mode                                    |ABSENT                                          |either         |LOW             |
|Properties/settings                            |Partial (Pydantic)                              |either         |LOW             |
|Profiles/collections                           |ABSENT                                          |either         |MEDIUM          |
|Stats/performance                              |Partial (health monitor)                        |either         |LOW             |
|Remote control                                 |Partial (HTTP + WS health, no bidirectional WS) |either         |MEDIUM          |
|Module/plugin system                           |N/A (CapabilityHandler)                         |—              |DEFER           |
|Projectors / Hotkeys                           |N/A (cockpit / API serve these)                 |—              |DEFER           |

-----

## Re-Derived Critical Path

Sequenced by dependency order + organism placement. **Phase 0 is new and foundational** —
everything "real" sits on top of the engine actually running where the hardware is.

### Phase 0: Organism Engine Placement (FOUNDATIONAL — everything real depends on it)

**Why first**: Every real capability (real capture, real audio, hardware encode) lives on the
Beast. None of it is reachable until the engine can run on the Beast and be driven from the VPS
control plane. This is the deferred cross-host piece finally made foundational.

**What to build**:

1. Engine as a node-portable process (already decoupled from the control plane — formalize it)
1. Beast runs an engine instance (Windows process / service), reachable over Tailscale
1. VPS control plane (cockpit backend + agent cells) starts/stops/drives the Beast engine via
   the existing broadcast socket — same API, different node target
1. Engine registration/addressing: the socket resolves "which engine on which node"
1. Health/status surfaced per node in the cockpit
1. Secret + egress hygiene over Tailscale (no host-networking; keep container/process isolation)

**Acceptance**: the deployed cockpit on the VPS starts an engine instance **on the Beast**,
streams a source, and reports health — same socket, different box. Cross-node proven.

**Scope**: Medium. No new broadcast capability — it's the substrate the rest runs on.

### Phase 1: Audio Pipeline (CRITICAL — biggest capability gap)

**Why here**: A broadcast tool without audio is a slideshow. The mixing *mechanics* are
node-independent, so they can be derisked and built with file/lavfi audio. The *real* target,
though, is **mic + system audio mix on the Beast** — the actual streamer scenario.

**Derisk first (spike — node-independent)**: confirm which params are live-ZMQ-commandable —
`volume` (expected yes), mute via `volume=0` (yes), sync offset via `adelay` (likely
**launch-time only**, verify), `amix weights` (version-dependent), and the **level readback path
for VU meters** (ZMQ is command-in only — levels must come out via `astats`/`ebur128` ->
metadata; this is the risky one).

**What to build**:

1. Per-source audio input in `filter_complex` (real inputs where present, `anullsrc` fallback)
1. Audio mixing via `amix`/`amerge`
1. Per-source volume via `volume` (ZMQ-addressable)
1. Per-source mute (`volume=0` via ZMQ)
1. Per-source sync offset via `adelay` (launch-time unless spike proves otherwise)
1. AAC encode for output (already in args — just feed real audio)
1. Level/VU readback path proven in the spike, surfaced to the cockpit
1. Cockpit audio mixer UI (per-source volume sliders, mute toggles, VU meters)
1. API: set volume, set mute, get audio levels

**Real validation**: mic + system audio mixed on the Beast (depends on Phase 2 capture for the
real inputs; mechanics validated earlier with file/lavfi).

**Wraps**: FFmpeg `amix`, `volume`, `adelay`, `pan`. **Scope**: Medium.

### Phase 2: Real Capture + Hardware Encode (Beast — node-aware) — pulled forward

**Why here** (was buried at old Phase 6/7, Linux-only): real capture and NVENC are first-class
organism capabilities available on the Beast *now*. They are the foundation of a real broadcast
tool — without them it's test patterns. Together with Phase 1 they form the streamer MVP:
capture screen + mic + system audio, mix, NVENC-encode, stream.

**What to build**:

1. Node-aware input resolution (the capability->construct table above): `ddagrab`/`gdigrab`,
   `dshow` (webcam + audio device), WASAPI/loopback (system audio) on Windows; `x11grab`/`v4l2`/
   `pulse` on Linux
1. NVENC hardware encode (`h264_nvenc`/`hevc_nvenc`) on the Beast; encoder selection by node
1. Encoder detection (probe FFmpeg `-encoders` per node)
1. Capability flags on the source primitive (which inputs a node can satisfy)
1. Windows system-audio loopback handling (the derisk item)
1. Cockpit source picker that reflects the node's available devices

**Wraps**: FFmpeg platform input drivers + NVENC. **Scope**: Medium-Large.

### Phase 3: Recording + Multi-Output

**Why here**: Stream AND record simultaneously is the second most-asked feature after "go live,"
and establishes the multi-output pattern that replay buffer and studio mode need.

**What to build**:

1. Multi-output via FFmpeg `tee` muxer (or multiple `-f` outputs)
1. Recording to MKV/MP4 (configurable container)
1. Simultaneous stream + record from the same encode
1. Recording start/stop/pause API (independent of stream)
1. Output directory + timestamped file naming
1. Cockpit recording controls
1. Multi-track audio recording (separate tracks per source to MKV)

**Wraps**: FFmpeg `-f tee`, segment muxer. **Scope**: Medium.

### Phase 4: Source Transform Completeness

Crop, rotation, opacity, blend modes, bounds (fit/fill/stretch), alignment/anchor, grouping,
nested scenes. Extends the `filter_complex` builder + `scene_model.py`; cockpit transform UI.
**Wraps**: FFmpeg `crop`, `rotate`, `blend`, `format`. **Scope**: Medium-Large.

### Phase 5: Video + Audio Filters

**Video**: color correction (`eq`/`hue`), chroma key (`chromakey`), color key (`colorkey`), LUT
(`lut3d`), blur (`gblur`), sharpen (`unsharp`), mask/blend.
**Audio**: noise suppression (`arnndn`), gate (`agate`), compressor (`acompressor`), limiter
(`alimiter`), EQ (`equalizer`), gain. Per-source ordered filter chain, ZMQ-addressable params,
add/remove/reorder/configure API, cockpit filter panel. **Scope**: Large (each is a thin wrap).

### Phase 6: Transitions

Fade (ZMQ opacity crossfade), cut (exists), stinger (alpha overlay video), configurable
duration, transition model + API + cockpit controls. Crossfade via ZMQ opacity animation; no
FFmpeg restart. **Wraps**: ZMQ param animation + FFmpeg overlay alpha. **Scope**: Medium.

### Phase 7: Service Registry

Service templates (Twitch/YouTube/Kick/custom RTMP: server URL pattern, stream-key ref via
1Password, recommended settings, bitrate caps), select/validate API, cockpit service selector +
test button. Codec parameter exposure (preset/profile/bitrate/rate-control) — *hardware encoder
support already landed in Phase 2.* **Scope**: Medium.

### Phase 8: Additional Source Types (synthetic / generated / relay)

Image (`image2`), text (`drawtext`), color (`color` lavfi), NDI input (`libndi` if present),
audio-only file/lavfi sources. *(Device captures moved up to Phase 2.)* Each is a new input
builder in `ffmpeg_args.py`. **Scope**: Medium.

### Phase 9: Replay Buffer + Live Source CRUD

Replay: circular segment buffer, save-on-demand, configurable duration, API + cockpit button.
Live source CRUD: add/remove/update source while live (ZMQ injection where possible; otherwise
seamless `filter_complex` rebuild via start-new/crossfade/stop-old). **Scope**: Large (live CRUD
is architecturally hard).

### Phase 10: Studio Mode (Preview/Program)

Dual output pads (preview + program), preview to cockpit via HLS/WebRTC, scene changes affect
preview then transition to program, dual-panel cockpit UI. Depends on Phase 3 (multi-output) +
Phase 6 (transitions). **Scope**: Large.

### Phase 11: Profiles + Scene Collections + Bidirectional WS

Profile + scene-collection models (named JSON), save/load/switch API + cockpit selector.
Bidirectional WS (source/filter/scene CRUD, event subscriptions, batch commands) beyond the
health push. **Scope**: Medium.

-----

## Dependency Graph

```
Phase 0: Organism Engine Placement  (engine runs on Beast, driven from VPS over Tailscale)
    |
    +--> Phase 1: Audio Pipeline  (mechanics node-independent; real target = Beast mic+system)
    |        |
    +--> Phase 2: Real Capture + HW Encode (Beast)  <-- provides real audio/video inputs + NVENC
    |        |
    |     [Phase 1 + Phase 2 together = real streamer MVP]
    |        v
    +--> Phase 3: Recording + Multi-Output
             |
             +--> Phase 4: Source Transforms  (parallel with Phase 3)
             |        |
             |        v
             +--> Phase 5: Video + Audio Filters  (audio filters need Phase 1)
             |        |
             |        v
             +--> Phase 6: Transitions  (needs Phase 4 opacity, Phase 1 audio crossfade)
             |
             +--> Phase 7: Services  (independent; any time after Phase 2)
             +--> Phase 8: Source Types  (additive; any time)
                      |
                      v
                  Phase 9: Replay + Live CRUD  (needs Phase 3 multi-output)
                      |
                      v
                  Phase 10: Studio Mode  (needs Phase 3 + Phase 6)
                      |
                      v
                  Phase 11: Profiles + Collections + Bidirectional WS
```

### Parallelization

- Phase 1 (audio mechanics) and Phase 2 (capture/encode) are tightly coupled but Phase 1's
  *mechanics* derisk independently — run the audio spike before either build.
- Phases 3 + 4 parallel. Phase 7 + Phase 8 any time after Phase 2. Phases 5 + 6 partially overlap.

-----

## Leverage Summary

|Verdict          |Count|What                                                                                                                                                                                     |
|-----------------|-----|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|**WRAP (FFmpeg)**|18   |Graphics, video pipeline, frame timing, encoders, most sources, all filters, transitions, audio mixing, recording                                                                        |
|**INTERNALIZE**  |8    |Source primitive, scene model, output management, service registry, stats, studio mode, profiles, remote control — **plus organism engine placement / node-aware resolution (UMH's own)**|
|**DEFER**        |5    |Plugin system, virtual camera, game capture, browser source, VST, hotkeys, projectors                                                                                                    |

**The fundamental insight**: OBS built a custom real-time GPU compositor because it's a desktop
app rendering in-process. UMH wraps FFmpeg because it's a **headless control plane orchestrating
subprocesses across an organism.** The capability surface is the same; the implementation and
*placement* strategy are completely different. Every OBS capability maps to FFmpeg parameters —
and runs on whichever organism node has the hardware for it.

**The differentiator**: OBS has no AI integration and no concept of a multi-node organism. UMH's
CapabilityHandler protocol makes every broadcast action (start, switch scene, adjust volume,
apply filter, record) agent-operable via the same socket humans use — and that socket drives the
engine on the VPS *or* the Beast transparently. An AI agent can direct a broadcast running on the
workstation's GPU from the always-on control plane. No existing broadcast tool does either.

-----

## Acceptance Criteria Per Phase

Each phase is complete when:

1. Unit tests cover the new `filter_complex` / capability constructs
1. Integration test: start (composite) engine, verify FFmpeg runs with the new capability
1. **Cross-node**: where the capability is Beast-resident, it is proven driven from the VPS
   control plane over Tailscale (not just locally on the Beast)
1. API endpoints documented and Clerk-authed
1. Cockpit UI renders the new controls
1. Agent-cell operable (CapabilityHandler updated)
1. Health monitoring covers the new state
1. Zero regression on existing Slice 0 / Wave 2 capabilities

-----

*Document re-derived 2026-06-13 from the complete OBS architecture study, then corrected for*
*UMH organism placement (VPS + Beast + iPhone as one system).*
*Supersedes the ad-hoc Wave list and the first re-derivation.*
