# UMH Broadcast Subsystem — Canonical Plan

> Zone C planning artifact. No GPL expression present.
> Specs referenced by path, not duplicated.
> All architecture and naming is original proprietary work.

---

## Product Framing

This is NOT an "OBS clone." Broadcasting is a UMH capability — the system can
broadcast because the organism can broadcast, the same way it can perceive or
execute. The wedge is **agent-operable broadcast**: the control-plane API that
drives the engine is the same contract UMH cells use. A human clicks "Go Live"
through the cockpit UI; a cell calls the same API endpoint programmatically.

---

## License Firewall Governance

Classification: **Integration-Boundary, HI-8 tier.**

| Zone | Purpose | Access | Persistence |
|------|---------|--------|-------------|
| **A — Operational Fork** | Internal-use OBS GPL fork. Study/reference only. | Never accessed by Zone C code | Persistent. Distribution PROHIBITED BY POLICY — distributing triggers copyleft. |
| **FFmpeg (bundled dep)** | LGPL CLI binary invoked as subprocess. NOT the fork. | Engine invokes via subprocess only | Persistent. Distribution PERMITTED with compliance (see Distribution Gate). |
| **B — Quarantine Read** | Ephemeral source-read scratch for producing concept-only specs. | Destroyed on exit | Non-persisted |
| **C — Clean Proprietary** | All shipped code: engine, API, UI, data models. | No access to A/B source | Persistent. Shippable. |

Enforcement: cell/memory boundary. Reader and implementer are isolated workers
with no shared memory. Governance trace (spec path + verification gate log) is
the clean-room audit proof.

The three Zone B specs produced by the reader pass:
- `docs/superpowers/specs/broadcast/SPEC_capture.md`
- `docs/superpowers/specs/broadcast/SPEC_compositing.md`
- `docs/superpowers/specs/broadcast/SPEC_encode_stream.md`

These are referenced throughout this plan. They are NOT duplicated here.

---

## Architecture

Decoupled. One codebase. Shell deferred.

```
+--------------------------------------------------+
|  UI Layer (React, cockpit panel)                  |
|  Browser-served today, shell-portable tomorrow    |
+------------------+-------------------------------+
                   | HTTP + WebSocket
                   v
+--------------------------------------------------+
|  API Layer (control plane)                        |
|  Same contract for UI and UMH cells               |
|  HTTP: commands (start/stop/configure)            |
|  WS: status push (health, state transitions)      |
+------------------+-------------------------------+
                   | internal calls
                   v
+--------------------------------------------------+
|  Engine Layer (headless, no UI knowledge)          |
|  Invokes FFmpeg CLI as subprocess (arm's-length)  |
|  Owns: lifecycle, config->args, source/scene model |
+--------------------------------------------------+
```

**Engine** — headless process. Wraps FFmpeg. API-driven. No UI imports.
Runs as a local process from day one (browser cannot do window capture,
hardware NVENC, or virtual camera).

**API** — HTTP + WebSocket control plane. The same contract that serves
the cockpit UI also serves UMH organism cells. This IS the broadcast socket.

**UI** — React panel in the cockpit (EOS stack: Zustand, Tailwind, Lucide).
Browser-served. No browser-only dependencies in the engine or API layers.

**Shell** — Tauri preferred (sovereignty-aligned, Rust core, web renderer).
Electron as fallback. DEFERRED — not in scope until the browser-served
cockpit proves the workflow.

---

## Leverage Stance

Wrap FFmpeg / GStreamer / platform SDKs. Write NO codec, muxer, or transport
code. Internalize only when bottlenecked.

**LGPL FFmpeg only.** x264 and x265 flip the build to GPL. Prefer:
1. Hardware encoders (NVENC, QSV, AMF, VAAPI) — no license issue.
2. Commercially-licensed x264 if software encoding is needed.
3. OpenH264 (BSD) as a lightweight fallback.

