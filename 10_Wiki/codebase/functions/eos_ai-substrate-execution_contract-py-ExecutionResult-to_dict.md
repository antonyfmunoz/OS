---
type: codebase-function
file: eos_ai/substrate/execution_contract.py
line: 265
generated: 2026-05-07
---

# ExecutionResult.to_dict

**File:** [[eos_ai-substrate-execution_contract-py]] | **Line:** 265
**Signature:** `to_dict() → dict[str, Any]`

**Class:** [[eos_ai-substrate-execution_contract-py-ExecutionResult]]

Serialize to a plain dict suitable for JSON transport.

## Called By

- [[eos_ai-substrate-execution_authority-py-ExecutionAuthority-make_handler]]
- [[eos_ai-substrate-execution_events-py-build_execution_completed_event]]
- [[eos_ai-substrate-execution_events-py-build_execution_failed_event]]
- [[eos_ai-substrate-execution_events-py-build_execution_rejected_event]]
- [[eos_ai-substrate-execution_events-py-build_execution_requested_event]]
- [[eos_ai-substrate-execution_events-py-build_execution_retried_event]]
- [[eos_ai-substrate-execution_events-py-build_execution_timed_out_event]]
