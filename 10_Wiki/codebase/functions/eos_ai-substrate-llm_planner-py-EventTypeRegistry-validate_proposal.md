---
type: codebase-function
file: eos_ai/substrate/llm_planner.py
line: 290
generated: 2026-05-07
---

# EventTypeRegistry.validate_proposal

**File:** [[eos_ai-substrate-llm_planner-py]] | **Line:** 290
**Signature:** `validate_proposal(proposal, config) → ValidationResult`

**Class:** [[eos_ai-substrate-llm_planner-py-EventTypeRegistry]]

Validate every ProposedEvent in a proposal.

Also enforces config limits: max_events_per_proposal,
max_payload_bytes_per_event, max_payload_bytes_total.

## Calls

- [[eos_ai-substrate-llm_planner-py-EventTypeRegistry-validate_event]]
- [[eos_ai-substrate-llm_planner-py-_canonical_json]]

## Called By

- [[eos_ai-substrate-llm_planner-py-LLMPlanningStrategy-propose]]
- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-_revalidate_canonical]]
