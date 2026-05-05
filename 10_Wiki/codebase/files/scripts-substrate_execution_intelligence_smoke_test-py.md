---
type: codebase-file
path: scripts/substrate_execution_intelligence_smoke_test.py
module: scripts.substrate_execution_intelligence_smoke_test
lines: 305
size: 11166
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_execution_intelligence_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Smoke test for Execution Intelligence Layer v1.

Validates the additive bounded upgrade on top of Meeting Intelligence:

  1. extract_commitments pulls commitments from simple utterances.
...

**Lines:** 305 | **Size:** 11,166 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]

## Contains

- **class** [[scripts-substrate_execution_intelligence_smoke_test-py-_FakeResult]] — 1 methods
- **fn** [[scripts-substrate_execution_intelligence_smoke_test-py-_force_model_failure]]`() → None`
- **fn** [[scripts-substrate_execution_intelligence_smoke_test-py-_stub_speak]]`() → list[dict]`
- **fn** [[scripts-substrate_execution_intelligence_smoke_test-py-_fresh]]`(node_id, meeting_id) → mi.MeetingSummary`
- **fn** [[scripts-substrate_execution_intelligence_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import sys
import time
from eos_ai.substrate import meeting_intelligence as mi
```
