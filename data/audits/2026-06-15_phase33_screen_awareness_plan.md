# Phase 33 — Screen Awareness Runtime

## Context

Phases 27–32 built topology, state authority, service dependency, operator home, presence/continuity. UMH now knows where it runs, what services exist, who owns state, what the operator was doing, and what should be resumed. But UMH cannot answer: what is the operator currently looking at? What repo is open? What file is being edited? What terminal is active?

Phase 33 creates the canonical screen awareness layer — deterministic inference of the operator's visual workspace context from existing subsystem state.

**Critical constraint: headless VPS.** The primary runtime has no display server. "Screen awareness" means **inferring** visual context from process state (terminals, git, engineering sessions), not actual screen capture. The data model supports future screen capture from devices that can see (Beast PC), but the VPS implementation is inference-only.

**Naming: "Screen Awareness" not "Vision."** `cockpit/src/renderer/stores/visionStore.ts` (1288 lines) already exists for camera/PTZ on Beast. "Vision" would collide. Phase 33 uses `screen_awareness` / `screen_observation` / `ScreenSnapshot` throughout.

---

## Design Decisions

### 1. Inference-first architecture
`current_snapshot()` on VPS returns INFERRED context from WorkspaceObservationEngine (terminals, sessions, repos) and WorkspaceTopologyEngine (workspace→repo mapping). No subprocess calls, no screen capture, no OCR. All deterministic.

### 2. Report path for devices that can see
`report_context(snapshot)` accepts visual context from Beast PC or iPad. This is the extension point — Phase 33 builds the data model and engine; future phases wire up device reporting.

### 3. ScreenSourceType: INFERRED / REPORTED / OBSERVED
Not SCREENSHOT/WINDOW/DISPLAY from the original spec. INFERRED = from process state (VPS default). REPORTED = pushed from another device. OBSERVED = actual screen capture (future).

### 4. No OperatorSnapshot modification
Screen context exposed as a separate `screen_context()` method on OperatorContextEngine, not injected into the existing OperatorSnapshot dataclass. Lower risk, same information accessible via a dedicated route.

### 5. Reuses PresenceDeviceType from Phase 32
No new device enum. Type coherence maintained.

### 6. WorkspaceTopologyEngine is at `substrate/meta_ide/workspace_topology_engine.py`
Not `substrate/organism/` — confirmed via grep.

---

## Implementation Plan

### Workcell A — Screen Awareness Models (~200 lines)

**File:** `substrate/operator/screen_awareness.py`

**3 Enums (str, Enum):**

| Enum | Values |
|------|--------|
| `ScreenSourceType` | INFERRED, REPORTED, OBSERVED |
| `ScreenContextStatus` | ACTIVE (<60s), STALE (60-300s), UNKNOWN (>300s or no data) |
| `ApplicationCategory` | IDE, TERMINAL, BROWSER, COMMUNICATION, DESIGN, OTHER |

**6 Dataclasses (all with `to_dict()` / `from_dict()`):**

| Dataclass | Key Fields |
|-----------|------------|
| `FocusedApplication` | app_name, category: ApplicationCategory, pid=0, window_title="", is_focused=True, detected_at |
| `ActiveWindow` | window_id, title, application="", is_active=True, workspace_id="", detected_at |
| `RepositoryContext` | repo_name, repo_path, workspace_id="", branch="", head_commit="", dirty_files=0, active_file="", detected_at |
| `FileContext` | file_path, file_name, repo_name="", language="", line_number=0, detected_at |
| `BrowserContext` | url="", title="", domain="", detected_at |
| `ScreenSnapshot` | source_type, status, device_type (PresenceDeviceType), device_id, active_application, active_window, repository_context, file_context, browser_context, applications: list, generated_at |

Import `PresenceDeviceType` from `substrate.operator.operator_presence`.

### Workcell B — Screen Observation Engine (~250 lines)

**File:** `substrate/operator/screen_observation_engine.py`

Aggregation façade composing 3 subsystems via lazy properties (same try/except pattern as ContinuityEngine):

| Dependency | Source | Used For |
|-----------|--------|----------|
| `WorkspaceObservationEngine` | `substrate.meta_ide.workspace_observation` | terminals, sessions, repos |
| `WorkspaceTopologyEngine` | `substrate.meta_ide.workspace_topology_engine` | workspace→repo mapping |
| `ContinuityEngine` | `substrate.operator.continuity_engine` | device context |

