---
type: codebase-file
path: core/coord_assignment.py
module: core.coord_assignment
lines: 405
size: 12996
generated: 2026-04-12
---

# core/coord_assignment.py

Semantic Space v1.1 — Coordinate Assignment

Assigns each graph node a 3D semantic coordinate:
  x = semantic position (PCA-1D of embedding)
  y = abstraction level (deterministic table)
...

**Lines:** 405 | **Size:** 12,996 bytes

## Contains

- **fn** [[core-coord_assignment-py-_summary_key]]`(node_id, node) → str`
- **fn** [[core-coord_assignment-py-_infer_node_type]]`(node_id, node) → str`
- **fn** [[core-coord_assignment-py-_compute_y]]`(node_id, node) → float`
- **fn** [[core-coord_assignment-py-_compute_z]]`(node_id, node) → float`
- **fn** [[core-coord_assignment-py-_recency_score]]`(node) → float`
- **fn** [[core-coord_assignment-py-_instability_score]]`(node) → float`
- **fn** [[core-coord_assignment-py-_compute_importance]]`(node_id, node, edge_stats) → float`
- **fn** [[core-coord_assignment-py-_compute_confidence]]`(node_id, node, summaries) → float`
- **fn** [[core-coord_assignment-py-_compute_risk]]`(node) → float`
- **fn** [[core-coord_assignment-py-_assemble_text]]`(node_id, node, summaries) → str`
- **fn** [[core-coord_assignment-py-_build_pca_model]]`(embeddings) → dict`
- **fn** [[core-coord_assignment-py-_project_x]]`(embedding, pca_model) → float`
- **fn** [[core-coord_assignment-py-compute_node_coord]]`(node_id, node, pca_model, embedding, summaries, edge_stats) → dict`
- **fn** [[core-coord_assignment-py-assign_semantic_coords]]`(graph) → dict`
- **fn** [[core-coord_assignment-py-_load_summaries]]`() → dict`
- **fn** [[core-coord_assignment-py-_compute_edge_stats]]`(graph) → dict[str, dict[str, int]]`
- **fn** [[core-coord_assignment-py-_write_json]]`(path, data, indent, sort_keys) → None`

## Import Statements

```python
import json
import os
import sys
import time
from datetime import datetime
from datetime import timezone
from pathlib import Path
import numpy as np
```
