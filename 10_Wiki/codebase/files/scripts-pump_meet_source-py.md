---
type: codebase-file
path: scripts/pump_meet_source.py
module: scripts.pump_meet_source
lines: 129
size: 4810
tags: [entry-point]
generated: 2026-05-07
---

# scripts/pump_meet_source.py

> **ENTRY POINT** — Contains `if __name__` or server start.

pump_meet_source — operator-driven single-shot pump for a Google Meet
transcript bridge source.

Attaches a ``GoogleMeetSource.from_bridge(...)`` to the default meeting
transport and drains up to ``--max`` lines from its JSONL caption bridge
...

**Lines:** 129 | **Size:** 4,810 bytes

## Contains

- **fn** [[scripts-pump_meet_source-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
import traceback
```
