---
type: codebase-cloud
generated: 2026-04-12
---

# Cloud Context — Codebase Knowledge Graph

This file instructs AI agents on how to use the preloaded
codebase knowledge graph stored in `10_Wiki/codebase/`.

## What This Is

A persistent, structured knowledge graph of the entire EOS codebase.
It contains 429 files, 459 classes,
and 3991 functions with full dependency mapping.

Every node (file, class, function) is a markdown page with:
- What it depends on (Depends On section with wikilinks)
- What depends on it (Used By section with wikilinks)
- What it contains (classes, functions)
- Docstring summary
- Line count and location

## How to Navigate

```
10_Wiki/codebase/
  index.md          ← Start here. Module list, critical files, entry points.
  cloud.md          ← This file. AI instructions.
  modules/          ← One page per top-level directory (eos_ai, services, etc.)
  files/            ← One page per Python file with full dependency map
  classes/          ← One page per class with methods and inheritance
  functions/        ← One page per public function with call graph
```

## Rules for AI Agents

1. **Always check this graph first** before scanning files.
   The graph already knows every file, class, function, and dependency.

2. **Only open a file when you need to read implementation details.**
   The graph gives you structure and relationships — you only need
   the actual source when you need to understand logic.

3. **Use the dependency map to understand impact.**
   Before modifying a file, check its "Used By" section to understand
   what will be affected.

4. **Start from modules, drill into files.**
   `modules/eos_ai.md` gives you the full module overview.
   Follow wikilinks to specific files.

5. **Critical files require extra care.**
   Files tagged `critical` are core infrastructure. Read the file
   AND its dependents before making changes.

6. **Entry points are where execution starts.**
   Files tagged `entry-point` contain `if __name__` blocks or
   server start logic. These are the roots of the call graph.

## Machine-Readable Graph

The full graph is also available as JSON at:
`data/codebase_graph.json`

Use this for programmatic queries, custom analysis, or
feeding into other tools.

## Freshness

This graph was generated on 2026-04-12.
Run `scripts/update-graph` to rebuild after code changes.
The graph does NOT auto-update — treat it as a snapshot.
If a file referenced in the graph doesn't exist, the graph is stale.
