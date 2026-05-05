---
type: codebase-file
path: core/security/environments.py
module: core.security.environments
lines: 227
size: 7548
generated: 2026-04-12
---

# core/security/environments.py

environments.py — Environment policy layer for the security module.

`core.environment` already provides full prod/sandbox/playground
isolation with path resolution, copy-on-write workspaces, and a
forbidden-writes list. This module adds the *policy* wrapper:
...

**Lines:** 227 | **Size:** 7,548 bytes

## Depends On

- [[core-capability-py]]
- [[core-environment-py]]

## Used By

- [[core-security-cli-py]]
- [[scripts-security_smoke_test-py]]

## Contains

- **class** [[core-security-environments-py-EnvironmentPolicy]] — 0 methods
- **class** [[core-security-environments-py-SecurityEnv]] — 9 methods
- **fn** [[core-security-environments-py-env_for_name]]`(name) → SecurityEnv`
- **fn** [[core-security-environments-py-wrap_environment]]`(env) → SecurityEnv`
- **fn** [[core-security-environments-py-_canon_tier]]`(name) → EnvTier`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
from core.capability import RiskTier
from core.capability import coerce_risk
from core.environment import Environment
from core.environment import EnvMode
from core.environment import make_playground
from core.environment import make_sandbox
```
