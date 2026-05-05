---
type: codebase-file
path: eos_ai/substrate/operator_presence.py
module: eos_ai.substrate.operator_presence
lines: 120
size: 4294
generated: 2026-04-12
---

# eos_ai/substrate/operator_presence.py

Operator presence — tiny deterministic hybrid intro/outro templates.

This is the ENTIRE "cinematic EA presence" layer. On purpose.

There is no LLM here. There is no prompt template engine. There is no
...

**Lines:** 120 | **Size:** 4,294 bytes

## Depends On

- [[eos_ai-substrate-operator_state-py]]

## Used By

- [[scripts-substrate_operator_state_smoke_test-py]]

## Contains

- **fn** [[eos_ai-substrate-operator_presence-py-line_for_transition]]`(from_mode, to_mode) → Optional[str]`
- **fn** [[eos_ai-substrate-operator_presence-py-intro_for_transition]]`(transition) → Optional[str]`

## Import Statements

```python
from __future__ import annotations
from typing import Optional
from eos_ai.substrate.operator_state import OperatorMode
```
