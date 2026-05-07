---
type: codebase-class
file: eos_ai/substrate/execution_adapter.py
line: 129
generated: 2026-05-07
---

# LocalRuntimeAdapter

**File:** [[eos_ai-substrate-execution_adapter-py]] | **Line:** 129

Wraps local_executor.execute_command() behind the ExecutionAdapter protocol.

Translates ExecutionRequest -> ControlCommand, calls the executor, and
translates the result dict -> ExecutionResult. Stateless — no references
to state stores, event logs, or other adapters.

## Methods

- [[eos_ai-substrate-execution_adapter-py-LocalRuntimeAdapter-__init__]]`() → None` — 
- [[eos_ai-substrate-execution_adapter-py-LocalRuntimeAdapter-adapter_id]]`() → str` — 
- [[eos_ai-substrate-execution_adapter-py-LocalRuntimeAdapter-node_id]]`() → str` — 
- [[eos_ai-substrate-execution_adapter-py-LocalRuntimeAdapter-capabilities]]`() → frozenset[str]` — 
- [[eos_ai-substrate-execution_adapter-py-LocalRuntimeAdapter-execute]]`(request) → ExecutionResult` — Execute a request via local_executor. Never raises.
- [[eos_ai-substrate-execution_adapter-py-LocalRuntimeAdapter-health]]`() → AdapterHealth` — Local executor is always available when the process is running.
