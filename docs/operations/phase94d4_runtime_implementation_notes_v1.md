# Phase 94D.4 Runtime Implementation Notes v1

**Phase**: 94D.4 — Auto Worker Runtime + Topology Boundary
**Status**: COMPLETE
**Date**: 2026-05-04

---

## What Was Built

7 Python modules implementing the Phase 94D.4 runtime contracts:

| Module | Purpose | Lines |
|--------|---------|-------|
| `topology_contracts.py` | Setup-agnostic topology profiles | ~245 |
| `capability_routing_contracts.py` | Capability-based node routing | ~176 |
| `worker_node_contracts.py` | Worker organism state machine | ~195 |
| `worker_node_runtime.py` | Pure worker lifecycle functions | ~212 |
| `governance_gate_contracts.py` | Governance gate evaluation | ~167 |
| `advisor_relay_runtime.py` | Advisor relay message construction | ~262 |
| `substrate_projection_boundaries.py` | UMH/EOS boundary enforcement | ~201 |

## Design Decisions

### Pure Functions, No Side Effects
All runtime modules are pure functions. No network calls, no database
writes, no file I/O. They produce data structures that callers use to
make decisions. This makes them testable without mocking.

### State Machine Enforcement at Contract Level
`WorkerRuntimeState.transition()` checks `WORKER_STATE_TRANSITIONS`
before allowing any state change. Invalid transitions raise `ValueError`.
This prevents runtime bugs from corrupting worker state.

### Governance Default: Require Approval
Unknown actions default to `REQUIRE_ADVISOR_APPROVAL`, not `ALLOW`.
This is fail-safe. A new action type that wasn't anticipated still
requires a human to approve it before execution.

### Capability Routing, Not Name Routing
`choose_best_node()` scores every node against required capabilities.
It never checks node names. A task that needs `gui_computer_use` goes
to whichever node has it, regardless of what that node is called.

### Scoring Algorithm
- Missing required capability → score 0.0 (unusable)
- Base score for all required met → 0.5
- Each preferred capability adds up to 0.3 total
- Online bonus → +0.2
- Offline penalty → -0.2
- Score clamped to [0.0, 1.0]

### Message Correlation
Responses match to requests via `approval_request_id` in payload first,
then fall back to `correlation_id` on the envelope. This handles both
structured approval flows and ad-hoc question/answer exchanges.

## Bugs Fixed During Implementation

1. `WORKER_STATE_TRANSITIONS` referenced `WorkerState.DISABLED` which
   does not exist (it's `WorkerMode.DISABLED`). Removed from IDLE
   transitions — IDLE can only go to CLAIMING_WORK.

## Test Coverage

89 tests across 5 test files. All passing.

| Test File | Tests | Focus |
|-----------|-------|-------|
| `test_phase94d4_topology_contracts.py` | 13 | Nodes, topology, serialization |
| `test_phase94d4_auto_worker_runtime.py` | 20 | Routing, state machine, claims |
| `test_phase94d4_advisor_relay_runtime.py` | 14 | Relay, routing, correlation |
| `test_phase94d4_governance_gates.py` | 15 | Block/approve/allow/unknown |
| `test_phase94d4_umh_eos_boundaries.py` | 17 | Classification, confusion, terms |
