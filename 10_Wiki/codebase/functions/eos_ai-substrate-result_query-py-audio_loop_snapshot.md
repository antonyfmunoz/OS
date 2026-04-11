---
type: codebase-function
file: eos_ai/substrate/result_query.py
line: 378
generated: 2026-04-11
---

# audio_loop_snapshot

**File:** [[eos_ai-substrate-result_query-py]] | **Line:** 378
**Signature:** `audio_loop_snapshot(node_id) → dict[str, Any]`

Bounded audio loop view for a node (or all nodes if node_id is None).

Read-only. JSON-friendly. Best-effort — returns an empty shape on
failure so callers don't need to wrap. Reports local interaction
window status, last primed/transcript/response timestamps, last
...

## Called By

- [[scripts-substrate_audio_loop_smoke_test-py-main]]
