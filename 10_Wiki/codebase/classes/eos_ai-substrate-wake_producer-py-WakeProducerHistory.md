---
type: codebase-class
file: eos_ai/substrate/wake_producer.py
line: 160
generated: 2026-05-07
---

# WakeProducerHistory

**File:** [[eos_ai-substrate-wake_producer-py]] | **Line:** 160

Bounded persistent history of wake producer events.

Mirrors TriggerHistory exactly: substrate KV, ring buffer at RETENTION_MAX,
thread-safe, best-effort.

## Methods

- [[eos_ai-substrate-wake_producer-py-WakeProducerHistory-__init__]]`() → None` — 
- [[eos_ai-substrate-wake_producer-py-WakeProducerHistory-_load]]`() → list[dict]` — 
- [[eos_ai-substrate-wake_producer-py-WakeProducerHistory-_save]]`(events) → None` — 
- [[eos_ai-substrate-wake_producer-py-WakeProducerHistory-record]]`(event) → None` — 
- [[eos_ai-substrate-wake_producer-py-WakeProducerHistory-latest]]`(limit, node_id) → list[dict]` — 
- [[eos_ai-substrate-wake_producer-py-WakeProducerHistory-clear]]`() → None` — 
