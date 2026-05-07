---
type: codebase-file
path: core/reality_input.py
module: core.reality_input
lines: 329
size: 9057
generated: 2026-05-07
---

# core/reality_input.py

Reality Input Layer — ingest external signals and convert to primitives.

Converts raw real-world inputs (text, API responses, metrics) into
L0 primitive sets with source tracking and timestamps.

...

**Lines:** 329 | **Size:** 9,057 bytes

## Depends On

- [[core-primitives-py]]

## Contains

- **class** [[core-reality_input-py-RealitySignal]] — 1 methods
- **fn** [[core-reality_input-py-_classify_text]]`(text) → set[PrimitiveTag]`
- **fn** [[core-reality_input-py-_store_signal]]`(signal) → None`
- **fn** [[core-reality_input-py-get_signal_history]]`(limit) → list[RealitySignal]`
- **fn** [[core-reality_input-py-clear_signal_history]]`() → None`
- **fn** [[core-reality_input-py-ingest_signal]]`(raw_input) → RealitySignal`
- **fn** [[core-reality_input-py-ingest_metric]]`(name, value) → RealitySignal`
- **fn** [[core-reality_input-py-ingest_api_response]]`(endpoint, status_code, body) → RealitySignal`

## Import Statements

```python
from __future__ import annotations
import time
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from core.primitives import PrimitiveTag
```
