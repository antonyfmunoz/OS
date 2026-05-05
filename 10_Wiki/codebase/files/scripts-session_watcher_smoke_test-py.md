---
type: codebase-file
path: scripts/session_watcher_smoke_test.py
module: scripts.session_watcher_smoke_test
lines: 245
size: 9051
generated: 2026-04-12
---

# scripts/session_watcher_smoke_test.py

Smoke tests for Session Watcher + Discord Bridge.

Tests:
  1. State machine transitions (all 5 states)
  2. Reply extraction from mock tmux output
...

**Lines:** 245 | **Size:** 9,051 bytes

## Contains

- **fn** [[scripts-session_watcher_smoke_test-py-check]]`(label, condition, detail) → None`

## Import Statements

```python
import sys
import threading
import time
```
