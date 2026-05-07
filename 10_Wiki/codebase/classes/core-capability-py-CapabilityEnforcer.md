---
type: codebase-class
file: core/capability.py
line: 206
generated: 2026-05-07
---

# CapabilityEnforcer

**File:** [[core-capability-py]] | **Line:** 206

Pure policy object. `may(...)` is the single answer-everything method.

The enforcer never mutates anything and never blocks. Its only job is
to return a Decision; the harness or action system acts on it.

## Methods

- [[core-capability-py-CapabilityEnforcer-may]]`(profile, kind, risk) → Decision` — 
- [[core-capability-py-CapabilityEnforcer-enforce]]`(profile, kind, risk) → Decision` — Raise PermissionError if denied, else return the Decision.
