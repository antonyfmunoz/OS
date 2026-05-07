---
type: codebase-function
file: eos_ai/substrate/llm_planner.py
line: 233
generated: 2026-05-07
---

# EventTypeRegistry.get

**File:** [[eos_ai-substrate-llm_planner-py]] | **Line:** 233
**Signature:** `get(event_type) → EventSchema | None`

**Class:** [[eos_ai-substrate-llm_planner-py-EventTypeRegistry]]

Look up a schema by event type.

## Called By

- [[eos_ai-substrate-llm_planner-py-EventTypeRegistry-validate_event]]
- [[eos_ai-substrate-llm_planner-py-LLMPlanningStrategy-propose]]
- [[eos_ai-substrate-llm_planner-py-ProposedEvent-from_dict]]
- [[eos_ai-substrate-llm_planner-py-_build_event_catalog]]
- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-_check_drift]]
- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-_get_key_lock]]
- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-_revalidate_canonical]]
- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-_store_get]]
- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-evaluate]]
