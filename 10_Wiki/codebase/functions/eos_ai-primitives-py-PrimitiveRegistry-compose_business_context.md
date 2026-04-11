---
type: codebase-function
file: eos_ai/primitives.py
line: 808
generated: 2026-04-11
---

# PrimitiveRegistry.compose_business_context

**File:** [[eos_ai-primitives-py]] | **Line:** 808
**Signature:** `compose_business_context(venture_id) → str`

**Class:** [[eos_ai-primitives-py-PrimitiveRegistry]]

Returns a formatted string of stage-appropriate rules for prompt injection.
Returns empty string on any failure — never blocks execution.

## Calls

- [[eos_ai-primitives-py-PrimitiveRegistry-_get_stage]]
