---
type: codebase-file
path: eos_ai/platforms/eos/delegation.py
module: eos_ai.platforms.eos.delegation
lines: 60
size: 2218
generated: 2026-05-07
---

# eos_ai/platforms/eos/delegation.py

Delegation logic — decides whether EA handles a founder intent directly or
delegates to a specialist role (CEO, Portfolio Advisor).

Design rules:
- EA is always the primary interface — delegation is internal.
...

**Lines:** 60 | **Size:** 2,218 bytes

## Depends On

- [[eos_ai-platforms-eos-intent_routing-py]]
- [[eos_ai-platforms-eos-roles-py]]

## Used By

- [[eos_ai-platforms-eos-ea_orchestrator-py]]

## Contains

- **fn** [[eos_ai-platforms-eos-delegation-py-should_delegate]]`(intent) → bool`
- **fn** [[eos_ai-platforms-eos-delegation-py-choose_delegate]]`(intent) → EOSRole | None`

## Import Statements

```python
from __future__ import annotations
from eos_ai.platforms.eos.intent_routing import FounderIntent
from eos_ai.platforms.eos.intent_routing import FounderIntentType
from eos_ai.platforms.eos.roles import EOSRole
```
