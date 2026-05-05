---
type: codebase-file
path: core/observability.py
module: core.observability
lines: 408
size: 15518
generated: 2026-04-12
---

# core/observability.py

observability.py — Read-only view over the EOS AI OS.

Single entry point for "what is the system doing right now?". Reads JSONL
and state files — never touches the runtime. Safe to run when the
orchestrator is not running.
...

**Lines:** 408 | **Size:** 15,518 bytes

## Used By

- [[scripts-eos_os-py]]
- [[scripts-sandbox_smoke_test-py]]

## Contains

- **class** [[core-observability-py-LogPaths]] — 0 methods
- **class** [[core-observability-py-Observability]] — 15 methods
- **fn** [[core-observability-py-_read_jsonl_tail]]`(path, n) → list[dict[str, Any]]`
- **fn** [[core-observability-py-_read_json]]`(path) → dict[str, Any]`
- **fn** [[core-observability-py-_paths_for_env_root]]`(root) → LogPaths`
- **fn** [[core-observability-py-_enumerate_envs]]`(root) → list[dict[str, Any]]`

## Import Statements

```python
from __future__ import annotations
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
```
