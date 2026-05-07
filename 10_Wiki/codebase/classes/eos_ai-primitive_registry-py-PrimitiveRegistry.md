---
type: codebase-class
file: eos_ai/primitive_registry.py
line: 156
generated: 2026-05-07
---

# PrimitiveRegistry

**File:** [[eos_ai-primitive_registry-py]] | **Line:** 156

Registry for ontological primitives used by the Meta Harness.

## Methods

- [[eos_ai-primitive_registry-py-PrimitiveRegistry-__init__]]`() → None` — 
- [[eos_ai-primitive_registry-py-PrimitiveRegistry-get]]`(primitive_id) → Primitive | None` — Return a primitive by ID, or None if not found.
- [[eos_ai-primitive_registry-py-PrimitiveRegistry-list_all]]`() → list[Primitive]` — Return all registered primitives.
- [[eos_ai-primitive_registry-py-PrimitiveRegistry-get_related]]`(primitive_id) → list[Primitive]` — Return all primitives related to the given primitive.
- [[eos_ai-primitive_registry-py-PrimitiveRegistry-validate_composition]]`(primitive_ids) → bool` — Check that a set of primitives forms a valid composition.