**Constructor:** `__init__(self, workspace_engine=None, topology_engine=None, continuity_engine=None)`

**Public API:**

| Method | Returns | Description |
|--------|---------|-------------|
| `current_snapshot()` | `ScreenSnapshot` | Infers visual context from process state |
| `active_application()` | `FocusedApplication \| None` | From engineering sessions/terminals |
| `active_window()` | `ActiveWindow \| None` | From most recent active terminal/session |
| `active_repository()` | `RepositoryContext \| None` | First dirty repo, or first repo |
| `active_file()` | `FileContext \| None` | From session or None on VPS |
| `active_browser()` | `BrowserContext \| None` | Always None on VPS |
| `report_context(snapshot)` | `None` | Accept visual context from another device |
| `history(limit=20)` | `list[ScreenSnapshot]` | Recent snapshots from deque(maxlen=100) |

**Inference logic (all deterministic):**
- `_infer_from_workspace()` → reads `workspace_engine.latest()`
- `_infer_active_application()` → from engineering sessions: claude_code → IDE, active terminal → TERMINAL
- `_infer_repository_context()` → from repos: pick first with dirty_files > 0, else first
- `_infer_file_context()` → None unless session provides file info
- `_infer_browser_context()` → None on VPS
- `_determine_status(generated_at)` → ACTIVE if <60s, STALE if <300s, UNKNOWN otherwise
- `_detect_device()` → delegates to continuity_engine for device_type/device_id

**Graceful degradation:** Each `_infer_*` returns None on failure. `current_snapshot()` always returns valid `ScreenSnapshot` — worst case: source_type=INFERRED, status=UNKNOWN, all fields None.

### Workcell C — Repository Context Resolver (~150 lines)

**File:** `substrate/operator/repository_context_resolver.py`

Maps workspace/topology data into structured repo context.

**Constructor:** `__init__(self, workspace_engine=None, topology_engine=None)`

**Public API:**

| Method | Returns | Description |
|--------|---------|-------------|
| `resolve(repo_path)` | `RepositoryContext \| None` | Path → full repo context |
| `resolve_workspace(workspace_id)` | `list[RepositoryContext]` | All repos in workspace |
| `active_repositories()` | `list[RepositoryContext]` | Repos with dirty_files > 0 |

Reads from `workspace_engine.latest().repositories` (list of dicts). Maps to `RepositoryContext` dataclass.

### Workcell D — ContinuityEngine Integration

**Modify:** `substrate/operator/continuity_engine.py`

- Add `self._screen_observation = None` to `__init__`
- Add lazy property `screen_observation` → `ScreenObservationEngine` (shares workspace_engine, topology_engine)
- Add public method `screen_context() -> dict | None` — returns `engine.current_snapshot().to_dict()` or None

### Workcell E — OperatorContextEngine Enrichment

**Modify:** `substrate/operator/operator_context_engine.py`

- Add `self._screen_observation = None` to `__init__`
- Add lazy property `screen_observation` → `ScreenObservationEngine`
- Add public method `screen_context() -> dict` — returns snapshot dict or `{}`

Do NOT modify `snapshot()` return shape — screen context is a separate route.

### Workcell F — Cockpit Routes (~100 lines)

**New file:** `transports/api/cockpit_screen_awareness_routes.py`

Pattern: identical to `cockpit_operator_presence_routes.py`

| Route | Method | Returns |
|-------|--------|---------|
| `/screen` | GET | Full ScreenSnapshot |
| `/screen/current` | GET | Active app + window |
| `/screen/application` | GET | Active application only |
| `/screen/file` | GET | Active file only |
| `/screen/repository` | GET | Active repository |
| `/screen/repositories` | GET | All active repos |

Module-level: `screen_awareness_router = APIRouter()`
Lazy singletons: `_get_engine()` → ScreenObservationEngine, `_get_resolver()` → RepositoryContextResolver

### Workcell G — Cockpit Store + Panel

**New file:** `cockpit/src/renderer/stores/screenAwarenessStore.ts` (~90 lines)
- Zustand store, `API_BASE = "/api/umh/screen"`
- `fetchSnapshot()`, `fetchRepositories()`

**New file:** `cockpit/src/renderer/panels/ScreenAwarenessPanel.tsx` (~180 lines)
- 10s polling, dark theme, guard renders
- Sections: Current Application, Active Repository, File Context, Browser Context

