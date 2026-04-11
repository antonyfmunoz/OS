---
type: codebase-file
path: eos_ai/substrate/operator_transitions.py
module: eos_ai.substrate.operator_transitions
lines: 482
size: 17484
generated: 2026-04-11
---

# eos_ai/substrate/operator_transitions.py

Operator transitions — deterministic state transition layer.

This is the brain of the operator state engine. It is intentionally tiny:

  - one pure function `decide_transition(state, trigger)` that returns the
...

**Lines:** 482 | **Size:** 17,484 bytes

## Depends On

- [[eos_ai-substrate-operator_state-py]]

## Used By

- [[scripts-substrate_audio_loop_smoke_test-py]]

## Contains

- **class** [[eos_ai-substrate-operator_transitions-py-TransitionTrigger]] — 0 methods
- **class** [[eos_ai-substrate-operator_transitions-py-TransitionDecision]] — 0 methods
- **fn** [[eos_ai-substrate-operator_transitions-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-operator_transitions-py-_utcnow]]`() → str`
- **fn** [[eos_ai-substrate-operator_transitions-py-_new_transition_id]]`() → str`
- **fn** [[eos_ai-substrate-operator_transitions-py-decide_transition]]`(state, trigger) → TransitionDecision`
- **fn** [[eos_ai-substrate-operator_transitions-py-_record_transition]]`(state, decision, trigger_kind, metadata) → None`
- **fn** [[eos_ai-substrate-operator_transitions-py-_emit_presence_if_needed]]`(state, transition) → None`
- **fn** [[eos_ai-substrate-operator_transitions-py-apply_wake_event]]`(event) → None`
- **fn** [[eos_ai-substrate-operator_transitions-py-apply_voice_session]]`(session) → None`
- **fn** [[eos_ai-substrate-operator_transitions-py-apply_ritual]]`(node_id) → None`

## Import Statements

```python
from __future__ import annotations
import sys
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from typing import Optional
from eos_ai.substrate.operator_state import OperatorMode
from eos_ai.substrate.operator_state import OperatorState
from eos_ai.substrate.operator_state import OperatorTransition
from eos_ai.substrate.operator_state import get_operator_state_store
```
