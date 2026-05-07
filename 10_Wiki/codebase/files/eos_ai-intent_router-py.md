---
type: codebase-file
path: eos_ai/intent_router.py
module: eos_ai.intent_router
lines: 174
size: 4447
generated: 2026-05-07
---

# eos_ai/intent_router.py

IntentRouter — classify founder messages to the correct agent domain.

Lightweight keyword routing layer. Runs before the cognitive loop
so the right agent gets context injected before it responds.

...

**Lines:** 174 | **Size:** 4,447 bytes

## Depends On

- [[eos_ai-context-py]]

## Contains

- **class** [[eos_ai-intent_router-py-IntentDomain]] — 0 methods
- **class** [[eos_ai-intent_router-py-IntentRouter]] — 3 methods

## Import Statements

```python
from enum import Enum
from eos_ai.context import EOSContext
```
