---
type: codebase-function
file: services/discord_bot.py
line: 2543
generated: 2026-04-12
---

# cmd_onboard

**File:** [[services-discord_bot-py]] | **Line:** 2543
**Signature:** `cmd_onboard(ctx)`

Start the EOS onboarding flow for a new founder.

## Calls

- [[eos_ai-onboarding_engine-py-OnboardingEngine-get_next_question]]
- [[eos_ai-onboarding_engine-py-OnboardingEngine-get_welcome_message]]
- [[eos_ai-onboarding_engine-py-OnboardingEngine-start_session]]

## Decorators

- `@bot.command`
