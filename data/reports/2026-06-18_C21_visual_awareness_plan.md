# Campaign 21 — Visual Awareness & Environmental Context

## Context

C20 gave UMH voice. C21 gives UMH sight.

Today UMH cannot reliably answer: "What am I looking at?" or "Continue this work" from screen context alone. Phase 33-34 built the screen observation pipeline (ScreenObservationEngine with 3 providers), but it's not composed into the operational runtime layer. C21 bridges that gap — composing existing visual infrastructure into a unified visual brain that answers 5 acceptance tests.

**Key architectural insight:** C21 is ~85% composition over existing infrastructure. Phase 33-34 already built ScreenObservationEngine, 3 providers, ScreenSnapshot types, WorkstationTranslator, and 10 API endpoints. C21 does NOT rebuild any of this — it composes it with workspace/session/attention runtimes.

---

## What Already Exists (100% reused, not rebuilt)

| System | Location | Lines |
|--------|----------|-------|
| ScreenObservationEngine | `substrate/operator/screen_observation_engine.py` | 272 |
| Screen types (8 types) | `substrate/operator/screen_awareness.py` | 291 |
| 3 Screen Providers | `substrate/operator/screen_context_providers.py` | 296 |
| WorkstationTranslator | `substrate/operator/workstation_translator.py` | 210 |
| RepositoryContextResolver | `substrate/operator/repository_context_resolver.py` | 107 |
| VisionSceneManager | `substrate/workstation/vision_scene.py` | 529 |
| Vision Query (VLM) | `substrate/workstation/vision_query.py` | 269 |
| Camera Commands | `substrate/workstation/camera_commands.py` | 647 |
| Screen Awareness Routes | `transports/api/cockpit_screen_awareness_routes.py` | 145 |
| screenAwarenessStore | `cockpit/src/renderer/stores/screenAwarenessStore.ts` | 130 |

Already registered in canonical_types.py lines 688-705: ScreenSourceType, ScreenContextStatus, ApplicationCategory, FocusedApplication, ActiveWindow, RepositoryContext, FileContext, BrowserContext, ScreenSnapshot, all 3 providers, ScreenObservationEngine, WorkstationTranslator.

---

## Build Plan

### C21.0 — Screen Awareness Runtime (~280 lines)

**File:** `substrate/workstation/screen_awareness_runtime.py`

**Purpose:** Thin composition over ScreenObservationEngine + WorkspaceAwarenessRuntime + PresenceRuntime. Adds device/session binding that Phase 33 doesn't have.

**Composes:**
- `substrate/operator/screen_observation_engine.ScreenObservationEngine` — current_snapshot(), provider_status()
- `substrate/organism/workspace_awareness.WorkspaceAwarenessRuntime` — detect_active_workspace()
- `substrate/organism/presence_runtime.PresenceRuntime` — capture_snapshot()

**New types (3):**
- `ScreenAwarenessHealth` (Enum: ACTIVE/STALE/DEGRADED/OFFLINE)
- `DeviceScreenBinding` (dataclass: device_id, device_role, session_id, source_type, provider_status, confidence)
- `ScreenAwarenessSnapshot` (dataclass: health, current_screen, device_binding, workspace_context, provider_status)

**Public API:**
- `current_screen()` → dict — ScreenSnapshot from engine
- `device_binding()` → DeviceScreenBinding — which device, session, provider
- `health()` → ScreenAwarenessHealth — derived from provider status + freshness
- `snapshot()` → ScreenAwarenessSnapshot — full composition

**Routes:** `transports/api/cockpit_visual_awareness_routes.py` (~55 lines)
- `GET /visual/awareness/snapshot`
- `GET /visual/awareness/health`
- `GET /visual/awareness/screen`

**Tests:** `tests/test_c21_0_screen_awareness_runtime.py` (~120 lines)

---

### C21.1 — Environment Awareness Runtime (~320 lines)

**File:** `substrate/workstation/environment_awareness_runtime.py`

