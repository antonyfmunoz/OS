---
type: codebase-file
path: eos_ai/platforms/eos/intent_routing.py
module: eos_ai.platforms.eos.intent_routing
lines: 236
size: 8422
generated: 2026-05-07
---

# eos_ai/platforms/eos/intent_routing.py

Founder intent parsing — deterministic classification of founder messages.

Classifies raw founder text into intent types and suggests which EOS role
should handle it.  All classification is keyword-based — zero LLM cost.
The founder never directly addresses CEO or Portfolio Advisor; the parser
...

**Lines:** 236 | **Size:** 8,422 bytes

## Depends On

- [[eos_ai-platforms-eos-roles-py]]

## Used By

- [[eos_ai-platforms-eos-delegation-py]]
- [[eos_ai-platforms-eos-ea_orchestrator-py]]

## Contains

- **class** [[eos_ai-platforms-eos-intent_routing-py-FounderIntentType]] — 0 methods
- **class** [[eos_ai-platforms-eos-intent_routing-py-FounderIntent]] — 2 methods
- **fn** [[eos_ai-platforms-eos-intent_routing-py-_extract_directives]]`(text) → list[str]`
- **fn** [[eos_ai-platforms-eos-intent_routing-py-_utcnow]]`() → str`
- **fn** [[eos_ai-platforms-eos-intent_routing-py-_new_id]]`() → str`
- **fn** [[eos_ai-platforms-eos-intent_routing-py-parse_founder_intent]]`(text) → FounderIntent`

## Import Statements

```python
from __future__ import annotations
import re
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from eos_ai.platforms.eos.roles import EOSRole
```
