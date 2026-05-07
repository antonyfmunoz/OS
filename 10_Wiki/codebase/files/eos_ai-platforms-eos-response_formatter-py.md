---
type: codebase-file
path: eos_ai/platforms/eos/response_formatter.py
module: eos_ai.platforms.eos.response_formatter
lines: 270
size: 8548
generated: 2026-05-07
---

# eos_ai/platforms/eos/response_formatter.py

Response formatter — owns ALL text shaping for founder-facing EOS output.

Takes structured context dicts ({meta, state, insights, suggestions}) and
EAResponse data, produces founder-facing text.  No other module in the
platform layer produces user-facing text.
...

**Lines:** 270 | **Size:** 8,548 bytes

## Depends On

- [[eos_ai-platforms-eos-roles-py]]

## Used By

- [[eos_ai-platforms-eos-ea_orchestrator-py]]

## Contains

- **fn** [[eos_ai-platforms-eos-response_formatter-py-format_briefing]]`(context) → str`
- **fn** [[eos_ai-platforms-eos-response_formatter-py-format_strategic_recommendation]]`(context) → str`
- **fn** [[eos_ai-platforms-eos-response_formatter-py-format_portfolio_recommendation]]`(context) → str`
- **fn** [[eos_ai-platforms-eos-response_formatter-py-format_execution_summary]]`() → str`
- **fn** [[eos_ai-platforms-eos-response_formatter-py-format_blocked_decision_summary]]`(blocked_titles) → str`
- **fn** [[eos_ai-platforms-eos-response_formatter-py-format_ea_response]]`() → str`

## Import Statements

```python
from __future__ import annotations
from typing import Any
from typing import Optional
from eos_ai.platforms.eos.roles import EOSRole
```
