---
type: codebase-function
file: eos_ai/human_intelligence.py
line: 244
generated: 2026-05-07
---

# HumanIntelligenceEngine.build_profile

**File:** [[eos_ai-human_intelligence-py]] | **Line:** 244
**Signature:** `build_profile(username) → dict`

**Class:** [[eos_ai-human_intelligence-py-HumanIntelligenceEngine]]

Read the lead file, synthesize via AI, store in memory.db, return profile.
Returns the profile dict, or raises FileNotFoundError if no lead file found.

## Calls

- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-_build_profile_prompt]]
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-_find_lead_file]]
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-_parse_lead_file]]
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-_store_profile]]

## Called By

- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-run_profile_cycle]]
