# Local Worker Message Loop v1

**Date**: 2026-05-04
**Phase**: 94D.3 — Central Advisor Session + Interface-Agnostic Communication Bus Correction v1

---

## 1. Problem Being Corrected

In Phase 94D, the work order was dispatched to the local PC. The local Claude Code session received it and:

1. Asked for approval in the local terminal only
2. Used Playwright/Chromium automation instead of visible GUI computer use

Both are wrong:
- Approval in the local terminal means the founder must be typing locally. This defeats the purpose of remote dispatch.
- Playwright automation is invisible. The founder cannot watch what's happening. The pilot should be observable.

---

## 2. Corrected Local Worker Behavior

The local worker MUST route all communication through the message bus to the central advisor session. It must NEVER require local terminal interaction for approvals (unless manually selected as fallback).

### Execution Loop

```
1. CLAIM
   Worker receives work order
   → Sends WORK_ORDER_CLAIMED to advisor session
   → Includes execution_backend (GUI_COMPUTER_USE, BROWSER_AUTOMATION, etc.)
   → Waits for advisor acknowledgement

2. STATUS
   Worker sends WORK_ORDER_STATUS to advisor session
   → Current phase, progress, what's happening

3. APPROVAL REQUEST
   Worker encounters action requiring approval
   → Sends APPROVAL_NEEDED to advisor session via message bus
   → Message includes: action, target, context, risk_level
   → Worker PAUSES execution
   → Worker does NOT prompt in local terminal

4. WAIT FOR APPROVAL
   Worker waits for APPROVAL_RESPONSE from advisor session
   → Response arrives via message bus (HTTP POST from VPS or bridge)
   → Decision: APPROVE → continue | DENY → skip | MODIFY → adjust | DEFER → pause

5. EXECUTE APPROVED ACTION
   Worker performs only the approved action
   → Using the approved backend (GUI computer use, not Playwright)
   → Captures evidence if required

6. REPORT RESULT
   Worker sends RESULT or EVIDENCE_AVAILABLE to advisor session
   → Includes what was found, evidence path, summary

7. REPEAT (3-6) for each action requiring approval

8. PAUSE ON SAFETY ISSUES
   If worker encounters:
   → Wrong Google account → sends ERROR with URGENT priority
   → Credentials/secrets → sends POLICY_BLOCK
   → Unexpected content → sends RISK_WARNING
   Worker PAUSES immediately. Does not continue without explicit RESUME.

9. COMPLETION
   Worker sends COMPLETION_REPORT to advisor session
   → Includes safety attestation, approval log, results
```

---

## 3. Message Bus Integration

### How the local worker sends messages to the advisor session

```
Local worker
  → Constructs MessageEnvelope with:
      sender: "node:local_pc_worker"
      target: "advisor"
      message_type: APPROVAL_NEEDED (or STATUS, RESULT, etc.)
  → Posts to VPS via:
      PRIMARY:  HTTP POST to http://100.77.233.50:8765/message-bus
      FALLBACK: HTTP POST to http://100.77.233.50:8765/cc-reply (existing)
      FALLBACK: Write to station bus outbox (file-based)
```

### How the local worker receives messages from the advisor session

```
Advisor session
  → Constructs MessageEnvelope with:
      sender: "advisor"
      target: "node:local_pc_worker"
      message_type: APPROVAL_RESPONSE (or COMMAND, STOP, etc.)
  → Delivers via:
      PRIMARY:  HTTP POST to http://100.74.199.102:8766/message-bus
      FALLBACK: forward_to_local() via /message endpoint
      FALLBACK: SSH → tmux send-keys
      FALLBACK: Station bus outbox (file-based)
```

---

## 4. Local Worker Does NOT

| Action | Why |
|--------|-----|
| Prompt for approval in local terminal | Founder may not be at local terminal |
| Assume CLI is the only interface | Founder may be on phone, Discord, voice |
| Block waiting for local keyboard input | Deadlocks if founder is remote |
| Use Playwright/Chromium as default | Pilot requires visible GUI computer use |
| Continue without approval response | Must wait for bus message |
| Retry approval locally after timeout | Escalate to advisor session instead |

