---
type: codebase-file
path: eos_ai/substrate/execution_trace.py
module: eos_ai.substrate.execution_trace
lines: 301
size: 9445
generated: 2026-04-11
---

# eos_ai/substrate/execution_trace.py

Execution trace for EOS request lifecycle.

Collects metadata as a request flows through:
mode routing → target policy → workflow delegation → workflow execution →
resource guard → context lifecycle → model router → response.
...

**Lines:** 301 | **Size:** 9,445 bytes

## Used By

- [[core-execution_contract-py]]
- [[scripts-test_execution_contract-py]]

## Contains

- **class** [[eos_ai-substrate-execution_trace-py-_TraceHistory]] — 8 methods
- **fn** [[eos_ai-substrate-execution_trace-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-execution_trace-py-new_trace]]`(source, mode, session_name) → dict`
- **fn** [[eos_ai-substrate-execution_trace-py-update_trace]]`(trace) → dict`
- **fn** [[eos_ai-substrate-execution_trace-py-finalize_trace]]`(trace, provider, model, latency_ms, result) → dict`
- **fn** [[eos_ai-substrate-execution_trace-py-format_trace_compact]]`(trace) → str`
- **fn** [[eos_ai-substrate-execution_trace-py-get_trace_history]]`() → _TraceHistory`
- **fn** [[eos_ai-substrate-execution_trace-py-set_current_trace]]`(trace) → None`
- **fn** [[eos_ai-substrate-execution_trace-py-get_current_trace]]`() → Optional[dict]`
- **fn** [[eos_ai-substrate-execution_trace-py-clear_current_trace]]`() → None`
- **fn** [[eos_ai-substrate-execution_trace-py-trace_context]]`(trace) → Generator[dict, None, None]`

## Import Statements

```python
from __future__ import annotations
import collections
import sys
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Any
from typing import Generator
from typing import Optional
from uuid import uuid4
```
