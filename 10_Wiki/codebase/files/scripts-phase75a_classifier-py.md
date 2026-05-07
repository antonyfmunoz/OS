---
type: codebase-file
path: scripts/phase75a_classifier.py
module: scripts.phase75a_classifier
lines: 280
size: 8462
tags: [entry-point]
generated: 2026-05-07
---

# scripts/phase75a_classifier.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Phase 75A — Auto-classify UMH modules by PRD domain and MVP status.

**Lines:** 280 | **Size:** 8,462 bytes

## Contains

- **fn** [[scripts-phase75a_classifier-py-module_from_path]]`(p) → str`
- **fn** [[scripts-phase75a_classifier-py-get_purpose]]`(filepath) → str`
- **fn** [[scripts-phase75a_classifier-py-classify]]`(mod, filepath) → str`
- **fn** [[scripts-phase75a_classifier-py-get_domain]]`(mod) → str`
- **fn** [[scripts-phase75a_classifier-py-extract_imports]]`(filepath) → list[str]`
- **fn** [[scripts-phase75a_classifier-py-main]]`()`

## Import Statements

```python
import ast
import json
from pathlib import Path
```