---

## 5. Manual Local Fallback

The local terminal CAN be used for approvals, but ONLY when:

1. Message bus is confirmed down (VPS unreachable, bridge dead, SSH dead)
2. Founder explicitly selects manual local control via a MODIFY_CONSTRAINTS message
3. The action is low-risk / read-only
4. The manual action is logged as MANUAL_FALLBACK in the audit trail

### Fallback detection

```
Worker attempts to send APPROVAL_NEEDED to advisor via:
  1. HTTP POST to VPS → fails
  2. Bridge reverse path → fails
  3. Station bus write → no acknowledgement within 60s
  → Worker logs: "Message bus unreachable — switching to local fallback"
  → Worker prompts locally: "Bus unreachable. Approve locally? [y/n]"
  → All local approvals tagged audit_tags: ["manual_fallback"]
```

---

## 6. Local Worker State Machine

```
IDLE
  → receives work order → CLAIMING

CLAIMING
  → sends WORK_ORDER_CLAIMED → EXECUTING

EXECUTING
  → encounters approval gate → WAITING_FOR_APPROVAL
  → encounters error → ERROR_PAUSED
  → completes all actions → COMPLETING

WAITING_FOR_APPROVAL
  → receives APPROVE → EXECUTING
  → receives DENY → EXECUTING (skip action)
  → receives MODIFY → EXECUTING (adjusted action)
  → receives STOP → STOPPED
  → bus timeout → LOCAL_FALLBACK_PROMPT

ERROR_PAUSED
  → receives RESUME → EXECUTING
  → receives STOP → STOPPED
  → receives MODIFY_CONSTRAINTS → EXECUTING (adjusted)

LOCAL_FALLBACK_PROMPT
  → local approval given → EXECUTING
  → local denial → EXECUTING (skip)
  → bus reconnects → WAITING_FOR_APPROVAL (re-route to bus)

COMPLETING
  → sends COMPLETION_REPORT → DONE

STOPPED
  → (terminal)

DONE
  → (terminal)
```

---

## 7. Approval Message Format (Node → Advisor)

```json
{
  "message_id": "msg_abc123",
  "session_id": "sess_main",
  "source_interface": "node",
  "target": "advisor",
  "sender": "node:local_pc_worker",
  "recipient": "founder",
  "message_type": "APPROVAL_NEEDED",
  "payload": {
    "approval_request_id": "apr_xyz789",
    "work_order_id": "WO-LOCAL-PILOT-GDRIVE-GDOCS-001",
    "node_id": "local_pc_worker",
    "action": "open_folder",
    "target": "Coaching Frameworks",
    "context": "Phase 1 Discovery — inventorying Google Drive folders",
    "risk_level": "LOW",
    "blocked_until_approved": true
  },
  "priority": "HIGH",
  "requires_response": true,
  "approval_required": true,
  "timestamp": "2026-05-04T18:00:00Z",
  "work_order_id": "WO-LOCAL-PILOT-GDRIVE-GDOCS-001",
  "node_id": "local_pc_worker",
  "status": "PENDING"
}
```

---

## 8. Approval Response Format (Advisor → Node)

```json
{
  "message_id": "msg_def456",
  "session_id": "sess_main",
  "source_interface": "cli_vps_main",
  "target": "node:local_pc_worker",
  "sender": "founder",
  "recipient": "node:local_pc_worker",
  "message_type": "APPROVAL_RESPONSE",
  "payload": {
    "approval_request_id": "apr_xyz789",
    "decision": "APPROVE",
    "modifications": null,
    "reason": null
  },
  "priority": "HIGH",
  "requires_response": false,
  "timestamp": "2026-05-04T18:00:15Z",
  "correlation_id": "msg_abc123",
  "work_order_id": "WO-LOCAL-PILOT-GDRIVE-GDOCS-001",
  "node_id": "local_pc_worker",
  "status": "DELIVERED"
}
```
