---
type: codebase-file
path: core/memory_evolution.py
module: core.memory_evolution
lines: 558
size: 20978
generated: 2026-05-07
---

# core/memory_evolution.py

Memory Evolution System — adaptive learning from execution history.

Stores execution runs at the primitive level, detects patterns across
runs, and suggests optimizations.  Feeds back into the transformer
to improve future compositions.
...

**Lines:** 558 | **Size:** 20,978 bytes

## Depends On

- [[core-primitives-py]]

## Contains

- **class** [[core-memory_evolution-py-RunRecord]] — 1 methods
- **class** [[core-memory_evolution-py-PrimitivePattern]] — 1 methods
- **class** [[core-memory_evolution-py-MemorySystem]] — 9 methods
- **class** [[core-memory_evolution-py-StrategyPattern]] — 1 methods
- **fn** [[core-memory_evolution-py-get_memory]]`() → MemorySystem`
- **fn** [[core-memory_evolution-py-_extract_strategies]]`(min_runs) → list[StrategyPattern]`
- **fn** [[core-memory_evolution-py-_rank_strategies]]`(min_runs) → list[StrategyPattern]`
- **fn** [[core-memory_evolution-py-_suggest_strategy_reuse]]`(intent, domain, current_tags) → list[dict[str, Any]]`

## Import Statements

```python
from __future__ import annotations
import json
import time
from collections import Counter
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any
from core.primitives import PrimitiveTag
```
