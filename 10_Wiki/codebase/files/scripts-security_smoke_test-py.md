---
type: codebase-file
path: scripts/security_smoke_test.py
module: scripts.security_smoke_test
lines: 503
size: 16080
tags: [entry-point]
generated: 2026-05-07
---

# scripts/security_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

security_smoke_test.py — End-to-end smoke test for core.security.

Runs against a temp data dir so it never touches production state.
Covers:

...

**Lines:** 503 | **Size:** 16,080 bytes

## Depends On

- [[core-capability-py]]
- [[core-security-approval-py]]
- [[core-security-audit-py]]
- [[core-security-context-py]]
- [[core-security-environments-py]]
- [[core-security-execution-py]]
- [[core-security-identity-py]]
- [[core-security-rbac-py]]

## Contains

- **class** [[scripts-security_smoke_test-py-SmokeFail]] — 1 methods
- **fn** [[scripts-security_smoke_test-py-assert_eq]]`(actual, expected, label) → None`
- **fn** [[scripts-security_smoke_test-py-assert_true]]`(cond, label) → None`
- **fn** [[scripts-security_smoke_test-py-step]]`(name) → None`
- **fn** [[scripts-security_smoke_test-py-test_identity]]`(tmp) → None`
- **fn** [[scripts-security_smoke_test-py-test_rbac]]`() → None`
- **fn** [[scripts-security_smoke_test-py-test_approval_queue]]`(tmp) → None`
- **fn** [[scripts-security_smoke_test-py-test_audit]]`(tmp) → None`
- **fn** [[scripts-security_smoke_test-py-test_execution]]`(tmp) → None`
- **fn** [[scripts-security_smoke_test-py-test_security_context]]`(tmp) → None`
- **fn** [[scripts-security_smoke_test-py-test_action_system_integration]]`(tmp) → None`
- **fn** [[scripts-security_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from core.capability import OperationKind
from core.capability import RiskTier
from core.security.approval import ApprovalError
from core.security.approval import ApprovalQueue
from core.security.approval import ApprovalStatus
from core.security.audit import AuditLog
from core.security.context import SecurityContext
from core.security.environments import env_for_name
from core.security.execution import ExecutionContext
from core.security.execution import ExecutionDenied
from core.security.execution import RestrictedExecutor
from core.security.identity import AuthError
from core.security.identity import IdentityStore
from core.security.rbac import RBACEngine
from core.security.rbac import RoleName
```
