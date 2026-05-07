---
type: codebase-function
file: eos_ai/company_instantiator.py
line: 269
generated: 2026-05-07
---

# CompanyInstantiator.ensure_ventures

**File:** [[eos_ai-company_instantiator-py]] | **Line:** 269
**Signature:** `ensure_ventures() → int`

**Class:** [[eos_ai-company_instantiator-py-CompanyInstantiator]]

Ensure all venture_ids exist in the ventures table. Returns count of new rows.

## Calls

- [[eos_ai-db-py-get_conn]]

## Called By

- [[eos_ai-company_instantiator-py-CompanyInstantiator-run]]
