# Local Worker Auto-Loop Daemon v1

**Phase**: 94D.6
**Status**: RUNNING
**Date**: 2026-05-04

---

## Purpose

Minimal auto-loop daemon that runs on the local PC (WSL) inside a tmux
session. Reads relay packets dispatched from the VPS advisor, claims
work orders, runs safe preflight and GUI backend healthchecks, emits
status messages to the outbox, sends the first approval request, and
polls the inbox for advisor response.

## Location

- **VPS source**: `eos_ai/substrate/local_worker_auto_loop.py`
- **Local deployed**: `~/umh_local_worker/local_worker_auto_loop.py`
- **Tmux session**: `umh_worker_loop`

## Architecture

```
Relay Packet (JSON)
    │
    ▼
┌─────────────────────────────────┐
│ local_worker_auto_loop.py       │
│                                 │
│ 1. Load packet from file        │
│ 2. Validate against WO-001      │
│ 3. Claim → write to outbox      │
│ 4. Preflight (8 checks)         │
│ 5. GUI healthcheck (subprocess) │
│ 6. Approval request → outbox    │
│ 7. Poll inbox for response      │
└─────────────────────────────────┘
    │                    ▲
    ▼                    │
~/eos_advisor_messages/  ~/eos_advisor_messages/
    outbox/                  inbox/
```

## Dependencies

None beyond Python stdlib. No `/opt/OS` imports. No pip packages.
Runs on any Python 3.8+ installation.

## Directories

| Path | Purpose |
|------|---------|
| `~/eos_advisor_messages/outbox/` | Worker writes status + approval requests |
| `~/eos_advisor_messages/inbox/` | Worker reads advisor responses |
| `~/eos_advisor_messages/` | Parent dir, relay packets stored here |
| `~/umh_local_worker/` | Deployed worker scripts |

## CLI Usage

```bash
python3 ~/umh_local_worker/local_worker_auto_loop.py ~/eos_advisor_messages/wo_001_relay_packet.json
```

## Tmux Launch

```bash
tmux new-session -d -s umh_worker_loop \
  "python3 ~/umh_local_worker/local_worker_auto_loop.py ~/eos_advisor_messages/wo_001_relay_packet.json"
```

## Outbox Messages Produced

| File | Message Type | When |
|------|-------------|------|
| `claimed_WO-*.json` | WORK_ORDER_CLAIMED | After validation passes |
| `preflight_WO-*.json` | PREFLIGHT_STATUS | After 8 preflight checks |
| `backend_health_WO-*.json` | BACKEND_HEALTH | After GUI healthcheck |
| `approval_request_WO-*.json` | APPROVAL_NEEDED | Before polling starts |
| `loop_summary_WO-*.json` | Summary | After loop terminates |

## Polling Behavior

Worker polls `~/eos_advisor_messages/inbox/` every 5 seconds for JSON
files matching the work order ID. Logs elapsed time every 60 seconds.

## Termination Conditions

| Advisor Decision | Worker Action |
|-----------------|---------------|
| APPROVE | Status = approved, loop exits, does NOT open Google Drive |
| DENY | Status = stopped, loop exits |
| STOP | Status = stopped, loop exits |
| (none) | Continues polling indefinitely |

## Safety Constraints

- No computer use
- No Google Drive
- No Playwright
- No Gmail
- No APIs
- Only reads files, writes files, runs safe import checks
