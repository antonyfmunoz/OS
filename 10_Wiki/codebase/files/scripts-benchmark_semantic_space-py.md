---
type: codebase-file
path: scripts/benchmark_semantic_space.py
module: scripts.benchmark_semantic_space
lines: 428
size: 14077
tags: [entry-point]
generated: 2026-05-07
---

# scripts/benchmark_semantic_space.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Benchmark semantic space prefilter vs baseline graph retrieval.

Compares three paths:
  1. Baseline — substring search + 1-hop graph expansion
  2. v1      — PCA spatial prefilter + proximity rerank + graph expansion
...

**Lines:** 428 | **Size:** 14,077 bytes

## Contains

- **fn** [[scripts-benchmark_semantic_space-py-_baseline_retrieve]]`(graph, scenario) → dict`
- **fn** [[scripts-benchmark_semantic_space-py-_semantic_retrieve]]`(graph, pca_model, scenario, embedding_store) → dict`
- **fn** [[scripts-benchmark_semantic_space-py-_compare]]`(baseline, variant, known_relevant) → dict`
- **fn** [[scripts-benchmark_semantic_space-py-run_scenario]]`(graph, pca_model, embedding_store, name, scenario, verbose) → dict`
- **fn** [[scripts-benchmark_semantic_space-py-_print_variant]]`(label, data, cmp) → None`
- **fn** [[scripts-benchmark_semantic_space-py-_recommendation]]`(results) → str`
- **fn** [[scripts-benchmark_semantic_space-py-_build_edge_index]]`(graph) → tuple[dict, dict]`
- **fn** [[scripts-benchmark_semantic_space-py-_expand_1hop]]`(seeds, out_edges, in_edges) → set[str]`
- **fn** [[scripts-benchmark_semantic_space-py-_result_dict]]`(method, candidates, expanded, elapsed) → dict`
- **fn** [[scripts-benchmark_semantic_space-py-main]]`() → None`

## Import Statements

```python
import argparse
import json
import os
import sys
import time
from datetime import datetime
from datetime import timezone
```
