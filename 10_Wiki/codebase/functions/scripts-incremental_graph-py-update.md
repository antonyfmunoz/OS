---
type: codebase-function
file: scripts/incremental_graph.py
line: 573
generated: 2026-04-11
---

# update

**File:** [[scripts-incremental_graph-py]] | **Line:** 573
**Signature:** `update(changed_paths) → dict[str, Any]`

Update the graph incrementally for the given changed paths.

mode:
    "auto"        — incremental if safe, else full rebuild
    "incremental" — force incremental (may still fall back on error)
...

## Calls

- [[scripts-codebase_graph-py-_rel]]
- [[scripts-incremental_graph-py-_compute_dirty_set]]
- [[scripts-incremental_graph-py-_is_tracked]]
- [[scripts-incremental_graph-py-_load_graph]]
- [[scripts-incremental_graph-py-_recompute_edges_for_dirty]]
- [[scripts-incremental_graph-py-_recompute_stats]]
- [[scripts-incremental_graph-py-_rel]]
- [[scripts-incremental_graph-py-_run_full_rebuild]]
- [[scripts-incremental_graph-py-_save_graph]]
- [[scripts-incremental_graph-py-_scan_non_python_file]]
- [[scripts-incremental_graph-py-_scan_python_files]]
- [[scripts-incremental_graph-py-_strip_dirty]]
- [[scripts-incremental_graph-py-_strip_non_python]]

## Called By

- [[scripts-incremental_graph-py-_compute_dirty_set]]
- [[scripts-incremental_graph-py-main]]
