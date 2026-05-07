---
type: codebase-file
path: scripts/session_watcher_smoke_test.py
module: scripts.session_watcher_smoke_test
lines: 433
size: 17440
generated: 2026-05-07
---

# scripts/session_watcher_smoke_test.py

Smoke tests for Session Watcher + Discord Bridge.

Tests:
  1. State machine transitions (all 5 states)
  2. Reply extraction from mock tmux output
...

**Lines:** 433 | **Size:** 17,440 bytes

## Depends On

- [[eos_ai-substrate-session_watcher-py]]

## Contains

- **fn** [[scripts-session_watcher_smoke_test-py-check]]`(label, condition, detail) → None`

## Import Statements

```python
import sys
import threading
import time
from eos_ai.substrate.session_watcher import _STABLE_CYCLES_FOR_COMPLETE
from eos_ai.substrate.session_watcher import _TOOL_CALL_PATTERNS
from eos_ai.substrate.session_watcher import _IDLE_TIMEOUT_S
from eos_ai.substrate.session_watcher import _WORKING_TIMEOUT_S
from eos_ai.substrate.session_watcher import _TOOL_CALL_PATTERNS
```
