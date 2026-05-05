# Advisor-Gated Human-in-the-Loop Policy v1

**Phase**: 94D.4 — Auto Worker Runtime + Topology Boundary
**Status**: ACTIVE
**Date**: 2026-05-04

---

## Policy

All human intervention routes through the Central Advisor Session.
The advisor session is the single point of coordination between the
founder and all worker nodes. Workers never talk directly to the founder.

## Message Flow

```
Worker → (approval request) → Message Bus → Advisor Session
Advisor Session → (routed to interface) → Founder
Founder → (response) → Message Bus → Advisor Session
Advisor Session → (correlated response) → Worker
```

## Relay Runtime Functions

| Function | Purpose |
|----------|---------|
| `create_approval_request_message()` | Worker builds APPROVAL_NEEDED envelope |
| `create_approval_response_message()` | Founder builds APPROVAL_RESPONSE envelope |
| `route_message_to_interface()` | Route to specific interface (Discord, CLI, etc.) |
| `route_message_to_worker()` | Route response back to specific worker |
| `correlate_response_to_request()` | Match response to pending request by approval ID or correlation ID |
| `build_worker_status_message()` | Worker reports progress |
| `build_worker_result_message()` | Worker reports final result |
| `apply_human_response_to_worker_state()` | Apply founder decision to worker state machine |

## Founder Response Types

| Response | Effect on Worker |
|----------|-----------------|
| `APPROVE` | Resume execution |
| `DENY` | Block worker, record reason |
| `MODIFY` | Resume execution with modifications |
| `STOP` | Terminate worker (FAILED) |
| `PAUSE` | Freeze worker (BLOCKED) |
| `RESUME` | Unfreeze paused worker |

## Correlation

Responses are matched to requests by:
1. `approval_request_id` in payload (primary)
2. `correlation_id` on the envelope (fallback)
3. If neither matches, response is unmatched (returns None)

## Interface Agnosticism

The approval request does not know which interface the founder will use.
The advisor session decides which interface to route to based on:
- Which interfaces are connected
- Which interfaces are approval-capable
- Founder preference

## File

`eos_ai/substrate/advisor_relay_runtime.py`
