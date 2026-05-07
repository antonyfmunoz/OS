---
type: codebase-function
file: core/composer.py
line: 242
generated: 2026-05-07
---

# compose

**File:** [[core-composer-py]] | **Line:** 242
**Signature:** `compose(intent, context) → ComposedStructure`

Convert intent + context into an executable composition.

This is the main entry point.  Steps:
1. Resolve which domain type the intent maps to
2. Instantiate the domain composition
...

## Calls

- [[core-composer-py-_populate_from_context]]
- [[core-composer-py-resolve_domain_type]]
- [[core-context-py-ContextualComposition-to_primitives]]
- [[core-context-py-ContextualComposition-validate_isolation]]
- [[core-context-py-apply_context]]
- [[core-domain-eos-py-DomainComposition-to_primitives]]
- [[core-primitives-py-decompose_to_dict]]
- [[core-primitives-py-validate_composition_tags]]
