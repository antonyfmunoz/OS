---
type: codebase-file
path: eos_ai/substrate/ritual_runner.py
module: eos_ai.substrate.ritual_runner
lines: 218
size: 7366
tags: [entry-point]
generated: 2026-04-12
---

# eos_ai/substrate/ritual_runner.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Ritual runner — shell-callable entry points for open_day / close_day.

Wires the RitualRegistry into existing cron scripts with the smallest
possible surface: a module that can be invoked as

...

**Lines:** 218 | **Size:** 7,366 bytes

## Depends On

- [[eos_ai-substrate-ritual_body-py]]
- [[eos_ai-substrate-rituals-py]]

## Used By

- [[eos_ai-substrate-local_listener-py]]
- [[scripts-substrate_durable_result_smoke_test-py]]
- [[scripts-substrate_operator_state_smoke_test-py]]
- [[scripts-substrate_result_loop_smoke_test-py]]
- [[scripts-substrate_smoke_test-py]]

## Contains

- **fn** [[eos_ai-substrate-ritual_runner-py-_apply_ritual_state]]`(policy, ritual_id, ritual_kind, ritual_state) → None`
- **fn** [[eos_ai-substrate-ritual_runner-py-_today_inputs]]`() → dict`
- **fn** [[eos_ai-substrate-ritual_runner-py-start_open_day]]`(inputs, policy) → str`
- **fn** [[eos_ai-substrate-ritual_runner-py-finish_open_day]]`(ritual_id, outputs, policy) → None`
- **fn** [[eos_ai-substrate-ritual_runner-py-start_close_day]]`(inputs, policy) → str`
- **fn** [[eos_ai-substrate-ritual_runner-py-finish_close_day]]`(ritual_id, outputs, policy) → None`
- **fn** [[eos_ai-substrate-ritual_runner-py-fail_ritual]]`(ritual_id, reason) → None`
- **fn** [[eos_ai-substrate-ritual_runner-py-_main]]`(argv) → int`

## Import Statements

```python
from __future__ import annotations
import sys
from datetime import date
from eos_ai.substrate.ritual_body import RitualPolicy
from eos_ai.substrate.ritual_body import run_close_day_body
from eos_ai.substrate.ritual_body import run_open_day_body
from eos_ai.substrate.rituals import RitualKind
from eos_ai.substrate.rituals import RitualRegistry
from eos_ai.substrate.rituals import RitualState
```
