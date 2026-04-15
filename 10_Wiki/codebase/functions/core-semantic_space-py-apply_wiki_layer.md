---
type: codebase-function
file: core/semantic_space.py
line: 412
generated: 2026-04-12
---

# apply_wiki_layer

**File:** [[core-semantic_space-py]] | **Line:** 412
**Signature:** `apply_wiki_layer(candidates, graph, max_expansions) → list[dict]`

Enrich candidates with wiki signal and apply bounded rerank bonus.

Steps:
    1. Build wiki index (cheap file scan, cached on WikiIndex instance)
    2. Enrich each candidate with wiki metadata
...
