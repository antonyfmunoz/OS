---
type: codebase-function
file: core/security/audit.py
line: 190
generated: 2026-04-12
---

# AuditLog.verify_chain

**File:** [[core-security-audit-py]] | **Line:** 190
**Signature:** `verify_chain() → tuple[bool, str]`

**Class:** [[core-security-audit-py-AuditLog]]

Walk the chain and verify every row.

Returns (ok, detail). On success detail is "N events, chain ok".
On failure detail points at the first broken row.

## Calls

- [[core-security-audit-py-AuditEvent-as_dict]]
- [[core-security-audit-py-AuditLog-_iter_events]]
- [[core-security-audit-py-_hash_row]]

## Called By

- [[core-security-cli-py-cmd_audit_verify]]
- [[scripts-security_smoke_test-py-test_audit]]
- [[scripts-security_smoke_test-py-test_security_context]]
