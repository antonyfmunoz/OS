---
type: codebase-file
path: eos_ai/substrate/planner.py
module: eos_ai.substrate.planner
lines: 452
size: 15081
generated: 2026-05-07
---

# eos_ai/substrate/planner.py

Planner — deterministic plan generation and step emission.

The planner implements DecisionStrategy so it plugs directly into the
existing DecisionEngine.  When active intents exist in state, the
planner takes precedence.  When no intents exist, it yields None so
...

**Lines:** 452 | **Size:** 15,081 bytes

## Depends On

- [[eos_ai-substrate-decision_engine-py]]

## Contains

- **class** [[eos_ai-substrate-planner-py-PlannerStrategy]] — 4 methods
- **class** [[eos_ai-substrate-planner-py-IntentAwareStrategy]] — 6 methods
- **fn** [[eos_ai-substrate-planner-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-planner-py-register_plan_generator]]`(intent_type, generator) → None`
- **fn** [[eos_ai-substrate-planner-py-get_plan_generator]]`(intent_type) → PlanGenerator | None`
- **fn** [[eos_ai-substrate-planner-py-_generate_lifecycle_finalize_plan]]`(intent, state) → tuple[PlanStep, ...]`
- **fn** [[eos_ai-substrate-planner-py-_generate_lifecycle_publish_plan]]`(intent, state) → tuple[PlanStep, ...]`
- **fn** [[eos_ai-substrate-planner-py-_generate_lifecycle_clear_plan]]`(intent, state) → tuple[PlanStep, ...]`
- **fn** [[eos_ai-substrate-planner-py-_generate_execution_request_plan]]`(intent, state) → tuple[PlanStep, ...]`
- **fn** [[eos_ai-substrate-planner-py-_generate_custom_plan]]`(intent, state) → tuple[PlanStep, ...]`
- **fn** [[eos_ai-substrate-planner-py-derive_plan]]`(intent, state) → Plan | None`
- **fn** [[eos_ai-substrate-planner-py-build_step_advance_mutations]]`(intent) → list[dict[str, Any]]`
- **fn** [[eos_ai-substrate-planner-py-build_intent_complete_mutations]]`(intent) → list[dict[str, Any]]`
- **fn** [[eos_ai-substrate-planner-py-build_intent_fail_mutations]]`(intent) → list[dict[str, Any]]`
- **fn** [[eos_ai-substrate-planner-py-_deterministic_decision_id]]`(strategy, intent_id, step_index, state_hash) → str`

## Import Statements

```python
from __future__ import annotations
import hashlib
import json
import sys
from typing import Any
from typing import Callable
from eos_ai.substrate.decision_engine import DecisionOutput
from eos_ai.substrate.decision_engine import _compute_state_hash
from eos_ai.substrate.intent_models import Intent
from eos_ai.substrate.intent_models import IntentStatus
from eos_ai.substrate.intent_models import IntentType
from eos_ai.substrate.intent_models import Plan
from eos_ai.substrate.intent_models import PlanStep
from eos_ai.substrate.intent_models import compute_plan_id
from eos_ai.substrate.intent_models import get_active_intents_from_state
from eos_ai.substrate.intent_models import intent_store_key
```
