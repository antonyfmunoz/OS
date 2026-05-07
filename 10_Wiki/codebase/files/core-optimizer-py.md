---
type: codebase-file
path: core/optimizer.py
module: core.optimizer
lines: 652
size: 23274
tags: [entry-point]
generated: 2026-05-07
---

# core/optimizer.py

> **ENTRY POINT** — Contains `if __name__` or server start.

optimizer.py — Feedback loop for the EOS AI OS.

Reads the append-only logs produced by the rest of the stack, looks for
patterns worth acting on, and writes improvement PROPOSALS to disk. A
proposal is a declarative record of a change — it never mutates anything
...

**Lines:** 652 | **Size:** 23,274 bytes

## Used By

- [[scripts-force_execution_loop-py]]

## Contains

- **class** [[core-optimizer-py-Proposal]] — 1 methods
- **class** [[core-optimizer-py-Optimizer]] — 7 methods
- **fn** [[core-optimizer-py-_new_id]]`() → str`
- **fn** [[core-optimizer-py-_read_jsonl]]`(path, limit) → list[dict[str, Any]]`
- **fn** [[core-optimizer-py-_read_json]]`(path) → dict[str, Any]`
- **fn** [[core-optimizer-py-analyze_flaky_steps]]`(ctx) → list[Proposal]`
- **fn** [[core-optimizer-py-analyze_disabled_jobs]]`(ctx) → list[Proposal]`
- **fn** [[core-optimizer-py-analyze_capability_denials]]`(ctx) → list[Proposal]`
- **fn** [[core-optimizer-py-analyze_stale_graph]]`(ctx) → list[Proposal]`
- **fn** [[core-optimizer-py-analyze_llm_failures]]`(ctx) → list[Proposal]`
- **fn** [[core-optimizer-py-analyze_advisor_effectiveness]]`(ctx) → list[Proposal]`
- **fn** [[core-optimizer-py-_cmd_once]]`(args) → int`
- **fn** [[core-optimizer-py-_cmd_list]]`(args) → int`
- **fn** [[core-optimizer-py-main]]`(argv) → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
import uuid
from collections import Counter
from collections import defaultdict
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
from typing import Callable
```
