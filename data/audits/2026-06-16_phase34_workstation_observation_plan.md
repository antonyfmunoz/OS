# Phase 34 — Workstation Observation Runtime

## Context

Phase 33 built a three-provider screen awareness model (Inferred/Observed/Reported) with preference ordering and source provenance. But the `ObservedScreenContextProvider` is a data-contract-complete stub — nothing pushes observed data to it. The VPS can infer what's happening from process state (confidence 0.3), but cannot observe what's actually on the Beast workstation screen.

**The gap is not new types.** Phase 33 already has `FocusedApplication`, `ActiveWindow`, `RepositoryContext`, `FileContext`, `BrowserContext`, and `ScreenSnapshot`. The gap is:

1. **Beast-side collection** — Beast daemon's `WorkspaceMonitor` only gets window titles. It needs full workstation observation: all windows, editor context, browser tabs, terminal sessions.
2. **Beast→VPS transport** — No code path exists from Beast mesh messages to `ObservedScreenContextProvider.report_observed()`. The mesh server handles `node.hello`, `node.heartbeat`, `node.capabilities_changed`, `signal.emit`, and binary camera frames — no workstation state message type.
3. **VPS-side bridge** — Something must deserialize incoming workstation state and call `report_observed()`.

**What already exists:**
- `nodes/windows/umh_node/workspace.py` — `WorkspaceMonitor`, polls active window title via pygetwindow (1s poll, 2s debounce)
- `nodes/windows/umh_node/adapters/desktop.py` — `DesktopAdapter` with `_list_windows()` (pygetwindow) and `_screenshot()` (pyautogui)
- `nodes/windows/umh_node/client.py` — `NodeClient` WebSocket client, `_on_workspace_change` callback (defined but never wired), binary frame protocol
- `transports/node_mesh/server.py` — `NodeMeshServer`, handles JSON-RPC methods, binary frames, frame callbacks
- `substrate/meta_ide/workspace_observation.py` — `TerminalObservation`, `ContainerObservation`, `EngineeringSession`, `WorkspaceObservationSnapshot`
- Phase 33's `ObservedScreenContextProvider.report_observed(ScreenSnapshot)` — the receiver, waiting for data

**Type Coherence enforcement:** The spec proposed 7 new snapshot types. Analysis shows 6 overlap with Phase 33/25 canonical types. Phase 34 reuses existing types and adds only genuinely new concepts (monitor geometry, multi-window list, browser tab list, editor project).

---

## Design Decisions

### 1. Extend Phase 33 types, don't create parallel types
`ApplicationSnapshot` → reuse `FocusedApplication` (add fields if needed)
`WindowSnapshot` → extend `ActiveWindow` (add geometry)
`BrowserTabSnapshot` → `BrowserContext` already has url/title/domain — extend to list
`TerminalSnapshot` → reuse Phase 25 `TerminalObservation`
`WorkstationSnapshot` → produce a `ScreenSnapshot` (Phase 33) with all nested fields populated

Only genuinely new types:
- `MonitorInfo` — monitor geometry/resolution (not in Phase 33)
- `EditorContext` — editor workspace/project (not just file)
- `WindowGeometry` — position/size/z-order for multi-window awareness
- `WorkstationObservationState` — full workstation state container for transport (wraps ScreenSnapshot + extras)

### 2. Three-layer architecture
```
Beast (nodes/windows/)     →  Mesh (transports/node_mesh/)  →  VPS (substrate/operator/)
Collects workstation state    Transports as JSON-RPC           Deserializes + feeds provider
```

### 3. Beast observes, VPS aggregates
All window/app/editor/browser collection runs on Beast in `nodes/windows/umh_node/`. The VPS never calls pygetwindow or pyautogui — it receives serialized state over the mesh.

### 4. New mesh message type: `node.workstation_state`
Beast sends workstation observation as a JSON-RPC method over the existing WebSocket. The mesh server routes it to a callback. No binary frame protocol needed — workstation state is structured data, not image bytes.

---

## Implementation Plan

### Workcell A — Extended Types (~80 lines)

**File:** `substrate/operator/screen_awareness.py` (MODIFY — extend existing)

