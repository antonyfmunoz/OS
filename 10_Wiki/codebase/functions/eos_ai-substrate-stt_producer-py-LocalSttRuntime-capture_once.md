---
type: codebase-function
file: eos_ai/substrate/stt_producer.py
line: 707
generated: 2026-04-12
---

# LocalSttRuntime.capture_once

**File:** [[eos_ai-substrate-stt_producer-py]] | **Line:** 707
**Signature:** `capture_once(node_id) → SttCaptureEvent`

**Class:** [[eos_ai-substrate-stt_producer-py-LocalSttRuntime]]

Perform one bounded capture. Never raises.

Returns a recorded SttCaptureEvent. The event is pushed into
SttCaptureHistory regardless of outcome.

...

## Calls

- [[eos_ai-substrate-stt_producer-py-LocalSttRuntime-_inject_and_record]]
- [[eos_ai-substrate-stt_producer-py-LocalSttRuntime-_record_and_return]]
- [[eos_ai-substrate-stt_producer-py-LocalSttRuntime-_record_mic]]
- [[eos_ai-substrate-stt_producer-py-LocalSttRuntime-_transcribe]]
- [[eos_ai-substrate-stt_producer-py-SttCaptureEvent-as_dict]]
- [[eos_ai-substrate-stt_producer-py-SttRuntimeCapability-as_dict]]
- [[eos_ai-substrate-stt_producer-py-_env_flag]]
- [[eos_ai-substrate-stt_producer-py-_env_float]]
- [[eos_ai-substrate-stt_producer-py-_env_int]]
- [[eos_ai-substrate-stt_producer-py-_env_str]]
- [[eos_ai-substrate-stt_producer-py-_probe_capability]]
- [[eos_ai-substrate-stt_producer-py-_validate_audio_quality]]

## Called By

- [[scripts-substrate_stt_producer_smoke_test-py-main]]
