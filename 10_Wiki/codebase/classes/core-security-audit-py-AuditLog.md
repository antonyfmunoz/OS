---
type: codebase-class
file: core/security/audit.py
line: 102
generated: 2026-04-12
---

# AuditLog

**File:** [[core-security-audit-py]] | **Line:** 102

Append-only hash-chained log.

Single-writer semantics are expected. Multiple writers still produce
a valid chain as long as the append is atomic (POSIX `write(2)` on
a JSONL line is), but readers may see interleaved events. The chain
...

## Methods

- [[core-security-audit-py-AuditLog-__init__]]`() → None` — 
- [[core-security-audit-py-AuditLog-record]]`() → AuditEvent` — Append a new event, chained to the previous tip.
- [[core-security-audit-py-AuditLog-read_all]]`() → list[AuditEvent]` — 
- [[core-security-audit-py-AuditLog-tail]]`(n) → list[AuditEvent]` — 
- [[core-security-audit-py-AuditLog-search]]`() → list[AuditEvent]` — 
- [[core-security-audit-py-AuditLog-verify_chain]]`() → tuple[bool, str]` — Walk the chain and verify every row.
- [[core-security-audit-py-AuditLog-_tail_hash]]`() → str` — 
- [[core-security-audit-py-AuditLog-_iter_events]]`() → Iterable[AuditEvent]` — 
