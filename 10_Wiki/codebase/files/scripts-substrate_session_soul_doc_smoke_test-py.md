---
type: codebase-file
path: scripts/substrate_session_soul_doc_smoke_test.py
module: scripts.substrate_session_soul_doc_smoke_test
lines: 196
size: 6958
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_session_soul_doc_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

substrate_session_soul_doc_smoke_test.py

Verifies that claude_session_bridge launches claude with the correct
--append-system-prompt for persona-bound sessions (dex_product_main) and
without any override for developer sessions (dex_builder_main).
...

**Lines:** 196 | **Size:** 6,958 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]

## Contains

- **fn** [[scripts-substrate_session_soul_doc_smoke_test-py-check]]`(name, ok, detail) → None`
- **fn** [[scripts-substrate_session_soul_doc_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import os
import sys
import tempfile
from pathlib import Path
from eos_ai.substrate import claude_session_bridge as csb
```
