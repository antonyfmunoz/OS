# Environment Bridge Doctrine v1

**Phase:** 96.8A / 96.8A.1
**Status:** Active
**Layer:** UMH Substrate — Environment Adapter

## Adapter Boundary Classification

The Environment Bridge is an **Environment Adapter** inside the Adapter
Engine. It exists because the UMH External Boundary Law requires that
all environment transitions pass through governed adapter boundaries.
Work packets are governed external interaction contracts. Local worker
execution crosses the UMH external boundary. All local GUI, Chrome,
tmux, and shell interactions require environment adapters.

See: `docs/operations/umh_external_boundary_law_v1.md`
See: `docs/operations/environment_adapters_doctrine_v1.md`

## Purpose

The Environment Bridge is the durable transport and governance layer
between the VPS orchestrator (Linux, always-on) and local execution
environments (Windows desktop, WSL, tmux). It replaces ad-hoc SSH push
with a pull-based, packet-governed architecture.

## Core Principle

**No packet executes without explicit approval.**

Every work unit is a WorkPacket with approval_status, risk_level,
blocked_actions, and proof_requirements. The system NEVER auto-executes
unapproved packets, and NEVER auto-applies founder confirmation.

## Architecture

```
VPS Orchestrator
  └─ writes WorkPacket → /opt/OS/data/work_queue/outbox/
  └─ reads results   ← /opt/OS/data/work_queue/results/
  └─ reads heartbeat ← /opt/OS/data/work_queue/heartbeats/

Local Worker (WSL/tmux)
  └─ polls VPS outbox → copies to ~/eos_advisor_messages/inbox/
  └─ claims + validates packet
  └─ executes locally (GUI, browser, tmux)
  └─ writes results → ~/eos_advisor_messages/results/
  └─ syncs results back to VPS
  └─ writes heartbeat → ~/eos_advisor_messages/heartbeats/
```

## Modules

| Module | Responsibility |
|--------|---------------|
| `work_packet.py` | Packet contract — status, risk, approval, blocked actions |
| `queue_paths.py` | Canonical filesystem paths for VPS and local queues |
| `packet_validator.py` | Pre-execution validation and CU governance enforcement |
| `local_pull_protocol.py` | Pull-based packet lifecycle — discover, copy, claim, execute, result |
| `result_ingestion.py` | Result validation — proof, governance, confirmation gates |
| `heartbeat.py` | Worker liveness via file-based heartbeat with staleness detection |
| `tmux_surface.py` | Tmux command safety — dangerous command blocking |
| `vps_local_bridge.py` | Bridge orchestrator — mode selection and status evaluation |
| `bootstrap_plan.py` | One-time local worker setup plan generation |

## Bridge Modes

| Mode | Role |
|------|------|
| `LOCAL_PULL_PRIMARY` | **Default.** Local worker polls VPS outbox. |
| `SSH_PUSH_OPTIONAL` | Optional. VPS pushes via SSH when reachable. |
| `MANUAL_FALLBACK` | Always available. Founder copies packets manually. |
| `SHARED_FOLDER` | Future. Shared filesystem between VPS and local. |
| `DISABLED` | Bridge inactive. |

## Governance

All packets targeting `local_windows_gui` or `local_browser` must
include all 17 CU_REQUIRED_BLOCKED_ACTIONS in their `blocked_actions`:

credential_capture, token_capture, cookie_capture, account_switching,
gmail, edit, delete, move, share, permission_change, export, download,
screenshot, ocr, playwright, cdp, memory_promotion.

Missing any one blocks the packet from executing.

## Design Decisions

1. **Pull over push.** SSH push is blocked by sandbox classifiers on
   the VPS. Pull is reliable because the local worker initiates.
2. **File-based transport.** JSON files on filesystem. No database
   required for the transport layer. Simple, auditable, git-friendly.
3. **Heartbeat for liveness.** Worker writes a JSON heartbeat file
   every cycle. VPS reads it to determine online/stale/offline.
4. **Tmux as execution surface.** Tmux provides persistent sessions
   that survive SSH disconnects. Dangerous commands blocked at model layer.
5. **Founder confirmation never auto-applied.** System can flag that
   confirmation is required but never sets it to confirmed without
   explicit founder input.
