---
type: codebase-file
path: eos_ai/platforms/eos/decision_log.py
module: eos_ai.platforms.eos.decision_log
lines: 177
size: 5678
generated: 2026-05-07
---

# eos_ai/platforms/eos/decision_log.py

EOS platform decision log — persists routing and delegation decisions.

Uses the substrate storage layer for persistence (same JSON/Neon dual-layer).
This is platform-level decision logging — it does NOT replace substrate
memory or perception records.
...

**Lines:** 177 | **Size:** 5,678 bytes

## Used By

- [[eos_ai-platforms-eos-ea_orchestrator-py]]

## Contains

- **class** [[eos_ai-platforms-eos-decision_log-py-EOSDecisionRecord]] — 2 methods
- **class** [[eos_ai-platforms-eos-decision_log-py-DecisionLog]] — 10 methods
- **fn** [[eos_ai-platforms-eos-decision_log-py-_log]]`(msg) → None`
- **fn** [[eos_ai-platforms-eos-decision_log-py-_utcnow]]`() → str`
- **fn** [[eos_ai-platforms-eos-decision_log-py-_new_id]]`() → str`

## Import Statements

```python
from __future__ import annotations
import sys
import threading
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Optional
```
