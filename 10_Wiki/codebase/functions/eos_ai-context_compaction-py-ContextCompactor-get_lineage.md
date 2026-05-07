---
type: codebase-function
file: eos_ai/context_compaction.py
line: 191
generated: 2026-05-07
---

# ContextCompactor.get_lineage

**File:** [[eos_ai-context_compaction-py]] | **Line:** 191
**Signature:** `get_lineage(session_id) → list[dict]`

**Class:** [[eos_ai-context_compaction-py-ContextCompactor]]

Return all compaction records for a session in chronological order.
Allows inspection of the full conversation lineage.

## Calls

- [[eos_ai-db-py-get_conn]]
