---
type: codebase-function
file: core/coord_assignment.py
line: 270
generated: 2026-05-07
---

# compute_node_coord

**File:** [[core-coord_assignment-py]] | **Line:** 270
**Signature:** `compute_node_coord(node_id, node, pca_model, embedding, summaries, edge_stats) → dict`

Compute full semantic coordinate for a single node.

Returns:
    Dict with semantic_coord and semantic_meta.

## Calls

- [[core-coord_assignment-py-_compute_confidence]]
- [[core-coord_assignment-py-_compute_importance]]
- [[core-coord_assignment-py-_compute_risk]]
- [[core-coord_assignment-py-_compute_y]]
- [[core-coord_assignment-py-_compute_z]]
- [[core-coord_assignment-py-_project_x]]

## Called By

- [[core-coord_assignment-py-assign_semantic_coords]]
