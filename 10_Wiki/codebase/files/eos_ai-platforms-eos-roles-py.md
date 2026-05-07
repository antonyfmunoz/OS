---
type: codebase-file
path: eos_ai/platforms/eos/roles.py
module: eos_ai.platforms.eos.roles
lines: 127
size: 4343
generated: 2026-05-07
---

# eos_ai/platforms/eos/roles.py

EOS platform roles — domain-specific business roles projected onto the substrate.

These are EOS-level roles used for founder intent routing, delegation, and
response formatting.  They are NOT substrate roles (those live in
eos_ai/substrate/roles.py).  The mapping between platform roles and substrate
...

**Lines:** 127 | **Size:** 4,343 bytes

## Used By

- [[eos_ai-platforms-eos-context_builder-py]]
- [[eos_ai-platforms-eos-delegation-py]]
- [[eos_ai-platforms-eos-discord_hook-py]]
- [[eos_ai-platforms-eos-ea_orchestrator-py]]
- [[eos_ai-platforms-eos-intent_routing-py]]
- [[eos_ai-platforms-eos-response_formatter-py]]

## Contains

- **class** [[eos_ai-platforms-eos-roles-py-EOSRole]] — 0 methods
- **fn** [[eos_ai-platforms-eos-roles-py-get_role_meta]]`(role) → dict[str, Any]`
- **fn** [[eos_ai-platforms-eos-roles-py-get_all_roles]]`() → list[dict[str, Any]]`
- **fn** [[eos_ai-platforms-eos-roles-py-is_founder_facing]]`(role) → bool`
- **fn** [[eos_ai-platforms-eos-roles-py-substrate_slug]]`(role) → str`

## Import Statements

```python
from __future__ import annotations
from enum import Enum
from typing import Any
```
