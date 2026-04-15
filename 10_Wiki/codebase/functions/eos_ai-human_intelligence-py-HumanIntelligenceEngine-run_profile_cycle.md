---
type: codebase-function
file: eos_ai/human_intelligence.py
line: 368
generated: 2026-04-12
---

# HumanIntelligenceEngine.run_profile_cycle

**File:** [[eos_ai-human_intelligence-py]] | **Line:** 368
**Signature:** `run_profile_cycle() → dict`

**Class:** [[eos_ai-human_intelligence-py-HumanIntelligenceEngine]]

Loop all lead files. Build or refresh profiles older than 48 hours.
Returns {"built": N, "skipped": M, "errors": K}.

## Calls

- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-_all_lead_files]]
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-_fetch_profile_row]]
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-_is_stale]]
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-_parse_lead_file]]
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-build_profile]]

## Called By

- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-profile_all_crm_leads]]
