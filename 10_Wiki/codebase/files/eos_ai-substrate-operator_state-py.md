---
type: codebase-file
path: eos_ai/substrate/operator_state.py
module: eos_ai.substrate.operator_state
lines: 394
size: 14790
generated: 2026-04-12
---

# eos_ai/substrate/operator_state.py

Operator state — bounded unified state model for the workstation operator.

Purpose
-------
Until now the substrate had four parallel signals living in four stores:
...

**Lines:** 394 | **Size:** 14,790 bytes

## Used By

- [[eos_ai-substrate-operator_presence-py]]
- [[eos_ai-substrate-operator_transitions-py]]
- [[scripts-substrate_audio_loop_smoke_test-py]]
- [[scripts-substrate_operator_state_smoke_test-py]]
- [[scripts-substrate_stt_producer_smoke_test-py]]

## Contains

- **class** [[eos_ai-substrate-operator_state-py-OperatorMode]] — 0 methods
- **class** [[eos_ai-substrate-operator_state-py-OperatorTransition]] — 2 methods
- **class** [[eos_ai-substrate-operator_state-py-OperatorState]] — 5 methods
- **class** [[eos_ai-substrate-operator_state-py-OperatorStateStore]] — 11 methods
- **fn** [[eos_ai-substrate-operator_state-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-operator_state-py-_utcnow]]`() → str`
- **fn** [[eos_ai-substrate-operator_state-py-_new_id]]`(prefix) → str`
- **fn** [[eos_ai-substrate-operator_state-py-get_operator_state_store]]`() → OperatorStateStore`
- **fn** [[eos_ai-substrate-operator_state-py-reset_operator_state_store_for_tests]]`() → None`

## Import Statements

```python
from __future__ import annotations
import sys
import threading
import uuid
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
from typing import Optional
```