### Workcell H — Type Registration + Mounts

**Modify:** `substrate/canonical_types.py` — add 11 types after Phase 32 block (before closing `}`):

```python
# Phase 33: Screen Awareness Runtime
"ScreenSourceType": ["substrate.operator.screen_awareness"],
"ScreenContextStatus": ["substrate.operator.screen_awareness"],
"ApplicationCategory": ["substrate.operator.screen_awareness"],
"FocusedApplication": ["substrate.operator.screen_awareness"],
"ActiveWindow": ["substrate.operator.screen_awareness"],
"RepositoryContext": ["substrate.operator.screen_awareness"],
"FileContext": ["substrate.operator.screen_awareness"],
"BrowserContext": ["substrate.operator.screen_awareness"],
"ScreenSnapshot": ["substrate.operator.screen_awareness"],
"ScreenObservationEngine": ["substrate.operator.screen_observation_engine"],
"RepositoryContextResolver": ["substrate.operator.repository_context_resolver"],
```

**Modify:** `substrate/operator/__init__.py` — add Phase 33 docstring block.

**Modify:** `transports/api/cockpit.py` — add `_mount_screen_awareness_router()` after line 663.

### Workcell I — Tests (~100 tests)

**File:** `tests/test_phase33_screen_awareness.py`

| Class | Tests |
|-------|-------|
| TestScreenSourceTypeEnum | 4 |
| TestScreenContextStatusEnum | 4 |
| TestApplicationCategoryEnum | 4 |
| TestFocusedApplication | 4 |
| TestActiveWindow | 4 |
| TestRepositoryContext | 4 |
| TestFileContext | 4 |
| TestBrowserContext | 4 |
| TestScreenSnapshot | 5 |
| TestScreenObservationEngine | 14 |
| TestRepositoryContextResolver | 8 |
| TestContinuityEngineIntegration | 5 |
| TestOperatorContextIntegration | 4 |
| TestTypeRegistration | 4 |
| TestCockpitRoutes | 6 |
| TestIntegration | 10 |

**Total: ~98 tests**

---

## Files Summary

### New (7)
| File | Layer | ~Lines |
|------|-------|--------|
| `substrate/operator/screen_awareness.py` | substrate | 200 |
| `substrate/operator/screen_observation_engine.py` | substrate | 250 |
| `substrate/operator/repository_context_resolver.py` | substrate | 150 |
| `transports/api/cockpit_screen_awareness_routes.py` | transport | 100 |
| `cockpit/src/renderer/stores/screenAwarenessStore.ts` | cockpit | 90 |
| `cockpit/src/renderer/panels/ScreenAwarenessPanel.tsx` | cockpit | 180 |
| `tests/test_phase33_screen_awareness.py` | tests | 850 |

### Modified (4)
| File | Change |
|------|--------|
| `substrate/operator/continuity_engine.py` | +screen_observation lazy property, +screen_context() |
| `substrate/operator/operator_context_engine.py` | +screen_observation lazy property, +screen_context() |
| `substrate/canonical_types.py` | +11 type registrations |
| `substrate/operator/__init__.py` | +Phase 33 docstring |
| `transports/api/cockpit.py` | +_mount_screen_awareness_router() |

**Total new: ~1,820 lines | Modified: ~50 lines**

---

## Verification

```bash
UMH_ROOT=$(pwd) python3 -m pytest tests/test_phase33_screen_awareness.py -v
python3 scripts/check_type_divergence.py --all
python3 scripts/check_dependency_direction.py --all
python3 scripts/check_projection_leak.py --all
python3 scripts/check_instance_leak.py --all
UMH_ROOT=$(pwd) python3 -m pytest tests/test_phase32_presence_continuity.py -v  # regression
python3 -c "from substrate.operator.screen_observation_engine import ScreenObservationEngine; e = ScreenObservationEngine(); print(e.current_snapshot().to_dict())"
```

---

## What This Phase Does NOT Do

- No actual screen capture or OCR
- No keyboard/mouse automation
- No remote desktop control
- No autonomous execution
- No LLM calls — deterministic inference only
- No modification to Phase 32 systems (presence/continuity)
- No modification to OperatorSnapshot dataclass shape
- No modification to existing visionStore.ts (camera/PTZ — different domain)
- Vision augments observation, never overrides substrate state
