---
type: codebase-function
file: core/semantic_space.py
line: 244
generated: 2026-04-12
---

# project_query

**File:** [[core-semantic_space-py]] | **Line:** 244
**Signature:** `project_query(query, pca_model) → tuple[float, float, float, np.ndarray]`

Project a user query into semantic coordinate space.

Returns (x, y, z, embedding) — the embedding is reusable for cosine
reranking so callers never need to embed the query a second time.

## Calls

- [[core-semantic_space-py-_project_x]]
- [[core-semantic_space-py-_query_to_y]]
- [[core-semantic_space-py-_query_to_z]]
