# Phase 34 — Workstation Observation Runtime Report

**Date**: 2026-06-16
**Status**: COMPLETE
**Commit**: 5e74b330
**Tests**: 81 passed, 0 failed (+ 115 Phase 33 regression)
**Gate Violations**: 0 (all 4 gates clean)

---

## What Phase 34 Delivers

The **producer + transport + bridge** that feeds real workstation observations from Beast into Phase 33's screen awareness model. When Beast is online and sending window/app/editor data, the VPS promotes OBSERVED (confidence 0.9) over INFERRED (0.3) via Phase 33's preference ordering.

### Key Design Decision: No New Type System

Phase 33 already has `FocusedApplication`, `ActiveWindow`, `RepositoryContext`, `FileContext`, `BrowserContext`, and `ScreenSnapshot`. Phase 34 extends these — one new `workstation_detail: dict` field on `ScreenSnapshot` for passthrough richness (monitors, all windows, terminals). `WorkstationTranslator` bridges Beast dict payloads into canonical Phase 33 types.

### Data Flow

```
Beast daemon (nodes/windows/umh_node/)
  WorkspaceMonitor → collect_workstation_state()
    pygetwindow, psutil, screeninfo, ctypes
  ↓ every 2s, only on change (hash-based debounce)
  NodeClient._workspace_emission_loop()
    emit_signal(signal_class="workstation_state", payload={...})
  ↓ JSON-RPC "signal.emit" over WebSocket (Tailscale :8094)

VPS mesh server (transports/node_mesh/server.py)
  _handle_signal() → signal_class == "workstation_state"
    → workstation_callback(node_id, payload)
  ↓

WorkstationTranslator (substrate/operator/)
  translate(node_id, payload) → ScreenSnapshot
    Maps: focused window → active_app/active_window
    Maps: editor → file_context/repo_context
    Maps: browser tabs → browser_context
    Stuffs: monitors/windows/tabs/terminals → workstation_detail
  ↓

ObservedScreenContextProvider.report_observed(snapshot)
  ↓ preference ordering (Phase 33)

ScreenObservationEngine.current_snapshot()
  → fresh OBSERVED (confidence 0.9) beats INFERRED (0.3)
  ↓

Cockpit API → ScreenAwarenessPanel
  workstation_detail visible when source_type == "observed"
```

---

## Files

### New (2)
| File | Layer | Lines |
|------|-------|-------|
| `substrate/operator/workstation_translator.py` | substrate | 210 |
| `tests/test_phase34_workstation_observation.py` | tests | 1171 |

### Modified (8)
| File | Change |
|------|--------|
| `substrate/operator/screen_awareness.py` | +workstation_detail field on ScreenSnapshot (+to_dict/from_dict) |
| `nodes/windows/umh_node/workspace.py` | +collect_workstation_state(), enhanced WorkspaceMonitor, +hash-based debounce |
| `nodes/windows/umh_node/client.py` | +_workspace_emission_loop() task, wired into _connect_and_serve() |
| `transports/node_mesh/server.py` | +register_workstation_callback(), +workstation_state signal handler |
| `transports/api/app.py` | +_wire_workstation_bridge() in _register_node_mesh() |
| `transports/api/cockpit_screen_awareness_routes.py` | +3 routes (/screen/workstation, /screen/windows, /screen/monitors) |
| `substrate/canonical_types.py` | +1 type registration (WorkstationTranslator) |
| `substrate/operator/__init__.py` | +Phase 34 docstring |

**Total: 1,822 new lines, 28 lines modified**

---

## Verification Results

| Check | Result |
|-------|--------|
| Phase 34 tests | 81/81 passed |
| Phase 33 regression | 115/115 passed |
| Type divergence gate | 0 Phase 34 violations |
| Dependency direction gate | 0 Phase 34 violations |
| Instance leak gate | Clean |
| Projection leak gate | Clean |
| Live VPS simulation | OBSERVED beats INFERRED |
| File sizes | All under 3000 lines |

---

## Test Coverage (17 test classes)

| Class | Tests | Focus |
|-------|-------|-------|
| TestWorkstationTranslatorBasic | 4 | Empty payload, source role, device_id, timestamp |
| TestWorkstationTranslatorFocusedWindow | 5 | Focused by ID, by flag, no focus, fields, PID |
| TestWorkstationTranslatorApplications | 3 | Visible→apps, hidden excluded, empty |
| TestWorkstationTranslatorEditor | 4 | Editor→file_context, editor→repo_context, no editor, no active file |
| TestWorkstationTranslatorBrowser | 3 | Active tab, no active, no tabs |
| TestWorkstationTranslatorDetail | 3 | Detail populated, in to_dict, roundtrip |
| TestAppClassification | 9 | IDE, browser, terminal, comms, design, unknown, empty, case insensitive, partial |
| TestScreenSnapshotExtension | 6 | Default {}, to_dict, from_dict, missing, roundtrip, existing fields |
| TestBeastWorkspaceCollection | 9 | Structure, lists, non-Windows, hash determinism, hash change, editor detect, no IDE, browser detect, terminal detect |
| TestMeshServerHandler | 3 | Register callback, default None, separate from frame callback |
| TestPreferenceWithWorkstation | 6 | OBSERVED beats INFERRED, detail survives, inferred empty, provider status, provenance, history |
| TestCockpitRoutes | 5 | Workstation inferred, observed, windows, monitors, existing unchanged |
| TestTypeRegistration | 4 | Registered, Phase 33 still there, no duplicates, no parallel types |
| TestNoControlMethods | 3 | No click/type, translate only, workspace no automation |
| TestPhase33Regression | 6 | Backward compat, providers work, report works, ordering unchanged, inferred without ws, observed with detail |
| TestIntegration | 8 | E2E observed beats inferred, cockpit data, empty graceful, VPS-only, roundtrip, multiple updates, passthrough, bridge wiring |

---

## Acceptance Criteria

- [x] Beast daemon collects full workstation state (windows, apps, editor, browser, terminals, monitors)
- [x] State transmitted to VPS via `signal.emit` with `signal_class="workstation_state"`
- [x] VPS translator converts Beast payload → canonical ScreenSnapshot
- [x] Translated snapshot fed to `ObservedScreenContextProvider.report_observed()`
- [x] Preference ordering promotes OBSERVED over INFERRED when Beast data is fresh
- [x] No new type system — one `workstation_detail` dict field on ScreenSnapshot
- [x] ScreenSnapshot fully backward compatible
- [x] Cockpit shows workstation detail when OBSERVED source active
- [x] Bridge wired in `_register_node_mesh()` (mesh server lifecycle, not cockpit.py)
- [x] No keyboard/mouse automation, no remote control, no autonomous execution
- [x] Phase 33 tests still pass (115/115 regression)

---

## What This Phase Does NOT Do

- No keyboard/mouse automation (observation only)
- No remote desktop control
- No screen capture/screenshot streaming (that's camera frames, different channel)
- No OCR or computer vision
- No LLM calls — deterministic window title parsing only
- No browser extension for tab URLs (window titles only for MVP)
- No modification to Phase 33 preference ordering logic
