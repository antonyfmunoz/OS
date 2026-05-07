---
type: codebase-function
file: core/security/audit.py
line: 118
generated: 2026-05-07
---

# AuditLog.record

**File:** [[core-security-audit-py]] | **Line:** 118
**Signature:** `record() → AuditEvent`

**Class:** [[core-security-audit-py-AuditLog]]

Append a new event, chained to the previous tip.

## Calls

- [[core-security-audit-py-AuditEvent-as_dict]]
- [[core-security-audit-py-AuditLog-_tail_hash]]
- [[core-security-audit-py-_hash_row]]
- [[core-security-audit-py-_new_event_id]]

## Called By

- [[scripts-security_smoke_test-py-test_audit]]
