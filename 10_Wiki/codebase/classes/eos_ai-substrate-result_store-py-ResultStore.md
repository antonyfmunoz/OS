---
type: codebase-class
file: eos_ai/substrate/result_store.py
line: 83
generated: 2026-04-11
---

# ResultStore

**File:** [[eos_ai-substrate-result_store-py]] | **Line:** 83

*No docstring.*

## Methods

- [[eos_ai-substrate-result_store-py-ResultStore-__init__]]`() → None` — 
- [[eos_ai-substrate-result_store-py-ResultStore-_load]]`() → None` — 
- [[eos_ai-substrate-result_store-py-ResultStore-_flush]]`() → None` — 
- [[eos_ai-substrate-result_store-py-ResultStore-_enforce_retention]]`() → None` — 
- [[eos_ai-substrate-result_store-py-ResultStore-put]]`(result) → None` — 
- [[eos_ai-substrate-result_store-py-ResultStore-get]]`(action_id) → Optional[IngestedResult]` — 
- [[eos_ai-substrate-result_store-py-ResultStore-get_many]]`(action_ids) → dict[str, IngestedResult]` — 
- [[eos_ai-substrate-result_store-py-ResultStore-by_node]]`(node_id) → list[IngestedResult]` — 
- [[eos_ai-substrate-result_store-py-ResultStore-by_status]]`(status) → list[IngestedResult]` — 
- [[eos_ai-substrate-result_store-py-ResultStore-all]]`() → list[IngestedResult]` — 
- [[eos_ai-substrate-result_store-py-ResultStore-latest]]`(limit) → list[IngestedResult]` — 
- [[eos_ai-substrate-result_store-py-ResultStore-stats]]`() → dict[str, Any]` — 
- [[eos_ai-substrate-result_store-py-ResultStore-clear]]`() → None` — Test helper. Drops in-memory rows AND the durable payload.
- [[eos_ai-substrate-result_store-py-ResultStore-__len__]]`() → int` — 
