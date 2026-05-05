---
type: codebase-file
path: core/action_system/policy.py
module: core.action_system.policy
lines: 165
size: 6077
generated: 2026-04-12
---

# core/action_system/policy.py

Policy bridge between the Control Plane and `eos_ai.authority_engine`.

Two governance systems coexist in EOS and they speak different dialects:

- `eos_ai/authority_engine.py` governs *business* actions (`send_dm`,
...

**Lines:** 165 | **Size:** 6,077 bytes

## Contains

- **fn** [[core-action_system-policy-py-normalize_risk]]`(value) → RiskLevel`
- **fn** [[core-action_system-policy-py-map_to_authority_class]]`(risk) → str`
- **fn** [[core-action_system-policy-py-required_autonomy_level]]`(risk) → int`
- **fn** [[core-action_system-policy-py-requires_explicit_approval]]`(risk) → bool`
- **fn** [[core-action_system-policy-py-blocks_auto_execute]]`(risk) → bool`
- **fn** [[core-action_system-policy-py-authority_classify]]`(business_action_type) → Optional[RiskLevel]`
- **fn** [[core-action_system-policy-py-resolve_effective_risk]]`(declared_risk, business_action_type) → RiskLevel`

## Import Statements

```python
from __future__ import annotations
from typing import Literal
from typing import Optional
```
