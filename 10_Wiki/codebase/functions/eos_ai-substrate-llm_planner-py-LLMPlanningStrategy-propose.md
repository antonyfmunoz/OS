---
type: codebase-function
file: eos_ai/substrate/llm_planner.py
line: 636
generated: 2026-05-07
---

# LLMPlanningStrategy.propose

**File:** [[eos_ai-substrate-llm_planner-py]] | **Line:** 636
**Signature:** `propose(canonical_state, state_hash, active_intents) → LLMProposalResult`

**Class:** [[eos_ai-substrate-llm_planner-py-LLMPlanningStrategy]]

Propose candidate events from current state.

Args:
    canonical_state: Pre-canonicalized state JSON string.
    state_hash: Pre-computed hash of canonical_state.
...

## Calls

- [[eos_ai-substrate-llm_planner-py-EventTypeRegistry-get]]
- [[eos_ai-substrate-llm_planner-py-EventTypeRegistry-validate_proposal]]
- [[eos_ai-substrate-llm_planner-py-_canonical_json]]
- [[eos_ai-substrate-llm_planner-py-_log]]
- [[eos_ai-substrate-llm_planner-py-_sha256_prefix]]
- [[eos_ai-substrate-llm_planner-py-build_llm_prompt]]
- [[eos_ai-substrate-llm_planner-py-compute_prompt_hash]]
