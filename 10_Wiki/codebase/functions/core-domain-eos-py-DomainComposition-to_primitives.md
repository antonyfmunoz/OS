---
type: codebase-function
file: core/domain/eos.py
line: 49
generated: 2026-05-07
---

# DomainComposition.to_primitives

**File:** [[core-domain-eos-py]] | **Line:** 49
**Signature:** `to_primitives() → set[PrimitiveTag]`

**Class:** [[core-domain-eos-py-DomainComposition]]

Return the L0 primitive tags this composition maps to.

## Calls

- [[core-domain-eos-py-Channel-_primitive_tags]]
- [[core-domain-eos-py-DomainComposition-_primitive_tags]]
- [[core-domain-eos-py-ICP-_primitive_tags]]
- [[core-domain-eos-py-KPI-_primitive_tags]]
- [[core-domain-eos-py-Offer-_primitive_tags]]
- [[core-domain-eos-py-Role-_primitive_tags]]
- [[core-domain-eos-py-Workflow-_primitive_tags]]

## Called By

- [[core-composer-py-compose]]
- [[core-composer-py-validate_composition]]
- [[core-context-py-ContextualComposition-__post_init__]]
- [[core-context-py-ContextualComposition-validate_isolation]]
