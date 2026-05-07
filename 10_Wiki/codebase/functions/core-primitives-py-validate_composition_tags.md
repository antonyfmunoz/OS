---
type: codebase-function
file: core/primitives.py
line: 201
generated: 2026-05-07
---

# validate_composition_tags

**File:** [[core-primitives-py]] | **Line:** 201
**Signature:** `validate_composition_tags(tags) → list[str]`

Validate that a composition's primitive tags form a coherent set.

A valid composition for execution must include at minimum:
- GOAL (what we're trying to achieve)
- ACTION (what we're doing)
...

## Calls

- [[core-primitives-py-validate_primitive_set]]

## Called By

- [[core-composer-py-compose]]
- [[core-composer-py-validate_composition]]
- [[core-domain-eos-py-DomainComposition-validate]]
- [[core-transformer-py-transform]]
