---
type: codebase-file
path: eos_ai/substrate/advisor_session_contracts.py
module: eos_ai.substrate.advisor_session_contracts
lines: 161
size: 5112
generated: 2026-05-07
---

# eos_ai/substrate/advisor_session_contracts.py

Advisor session contracts for Phase 94D.3.

Additive-only module. Defines the state model and event types for the
central advisor session — the founder-facing command/intelligence layer.

...

**Lines:** 161 | **Size:** 5,112 bytes

## Contains

- **class** [[eos_ai-substrate-advisor_session_contracts-py-AdvisorSessionState]] — 0 methods
- **class** [[eos_ai-substrate-advisor_session_contracts-py-AdvisorEventKind]] — 0 methods
- **class** [[eos_ai-substrate-advisor_session_contracts-py-AdvisorSessionEvent]] — 2 methods
- **class** [[eos_ai-substrate-advisor_session_contracts-py-AdvisorSessionCommand]] — 2 methods
- **class** [[eos_ai-substrate-advisor_session_contracts-py-PendingApproval]] — 2 methods
- **fn** [[eos_ai-substrate-advisor_session_contracts-py-_new_id]]`() → str`
- **fn** [[eos_ai-substrate-advisor_session_contracts-py-_now_iso]]`() → str`

## Import Statements

```python
from __future__ import annotations
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
```
