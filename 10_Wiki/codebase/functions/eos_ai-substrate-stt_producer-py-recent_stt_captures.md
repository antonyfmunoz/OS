---
type: codebase-function
file: eos_ai/substrate/stt_producer.py
line: 1121
generated: 2026-04-12
---

# recent_stt_captures

**File:** [[eos_ai-substrate-stt_producer-py]] | **Line:** 1121
**Signature:** `recent_stt_captures(limit, node_id) → list[dict[str, Any]]`

Return recent capture events as JSON-friendly dicts (newest-first).

## Calls

- [[eos_ai-substrate-stt_producer-py-SttCaptureEvent-as_dict]]
- [[eos_ai-substrate-stt_producer-py-SttCaptureHistory-latest]]
- [[eos_ai-substrate-stt_producer-py-SttRuntimeCapability-as_dict]]
- [[eos_ai-substrate-stt_producer-py-get_stt_capture_history]]

## Called By

- [[scripts-substrate_stt_producer_smoke_test-py-main]]
