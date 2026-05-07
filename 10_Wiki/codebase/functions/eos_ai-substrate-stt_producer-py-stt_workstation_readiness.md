---
type: codebase-function
file: eos_ai/substrate/stt_producer.py
line: 456
generated: 2026-05-07
---

# stt_workstation_readiness

**File:** [[eos_ai-substrate-stt_producer-py]] | **Line:** 456
**Signature:** `stt_workstation_readiness() → dict[str, Any]`

Operator-facing readiness summary for real push-to-talk.

Answers the question: "If I press PTT right now on this workstation,
what will happen, and if it won't work — what should I do?"

...

## Calls

- [[eos_ai-substrate-stt_producer-py-SttCaptureEvent-as_dict]]
- [[eos_ai-substrate-stt_producer-py-SttRuntimeCapability-as_dict]]
- [[eos_ai-substrate-stt_producer-py-_detect_environment]]
- [[eos_ai-substrate-stt_producer-py-_enumerate_input_devices]]
- [[eos_ai-substrate-stt_producer-py-_env_flag]]
- [[eos_ai-substrate-stt_producer-py-_probe_capability]]
- [[eos_ai-substrate-stt_producer-py-_utcnow_iso]]

## Called By

- [[eos_ai-substrate-stt_producer-py-stt_runtime_status]]
- [[scripts-substrate_ptt_binding_smoke_test-py-main]]
