# VPS ↔ Local Worker Bridge Doctrine v1

**Phase:** 96.8A / 96.8A.1
**Status:** Active
**Layer:** UMH Substrate — Environment Adapter
**Module:** `core/environment_bridge/vps_local_bridge.py`

## Adapter Boundary Classification

The VPS-Local Bridge is an Environment Adapter within the Adapter Engine.
Per the UMH External Boundary Law, every environment transition (VPS →
WSL → tmux → Windows GUI → Chrome) crosses an external boundary and
requires adapter governance. Work packets dispatched through this bridge
are governed external interaction contracts.

## Purpose

The VPS-Local Bridge is the orchestrator module that evaluates which
transport paths are available and what the overall bridge status is.
It does not execute packets — it determines readiness.

## Status Evaluation Logic

```
heartbeat present + fresh + SSH reachable → READY
heartbeat present + fresh + SSH blocked   → PUSH_BLOCKED_PULL_AVAILABLE
heartbeat present + stale                 → PARTIAL (blocker: HEARTBEAT_STALE)
no heartbeat at all                       → PULL_NOT_BOOTSTRAPPED (blocker: NO_HEARTBEAT)
heartbeat present but worker missing      → MANUAL_REQUIRED
```

## Bridge Modes

The bridge always has `LOCAL_PULL_PRIMARY` as its primary mode.
Optional modes are appended dynamically:

- `SSH_PUSH_OPTIONAL` — added when SSH is confirmed reachable
- `MANUAL_FALLBACK` — always added as last resort

## Dispatch Rules

- `bridge_can_dispatch_by_pull()` — true when primary mode is LOCAL_PULL_PRIMARY
- `bridge_can_dispatch_by_push()` — true when SSH_PUSH_OPTIONAL is in optional_modes
- `bridge_requires_manual_bootstrap()` — true when status is PULL_NOT_BOOTSTRAPPED or MANUAL_REQUIRED

## Integration Points

- **Heartbeat module** — `heartbeat_is_stale()` determines if worker is alive
- **Queue paths** — VPS queue at `/opt/OS/data/work_queue/`, local at `~/eos_advisor_messages/`
- **Tmux surface** — attached to bridge for local command execution

## Key Design Constraint

The bridge evaluates status but does not initiate transport. The local
worker initiates pull. The VPS places packets in outbox and waits.
This is intentional — the VPS cannot reliably push to the local
environment due to sandbox classifier restrictions on SSH.

## Phase 96.8A.1 Terminology Alignment

- Bridge is an **Environment Adapter / bridge boundary** (not isolated infrastructure)
- Bridge connects and translates — it does **not** independently execute
- Local worker is a **worker runtime** (performs execution, does not decide)
- tmux is an **execution surface** (where commands run, not intelligence)
- Windows GUI / Chrome are **explicit environments** requiring adapter boundaries
- Work packets are **governed executable instructions** bound to execution contexts
- Mastery requirements must be declared for external interactions
- Proof artifact requirements must exist before execution

