---
type: codebase-function
file: eos_ai/substrate/llm_planner.py
line: 249
generated: 2026-05-07
---

# EventTypeRegistry.validate_event

**File:** [[eos_ai-substrate-llm_planner-py]] | **Line:** 249
**Signature:** `validate_event(event_type, payload) → tuple[bool, str]`

**Class:** [[eos_ai-substrate-llm_planner-py-EventTypeRegistry]]

Validate an event_type + payload against the registry.

Returns (valid, reason).  Checks:
1. Event type exists.
2. All required fields present.
...

## Calls

- [[eos_ai-substrate-llm_planner-py-EventTypeRegistry-get]]

## Called By

- [[eos_ai-substrate-llm_planner-py-EventTypeRegistry-validate_proposal]]
