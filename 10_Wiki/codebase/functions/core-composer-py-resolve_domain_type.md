---
type: codebase-function
file: core/composer.py
line: 71
generated: 2026-05-07
---

# resolve_domain_type

**File:** [[core-composer-py]] | **Line:** 71
**Signature:** `resolve_domain_type(intent) → str`

Map a natural-language intent to a domain composition type key.

Returns the DOMAIN_TYPES key (e.g. "icp", "offer").
Falls back to "workflow" when no keywords match — most intents
describe a process to execute.

## Called By

- [[core-composer-py-compose]]
