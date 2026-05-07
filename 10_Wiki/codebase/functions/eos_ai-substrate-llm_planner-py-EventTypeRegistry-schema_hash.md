---
type: codebase-function
file: eos_ai/substrate/llm_planner.py
line: 197
generated: 2026-05-07
---

# EventTypeRegistry.schema_hash

**File:** [[eos_ai-substrate-llm_planner-py]] | **Line:** 197
**Signature:** `schema_hash() → str`

**Class:** [[eos_ai-substrate-llm_planner-py-EventTypeRegistry]]

Deterministic hash of all registered schemas.

Computed from canonical JSON of all schemas sorted by event_type.

## Calls

- [[eos_ai-substrate-llm_planner-py-_canonical_json]]
- [[eos_ai-substrate-llm_planner-py-_sha256_prefix]]

## Decorators

- `@property`
