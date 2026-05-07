---
type: codebase-file
path: eos_ai/substrate/auto_task_generation.py
module: eos_ai.substrate.auto_task_generation
lines: 291
size: 9966
generated: 2026-05-07
---

# eos_ai/substrate/auto_task_generation.py

Auto-task generation — bridges the perception layer to the task system.

Consumes PerceptionRecords produced by the ambient collectors and generates
tasks for WARNING and CRITICAL observations.  Also provides a full
perception-to-task cycle runner and a summary endpoint for open_day briefings.
...

**Lines:** 291 | **Size:** 9,966 bytes

## Depends On

- [[eos_ai-substrate-perception-py]]

## Contains

- **fn** [[eos_ai-substrate-auto_task_generation-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-auto_task_generation-py-_utcnow]]`() → str`
- **fn** [[eos_ai-substrate-auto_task_generation-py-_candidate_title]]`(p) → str`
- **fn** [[eos_ai-substrate-auto_task_generation-py-generate_tasks_from_perceptions]]`(perceptions) → list[object]`
- **fn** [[eos_ai-substrate-auto_task_generation-py-run_perception_cycle]]`() → dict`
- **fn** [[eos_ai-substrate-auto_task_generation-py-get_perception_summary]]`() → dict`

## Import Statements

```python
from __future__ import annotations
import sys
from datetime import datetime
from datetime import timezone
from typing import Optional
from eos_ai.substrate.perception import PerceptionRecord
from eos_ai.substrate.perception import PerceptionSeverity
from eos_ai.substrate.perception import PerceptionStore
from eos_ai.substrate.perception import collect_all_perceptions
```
