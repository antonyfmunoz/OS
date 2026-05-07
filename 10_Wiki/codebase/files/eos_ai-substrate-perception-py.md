---
type: codebase-file
path: eos_ai/substrate/perception.py
module: eos_ai.substrate.perception
lines: 994
size: 40462
generated: 2026-05-07
---

# eos_ai/substrate/perception.py

Perception layer — ambient sensing of system and environment state.

Collects structured observations from across the substrate (tasks, pipelines,
operator session, node registry, git, runtime logs) into a unified stream of
PerceptionRecords.  The cognitive loop can consume these records to decide
...

**Lines:** 994 | **Size:** 40,462 bytes

## Used By

- [[eos_ai-substrate-auto_task_generation-py]]

## Contains

- **class** [[eos_ai-substrate-perception-py-PerceptionSource]] — 0 methods
- **class** [[eos_ai-substrate-perception-py-PerceptionSeverity]] — 0 methods
- **class** [[eos_ai-substrate-perception-py-PerceptionRecord]] — 3 methods
- **class** [[eos_ai-substrate-perception-py-PerceptionStore]] — 13 methods
- **fn** [[eos_ai-substrate-perception-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-perception-py-_utcnow]]`() → str`
- **fn** [[eos_ai-substrate-perception-py-_now]]`() → datetime`
- **fn** [[eos_ai-substrate-perception-py-_new_id]]`() → str`
- **fn** [[eos_ai-substrate-perception-py-_make_fingerprint]]`(source_value, summary) → str`
- **fn** [[eos_ai-substrate-perception-py-collect_task_perception]]`() → list[PerceptionRecord]`
- **fn** [[eos_ai-substrate-perception-py-collect_pipeline_perception]]`() → list[PerceptionRecord]`
- **fn** [[eos_ai-substrate-perception-py-collect_operator_session_perception]]`() → list[PerceptionRecord]`
- **fn** [[eos_ai-substrate-perception-py-collect_node_status_perception]]`() → list[PerceptionRecord]`
- **fn** [[eos_ai-substrate-perception-py-collect_git_perception]]`() → list[PerceptionRecord]`
- **fn** [[eos_ai-substrate-perception-py-collect_runtime_log_perception]]`() → list[PerceptionRecord]`
- **fn** [[eos_ai-substrate-perception-py-collect_station_presence_perception]]`() → list[PerceptionRecord]`
- **fn** [[eos_ai-substrate-perception-py-collect_local_control_perception]]`() → list[PerceptionRecord]`
- **fn** [[eos_ai-substrate-perception-py-collect_live_session_perception]]`() → list[PerceptionRecord]`
- **fn** [[eos_ai-substrate-perception-py-collect_all_perceptions]]`() → list[PerceptionRecord]`

## Import Statements

```python
from __future__ import annotations
import hashlib
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from datetime import timedelta
from enum import Enum
from typing import Any
from typing import Optional
```
