# Phase 13: Execution Coordinator Runtime — Proof Document

**Date:** 2026-06-13
**Phase:** 13 — Execution Coordinator Runtime
**Status:** COMPLETE

## What Was Built

The Execution Coordinator Runtime — the canonical "DO" orchestration layer
that bridges UMH's awareness systems (WHO/HOW/WHERE/WHAT/WHY/MEMORY) with
actual execution. It receives approved WorkPackets, creates execution plans,
manages approval gates, queues work, assigns targets, and tracks full
lifecycle. It NEVER executes — only coordinates.

## Architecture

```
Command Runtime (P9) → Empire Router (P3) → WorkPackets
                                                  ↓
                              Execution Coordinator (P13)
                                   ↓         ↓
                           GovernanceGate  ExecutionQueue
                                   ↓         ↓
                              PlanStore   LifecycleTracker
                                   ↓
                           ExecutorRegistry (7 target types)
                                   ↓
                         [Phase 14+ Executor Runtimes]
```

## Components

### Canonical Types (6 enums, 4 data models)
- `ExecutionPlanStatus` — 8 states: drafted → approved → queued → dispatched → executing → completed/failed/cancelled
- `ExecutionTargetType` — 7 targets: workstation, agent, vps, container, browser, mobile, external
- `ExecutionMode` — 4 modes: synchronous, asynchronous, background, scheduled
- `ExecutionPriority` — 5 levels: critical, high, normal, low, background
- `CoordinatorApprovalState` — 4 states: pending, approved, denied, expired
- `LifecycleEventType` — 11 events covering full plan lifecycle
- `CoordinatorExecutionPlan` — binds WorkPacket to executor with session/profile
- `ExecutorDefinition` — registry entry with type, capabilities, availability
- `LifecycleEvent` — timestamped lifecycle event with details
- `ExecutionCoordinatorSnapshot` — point-in-time coordinator state

### Engines
- `ExecutorRegistry` — canonical executor target registry with 7 default types
- `ExecutionQueue` — priority queue with enqueue/dequeue/cancel/reprioritize
- `ExecutionLifecycleTracker` — JSONL event recording with query by plan/type
- `GovernanceGate` — fail-closed approval gate (low/negligible auto-approve, medium+ requires operator)
- `PlanStore` — persistent plan storage with queries by status/wp/session/profile
- `CrossRuntimeCompositor` — assembles context from P6-P12 without modifying them
- `ExecutionCoordinator` — top-level orchestrator singleton

### API Routes (13 endpoints)
- GET: `/execcoord/state`, `/execcoord/queue`, `/execcoord/active`, `/execcoord/awaiting`, `/execcoord/history`, `/execcoord/lifecycle`, `/execcoord/executors`
- POST: `/execcoord/create`, `/execcoord/approve`, `/execcoord/deny`, `/execcoord/enqueue`, `/execcoord/dispatch`, `/execcoord/cancel`

### Cockpit Panel
- ExecCoordPanel with 5 tabs: Queue, Active, Waiting Approval, History, Executors
- KPI bar: Total Plans, Queue Depth, Active, Awaiting Approval, Executors
- PlanCard component with status/priority/risk coloring and action buttons

## Governance Integration

| Risk Class | Auto-Approve? | Dispatch Allowed? |
|-----------|---------------|-------------------|
| negligible | Yes | Yes |
| low | Yes | Yes |
| medium | No | Only after operator approval |
| high | No | Only after operator approval |
| critical | No | Only after operator approval |
| unknown | No (fail closed) | Only after operator approval |

## Cross-Runtime Composition

Composes P3-P12 without modifying any of them:
- **P3** — WorkPacket as execution contract (source_workpacket_id binding)
- **P6** — Projection snapshot assembled by CrossRuntimeCompositor
- **P7** — Continuity snapshot for context assembly
- **P8** — Presence context for operator availability
- **P10** — Workstation context for workspace preparation
- **P11** — Profile context (profile_id binding on plans)
- **P12** — Session context (session_id binding on plans)

## Test Coverage

- 94 tests across 16 test classes
- Enum tests: 6 classes (all values verified)
- Data model tests: 4 classes (auto-ID, roundtrip, defaults)
- Component tests: ExecutorRegistry (7), ExecutionQueue (8), LifecycleTracker (4), GovernanceGate (12), PlanStore (10)
- Integration tests: ExecutionCoordinator (27)
- Singleton tests: 2
- Acceptance tests: 10 (full lifecycle, high-risk approval, denied plans, all types, priority ordering, failure preservation, no automation, session/profile binding, all statuses, snapshot accuracy)

## Acceptance Scenario Result

PASS. Full lifecycle: create plan → auto-approve (low risk) → enqueue → dispatch → mark started → mark completed with proof → 5 lifecycle events persisted → no execution methods exist on coordinator.

## Files

| File | Lines | Type |
|------|-------|------|
| `substrate/organism/execution_coordinator.py` | 771 | NEW |
| `tests/test_execution_coordinator.py` | 670 | NEW |
| `cockpit/src/renderer/panels/ExecCoordPanel.tsx` | 260 | NEW |
| `transports/api/cockpit_operator_loop_routes.py` | +195 | MODIFIED |
| `substrate/canonical_types.py` | +17 | MODIFIED |
| `cockpit/src/renderer/stores/cockpitStore.ts` | +1 | MODIFIED |
| `cockpit/src/renderer/components/Shell.tsx` | +2 | MODIFIED |
| `cockpit/src/renderer/types/routes.ts` | +2 | MODIFIED |

## Phase 14 Candidates

1. **Executor Runtime** — actual execution on workstation/agent/vps targets
2. **Notification Runtime** — cross-device notification routing with priority
3. **Governance Runtime** — unified governance policy engine
4. **Multi-Operator Support** — extend model for team-based operation
