---
type: codebase-function
file: eos_ai/evolution_engine.py
line: 183
generated: 2026-04-12
---

# EvolutionEngine.is_primitive_unlocked

**File:** [[eos_ai-evolution_engine-py]] | **Line:** 183
**Signature:** `is_primitive_unlocked(primitive_id, venture_id) → dict`

**Class:** [[eos_ai-evolution_engine-py-EvolutionEngine]]

Check whether a primitive applies at the venture's current stage.

Returns:
    {
        'applies':              bool,
...

## Calls

- [[eos_ai-evolution_engine-py-EvolutionEngine-_get_stage]]

## Called By

- [[eos_ai-evolution_engine-py-EvolutionEngine-check_prerequisites]]
