---
type: codebase-function
file: core/execution_contract.py
line: 75
generated: 2026-04-12
---

# run_task

**File:** [[core-execution_contract-py]] | **Line:** 75
**Signature:** `run_task(text, channel, mode, username, metadata) → dict`

Execute a single task through the full EOS pipeline.

Args:
    text: Raw user input.
    channel: Origin channel — "discord", "telegram", "voice", "cli".
...

## Calls

- [[core-execution_contract-py-_learn_async]]
- [[core-execution_contract-py-_resolve_session]]
- [[core-execution_contract-py-_result]]
- [[core-execution_contract-py-_split_provider_model]]
- [[eos_ai-context-py-load_context_from_env]]
- [[eos_ai-substrate-execution_trace-py-_TraceHistory-record]]
- [[eos_ai-substrate-execution_trace-py-finalize_trace]]
- [[eos_ai-substrate-execution_trace-py-get_trace_history]]
- [[eos_ai-substrate-execution_trace-py-new_trace]]
- [[eos_ai-substrate-execution_trace-py-update_trace]]

## Called By

- [[scripts-test_execution_contract-py-main]]
