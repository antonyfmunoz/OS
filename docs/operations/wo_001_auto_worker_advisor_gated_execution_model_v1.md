# WO-001 Auto Worker + Advisor-Gated Execution Model v1

**Phase**: 94D.4 — Auto Worker Runtime + Topology Boundary
**Status**: ACTIVE
**Date**: 2026-05-04

---

## Purpose

Define how WO-LOCAL-PILOT-GDRIVE-GDOCS-001 would execute under the
Phase 94D.4 runtime. This is the corrected execution model using
auto workers, capability routing, governance gates, and advisor relay.

## Step 1 — Capability Routing

```
Task: GOOGLE_WORKSPACE_DISCOVERY
Required: gui_computer_use, browser_session
```

`choose_best_node()` evaluates the founder's topology:
- VPS: no gui_computer_use → score 0.0
- Local PC: gui_computer_use + browser_session → score ~0.7+

**Result**: Routed to `local_pc_worker`.

## Step 2 — Worker Claim

Local PC worker validates it can claim:
- Mode: AUTO ✓
- Capabilities: gui_computer_use ✓, browser_session ✓

**Result**: Claimed. Worker transitions IDLE → CLAIMING → VALIDATING → PLANNING.

## Step 3 — Execution Plan

Work order allowed actions:
- `inventory_files` → ALLOW (no approval needed)
- `read_document` → REQUIRE_ADVISOR_APPROVAL
- `screenshot_capture` → REQUIRE_ADVISOR_APPROVAL
- `export_document` → REQUIRE_ADVISOR_APPROVAL

Plan: 4 actions in order. 3 require approval.

## Step 4 — Auto Execution with Gates

```
Action 1: inventory_files
  → evaluate_action_gate() → ALLOW
  → execute automatically
  → EXECUTING → OBSERVING → EXECUTING

Action 2: read_document
  → evaluate_action_gate() → REQUIRE_ADVISOR_APPROVAL
  → pause, send APPROVAL_NEEDED via message bus
  → advisor session routes to founder's active interface
  → founder responds APPROVE
  → resume execution
  → EXECUTING → OBSERVING → EXECUTING

Action 3: screenshot_capture
  → same approval flow

Action 4: export_document
  → same approval flow
```

## Step 5 — Reporting

Worker transitions EXECUTING → REPORTING.
Sends RESULT message via bus with:
- Status: success/partial
- Summary: what was accomplished
- Result path: where output was written

## Step 6 — Feedback Sync

Worker emits `WorkerFeedbackEvent` for organism learning.
Transitions REPORTING → FEEDBACK_SYNC → COMPLETE.

## Governance Invariants

- `send_emails`, `delete_files`, etc. → permanently BLOCKED
- Unknown actions → default to REQUIRE_ADVISOR_APPROVAL
- No action bypasses governance, even in AUTO mode
- BLOCK is terminal for that action

## Files

- `eos_ai/substrate/worker_node_runtime.py`
- `eos_ai/substrate/advisor_relay_runtime.py`
- `eos_ai/substrate/governance_gate_contracts.py`
- `eos_ai/substrate/capability_routing_contracts.py`
