---
type: codebase-file
path: scripts/substrate_claude_responder_smoke_test.py
module: scripts.substrate_claude_responder_smoke_test
lines: 229
size: 9474
tags: [entry-point]
generated: 2026-05-07
---

# scripts/substrate_claude_responder_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Substrate Claude Responder v1 — smoke test.

Validates that the `claude_responder` adapter routes text through the
Claude Session Bridge and returns a structured reply dict without crashing
under any environment condition (tmux missing, session missing, empty
...

**Lines:** 229 | **Size:** 9,474 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]

## Contains

- **fn** [[scripts-substrate_claude_responder_smoke_test-py-check]]`(name, cond, detail) → None`
- **fn** [[scripts-substrate_claude_responder_smoke_test-py-_hotpath_clean]]`() → bool`
- **fn** [[scripts-substrate_claude_responder_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import json
import os
import sys
import uuid
from eos_ai.substrate import claude_responder as cr
from eos_ai.substrate import claude_session_bridge as csb
from eos_ai.substrate import discord_text_transport as dtt
```