Add to existing file:

```python
@dataclass
class MonitorInfo:
    """Monitor/display geometry."""
    monitor_id: str = ""
    name: str = ""
    width: int = 0
    height: int = 0
    x: int = 0
    y: int = 0
    is_primary: bool = False
    scale_factor: float = 1.0
    detected_at: float = field(default_factory=time.time)

@dataclass
class WindowGeometry:
    """Window position and size."""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    monitor_id: str = ""
    is_visible: bool = True
    is_minimized: bool = False
    z_order: int = 0

@dataclass  
class EditorContext:
    """IDE/editor workspace context beyond file-level."""
    editor_name: str = ""
    editor_category: ApplicationCategory = ApplicationCategory.IDE
    workspace_name: str = ""
    workspace_path: str = ""
    project_name: str = ""
    open_files: list[str] = field(default_factory=list)
    active_file: str = ""
    language: str = ""
    detected_at: float = field(default_factory=time.time)
```

Extend `ActiveWindow`:
- Add `geometry: WindowGeometry | None = None`

Extend `ScreenSnapshot`:
- Add `monitors: list[MonitorInfo] = field(default_factory=list)`
- Add `windows: list[ActiveWindow] = field(default_factory=list)` (all visible windows, not just active)
- Add `editor_context: EditorContext | None = None`
- Add `browser_tabs: list[BrowserContext] = field(default_factory=list)` (all tabs, not just active)
- Add `terminal_sessions: list[dict] = field(default_factory=list)`

Update `to_dict()` and `from_dict()` for all extended fields.

### Workcell B — Beast Workstation Observer (~200 lines)

**File:** `nodes/windows/umh_node/workstation_observer.py` (NEW)

Collects full workstation state on Beast. This is the PRODUCER for Phase 33's `ObservedScreenContextProvider`.

```python
class WorkstationObserver:
    """Collects workstation visual state for mesh transmission."""
    
    def __init__(self, desktop_adapter: DesktopAdapter | None = None):
        self._desktop = desktop_adapter or DesktopAdapter()
        self._poll_interval = 5.0  # seconds
        self._last_snapshot: dict | None = None
    
    def collect(self) -> dict:
        """Collect full workstation state as serializable dict."""
        windows = self._collect_windows()
        active = self._detect_active_window(windows)
        app = self._classify_application(active) if active else None
        editor = self._detect_editor_context(windows)
        browser = self._detect_browser_tabs(windows)
        monitors = self._detect_monitors()
        terminals = self._detect_terminals(windows)
        repo = self._detect_repository_context(editor)
        file_ctx = self._detect_file_context(editor)
        
        return {
            "source_type": "observed",
            "status": "active",
            "source_confidence": 0.9,
            "active_application": app,
            "active_window": active,
            "windows": windows,
            "editor_context": editor,
            "browser_tabs": browser,
            "browser_context": browser[0] if browser else None,
            "monitors": monitors,
            "terminal_sessions": terminals,
            "repository_context": repo,
            "file_context": file_ctx,
            "applications": self._list_applications(windows),
            "generated_at": time.time(),
        }
```

**Methods (all deterministic, no LLM):**
- `_collect_windows()` — pygetwindow: title, visible, minimized, geometry
- `_detect_active_window(windows)` — pygetwindow.getActiveWindow()
- `_classify_application(window)` — window title → ApplicationCategory via known patterns:
  - "Visual Studio Code", "VS Code" → IDE
  - "Cursor" → IDE
  - "Chrome", "Firefox", "Edge" → BROWSER
  - "PowerShell", "Windows Terminal", "cmd" → TERMINAL
  - "Discord", "Slack", "Teams" → COMMUNICATION
  - "Figma" → DESIGN
- `_detect_editor_context(windows)` — finds IDE windows, extracts workspace name from title pattern (`workspace - VS Code`)
- `_detect_browser_tabs(windows)` — all browser windows → title + infer domain from title
- `_detect_monitors()` — screeninfo or win32api: resolution, position, primary flag
- `_detect_terminals(windows)` — terminal-class windows
- `_detect_repository_context(editor)` — from editor workspace path if available
- `_detect_file_context(editor)` — from editor title parsing
- `_list_applications(windows)` — deduplicate by app name

