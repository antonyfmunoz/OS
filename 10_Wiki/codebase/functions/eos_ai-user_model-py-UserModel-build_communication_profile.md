---
type: codebase-function
file: eos_ai/user_model.py
line: 129
generated: 2026-04-12
---

# UserModel.build_communication_profile

**File:** [[eos_ai-user_model-py]] | **Line:** 129
**Signature:** `build_communication_profile() → dict`

**Class:** [[eos_ai-user_model-py-UserModel]]

Query last 30 days of interactions from Neon. Analyze input_summary
patterns. Synthesize via CognitiveLoop.

Returns:
    communication_style:   str
...

## Calls

- [[eos_ai-agent_runtime-py-AgentRuntime-run]]
- [[eos_ai-cognitive_loop-py-CognitiveLoop-run]]
- [[eos_ai-db-py-get_conn]]
- [[eos_ai-user_model-py-UserModel-get_trust_level]]

## Called By

- [[eos_ai-user_model-py-UserModel-update_profile]]
