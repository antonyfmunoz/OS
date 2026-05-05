---
type: codebase-function
file: core/security/approval.py
line: 328
generated: 2026-04-12
---

# ApprovalQueue.wait_for_decision

**File:** [[core-security-approval-py]] | **Line:** 328
**Signature:** `wait_for_decision(request_id) → ApprovalRequest | None`

**Class:** [[core-security-approval-py-ApprovalQueue]]

Block until the request is decided or `timeout` elapses.

`timeout=0` → return immediately (non-blocking check).
Returns None on timeout. Returns the request on any terminal state.

## Calls

- [[core-security-approval-py-ApprovalQueue-_append]]
- [[core-security-approval-py-ApprovalQueue-_is_expired]]
- [[core-security-approval-py-ApprovalQueue-_write_state]]
- [[core-security-approval-py-ApprovalQueue-get]]
- [[core-security-approval-py-ApprovalRequest-as_dict]]
