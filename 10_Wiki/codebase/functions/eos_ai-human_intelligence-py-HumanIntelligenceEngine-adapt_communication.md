---
type: codebase-function
file: eos_ai/human_intelligence.py
line: 572
generated: 2026-04-12
---

# HumanIntelligenceEngine.adapt_communication

**File:** [[eos_ai-human_intelligence-py]] | **Line:** 572
**Signature:** `adapt_communication(target_human, human_type, message, context) → str`

**Class:** [[eos_ai-human_intelligence-py-HumanIntelligenceEngine]]

Adapt a message to this specific human's style and role context.

A message to an investor reads differently than the same message
to a team member or a lead. Routes through Sonnet.

...

## Calls

- [[eos_ai-agent_runtime-py-AgentRuntime-run]]
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-get_profile]]
