---
type: codebase-function
file: eos_ai/substrate/execution_trace.py
line: 287
generated: 2026-05-07
---

# trace_context

**File:** [[eos_ai-substrate-execution_trace-py]] | **Line:** 287
**Signature:** `trace_context(trace) → Generator[dict, None, None]`

Context manager that sets the thread-local trace and clears on exit.

Usage::

    with trace_context(my_trace) as t:
...

## Calls

- [[eos_ai-substrate-execution_trace-py-clear_current_trace]]
- [[eos_ai-substrate-execution_trace-py-set_current_trace]]

## Decorators

- `@contextmanager`
