---
type: codebase-file
path: eos_ai/platforms/eos/ea_orchestrator.py
module: eos_ai.platforms.eos.ea_orchestrator
lines: 346
size: 11386
generated: 2026-05-07
---

# eos_ai/platforms/eos/ea_orchestrator.py

EA Orchestrator — main entrypoint for the EOS platform layer.

All founder messages enter through handle_founder_message().  EA parses
intent, builds context, decides whether to handle directly or delegate to
CEO / Portfolio Advisor, creates substrate work if needed, and returns
...

**Lines:** 346 | **Size:** 11,386 bytes

## Depends On

- [[eos_ai-platforms-eos-context_builder-py]]
- [[eos_ai-platforms-eos-decision_log-py]]
- [[eos_ai-platforms-eos-delegation-py]]
- [[eos_ai-platforms-eos-intent_routing-py]]
- [[eos_ai-platforms-eos-response_formatter-py]]
- [[eos_ai-platforms-eos-roles-py]]

## Used By

- [[eos_ai-platforms-eos-discord_hook-py]]

## Contains

- **class** [[eos_ai-platforms-eos-ea_orchestrator-py-EAResponse]] — 1 methods
- **fn** [[eos_ai-platforms-eos-ea_orchestrator-py-_log]]`(msg) → None`
- **fn** [[eos_ai-platforms-eos-ea_orchestrator-py-_utcnow]]`() → str`
- **fn** [[eos_ai-platforms-eos-ea_orchestrator-py-_new_id]]`() → str`
- **fn** [[eos_ai-platforms-eos-ea_orchestrator-py-_create_substrate_task]]`(text) → Optional[str]`
- **fn** [[eos_ai-platforms-eos-ea_orchestrator-py-_get_blocked_task_titles]]`() → list[str]`
- **fn** [[eos_ai-platforms-eos-ea_orchestrator-py-_handle_status]]`(intent) → EAResponse`
- **fn** [[eos_ai-platforms-eos-ea_orchestrator-py-_handle_review]]`(intent) → EAResponse`
- **fn** [[eos_ai-platforms-eos-ea_orchestrator-py-_handle_execution]]`(intent) → EAResponse`
- **fn** [[eos_ai-platforms-eos-ea_orchestrator-py-_handle_strategy]]`(intent) → EAResponse`
- **fn** [[eos_ai-platforms-eos-ea_orchestrator-py-_handle_portfolio]]`(intent) → EAResponse`
- **fn** [[eos_ai-platforms-eos-ea_orchestrator-py-_handle_direct_ea]]`(intent) → EAResponse`
- **fn** [[eos_ai-platforms-eos-ea_orchestrator-py-handle_founder_message]]`(text) → EAResponse`

## Import Statements

```python
from __future__ import annotations
import sys
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Optional
from eos_ai.platforms.eos.context_builder import build_context_for_role
from eos_ai.platforms.eos.context_builder import build_ea_context
from eos_ai.platforms.eos.decision_log import DecisionLog
from eos_ai.platforms.eos.decision_log import EOSDecisionRecord
from eos_ai.platforms.eos.delegation import choose_delegate
from eos_ai.platforms.eos.delegation import should_delegate
from eos_ai.platforms.eos.intent_routing import FounderIntent
from eos_ai.platforms.eos.intent_routing import FounderIntentType
from eos_ai.platforms.eos.intent_routing import parse_founder_intent
from eos_ai.platforms.eos.response_formatter import format_ea_response
from eos_ai.platforms.eos.roles import EOSRole
```
