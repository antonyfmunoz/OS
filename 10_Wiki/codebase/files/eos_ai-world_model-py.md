---
type: codebase-file
path: eos_ai/world_model.py
module: eos_ai.world_model
lines: 257
size: 10457
tags: [entry-point]
generated: 2026-05-07
---

# eos_ai/world_model.py

> **ENTRY POINT** — Contains `if __name__` or server start.

WorldModel — two-layer world model for the Meta Harness.

Canonical layer: shared truths across all orgs (slow-changing, seeded).
Instance layer: per-org observations and learnings (fast-changing).

...

**Lines:** 257 | **Size:** 10,457 bytes

## Contains

- **class** [[eos_ai-world_model-py-WorldModelEntry]] — 0 methods
- **class** [[eos_ai-world_model-py-CanonicalWorldModel]] — 6 methods
- **class** [[eos_ai-world_model-py-InstanceWorldModel]] — 6 methods
- **class** [[eos_ai-world_model-py-WorldModel]] — 4 methods

## Import Statements

```python
import os
import sys
import uuid as _uuid
from dataclasses import dataclass
from dataclasses import field
from dataclasses import asdict
from datetime import datetime
from datetime import timezone
```
