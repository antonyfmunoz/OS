---
type: codebase-function
file: scripts/memory_neon.py
line: 188
generated: 2026-05-07
---

# search_memory_events

**File:** [[scripts-memory_neon-py]] | **Line:** 188
**Signature:** `search_memory_events(query, event_type, date_from, date_to, salience_label, limit) → list[dict]`

Search memory pipeline events with optional filters.

Args:
    query: Free-text search against payload_json (uses JSONB containment
           or text match on title/topics).
...

## Calls

- [[eos_ai-db-py-get_conn]]
