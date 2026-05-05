---
type: codebase-file
path: eos_ai/tenant.py
module: eos_ai.tenant
lines: 146
size: 5318
generated: 2026-04-12
---

# eos_ai/tenant.py

Tenant — formal multi-tenant isolation layer for EOS.

Three-layer model:
  PLATFORM  — shared codebase on GitHub (cognitive_loop, primitives, hierarchy)
  INSTANCE  — per-user context loaded from DB (org_id, ai_name, offer, ICP)
...

**Lines:** 146 | **Size:** 5,318 bytes

## Contains

- **class** [[eos_ai-tenant-py-TenantLayer]] — 0 methods
- **class** [[eos_ai-tenant-py-TenantContext]] — 0 methods
- **class** [[eos_ai-tenant-py-TenantManager]] — 5 methods

## Import Statements

```python
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
```
