---
type: codebase-class
file: eos_ai/substrate/stt_producer.py
line: 688
generated: 2026-04-12
---

# LocalSttRuntime

**File:** [[eos_ai-substrate-stt_producer-py]] | **Line:** 688

Bounded local STT capture runtime.

Three capture modes:
    capture_once(..., simulated_text=...)     → SIMULATED_STT
    capture_once(..., mode="manual", text=)   → MANUAL_CAPTURE
...

## Methods

- [[eos_ai-substrate-stt_producer-py-LocalSttRuntime-__init__]]`(default_duration_s, default_sample_rate) → None` — 
- [[eos_ai-substrate-stt_producer-py-LocalSttRuntime-capture_once]]`(node_id) → SttCaptureEvent` — Perform one bounded capture. Never raises.
- [[eos_ai-substrate-stt_producer-py-LocalSttRuntime-_record_mic]]`(duration_s, sample_rate)` — Record `duration_s` of mono audio. Bounded and timeout-guarded.
- [[eos_ai-substrate-stt_producer-py-LocalSttRuntime-_transcribe]]`(audio, sample_rate, providers_available) → tuple[str, Optional[float], Optional[str]]` — Transcribe recorded int16 mono audio. Lazy import of provider.
- [[eos_ai-substrate-stt_producer-py-LocalSttRuntime-_inject_and_record]]`(event) → SttCaptureEvent` — Push event.text into the voice loop via inject_transcript.
- [[eos_ai-substrate-stt_producer-py-LocalSttRuntime-_record_and_return]]`(event) → SttCaptureEvent` — 
