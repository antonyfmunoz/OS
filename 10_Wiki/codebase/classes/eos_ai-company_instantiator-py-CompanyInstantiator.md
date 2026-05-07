---
type: codebase-class
file: eos_ai/company_instantiator.py
line: 220
generated: 2026-05-07
---

# CompanyInstantiator

**File:** [[eos_ai-company_instantiator-py]] | **Line:** 220

Instantiate all 6 Munoz Conglomerate companies as template instances.

## Methods

- [[eos_ai-company_instantiator-py-CompanyInstantiator-__init__]]`(org_id)` — 
- [[eos_ai-company_instantiator-py-CompanyInstantiator-instantiate_all]]`() → dict[str, TemplateInstance]` — Instantiate all 6 companies. Returns dict of venture_id -> TemplateInstance.
- [[eos_ai-company_instantiator-py-CompanyInstantiator-seed_offers]]`() → int` — Insert offer ladder rows for all companies. Returns total rows inserted.
- [[eos_ai-company_instantiator-py-CompanyInstantiator-ensure_ventures]]`() → int` — Ensure all venture_ids exist in the ventures table. Returns count of new rows.
- [[eos_ai-company_instantiator-py-CompanyInstantiator-run]]`() → None` — Full instantiation: ensure ventures -> instantiate templates -> seed offers.
