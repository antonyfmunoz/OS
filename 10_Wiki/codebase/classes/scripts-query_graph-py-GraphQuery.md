---
type: codebase-class
file: scripts/query_graph.py
line: 46
generated: 2026-04-12
---

# GraphQuery

**File:** [[scripts-query_graph-py]] | **Line:** 46

Indexed view of the codebase graph with traversal + ranking.

## Methods

- [[scripts-query_graph-py-GraphQuery-load]]`(path) → 'GraphQuery'` — 
- [[scripts-query_graph-py-GraphQuery-resolve]]`(token) → str | None` — Resolve a user-supplied token to a node id in the graph.
- [[scripts-query_graph-py-GraphQuery-dependencies]]`(node) → list[str]` — What this node depends on (what it imports or calls).
- [[scripts-query_graph-py-GraphQuery-dependents]]`(node) → list[str]` — What depends on this node (reverse lookup).
- [[scripts-query_graph-py-GraphQuery-path]]`(src, dst, max_depth) → list[str] | None` — BFS over the file-level import graph between two files.
- [[scripts-query_graph-py-GraphQuery-entry_points]]`() → list[str]` — 
- [[scripts-query_graph-py-GraphQuery-critical_files]]`() → list[str]` — 
- [[scripts-query_graph-py-GraphQuery-centrality]]`(top) → list[tuple[str, int, int]]` — Rank files by (imported_by + imports) — simple centrality proxy.
- [[scripts-query_graph-py-GraphQuery-search]]`(term) → list[str]` — 
- [[scripts-query_graph-py-GraphQuery-freshness]]`() → dict[str, Any]` — 
- [[scripts-query_graph-py-GraphQuery-languages]]`() → dict[str, int]` — Language-coverage counts from the last graph build.
- [[scripts-query_graph-py-GraphQuery-non_python_files]]`(language) → list[str]` — All non-Python files in the graph, optionally filtered by language.

## Decorators

- `@dataclass`
