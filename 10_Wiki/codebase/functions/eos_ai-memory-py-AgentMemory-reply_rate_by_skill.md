---
type: codebase-function
file: eos_ai/memory.py
line: 634
generated: 2026-04-11
---

# AgentMemory.reply_rate_by_skill

**File:** [[eos_ai-memory-py]] | **Line:** 634
**Signature:** `reply_rate_by_skill() → list[dict]`

**Class:** [[eos_ai-memory-py-AgentMemory]]

RLHF aggregate: reply rate per skill, sorted by reply_rate desc.

## Calls

- [[eos_ai-db-py-get_conn]]

## Called By

- [[eos_ai-status-py-_fetch_reply_rates]]
