---
type: codebase-file
path: core/security/identity.py
module: core.security.identity
lines: 401
size: 13847
generated: 2026-04-12
---

# core/security/identity.py

identity.py — User model and token-based authentication.

Scope
-----
Single-tenant founder-phase OS. No OAuth, no external IdP, no LDAP.
...

**Lines:** 401 | **Size:** 13,847 bytes

## Used By

- [[core-security-cli-py]]
- [[scripts-security_smoke_test-py]]

## Contains

- **class** [[core-security-identity-py-AuthError]] — 0 methods
- **class** [[core-security-identity-py-User]] — 2 methods
- **class** [[core-security-identity-py-Token]] — 1 methods
- **class** [[core-security-identity-py-IdentityStore]] — 14 methods
- **fn** [[core-security-identity-py-_b64url_encode]]`(b) → str`
- **fn** [[core-security-identity-py-_b64url_decode]]`(s) → bytes`
- **fn** [[core-security-identity-py-_hash_api_key]]`(raw) → str`

## Import Statements

```python
from __future__ import annotations
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Iterable
```
