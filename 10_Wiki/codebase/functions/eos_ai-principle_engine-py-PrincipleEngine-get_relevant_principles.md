---
type: codebase-function
file: eos_ai/principle_engine.py
line: 364
generated: 2026-05-07
---

# PrincipleEngine.get_relevant_principles

**File:** [[eos_ai-principle_engine-py]] | **Line:** 364
**Signature:** `get_relevant_principles(task_type, venture_id) → list[str]`

**Class:** [[eos_ai-principle_engine-py-PrincipleEngine]]

Return principles relevant to the task type.
ROOT_RULE is always first — it is the permanent root.

Args:
    task_type:  Task domain — 'sales', 'content', 'research', 'ops',
...

## Called By

- [[eos_ai-principle_engine-py-PrincipleEngine-format_for_prompt]]
