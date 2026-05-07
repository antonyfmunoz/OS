---
type: codebase-class
file: eos_ai/template_registry.py
line: 525
generated: 2026-05-07
---

# TemplateRegistry

**File:** [[eos_ai-template_registry-py]] | **Line:** 525

Registry for composable template blueprints.

## Methods

- [[eos_ai-template_registry-py-TemplateRegistry-__init__]]`() → None` — 
- [[eos_ai-template_registry-py-TemplateRegistry-register]]`(template) → None` — Add or overwrite a template in the registry.
- [[eos_ai-template_registry-py-TemplateRegistry-get]]`(template_id) → Template | None` — Retrieve a template by id.
- [[eos_ai-template_registry-py-TemplateRegistry-list_by_domain]]`(domain) → list[Template]` — Return all templates in a given domain.
- [[eos_ai-template_registry-py-TemplateRegistry-instantiate]]`(template_id, context) → TemplateInstance | None` — Create a TemplateInstance by filling slots from context dict.
- [[eos_ai-template_registry-py-TemplateRegistry-validate_slots]]`(template_id, context) → tuple[bool, list[str]]` — Check which required slots are missing from context.
