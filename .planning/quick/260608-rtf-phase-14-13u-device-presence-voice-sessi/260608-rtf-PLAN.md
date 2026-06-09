# Quick Task 260608-rtf: Phase 14.13U — Device Presence + Voice Session Routing + Spoken Response Contract

## Goal

Implement device-aware voice routing so voice belongs to the operator session,
execution belongs to the target node, and audio returns to the source device
unless explicitly redirected.

## must_haves

```yaml
truths:
  - Device presence registry tracks active cockpit sessions with heartbeat
  - Frontend clients register device/session identity on connect
  - Voice requests include routing metadata (source_device, source_session, audio_return_route)
  - Route resolver separates execution target from audio output device
  - AdvisorResponse includes separated display_text and spoken_text
  - TTS jobs are scoped to specific audio output sessions
  - Voice route HUD visible in cockpit RightRail
  - Governance unchanged for workstation/VPS commands
  - Transcript persistence includes device/session metadata
  - All existing voice identity tests still pass

artifacts:
  - substrate/workstation/device_presence.py
  - substrate/workstation/voice_route_resolver.py
  - cockpit/src/renderer/stores/deviceSessionStore.ts
  - cockpit/src/renderer/api/device-presence.ts
  - cockpit/src/renderer/components/VoiceRouteHud.tsx
  - tests/test_device_presence.py
  - tests/test_voice_route_resolver.py
  - data/umh/trinity_convergence/phase14_13u_device_presence_voice_session_routing_report.md

key_links:
  - substrate/workstation/activation.py (existing presence/activation)
  - substrate/organism/advisor_conversation.py (converse endpoint handler)
  - substrate/organism/system_identity.py (identity deterministic handler)
  - umh/voice_server.py (STT+TTS bridge)
  - cockpit/src/renderer/api/voice-ws.ts (VoiceWsClient)
  - cockpit/src/renderer/api/voice-controller.ts (voice pipeline)
  - cockpit/src/renderer/stores/voiceStore.ts (voice state)
  - cockpit/src/renderer/stores/chatStore.ts (chat dispatch)
  - cockpit/src/renderer/components/RightRail.tsx (right rail UI)
  - transports/api/cockpit.py (API endpoints + voice proxy)
  - infra/device_registry.json (canonical device registry)
```

---

## Task 1: Backend — Device Presence Registry + Voice Route Resolver + Response Contract

**files:**
- substrate/workstation/device_presence.py (CREATE)
- substrate/workstation/voice_route_resolver.py (CREATE)
- substrate/organism/advisor_conversation.py (MODIFY)
- transports/api/cockpit.py (MODIFY — add device presence endpoints + routing in advisor/converse)
- umh/voice_server.py (MODIFY — session_id awareness in handle_voice)

**action:**

### A. Device Presence Registry (`substrate/workstation/device_presence.py`)

Create in-memory registry for active device sessions:

```python
@dataclass
class DeviceSession:
    device_id: str
    session_id: str
    operator_id: str = "default"
    client_type: str = "desktop_browser"  # mobile_browser | desktop_browser | electron | terminal
    device_label: str = ""
    control_surface: str = "fly_cockpit"  # fly_cockpit | local_cockpit | electron_cockpit | terminal
    current_panel: str = ""
    can_capture_audio: bool = True
    can_play_audio: bool = True
    reachable_nodes: list[str] = field(default_factory=lambda: ["cockpit", "vps"])
    last_seen: str = ""
    status: str = "active"  # active | idle | disconnected

class DevicePresenceRegistry:
    _sessions: dict[str, DeviceSession]  # session_id -> DeviceSession
    _lock: threading.Lock

    register_session(session: DeviceSession) -> None
    heartbeat(session_id: str, updates: dict) -> bool
    get_session(session_id: str) -> DeviceSession | None
    get_active_sessions() -> list[DeviceSession]
    get_default_audio_output(source_session_id: str) -> str
    mark_disconnected(session_id: str) -> None
    cleanup_stale(max_age_seconds: int = 60) -> int

# Module-level singleton
_registry = DevicePresenceRegistry()
def get_registry() -> DevicePresenceRegistry: ...
```

Session expiry: mark disconnected after 60s without heartbeat.

### B. Voice Route Resolver (`substrate/workstation/voice_route_resolver.py`)

