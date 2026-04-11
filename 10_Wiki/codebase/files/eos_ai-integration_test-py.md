---
type: codebase-file
path: eos_ai/integration_test.py
module: eos_ai.integration_test
lines: 257
size: 10132
tags: [entry-point]
generated: 2026-04-11
---

# eos_ai/integration_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

EOS Full Integration Test — end-to-end chain validation.

Drives the complete signal → analysis → lead → outreach pipeline
through every layer: gateway → event bus → agent teams → memory.

...

**Lines:** 257 | **Size:** 10,132 bytes

## Depends On

- [[eos_ai-memory-py]]

## Contains

- **fn** [[eos_ai-integration_test-py-step]]`(n, label) → None`
- **fn** [[eos_ai-integration_test-py-show_events]]`(limit) → None`
- **fn** [[eos_ai-integration_test-py-show_pending]]`(gw) → None`
- **fn** [[eos_ai-integration_test-py-main]]`() → None`

## Import Statements

```python
import datetime
import json
import os
import sqlite3
import sys
from pathlib import Path
from eos_ai.memory import DB_PATH
```
