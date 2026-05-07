---
type: codebase-function
file: eos_ai/substrate/result_query.py
line: 398
generated: 2026-05-07
---

# recent_audio_loop_transcripts

**File:** [[eos_ai-substrate-result_query-py]] | **Line:** 398
**Signature:** `recent_audio_loop_transcripts(node_id, limit) → list[dict]`

Most recent transcript entries for a node's audio loop, newest-first.

JSON-friendly. Bounded. Read-only view over the inline transcript ring
buffer held on AudioLoopState.

## Calls

- [[eos_ai-substrate-result_store-py-IngestedResult-as_dict]]
- [[eos_ai-substrate-result_store-py-ResultStore-get]]

## Called By

- [[scripts-substrate_audio_loop_smoke_test-py-main]]
