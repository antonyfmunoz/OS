---
type: codebase-file
path: scripts/substrate_resolution_intelligence_smoke_test.py
module: scripts.substrate_resolution_intelligence_smoke_test
lines: 241
size: 7902
tags: [entry-point]
generated: 2026-04-11
---

# scripts/substrate_resolution_intelligence_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Smoke test for Resolution Intelligence Layer v1.

Validates the additive bounded upgrade on top of Execution Intelligence:

  1. A commitment is created via update_meeting_summary.
...

**Lines:** 241 | **Size:** 7,902 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]

## Contains

- **fn** [[scripts-substrate_resolution_intelligence_smoke_test-py-_force_model_failure]]`() → None`
- **fn** [[scripts-substrate_resolution_intelligence_smoke_test-py-_stub_speak]]`() → list[dict]`
- **fn** [[scripts-substrate_resolution_intelligence_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import subprocess
import sys
import time
from eos_ai.substrate import meeting_intelligence as mi
```
