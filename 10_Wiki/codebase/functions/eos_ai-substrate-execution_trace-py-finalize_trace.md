---
type: codebase-function
file: eos_ai/substrate/execution_trace.py
line: 141
generated: 2026-04-12
---

# finalize_trace

**File:** [[eos_ai-substrate-execution_trace-py]] | **Line:** 141
**Signature:** `finalize_trace(trace, provider, model, latency_ms, result) → dict`

Finalize a trace after the request lifecycle completes.

Sets provider/model/result/latency and stamps ``finalized_at``.

Args:
...

## Called By

- [[core-execution_contract-py-run_task]]
