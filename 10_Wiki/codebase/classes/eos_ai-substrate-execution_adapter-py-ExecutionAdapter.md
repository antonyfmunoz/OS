---
type: codebase-class
file: eos_ai/substrate/execution_adapter.py
line: 49
generated: 2026-05-07
---

# ExecutionAdapter

**File:** [[eos_ai-substrate-execution_adapter-py]] | **Line:** 49

Contract for execution plane adapters.

Adapters are stateless workers. They receive a request, run the primitive,
and return a result. They never make decisions about WHAT to run.

...

## Inherits From

- `Protocol`

## Methods

- [[eos_ai-substrate-execution_adapter-py-ExecutionAdapter-adapter_id]]`() → str` — 
- [[eos_ai-substrate-execution_adapter-py-ExecutionAdapter-node_id]]`() → str` — 
- [[eos_ai-substrate-execution_adapter-py-ExecutionAdapter-capabilities]]`() → frozenset[str]` — 
- [[eos_ai-substrate-execution_adapter-py-ExecutionAdapter-execute]]`(request) → ExecutionResult` — 
- [[eos_ai-substrate-execution_adapter-py-ExecutionAdapter-health]]`() → AdapterHealth` — 
