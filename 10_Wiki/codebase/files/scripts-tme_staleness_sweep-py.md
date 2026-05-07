---
type: codebase-file
path: scripts/tme_staleness_sweep.py
module: scripts.tme_staleness_sweep
lines: 86
size: 3194
tags: [entry-point]
generated: 2026-05-07
---

# scripts/tme_staleness_sweep.py

> **ENTRY POINT** — Contains `if __name__` or server start.

TME staleness sweep — summary-first report for hooks and cron.

**Lines:** 86 | **Size:** 3,194 bytes

## Depends On

- [[scripts-_tme_common-py]]

## Contains

- **fn** [[scripts-tme_staleness_sweep-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
from datetime import date
from scripts._tme_common import NEAR_STALE_FRACTION
from scripts._tme_common import load_all_skills
from scripts._tme_common import days_since
from scripts._tme_common import freshness_window
```
