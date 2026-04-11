---
type: codebase-function
file: scripts/codebase_graph.py
line: 240
generated: 2026-04-11
---

# scan_file

**File:** [[scripts-codebase_graph-py]] | **Line:** 240
**Signature:** `scan_file(path) → tuple[FileNode, list[ClassNode], list[FunctionNode]]`

Parse a single Python file and extract all nodes.

## Calls

- [[scripts-codebase_graph-py-_annotation_str]]
- [[scripts-codebase_graph-py-_decorator_name]]
- [[scripts-codebase_graph-py-_extract_calls]]
- [[scripts-codebase_graph-py-_is_entry_point]]
- [[scripts-codebase_graph-py-_module_name]]
- [[scripts-codebase_graph-py-_rel]]

## Called By

- [[scripts-codebase_graph-py-scan_codebase]]
