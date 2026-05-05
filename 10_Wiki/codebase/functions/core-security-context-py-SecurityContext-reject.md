---
type: codebase-function
file: core/security/context.py
line: 433
generated: 2026-04-12
---

# SecurityContext.reject

**File:** [[core-security-context-py]] | **Line:** 433
**Signature:** `reject() → ApprovalRequest`

**Class:** [[core-security-context-py-SecurityContext]]

Reject a pending request. Any authenticated user may reject.

## Calls

- [[core-security-context-py-SecurityContext-verify_token]]
- [[core-security-context-py-_chain_entry]]

## Called By

- [[core-security-cli-py-cmd_approval_reject]]
- [[scripts-security_smoke_test-py-test_approval_queue]]
