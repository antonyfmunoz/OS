---
type: codebase-function
file: core/wiki_navigation.py
line: 74
generated: 2026-05-07
---

# WikiIndex.build

**File:** [[core-wiki_navigation-py]] | **Line:** 74
**Signature:** `build(graph) → 'WikiIndex'`

**Class:** [[core-wiki_navigation-py-WikiIndex]]

Build the index. Cheap — file scan only, no embeddings.

## Calls

- [[core-wiki_navigation-py-WikiIndex-_compute_incoming_counts]]
- [[core-wiki_navigation-py-WikiIndex-_map_nodes_to_wiki]]
- [[core-wiki_navigation-py-WikiIndex-_scan_summaries]]
- [[core-wiki_navigation-py-WikiIndex-_scan_wiki_pages]]