### Workcell C — Client Integration (~50 lines)

**File:** `nodes/windows/umh_node/client.py` (MODIFY)

Wire `WorkstationObserver` into the daemon's main loop:

1. Import `WorkstationObserver`
2. In `_init_adapters()`: create `WorkstationObserver` (passing desktop adapter)
3. Add `_workstation_observation_loop()` async method — runs every 5s (configurable):
   - Calls `observer.collect()` in thread executor (pygetwindow blocks)
   - Sends `node.workstation_state` JSON-RPC message over WS
   - Only sends if state changed (diff against last snapshot)
4. Start observation loop task alongside heartbeat in `_connect_and_serve()`

Message format:
```json
{
  "jsonrpc": "2.0",
  "method": "node.workstation_state",
  "params": {
    "node_id": "umh-windows",
    "device_id": "beast",
    "snapshot": { /* serialized workstation state */ }
  }
}
```

### Workcell D — Mesh Server Handler (~40 lines)

**File:** `transports/node_mesh/server.py` (MODIFY)

Add handler for `node.workstation_state`:

1. In `_handle_connection()` message dispatch, add:
   ```python
   elif method == "node.workstation_state" and node_id:
       await self._handle_workstation_state(node_id, params, msg_id, ws)
   ```

2. Add `_handle_workstation_state()` method:
   - Validates incoming snapshot dict
   - Calls `_workstation_callback(node_id, params["snapshot"])` if registered
   - ACKs with JSON-RPC response

3. Add `register_workstation_callback(callback)` — parallel to existing `register_frame_callback()`

### Workcell E — VPS-Side Bridge (~100 lines)

**File:** `substrate/operator/workstation_bridge.py` (NEW)

The bridge between mesh transport and Phase 33's screen observation engine.

```python
class WorkstationObservationBridge:
    """Deserializes mesh workstation state → feeds ObservedScreenContextProvider."""
    
    def __init__(self, screen_engine: ScreenObservationEngine | None = None):
        self._screen_engine = screen_engine
    
    @property
    def screen_engine(self):
        if self._screen_engine is None:
            from substrate.operator.screen_observation_engine import ScreenObservationEngine
            self._screen_engine = ScreenObservationEngine()
        return self._screen_engine
    
    def on_workstation_state(self, node_id: str, data: dict) -> None:
        """Called by mesh server when Beast sends workstation_state."""
        snapshot = ScreenSnapshot.from_dict(data)
        snapshot.source_type = ScreenSourceType.OBSERVED
        snapshot.source_node_id = node_id
        snapshot.source_device_role = "workstation"
        self.screen_engine.report_observed(snapshot)
```

### Workcell F — Boot Wiring (~30 lines)

**File:** `transports/api/cockpit.py` (MODIFY)

Wire the bridge to the mesh server at startup:

```python
def _wire_workstation_bridge():
    """Connect mesh server workstation callback to screen observation."""
    try:
        from substrate.operator.workstation_bridge import WorkstationObservationBridge
        from transports.node_mesh.server import NodeMeshServer
        bridge = WorkstationObservationBridge()
        # Register with mesh server singleton
        ...
    except Exception:
        logger.debug("workstation bridge wiring skipped")
```

### Workcell G — Cockpit Routes (~60 lines)

**File:** `transports/api/cockpit_screen_awareness_routes.py` (MODIFY)

Add workstation-specific routes to existing router:

| Route | Method | Returns |
|-------|--------|---------|
| `/screen/workstation` | GET | Full workstation state (windows, monitors, editor, browser tabs) |
| `/screen/windows` | GET | All visible windows with geometry |
| `/screen/editor` | GET | Editor/IDE context (workspace, project, open files) |
| `/screen/monitors` | GET | Monitor layout |
| `/screen/terminals` | GET | Terminal sessions from workstation |

### Workcell H — Cockpit UI (~150 lines)

**File:** `cockpit/src/renderer/stores/screenAwarenessStore.ts` (MODIFY)

