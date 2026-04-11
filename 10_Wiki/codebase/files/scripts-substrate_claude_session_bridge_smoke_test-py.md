---
type: codebase-file
path: scripts/substrate_claude_session_bridge_smoke_test.py
module: scripts.substrate_claude_session_bridge_smoke_test
lines: 208
size: 8260
tags: [entry-point]
generated: 2026-04-11
---

# scripts/substrate_claude_session_bridge_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Substrate Claude Code Session Bridge v1 — smoke test.

Validates the bridge end-to-end without depending on the claude CLI itself.
Sessions are created with launch_claude=False so the test runs against a
plain shell pane; message injection and capture are exercised using shell
...

**Lines:** 208 | **Size:** 8,260 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]

## Contains

- **fn** [[scripts-substrate_claude_session_bridge_smoke_test-py-check]]`(name, cond, detail) → None`
- **fn** [[scripts-substrate_claude_session_bridge_smoke_test-py-_hotpath_clean]]`() → bool`
- **fn** [[scripts-substrate_claude_session_bridge_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import json
import sys
import time
import uuid
from eos_ai.substrate import claude_session_bridge as csb
```
