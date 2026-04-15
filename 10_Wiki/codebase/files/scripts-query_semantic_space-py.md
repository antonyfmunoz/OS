---
type: codebase-file
path: scripts/query_semantic_space.py
module: scripts.query_semantic_space
lines: 342
size: 11731
tags: [entry-point]
generated: 2026-04-12
---

# scripts/query_semantic_space.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Query the semantic space — inspect coordinates, run queries, explore regions.

Usage:
    python3 scripts/query_semantic_space.py query "how does memory work"
    python3 scripts/query_semantic_space.py query "what breaks if I change memory" --show-scores
...

**Lines:** 342 | **Size:** 11,731 bytes

## Contains

- **fn** [[scripts-query_semantic_space-py-_load_graph]]`(path) → dict`
- **fn** [[scripts-query_semantic_space-py-_load_pca]]`(path) → dict`
- **fn** [[scripts-query_semantic_space-py-_check_semantic_space]]`(graph) → bool`
- **fn** [[scripts-query_semantic_space-py-_find_node]]`(graph, identifier) → tuple[str, dict, str] | None`
- **fn** [[scripts-query_semantic_space-py-_load_embedding_store]]`(graph) → dict[str, list[float]] | None`
- **fn** [[scripts-query_semantic_space-py-cmd_query]]`(args) → None`
- **fn** [[scripts-query_semantic_space-py-_print_results]]`(results, top_k, show_scores, show_wiki) → None`
- **fn** [[scripts-query_semantic_space-py-cmd_coord]]`(args) → None`
- **fn** [[scripts-query_semantic_space-py-cmd_neighbors]]`(args) → None`
- **fn** [[scripts-query_semantic_space-py-cmd_region]]`(args) → None`
- **fn** [[scripts-query_semantic_space-py-main]]`() → None`

## Import Statements

```python
import argparse
import json
import os
import sys
```
