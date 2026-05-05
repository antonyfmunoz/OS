---
type: codebase-class
file: eos_ai/tenant.py
line: 52
generated: 2026-04-12
---

# TenantManager

**File:** [[eos_ai-tenant-py]] | **Line:** 52

*No docstring.*

## Methods

- [[eos_ai-tenant-py-TenantManager-__init__]]`(ctx) → None` — 
- [[eos_ai-tenant-py-TenantManager-get_tenant_context]]`() → TenantContext` — Load full tenant context from DB via BIS.
- [[eos_ai-tenant-py-TenantManager-validate_isolation]]`(query_org_id) → bool` — Verify org_id matches current context. Prevents cross-tenant data access.
- [[eos_ai-tenant-py-TenantManager-get_layer]]`(field_name) → TenantLayer` — Returns which protocol layer a field belongs to.
- [[eos_ai-tenant-py-TenantManager-format_for_prompt]]`() → str` — Format tenant context for injection into agent system prompts.
