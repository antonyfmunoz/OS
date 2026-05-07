---
type: codebase-file
path: core/capabilities.py
module: core.capabilities
lines: 331
size: 10806
generated: 2026-05-07
---

# core/capabilities.py

Capability Registry — models available execution resources.

Each Capability represents a resource that can execute primitive-derived
tasks: an LLM, a local Python runtime, an external API, or a human.
The registry is the single source of truth for what the system can use.
...

**Lines:** 331 | **Size:** 10,806 bytes

## Used By

- [[core-matcher-py]]
- [[core-router-py]]

## Contains

- **class** [[core-capabilities-py-PerformanceRecord]] — 4 methods
- **class** [[core-capabilities-py-Capability]] — 2 methods
- **fn** [[core-capabilities-py-_build_default_capabilities]]`() → dict[str, Capability]`
- **fn** [[core-capabilities-py-get_capability]]`(name) → Capability | None`
- **fn** [[core-capabilities-py-register_capability]]`(cap) → None`
- **fn** [[core-capabilities-py-list_capabilities]]`(type_filter) → list[Capability]`
- **fn** [[core-capabilities-py-record_outcome]]`(capability_name) → None`
- **fn** [[core-capabilities-py-load_performance_data]]`() → None`
- **fn** [[core-capabilities-py-_persist_performance]]`(cap_name, perf) → None`

## Import Statements

```python
from __future__ import annotations
import json
import os
import time
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any
```
