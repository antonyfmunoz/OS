---
type: codebase-function
file: scripts/memory_neon.py
line: 274
generated: 2026-04-12
---

# search_summaries

**File:** [[scripts-memory_neon-py]] | **Line:** 274
**Signature:** `search_summaries(query, topic, salience_label, date_from, date_to, promoted, limit) → list[dict]`

Search summary events in Neon with salience-aware ranking.

Results are ordered by salience_score descending, then recency.

Args:
...

## Calls

- [[eos_ai-db-py-get_conn]]
- [[scripts-memory_neon-py-_get_promoted_summary_slugs]]
- [[scripts-memory_neon-py-_path_to_slug]]