```python
@dataclass
class VoiceRoute:
    input_device: str
    control_surface: str
    execution_target: str
    audio_output_device: str
    audio_output_session: str
    response_render_surface: str
    handoff_mode: str = "conversation"  # conversation | remote_control
    route_reason: str = ""
    requires_approval: bool = False

def resolve_voice_route(
    transcript: str,
    source_session_id: str,
    view_context: dict | None = None,
    requested_target_node: str | None = None,
) -> VoiceRoute: ...
```

Route resolution rules:
1. Audio returns to source session by default
2. Detect target node from transcript: "on the workstation"/"on Beast" -> beast_windows, "on VPS"/"on the server" -> vps
3. Detect audio overrides: "speak from the workstation", "talk back here", "say it on my phone"
4. If source session can't play audio -> text_only
5. If no audio session exists -> text_only

Expose `parse_audio_override(transcript)` and `parse_target_node(transcript)` as separate deterministic functions.

### C. Spoken Response Contract

Modify `AdvisorResponse` in advisor_conversation.py to add:
```python
@dataclass
class AdvisorResponse:
    text: str  # existing — becomes display_text alias
    spoken_text: str = ""  # new — concise version for TTS
    ... existing fields ...
    routing: dict[str, Any] = field(default_factory=dict)  # voice route metadata

    @property
    def display_text(self) -> str:
        return self.text

    def to_api_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.spoken_text:
            d["spoken_text"] = self.spoken_text
        if self.routing:
            d["routing"] = self.routing
        return d
```

In `converse()`, after getting the response:
- If source == "voice", generate spoken_text from text (strip markdown, shorten)
- If routing metadata in the request, run route resolver and attach routing to response

### D. API Endpoints

Add to `transports/api/cockpit.py`:
- `POST /device/register` — register a device session
- `POST /device/heartbeat` — heartbeat update
- `GET /device/sessions` — list active sessions
- `POST /device/disconnect` — mark session disconnected

Modify `advisor_converse()`:
- Accept optional `routing` dict in payload
- If present, run `resolve_voice_route()` and attach to response
- Pass routing metadata through to response JSON

### E. Voice Server Session Awareness

In `umh/voice_server.py`, update `handle_voice()`:
- Accept session_id from the client via initial JSON message
- Store session_id per WebSocket connection
- Include session_id in transcript responses

**verify:**
```bash
python3 -m py_compile substrate/workstation/device_presence.py
python3 -m py_compile substrate/workstation/voice_route_resolver.py
python3 -m py_compile substrate/organism/advisor_conversation.py
python3 -m py_compile transports/api/cockpit.py
python3 -m py_compile umh/voice_server.py
```

**done:** All backend modules compile, device registry accepts sessions, route resolver separates execution from audio, response contract includes spoken_text.

---

## Task 2: Frontend — Device Session Store + Routing Metadata + Voice Route HUD

**files:**
- cockpit/src/renderer/stores/deviceSessionStore.ts (CREATE)
- cockpit/src/renderer/api/device-presence.ts (CREATE)
- cockpit/src/renderer/components/VoiceRouteHud.tsx (CREATE)
- cockpit/src/renderer/api/voice-ws.ts (MODIFY)
- cockpit/src/renderer/api/voice-controller.ts (MODIFY)
- cockpit/src/renderer/stores/chatStore.ts (MODIFY)
- cockpit/src/renderer/stores/voiceStore.ts (MODIFY)
- cockpit/src/renderer/components/RightRail.tsx (MODIFY)

**action:**

### A. Device Session Store (`deviceSessionStore.ts`)

Zustand store with:
```typescript
interface DeviceSessionState {
  deviceId: string        // persisted in localStorage
  sessionId: string       // persisted in sessionStorage
  clientType: 'mobile_browser' | 'desktop_browser' | 'electron' | 'terminal'
  canCaptureAudio: boolean
  canPlayAudio: boolean
  registered: boolean
  lastHeartbeat: string | null
  voiceRoute: VoiceRouteInfo | null

  initialize: () => void  // detect client type, generate/restore IDs, register
  heartbeat: () => void
  setVoiceRoute: (route: VoiceRouteInfo | null) => void
}

interface VoiceRouteInfo {
  inputDevice: string
  controlSurface: string
  executionTarget: string
  audioOutputDevice: string
  audioOutputSession: string
  handoffMode: string
  routeReason: string
}
```

Client type detection:
- `window.cockpit` exists -> electron
- mobile UA or viewport < 768px -> mobile_browser
- else -> desktop_browser

On initialize: register with backend, start 20s heartbeat interval.

### B. Device Presence API (`device-presence.ts`)

