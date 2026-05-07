---
type: codebase-function
file: core/coord_assignment.py
line: 302
generated: 2026-05-07
---

# assign_semantic_coords

**File:** [[core-coord_assignment-py]] | **Line:** 302
**Signature:** `assign_semantic_coords(graph) → dict`

Assign semantic coordinates to all nodes in the graph.

Writes PCA model and embedding store to data/semantic_space/.
Modifies graph in-place and returns it.

## Calls

- [[core-coord_assignment-py-_assemble_text]]
- [[core-coord_assignment-py-_build_pca_model]]
- [[core-coord_assignment-py-_compute_edge_stats]]
- [[core-coord_assignment-py-_load_summaries]]
- [[core-coord_assignment-py-_write_json]]
- [[core-coord_assignment-py-compute_node_coord]]
