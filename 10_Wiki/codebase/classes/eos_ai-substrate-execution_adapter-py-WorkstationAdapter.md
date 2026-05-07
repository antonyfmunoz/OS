---
type: codebase-class
file: eos_ai/substrate/execution_adapter.py
line: 247
generated: 2026-05-07
---

# WorkstationAdapter

**File:** [[eos_ai-substrate-execution_adapter-py]] | **Line:** 247

Wraps node_transport.send_task_via_http() behind the ExecutionAdapter protocol.

Translates ExecutionRequest -> action dict for the HTTP endpoint, calls
send_task_via_http, and translates the response -> ExecutionResult.
Stateless — no references to state stores, event logs, or other adapters.

## Methods

- [[eos_ai-substrate-execution_adapter-py-WorkstationAdapter-__init__]]`() → None` — 
- [[eos_ai-substrate-execution_adapter-py-WorkstationAdapter-adapter_id]]`() → str` — 
- [[eos_ai-substrate-execution_adapter-py-WorkstationAdapter-node_id]]`() → str` — 
- [[eos_ai-substrate-execution_adapter-py-WorkstationAdapter-capabilities]]`() → frozenset[str]` — 
- [[eos_ai-substrate-execution_adapter-py-WorkstationAdapter-execute]]`(request) → ExecutionResult` — Execute a request via HTTP to the workstation daemon. Never raises.
- [[eos_ai-substrate-execution_adapter-py-WorkstationAdapter-health]]`() → AdapterHealth` — Check workstation health via HTTP. Never raises.
