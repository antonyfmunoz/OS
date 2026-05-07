---
type: codebase-file
path: eos_ai/substrate/write_founder_gate_confirmation.py
module: eos_ai.substrate.write_founder_gate_confirmation
lines: 106
size: 3098
tags: [entry-point]
generated: 2026-05-07
---

# eos_ai/substrate/write_founder_gate_confirmation.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Write a founder visual confirmation file to the local inbox.

Usage:
    python3 /opt/OS/eos_ai/substrate/write_founder_gate_confirmation.py         --work-order-id WO-LOCAL-PILOT-GDRIVE-GDOCS-001         --gate VISIBLE_CHROME_LAUNCH         --confirmed true         --notes "Chrome visibly open on desktop"

...

**Lines:** 106 | **Size:** 3,098 bytes

## Contains

- **fn** [[eos_ai-substrate-write_founder_gate_confirmation-py-build_founder_visual_confirmation]]`(work_order_id, gate, confirmed, visible_app, notes) → dict`
- **fn** [[eos_ai-substrate-write_founder_gate_confirmation-py-write_confirmation]]`(work_order_id, gate, confirmed, visible_app, notes, inbox_dir) → Path`
- **fn** [[eos_ai-substrate-write_founder_gate_confirmation-py-main]]`() → None`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime
from datetime import timezone
from pathlib import Path
```