Add to existing store:
- `fetchWindows()`, `fetchEditor()`, `fetchMonitors()`
- Interfaces: `MonitorInfo`, `WindowGeometry`, `EditorContext`

**File:** `cockpit/src/renderer/panels/ScreenAwarenessPanel.tsx` (MODIFY)

Add sections to existing panel:
- **Windows** — all visible windows with geometry, highlight focused
- **Editor** — workspace name, project, open files, active file
- **Monitors** — monitor layout diagram (primary highlighted)
- **Terminals** — terminal sessions from workstation observation

### Workcell I — Type Registration (~10 lines)

**File:** `substrate/canonical_types.py` (MODIFY)

Add after Phase 33 block:
```python
# Phase 34: Workstation Observation Runtime
"MonitorInfo": ["substrate.operator.screen_awareness"],
"WindowGeometry": ["substrate.operator.screen_awareness"],
"EditorContext": ["substrate.operator.screen_awareness"],
"WorkstationObservationBridge": ["substrate.operator.workstation_bridge"],
```

4 new type registrations.

### Workcell J — Tests (~120 tests)

**File:** `tests/test_phase34_workstation_observation.py`

| Class | Tests | Focus |
|-------|-------|-------|
| TestMonitorInfo | 4 | creation, to_dict, from_dict, roundtrip |
| TestWindowGeometry | 4 | creation, to_dict, from_dict, roundtrip |
| TestEditorContext | 4 | creation, to_dict, from_dict, roundtrip |
| TestExtendedActiveWindow | 4 | geometry field, backward compat, to_dict, from_dict |
| TestExtendedScreenSnapshot | 6 | monitors, windows list, editor_context, browser_tabs, terminal_sessions, backward compat |
| TestWorkstationObserver | 12 | collect, classify_application (6 categories), detect_editor, detect_browser, detect_monitors, detect_terminals, changed detection |
| TestWorkstationBridge | 8 | on_workstation_state, source_type set to OBSERVED, source_node_id set, confidence 0.9, feeds screen_engine, graceful degradation, empty state, malformed data |
| TestMeshServerHandler | 6 | workstation_state method recognized, callback invoked, ACK sent, validation, register_workstation_callback, unknown method still rejected |
| TestClientObservationLoop | 6 | loop starts, sends workstation_state, only sends on change, interval configurable, graceful on disconnect, thread executor used |
| TestPreferenceWithWorkstation | 10 | observed workstation beats inferred, observed workstation beats reported, stale observed loses to fresh inferred, full chain, provider status updated, source provenance correct, confidence 0.9, history records, cockpit data shape, backward compat |
| TestCockpitRoutes | 5 | /screen/workstation, /screen/windows, /screen/editor, /screen/monitors, /screen/terminals |
| TestTypeRegistration | 4 | MonitorInfo, WindowGeometry, EditorContext, WorkstationObservationBridge registered |
| TestNoControlMethods | 3 | no click/type/keypress, no focus_window in observer, no automation |
| TestPhase33Regression | 8 | existing ScreenSnapshot backward compat, existing providers still work, existing routes still work, preference ordering unchanged, inferred still works without workstation, observed provider accepts new fields, type coherence no violations, all Phase 33 tests pass |
| TestIntegration | 10 | end-to-end: Beast collects → serializes → bridge receives → provider updated → engine returns OBSERVED → cockpit gets data |

**Total: ~94 tests** (aiming for ~120 with edge cases)

---

## Files Summary

### New (3)
| File | Layer | ~Lines |
|------|-------|--------|
| `nodes/windows/umh_node/workstation_observer.py` | nodes | 200 |
| `substrate/operator/workstation_bridge.py` | substrate | 100 |
| `tests/test_phase34_workstation_observation.py` | tests | 1000 |

