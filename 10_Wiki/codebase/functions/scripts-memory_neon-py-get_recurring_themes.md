---
type: codebase-function
file: scripts/memory_neon.py
line: 476
generated: 2026-05-07
---

# get_recurring_themes

**File:** [[scripts-memory_neon-py]] | **Line:** 476
**Signature:** `get_recurring_themes(window_days, min_occurrences, limit) → list[dict]`

Find topics/entities that recur across multiple memory events.

Queries memory_summary_created events and aggregates topics
to find the most frequently recurring themes.

...

## Calls

- [[eos_ai-db-py-get_conn]]
