---
type: codebase-function
file: core/security/context.py
line: 376
generated: 2026-04-12
---

# SecurityContext.approve

**File:** [[core-security-context-py]] | **Line:** 376
**Signature:** `approve() → ApprovalRequest`

**Class:** [[core-security-context-py-SecurityContext]]

Approve a pending request. Operator calls this.

The approver's role must have authority over the request's risk.
Writes an audit row on success.

## Calls

- [[core-security-context-py-SecurityContext-verify_token]]
- [[core-security-context-py-_chain_entry]]

## Called By

- [[core-security-cli-py-cmd_approval_approve]]
- [[scripts-security_smoke_test-py-test_approval_queue]]
- [[scripts-security_smoke_test-py-test_security_context]]