**Purpose:** Aggregates all observable surfaces UMH can see. Genuinely new — nothing currently answers "what surfaces am I on?"

**Composes:**
- `substrate/organism/presence_runtime.PresenceRuntime` — get_devices(), get_online_devices()
- `substrate/workstation/session_machine_runtime.SessionMachineRuntime` — bindings(), active_workspaces()
- C21.0 `ScreenAwarenessRuntime` — current_screen()

**New types (4):**
- `SurfaceType` (Enum: DESKTOP/COCKPIT/TERMINAL/BROWSER/IDE/CONTAINER/MOBILE)
- `SurfaceHealth` (Enum: ACTIVE/IDLE/STALE/OFFLINE)
- `ObservedSurface` (dataclass: surface_type, device_id, device_role, session_id, status, detail)
- `EnvironmentAwarenessSnapshot` (dataclass: surfaces, active_count, device_count, primary_surface)

**Public API:**
- `surfaces()` → list[ObservedSurface] — all observed surfaces
- `active_surfaces()` → list[ObservedSurface] — only ACTIVE
- `primary_surface()` → ObservedSurface | None — where operator is focused
- `snapshot()` → EnvironmentAwarenessSnapshot

**Routes:** `transports/api/cockpit_visual_environment_routes.py` (~55 lines)
- `GET /visual/environment/snapshot`
- `GET /visual/environment/surfaces`

**Tests:** `tests/test_c21_1_environment_awareness.py` (~130 lines)

---

### C21.2 — Visual Context Runtime (~350 lines)

**File:** `substrate/workstation/visual_context_runtime.py`

**Purpose:** Converts screen state to operational context. The "continue this work" resolver. Screen → app → repo → branch → file → work packet → goals → decisions.

**Composes:**
- C21.0 `ScreenAwarenessRuntime` — current_screen()
- `substrate/workstation/meta_ide_context_runtime.MetaIdeContextRuntime` — context() → related_goals, decisions
- `substrate/organism/workspace_awareness.WorkspaceAwarenessRuntime` — detect_active_workspace()

**New types (3):**
- `ContextBindingDepth` (Enum: SCREEN/APPLICATION/REPOSITORY/FILE/WORK)
- `ContextBinding` (dataclass: depth, screen_summary, application, repository, branch, file_path, work_packet_id, campaign, goals, decisions, confidence)
- `VisualContextSnapshot` (dataclass: binding, binding_depth, meta_ide_context, screen_source)

**Public API:**
- `resolve_context()` → ContextBinding — full screen→work chain (waterfall resolution)
- `binding_depth()` → ContextBindingDepth — how deep the chain resolves
- `continue_work()` → dict — "continue this work" resolution
- `snapshot()` → VisualContextSnapshot

**Key logic:** `resolve_context()` is a deterministic waterfall:
1. Get screen → depth=SCREEN
2. Extract application → depth=APPLICATION
3. Extract repository → depth=REPOSITORY
4. Extract file → depth=FILE
5. Query MetaIdeContextRuntime with repo/branch → goals, decisions → depth=WORK

**Routes:** `transports/api/cockpit_visual_context_routes.py` (~60 lines)
- `GET /visual/context/snapshot`
- `GET /visual/context/binding`
- `GET /visual/context/continue`

**Tests:** `tests/test_c21_2_visual_context.py` (~140 lines)

---

### C21.3 — Attention Vision Runtime (~300 lines)

**File:** `substrate/workstation/attention_vision_runtime.py`

**Purpose:** Visual attention ranking — screen-derived error signals. Genuinely new. Adds visual sources to the attention pipeline.

**Composes:**
- C21.0 `ScreenAwarenessRuntime` — current_screen()
- `substrate/workstation/attention_aggregation_runtime.AttentionAggregationRuntime` — queue()
- C21.1 `EnvironmentAwarenessRuntime` — active_surfaces()

