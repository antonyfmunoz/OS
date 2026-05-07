---
type: codebase-function
file: scripts/memory_neon.py
line: 548
generated: 2026-05-07
---

# ensure_indexes

**File:** [[scripts-memory_neon-py]] | **Line:** 548
**Signature:** `ensure_indexes() → None`

Create GIN index on events.payload_json if not exists.

Safe to call multiple times (idempotent via IF NOT EXISTS).
Run once during setup or migration.

## Calls

- [[eos_ai-db-py-get_conn]]
