---
type: codebase-function
file: core/security/approval.py
line: 200
generated: 2026-04-12
---

# ApprovalQueue.approve

**File:** [[core-security-approval-py]] | **Line:** 200
**Signature:** `approve(request_id) → ApprovalRequest`

**Class:** [[core-security-approval-py-ApprovalQueue]]

Flip a pending request to APPROVED.

Caller must supply `can_approve_risk` — the SecurityContext
computes this from RBAC. The queue itself does not know about
roles; it just enforces self-approval rules and terminal state.

## Calls

- [[core-security-approval-py-ApprovalQueue-_decide]]

## Called By

- [[core-security-cli-py-cmd_approval_approve]]
- [[scripts-security_smoke_test-py-test_approval_queue]]
- [[scripts-security_smoke_test-py-test_security_context]]
