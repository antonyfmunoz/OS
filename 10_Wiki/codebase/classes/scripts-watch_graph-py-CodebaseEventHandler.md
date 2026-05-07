---
type: codebase-class
file: scripts/watch_graph.py
line: 118
generated: 2026-05-07
---

# CodebaseEventHandler

**File:** [[scripts-watch_graph-py]] | **Line:** 118

Accumulates file-system events into a thread-safe pending set.

## Inherits From

- `FileSystemEventHandler`

## Methods

- [[scripts-watch_graph-py-CodebaseEventHandler-__init__]]`(pending, lock, cond, verbose)` — 
- [[scripts-watch_graph-py-CodebaseEventHandler-_record]]`(src_path) → None` — 
- [[scripts-watch_graph-py-CodebaseEventHandler-on_created]]`(event) → None` — 
- [[scripts-watch_graph-py-CodebaseEventHandler-on_modified]]`(event) → None` — 
- [[scripts-watch_graph-py-CodebaseEventHandler-on_deleted]]`(event) → None` — 
- [[scripts-watch_graph-py-CodebaseEventHandler-on_moved]]`(event) → None` — 
- [[scripts-watch_graph-py-CodebaseEventHandler-runaway_active]]`() → bool` — 
