---
type: codebase-class
file: core/context.py
line: 66
generated: 2026-05-07
---

# ContextualComposition

**File:** [[core-context-py]] | **Line:** 66

A domain composition enriched with L1 context.

The primitive tags remain identical to the original composition —
context only affects content, not structure.

## Methods

- [[core-context-py-ContextualComposition-__post_init__]]`() → None` — 
- [[core-context-py-ContextualComposition-to_primitives]]`() → set[PrimitiveTag]` — Primitive tags are preserved — context doesn't change structure.
- [[core-context-py-ContextualComposition-validate_isolation]]`() → list[str]` — Verify L1 context has not modified L0 structure.
- [[core-context-py-ContextualComposition-to_dict]]`() → dict[str, Any]` — 

## Decorators

- `@dataclass`
