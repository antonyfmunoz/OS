---
type: codebase-function
file: eos_ai/memory.py
line: 180
generated: 2026-04-12
---

# AgentMemory.log_lead_scored

**File:** [[eos_ai-memory-py]] | **Line:** 180
**Signature:** `log_lead_scored(username, venture_id, comment_text, score, archetype, model_used, input_tokens, output_tokens) → str`

**Class:** [[eos_ai-memory-py-AgentMemory]]

Called by icp_scorer when a lead is qualified and a lead file is created.
Returns the new interaction_id (UUID) — store it in the lead file if needed.

## Calls

- [[eos_ai-db-py-get_conn]]
- [[eos_ai-db-py-resolve_skill]]
- [[eos_ai-db-py-resolve_venture]]
- [[eos_ai-memory-py-_tokens_to_neon]]

## Called By

- [[eos_ai-integration_test-py-main]]
- [[services-icp_scorer-py-create_lead_file]]
