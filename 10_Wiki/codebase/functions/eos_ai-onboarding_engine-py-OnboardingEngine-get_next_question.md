---
type: codebase-function
file: eos_ai/onboarding_engine.py
line: 121
generated: 2026-05-07
---

# OnboardingEngine.get_next_question

**File:** [[eos_ai-onboarding_engine-py]] | **Line:** 121
**Signature:** `get_next_question(session) → Optional[str]`

**Class:** [[eos_ai-onboarding_engine-py-OnboardingEngine]]

Return the next question to ask, advancing steps as needed.
Returns None when all questions are answered (triggers provisioning).
Sets session.pending_question to the returned question.
