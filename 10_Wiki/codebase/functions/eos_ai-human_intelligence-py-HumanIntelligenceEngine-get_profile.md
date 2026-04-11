---
type: codebase-function
file: eos_ai/human_intelligence.py
line: 320
generated: 2026-04-11
---

# HumanIntelligenceEngine.get_profile

**File:** [[eos_ai-human_intelligence-py]] | **Line:** 320
**Signature:** `get_profile(username, venture_id) → dict | None`

**Class:** [[eos_ai-human_intelligence-py-HumanIntelligenceEngine]]

Return stored profile dict, or None if not yet built.

## Calls

- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-_fetch_profile_row]]

## Called By

- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-adapt_communication]]
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-get_adapted_message]]
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-get_relationship_context]]