The engine invokes the FFmpeg CLI binary as a SUBPROCESS (arm's-length). The
engine binary MUST NOT link libav* libraries (libavcodec, libavformat, etc.).
The subprocess boundary keeps the engine proprietary; linking would make it a
derivative work. FFmpeg is a permissible bundled dependency, NOT the Zone A
operational fork. Zone A refers exclusively to the OBS GPL fork.

---

## Browser Ceiling

Pure browser cannot do:
- Window capture (requires OS-level API)
- Hardware encoder access (NVENC/QSV/AMF)
- Virtual camera output (requires OS-level loopback driver)
- Desktop audio capture (browser sandbox blocks it)

These require the engine as a local process. The engine runs locally from
Slice 0. The UI connects to it over localhost HTTP/WS.

---

## Slice 0 — COMPLETE (Minimum Viable Broadcast)

**Goal:** One source -> one trivial scene -> H.264 -> one RTMP out.
Start/stop via API. Status (bitrate, dropped frames, uptime) over WS.
Proof = live frames arriving at an RTMP endpoint.

**Status:** PROVEN — dual-consumer (agent cell + cockpit human). See
`docs/superpowers/specs/broadcast/SLICE0_PROOF_REPORT.md` for full evidence.

**Proprietary code (Zone C):**

| Component | Location | What it does |
|-----------|----------|--------------|
| Request/response models | `transports/api/cockpit_broadcast_routes.py` (local) | Pydantic schemas for start request, status response, source type enum. Local to route file per rooms pattern — graduates to substrate/ when stabilized. |
| Process lifecycle | `adapters/broadcast/process_lifecycle.py` | Subsystem-agnostic subprocess lifecycle (process group isolation, SIGTERM→SIGKILL, CPU gate, asyncio.Lock, SIGKILL wait timeout) |
| Engine process | `adapters/broadcast/engine.py` | FFmpeg subprocess lifecycle, config->args, health parsing, asyncio.Lock on state transitions |
| FFmpeg arg builder | `adapters/broadcast/ffmpeg_args.py` | Translate config into FFmpeg CLI args (with input validation + output URL SSRF guard) |
| Broadcast API routes | `transports/api/cockpit_broadcast_routes.py` | HTTP + WS endpoints (start/stop/status, 1s health push) |
| Capability handler | `adapters/broadcast/integration/handlers.py` | BroadcastCapabilityHandler — agent cell surface (CapabilityHandler Protocol) |
| Capability manifest | `adapters/broadcast/integration/manifest.py` | start/stop/status descriptors for IntegrationRegistry |
| Broadcast store | `cockpit/.../stores/broadcastStore.ts` | Zustand store |
| Broadcast panel | `cockpit/.../panels/BroadcastPanel.tsx` | Cockpit UI |
| Broadcast WS hook | `cockpit/.../hooks/useBroadcastConnection.ts` | Module-level singleton auto-connect hook |
| Broadcast WS client | `cockpit/.../api/broadcast-ws.ts` | WS health client |
| ProcessLifecycle tests | `tests/adapters/broadcast/test_process_lifecycle.py` | 7 unit tests covering all 4 fixes |

**What Slice 0 does NOT include:**
- No multi-source compositing (one source fills the canvas)
- No scene transitions (only one scene)
- No filters/effects
- No recording (stream only)
- No virtual camera
- No replay buffer
- No AI producer
- No multi-destination

**Verification (all PASS):**
- FFmpeg subprocess starts with correct args
- RTMP connection established to test endpoint (same-host MediaMTX)
- Health metrics (bitrate, frames, uptime) arrive over WS
- Start/stop lifecycle works cleanly via both HTTP and CapabilityHandler
- Process cleanup on stop (no orphan FFmpeg processes)
- ffprobe confirms H.264 High profile, 30fps, 1920x1080
- Cockpit panel renders, Go Live flips to LIVE, Stop returns to IDLE
- 7/7 ProcessLifecycle unit tests pass
- Cross-host egress (VPS → Beast): DEFERRED — Beast MediaMTX pending

---

## Slice Backlog — Ordered Waves

Each wave is a narrow end-to-end increment over the working spine.
"Internalize when bottlenecked" — wrap external tools until the wrapper
itself becomes the constraint, then replace the inner layer.

### Wave 1 — Recording + Multi-Output
**Depends on:** Slice 0 complete.
**Adds:** Local file recording (MKV). Stream + record simultaneously.
Pause/resume recording. Recording health (file size, duration, disk space).
**Spec refs:** SPEC_encode_stream S7 (Recording), S14 (Multi-Output).
**Internalization:** None. FFmpeg handles muxing to file.

### Wave 2 — Multi-Source + Scene Switching
**Depends on:** Wave 1.
**Adds:** Multiple sources per scene. Multiple scenes. Cut transitions.
Source positioning (x, y, w, h, z-order). Basic audio mixing (volume, mute).
**Spec refs:** SPEC_capture S5, SPEC_compositing S3-S5, S7.
**Internalization:** None yet. FFmpeg complex filtergraph composites.
This layer strains first.

### Wave 3 — Device Scanner + Source Browser
**Depends on:** Wave 2.
**Adds:** Enumerate cameras, mics, displays, windows. User picks from list.
Hot-plug detection.
**Spec refs:** SPEC_capture S8, S10.
**Internalization:** Platform-specific device enumeration. Thin adapter per OS.

### Wave 4 — Transitions + Preview/Program
**Depends on:** Wave 2.
**Adds:** Preview/program dual-output (studio mode). Animated transitions
(fade, slide, wipe). Duration and easing.
**Spec refs:** SPEC_compositing S6, S9.
**Internalization:** Preview rendering requires second pipeline or browser canvas.

### Wave 5 — Filters + Effects
**Depends on:** Wave 2.
**Adds:** Per-source visual filters (color correction, chroma key, blur, LUT).
Per-source audio filters (gain, noise suppression, compressor, EQ).
**Spec refs:** SPEC_compositing S8.
**Internalization:** FFmpeg filtergraph handles most. Custom = GPU shader pipeline.

### Wave 6 — Advanced Outputs
**Depends on:** Wave 1.
**Adds:** Virtual camera (v4l2loopback). Replay buffer. SRT output.
Multi-destination streaming.
**Spec refs:** SPEC_encode_stream S6.2, S6.6, S7, S8.
**Internalization:** Virtual camera = OS driver integration. Replay buffer = proprietary ring buffer.

### Wave 7 — AI Producer Layer
**Depends on:** Waves 2, 5.
**Adds:** AI scene switching suggestions, silence/black/freeze detection,
audio clipping monitoring, highlight markers, stream summarization,
clip generation, technical issue alerts.
**Governance:** AI cannot go live, stop stream, delete files, or change
destinations without explicit operator approval.
**Spec refs:** Original requirements SG.
**Internalization:** UMH-native. AI producer is a UMH cell consuming the broadcast API.

### Wave 8 — Compositor Internalization (First Major Internalization)
**Depends on:** Waves 2, 4, 5 proven as bottleneck.
**Replaces:** FFmpeg complex filtergraph with proprietary GPU render graph.
**Why:** Multi-source + filters + transitions strain the filtergraph.
Real-time manipulation needs lower latency than subprocess piping.
**What:** GPU-accelerated compositor (WebGPU/wgpu or OpenGL/Vulkan).
**What NOT:** Not a codec, muxer, or transport. Those stay wrapped.

---

## Dependency Graph

```
Slice 0 (one source -> RTMP)
    |
    +---> Wave 1 (recording + multi-output)
    |        |
    |        +---> Wave 6 (virtual cam, replay, SRT, multi-dest)
    |        |
    |        +---> Wave 2 (multi-source + scenes)
    |                 |
    |                 +---> Wave 3 (device scanner)
    |                 |
    |                 +---> Wave 4 (transitions + preview/program)
    |                 |
    |                 +---> Wave 5 (filters + effects)
    |                 |
    |                 +---> Wave 7 (AI producer) [needs Wave 5]
    |
    +---> Wave 8 (compositor internalization) [needs 2,4,5 proven]
```

---

## Separation Map

| Subsystem | Boundary | Shared Physical Device? | State Isolation |
|-----------|----------|------------------------|-----------------|
| **Broadcast** | `adapters/broadcast/`, `transports/api/cockpit_broadcast_routes.py` | May use same webcam | Own source model, own lifecycle |
| **Vision (PTZ)** | `cockpit/.../components/vision/`, `api/vision-ws.ts` | May use same webcam | Own tracking state, own PTZ control |
| **Conference Rooms** | `cockpit/.../components/rooms/`, LiveKit | May use same webcam | Own room state, own LiveKit session |

Rules:
- Broadcast errors MUST NOT break Vision or Conference Rooms.
- Vision errors MUST NOT break Broadcast or Conference Rooms.
- Conference Room errors MUST NOT break Broadcast or Vision.
- If shared physical device: each acquires independently or uses multiplexing adapter.

---

## Distribution Gate

Two hard rules. One protects against copyleft trigger. The other ensures
FFmpeg compliance when the desktop shell ships.

### Rule A — OBS Fork (Zone A): NEVER distribute

The operational OBS GPL fork may NEVER be pushed, packaged, or shipped to any
external destination. This is a structural block, not a procedural one — no CI
pipeline, build script, or release process may reference Zone A artifacts.
Distributing the fork would trigger GPL copyleft and forfeit proprietary status
for any combined work. This is not illegal — it is off-limits to us by policy.

### Rule B — FFmpeg: distribute WITH compliance (dormant until shell ships)

When the desktop shell ships and FFmpeg is bundled for end-user distribution,
ALL of the following must hold:

- [ ] LGPL FFmpeg build — no x264/x265 GPL components linked. Use hardware
      encoders (NVENC/QSV/AMF/VAAPI), OpenH264 (BSD), or commercially-licensed
      x264 instead.
- [ ] CLI subprocess only — zero libav* linking in the engine binary. The engine
      calls `ffmpeg` as an external process. No `#include <libavcodec/...>`.
- [ ] Ship FFmpeg as a SEPARATE binary — not statically combined with the engine
      executable. The engine and FFmpeg are distinct files in the distribution.
- [ ] Include FFmpeg's license text + a written offer for FFmpeg source in the
      distribution package, per LGPL requirements.

Until the shell ships (server-only / internal-use), Rule B is dormant but
pre-satisfied by the subprocess architecture established in Slice 0.

---

## Files This Plan Does NOT Touch

- `substrate/types.py` — unless new broadcast types registered via canonical_types
- `substrate/__init__.py` — no changes
- `substrate/control_plane/` — no changes
- `substrate/execution/` — no changes
- `services/discord_bot.py` — no changes
- `adapters/models/model_router.py` — no changes
- All existing Vision components
- All existing Conference Room components
