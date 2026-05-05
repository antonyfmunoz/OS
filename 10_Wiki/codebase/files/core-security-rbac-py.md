---
type: codebase-file
path: core/security/rbac.py
module: core.security.rbac
lines: 304
size: 9415
generated: 2026-04-12
---

# core/security/rbac.py

rbac.py — Role-based access control on top of core.capability.

Design decision
---------------
`core.capability` already has `CapabilityProfile` + `CapabilityEnforcer`
...

**Lines:** 304 | **Size:** 9,415 bytes

## Depends On

- [[core-capability-py]]

## Used By

- [[core-security-cli-py]]
- [[scripts-security_smoke_test-py]]

## Contains

- **class** [[core-security-rbac-py-RoleName]] — 0 methods
- **class** [[core-security-rbac-py-Role]] — 1 methods
- **class** [[core-security-rbac-py-RBACCheck]] — 0 methods
- **class** [[core-security-rbac-py-RBACEngine]] — 6 methods
- **fn** [[core-security-rbac-py-_role]]`(name, cap, auto_risk, authority) → Role`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Iterable
from core.capability import Capability
from core.capability import OperationKind
from core.capability import RiskTier
from core.capability import cap_implies
from core.capability import coerce_risk
from core.capability import required_capability
```
