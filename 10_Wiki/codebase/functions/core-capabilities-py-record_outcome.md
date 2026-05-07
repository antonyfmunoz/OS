---
type: codebase-function
file: core/capabilities.py
line: 254
generated: 2026-05-07
---

# record_outcome

**File:** [[core-capabilities-py]] | **Line:** 254
**Signature:** `record_outcome(capability_name) → None`

Record the outcome of an execution against a capability.

Updates the in-memory performance record and persists to disk.

## Calls

- [[core-capabilities-py-_persist_performance]]

## Called By

- [[core-router-py-execute_routed]]
