---
type: codebase-function
file: eos_ai/substrate/execution_events.py
line: 25
generated: 2026-05-07
---

# build_execution_requested_event

**File:** [[eos_ai-substrate-execution_events-py]] | **Line:** 25
**Signature:** `build_execution_requested_event(request, session_name, run_id) → SchedulerEvent`

Build EXECUTION_REQUESTED event from an ExecutionRequest.

## Calls

- [[eos_ai-substrate-execution_contract-py-ExecutionRequest-to_dict]]
- [[eos_ai-substrate-execution_contract-py-ExecutionResult-to_dict]]

## Called By

- [[eos_ai-substrate-execution_authority-py-ExecutionAuthority-make_handler]]
