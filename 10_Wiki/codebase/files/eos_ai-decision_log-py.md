---
type: codebase-file
path: eos_ai/decision_log.py
module: eos_ai.decision_log
lines: 218
size: 7413
generated: 2026-04-11
---

# eos_ai/decision_log.py

DecisionLog — permanent record of important decisions made in conversation.

Decisions disappear after the context window closes. This module detects
decision language in founder messages, extracts the key decision via LLM,
and stores it permanently in Neon as a 'decision' event.
...

**Lines:** 218 | **Size:** 7,413 bytes

## Depends On

- [[eos_ai-context-py]]

## Contains

- **class** [[eos_ai-decision_log-py-Decision]] — 0 methods
- **class** [[eos_ai-decision_log-py-DecisionLog]] — 6 methods

## Import Statements

```python
import json
import re
import uuid
from dataclasses import dataclass
from dataclasses import field
from eos_ai.context import EOSContext
```
