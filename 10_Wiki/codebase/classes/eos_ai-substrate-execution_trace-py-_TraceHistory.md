---
type: codebase-class
file: eos_ai/substrate/execution_trace.py
line: 202
generated: 2026-04-12
---

# _TraceHistory

**File:** [[eos_ai-substrate-execution_trace-py]] | **Line:** 202

Thread-safe in-memory ring buffer of finalized traces.

## Methods

- [[eos_ai-substrate-execution_trace-py-_TraceHistory-__init__]]`(maxlen) → None` — 
- [[eos_ai-substrate-execution_trace-py-_TraceHistory-record]]`(trace) → None` — Append a finalized trace to the ring buffer.
- [[eos_ai-substrate-execution_trace-py-_TraceHistory-latest]]`(limit) → list[dict]` — Return the most recent *limit* traces (newest last).
- [[eos_ai-substrate-execution_trace-py-_TraceHistory-by_mode]]`(mode, limit) → list[dict]` — Return recent traces filtered by mode.
- [[eos_ai-substrate-execution_trace-py-_TraceHistory-by_session]]`(session_name, limit) → list[dict]` — Return recent traces filtered by session_name.
- [[eos_ai-substrate-execution_trace-py-_TraceHistory-by_provider]]`(provider, limit) → list[dict]` — Return recent traces filtered by provider.
- [[eos_ai-substrate-execution_trace-py-_TraceHistory-by_execution_path]]`(path, limit) → list[dict]` — Return recent traces filtered by execution_path.
- [[eos_ai-substrate-execution_trace-py-_TraceHistory-clear]]`() → None` — Empty the buffer.
