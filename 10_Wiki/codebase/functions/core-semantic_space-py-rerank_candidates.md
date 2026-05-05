---
type: codebase-function
file: core/semantic_space.py
line: 192
generated: 2026-04-12
---

# rerank_candidates

**File:** [[core-semantic_space-py]] | **Line:** 192
**Signature:** `rerank_candidates(candidates, query_embedding, embedding_store, is_action) → list[dict]`

Rerank spatial candidates.

v1.1 (cosine available):
    score = 0.20 * proximity + 0.65 * cosine_sim + 0.15 * metadata
    Cosine dominates — PCA proximity is a coarse prefilter, not a ranking signal.
...

## Calls

- [[core-semantic_space-py-_metadata_score]]
- [[core-semantic_space-py-cosine_sim]]

## Called By

- [[core-semantic_space-py-region_search]]
