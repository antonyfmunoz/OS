---
type: codebase-function
file: scripts/vault_backlink_audit.py
line: 179
generated: 2026-04-12
---

# run_retrieval_signals

**File:** [[scripts-vault_backlink_audit-py]] | **Line:** 179
**Signature:** `run_retrieval_signals(wiki_slugs, incoming, outgoing) → None`

Report retrieval-quality signals for the wiki-graph bridge.

Requires the graph to be present. Reports:
- Dead-end wiki pages (inbound but no useful outbound)
- Graph nodes with promoted wiki pages but no inbound wiki references
...

## Called By

- [[scripts-vault_backlink_audit-py-run_health_check]]
