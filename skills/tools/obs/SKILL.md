<<<<<<< Updated upstream
---
name: obs
description: "Use when configuring OBS Studio scenes/sources/encoders for streaming or recording, automating OBS from scripts via obs-websocket v5 (scene switching, source visibility, text/lower-third updates, recording start/stop, replay buffer, screenshots), debugging dropped frames or encoder overload, choosing x264 vs NVENC/AMF/QSV, planning multi-RTMP restreams, or building agent-callable broadcast control for Initiate Arena lives and personal brand content."
allowed-tools: "Read, Bash, Write, Edit"
version: 1.0
source_url: "https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "obs-websocket v5.x, OBS Studio 31.x"
sdk_version: "obsws-python 1.7+ (Python), obs-websocket-js 5.x (Node)"
speed_category: stable
trigger: both
effort: low
context: fork
---

# Tool: obs (OBS Studio + obs-websocket)

## What This Tool Does

OBS Studio is the open-source video compositor and broadcaster Antony uses
for personal-brand content and Initiate Arena live sessions. It composes
arbitrary inputs (camera, screen, browser, media) into named **scenes**,
encodes the program output with a software or hardware encoder, and ships
it to disk (recording), to RTMP/WHIP endpoints (streaming), to a virtual
camera, or out an NDI feed.

This is a **hybrid skill**: the GUI is the human surface (Antony arranges
shots, picks cameras, builds scene collections); **obs-websocket v5** is
the agent surface — a JSON-RPC protocol over WebSocket that exposes the
full OBS command set so Claude / EOS agents can drive the broadcast in
real time without touching the mouse.

Core capabilities:

- **Scene composition** — multi-layer canvases of sources (video capture, display capture, browser, media, text, image, color)
- **Filters** — per-source chains (chroma key, color correct, LUT, NVIDIA noise removal, scale)
- **Studio Mode** — preview/program with explicit transitions
- **Encoders** — x264 (CPU), NVENC H.264/HEVC/AV1 (NVIDIA), AMF (AMD), QuickSync (Intel), Apple VT
- **Outputs** — recording (MKV/MP4/MOV/fragmented MP4), streaming (RTMP/RTMPS/SRT/WHIP), virtual camera, NDI, replay buffer
- **obs-websocket v5** — JSON-RPC 2.0 over WebSocket on port 4455 with HMAC-SHA256 auth; full request/event surface
- **Plugin ecosystem** — StreamFX, Move Transition, Source Record, Advanced Scene Switcher, obs-multi-rtmp, NDI, Background Removal

## EOS Integration

OBS is the broadcast substrate for personal-brand content (north-star item
2) and live Initiate Arena sessions (north-star item 1). EOS agents drive
it via obs-websocket v5 so the broadcast is operable from Discord, from
the cognitive loop, and from scheduled jobs.

Primary agent-callable patterns:

- **Scene switching during lives** — `SetCurrentProgramScene` from a Discord
  command or a cognitive-loop trigger ("question being answered", "demo",
  "outro")
- **Lower-third text updates** — `SetInputSettings` on a `text_gdiplus_v3`
  (Win) / `text_ft2_source_v2` (Linux/Mac) source to show "Now: <topic>",
  current caller name, or a CTA URL
- **Recording control** — `StartRecord` / `StopRecord` from `morning_prep.sh`
  (auto-record solo brand content) or from the EA when an Initiate Arena
  session begins
- **Replay buffer** — `SaveReplayBuffer` for "did you see that" highlight
  capture during outreach demos
- **Snapshot for alerts** — `GetSourceScreenshot` returns base64 PNG; the
  monitor can post current-program thumbnails to Discord
- **Stream control** — `StartStream` / `StopStream` for scheduled brand
  content drops; multi-RTMP restream handled by the obs-multi-rtmp plugin
  with separate output configs

Canonical EOS pattern: a single named WebSocket connection from
`eos_ai/obs_controller.py` (to be built) using `obsws-python`, with the
password loaded from `eos_ai/.env` (`OBS_WS_PASSWORD`), and a thin
function-per-verb facade so any agent can call `obs.show_scene("Live")`
without knowing the protocol.

## Authentication

obs-websocket v5 uses **HMAC-SHA256 challenge-response**, not bearer tokens.
The server sends a `salt` and `challenge` in the Hello (op 0) message; the
client computes
`base64(sha256(base64(sha256(password + salt)) + challenge))`
and sends it in Identify (op 1). Auth is **per-connection**, not per-request.

