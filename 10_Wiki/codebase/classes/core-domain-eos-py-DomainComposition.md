---
type: codebase-class
file: core/domain/eos.py
line: 36
generated: 2026-05-07
---

# DomainComposition

**File:** [[core-domain-eos-py]] | **Line:** 36

Base class for all L2 domain structures.

Subclasses define which L0 primitives they map to by implementing
`_primitive_tags()`.  The public API (`to_primitives`, `validate`,
`to_dict`) is inherited.

## Inherited By

- [[core-domain-creator-py-Content]]
- [[core-domain-creator-py-Audience]]
- [[core-domain-creator-py-Platform]]
- [[core-domain-creator-py-Engagement]]
- [[core-domain-eos-py-ICP]]
- [[core-domain-eos-py-Offer]]
- [[core-domain-eos-py-Channel]]
- [[core-domain-eos-py-Workflow]]
- [[core-domain-eos-py-KPI]]
- [[core-domain-eos-py-Role]]
- [[core-domain-lyfe-py-Habit]]
- [[core-domain-lyfe-py-Energy]]
- [[core-domain-lyfe-py-Focus]]
- [[core-domain-lyfe-py-IdentityState]]

## Methods

- [[core-domain-eos-py-DomainComposition-_primitive_tags]]`() → set[PrimitiveTag]` — 
- [[core-domain-eos-py-DomainComposition-to_primitives]]`() → set[PrimitiveTag]` — Return the L0 primitive tags this composition maps to.
- [[core-domain-eos-py-DomainComposition-validate]]`() → list[str]` — Validate the primitive mapping is coherent.
- [[core-domain-eos-py-DomainComposition-to_dict]]`() → dict[str, Any]` — Serialise composition with full primitive trace.

## Decorators

- `@dataclass`