### Modified (7)
| File | Change |
|------|--------|
| `substrate/operator/screen_awareness.py` | +MonitorInfo, +WindowGeometry, +EditorContext dataclasses; extend ActiveWindow + ScreenSnapshot |
| `nodes/windows/umh_node/client.py` | +WorkstationObserver init, +_workstation_observation_loop() |
| `transports/node_mesh/server.py` | +_handle_workstation_state(), +register_workstation_callback() |
| `transports/api/cockpit_screen_awareness_routes.py` | +5 workstation routes |
| `transports/api/cockpit.py` | +_wire_workstation_bridge() |
| `substrate/canonical_types.py` | +4 type registrations |
| `cockpit/src/renderer/stores/screenAwarenessStore.ts` | +workstation fetch methods |
| `cockpit/src/renderer/panels/ScreenAwarenessPanel.tsx` | +windows/editor/monitors/terminals sections |

**Total new: ~1,300 lines | Modified: ~300 lines**

---

## Data Flow

```
Beast daemon (nodes/windows/umh_node/)
  WorkstationObserver.collect() — pygetwindow, screeninfo
  ↓ every 5s, only on change
  NodeClient._workstation_observation_loop()
  ↓ JSON-RPC: "node.workstation_state"
  WebSocket (Tailscale :8094)
  ↓
VPS mesh server (transports/node_mesh/server.py)
  _handle_workstation_state()
  ↓ workstation_callback
WorkstationObservationBridge (substrate/operator/)
  on_workstation_state()
  ScreenSnapshot.from_dict(data)
  ↓
ObservedScreenContextProvider.report_observed(snapshot)
  ↓ preference ordering
ScreenObservationEngine.current_snapshot()
  → fresh OBSERVED (confidence 0.9) beats INFERRED (0.3)
  ↓
Cockpit API → ScreenAwarenessPanel
```

---

## Verification

```bash
# Phase 34 tests
UMH_ROOT=$(pwd) python3 -m pytest tests/test_phase34_workstation_observation.py -v

# Phase 33 regression
UMH_ROOT=$(pwd) python3 -m pytest tests/test_phase33_screen_awareness.py -v

# Pre-commit gates
python3 scripts/check_type_divergence.py --all
python3 scripts/check_dependency_direction.py --all
python3 scripts/check_instance_leak.py --all
python3 scripts/check_projection_leak.py --all

# Live verification (VPS — without Beast connected)
python3 -c "
from substrate.operator.screen_observation_engine import ScreenObservationEngine
from substrate.operator.workstation_bridge import WorkstationObservationBridge
e = ScreenObservationEngine()
b = WorkstationObservationBridge(screen_engine=e)
# Simulate Beast pushing workstation state
b.on_workstation_state('umh-windows', {
    'source_type': 'observed',
    'source_confidence': 0.9,
    'active_application': {'app_name': 'VS Code', 'category': 'ide'},
    'windows': [{'title': 'test.py - VS Code', 'is_active': True}],
    'monitors': [{'monitor_id': 'M1', 'width': 2560, 'height': 1440, 'is_primary': True}],
})
snap = e.current_snapshot()
print(f'source_type={snap.source_type}')  # Should be OBSERVED
print(f'confidence={snap.source_confidence}')  # Should be 0.9
print(f'app={snap.active_application.app_name if snap.active_application else None}')
print(f'monitors={len(snap.monitors)}')
"
```

---

## Acceptance Criteria

- [ ] Beast daemon collects full workstation state (windows, apps, editor, browser, terminals, monitors)
- [ ] State transmitted to VPS via `node.workstation_state` mesh message
- [ ] VPS bridge deserializes and feeds `ObservedScreenContextProvider.report_observed()`
- [ ] Preference ordering promotes OBSERVED over INFERRED when Beast data is fresh
- [ ] Phase 33 types extended (not duplicated) — 0 type coherence violations
- [ ] ScreenSnapshot backward compatible — existing code works unchanged
- [ ] Cockpit shows workstation-level detail (windows, editor, monitors)
- [ ] No keyboard/mouse automation, no remote control, no autonomous execution
- [ ] Phase 33 tests still pass (full regression)

---

## What This Phase Does NOT Do

- No keyboard/mouse automation (observation only)
- No remote desktop control
- No screen capture/screenshot streaming (that's camera frames, different channel)
- No OCR or computer vision
- No LLM calls — deterministic window title parsing only
- No new parallel type system — extends Phase 33 types
- No modification to Phase 33 preference ordering logic
- No browser extension for tab data (window titles only, for now)
