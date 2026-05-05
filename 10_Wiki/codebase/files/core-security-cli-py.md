---
type: codebase-file
path: core/security/cli.py
module: core.security.cli
lines: 288
size: 9255
tags: [entry-point]
generated: 2026-04-12
---

# core/security/cli.py

> **ENTRY POINT** — Contains `if __name__` or server start.

cli.py — Operator CLI for the EOS security layer.

Usage
-----
    python3 -m core.security.cli user create <id> --role operator
...

**Lines:** 288 | **Size:** 9,255 bytes

## Depends On

- [[core-security-approval-py]]
- [[core-security-audit-py]]
- [[core-security-context-py]]
- [[core-security-environments-py]]
- [[core-security-identity-py]]
- [[core-security-rbac-py]]

## Contains

- **fn** [[core-security-cli-py-cmd_user_create]]`(args) → int`
- **fn** [[core-security-cli-py-cmd_user_list]]`(_) → int`
- **fn** [[core-security-cli-py-cmd_user_disable]]`(args) → int`
- **fn** [[core-security-cli-py-cmd_user_role]]`(args) → int`
- **fn** [[core-security-cli-py-cmd_user_auth]]`(args) → int`
- **fn** [[core-security-cli-py-cmd_role_list]]`(_) → int`
- **fn** [[core-security-cli-py-cmd_approval_list]]`(_) → int`
- **fn** [[core-security-cli-py-cmd_approval_show]]`(args) → int`
- **fn** [[core-security-cli-py-cmd_approval_approve]]`(args) → int`
- **fn** [[core-security-cli-py-cmd_approval_reject]]`(args) → int`
- **fn** [[core-security-cli-py-cmd_audit_tail]]`(args) → int`
- **fn** [[core-security-cli-py-cmd_audit_verify]]`(_) → int`
- **fn** [[core-security-cli-py-cmd_env_show]]`(args) → int`
- **fn** [[core-security-cli-py-build_parser]]`() → argparse.ArgumentParser`
- **fn** [[core-security-cli-py-main]]`(argv) → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from core.security.approval import ApprovalQueue
from core.security.audit import AuditLog
from core.security.context import SecurityContext
from core.security.environments import env_for_name
from core.security.identity import AuthError
from core.security.identity import IdentityStore
from core.security.rbac import RBACEngine
from core.security.rbac import RoleName
```
