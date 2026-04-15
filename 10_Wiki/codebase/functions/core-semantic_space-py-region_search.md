---
type: codebase-function
file: core/semantic_space.py
line: 261
generated: 2026-04-12
---

# region_search

**File:** [[core-semantic_space-py]] | **Line:** 261
**Signature:** `region_search(graph, qcoord, top_k, weights, query, embedding_store, query_embedding) → list[dict]`

Dual-pool prefilter → cosine rerank → return top_k candidates.

v1 (no cosine): spatial prefilter only, ranked by proximity + metadata.
v1.1 (cosine):  union of PCA spatial pool + direct cosine pool, then
                final rerank by cosine-dominant scoring.
...

## Calls

- [[core-semantic_space-py-_get_weight_overrides]]
- [[core-semantic_space-py-_is_action_query]]
- [[core-semantic_space-py-cosine_sim]]
- [[core-semantic_space-py-rerank_candidates]]
