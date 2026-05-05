---
type: codebase-class
file: eos_ai/substrate/local_listener.py
line: 123
generated: 2026-04-12
---

# TriggerHistory

**File:** [[eos_ai-substrate-local_listener-py]] | **Line:** 123

Bounded persistent history of trigger events.

Backed by the existing substrate storage key/value layer (Neon → JSON file
fallback). Ring-buffered: oldest events drop at RETENTION_MAX.

## Methods

- [[eos_ai-substrate-local_listener-py-TriggerHistory-__init__]]`() → None` — 
- [[eos_ai-substrate-local_listener-py-TriggerHistory-_load]]`() → list[dict]` — 
- [[eos_ai-substrate-local_listener-py-TriggerHistory-_save]]`(events) → None` — 
- [[eos_ai-substrate-local_listener-py-TriggerHistory-record]]`(trigger) → None` — 
- [[eos_ai-substrate-local_listener-py-TriggerHistory-latest]]`(limit, node_id) → list[dict]` — 
- [[eos_ai-substrate-local_listener-py-TriggerHistory-clear]]`() → None` — 