**New types (4):**
- `VisualSignalType` (Enum: ERROR_BANNER/FAILING_TEST/STACK_TRACE/BUILD_FAILURE/BLOCKED_EXECUTION/LINT_WARNING/NOTIFICATION)
- `VisualSignalSeverity` (Enum: CRITICAL/WARNING/INFO)
- `VisualAttentionSignal` (dataclass: signal_type, severity, source_surface, description, detected_from, confidence)
- `AttentionVisionSnapshot` (dataclass: visual_signals, critical_count, warning_count, attention_items)

**Public API:**
- `detect_visual_signals()` → list[VisualAttentionSignal] — deterministic pattern matching on screen state
- `merged_attention()` → list[dict] — visual signals + existing attention items merged
- `critical_signals()` → list[VisualAttentionSignal] — CRITICAL only
- `snapshot()` → AttentionVisionSnapshot

**Key logic:** `detect_visual_signals()` is 100% deterministic — regex/keyword matching on ScreenSnapshot fields:
- Window title contains "error", "failed", "FAIL" → ERROR_BANNER
- Terminal + test runner pattern → FAILING_TEST
- Active file contains stack trace keywords → STACK_TRACE
- IDE with build errors → BUILD_FAILURE
No LLM calls. Deterministic-first principle.

**Routes:** `transports/api/cockpit_visual_attention_routes.py` (~55 lines)
- `GET /visual/attention/snapshot`
- `GET /visual/attention/signals`
- `GET /visual/attention/critical`

**Tests:** `tests/test_c21_3_attention_vision.py` (~130 lines)

---

### C21.4 — Visual Operations Runtime (~350 lines, facade)

**File:** `substrate/workstation/visual_operations_runtime.py`

**Purpose:** Unified facade. Exactly mirrors VoiceOperationsRuntime (C20.4). Single entry point for all visual awareness queries.

**Composes:**
- C21.0 `ScreenAwarenessRuntime`
- C21.1 `EnvironmentAwarenessRuntime`
- C21.2 `VisualContextRuntime`
- C21.3 `AttentionVisionRuntime`

**New types (3):**
- `VisualOperationsHealth` (Enum: OPTIMAL/ACTIVE/DEGRADED/OFFLINE)
- `VisualCapabilityStatus` (dataclass: screen_awareness, environment_awareness, visual_context, attention_vision)
- `VisualOperationsSnapshot` (dataclass: health, screen_state, environment, context_binding, visual_signals, capabilities, critical_count)

**Public API (maps to acceptance tests):**
- `what_am_i_looking_at()` → dict — **acceptance test 1**
- `continue_this_work()` → dict — **acceptance test 2**
- `error_awareness()` → dict — **acceptance test 3**
- `all_surfaces()` → list[dict] — **acceptance test 4**
- `snapshot()` → VisualOperationsSnapshot
- `health()` → VisualOperationsHealth
- `capabilities()` → VisualCapabilityStatus

**Routes:** `transports/api/cockpit_visual_ops_routes.py` (~75 lines)
- `GET /visual/operations/snapshot`
- `GET /visual/operations/health`
- `GET /visual/operations/what-am-i-looking-at`
- `GET /visual/operations/continue`
- `GET /visual/operations/errors`
- `GET /visual/operations/surfaces`

**Tests:** `tests/test_c21_4_visual_operations.py` (~150 lines)

---

### Voice + Vision Integration (acceptance test 5)

**NOT a new runtime.** ~20 lines modifying the existing VoiceQueryEngine.

**File:** `substrate/operator/voice_query_engine.py` (currently has SCREEN domain pointing to ScreenObservationEngine)

**Change:** Extend the existing `_resolve_screen()` method to also pull from VisualOperationsRuntime when available. Add a lazy `visual_operations` property. When voice asks "what am I looking at?" or "what's failing?", the SCREEN domain now returns the richer VisualOperationsRuntime response.

No new QueryDomain enum needed — SCREEN already exists and is the right semantic bucket.

