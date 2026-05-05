---
type: codebase-function
file: scripts/query_graph.py
line: 175
generated: 2026-04-12
---

# GraphQuery.centrality

**File:** [[scripts-query_graph-py]] | **Line:** 175
**Signature:** `centrality(top) → list[tuple[str, int, int]]`

**Class:** [[scripts-query_graph-py-GraphQuery]]

Rank files by (imported_by + imports) — simple centrality proxy.

## Called By

- [[scripts-action_system-py-ActionSystem-_critical_hub_set]]
- [[scripts-action_system-py-ActionSystem-assess_impact]]
- [[scripts-query_graph-py-main]]
