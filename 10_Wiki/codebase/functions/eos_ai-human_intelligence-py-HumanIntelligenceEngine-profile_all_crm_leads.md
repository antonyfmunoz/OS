---
type: codebase-function
file: eos_ai/human_intelligence.py
line: 414
generated: 2026-05-07
---

# HumanIntelligenceEngine.profile_all_crm_leads

**File:** [[eos_ai-human_intelligence-py]] | **Line:** 414
**Signature:** `profile_all_crm_leads() → dict`

**Class:** [[eos_ai-human_intelligence-py-HumanIntelligenceEngine]]

Alias for run_profile_cycle. Profiles all leads in 03_CRM/Leads/,
writes to Neon human_profiles.
Returns {"leads_processed": N, "profiles_written": N, "errors": K}.

## Calls

- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-run_profile_cycle]]

## Called By

- [[eos_ai-onboarding_backfill-py-OnboardingBackfill-_backfill_crm]]
