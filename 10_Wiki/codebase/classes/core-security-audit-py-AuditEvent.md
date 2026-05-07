---
type: codebase-class
file: core/security/audit.py
line: 50
generated: 2026-05-07
---

# AuditEvent

**File:** [[core-security-audit-py]] | **Line:** 50

One row in the audit chain.

The `hash` and `prev_hash` are populated by AuditLog on write.
Callers never set them directly.

## Methods

- [[core-security-audit-py-AuditEvent-as_dict]]`() → dict` — 
- [[core-security-audit-py-AuditEvent-from_dict]]`(d) → 'AuditEvent'` — 

## Decorators

- `@dataclass`
