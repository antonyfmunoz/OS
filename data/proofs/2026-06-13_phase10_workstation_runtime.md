# Phase 10: Workstation Runtime — Proof Document

**Date:** 2026-06-13
**Status:** Complete
**Tests:** 77 passed, 0 failed

## What Was Built

Canonical workstation planning layer that transforms UMH from an intelligent
command system into a workstation orchestration system.  This phase plans
workspaces — it never executes.

## Architecture Decisions

1. **Planning-only layer** — `prepare_workspace()` returns a `WorkspacePreparationPlan`
   with steps, context, recommendations.  Status stays `planned`.  No launching,
   no browser automation, no desktop control.

2. **Composition over creation** — composes Presence (P8), Continuity (P7),
   Projection (P6), Tick Loop (P5), Gap Engine (P4), Empire Router (P3),
   Command Runtime (P9).  Zero new execution engines.

3. **Deterministic mode classification** — `ModeClassifier` uses compiled regex
   patterns across 6 modes (engineering, content, music, business, research, admin).
   Weighted scoring by match count per mode.  No LLM calls.

4. **Data-driven templates** — `WorkspaceTemplateRegistry` loads from JSON, seeds
   defaults on first run.  Templates define applications, repositories, cockpit
   panels, browser tabs, context sources.  Extensible without code changes.

5. **Individually fault-tolerant context assembly** — `WorkspaceContextAssembler`
   wraps each subsystem in try/except with debug logging.  If P6 is broken,
   you still get P7+P8+P4+P5 context.

6. **JSONL-backed persistence** — `SnapshotStore` uses append-only JSONL.
   Preparation plans also persisted to JSONL.

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `substrate/organism/workstation_runtime.py` | 1,387 | Core module — all types, engines, runtime |
| `tests/test_workstation_runtime.py` | 896 | 77 tests across 19 test classes |
| `cockpit/src/renderer/panels/WorkstationPanel.tsx` | 458 | 5-tab cockpit panel |
| `data/proofs/2026-06-13_phase10_workstation_runtime.md` | this | Proof document |

## Files Modified

| File | Change |
|------|--------|
| `transports/api/cockpit_operator_loop_routes.py` | +7 routes, +101 lines (handlers) |
| `cockpit/src/renderer/stores/cockpitStore.ts` | Added `'workstation'` to Panel type |
| `cockpit/src/renderer/types/routes.ts` | Added route entry with Monitor icon, key 'k' |
| `cockpit/src/renderer/components/Shell.tsx` | Added import + case for WorkstationPanel |
| `substrate/canonical_types.py` | Registered 23 new types |

## Canonical Types Registered (23)

WorkstationMode, WorkspaceStatus, PreparationStepType, SnapshotTrigger,
RecommendationType, WorkspaceTemplate, PreparationStep,
WorkspacePreparationPlan, ApplicationState, WorkspaceState,
WorkspaceSnapshot, RestorationPlan, WorkspaceSequence,
WorkstationProfile, Workstation, WorkstationRecommendation,
ModeClassifier, WorkspaceTemplateRegistry, WorkspaceContextAssembler,
SnapshotStore, RecommendationEngine, PreparationSequencer,
WorkstationRuntime

## APIs Created (7)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/workstation/prepare` | POST | Generate workspace preparation plan |
| `/workstation/restore` | POST | Generate restoration plan from snapshot |
| `/workstation/templates` | GET | List all workspace templates |
| `/workstation/snapshots` | GET | List recent snapshots |
| `/workstation/snapshots/take` | POST | Take a workspace snapshot |
| `/workstation/recommendations` | GET | Get deterministic recommendations |
| `/workstation/state` | GET | Get current workstation state |

## Cockpit Panel

5-tab panel: Preparation, Templates, Snapshots, Restoration, Recommendations.
- Preparation: intent input with examples, full plan display with step badges
- Templates: all 6 templates with application/panel/repo/context breakdowns
- Snapshots: list with trigger, notes, objectives, restore button
- Restoration: restoration plan display with objectives and work packets
- Recommendations: priority-sorted list with type badges and source attribution

## Test Coverage (77 tests, 19 classes)

- Enums: 5 classes (WorkstationMode, WorkspaceStatus, PreparationStepType, SnapshotTrigger, RecommendationType)
- Data models: 10 classes (all types roundtrip + auto-id + nested deserialization)
- ModeClassifier: 10 tests (all 6 modes + empty/ambiguous/mixed/case-insensitive)
- TemplateRegistry: 7 tests (seed/get/add/remove/persist/missing)
- ContextAssembler: 2 tests (structure + graceful degradation)
- SnapshotStore: 5 tests (save/retrieve/by-id/latest/limit)
- RecommendationEngine: 4 tests (generate/sort/blocked-packets/approval-packets)
- PreparationSequencer: 4 tests (from-template/with-packets/priority/empty)
- WorkstationRuntime: 10 tests (prepare/restore/snapshot/state/templates)
- Singleton: 2 tests (identity/reset)
- Acceptance: 9 tests (spec scenario + no-execution + snapshot-restore + data-driven + deterministic + governance + full-lifecycle + multi-mode + context-assembly)

## Acceptance Proof

```
Intent: "Work on Operator"
  ↓ Command Runtime classifies (action_type=execute, domain=engineering)
  ↓ ModeClassifier selects ENGINEERING mode (confidence=1.0)
  ↓ WorkspaceTemplateRegistry resolves tpl-engineering
  ↓ WorkspaceContextAssembler pulls from P4-P8
  ↓ PreparationSequencer builds ordered steps
  ↓ RecommendationEngine generates from gap/projection/tick/packets
  ↓ WorkspacePreparationPlan returned (status=planned)
  ↓ No applications launched
  ↓ No work executed
  ↓ Governance maintained
```

## What Remains Before True Workstation Automation

1. **Session Runtime** — manage Claude Code / coding sessions as first-class entities
2. **Profile Runtime** — operator profile switching with workspace template binding
3. **Execution Layer** — actually launching applications, opening repositories
4. **Device Integration** — Beast daemon + VPS mesh for cross-device workspace
5. **Desktop Automation** — window management, application focus, screen layout
