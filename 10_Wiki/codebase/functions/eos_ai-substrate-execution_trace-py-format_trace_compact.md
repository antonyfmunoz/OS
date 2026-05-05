---
type: codebase-function
file: eos_ai/substrate/execution_trace.py
line: 179
generated: 2026-04-12
---

# format_trace_compact

**File:** [[eos_ai-substrate-execution_trace-py]] | **Line:** 179
**Signature:** `format_trace_compact(trace) → str`

Return a one-line human-readable summary of a trace.

Format:
    [trace_id[:8]] mode→target | exec_path | provider/model | result | latency_ms
