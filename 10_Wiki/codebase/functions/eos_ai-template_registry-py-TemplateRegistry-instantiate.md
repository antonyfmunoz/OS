---
type: codebase-function
file: eos_ai/template_registry.py
line: 543
generated: 2026-05-07
---

# TemplateRegistry.instantiate

**File:** [[eos_ai-template_registry-py]] | **Line:** 543
**Signature:** `instantiate(template_id, context) → TemplateInstance | None`

**Class:** [[eos_ai-template_registry-py-TemplateRegistry]]

Create a TemplateInstance by filling slots from context dict.

## Calls

- [[eos_ai-template_registry-py-TemplateRegistry-get]]
- [[eos_ai-template_registry-py-TemplateRegistry-validate_slots]]

## Called By

- [[eos_ai-company_instantiator-py-CompanyInstantiator-instantiate_all]]