```typescript
export async function registerDevice(session: DeviceRegistration): Promise<void>
export async function heartbeatDevice(sessionId: string, updates: object): Promise<void>
export async function disconnectDevice(sessionId: string): Promise<void>
export async function getActiveSessions(): Promise<DeviceSession[]>
```

### C. Chat Store Modifications

In `sendMessage()` and `addVoiceTranscript()`, include routing metadata from deviceSessionStore:
```typescript
const routing = {
  source_device_id: deviceSessionStore.getState().deviceId,
  source_session_id: deviceSessionStore.getState().sessionId,
  control_surface: deviceSessionStore.getState().clientType === 'electron' ? 'electron_cockpit' : 'fly_cockpit',
  audio_return_route: 'source_device',
}
```

### D. Voice Controller Modifications

In voice-controller.ts, after receiving DEX response:
- Check for `spoken_text` in the response — use it for TTS instead of full `content`
- Update voiceStore with route info from response metadata

### E. Voice Route HUD (`VoiceRouteHud.tsx`)

Compact display for RightRail showing active voice route:
```
VOICE ROUTE
Input: iPhone mic
Output: iPhone speaker
Target: Beast Windows
Mode: Remote control
```

Only shows when voice is active (micState !== 'idle' or ttsState !== 'idle').

### F. RightRail Integration

Import and render VoiceRouteHud in ChatSection, between the AI name header and messages.
Initialize deviceSessionStore on RightRail mount (Shell.tsx).

**verify:**
```bash
cd cockpit && npx tsc --noEmit && npm run build
```

**done:** Frontend registers device sessions, voice requests include routing metadata, voice route HUD visible, TTS uses spoken_text when available.

---

## Task 3: Tests + Transcript Persistence + Final Report

**files:**
- tests/test_device_presence.py (CREATE)
- tests/test_voice_route_resolver.py (CREATE)
- data/umh/trinity_convergence/phase14_13u_device_presence_voice_session_routing_report.md (CREATE)

**action:**

### A. Device Presence Tests (`test_device_presence.py`)

```python
test_register_session()           # session registers and is retrievable
test_heartbeat_updates()          # heartbeat refreshes last_seen
test_stale_session_cleanup()      # sessions expire after timeout
test_multiple_sessions()          # multiple sessions coexist
test_default_audio_output()       # returns source session as audio output
test_disconnect_marks_status()    # disconnect changes status
```

### B. Voice Route Resolver Tests (`test_voice_route_resolver.py`)

```python
test_phone_to_beast_audio_returns_phone()       # "open spotify on workstation" from phone -> audio stays on phone
test_workstation_audio_returns_workstation()     # "open spotify" from beast -> audio on beast
test_vps_audio_returns_source()                 # "show docker containers" from phone -> audio on phone
test_override_speak_from_workstation()          # "speak from the workstation" -> audio rerouted
test_text_only_no_audio()                       # terminal session -> text_only
test_spoken_text_no_metadata()                  # spoken_text strips markdown/metadata
test_display_and_spoken_separated()             # display_text != spoken_text for complex responses
test_identity_response_contract()               # identity answers use spoken contract
test_governance_unchanged()                     # unsafe VPS commands still blocked
test_target_node_parsing()                      # "on the workstation" / "on beast" / "on vps" parsed
test_audio_override_parsing()                   # "talk to me on my phone" / "speak from beast"
test_conversation_default()                     # no target node -> conversation target
```

### C. Transcript Persistence

In `AdvisorConversation._save_turn()`, add routing/device metadata to the persisted JSONL entry when source is voice:
```python
entry["source"] = source  # "voice" or "text"
entry["device_id"] = routing.get("source_device_id", "")
entry["session_id"] = routing.get("source_session_id", "")
entry["execution_target"] = routing.get("execution_target", "")
entry["audio_output_session"] = routing.get("audio_output_session", "")
```

### D. Final Report

Create `data/umh/trinity_convergence/phase14_13u_device_presence_voice_session_routing_report.md`:
- Original problem statement
- LyfeOS lessons extracted (brief)
- Device registry design and result
- Voice routing metadata result
- Route resolver result
- Spoken/display contract result
- Test results
- Remaining limitations (multi-device hardware test needs operator, real TTS session scoping needs voice server restart)
- Final verdict: PARTIAL (simulation verified, hardware multi-device test requires operator)

**verify:**
```bash
cd /opt/OS/.claude/worktrees/voice-ws-proxy-fix
python3 -m pytest tests/test_device_presence.py tests/test_voice_route_resolver.py tests/test_voice_identity.py -v
```

**done:** All tests pass, transcript persistence includes device metadata, final report exists with clear verdict.
