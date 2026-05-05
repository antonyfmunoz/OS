---
type: codebase-file
path: core/execution_contract.py
module: core.execution_contract
lines: 385
size: 13347
generated: 2026-04-12
---

# core/execution_contract.py

ExecutionContract — unified execution entry point for all EOS AI operations.

Every message in, every response out. Eight mandatory steps, no exceptions.
Never raises — always returns a result dict with ok=True/False.

...

**Lines:** 385 | **Size:** 13,347 bytes

## Depends On

- [[eos_ai-context-py]]
- [[eos_ai-db-py]]
- [[eos_ai-substrate-execution_trace-py]]

## Used By

- [[scripts-test_execution_contract-py]]

## Contains

- **fn** [[core-execution_contract-py-_resolve_session]]`(channel, username) → str`
- **fn** [[core-execution_contract-py-run_task]]`(text, channel, mode, username, metadata) → dict`
- **fn** [[core-execution_contract-py-_split_provider_model]]`(raw) → tuple[str, str]`
- **fn** [[core-execution_contract-py-_result]]`(response, trace_id, session_id, provider, path, logged, ok, error) → dict`
- **fn** [[core-execution_contract-py-_learn_async]]`(trace_id, text, response, channel, username, provider) → None`

## Import Statements

```python
import sys
import threading
import time
import uuid as _uuid
from eos_ai.context import load_context_from_env
from eos_ai.context import EOSContext
from eos_ai.db import get_conn
from eos_ai.db import ORG_ID
from eos_ai.substrate.execution_trace import new_trace
from eos_ai.substrate.execution_trace import update_trace
from eos_ai.substrate.execution_trace import finalize_trace
from eos_ai.substrate.execution_trace import get_trace_history
```
