---
type: codebase-function
file: eos_ai/human_intelligence.py
line: 332
generated: 2026-04-11
---

# HumanIntelligenceEngine.get_adapted_message

**File:** [[eos_ai-human_intelligence-py]] | **Line:** 332
**Signature:** `get_adapted_message(username, base_message) → str`

**Class:** [[eos_ai-human_intelligence-py-HumanIntelligenceEngine]]

Adapt a base outreach message to this specific person's communication
style and dominant pain. Falls back to base_message if no profile exists.

## Calls

- [[eos_ai-agent_runtime-py-AgentRuntime-run]]
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-get_profile]]