Setup:
1. OBS → Tools → WebSocket Server Settings → Enable WebSocket server
2. Set port (default 4455), enable auth, copy password
3. Store in `eos_ai/.env` as `OBS_WS_PASSWORD=...`
4. Bind to 127.0.0.1 only — never expose 4455 publicly. For remote (iPad)
   access, tunnel through Tailscale.

`obsws-python` handles the handshake automatically:

```python
import obsws_python as obs
client = obs.ReqClient(host='127.0.0.1', port=4455,
                       password=os.getenv('OBS_WS_PASSWORD'))
```

## Quick Reference

### Connect and switch scenes (Python, obsws-python)

```python
import os, obsws_python as obs
cl = obs.ReqClient(host='127.0.0.1', port=4455,
                   password=os.getenv('OBS_WS_PASSWORD'), timeout=3)
cl.set_current_program_scene('Live - Talking Head')
print(cl.get_current_program_scene().current_program_scene_name)
```

### Update lower-third text

```python
cl.set_input_settings(
    name='LowerThird',
    settings={'text': 'Now: Initiate Arena Cohort 01 — Q&A'},
    overlay=True,  # merge with existing settings, don't replace
)
```

### Toggle source visibility in current scene

```python
scene = cl.get_current_program_scene().current_program_scene_name
item  = cl.get_scene_item_id(scene_name=scene, source_name='Webcam').scene_item_id
cl.set_scene_item_enabled(scene_name=scene, item_id=item, enabled=True)
```

### Recording / streaming / replay buffer

```python
cl.start_record()                       # returns immediately
cl.get_record_status()                  # .output_active, .output_timecode, .output_bytes
path = cl.stop_record().output_path     # absolute path to the finished file
cl.start_stream(); cl.stop_stream()
cl.save_replay_buffer()                 # writes last N seconds to disk
```

### Screenshot a source

```python
shot = cl.get_source_screenshot(name='Live - Talking Head',
                                img_format='png', width=640, height=360,
                                quality=-1)
# shot.image_data is "data:image/png;base64,iVBOR..." — strip prefix and decode
```

### Raw protocol (no SDK)

```json
// → Hello (op 0) from server
// ← Identify (op 1)
{"op":1,"d":{"rpcVersion":1,"authentication":"<computed>","eventSubscriptions":33}}
// → Identified (op 2)
// ← Request (op 6)
{"op":6,"d":{"requestType":"SetCurrentProgramScene","requestId":"a1",
              "requestData":{"sceneName":"Live"}}}
// → RequestResponse (op 7)
```

### Encoder cheat-sheet

| Goal | Encoder | Rate ctrl | Bitrate | Keyframe | Preset |
|---|---|---|---|---|---|
| 1080p60 stream Twitch/YT | NVENC H.264 | CBR | 6000–8000 kbps | 2s | p5 Quality, look-ahead, PVT |
| 1080p30 stream low-bw | NVENC H.264 | CBR | 4500 kbps | 2s | p5 |
| Local recording (edit) | NVENC HEVC | CQP | CQ 18–21 | 2s | p7 |
| No GPU streaming | x264 | CBR | 6000 kbps | 2s | veryfast |
| Audio (any) | AAC | — | 160 kbps | — | — |

## Conceptual Model

**OBS is a compositor first, a streamer second.** The mental model:

```
sources → scenes → program output → encoder → output(s)
```

A **source** is a producer (camera, browser, text). A **scene** is a
named ordered list of source instances (technically: scene items, each
with their own transform, crop, and visibility flag). The **program scene**
is the one currently being mixed. The **canvas** has a fixed base
resolution (e.g. 1920x1080); everything else scales.

The **encoder** runs on a separate thread, pulling rendered canvas frames
at the canvas FPS, compressing them, and handing them to one or more
**outputs** (file, RTMP, virtual cam, NDI). Recording and streaming have
**independent encoder configs** in Advanced output mode — this is why you
can record in HEVC CQP while streaming x264 CBR from the same scene.

**obs-websocket** is a plugin that exposes a JSON-RPC interface over a
WebSocket. It does not bypass OBS — every request is dispatched through
the same internal API used by the GUI buttons. If a button can do it,
the protocol can; if the GUI can't, neither can the protocol.

Internalize these and the foot-guns vanish:
- "I changed the source but the recording still has the old one" → recording
  uses its own encoder, but it shares the canvas; check whether you were
  in Studio Mode without hitting Transition
