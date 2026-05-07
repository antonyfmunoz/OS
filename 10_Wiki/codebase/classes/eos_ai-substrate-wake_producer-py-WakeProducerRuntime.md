---
type: codebase-class
file: eos_ai/substrate/wake_producer.py
line: 214
generated: 2026-05-07
---

# WakeProducerRuntime

**File:** [[eos_ai-substrate-wake_producer-py]] | **Line:** 214

Bounded wake producer runtime.

TODO / provider seam:
    Real wake-word engines (Porcupine, openWakeWord) and real clap
    detectors plug in here as *producers* that call `submit(...)` with
...

## Methods

- [[eos_ai-substrate-wake_producer-py-WakeProducerRuntime-__init__]]`(listener, voice_runtime, history) → None` — 
- [[eos_ai-substrate-wake_producer-py-WakeProducerRuntime-simulate_wake_word]]`(node_id, phrase, confidence, metadata, issued_by) → WakeProducerEvent` — 
- [[eos_ai-substrate-wake_producer-py-WakeProducerRuntime-simulate_clap]]`(node_id, confidence, metadata, issued_by) → WakeProducerEvent` — 
- [[eos_ai-substrate-wake_producer-py-WakeProducerRuntime-submit]]`(event) → WakeProducerEvent` — Dispatch a wake producer event. Never raises.
- [[eos_ai-substrate-wake_producer-py-WakeProducerRuntime-_handle_wake_word]]`(event) → None` — 
- [[eos_ai-substrate-wake_producer-py-WakeProducerRuntime-_handle_clap]]`(event) → None` — 
- [[eos_ai-substrate-wake_producer-py-WakeProducerRuntime-report]]`(node_id, limit) → dict` — 