**Integration test:** `tests/test_c21_integration.py` (~80 lines) — tests voice→vision bridge, multi-surface composition, full acceptance test flow.

---

## Design Decision: VisionRelayRuntime

**OUT OF SCOPE.** The vision relay (`umh/vision_relay.py`, 2,623 lines) is ungoverned WebSocket code spawned by Electron. None of the 5 acceptance tests require it. It works as-is for the cockpit camera UI. Governing it should be a separate campaign.

---

## Totals

| Category | Count |
|----------|-------|
| New runtime files | 5 |
| New route files | 5 |
| New test files | 6 |
| Modified files | 3 (cockpit.py, canonical_types.py, voice_query_engine.py) |
| New types | 17 |
| New API endpoints | 18 |
| Est. new lines | ~2,700 |
| Est. test lines | ~750 |

---

## Build Order

```
C21.0 Screen Awareness Runtime
  ↓
C21.1 Environment Awareness   +   C21.2 Visual Context    (parallel — both depend on C21.0 only)
  ↓                                   ↓
C21.3 Attention Vision (depends on C21.0 + C21.1)
  ↓
C21.4 Visual Operations Facade (depends on C21.0-C21.3)
  ↓
Voice+Vision bridge (modify voice_query_engine.py)
  ↓
Type registration in canonical_types.py
  ↓
Cockpit router mounting in cockpit.py
  ↓
Integration tests
```

---

## Verification

```bash
# Import checks (per runtime)
python3 -c "import sys; sys.path.insert(0, '/opt/OS'); from substrate.workstation.screen_awareness_runtime import ScreenAwarenessRuntime; print('C21.0 OK')"
python3 -c "import sys; sys.path.insert(0, '/opt/OS'); from substrate.workstation.environment_awareness_runtime import EnvironmentAwarenessRuntime; print('C21.1 OK')"
python3 -c "import sys; sys.path.insert(0, '/opt/OS'); from substrate.workstation.visual_context_runtime import VisualContextRuntime; print('C21.2 OK')"
python3 -c "import sys; sys.path.insert(0, '/opt/OS'); from substrate.workstation.attention_vision_runtime import AttentionVisionRuntime; print('C21.3 OK')"
python3 -c "import sys; sys.path.insert(0, '/opt/OS'); from substrate.workstation.visual_operations_runtime import VisualOperationsRuntime; print('C21.4 OK')"

# Full test suite
python3 -m pytest tests/test_c21_0_screen_awareness_runtime.py tests/test_c21_1_environment_awareness.py tests/test_c21_2_visual_context.py tests/test_c21_3_attention_vision.py tests/test_c21_4_visual_operations.py tests/test_c21_integration.py -v

# Pre-commit gates
python3 scripts/check_dependency_direction.py --all
python3 scripts/check_type_divergence.py --all
python3 scripts/check_instance_leak.py --all
python3 scripts/check_projection_leak.py --all

# Compile check
python3 -m py_compile substrate/workstation/screen_awareness_runtime.py
python3 -m py_compile substrate/workstation/environment_awareness_runtime.py
python3 -m py_compile substrate/workstation/visual_context_runtime.py
python3 -m py_compile substrate/workstation/attention_vision_runtime.py
python3 -m py_compile substrate/workstation/visual_operations_runtime.py

# Type registration verification
python3 -c "from substrate.canonical_types import lookup; print(lookup('ScreenAwarenessRuntime')); print(lookup('VisualOperationsRuntime'))"
```

---

## Cockpit Frontend (NOT in this campaign)

The user's spec mentioned frontend wiring (visionStore, Right Rail section, Operations Panel card). However:
- `screenAwarenessStore.ts` (130 lines) already exists and polls `/api/umh/screen`
- `ScreenAwarenessPanel.tsx` (263 lines) already shows screen context in the cockpit
- The new `/visual/*` endpoints can be consumed by extending the existing store

Frontend wiring is minimal and can be done as a follow-up after backend verification. The backend runtimes + routes are the C21 deliverable.