- "Scene switch didn't fire" → you targeted preview, not program. Use
  `SetCurrentProgramScene`, not `SetCurrentPreviewScene`
- "Recording started but file is empty" → encoder failed; check
  `output_active=true` but `output_bytes=0`, then read OBS log

## Gotchas

- **Port 4455 default in v5** (4444 was v4). v4 clients hitting 4444 silently
  fail. Always use 4455 + the v5 protocol.
- **Auth handshake order matters** — Hello → Identify must be sent within
  ~10s or the server drops the socket.
- **`SetCurrentProgramScene` vs `SetCurrentPreviewScene`** — in Studio Mode
  the latter only stages, you still need `TriggerStudioModeTransition`.
- **`SetInputSettings` with `overlay=False` REPLACES all settings** —
  including font, color, alignment. Always pass `overlay=True` for partial
  updates like text changes.
- **Source name vs UUID** — v5 accepts both via `inputName` / `inputUuid`.
  Names are mutable; cache UUIDs (`GetInputList`) at startup for long-running
  agents.
- **Text source kind is platform-dependent** — `text_gdiplus_v3` on Windows,
  `text_ft2_source_v2` on Linux/Mac. Detect via `GetInputKindList`.
- **Encoder overload** = CPU can't keep up with x264 preset. Drop preset,
  switch to NVENC, or lower output res.
- **Dropped frames** = network, not encoder. CBR + bitrate >75% of upload
  pipe will drop on jitter.
- **Recording in MP4 + crash = corrupted file**. Always record to MKV (or
  fragmented MP4) and remux after.
- **Replay buffer eats RAM** — 60s of 1080p60 NVENC ≈ 600 MB. Don't enable
  on the VPS.
- **`StartRecord` returns success even if no encoder is configured** —
  output silently does nothing. Verify with `GetRecordStatus` after 500ms.
- **Headless OBS on the VPS is not supported** — OBS needs a real GPU
  context. For server-side compositing use FFmpeg, not OBS.
- **Multi-RTMP restream** is a plugin (`obs-multi-rtmp`), not built-in.
  Each target gets its own encoder instance — CPU/GPU cost multiplies.

See references/best_practices.md for the full 19-section creator-level knowledge base
covering protocol details, encoder tuning, EOS recipes, and the failure catalog.
=======
---
name: obs
description: "Use when configuring OBS Studio scenes/sources/encoders for streaming or recording, automating OBS from scripts via obs-websocket v5 (scene switching, source visibility, text/lower-third updates, recording start/stop, replay buffer, screenshots), debugging dropped frames or encoder overload, choosing x264 vs NVENC/AMF/QSV, planning multi-RTMP restreams, or building agent-callable broadcast control for Initiate Arena lives and personal brand content."
allowed-tools: "Read, Bash, Write, Edit"
version: 1.0
source_url: "https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "obs-websocket v5.x, OBS Studio 31.x"
sdk_version: "obsws-python 1.7+ (Python), obs-websocket-js 5.x (Node)"
speed_category: stable
---

# Tool: obs (OBS Studio + obs-websocket)

## What This Tool Does

OBS Studio is the open-source video compositor and broadcaster Antony uses
for personal-brand content and Initiate Arena live sessions. It composes
arbitrary inputs (camera, screen, browser, media) into named **scenes**,
encodes the program output with a software or hardware encoder, and ships
it to disk (recording), to RTMP/WHIP endpoints (streaming), to a virtual
camera, or out an NDI feed.

This is a **hybrid skill**: the GUI is the human surface (Antony arranges
shots, picks cameras, builds scene collections); **obs-websocket v5** is
the agent surface — a JSON-RPC protocol over WebSocket that exposes the
full OBS command set so Claude / EOS agents can drive the broadcast in
real time without touching the mouse.

Core capabilities:

- **Scene composition** — multi-layer canvases of sources (video capture, display capture, browser, media, text, image, color)
- **Filters** — per-source chains (chroma key, color correct, LUT, NVIDIA noise removal, scale)
- **Studio Mode** — preview/program with explicit transitions
- **Encoders** — x264 (CPU), NVENC H.264/HEVC/AV1 (NVIDIA), AMF (AMD), QuickSync (Intel), Apple VT
- **Outputs** — recording (MKV/MP4/MOV/fragmented MP4), streaming (RTMP/RTMPS/SRT/WHIP), virtual camera, NDI, replay buffer
- **obs-websocket v5** — JSON-RPC 2.0 over WebSocket on port 4455 with HMAC-SHA256 auth; full request/event surface
- **Plugin ecosystem** — StreamFX, Move Transition, Source Record, Advanced Scene Switcher, obs-multi-rtmp, NDI, Background Removal

