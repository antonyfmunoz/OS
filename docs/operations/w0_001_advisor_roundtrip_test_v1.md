# W0-001 Advisor Roundtrip Test v1

**Phase**: 94D.6
**Status**: COMPLETE
**Date**: 2026-05-04

---

## Test Objective

End-to-end test of the advisor relay roundtrip:
VPS dispatches relay packet → local worker processes it →
worker emits approval request → VPS polls and surfaces it →
advisor responds → worker receives response.

## Current State

| Step | Status | Evidence |
|------|--------|----------|
| 1. VPS dispatches relay packet | DONE | Phase 94D.5 — 1424 bytes dispatched |
| 2. Local worker claims packet | DONE | `claimed_WO-LOCAL-PILOT-GDRIVE-GDOCS-001.json` in outbox |
| 3. Preflight passes | DONE | 8/8 checks passed |
| 4. GUI healthcheck runs | DONE | Display=available, GUI libs=missing |
| 5. Approval request emitted | DONE | `approval_request_WO-LOCAL-PILOT-GDRIVE-GDOCS-001.json` |
| 6. VPS polls and surfaces request | DONE | Read via SSH, displayed in VPS session |
| 7. Advisor responds | DONE | APPROVE piped via SSH stdin to inbox |
| 8. Worker processes response | DONE | status=approved, summary written, worker exited cleanly |

## How to Complete the Roundtrip

From VPS, write advisor response to local inbox:

```bash
ssh -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes -o BatchMode=yes \
  'DESKTOP-LVGUIQ9\antonys beast pc'@100.74.199.102 \
  'wsl -e bash -c "cat > ~/eos_advisor_messages/inbox/advisor_response.json << '\''EOF'\''
{
  \"message_type\": \"APPROVAL_RESPONSE\",
  \"work_order_id\": \"WO-LOCAL-PILOT-GDRIVE-GDOCS-001\",
  \"sender\": \"founder\",
  \"recipient\": \"advisor\",
  \"payload\": {
    \"approval_request_id\": \"apr_first_gate_1777925162\",
    \"decision\": \"APPROVE\",
    \"reason\": null
  }
}
EOF"'
```

## Expected Worker Behavior on APPROVE

Worker logs: "Worker APPROVED — but NOT proceeding (Phase 94D.6 stops here)"
Worker writes `loop_summary_WO-*.json` with status = "approved"
Worker exits. Google Drive is NOT opened.

## Verification Commands

```bash
# Check worker still running
ssh ... 'wsl -e bash -c "tmux list-sessions"'

# Check outbox files
ssh ... 'wsl -e bash -c "ls -la ~/eos_advisor_messages/outbox/"'

# Check if summary was written (after response)
ssh ... 'wsl -e bash -c "cat ~/eos_advisor_messages/outbox/loop_summary_WO-LOCAL-PILOT-GDRIVE-GDOCS-001.json"'
```
