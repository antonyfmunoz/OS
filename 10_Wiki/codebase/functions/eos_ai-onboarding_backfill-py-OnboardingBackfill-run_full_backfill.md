---
type: codebase-function
file: eos_ai/onboarding_backfill.py
line: 43
generated: 2026-04-12
---

# OnboardingBackfill.run_full_backfill

**File:** [[eos_ai-onboarding_backfill-py]] | **Line:** 43
**Signature:** `run_full_backfill(venture_id) → dict`

**Class:** [[eos_ai-onboarding_backfill-py-OnboardingBackfill]]

Run all backfill sources in sequence.
Returns summary dict of what was found across all sources.

## Calls

- [[eos_ai-onboarding_backfill-py-OnboardingBackfill-_backfill_calendar]]
- [[eos_ai-onboarding_backfill-py-OnboardingBackfill-_backfill_crm]]
- [[eos_ai-onboarding_backfill-py-OnboardingBackfill-_backfill_drive]]
- [[eos_ai-onboarding_backfill-py-OnboardingBackfill-_backfill_gmail]]
- [[eos_ai-onboarding_backfill-py-OnboardingBackfill-_backfill_tasks]]
- [[eos_ai-onboarding_backfill-py-OnboardingBackfill-_build_knowledge_base]]