## EOS Integration

OBS is the broadcast substrate for personal-brand content (north-star item
2) and live Initiate Arena sessions (north-star item 1). EOS agents drive
it via obs-websocket v5 so the broadcast is operable from Discord, from
the cognitive loop, and from scheduled jobs.

Primary agent-callable patterns:

- **Scene switching during lives** — `SetCurrentProgramScene` from a Discord
  command or a cognitive-loop trigger ("question being answered", "demo",
  "outro")
- **Lower-third text updates** — `SetInputSettings` on a `text_gdiplus_v3`
  (Win) / `text_ft2_source_v2` (Linux/Mac) source to show "Now: <topic>",
  current caller name, or a CTA URL
- **Recording control** — `StartRecord` / `StopRecord` from `morning_prep.sh`
  (auto-record solo brand content) or from the EA when an Initiate Arena
  session begins
- **Replay buffer** — `SaveReplayBuffer` for "did you see that" highlight
  capture during outreach demos
- **Snapshot for alerts** — `GetSourceScreenshot` returns base64 PNG; the
  monitor can post current-program thumbnails to Discord
- **Stream control** — `StartStream` / `StopStream` for scheduled brand
  content drops; multi-RTMP restream handled by the obs-multi-rtmp plugin
  with separate output configs

Canonical EOS pattern: a single named WebSocket connection from
`eos_ai/obs_controller.py` (to be built) using `obsws-python`, with the
password loaded from `eos_ai/.env` (`OBS_WS_PASSWORD`), and a thin
function-per-verb facade so any agent can call `obs.show_scene("Live")`
without knowing the protocol.

## Authentication

obs-websocket v5 uses **HMAC-SHA256 challenge-response**, not bearer tokens.
The server sends a `salt` and `challenge` in the Hello (op 0) message; the
client computes
`base64(sha256(base64(sha256(password + salt)) + challenge))`
and sends it in Identify (op 1). Auth is **per-connection**, not per-request.

Setup:
1. OBS → Tools → WebSocket Server Settings → Enable WebSocket server
2. Set port (default 4455), enable auth, copy password
3. Store in `eos_ai/.env` as `OBS_WS_PASSWORD=...`
4. Bind to 127.0.0.1 only — never expose 4455 publicly. For remote (iPad)
   access, tunnel through Tailscale.

`obsws-python` handles the handshake automatically:

```python
import obsws_python as obs
client = obs.ReqClient(host='127.0.0.1', port=4455,
                       password=os.getenv('OBS_WS_PASSWORD'))
```

## Quick Reference

### Connect and switch scenes (Python, obsws-python)

```python
import os, obsws_python as obs
cl = obs.ReqClient(host='127.0.0.1', port=4455,
                   password=os.getenv('OBS_WS_PASSWORD'), timeout=3)
cl.set_current_program_scene('Live - Talking Head')
print(cl.get_current_program_scene().current_program_scene_name)
```

### Update lower-third text

```python
cl.set_input_settings(
    name='LowerThird',
    settings={'text': 'Now: Initiate Arena Cohort 01 — Q&A'},
    overlay=True,  # merge with existing settings, don't replace
)
```

### Toggle source visibility in current scene

```python
scene = cl.get_current_program_scene().current_program_scene_name
item  = cl.get_scene_item_id(scene_name=scene, source_name='Webcam').scene_item_id
cl.set_scene_item_enabled(scene_name=scene, item_id=item, enabled=True)
```

### Recording / streaming / replay buffer

```python
cl.start_record()                       # returns immediately
cl.get_record_status()                  # .output_active, .output_timecode, .output_bytes
path = cl.stop_record().output_path     # absolute path to the finished file
cl.start_stream(); cl.stop_stream()
cl.save_replay_buffer()                 # writes last N seconds to disk
```

### Screenshot a source

```python
shot = cl.get_source_screenshot(name='Live - Talking Head',
                                img_format='png', width=640, height=360,
                                quality=-1)
# shot.image_data is "data:image/png;base64,iVBOR..." — strip prefix and decode
```

### Raw protocol (no SDK)

