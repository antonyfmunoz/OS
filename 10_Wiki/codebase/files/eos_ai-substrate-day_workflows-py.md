---
type: codebase-file
path: eos_ai/substrate/day_workflows.py
module: eos_ai.substrate.day_workflows
lines: 571
size: 24855
generated: 2026-05-07
---

# eos_ai/substrate/day_workflows.py

Day workflow coordination — open_day / close_day.

Coordination layer between the operator session spine (OperatorSessionStore)
and the existing ritual registry (RitualRegistry). No LLM calls. No tmux
logic. No Discord send logic. No operator_state / operator_transitions wiring.
...

**Lines:** 571 | **Size:** 24,855 bytes

## Depends On

- [[eos_ai-substrate-operator_session-py]]
- [[eos_ai-substrate-rituals-py]]

## Contains

- **fn** [[eos_ai-substrate-day_workflows-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-day_workflows-py-_utcnow]]`() → str`
- **fn** [[eos_ai-substrate-day_workflows-py-_today_str]]`() → str`
- **fn** [[eos_ai-substrate-day_workflows-py-_start_ritual_best_effort]]`(kind, inputs) → tuple[Optional[str], Optional[str]]`
- **fn** [[eos_ai-substrate-day_workflows-py-_advance_ritual_best_effort]]`(ritual_id, states, outputs) → Optional[str]`
- **fn** [[eos_ai-substrate-day_workflows-py-open_day]]`() → dict`
- **fn** [[eos_ai-substrate-day_workflows-py-close_day]]`() → dict`

## Import Statements

```python
from __future__ import annotations
import sys
from datetime import datetime
from datetime import timezone
from typing import Optional
from eos_ai.substrate.operator_session import OperatorDayMode
from eos_ai.substrate.operator_session import OperatorSession
from eos_ai.substrate.operator_session import OperatorSessionStore
from eos_ai.substrate.rituals import RitualKind
from eos_ai.substrate.rituals import RitualRegistry
from eos_ai.substrate.rituals import RitualState
```
