---
type: codebase-class
file: eos_ai/substrate/stt_producer.py
line: 597
generated: 2026-05-07
---

# SttCaptureHistory

**File:** [[eos_ai-substrate-stt_producer-py]] | **Line:** 597

Thread-safe ring buffer for SttCaptureEvent, mirrors WakeProducerHistory.

## Methods

- [[eos_ai-substrate-stt_producer-py-SttCaptureHistory-__init__]]`() → None` — 
- [[eos_ai-substrate-stt_producer-py-SttCaptureHistory-_load]]`() → None` — 
- [[eos_ai-substrate-stt_producer-py-SttCaptureHistory-_flush]]`() → None` — 
- [[eos_ai-substrate-stt_producer-py-SttCaptureHistory-record]]`(event) → SttCaptureEvent` — 
- [[eos_ai-substrate-stt_producer-py-SttCaptureHistory-latest]]`(limit, node_id) → list[SttCaptureEvent]` — 
- [[eos_ai-substrate-stt_producer-py-SttCaptureHistory-clear]]`() → None` — 
