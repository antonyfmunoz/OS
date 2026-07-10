---
type: codewiki-dir
dir: umh
---

# `umh/` — thin relay entrypoints (media bridges + voice preflight)

**3 files · 139,588 bytes · [Full file inventory](../inventory/umh.md)**

## Purpose
`umh/` is a small tray of standalone relay/entrypoint scripts that bridge live media between the Beast (the GPU workstation node) and cockpit viewers, plus one server-side audio preprocessor. Despite the top-level name, this is **not** the substrate — it is glue: three run-directly modules that sit at the edge of the mesh and shovel frames or normalize audio. Two are WebSocket relay servers; one is a request-time audio preflight helper.

## How it fits
These are edge processes, not a layer in the dependency stack. They connect *downward* into the substrate for their real logic — e.g. `voice_preflight.py` imports the canonical error taxonomy from `substrate/execution/voice/error_codes.py` — and they interoperate with the transport mesh: `transports/node_mesh/server.py` holds a `register_desktop_relay(ws_url, token)` surface and a `_desktop_relay_ws_loop()` that connects to the desktop relay this directory serves. So `umh/` is best read as relay endpoints that the node-mesh transport dials into, backed by substrate contracts. Do not treat it as substrate or add domain logic here.

## Structure

| File | Lines | Role |
|---|---|---|
| `vision_relay.py` | 3,010 | Vision relay server — bridges Beast camera frames to cockpit viewers |
| `desktop_relay.py` | 341 | Desktop relay server — bridges Beast desktop frames to cockpit viewers |
| `voice_preflight.py` | 393 | Server-side audio preflight: normalization + precise error taxonomy |

## Key components
**`vision_relay.py`** is by far the largest (3,010 lines) — it relays live camera frames from the Beast's vision pipeline (webcam/PTZ capture, object detection) out to cockpit viewers over WebSocket. **`desktop_relay.py`** does the same for screen frames (the Beast's desktop stream). Both are the viewer-facing half of a producer→relay→viewer chain whose producer half lives on the Windows node (`nodes/windows/umh_node/adapters/desktop_stream.py`, `camera.py`) and whose transport coordination lives in `transports/node_mesh/server.py`.

**`voice_preflight.py`** is different in kind: not a relay but a request-time helper that normalizes inbound audio and classifies failures against a precise error taxonomy before the voice pipeline proceeds. It imports `substrate/execution/voice/error_codes.py` so the errors it emits match the canonical set the rest of the voice stack understands.

## Data & state
No persistent stores. The relays hold in-memory frame buffers and WebSocket connection state per session; `voice_preflight.py` uses `tempfile` for transient audio normalization and returns typed results. Auth to the desktop relay is token-based (`register_desktop_relay(..., token)`), so the relay expects a shared token rather than being open.

## Gotchas
- **Note `voice_preflight.py`'s import ordering.** It uses `from __future__ import annotations` at the top, then imports below it with `# noqa: E402` on the substrate import — this is the deliberate pattern required because `from __future__` must be the first statement; do not "fix" the ordering.
- These are **entrypoints/glue, not substrate** — resist the pull of the `umh/` name. Business logic and canonical types belong in `substrate/`; this directory only bridges and preprocesses.
- The vision/desktop relays are the viewer end of a mesh chain. If frames aren't reaching the cockpit, the fault could be at the producer (Windows node adapters), the mesh server (`transports/node_mesh/server.py`), or here — check all three, and remember the mesh WS server is a **host process**, not a Docker container, so `docker restart` won't touch it.

## See also
- [nodes.md](nodes.md) — the Windows node adapters that produce the frames these relays forward
- [transports.md](transports.md) — `node_mesh/server.py` coordinates the desktop relay
- [substrate.md](substrate.md) — `execution/voice/error_codes.py` backs the preflight taxonomy
