---
type: codebase-file
path: eos_ai/substrate/roles.py
module: eos_ai.substrate.roles
lines: 156
size: 5496
generated: 2026-04-12
---

# eos_ai/substrate/roles.py

Agent role abstraction — clean contract for multi-agent orchestration.

EOS already has agent_hierarchy.py, which encodes the org chart for prompt
injection. This module does NOT replace it. It adds a complementary,
routing-friendly `AgentRole` abstraction that captures:
...

**Lines:** 156 | **Size:** 5,496 bytes

## Used By

- [[eos_ai-substrate-role_resolver-py]]
- [[eos_ai-substrate-voice_session-py]]

## Contains

- **class** [[eos_ai-substrate-roles-py-RoleScope]] — 0 methods
- **class** [[eos_ai-substrate-roles-py-AgentRole]] — 2 methods
- **class** [[eos_ai-substrate-roles-py-RoleRegistry]] — 5 methods

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Optional
```
