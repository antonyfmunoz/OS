---
type: codebase-function
file: core/security/context.py
line: 214
generated: 2026-05-07
---

# SecurityContext.authorize_action

**File:** [[core-security-context-py]] | **Line:** 214
**Signature:** `authorize_action() → AuthorizationDecision`

**Class:** [[core-security-context-py-SecurityContext]]

Run the full authorization pipeline.

Steps
-----
1. Verify the token (or fail with "denied" + audit row).
...

## Calls

- [[core-capability-py-coerce_risk]]
- [[core-security-context-py-SecurityContext-_approve_and_audit]]
- [[core-security-context-py-SecurityContext-_deny_and_audit]]
- [[core-security-context-py-SecurityContext-_pending_and_audit]]
- [[core-security-context-py-SecurityContext-verify_token]]
- [[core-security-context-py-_chain_entry]]

## Called By

- [[scripts-security_smoke_test-py-test_security_context]]
