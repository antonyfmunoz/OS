# Phase 33 — Screen Awareness Runtime Report

**Date**: 2026-06-16
**Status**: COMPLETE
**Commit**: 6586134e (merged to main as 6a4d8e15)
**Tests**: 115 passed, 0 failed
**Gate Violations**: 0 (all 4 gates clean)

---

## What Phase 33 Delivers

A **node-role-aware visual workspace observation layer** for UMH's distributed organism. The system can answer "what is the operator currently looking at?" across all nodes.

### Three-Provider Architecture

| Provider | Node | Confidence | Activation |
|----------|------|-----------|------------|
| InferredScreenContextProvider | VPS (orchestrator) | 0.3 | Always active — infers from terminals, sessions, repos |
| ObservedScreenContextProvider | Beast (workstation) | 0.9 | Activated when Beast daemon pushes observed snapshots |
| ReportedScreenContextProvider | iPad/iPhone (controller) | 0.6 | Activated when controller device reports context |

### Preference Ordering

```
Sort by (status_priority, source_priority):
  ACTIVE < 60s, STALE 60-300s, UNKNOWN > 300s
  OBSERVED > REPORTED > INFERRED (within same freshness)
  
Key: stale OBSERVED does NOT beat fresh INFERRED
```

### Source Provenance

Every `ScreenSnapshot` carries:
- `source_node_id` — which UMH node produced this data
- `source_device_id` — which physical device
- `source_device_role` — role classification (orchestrator, workstation, controller)
- `source_confidence` — 0.0-1.0 confidence score

---

## Files

### New (8)
| File | Layer | Lines |
|------|-------|-------|
| `substrate/operator/screen_awareness.py` | substrate | 281 |
| `substrate/operator/screen_context_providers.py` | substrate | 296 |
| `substrate/operator/screen_observation_engine.py` | substrate | 272 |
| `substrate/operator/repository_context_resolver.py` | substrate | 107 |
| `transports/api/cockpit_screen_awareness_routes.py` | transport | 106 |
| `cockpit/src/renderer/stores/screenAwarenessStore.ts` | cockpit | 130 |
| `cockpit/src/renderer/panels/ScreenAwarenessPanel.tsx` | cockpit | 263 |
| `tests/test_phase33_screen_awareness.py` | tests | 1396 |

### Modified (5)
| File | Change |
|------|--------|
| `substrate/operator/continuity_engine.py` | +screen_observation lazy property, +screen_context(), +visual metadata in checkpoints |
| `substrate/operator/operator_context_engine.py` | +screen_observation lazy property, +screen_context() |
| `substrate/canonical_types.py` | +15 type registrations |
| `substrate/operator/__init__.py` | +Phase 33 docstring |
| `transports/api/cockpit.py` | +screen_awareness_router mount |

**Total: 2,966 new lines across 13 files**

---

## Verification Results

| Check | Result |
|-------|--------|
| Phase 33 tests | 115/115 passed |
| Phase 32 regression | 108/108 passed |
| Type divergence gate | 0 Phase 33 violations |
| Dependency direction gate | 0 Phase 33 violations |
| Instance leak gate | 0 Phase 33 violations |
| Projection leak gate | 0 Phase 33 violations |
| Live VPS snapshot | source_type=inferred, confidence=0.3, node=umh-vps |
| Provider status | inferred=available, observed=unavailable, reported=unavailable |
| All files compile | 8/8 clean |

---

## Test Coverage (20 test classes)

| Class | Tests | Focus |
|-------|-------|-------|
| TestScreenSourceTypeEnum | 4 | Enum values, from_value |
| TestScreenContextStatusEnum | 4 | Enum values, from_value |
| TestApplicationCategoryEnum | 4 | 6 categories |
| TestFocusedApplication | 4 | Dataclass roundtrip |
| TestActiveWindow | 4 | Dataclass roundtrip |
| TestRepositoryContext | 4 | Dataclass roundtrip |
| TestFileContext | 4 | Dataclass roundtrip |
| TestBrowserContext | 4 | Dataclass roundtrip |
| TestScreenSnapshot | 6 | Source provenance, nested objects |
| TestInferredProvider | 6 | Workspace inference, always available |
| TestObservedProvider | 6 | Report/stale lifecycle |
| TestReportedProvider | 5 | Report/expiry lifecycle |
| TestScreenObservationEngine | 16 | **Preference ordering**, role mapping, graceful degradation |
| TestRepositoryContextResolver | 8 | Path/prefix/workspace resolution |
| TestContinuityEngineIntegration | 6 | Visual metadata in checkpoints |
| TestOperatorContextIntegration | 5 | Preference ordering in context |
| TestTypeRegistration | 4 | 15 canonical types registered |
| TestCockpitRoutes | 7 | 7 API routes verified |
| TestNoControlMethods | 3 | No keyboard/mouse/OCR/remote |
| TestIntegration | 10 | End-to-end preference chain |

---

## Acceptance Criteria

- [x] VPS produces inferred screen/work context from substrate state
- [x] Beast/Windows has real observed-context pathway (OBSERVED provider + report_observed())
- [x] Node-role-aware via UMHNodeRegistry (Phase 28)
- [x] ScreenSnapshot records source_node_id, source_device_id, source_device_role, source_confidence
- [x] Operator context prefers observed over inferred
- [x] Continuity checkpoints preserve visual metadata
- [x] Cockpit distinguishes inferred/observed/reported context
- [x] No remote control, no keyboard/mouse automation
- [x] No conflict with visionStore.ts camera/PTZ domain

---

## What This Phase Does NOT Do

- No actual screen capture APIs (future Beast daemon integration)
- No keyboard/mouse automation
- No remote desktop control
- No OCR or computer vision
- No LLM calls — deterministic inference and preference ordering only
