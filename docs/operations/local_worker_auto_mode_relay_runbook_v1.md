# Local Worker Auto-Mode Relay Runbook v1

**Phase**: 94D.5 — Relay Wiring + GUI Healthcheck + W0-001 Relaunch
**Status**: READY
**Date**: 2026-05-04

---

## Purpose

Exact behavior the local worker must follow when executing W0-001
in AUTO mode with advisor-gated relay.

## Step-by-Step Execution

### 1. Load Work Order

Worker reads relay packet from `~/eos_inbox/` or `~/eos_advisor_messages/`.
Packet contains: work_order_id, worker_mode, approval_routing, blocked_actions,
target_account, preferred_backend, etc.

### 2. Report CLAIMED Status to Advisor

Worker writes to `~/eos_outbox/claimed_{work_order_id}.json`:
```json
{
  "message_type": "WORK_ORDER_CLAIMED",
  "work_order_id": "WO-LOCAL-PILOT-GDRIVE-GDOCS-001",
  "sender": "node:local_pc_worker",
  "recipient": "advisor",
  "payload": {
    "worker_mode": "auto",
    "preferred_backend": "GUI_COMPUTER_USE"
  }
}
```

### 3. Run GUI Backend Healthcheck

Execute healthcheck commands from `gui_backend_healthcheck.py`:
- Check visible display
- Check pyautogui
- Check Anthropic SDK
- Check Windows UI automation

If GUI backend unavailable:
- Write `GUI_BACKEND_DECISION` approval request to outbox
- STOP. Wait for advisor response.

### 4. Emit First Approval Request

Write to `~/eos_outbox/advisor_request_{work_order_id}.json`:
```json
{
  "message_type": "APPROVAL_NEEDED",
  "work_order_id": "WO-LOCAL-PILOT-GDRIVE-GDOCS-001",
  "payload": {
    "action": "OPEN_GOOGLE_DRIVE",
    "target": "antonyfm@empyreanstudios.co",
    "description": "Approve opening Google Drive for antonyfm@empyreanstudios.co using visible GUI computer-use?",
    "risk_level": "MEDIUM",
    "backend": "GUI_COMPUTER_USE",
    "blocked_until_approved": true
  }
}
```

### 5. Wait for Advisor Response from VPS

Worker polls `~/eos_advisor_messages/` or `~/eos_inbox/` for response file.
VPS writes response via SSH or bridge.

### 6. If Approved: Proceed Only with Opening Drive

- Open Google Drive ONLY
- Verify active account matches `antonyfm@empyreanstudios.co`
- If wrong account → STOP, send ERROR to advisor
- Do NOT open any documents without separate approval

### 7. If Denied/Paused/Stopped: Obey

- DENY → Block worker, record reason, write status to outbox
- PAUSE → Freeze worker, wait for RESUME
- STOP → Terminate worker (FAILED), write final status

### 8. Report Status Back

Write result to `~/eos_outbox/status_{work_order_id}.json`.

## What the Worker Does NOT Do

- Does NOT prompt for approval in local terminal (unless manual fallback selected)
- Does NOT open Gmail
- Does NOT switch Google accounts
- Does NOT open documents without per-document approval
- Does NOT use Playwright
- Does NOT edit/delete/move/share files
- Does NOT capture credentials
- Does NOT promote memory

## Relay Unavailable Behavior

If advisor relay is unavailable (SSH down, bridge down, no response within timeout):
- Worker writes to outbox anyway (file persists)
- Worker does NOT fall back to local terminal approval automatically
- Worker STOPS at first gate and waits
- Manual intervention: founder SSHs into local PC and reads outbox

## File

`eos_ai/substrate/local_worker_relay_packets.py`
