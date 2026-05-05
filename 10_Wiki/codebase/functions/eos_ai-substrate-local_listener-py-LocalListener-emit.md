---
type: codebase-function
file: eos_ai/substrate/local_listener.py
line: 191
generated: 2026-04-12
---

# LocalListener.emit

**File:** [[eos_ai-substrate-local_listener-py]] | **Line:** 191
**Signature:** `emit(trigger) → LocalTrigger`

**Class:** [[eos_ai-substrate-local_listener-py-LocalListener]]

Emit a trigger and attempt activation. Always returns the trigger
with status/decision_reason filled in. Never raises.

## Calls

- [[eos_ai-substrate-local_listener-py-LocalListener-_activate]]
- [[eos_ai-substrate-local_listener-py-TriggerHistory-record]]
- [[eos_ai-substrate-local_listener-py-_log]]
- [[eos_ai-substrate-ritual_body-py-_log]]
- [[eos_ai-substrate-storage-py-_log]]

## Called By

- [[eos_ai-substrate-local_listener-py-LocalListener-hotkey_activate]]
- [[eos_ai-substrate-local_listener-py-LocalListener-manual_activate]]
- [[eos_ai-substrate-local_listener-py-LocalListener-simulate_clap]]
- [[eos_ai-substrate-local_listener-py-LocalListener-simulate_wake_word]]
- [[eos_ai-substrate-wake_producer-py-WakeProducerRuntime-_handle_clap]]
- [[scripts-substrate_local_listener-py-main]]
