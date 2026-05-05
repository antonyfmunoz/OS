---
type: codebase-file
path: core/semantic_space.py
module: core.semantic_space
lines: 499
size: 16914
generated: 2026-04-12
---

# core/semantic_space.py

Semantic Space v1.2 — Query Projection, Region Search, Graph Expansion,
                      Wiki-Aware Enrichment

Public API:
    project_query(query, pca_model) -> (x, y, z, embedding)
...

**Lines:** 499 | **Size:** 16,914 bytes

## Contains

- **fn** [[core-semantic_space-py-_query_to_y]]`(query) → float`
- **fn** [[core-semantic_space-py-_query_to_z]]`(query) → float`
- **fn** [[core-semantic_space-py-_project_x]]`(embedding, pca_model) → float`
- **fn** [[core-semantic_space-py-_is_action_query]]`(query) → bool`
- **fn** [[core-semantic_space-py-_get_weight_overrides]]`(query) → dict[str, float]`
- **fn** [[core-semantic_space-py-_metadata_score]]`(coord, is_action) → float`
- **fn** [[core-semantic_space-py-cosine_sim]]`(vec_a, vec_b) → float`
- **fn** [[core-semantic_space-py-rerank_candidates]]`(candidates, query_embedding, embedding_store, is_action) → list[dict]`
- **fn** [[core-semantic_space-py-project_query]]`(query, pca_model) → tuple[float, float, float, np.ndarray]`
- **fn** [[core-semantic_space-py-region_search]]`(graph, qcoord, top_k, weights, query, embedding_store, query_embedding) → list[dict]`
- **fn** [[core-semantic_space-py-expand_with_graph]]`(graph, node_ids, hops) → dict`
- **fn** [[core-semantic_space-py-apply_wiki_layer]]`(candidates, graph, max_expansions) → list[dict]`
- **fn** [[core-semantic_space-py-load_pca_model]]`(path) → dict`
- **fn** [[core-semantic_space-py-load_embedding_store]]`(path) → dict[str, list[float]]`

## Import Statements

```python
import json
import math
import re
import sys
import numpy as np
```
