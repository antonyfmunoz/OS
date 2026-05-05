---
type: codebase-function
file: eos_ai/substrate/wake_producer.py
line: 274
generated: 2026-04-12
---

# WakeProducerRuntime.submit

**File:** [[eos_ai-substrate-wake_producer-py]] | **Line:** 274
**Signature:** `submit(event) → WakeProducerEvent`

**Class:** [[eos_ai-substrate-wake_producer-py-WakeProducerRuntime]]

Dispatch a wake producer event. Never raises.

## Calls

- [[eos_ai-substrate-local_listener-py-TriggerHistory-record]]
- [[eos_ai-substrate-local_listener-py-_log]]
- [[eos_ai-substrate-storage-py-_log]]
- [[eos_ai-substrate-voice_session-py-_log]]
- [[eos_ai-substrate-wake_producer-py-WakeProducerHistory-record]]
- [[eos_ai-substrate-wake_producer-py-WakeProducerRuntime-_handle_clap]]
- [[eos_ai-substrate-wake_producer-py-WakeProducerRuntime-_handle_wake_word]]
- [[eos_ai-substrate-wake_producer-py-_log]]

## Called By

- [[eos_ai-substrate-wake_producer-py-WakeProducerRuntime-simulate_clap]]
- [[eos_ai-substrate-wake_producer-py-WakeProducerRuntime-simulate_wake_word]]
