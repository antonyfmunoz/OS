---
type: codebase-file
path: core/security/context.py
module: core.security.context
lines: 642
size: 22025
generated: 2026-05-07
---

# core/security/context.py

context.py — SecurityContext facade.

Single entry point that composes identity + RBAC + approval +
environment-policy + audit into one call:

...

**Lines:** 642 | **Size:** 22,025 bytes

## Depends On

- [[core-capability-py]]

## Used By

- [[core-security-cli-py]]
- [[scripts-security_smoke_test-py]]

## Contains

- **class** [[core-security-context-py-AuthorizationDecision]] — 4 methods
- **class** [[core-security-context-py-SecurityContext]] — 11 methods
- **fn** [[core-security-context-py-_chain_entry]]`(request, decided) → dict`

## Import Statements

```python
from __future__ import annotations
import time
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Literal
from core.capability import OperationKind
from core.capability import RiskTier
from core.capability import coerce_risk
from approval import ApprovalError
from approval import ApprovalQueue
from approval import ApprovalRequest
from approval import ApprovalStatus
from audit import AuditEvent
from audit import AuditLog
from environments import SecurityEnv
from environments import env_for_name
from environments import wrap_environment
from execution import ExecutionContext
from identity import AuthError
from identity import IdentityStore
from identity import Token
from rbac import RBACEngine
from rbac import RoleName
```
