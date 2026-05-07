---
type: codebase-class
file: eos_ai/onboarding_engine.py
line: 59
generated: 2026-05-07
---

# OnboardingEngine

**File:** [[eos_ai-onboarding_engine-py]] | **Line:** 59

*No docstring.*

## Methods

- [[eos_ai-onboarding_engine-py-OnboardingEngine-__init__]]`(ctx) → None` — 
- [[eos_ai-onboarding_engine-py-OnboardingEngine-start_session]]`(org_id, user_id) → OnboardingSession` — 
- [[eos_ai-onboarding_engine-py-OnboardingEngine-get_session]]`(org_id) → Optional[OnboardingSession]` — 
- [[eos_ai-onboarding_engine-py-OnboardingEngine-clear_session]]`(org_id) → None` — 
- [[eos_ai-onboarding_engine-py-OnboardingEngine-get_welcome_message]]`() → str` — 
- [[eos_ai-onboarding_engine-py-OnboardingEngine-get_next_question]]`(session) → Optional[str]` — Return the next question to ask, advancing steps as needed.
- [[eos_ai-onboarding_engine-py-OnboardingEngine-store_answer]]`(session, answer) → None` — Store the answer to session.pending_question and advance index.
- [[eos_ai-onboarding_engine-py-OnboardingEngine-analyze_and_provision]]`(session) → dict` — AI analyses all answers and provisions the complete system.
- [[eos_ai-onboarding_engine-py-OnboardingEngine-get_completion_message]]`(data, results) → str` — 
