---
type: codebase-file
path: scripts/substrate_meeting_intelligence_smoke_test.py
module: scripts.substrate_meeting_intelligence_smoke_test
lines: 143
size: 5902
tags: [entry-point]
generated: 2026-04-11
---

# scripts/substrate_meeting_intelligence_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Smoke test for Meeting Intelligence Layer v1.

Validates:
  1. Utterances flow through update_meeting_summary.
  2. Summary updates after threshold.
...

**Lines:** 143 | **Size:** 5,902 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]

## Contains

- **class** [[scripts-substrate_meeting_intelligence_smoke_test-py-MockSummary]] — 0 methods
- **fn** [[scripts-substrate_meeting_intelligence_smoke_test-py-_force_model_failure]]`()`
- **fn** [[scripts-substrate_meeting_intelligence_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import sys
import time
from eos_ai.substrate import meeting_intelligence as mi
```
