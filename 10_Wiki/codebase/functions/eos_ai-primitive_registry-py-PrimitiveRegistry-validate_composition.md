---
type: codebase-function
file: eos_ai/primitive_registry.py
line: 181
generated: 2026-05-07
---

# PrimitiveRegistry.validate_composition

**File:** [[eos_ai-primitive_registry-py]] | **Line:** 181
**Signature:** `validate_composition(primitive_ids) → bool`

**Class:** [[eos_ai-primitive_registry-py-PrimitiveRegistry]]

Check that a set of primitives forms a valid composition.

Valid = every referenced relationship is either in the set
or exists in the registry.

## Calls

- [[eos_ai-primitive_registry-py-PrimitiveRegistry-get]]
