---
type: codebase-function
file: core/security/approval.py
line: 226
generated: 2026-04-12
---

# ApprovalQueue.reject

**File:** [[core-security-approval-py]] | **Line:** 226
**Signature:** `reject(request_id) → ApprovalRequest`

**Class:** [[core-security-approval-py-ApprovalQueue]]

Flip a pending request to REJECTED. Any role can reject a
request that has authority — or more strictly, any role can
reject a request made against them. We allow rejection broadly
because rejecting is never destructive.

## Calls

- [[core-security-approval-py-ApprovalQueue-_decide]]

## Called By

- [[core-security-cli-py-cmd_approval_reject]]
- [[scripts-security_smoke_test-py-test_approval_queue]]
