# W0-001 Relaunch Test Plan v1

**Phase**: 94D.5 — Relay Wiring + GUI Healthcheck + W0-001 Relaunch
**Status**: READY
**Date**: 2026-05-04

---

## Test Objective

Relaunch W0-001 with corrected auto-mode relay behavior.
Stop at the first advisor approval gate. Do NOT open Google Drive
until founder explicitly approves through the VPS advisor session.

## Test Steps

### Step 1 — Send Corrected Relay Packet to Local Worker

From VPS, dispatch the W0-001 relay packet to local PC via bridge:

```python
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.substrate.local_worker_relay_packets import build_wo_001_relay_packet
from services.local_bridge_client import forward_to_local

packet = build_wo_001_relay_packet()
result = forward_to_local(packet.to_json(), 'umh_core')
print(f"Dispatch: {'OK' if result else 'FAILED'}")
```

### Step 2 — Local Worker Claims Packet

Expected: local worker reads packet from inbox, validates, claims.
Verification: check `~/eos_outbox/claimed_*.json` exists.

```bash
ssh ... 'wsl -e bash -c "ls ~/eos_outbox/claimed_*.json 2>/dev/null"'
```

### Step 3 — Local Worker Runs GUI Backend Healthcheck

Expected: worker runs healthcheck commands, writes report.
Verification: check `~/eos_outbox/healthcheck_*.json` exists.

### Step 4 — Local Worker Sends First Approval Request

Expected: worker writes approval request to `~/eos_outbox/`:

```json
{
  "message_type": "APPROVAL_NEEDED",
  "work_order_id": "WO-LOCAL-PILOT-GDRIVE-GDOCS-001",
  "payload": {
    "action": "OPEN_GOOGLE_DRIVE",
    "target": "antonyfm@empyreanstudios.co",
    "risk_level": "MEDIUM",
    "backend": "GUI_COMPUTER_USE",
    "blocked_until_approved": true
  }
}
```

### Step 5 — VPS Receives/Displays Approval Request

VPS polls local outbox via SSH:

```bash
ssh ... 'wsl -e bash -c "cat ~/eos_outbox/advisor_request_*.json 2>/dev/null"'
```

Display approval request to founder on VPS terminal.

### Step 6 — STOP

Do NOT proceed. Do NOT open Google Drive.
Wait for founder to explicitly approve via VPS.

## Success Criteria

| Criterion | Required |
|-----------|----------|
| Packet dispatched to local | YES |
| Local worker acknowledges | YES (or file-based claim) |
| GUI healthcheck runs | YES |
| First approval request reaches VPS | YES |
| Google Drive NOT opened | YES |
| Playwright NOT used | YES |
| No unsafe actions | YES |

## Current Reality

The local worker does not yet have an automated loop that reads relay
packets, runs healthchecks, and writes outbox files autonomously.
The packet is dispatched to the inbox. The local CC `umh_core` session
can read it. Full automation requires a local worker daemon — not in scope
for this phase.

For this test, the packet dispatch and first-gate-stop are the goals.
The local worker processing is manual or semi-manual through the
existing tmux session.
