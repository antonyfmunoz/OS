---
type: codebase-file
path: eos_ai/pattern_engine.py
module: eos_ai.pattern_engine
lines: 206
size: 8569
generated: 2026-05-07
---

# eos_ai/pattern_engine.py

PatternEngine — cross-session behavioral pattern detection.

Analyzes stored messages and events in Neon to detect recurring patterns
across multiple sessions. Surfaces avoidance behaviors, building-over-selling
tendencies, low follow-through, and late working habits.
...

**Lines:** 206 | **Size:** 8,569 bytes

## Depends On

- [[eos_ai-context-py]]

## Contains

- **class** [[eos_ai-pattern_engine-py-Pattern]] — 0 methods
- **class** [[eos_ai-pattern_engine-py-PatternEngine]] — 4 methods

## Import Statements

```python
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timedelta
from eos_ai.context import EOSContext
```
