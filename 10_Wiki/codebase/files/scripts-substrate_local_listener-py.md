---
type: codebase-file
path: scripts/substrate_local_listener.py
module: scripts.substrate_local_listener
lines: 104
size: 3156
tags: [entry-point]
generated: 2026-04-11
---

# scripts/substrate_local_listener.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Local listener CLI — emit a bounded activation trigger.

This is the operator-facing entrypoint for the new local listener layer.
It is intentionally tiny: pick a trigger kind, pick a node, optionally
hint a requested mode, and the listener will (safely) attempt to start an
...

**Lines:** 104 | **Size:** 3,156 bytes

## Depends On

- [[eos_ai-substrate-local_listener-py]]

## Contains

- **fn** [[scripts-substrate_local_listener-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
from eos_ai.substrate.local_listener import LocalListener
from eos_ai.substrate.local_listener import TriggerKind
from eos_ai.substrate.local_listener import get_trigger_history
from eos_ai.substrate.local_listener import listener_report
```
