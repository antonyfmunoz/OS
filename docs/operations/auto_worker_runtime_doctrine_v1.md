# Auto Worker Runtime Doctrine v1

**Phase**: 94D.4 — Auto Worker Runtime + Topology Boundary
**Status**: ACTIVE
**Date**: 2026-05-04

---

## Doctrine

Workers default to AUTO mode. In AUTO mode, a worker proceeds through
its governed runtime loop automatically and only pauses at required
governance gates. The human is not asked to confirm every step.

## AUTO Mode Runtime Loop

```
1. BOOTING → boot_complete → IDLE
2. IDLE → work_available → CLAIMING_WORK
3. CLAIMING_WORK → claimed → VALIDATING_WORK
4. VALIDATING_WORK → valid → PLANNING
5. PLANNING → plan_ready → EXECUTING  (or → approval_needed)
6. EXECUTING → action_complete → OBSERVING → continue → EXECUTING
7. EXECUTING → all_done → REPORTING
8. REPORTING → complete → COMPLETE  (or → feedback → FEEDBACK_SYNC)
```

The worker only stops at step 5 or 6 if governance says the next action
requires advisor approval.

## Governance Integration

Every action in the execution plan passes through `evaluate_action_gate()`:
- `ALLOW` → proceed immediately
- `REQUIRE_ADVISOR_APPROVAL` → pause, send approval request via message bus
- `BLOCK` → action cannot proceed, worker moves to BLOCKED
- `PAUSE_FOR_HUMAN` → freeze entire worker until founder responds

## Claim Validation

Before a worker can claim a work order:
1. Worker must not be `DISABLED` or `PAUSED`
2. Worker must have all capabilities required by the work order's task type
3. Missing capabilities → claim denied, reason explains what's missing

## Execution Plan Construction

`create_worker_execution_plan()` takes a work order and produces a list
of `WorkerAction` objects in execution order. Each action knows:
- Whether it requires approval (from work order authority mode)
- Its risk level
- Its target backend (GUI computer use, browser, API, manual)

## Advisor Response Handling

When an approval response arrives:
- `APPROVE` → transition to EXECUTING, clear pending approval
- `DENY` → transition to BLOCKED, record reason
- `MODIFY` → transition to EXECUTING with modifications
- `STOP` → transition to FAILED

## Files

- `eos_ai/substrate/worker_node_runtime.py` — all runtime functions
- `eos_ai/substrate/governance_gate_contracts.py` — gate evaluation