```json
// → Hello (op 0) from server
// ← Identify (op 1)
{"op":1,"d":{"rpcVersion":1,"authentication":"<computed>","eventSubscriptions":33}}
// → Identified (op 2)
// ← Request (op 6)
{"op":6,"d":{"requestType":"SetCurrentProgramScene","requestId":"a1",
              "requestData":{"sceneName":"Live"}}}
// → RequestResponse (op 7)
```

### Encoder cheat-sheet

| Goal | Encoder | Rate ctrl | Bitrate | Keyframe | Preset |
|---|---|---|---|---|---|
| 1080p60 stream Twitch/YT | NVENC H.264 | CBR | 6000–8000 kbps | 2s | p5 Quality, look-ahead, PVT |
| 1080p30 stream low-bw | NVENC H.264 | CBR | 4500 kbps | 2s | p5 |
| Local recording (edit) | NVENC HEVC | CQP | CQ 18–21 | 2s | p7 |
| No GPU streaming | x264 | CBR | 6000 kbps | 2s | veryfast |
| Audio (any) | AAC | — | 160 kbps | — | — |

## Conceptual Model

**OBS is a compositor first, a streamer second.** The mental model:

```
sources → scenes → program output → encoder → output(s)
```

A **source** is a producer (camera, browser, text). A **scene** is a
named ordered list of source instances (technically: scene items, each
with their own transform, crop, and visibility flag). The **program scene**
is the one currently being mixed. The **canvas** has a fixed base
resolution (e.g. 1920x1080); everything else scales.

The **encoder** runs on a separate thread, pulling rendered canvas frames
at the canvas FPS, compressing them, and handing them to one or more
**outputs** (file, RTMP, virtual cam, NDI). Recording and streaming have
**independent encoder configs** in Advanced output mode — this is why you
can record in HEVC CQP while streaming x264 CBR from the same scene.

**obs-websocket** is a plugin that exposes a JSON-RPC interface over a
WebSocket. It does not bypass OBS — every request is dispatched through
the same internal API used by the GUI buttons. If a button can do it,
the protocol can; if the GUI can't, neither can the protocol.

Internalize these and the foot-guns vanish:
- "I changed the source but the recording still has the old one" → recording
  uses its own encoder, but it shares the canvas; check whether you were
  in Studio Mode without hitting Transition
- "Scene switch didn't fire" → you targeted preview, not program. Use
  `SetCurrentProgramScene`, not `SetCurrentPreviewScene`
- "Recording started but file is empty" → encoder failed; check
  `output_active=true` but `output_bytes=0`, then read OBS log

## Gotchas

- **Port 4455 default in v5** (4444 was v4). v4 clients hitting 4444 silently
  fail. Always use 4455 + the v5 protocol.
- **Auth handshake order matters** — Hello → Identify must be sent within
  ~10s or the server drops the socket.
- **`SetCurrentProgramScene` vs `SetCurrentPreviewScene`** — in Studio Mode
  the latter only stages, you still need `TriggerStudioModeTransition`.
- **`SetInputSettings` with `overlay=False` REPLACES all settings** —
  including font, color, alignment. Always pass `overlay=True` for partial
  updates like text changes.
- **Source name vs UUID** — v5 accepts both via `inputName` / `inputUuid`.
  Names are mutable; cache UUIDs (`GetInputList`) at startup for long-running
  agents.
- **Text source kind is platform-dependent** — `text_gdiplus_v3` on Windows,
  `text_ft2_source_v2` on Linux/Mac. Detect via `GetInputKindList`.
- **Encoder overload** = CPU can't keep up with x264 preset. Drop preset,
  switch to NVENC, or lower output res.
- **Dropped frames** = network, not encoder. CBR + bitrate >75% of upload
  pipe will drop on jitter.
- **Recording in MP4 + crash = corrupted file**. Always record to MKV (or
  fragmented MP4) and remux after.
- **Replay buffer eats RAM** — 60s of 1080p60 NVENC ≈ 600 MB. Don't enable
  on the VPS.
- **`StartRecord` returns success even if no encoder is configured** —
  output silently does nothing. Verify with `GetRecordStatus` after 500ms.
- **Headless OBS on the VPS is not supported** — OBS needs a real GPU
  context. For server-side compositing use FFmpeg, not OBS.
- **Multi-RTMP restream** is a plugin (`obs-multi-rtmp`), not built-in.
  Each target gets its own encoder instance — CPU/GPU cost multiplies.

See references/best_practices.md for the full 19-section creator-level knowledge base
covering protocol details, encoder tuning, EOS recipes, and the failure catalog.
>>>>>>> Stashed changes
