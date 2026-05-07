---
type: codebase-file
path: scripts/phase75a_dep_scanner.py
module: scripts.phase75a_dep_scanner
lines: 232
size: 7797
tags: [entry-point]
generated: 2026-05-07
---

# scripts/phase75a_dep_scanner.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Phase 75A — AST-based dependency scanner for UMH.

Extracts internal imports among umh.* modules, identifies:
- internal import graph (who imports whom)
- circular imports
...

**Lines:** 232 | **Size:** 7,797 bytes

## Contains

- **fn** [[scripts-phase75a_dep_scanner-py-find_python_files]]`(base) → list[Path]`
- **fn** [[scripts-phase75a_dep_scanner-py-module_from_path]]`(p) → str`
- **fn** [[scripts-phase75a_dep_scanner-py-extract_imports]]`(filepath) → list[str]`
- **fn** [[scripts-phase75a_dep_scanner-py-normalize_to_package]]`(mod) → str`
- **fn** [[scripts-phase75a_dep_scanner-py-find_cycles]]`(graph) → list[list[str]]`
- **fn** [[scripts-phase75a_dep_scanner-py-detect_sensitive_imports]]`(files, mod_map) → list[dict]`
- **fn** [[scripts-phase75a_dep_scanner-py-main]]`()`

## Import Statements

```python
import ast
import json
from collections import defaultdict
from pathlib import Path
```
