# Phase 14.13U — Device Presence + Voice Session Routing + Spoken Response Contract

**Date:** 2026-06-09
**Status:** VERIFIED (simulation — hardware multi-device test requires operator)

---

## Original Problem Statement

Voice commands from any device (iPhone, iPad, desktop) had no routing contract:
- No tracking of which operator surface was active
- No separation of execution target vs audio output device
- TTS always sent the full markdown response, not a speech-optimized version
- No visibility into the active voice route in the cockpit

The doctrine: **Voice belongs to the operator session. Execution belongs to the target node. Audio returns to the source device unless explicitly redirected.**

---

## Design and Implementation

### A. Device Presence Registry

`substrate/workstation/device_presence.py`

In-memory singleton registry tracking active cockpit sessions. Each session has:
- `device_id` — stable identifier (persisted in localStorage)
- `session_id` — per-tab identifier (persisted in sessionStorage)
- `client_type` — mobile_browser | desktop_browser | electron | terminal
- `control_surface` — fly_cockpit | local_cockpit | electron_cockpit | terminal
- `can_capture_audio`, `can_play_audio` — capability flags
- `reachable_nodes` — mesh nodes the session can target
- `last_seen` — ISO timestamp, refreshed on heartbeat
- `status` — active | idle | disconnected

Sessions expire after 60s without heartbeat. Thread-safe via `threading.Lock`.

Four REST endpoints added to cockpit.py:
- `POST /device/register` — register a device session
- `POST /device/heartbeat` — refresh last_seen with optional field updates
- `GET /device/sessions` — list active sessions
- `POST /device/disconnect` — mark session disconnected

### B. Voice Route Resolver

`substrate/workstation/voice_route_resolver.py`

Fully deterministic (no LLM calls). Resolves the full voice routing contract:

```
VoiceRoute:
  input_device          # source device ID
  control_surface       # fly_cockpit | local_cockpit | electron_cockpit
  execution_target      # cockpit | beast_windows | vps
  audio_output_device   # device to play TTS audio
  audio_output_session  # session ID to route TTS to
  response_render_surface # surface to render text response
  handoff_mode          # conversation | remote_control
  route_reason          # human-readable reason
  requires_approval     # always False from resolver (governance is a separate layer)
```

Resolution logic:
1. Parse execution target from transcript keywords ("on beast", "on vps", "docker ps")
2. Parse audio override ("speak from workstation", "talk back here")
3. Audio returns to source session by default
4. Terminal sessions get text_only audio path
5. Non-local targets get remote_control handoff mode

### C. Spoken Response Contract

`AdvisorResponse` gains two new fields:
- `spoken_text: str = ""` — concise, markdown-free TTS version (auto-generated for voice source)
- `routing: dict = {}` — resolved VoiceRoute metadata

`display_text` property is an alias for `text`. `to_api_dict()` omits empty fields.

`converse()` updated:
- Accepts optional `routing` dict from caller
- When `source == "voice"`: generates `spoken_text` via `prepare_voice_response()`
- When `routing` dict provided: resolves and attaches VoiceRoute to response

`_save_turn()` persists device/session metadata when routing is present:
`source`, `device_id`, `session_id`, `execution_target`, `audio_output_session`

### D. Voice Server Session Awareness

`umh/voice_server.py` updated:
- `handle_voice()` accepts `session_id` from `mic_start` JSON message
- Transcript responses include `session_id` field

---

## Frontend

### deviceSessionStore.ts

Zustand store that:
- Detects client type (electron via `window.cockpit`, mobile via UA/viewport)
- Generates/restores `device_id` (localStorage) and `session_id` (sessionStorage)
- Registers with backend on `Shell` mount
- Heartbeats every 20 seconds
- Provides `getRoutingMetadata()` for chatStore injection

### device-presence.ts

API client for the four device presence endpoints.

### VoiceRouteHud.tsx

Compact read-only display shown when mic or TTS is active:
```
VOICE ROUTE
Input:  [device_id]
Output: [audio_output_device]
Target: [execution_target]
Mode:   [handoff_mode]
```

Integrated in RightRail's ChatSection.

### voice-controller.ts

Updated to:
- Extract `spoken_text` from response metadata and use it for TTS instead of full content
- Update deviceSessionStore voiceRoute when `routing` metadata is present in response

### chatStore.ts

`sendMessage()` now includes routing metadata in voice requests:
```json
{
  "source_device_id": "...",
  "source_session_id": "...",
  "control_surface": "fly_cockpit",
  "audio_return_route": "source_device"
}
```

### voiceStore.ts

`TtsState` expanded to include full state machine:
`idle | generating_tts | ready_to_speak | speaking | tts_failed`

---

## Test Results

```
tests/test_device_presence.py    16 passed
tests/test_voice_route_resolver.py  31 passed
tests/test_voice_identity.py     28 passed
Total: 75 passed, 0 failed
```

All backend modules compile clean:
- substrate/workstation/device_presence.py
- substrate/workstation/voice_route_resolver.py
- substrate/organism/advisor_conversation.py
- transports/api/cockpit.py
- umh/voice_server.py

TypeScript check: PASS (no errors)

---

## Remaining Limitations

1. **Multi-device hardware test requires operator** — physically routing TTS audio to a different device (iPhone → Beast speaker) requires real Tailscale connectivity and operator verification.

2. **Real TTS session scoping needs voice server restart** — to fully test session_id threading from frontend through proxy to voice server.

3. **Device presence is in-memory only** — sessions don't survive voice server restart. A future phase could persist to Neon.

4. **Audio override to Beast** — the resolver correctly sets `audio_output_device = "beast_windows"` but the voice server doesn't yet have a WebSocket connection to Beast's audio output. This is a Phase 14.13V concern.

---

## Final Verdict

**PARTIAL — simulation verified, hardware multi-device test requires operator**

Core contract is in place and tested:
- Device registry accepts sessions and tracks heartbeats
- Route resolver deterministically separates execution from audio
- Spoken/display contract is live in AdvisorResponse
- Frontend sends routing metadata on all voice requests
- VoiceRouteHud renders active route
- 75 tests pass

What remains is hardware verification of actual cross-device audio routing.
