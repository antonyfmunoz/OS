---
type: codebase-function
file: eos_ai/substrate/stt_producer.py
line: 1095
generated: 2026-04-12
---

# stt_capture_snapshot

**File:** [[eos_ai-substrate-stt_producer-py]] | **Line:** 1095
**Signature:** `stt_capture_snapshot(node_id) → dict[str, Any]`

Return the most recent capture event per node as a JSON-friendly dict.

If node_id is given, only events for that node are considered.

## Calls

- [[eos_ai-substrate-stt_producer-py-SttCaptureEvent-as_dict]]
- [[eos_ai-substrate-stt_producer-py-SttCaptureHistory-latest]]
- [[eos_ai-substrate-stt_producer-py-SttRuntimeCapability-as_dict]]
- [[eos_ai-substrate-stt_producer-py-_utcnow_iso]]
- [[eos_ai-substrate-stt_producer-py-get_stt_capture_history]]

## Called By

- [[scripts-substrate_stt_producer_smoke_test-py-main]]
