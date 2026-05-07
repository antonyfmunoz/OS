---
type: codebase-class
file: eos_ai/authority_engine.py
line: 43
generated: 2026-05-07
---

# AuthorityEngine

**File:** [[eos_ai-authority_engine-py]] | **Line:** 43

*No docstring.*

## Methods

- [[eos_ai-authority_engine-py-AuthorityEngine-__init__]]`(ctx)` — 
- [[eos_ai-authority_engine-py-AuthorityEngine-_load_org_autonomy]]`() → int` — 
- [[eos_ai-authority_engine-py-AuthorityEngine-classify_action]]`(action_type) → str` — 
- [[eos_ai-authority_engine-py-AuthorityEngine-get_autonomy_level]]`(workflow_id) → int` — 
- [[eos_ai-authority_engine-py-AuthorityEngine-check_can_execute]]`(action_type, workflow_id) → dict` — 
- [[eos_ai-authority_engine-py-AuthorityEngine-queue_for_approval]]`(action_type, payload, agent) → str` — 
- [[eos_ai-authority_engine-py-AuthorityEngine-execute_or_queue]]`(action_type, payload, agent, execute_fn) → dict` — 
- [[eos_ai-authority_engine-py-AuthorityEngine-approve]]`(approval_id) → dict` — 
- [[eos_ai-authority_engine-py-AuthorityEngine-_create_agent_soul_doc]]`(agent_spec) → None` — Write a soul doc to agents/ when a new agent is approved.
- [[eos_ai-authority_engine-py-AuthorityEngine-reject]]`(approval_id) → dict` — 
- [[eos_ai-authority_engine-py-AuthorityEngine-get_pending]]`() → list` — 
