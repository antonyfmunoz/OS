---
type: codebase-class
file: eos_ai/onboarding_backfill.py
line: 30
generated: 2026-04-12
---

# OnboardingBackfill

**File:** [[eos_ai-onboarding_backfill-py]] | **Line:** 30

*No docstring.*

## Methods

- [[eos_ai-onboarding_backfill-py-OnboardingBackfill-__init__]]`(ctx) → None` — 
- [[eos_ai-onboarding_backfill-py-OnboardingBackfill-run_full_backfill]]`(venture_id) → dict` — Run all backfill sources in sequence.
- [[eos_ai-onboarding_backfill-py-OnboardingBackfill-_backfill_drive]]`(venture_id) → None` — Read Google Drive docs and store as events for future retrieval.
- [[eos_ai-onboarding_backfill-py-OnboardingBackfill-_backfill_gmail]]`(venture_id) → None` — Extract email contacts and link them to the venture graph.
- [[eos_ai-onboarding_backfill-py-OnboardingBackfill-_backfill_calendar]]`(venture_id) → None` — Read 90 days of calendar events and store time/contact patterns.
- [[eos_ai-onboarding_backfill-py-OnboardingBackfill-_backfill_tasks]]`() → None` — Import existing Google Tasks into the Neon tasks table.
- [[eos_ai-onboarding_backfill-py-OnboardingBackfill-_backfill_crm]]`(venture_id) → None` — Profile all CRM leads — builds human_profiles in Neon.
- [[eos_ai-onboarding_backfill-py-OnboardingBackfill-_build_knowledge_base]]`(venture_id) → None` — Synthesize all gathered data into a structured business intelligence
- [[eos_ai-onboarding_backfill-py-OnboardingBackfill-get_backfill_status]]`() → str` — Return a Telegram-ready status summary.
