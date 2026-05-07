---
type: codebase-function
file: core/context.py
line: 84
generated: 2026-05-07
---

# ContextualComposition.validate_isolation

**File:** [[core-context-py]] | **Line:** 84
**Signature:** `validate_isolation() → list[str]`

**Class:** [[core-context-py-ContextualComposition]]

Verify L1 context has not modified L0 structure.

## Calls

- [[core-context-py-ContextualComposition-to_primitives]]
- [[core-domain-eos-py-DomainComposition-to_primitives]]

## Called By

- [[core-composer-py-compose]]
- [[core-composer-py-validate_composition]]
- [[core-context-py-ContextualComposition-to_dict]]
