---
type: codebase-class
file: eos_ai/primitives.py
line: 783
generated: 2026-04-12
---

# PrimitiveRegistry

**File:** [[eos_ai-primitives-py]] | **Line:** 783

Composes stage-appropriate business primitives for CognitiveLoop injection.
Reads the live BIS to determine the current stage per venture.

## Methods

- [[eos_ai-primitives-py-PrimitiveRegistry-__init__]]`(ctx)` — 
- [[eos_ai-primitives-py-PrimitiveRegistry-_get_stage]]`(venture_id) → int` — Read BIS stage. Returns 1 on any failure (safe default).
- [[eos_ai-primitives-py-PrimitiveRegistry-compose_business_context]]`(venture_id) → str` — Returns a formatted string of stage-appropriate rules for prompt injection.
